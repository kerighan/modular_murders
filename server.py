"""The game over WebSocket, one socket per detective. Usage: uvicorn server:app --reload

Messages from the client: {"type": "equip", "items": [...], "start": place}, {"type": "play", "key": [...]},
{"type": "score", "score": 0..1} in answer to a challenge. Messages to the client: {"type": "view", ...},
{"type": "events", "events": [...]}, {"type": "challenge", "kind", "difficulty"}, {"type": "error", "message"}.
The engine runs in a worker thread; a challenge blocks that thread until the client's score arrives.
"""

import asyncio
import logging
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from game import FREE_STARTS, ITEMS, PAID_STARTS, START, Game
from store import Store

try:
    from dialogue import speak
except ImportError:
    speak = None

app = FastAPI()
store = Store()
tables = {}  # seed -> Table


class Table:
    """One game and the sockets of its detectives."""

    def __init__(self, seed, players):
        self.seed, self.players = seed, list(players)
        self.game = Game(seed, players, challenge=self.challenge, speak=speak)
        self.sockets = {}  # name -> (websocket, inbox queue)
        self.equipped = set()
        self.loop = asyncio.get_event_loop()
        self.lock = threading.Lock()

    # ---- challenges: the engine thread asks the acting player's socket and waits
    def challenge(self, kind, difficulty):
        name = self.game.player.name
        if name not in self.sockets:
            return 0.0
        future = asyncio.run_coroutine_threadsafe(self.ask_score(name, kind, difficulty), self.loop)
        return float(future.result(timeout=120))

    async def ask_score(self, name, kind, difficulty):
        ws, inbox = self.sockets[name]
        await ws.send_json({"type": "challenge", "kind": kind, "difficulty": difficulty})
        while True:
            msg = await inbox.get()
            if msg.get("type") == "score":
                return max(0.0, min(1.0, float(msg.get("score", 0))))

    # ---- views
    async def push_views(self):
        for name, (ws, _) in list(self.sockets.items()):
            p = next(q for q in self.game.players if q.name == name)
            payload = {"type": "view", **self.game.view(p)}
            if name not in self.equipped:  # what there is to choose from, until they have chosen
                payload["setup"] = {"items": ITEMS, "free_starts": FREE_STARTS, "paid_starts": PAID_STARTS, "slots": 2}
            await ws.send_json(payload)

    async def send_events(self, name, events):
        if name in self.sockets:
            await self.sockets[name][0].send_json({"type": "events", "events": events})

    async def handle(self, name, msg):
        kind = msg.get("type")
        if kind == "equip":
            if name in self.equipped:
                return
            i = self.players.index(name)
            self.game.equip(i, msg.get("items", []), msg.get("start", START))
            self.equipped.add(name)
            if self.equipped == set(self.players):
                await self.send_events(self.game.player.name, self.game.start())
            await self.push_views()
        elif kind == "play":
            if self.equipped != set(self.players):
                await self.sockets[name][0].send_json({"type": "error", "message": "tout le monde n'est pas équipé"})
                return
            if self.game.player.name != name:
                await self.sockets[name][0].send_json({"type": "error", "message": "ce n'est pas votre tour"})
                return
            # JSON has no integers: 3 comes back as 3.0, and the engine indexes suspects by int
            key = tuple(int(x) if isinstance(x, float) and x.is_integer() else x for x in msg.get("key", []))
            try:
                with self.lock:
                    events = await asyncio.to_thread(self.game.play, key)
            except ValueError as e:
                await self.sockets[name][0].send_json({"type": "error", "message": str(e)})
                return
            except Exception as e:  # a bug in the engine or a model call: say so, keep playing
                logging.exception("play failed")
                await self.sockets[name][0].send_json({"type": "error", "message": f"{type(e).__name__}: {e}"})
                return
            try:
                store.save(str(self.seed), self.game)
            except Exception:  # an old murders.loom with another schema, for instance
                logging.exception("save failed: delete murders.loom if its schema is stale")
            await self.send_events(name, events)
            await self.push_views()


@app.websocket("/ws/{seed}/{name}")
async def socket(ws: WebSocket, seed: int, name: str, players: str = ""):
    """Join game `seed` as `name`. The first to connect creates it, `?players=Ada,Bob` sets the table."""
    await ws.accept()
    table = tables.get(seed)
    if table is None:
        table = tables[seed] = Table(seed, players.split(",") if players else [name])
    if name not in table.players:
        await ws.send_json({"type": "error", "message": "pas de place à cette table"})
        await ws.close()
        return
    inbox = asyncio.Queue()
    table.sockets[name] = (ws, inbox)
    await table.push_views()

    async def reader():
        try:
            while True:
                await inbox.put(await ws.receive_json())
        except WebSocketDisconnect:
            await inbox.put({"type": "bye"})

    task = asyncio.create_task(reader())
    try:
        while True:
            msg = await inbox.get()
            if msg.get("type") == "bye":
                break
            await table.handle(name, msg)
    finally:
        task.cancel()
        table.sockets.pop(name, None)
