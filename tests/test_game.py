from collections import deque

import pytest

from city import FAR_TRAITS
from game import AP, GRUDGE, RULES_VERSION, Game
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
        alive_ids = {r["id"] for r in alive}
        local = next((k for k in opts if k[0] in ("authorize", "search", "unlock", "try_code", "lab", "interrogate", "ring", "observe", "verify")
                      or (k[0] in ("file", "record") and k[1] in alive_ids)), None)  # favours only on live candidates
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
            if g.pocket(p) and not p.unlocked and len(p.secrets) < 3:  # a locked phone: dig into the victim's life
                targets.add("victim_house")
            if any(e.fact not in certain for e, _, _ in g.lab):  # analyses waiting at the hospital
                targets.add("hospital")
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
                    elif BloodType in missing and p.favors["hospital"]:
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
    assert p.ap == 0 and g.tick == 0
    assert list(g.options()) == [("end",)]
    g.play(("end",))
    assert p.ap == AP and g.tick == 1


def test_wrong_accusation_penalty():
    g = Game(seed=3, challenge=lambda *a: True)
    g.equip(0, ["taxi"])
    g.start()
    p = g.player
    innocent = 1
    g.reveal(p, innocent, FAR_TRAITS, name=True)
    g.play(("move", "police"))
    g.play(("accuse", innocent))
    assert g.winner is None and innocent in p.cleared and g.tick == 0
    g.play(("end",))
    assert g.tick == 3  # two turns lost, only after manually ending the turn


def test_lab_results_are_read_at_the_hospital_by_anyone():
    g = Game(seed=5, players=["Ada", "Bob"], challenge=lambda *a: True)
    g.start()
    ada, bob = g.players
    blood = next(e for e in g.evidence if e.blood)
    g.examine(ada, blood)
    assert blood.fact not in ada.facts and g.lab and not g.lab_results(ada)
    ada.place = bob.place = "hospital"
    g.play(("end",))  # Bob's turn
    ev = g.play(("end",))  # a tick passes, Ada again, with her notification
    assert any(e.startswith("🔔 Le labo a fini") for e in ev)
    ev = g.play(("lab",))
    assert ev[0].startswith("Votre échantillon") and blood.fact in ada.facts
    g.play(("end",))
    assert g.player is bob
    ev = g.play(("lab",))
    assert ev[0].startswith("Ada a déposé") and blood.fact in bob.facts


def test_store_roundtrip(tmp_path):
    g = bot(7, max_turns=4)
    store = Store(str(tmp_path / "t.loom"))
    store.save("7", g)
    store.close()
    store = Store(str(tmp_path / "t.loom"))
    h = store.load("7", challenge=lambda *a: True)
    assert h.starts_chosen == g.starts_chosen
    store.close()
    p, q = g.players[0], h.players[0]
    assert (p.place, p.facts, p.known, p.names, p.found, h.tick) == (q.place, q.facts, q.known, q.names, q.found, g.tick)


def test_store_migrates_automatic_history_and_keeps_manual_tail(tmp_path):
    g = Game(42)
    g.equip(0, ["taxi"], "bar")
    g.start()
    g.auto_end = True
    for place in ("police", "bar", "police", "bar"):
        g.play(("move", place))
    path = str(tmp_path / "legacy.loom")
    store = Store(path)
    try:
        store.games.insert({"id": "old", "seed": g.seed, "players": ["Ada"],
                            "items": [["taxi"]], "starts": g.starts_chosen,
                            "history": {"version": 2, "rules_version": RULES_VERSION,
                                        "actions": g.history, "legacy_auto_end": len(g.history)}})
        restored = store.load("old")
        assert restored.tick == g.tick and restored.player.ap == g.player.ap
        assert restored.legacy_auto_end == 4 and not restored.auto_end
        restored.play(("move", "police"))
        restored.play(("move", "bar"))
        assert restored.player.ap == 0 and restored.tick == g.tick
        store.save("old", restored)
    finally:
        store.close()
    store = Store(path)
    try:
        again = store.load("old")
        assert again.player.ap == 0 and again.tick == g.tick
        again.play(("end",))
        assert again.tick == g.tick + 1
    finally:
        store.close()


def test_store_refuses_an_old_generator_without_modifying_its_record(tmp_path):
    store = Store(str(tmp_path / "old-rules.loom"))
    try:
        old = {"version": 2, "actions": [], "legacy_auto_end": 0,
               "journals": [[{"text": "An obsolete clue"}]]}
        store.games.insert({"id": "old", "seed": 42, "players": ["Ada"],
                            "items": [["taxi"]], "starts": ["bar"], "history": old})
        with pytest.raises(ValueError, match="ancienne génération"):
            store.load("old")
        assert store.games["old"]["history"] == old
    finally:
        store.close()


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


