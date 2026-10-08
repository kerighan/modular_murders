"""Play in the terminal. Usage: python cli.py [seed]  |  python cli.py --resume SEED"""

import os
import random
import sys
import textwrap
import time

from collections import Counter

from city import GRID, STREETS, TRAIT_LABELS, TRAIT_TEXT, fact_label
from game import AP, ITEMS, Game
from genotype import TRAITS
from store import Store

try:
    from dialogue import speak
except ImportError:  # no aiquery: characters answer with the plain template
    speak = None

COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
STYLES = [  # (line prefix, ANSI code)
    ("Indice", "1;32"), ("Témoignage noté", "32"), ("Noté", "32"), ("Vous êtes", "1;36"), ("Vous trouvez", "33"), ("Vous remarquez", "35"), ("C'est chez", "35"),
    ("Il y a", "35"), ("⚡", "1;33"), ("—", "1"), ("📰", "1;35"), ("Réussi", "32"), ("Raté", "31"),
]


def paint(text, code=None):
    if not COLOR:
        return text
    code = code or next((c for prefix, c in STYLES if text.startswith(prefix)), "3;95" if " — " in text else None)
    return f"\033[{code}m{text}\033[0m" if code else text


BOX_STARTS = ("Vous trouvez", "Le labo", "Le code", "Le kit de hacking", "Vous sortez le kit")
BOX_ENDS = ("D'autres choses", "Vous avez fait le tour")


def box(lines, width=72):
    """A framed discovery: the story of the find, then the clue it yields."""
    wrapped = [w for line in lines for w in textwrap.wrap(line, width) or [""]]
    inner = max(len(w) for w in wrapped)
    title = "Indice" if any(l.startswith("Indice") for l in lines) else "Découverte"
    out = [f"╭─ {title} {'─' * (inner - len(title) - 1)}╮"]
    for line in lines:
        for w in textwrap.wrap(line, width) or [""]:
            body = paint(w, "1;32") if line.startswith("Indice") else w
            out.append(f"│ {body}{' ' * (inner - len(w))} │")
    out.append(f"╰{'─' * (inner + 2)}╯")
    print("\n".join(paint(o, "32") if i in (0, len(out) - 1) else o for i, o in enumerate(out)))


def say(events):
    block = []
    for e in events:
        if e.startswith("— Tour"):
            print(paint(f"\n{'═' * 40}\n  {e.strip('— .')}\n{'═' * 40}", "1;33"))
        elif e.startswith(BOX_STARTS) or (block and not e.startswith(BOX_ENDS)):
            block.append(e)
            if e.startswith("Indice"):
                box(block)
                block = []
        else:
            if block:
                box(block)
                block = []
            print(paint(e))
    if block:
        box(block)


WORDS = ["indice", "mobile", "alibi", "suspect", "preuve", "ruelle", "enquête", "cadavre"]


def pick(options, n=1):
    """Numbered menu; returns the chosen keys."""
    keys = list(options)
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {options[k]}")
    chosen = []
    while len(chosen) < n:
        try:
            i = int(input("> ")) - 1
            if 0 <= i < len(keys) and keys[i] not in chosen:
                chosen.append(keys[i])
        except ValueError:
            pass
    return chosen


def challenge(kind, difficulty):
    word, limit = random.choice(WORDS), 4 - 3 * difficulty
    print(paint(f"⚡ {kind.capitalize()} : tapez « {word} » en moins de {limit:.1f}s"))
    t = time.time()
    ok = input("> ").strip().lower() == word and time.time() - t <= limit
    print(paint("Réussi !" if ok else "Raté."))
    return ok


W = 24  # map cell width


