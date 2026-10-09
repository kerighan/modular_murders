"""Local persistence with loom. A game is its seed, its equipment and its action history."""

from loom import DB
from loom.errors import DuplicateNameError

from game import Game, RULES_VERSION

SCHEMA = {"id": "utf8[32]", "seed": "int64", "players": "json", "items": "json", "starts": "json", "history": "json"}


class Store:
    def __init__(self, path="murders.loom"):
        self.db = DB(path, exclusive=True)
        try:
            self.games = self.db.collection("games", SCHEMA, indexes={"id": "primary"})
        except DuplicateNameError:
            self.games = self.db.collection("games")

    def save(self, id, game):
        self.games.insert({
            "id": id, "seed": game.seed, "players": [p.name for p in game.players],
            "items": [sorted(p.items) for p in game.players], "starts": game.starts_chosen,
            # Version inside the existing JSON field: no collection migration.
            "history": {"version": 2, "actions": game.history,
                        "rules_version": RULES_VERSION,
                        "legacy_auto_end": game.legacy_auto_end,
                        "journals": [p.journal for p in game.players]},
        })

    def load(self, id, challenge=None, speak=None):
        r = self.games[id]
        saved = r["history"]
        if not isinstance(saved, dict) or saved.get("rules_version") != RULES_VERSION:
            raise ValueError("ancienne génération de scénario : une nouvelle enquête est nécessaire")
        if saved["version"] != 2:
            raise ValueError("version de sauvegarde incompatible")
        history, legacy = saved["actions"], saved["legacy_auto_end"]
        if type(legacy) is not int or not 0 <= legacy <= len(history):
            raise ValueError("historique de tours incompatible")
        game = Game.replay(r["seed"], r["players"], r["items"], history, challenge,
                           starts=r["starts"], legacy_auto_end=legacy)
        # Keep the actual spoken notes, including custom/model speech, not a
        # differently worded template produced while replaying.
        if isinstance(saved, dict) and "journals" in saved:
            for p, journal in zip(game.players, saved["journals"]):
                p.journal = journal
        game._speak = speak or game._speak
        return game

    def close(self):
        self.db.close()
