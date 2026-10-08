from collections import deque

import pytest

from city import FAR_TRAITS
from game import AP, Game
from genotype import BloodType, Gender, HairColor, Height, LinkToVictim
from store import Store

SEEDS = range(40)


def path(game, src, dst):
    """Next step from src towards dst, or None if already there."""
    prev, queue = {src: None}, deque([src])
    while queue:
        node = queue.popleft()
        for n in game.map[node][1]:
            if n not in prev:
                prev[n] = node
                queue.append(n)
    if src == dst or dst not in prev:
        return None
    while prev[dst] != src:
        dst = prev[dst]
    return dst


def bot(seed, max_turns=60):
    """A greedy detective: collect what's here, walk to useful places, accuse when sure."""
    g = Game(seed, challenge=lambda *a: True)
    g.equip(0, ["forensic_kit", "crowbar"])
    g.start()
    p = g.players[0]
    while not g.winner and g.tick < max_turns:
        opts, rows = g.options(), g.notebook(p)
        alive = [r for r in rows if not r["out"]]
        if len(alive) == 1 and ("accuse", alive[0]["id"]) in opts:
            g.play(("accuse", alive[0]["id"]))
            continue
        if g.pending:  # three questions: what they saw, their alibi, their link
            g.play(next(k for k in opts if k[0] == "ask"))
            continue
        local = next((k for k in opts if k[0] in ("authorize", "search", "unlock", "interrogate", "ring", "observe", "file", "record", "verify")), None)
        if local:
            g.play(local)
            continue
        needed = {type(f) for f in g.deduce(p)[0]}
        if len(alive) == 1 and alive[0]["name"] != "?":
            targets = {"police"}
        elif not p.authorized:
            targets = {"police"}
        else:
            certain, _ = g.deduce(p)
            targets = {e.place for e in g.evidence if e.place and e.fact not in certain and e.id not in p.found}
            for e in g.evidence:  # a locked phone: fetch the code, then come back to it
                if e.phone and e.id in p.found and e.fact not in p.facts:
                    targets.add(e.place if p.code else "victim_house")
            for e in g.evidence:  # testimonies: find the witness, then make them trustworthy
                if e.person and e.fact not in certain and p.alibis.get(e.who, False) is False:
                    targets.add((g.alibi_place(e.who) if e.who in p.talked else g.where[e.who]) or "police")
            if not targets:  # learn what rules the remaining suspects in or out
                for r in alive:
                    missing = needed - set(r["traits"])
                    if r["name"] == "?":
                        targets.add(f"house_{r['id']}")
                    elif not missing:
                        continue
                    elif BloodType in missing:
                        targets.add("hospital")
                    elif missing <= {LinkToVictim, Gender, Height, HairColor}:
                        targets.add("police")
                    elif missing:
                        targets.add(g.where[r["id"]])
        steps = [path(g, p.place, t) for t in targets]
        step = next((s for s in steps if s and ("move", s) in opts), None)
        g.play(("move", step) if step else ("end",))
    return g


@pytest.mark.parametrize("seed", SEEDS)
def test_bot_solves_the_case(seed):
    g = bot(seed)
    assert g.winner is not None, f"unsolved after {g.tick} turns"


def test_options_match_play_and_turn_flow():
    g = Game(seed=1)
    g.start()
    p = g.player
    assert p.ap == AP
    with pytest.raises(ValueError):
        g.play(("accuse", 0))
    for _ in range(AP):
        move = next(k for k in g.options() if k[0] == "move" and g.owner(k[1]) is None)
        g.play(move)
    assert p.ap == AP and g.tick == 1  # auto end of turn after the last action point


def test_wrong_accusation_penalty():
    g = Game(seed=3, challenge=lambda *a: True)
    g.equip(0, ["taxi"])
    g.start()
    p = g.player
    innocent = 1
    g.reveal(p, innocent, FAR_TRAITS, name=True)
    g.play(("move", "police"))
    g.play(("accuse", innocent))
    assert g.winner is None and innocent in p.cleared and g.tick == 3  # two turns lost


def test_lab_delay_without_kit():
    g = Game(seed=5)
    g.start()
    p = g.player
    blood = next(e for e in g.evidence if e.blood)
    g.examine(p, blood)
    assert blood.fact not in p.facts and p.lab
    g.play(("end",))
    assert blood.fact in p.facts and not p.lab


def test_store_roundtrip(tmp_path):
    g = bot(7, max_turns=4)
    store = Store(str(tmp_path / "t.loom"))
    store.save("7", g)
    store.close()
    store = Store(str(tmp_path / "t.loom"))
    h = store.load("7", challenge=lambda *a: True)
    store.close()
    p, q = g.players[0], h.players[0]
    assert (p.place, p.facts, p.known, p.names, p.found, h.tick) == (q.place, q.facts, q.known, q.names, q.found, g.tick)


