"""Offline adapter for the existing game engine (Android and desktop review).

No HTTP server, database, LLM, or network access. The UI uses the same JSON
messages as server.py. A worker owns the game; QTE scores have their own queue
so waiting for a score never blocks the Android/Godot rendering thread.
"""

import copy
import json
import math
import os
from pathlib import Path
import queue
import random
import threading
import time
import uuid

from game import FREE_STARTS, ITEMS, PAID_STARTS, RULES_VERSION, START, Game

SAVE_VERSION = 2


class SoloSession:
    def __init__(self, save_path, seed=42, name="Ada", engine="legacy"):
        self.path = Path(save_path)
        if engine not in ("legacy", "causal"):
            raise ValueError("moteur inconnu")
        self.engine = engine
        self.seed, self.name = int(seed), str(name)
        self.case_id = uuid.uuid4().hex
        self.commands, self.scores, self.messages = queue.Queue(), queue.Queue(), queue.Queue()
        self.closed = threading.Event()
        self.waiting_score = threading.Event()
        self.game = None
        self.equipped = False
        self.worker = threading.Thread(target=self._run, name="nexus-solo", daemon=True)
        self.worker.start()

    def send(self, raw):
        try:
            msg = json.loads(raw)
            if not isinstance(msg, dict):
                raise ValueError("message invalide")
            if msg.get("type") == "score":
                if self.waiting_score.is_set():
                    value = float(msg.get("score", 0))
                    if not math.isfinite(value):
                        raise ValueError("score invalide")
                    self.scores.put(max(0.0, min(1.0, value)))
            else:
                self.commands.put(msg)
        except (TypeError, ValueError) as exc:
            self._emit("error", message=str(exc))

    def poll(self):
        result = []
        while True:
            try:
                result.append(self.messages.get_nowait())
            except queue.Empty:
                return json.dumps(result, ensure_ascii=False)

    def close(self):
        self.closed.set()
        self.scores.put(None)
        self.commands.put(None)

    def _emit(self, message_type, **payload):
        self.messages.put({"type": message_type, **payload})

    def _challenge(self, kind, difficulty):
        while not self.scores.empty():
            self.scores.get_nowait()
        self.waiting_score.set()
        self._emit("challenge", kind=kind, difficulty=difficulty)
        try:
            score = self.scores.get(timeout=120)
            if score is None:
                raise RuntimeError("partie fermée")
            return score
        finally:
            self.waiting_score.clear()

    def _fresh(self):
        self.case_id = uuid.uuid4().hex
        if self.engine == "causal":
            from causal_game import CausalGame
            self.game = CausalGame(self.seed, [self.name])
        else:
            self.game = Game(self.seed, [self.name], challenge=self._challenge)
        self.equipped = False
        self.legacy_auto_end = 0

    def _snapshot(self):
        if self.engine == "causal":
            return {"version": SAVE_VERSION, "engine": self.engine, "seed": self.seed, "case_id": self.case_id,
                    "name": self.name, "equipped": self.equipped, "game": self.game.snapshot()}
        return {
            "version": SAVE_VERSION, "seed": self.seed, "name": self.name, "case_id": self.case_id,
            "rules_version": RULES_VERSION,
            "equipped": self.equipped,
            "items": [sorted(p.items) for p in self.game.players],
            "starts": self.game.starts_chosen, "history": self.game.history,
            "legacy_auto_end": self.legacy_auto_end,
            "journals": [p.journal for p in self.game.players],
        }

    def _restore(self, data):
        if data["version"] not in (1, SAVE_VERSION):
            raise ValueError("version de sauvegarde incompatible")
        if data.get("engine", "legacy") != self.engine:
            raise ValueError("Cette sauvegarde appartient à un autre moteur d'enquête")
        self.seed, self.name = int(data["seed"]), str(data["name"])
        self.case_id = data.get("case_id") or self.case_id
        if self.engine == "causal":
            from causal_game import CausalGame
            self.game = CausalGame.restore(self.seed, self.name, data["game"], data["equipped"])
            self.equipped = data["equipped"]
            return
        if data["equipped"]:
            if data.get("rules_version") != RULES_VERSION:
                raise ValueError("ancienne génération de scénario : une nouvelle enquête est nécessaire")
            legacy = len(data["history"]) if data["version"] == 1 else data.get("legacy_auto_end", 0)
            if type(legacy) is not int or not 0 <= legacy <= len(data["history"]):
                raise ValueError("historique de tours incompatible")
            game = Game.replay(self.seed, [self.name], data["items"], data["history"],
                               starts=data["starts"], challenge=self._challenge, legacy_auto_end=legacy)
            self.game, self.equipped = game, True
            if "journals" in data:
                for p, journal in zip(game.players, data["journals"]):
                    p.journal = journal
            self.legacy_auto_end = legacy
        else:
            self._fresh()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as target:
            json.dump(self._snapshot(), target, ensure_ascii=False)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, self.path)

    def _try_save(self):
        try:
            self._save()
        except OSError as exc:
            self._emit("error", message=f"Partie non sauvegardée : {exc}")

    def _view(self, resumed=False):
        payload = self.game.view(self.game.players[0])
        payload["solo"] = {"seed": self.seed, "case_id": self.case_id, "resumed": resumed, "offline": True}
        if not self.equipped:
            payload["setup"] = self.game.setup() if self.engine == "causal" else {
                "items": ITEMS, "free_starts": FREE_STARTS, "paid_starts": PAID_STARTS, "slots": 2}
        self._emit("view", **payload)

    def _handle(self, msg):
        kind = msg.get("type")
        if kind == "restart":
            # Write a fresh, unequipped save: restarting the app retains this seed.
            self.seed = random.SystemRandom().randrange(0, 1001)
            self._fresh()
            self._try_save()
            self._emit("reset")
            self._view()
        elif kind == "equip" and not self.equipped:
            items, start = msg.get("items", []), msg.get("start", self.game.setup()["default_start"] if self.engine == "causal" else START)
            if not isinstance(items, list) or len(items) > 2 or len(set(items)) != len(items):
                raise ValueError("choisissez au maximum deux équipements différents")
            allowed_items = self.game.setup()["items"] if self.engine == "causal" else ITEMS
            if any(item not in allowed_items for item in items):
                raise ValueError("équipement inconnu")
            if start not in self.game.starts(items):
                raise ValueError("lieu de départ indisponible")
            if self.engine == "causal":
                difficulty = msg.get("difficulty", self.game.setup()["default_difficulty"])
                if difficulty not in self.game.setup()["difficulties"]:
                    raise ValueError("difficulté inconnue")
                self.game.equip(0, items, start, difficulty)
            else:
                self.game.equip(0, items, start)
            events = self.game.start()
            self.equipped = True
            self._try_save()
            self._emit("events", events=events)
            self._view()
        elif kind == "play":
            if not self.equipped:
                raise ValueError("choisissez votre équipement d'abord")
            raw_key = msg.get("key", [])
            if not isinstance(raw_key, list) or not raw_key:
                raise ValueError("action invalide")
            key = tuple(int(x) if isinstance(x, float) and x.is_integer() else x for x in raw_key)
            before = copy.deepcopy(self._snapshot())
            try:
                events = self.game.play(key)
            except Exception:
                self._restore(before)
                raise
            self._try_save()
            self._emit("events", events=events)
            self._view()
        else:
            raise ValueError("message inconnu ou préparation déjà terminée")

    def _run(self):
        try:
            resumed = False
            if self.path.exists():
                try:
                    saved = json.loads(self.path.read_text(encoding="utf-8"))
                    self._restore(saved)
                    if "case_id" not in saved:
                        self._try_save()  # Persist the identity when upgrading a v16 save.
                    resumed = self.equipped
                except Exception as exc:
                    # Keep the old bytes for recovery instead of overwriting them.
                    backup = self.path.with_name(self.path.name + f".invalid-{time.time_ns()}")
                    self.path.rename(backup)
                    if "incompatible" in str(exc) or "autre moteur" in str(exc):
                        # A new build starts from scratch: the old investigation is archived, not patched.
                        self._emit("events", events=["🔔 Nouvelle version du jeu : l'enquête précédente est archivée, une nouvelle commence."])
                    else:
                        self._emit("error", message=f"Sauvegarde illisible, conservée dans {backup.name} : {exc}")
                    self.seed = random.SystemRandom().randrange(0, 1001)
                    self._fresh()
            else:
                self._fresh()
            self._view(resumed)
            while not self.closed.is_set():
                msg = self.commands.get()
                if msg is None:
                    break
                try:
                    self._handle(msg)
                except Exception as exc:
                    if not self.closed.is_set():
                        self._emit("error", message=f"{type(exc).__name__} : {exc}")
                        self._view()
        except Exception as exc:
            self._emit("error", message=f"Démarrage solo impossible : {type(exc).__name__} : {exc}")


def _stdio():
    """Desktop development transport: local pipes, no listening TCP port."""
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--engine", choices=("causal", "legacy"), default="causal")
    args = parser.parse_args()
    session = SoloSession(args.save, args.seed, engine=args.engine)
    def output():
        while not session.closed.is_set():
            try:
                msg = session.messages.get(timeout=0.1)
                print(json.dumps(msg, ensure_ascii=False), flush=True)
            except queue.Empty:
                pass
    threading.Thread(target=output, daemon=True).start()
    try:
        for line in sys.stdin:
            session.send(line)
    finally:
        session.close()


if __name__ == "__main__":
    _stdio()
