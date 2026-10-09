"""Play in the terminal. Usage: python cli.py [seed]  |  python cli.py --resume SEED"""

import os
import random
import sys
import textwrap
import time

from collections import Counter

from city import TRAIT_LABELS
from game import AP, ITEMS, Game
from store import Store

try:
    from dialogue import speak
except ImportError:  # no aiquery: characters answer with the plain template
    speak = None

COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
STYLES = [  # (line prefix, ANSI code)
    ("Indice", "1;32"), ("Témoignage noté", "32"), ("Noté", "32"), ("Vous êtes", "1;36"), ("Vous trouvez", "33"), ("Vous remarquez", "35"), ("C'est chez", "35"),
    ("Il y a", "35"), ("⚡", "1;33"), ("—", "1"), ("📰", "1;35"), ("🔔", "1;36"), ("Réussi", "32"), ("Raté", "31"),
]


def paint(text, code=None):
    if not COLOR:
        return text
    code = code or next((c for prefix, c in STYLES if text.startswith(prefix)), "3;95" if " — " in text else None)
    return f"\033[{code}m{text}\033[0m" if code else text


BOX_STARTS = ("Vous trouvez", "Vous examinez", "Vous visionnez", "Votre échantillon", "Le code", "Le kit de hacking", "Vous sortez le kit", "Le téléphone s'ouvre", "Dossier de la victime")
BOX_ENDS = ("D'autres choses", "Vous avez fait le tour", "Vous êtes", "Vous remarquez", "Vous reconnaissez", "Il y a", "Dans les papiers", "Chez ", "Fenêtres")


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
        elif e.startswith(BOX_STARTS) or " a déposé un échantillon" in e or (block and not e.startswith(BOX_ENDS)):
            block.append(e)
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
    """Type the word: fast is a perfect score, in time a good one, a bit late a poor one."""
    word, limit = random.choice(WORDS), 4 - 3 * difficulty
    print(paint(f"⚡ {kind.capitalize()} : tapez « {word} » en moins de {limit:.1f}s (deux fois plus vite pour briller)"))
    t = time.time()
    typed = input("> ").strip().lower() == word
    elapsed = time.time() - t
    score = 0 if not typed else 1.0 if elapsed <= limit / 2 else .6 if elapsed <= limit else .25 if elapsed <= 1.5 * limit else 0
    print(paint({1.0: "Parfait !", .6: "Réussi.", .25: "Un peu tard.", 0: "Raté."}[score], "32" if score >= .6 else "31"))
    return score


W = 24  # map cell width