def test_interrogation_is_three_questions_then_over():
    g = Game(seed=2, challenge=lambda *a: True)
    g.equip(0, ["taxi"])
    g.start()
    p = g.player
    s = [i for i in range(g.n) if not g.where[i].startswith("house")]
    g.play(("move", g.where[s[0]]))
    g.play(("interrogate", s[0]))
    assert g.pending and all(k[0] in ("ask", "stop") for k in g.options())
    for _ in range(3):
        g.play(next(k for k in g.options() if k[0] == "ask"))
    assert g.pending is None and ("interrogate", s[0]) not in g.options()


def test_murderer_lies_and_innocents_tell_the_truth():
    for seed in range(20):
        g = Game(seed=seed)
        p = g.players[0]
        assert g.lie != g.case[0][type(g.lie)]
        for s in range(g.n):
            intent, _ = g.answer_seen(p, s)
            if s == 0:
                assert g.lie in p.heard[0]
            elif g.testimony(s):
                assert all(f in g.case.facts for f in p.heard[s])
        assert all(e.who != 0 and e.place is None for e in g.evidence if e.person)
        assert g.map[f"house_{g.neighbor}"][1] == ["victim_street"]


def test_cleared_suspects_make_their_testimony_certain():
    g = Game(seed=4)
    p = g.players[0]
    witness = next((e.who for e in g.evidence if e.person), None)
    if witness is None:
        return
    g.answer_seen(p, witness)
    assert not g.deduce(p)[0]
    p.cleared.add(witness)
    assert g.deduce(p)[0] == set(p.heard[witness])


def test_persona_sheet_is_in_french_and_hides_nothing_needed():
    g = Game(seed=1)
    sheet = g.persona(0)
    assert sheet["nom"] == g.name(0) and "coupable" in sheet["rôle"]
    assert "coupable" not in g.persona(1)["rôle"]


def test_alibi_checks_are_fixed_per_suspect_and_hopeless_for_the_murderer():
    confirmed = failed = 0
    for seed in range(30):
        g = Game(seed=seed, players=["P1", "P2"])
        for s in range(g.n):
            if g.alibi_place(s) is None:
                continue
            answers = []
            for p in g.players:
                p.alibis[s], p.place = False, g.alibi_place(s)
                g.do_verify(p, s)
                answers.append(s in p.cleared)
            assert answers[0] == answers[1]  # same memory for every player
            confirmed += answers[0]
            failed += not answers[0]
    assert confirmed > 0 and failed > confirmed // 3


def test_every_fact_has_physical_evidence():
    for seed in range(50):
        g = Game(seed=seed)
        assert {e.fact for e in g.evidence if not e.person} == set(g.case.facts)


def test_night_reconstruction_is_consistent():
    for seed in range(30):
        g = Game(seed=seed)
        p = g.players[0]
        for s in range(g.n):
            g.answer_alibi(p, s)
        for s in range(g.n):
            place, cited = p.claims[s]
            assert 0 not in cited  # nobody saw the murderer that night
            assert set(cited) <= set(g.company(s))  # names are real, memories just incomplete
            assert all(g.night[t] == place for t in cited)
        # vouching spreads innocence, never to the murderer
        for s in range(1, g.n):
            if p.claims[s][0] != "home":
                p.cleared = {s}
                _, innocents = g.deduce(p)
                assert set(p.claims[s][1]) <= innocents and 0 not in innocents


def test_occupied_houses_are_rung_not_entered():
    for seed in range(10):
        g = Game(seed=seed, challenge=lambda *a: True)
        g.equip(0, ["taxi"])
        g.start()
        p = g.player
        home = [i for i in range(g.n) if g.where[i] == f"house_{i}"]
        if not home:
            continue
        street = g.map[f"house_{home[0]}"][1][0]
        g.play(("move", street))
        opts = g.options()
        assert ("move", f"house_{home[0]}") not in opts and ("ring", home[0]) in opts
        g.play(("ring", home[0]))
        assert g.pending and g.pending["who"] == home[0] and p.place == street
        return


def test_every_empty_house_can_be_searched():
    g = Game(seed=3, challenge=lambda *a: True)
    g.equip(0, ["taxi", "crowbar"])
    g.start()
    p = g.player
    empty = [i for i in range(1, g.n) if g.where[i] != f"house_{i}"]
    g.play(("move", f"house_{empty[0]}"))
    assert ("search",) in g.options()
    assert g.play(("search",))[0] == "Rien d'intéressant ici."
    assert ("search",) not in g.options()


def test_a_face_is_not_a_name_until_you_talk_or_are_told():
    g = Game(seed=5, challenge=lambda *a: True)
    g.equip(0, ["taxi"])
    g.start()
    p = g.player
    out = [i for i in range(g.n) if not g.where[i].startswith("house")]
    ev = g.play(("move", g.where[out[0]]))
    assert any(e.startswith("Vous remarquez quelqu'un") for e in ev)
    assert not p.knows(out[0]) and p.knows(out[0], Gender)
    g.play(("interrogate", out[0]))
    assert p.knows(out[0])
    g.reveal(p, out[1], [], name=True)  # someone mentioned them
    p.known.pop(out[1], None)
    g.where[out[1]] = p.place
    assert any("reconnaissez" in e for e in g.arrive(p))
