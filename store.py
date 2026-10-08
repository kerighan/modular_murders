"""Local persistence with loom. A game is its seed, its equipment and its action history."""

from loom import DB
from loom.errors import DuplicateNameError

from game import Game

SCHEMA = {"id": "utf8[32]", "seed": "int64", "players": "json", "items": "json", "history": "json"}


class Store:
    def __init__(self, path="murders.loom"):
        self.db = DB(path)
        try:
            self.games = self.db.collection("games", SCHEMA, indexes={"id": "primary"})
        except DuplicateNameError:
            self.games = self.db.collection("games")

    def save(self, id, game):
        self.games.insert({
            "id": id, "seed": game.seed, "players": [p.name for p in game.players],
            "items": [sorted(p.items) for p in game.players], "history": game.history,
        })

    def load(self, id, challenge=None, speak=None):
        r = self.games[id]
        game = Game.replay(r["seed"], r["players"], r["items"], r["history"], challenge)
        game._speak = speak or game._speak
        return game

    def close(self):
        self.db.close()