def ascii_map(v):
    """The grid of streets, the player's cell in brackets, apartments counted per street."""
    places = v["places"]
    street = places[v["place"]]["street"] or v["place"]
    houses = Counter(q["street"] for q in places.values() if q["street"])

    def cell(q):
        if not q:
            return " " * W
        if q == street and v["place"] != street:  # inside an apartment: just its name
            return f"{'[' + places[v['place']]['label'] + ']':^{W}}"
        label = places[q]["label"]
        people, lit = v["glance"].get(q, (0, None))
        if houses[q]:
            label += f" ⌂{houses[q]}" if lit is None else f" ⌂{lit}/{houses[q]}"
        if people:
            label += " " + ("●" * people if people <= 3 else f"●×{people}")
        if places[q]["searched"]:
            label += " ✓"
        return f"{f'[{label}]' if q == street else label:^{W}}"

    grid, lines = v["grid"], []
    for r, row in enumerate(grid):
        lines.append("".join(cell(q) + ("──" if q and c + 1 < len(row) and row[c + 1] else "  ") for c, q in enumerate(row)))
        if r + 1 < len(grid):
            lines.append("".join(" " * (W // 2) + ("│" if q and grid[r + 1][c] else " ") + " " * (W - W // 2 + 1) for c, q in enumerate(row)))
    return "\n".join(lines)


def notebook(v):
    facts = ", ".join(v["facts"]) or "aucune pour l'instant"
    print(f"\nPreuves : {facts}" + (f"\nTémoignages fiables : {', '.join(v['trusted'])}" if v["trusted"] else ""))
    cols = list(TRAIT_LABELS.values())
    print(f"      {'suspect':<10}" + "".join(f"{c:<10}" for c in cols) + "│ ce qu'on sait d'autre")
    for r in v["notebook"]:
        cells = "".join(f"{r['traits'].get(c, '?'):<10}" for c in cols)
        notes = []
        if r.get("home"):
            notes.append(f"domicile : {r['home']['region_label']} · {r['home']['label']}")
        if r.get("life"):
            notes.append(f"projet : {r['life']['goal']} · pression : {r['life']['pressure']}")
        if r.get("relationship"):
            rel = r["relationship"]
            if rel["claim"] is not None:
                notes.append(f"lien déclaré : {rel['claim']}")
            if rel["witnesses"]:
                notes.append(f"selon {', '.join(rel['witnesses'])} : {rel['reported']}" + (" · CONTRADICTION" if rel["contradiction"] else ""))
        if r["claim"]:
            notes.append(f"alibi : {r['claim']}" + (f" avec {', '.join(r['with'])}…" if r["with"] else "") + f" ({r['alibi']})")
        if r["said"]:
            notes.append("a vu : " + ", ".join(r["said"]))
        row = f"  {'xx' if r['out'] else '  '}  {r['name']:<10}{cells}│ " + "  ·  ".join(notes)
        print(paint(row, "2") if r["out"] else row)
    print()


def main(argv):
    store = Store(os.environ.get("NEXUS_SAVE", "murders.loom"))
    try:
        _play(argv, store)
    finally:
        store.close()


def _play(argv, store):
    compact = "--compact" in argv
    voice = None if "--offline" in argv else speak
    qte = (lambda *_: 1.0) if "--perfect" in argv else challenge
    argv = [arg for arg in argv if arg not in ("--offline", "--perfect", "--compact")]
    if argv[:1] == ["--resume"]:
        seed = int(argv[1])
        game = store.load(str(seed), qte, voice)
        events = game.resume()
    else:
        seed = int(argv[0]) if argv else random.randrange(10**6)
        game = Game(seed, challenge=qte, speak=voice)
        print(f"Partie {seed}. Choisissez 2 objets :")
        items = pick(ITEMS, n=2)
        print("Point de départ :")
        start = pick({place: game.label(place) for place in game.starts(items)})[0]
        game.equip(0, items, start)
        events = game.start()
        store.save(str(seed), game)
    print(f"\n{game.n} suspects. Sur la carte : ● une personne sur place, ⌂2/5 deux appartements éclairés sur cinq.\n")

    while True:
        say(events)
        v = game.view(game.player)
        if v["winner"]:
            break
        if not compact:
            print("\n" + ascii_map(v))
        pr = v["progress"]
        print(paint(f"\n[{v['player']}, tour {v['tick'] + 1}, {v['ap']}/{AP} PA · {pr['preuves']} preuves · {pr['documents']} documents · "
                    f"{pr['identifiés']} identifiés · {pr['écartés']} écartés, {pr['restants']} restants]", "1"))
        if len(v["scoreboard"]) > 1:
            print(paint("Tableau : " + "  ".join(f"{q['name']}: {q['preuves']} preuves, {q['écartés']} écartés" for q in v["scoreboard"]), "2"))
        options = dict(v["options"])
        taxi = {k: label for k, label in options.items() if label.startswith("Taxi")}
        keys = [k for k in options if k not in taxi]
        for i, k in enumerate(keys, 1):
            print(f"  {paint(str(i), '1')}. {options[k]}")
        if taxi:
            print("  t. Taxi…")
        print("  c. Carnet · n. Notes · q. Sauvegarder et quitter")
        if v["can_try_code"]:
            print("  k. Essayer un code de votre choix (1 PA)")
        answer = input("> ").strip().lower()
        if answer == "c":
            notebook(v)
            events = []
            continue
        if answer == "n":
            journal(v)
            events = []
            continue
        if answer == "q":
            store.save(str(seed), game)
            print("Affaire sauvegardée. Reprise : --resume " + str(seed))
            return
        if answer == "k" and v["can_try_code"]:
            key = ("try_code", input("code > ").strip())
        elif answer == "t" and taxi:
            key = pick(taxi)[0]
        else:
            try:
                key = keys[int(answer) - 1]
            except (ValueError, IndexError):
                events = []
                continue
        events = game.play(key)
        store.save(str(seed), game)


def journal(v):
    print("\nNOTES DE L'AFFAIRE")
    for note in v.get("journal", []):
        print(f"\n[Tour {note['turn']} · {note['kind']} · {note['source']}] {note['title']}")
        print(note["text"])
        for place in note["leads"]:
            print("  → " + v["places"][place]["label"])


if __name__ == "__main__":
    main(sys.argv[1:])