def test_descriptions_are_truthful_or_partial_not_a_unique_liar_shortcut():
    for seed in range(40):
        g = Game(seed=seed)
        p = g.players[0]
        for s in range(g.n):
            intent, _ = g.answer_seen(p, s)
            if s == 0:
                assert g.lie is None and 0 not in p.heard
                assert "aucun témoignage" in intent
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


def test_persona_sheet_never_tells_the_model_who_is_guilty():
    g = Game(seed=1)
    sheet = g.persona(0)
    assert sheet["nom"] == g.name(0)
    assert all("coupable" not in str(v) for s in range(g.n) for v in g.persona(s).values())
    assert len({g.mood[s] for s in range(g.n)}) > 1  # tempers are random, the murderer's included


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
        if p.place != street:
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
    events = g.play(("search",))
    assert any("papiers" in event or "correspondance" in event or "attestation" in event for event in events)
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


def test_the_phone_goes_to_whoever_finds_it():
    seed = next(s for s in range(40) if any(e.phone and e.place for e in Game(s).evidence))
    g = Game(seed, players=["Ada", "Bob"], challenge=lambda *a: True)
    for i in range(2):
        g.equip(i, ["taxi", "hacking_kit"])
    g.start()
    ada, bob = g.players
    phone = next(e for e in g.evidence if e.phone and e.place)
    ada.place, ada.authorized = phone.place, True
    while not any(e.phone for e in g.evidence if e.id in ada.found):
        g.current, ada.ap = 0, AP  # Ada keeps digging, whatever the turn order
        g.play(("search",))
    assert all(g.taken[e.id] == "Ada" for e in g.evidence if e.phone)
    assert phone.fact in ada.facts  # hacking kit: read on the spot
    assert any(text.endswith("téléphone de la victime.") for _, _, text in g.log)
    bob.place, bob.authorized = phone.place, True
    g.current = 1
    assert not any(e.phone for e in g.here(bob))


def test_a_locked_phone_tells_nothing_until_the_code_is_found():
    seed = next(s for s in range(40) if any(e.phone and e.place for e in Game(s).evidence) and Game(s).code)
    g = Game(seed, challenge=lambda *a: True)
    g.start()
    p = g.player
    phone = next(e for e in g.evidence if e.phone and e.place)
    p.place, p.authorized = phone.place, True
    ev = []
    while not g.pocket(p):
        ev = g.play(("search",))
    assert phone.text not in ev and phone.fact not in p.facts and not any(k[0] == "try_code" for k in g.options())
    assert g.play(("try_code", "0000"))[0] == "Code 0000 refusé."  # a free guess is always allowed
    p.place = "victim_house"
    while len(p.secrets) < 3:
        if p.ap == 0:
            g.play(("end",))
        g.play(("search",))
    if p.ap == 0:
        g.play(("end",))
    assert any(k[0] == "try_code" for k in g.options())
    answer = {"birthday": g.secrets[0][2], "pet": g.secrets[1][2], "memo": g.secrets[2][2]}[g.code]
    ev = g.play(("try_code", answer))
    assert p.unlocked and phone.text in ev and phone.fact in p.facts


def test_crime_scene_without_authorization_is_one_discreet_look():
    for seed in range(40):
        g = Game(seed, challenge=lambda *a: True)
        g.start()
        p = g.player
        pool = [e for e in g.evidence if e.place == "crime_scene"]
        if not pool or not any(e.portable for e in pool):
            continue
        p.place = "crime_scene"
        ev = g.play(("search",))
        assert ("search",) not in g.options()  # one look only
        assert not any(g.taken.get(e.id) for e in pool)  # nothing pocketed
        if all(e.portable for e in pool):
            assert ev[0].startswith("Il y a quelque chose là-bas")
        p.authorized = True
        assert ("search",) in g.options()
        return


def test_rumours_lean_on_the_murderer_without_naming_them_every_time():
    murderer = innocent = games = 0
    for seed in range(200):
        g = Game(seed)
        if g.case[0][LinkToVictim] not in GRUDGE:
            continue
        named = [g.gossip[s] for s in range(1, g.n) if g.gossip[s] is not None]
        linked = [t for t in range(1, g.n) if g.case[t][LinkToVictim] in GRUDGE]
        if not named or not linked:
            continue
        games += 1
        murderer += named.count(0) / len(named)
        innocent += sum(named.count(t) for t in linked) / len(named) / len(linked)
    assert 1.5 < murderer / innocent < 3  # about twice the odds of any single innocent
    assert murderer / games < .5  # still named by a minority


