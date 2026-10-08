# modular_murders

Procedural murder-mystery game, in the spirit of Minuit meurtres en mer, Cluedo and
Qui est-ce ?. Rival detectives roam a city, collect clues about the murderer's traits,
strike suspects off their notebook and race to the police station to accuse.

```
pip install -r requirements.txt
python cli.py 42            # play seed 42 in the terminal
python cli.py --resume 42   # pick up where you left (saved in murders.loom)
pytest
```

## Layers

- **Case** (`suspect.py`): draws the suspects, makes suspect 0 the murderer, picks the
  smallest set of their traits that singles them out. Traits and weights live in
  `genotype.py`, the clue catalogue in `clue.py`.
- **Game** (`game.py`, `city.py`): drops the case into the city. Places, evidence,
  suspects moving between home and hangout, items, action points, obstacles and
  challenges, accusation. Pure and deterministic: `options()` lists what the current
  player can do, `play(key)` does it and returns events. The client resolves
  challenges (QTEs) through a callback, so tests pass a stub.
- **Dialogue** (`dialogue.py`): characters voiced by gpt-6-luna through aiquery. The
  engine decides what someone says (alibi, link, testimony, the murderer's lie) and hands
  the model a character sheet; the line is checked for the facts it must carry and
  falls back to the plain text. Without aiquery, the plain text is used.
- **Store** (`store.py`): a game is saved as seed + equipment + action history and
  rebuilt by replay, with loom.
- **CLI** (`cli.py`): numbered menus, timed-typing challenges, the notebook on `c`.

```python
from game import Game

game = Game(seed=42, players=["Ada", "Bob"])
game.equip(0, ["crowbar", "forensic_kit"])
game.start()
game.options()                 # {("move", "bar"): "Aller : Bar", ...}
game.play(("move", "bar"))     # ["Vous êtes : Bar.", "Vous remarquez Hugo (...)"]
game.play(("interrogate", 3))  # a good look, then three questions among four
game.play(("ask", "seen"))     # innocents tell the truth or saw nothing, the murderer lies
game.notebook(game.player)     # rows the client renders as the Qui est-ce ? board
```