def ascii_map(game, p):
    """The grid of streets, the player's cell in brackets, houses counted per street."""
    street = p.place if p.place in STREETS else game.map[p.place][1][0]
    houses = Counter(game.map[h][1][0] for h in game.map if h.startswith("house_"))
    glance = game.glance(p)

    def cell(q):
        if not q:
            return " " * W
        if q == street and p.place != street:  # inside a house: just its name
            return f"{f'[{game.place_label(p, p.place)}]':^{W}}"
        label = game.label(q)
        people, lit = glance.get(q, (0, None))
        if houses[q]:
            label += f" ⌂{houses[q]}" if lit is None else f" ⌂{lit}/{houses[q]}"
        if people:
            label += " " + ("●" * people if people <= 3 else f"●×{people}")
        return f"{f'[{label}]' if q == street else label:^{W}}"

    lines = []
    for r, row in enumerate(GRID):
        lines.append("".join(cell(q) + ("──" if q and c + 1 < len(row) and row[c + 1] else "  ") for c, q in enumerate(row)))
        if r + 1 < len(GRID):
            lines.append("".join(" " * (W // 2) + ("│" if q and GRID[r + 1][c] else " ") + " " * (W - W // 2 + 1) for c, q in enumerate(row)))
    return "\n".join(lines)


def notebook(game, p):
    certain, _ = game.deduce(p)
    facts = ", ".join(fact_label(f) for f in p.facts) or "aucune pour l'instant"
    trusted = ", ".join(fact_label(f) for f in certain - p.facts)
    print(f"\nPreuves : {facts}" + (f"\nTémoignages fiables : {trusted}" if trusted else ""))
    cols = list(TRAITS)
    print(f"      {'suspect':<10}" + "".join(f"{TRAIT_LABELS[t]:<10}" for t in cols))
    for r in game.notebook(p):
        cells = "".join(f"{TRAIT_TEXT[r['traits'][t]] if t in r['traits'] else '?':<10}" for t in cols)
        notes = []
        if r["claim"]:
            status = {True: "confirmé", False: "à vérifier", None: "invérifiable"}[r["alibi"]]
            notes.append(f"{r['claim']}" + (f" avec {', '.join(r['with'])}…" if r["with"] else "") + f" ({status})")
        if r["said"]:
            notes.append("dit : " + ", ".join(fact_label(f) for f in r["said"]))
        row = f"  {'xx' if r['out'] else '  '}  {r['name']:<10}{cells}" + "  |  ".join(notes)
        print(paint(row, "2") if r["out"] else row)
    print()


def main(argv):
    store = Store()
    if argv[:1] == ["--resume"]:
        seed = int(argv[1])
        game = store.load(str(seed), challenge, speak)
        events = game.arrive(game.player)
    else:
        seed = int(argv[0]) if argv else random.randrange(10**6)
        game = Game(seed, challenge=challenge, speak=speak)
        print(f"Partie {seed}. Choisissez 2 objets :")
        game.equip(0, pick(ITEMS, n=2))
        events = game.start()
    print(f"\n{game.n} suspects. Vous commencez devant la scène de crime. Sur la carte : ● une personne dans la rue, ⌂2/5 deux maisons éclairées sur cinq, visible alentour seulement.\n")

    shown = 0
    while not game.winner:
        say(events)
        p = game.player
        for _, author, text in game.log[shown:]:
            if author != p.name:  # what the others did, public knowledge
                print(paint(f"📰 {text}"))
        shown = len(game.log)
        print("\n" + ascii_map(game, p))
        print(paint(f"\n[{p.name}, tour {game.tick + 1}, {p.ap}/{AP} PA]", "1"))
        options = game.options()
        taxi = {k: v for k, v in options.items() if v.startswith("Taxi")}
        keys = [k for k in options if k not in taxi]
        for i, k in enumerate(keys, 1):
            print(f"  {paint(str(i), '1')}. {options[k]}")
        if taxi:
            print("  t. Taxi…")
        print("  c. Carnet (gratuit)")
        answer = input("> ").strip().lower()
        if answer == "c":
            notebook(game, p)
            events = []
            continue
        if answer == "t" and taxi:
            events = game.play(pick(taxi)[0])
            store.save(str(seed), game)
            continue
        try:
            key = keys[int(answer) - 1]
        except (ValueError, IndexError):
            events = []
            continue
        events = game.play(key)
        store.save(str(seed), game)
    say(events)
    store.close()


if __name__ == "__main__":
    main(sys.argv[1:])