def test_starting_points_free_or_paid_with_an_item():
    g = Game(seed=1)
    assert "police" not in g.starts(["taxi"]) and "police" in g.starts(["contact_police"])
    with pytest.raises(ValueError):
        g.equip(0, ["taxi"], "police")
    g.equip(0, ["victim_key"], "victim_house")
    assert g.player.place == "victim_house" and "victim_house" in g.player.opened
    ev = g.start()
    assert ev[0] == "Vous êtes : Chez la victime."


def test_the_owner_coming_home_puts_you_back_on_the_street():
    for ok in (True, False):
        g = Game(seed=3, challenge=lambda *a: ok)
        g.equip(0, ["taxi", "crowbar"])
        g.start()
        p = g.player
        away = next(i for i in range(1, g.n) if g.where[i] != f"house_{i}")
        g.play(("move", f"house_{away}"))
        g.where[away] = f"house_{away}"  # they come home
        g._rolls = []
        ev = g.caught_inside(p)
        assert p.place == g.map[f"house_{away}"][1][0]
        assert (away in p.shunned) is (not ok)
        assert ("sans être vu" in ev[0]) is ok
        if not ok:
            assert g.play(("ring", away)) == [f"{g.name(away)} — Je n'ai rien à vous dire."] and not g.pending


def test_suspects_follow_personal_routines():
    g = Game(seed=8)
    for i in range(g.n):
        home, out, _ = g.routine[i]
        places = [g.place_at(i, t) for t in range(home + out)]
        assert places.count(f"house_{i}") == home and places.count(g.hangout[i]) == out
        assert g.place_at(i, 0) == g.place_at(i, home + out)  # periodic
    periods = {sum(g.routine[i][:2]) for i in range(g.n)}
    assert len(periods) > 1  # not everyone in phase


def test_interrogation_length_follows_the_score():
    for score, expected in ((0, 0), (.3, 1), (.6, 2), (1, 3)):
        g = Game(seed=2, challenge=lambda *a: score)
        g.equip(0, ["taxi"])
        g.start()
        s = next(i for i in range(g.n) if not g.where[i].startswith("house"))
        g.play(("move", g.where[s]))
        g.play(("interrogate", s))
        assert (g.pending["left"] if g.pending else 0) == expected


def test_favours_are_scarce_and_blood_only_settles_the_last_few():
    for seed in range(30):
        g = Game(seed)
        assert g.blood_candidates() <= 3
    g = Game(seed=4, challenge=lambda *a: 1)
    g.equip(0, ["contact_hospital"], "hospital")
    g.start()
    p = g.player
    assert p.favors == {"hospital": 4, "police": 2}
    for s in range(1, 5):
        g.reveal(p, s, [], name=True)
    for s in range(1, 5):
        p.ap = AP
        ev = g.play(("file", s))
    assert p.favors["hospital"] == 0 and ev[-1].startswith("L'infirmière ne vous doit plus rien")
    assert not any(k[0] == "file" for k in g.options())
    while g.tick < 3:
        ev = g.play(("end",))
    assert p.favors["hospital"] == 4  # the window reset
    assert "🔔 L'infirmière accepte à nouveau de vous rendre service." in ev


def test_public_events_reach_the_other_detectives_only():
    g = Game(seed=1, players=["Ada", "Bob"], challenge=lambda *a: 1)
    g.equip(0, ["taxi"])
    g.equip(1, ["taxi"])
    g.start()
    g.play(("move", "police"))
    assert g.inbox["Bob"] == ["📰 Ada entre au commissariat."] and g.inbox["Ada"] == []
    ev = g.play(("end",))
    assert "📰 Ada entre au commissariat." in ev and g.inbox["Bob"] == []


def test_view_is_plain_data_the_client_can_serialise():
    import json
    g = Game(seed=6, players=["Ada", "Bob"], challenge=lambda *a: 1)
    g.equip(0, ["taxi"])
    g.equip(1, ["taxi"])
    g.start()
    g.play(("move", "bar"))
    for p in g.players:
        v = g.view(p)
        json.dumps(v)  # no Enum, no engine object
        assert set(v) >= {"options", "notebook", "glance", "places", "progress", "scoreboard", "facts"}
    assert g.view(g.players[1])["options"] == []  # not their turn
    assert all(isinstance(k, tuple) for k, _ in g.view(g.players[0])["options"])
