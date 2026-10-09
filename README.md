# modular_murders

Procedural murder-mystery game, in the spirit of Minuit meurtres en mer, Cluedo and
Qui est-ce ?. Rival detectives roam a city, collect clues about the murderer's traits,
strike suspects off their notebook and race to the police station to accuse.

```
pip install -r requirements.txt
python cli.py 42            # play seed 42 in the terminal
python cli.py --resume 42   # pick up where you left (saved in murders.loom)
python cli.py 7 --offline --perfect --compact  # reproducible gameplay review
uvicorn server:app          # the same game over WebSocket, for the Godot client
pytest
```

## Layers

- **Case** (`suspect.py`): draws the suspects, makes suspect 0 the murderer, picks the
  longest minimal combination of shared traits that singles them out. Each trait
  and each physical artifact still matches at least two suspects. Traits live in
  `genotype.py`, the clue catalogue in `clue.py`.
- **Game** (`game.py`, `city.py`): drops the case into the city. Places, evidence,
  suspects moving between home and hangout, items, action points, obstacles and
  challenges, accusation. Pure and deterministic: `options()` lists what the current
  player can do, `play(key)` does it and returns events. The client resolves
  challenges (QTEs) through a callback, so tests pass a stub.
- **Dialogue** (`dialogue.py`): characters voiced by gpt-6-luna through aiquery. The
  engine decides what someone knows (alibi, link, truthful or partial testimony) and hands
  the model a character sheet; the line is checked for the facts it must carry and
  falls back to the plain text. Without aiquery, the plain text is used.
- **Story** (`narrative.py`): offline motives, shared pressures, missing objects,
  crime windows and independent verification. No forced intermediary: an object
  can be hidden anonymously or unavailable, and revenge has no stolen object.
  Recovery is never required; opportunity, motive and images converge. Neighbours can report
  relationships, but strangers do not invent gossip and innocents do not lie.
  `scenario_graph.py` enforces shared candidate sets: at least two per incriminating
  observation, convergence through independent axes. See [contracts](godot/SCENARIO_GRAPH.md).
  Contextual questions remain available after a normal interrogation.
- **Store** (`store.py`): seed + equipment + action history replay, with loom;
  exact journal text is also saved as JSON so spoken notes survive a restart.
- **CLI** (`cli.py`): numbered menus, timed-typing challenges, notebook on `c`,
  chronological notes on `n`, save and quit on `q`. `NEXUS_SAVE` isolates the DB.
- **Server** (`server.py`): one WebSocket per detective, `view` out, `play` in, challenges
  asked to the acting player's socket. `ws://host/ws/<seed>/<name>?players=Ada,Bob`.
- **Godot client** (`godot/`): procedural neon voxel city, touch navigation and RPG
  dialogue, portraits, Personnes / Pistes / Notes notebook, and a large generic
  lounge in the same 3D world (camera teleport, not a modal). Android embeds Python for
  offline solo play; desktop supports either solo or the existing server.
  See [Android build](godot/android-solo/README.md) and [handoff](godot/HANDOFF.md).

Turns end explicitly with `("end",)`, never automatically at zero AP. Pending
questions remain free to finish; inhabitants advance only at the end of the
detectives' round. Saves record both their format and scenario-rules version;
incompatible generators cannot mix old notes with a different reconstructed world.

Every client reads one thing, `Game.view(player)`, plain JSON-able data, and sends one
thing, an option key. Challenges (QTEs) return a score between 0 and 1.

```python
from game import Game

game = Game(seed=42, players=["Ada", "Bob"])
game.equip(0, ["crowbar", "forensic_kit"])
game.start()
game.options()                 # {("move", "bar"): "Aller : Le Néon Bleu", ...}
game.play(("move", "bar"))     # ["Vous êtes : Bar.", "Vous remarquez Hugo (...)"]
game.play(("interrogate", 3))  # a good look, then three questions among five
game.play(("ask", "seen"))     # truthful/partial testimony, or no testimony
game.notebook(game.player)     # rows the client renders as the Qui est-ce ? board
```

## Working on the Godot client

Godot is a single binary, installed at `~/.local/bin/godot` (4.7). Two terminals:

```
uvicorn server:app --reload       # terminal 1: the engine
godot --path godot -e             # terminal 2: the editor on the project; F5 runs, F8 stops
godot --path godot                # or run the game straight away, no editor
```

`godot/main.gd` coordinates the procedural scene; `city_visuals.gd`,
`interior_lounge.gd` and `rpg_dialogue.gd` provide the art and interactions. The bottom
"Output" panel of the editor shows script errors and `print()` calls. Without a window:

```
godot --headless --path godot --check-only --script res://main.gd   # syntax
godot --headless --path godot --quit-after 240                       # 4 seconds of runtime, errors on stderr
```

VS Code: the `godot-tools` extension gives GDScript completion when the editor is open
(it listens on port 6005). In the Godot editor, Editor Settings › Text Editor › External,
tick "Use External Editor" with exec path `code` and flags `{project} --goto {file}:{line}:{col}`
to open scripts in VS Code by double-clicking them.
