"""Causal stories, private knowledge and exact notes survive both transports."""
import json

import pytest

from game import Game
from store import Store
from loom.errors import DatabaseLockedError
from solo_runtime import SoloSession
from test_solo import receive


def game(seed=1, players=("Ada",)):
    # Explicit object-case fixture with a grounded pressure speaker in rules 13.
    # Seed 42 now legitimately produces a different family after partner sampling.
    g = Game(seed, players=players, challenge=lambda *_: 1.0)
    g.equip(0, ["taxi", "crowbar"])
    g.start()
    return g


def read(g, key):
    # Rules tests target the interaction, not travel/routine randomness.
    p, story = g.player, g.story
    p.place = story.sources[key]["place"]
    p.ap = 3
    if p.place == "crime_scene":
        p.authorized = True
    return g.play(("search",))


@pytest.mark.parametrize("seed", range(40))
def test_stories_are_deterministic_and_have_independent_converging_sources(seed):
    a, b = Game(seed), Game(seed)
    assert a.story.sources == b.story.sources
    story = a.story
    assert len(set(story.access)) >= 2 and 0 in story.access
    assert story.graph.minimum_depth() == 3
    assert story.rival != 0
    assert story.profiles[0]["pressure"] == story.profiles[story.rival]["pressure"]
    assert {doc["place"] for doc in story.sources.values()} <= set(a.map)
    assert all(doc["place"].startswith("house_") for key, doc in story.sources.items() if key in ("trace", "rival"))
    assert "handoff" not in story.sources and "relay" not in story.sources
    assert ("cache" in story.sources) == (story.object_fate == "hidden")


def test_no_story_spoilers_in_initial_view_or_other_detectives_notes():
    g = game(players=("Ada", "Bob"))
    ada, bob = g.players
    before = g.view(bob)
    assert before["journal"] == []
    assert before["story"]["window"] is None and before["story"]["object"] is None
    assert before["story"]["motive"] is None
    assert all(row["life"] is None for row in before["notebook"])
    read(g, "loss")
    assert "loss" in ada.story_found
    assert any(note["title"] == "Un objet manque" for note in ada.journal)
    assert not ada.names  # Missing property does not identify anyone.
    assert not ada.cleared and not ada.story_resolved
    for field in ("journal", "story", "notebook", "facts", "trusted", "conversation"):
        assert g.view(bob)[field] == before[field]
    assert not g.view(ada)["story"]["resolved"]


def test_motive_and_possession_alone_never_resolve_the_case():
    g = game()
    for key in ("loss", "access", "trace"):
        read(g, key)
    p = g.player
    p.place, p.ap = "bar", 3
    g.where[0] = "bar"
    assert ("confront", 0, "trace") in g.options()
    g.play(("confront", 0, "trace"))
    assert not p.story_resolved
    assert g.view(p)["story"]["motive"] is None
    assert not p.cleared
    assert ("confront", 0, "trace") not in g.options()
    read(g, "clock")
    p.place, p.ap = "bar", 3
    g.where[0] = "bar"
    assert ("confront", 0, "trace") in g.options()  # newly crossed evidence permits a follow-up
    g.play(("confront", 0, "trace"))
    assert not p.story_resolved  # a ticket alone is not proof of who used it
    p.place, p.ap, p.authorized = "cctv", 3, True
    g.play(("check_timeline", 0))
    p.place, p.ap = "bar", 3
    g.where[0] = "bar"
    g.play(("confront", 0, "trace"))
    assert p.story_resolved and g.view(p)["story"]["motive"]
    assert g.winner is None  # map travel and final accusation still belong to the player


def test_grounded_testimony_points_at_a_shared_problem_not_a_random_individual():
    g = game()
    speaker = next(s for s in range(g.n) if g.story.knowledge[s] == "pressure")
    p = g.player
    before = set(p.names)
    text, notes = g.answer_grudge(p, speaker)
    assert "aucune personne nommée" in notes[0]
    assert p.story_rumours[speaker]["people"] == []
    assert p.names == before
    assert all(g.name(s) not in text for s in g.story.pressure_people)
    assert next(lead for lead in g.story.leads_view(p) if lead["id"] == "motive")["destinations"] == []
    assert not p.facts and not p.heard and not p.cleared


def test_real_conflict_is_shared_but_verified_timing_can_clear_the_innocent():
    g = game()
    read(g, "rival")
    assert g.story.rival not in g.player.cleared
    g.player.place = g.story.check_place
    g.player.ap = 3
    g.play(("check_timeline", g.story.rival))
    assert g.story.rival in g.player.cleared
    assert 0 not in g.player.cleared
    assert not g.player.story_resolved
    assert g.story.family in ("theft", "blackmail", "revenge")


def test_documents_open_contextual_questions_and_a_consented_visit():
    g = game()
    read(g, "access")
    p, sid = g.player, next(s for s in g.story.access if s != 0)
    home = f"house_{sid}"
    p.place = g.map[home][1][0]
    g.where[sid] = home
    assert ("confront", sid, "access") in g.options()
    g.play(("confront", sid, "access"))
    assert sid in p.invited
    assert ("move", home) in g.options()
    p.ap = 3
    g.play(("move", home))
    assert g.caught_inside(p) == []


def test_invitation_opens_the_door_even_when_owner_is_away_without_tools_or_qte():
    g = game()
    p, sid = g.player, next(s for s in g.story.access if s != 0)
    home = f"house_{sid}"
    p.items.clear()
    p.invited.add(sid)
    p.place = g.map[home][1][0]
    g.where[sid] = "bar"
    g._challenge = lambda *_: 0.0
    events = g.play(("move", home))
    assert p.place == home
    assert not any("serrure" in event or "résiste" in event for event in events)


def test_a_spoken_appearance_lie_can_be_confronted_after_three_questions():
    g = game()
    p = g.player
    g.reveal(p, 0, [], name=True)
    p.facts.update(g.case.facts)
    # Retain support for an imported/legacy false statement, but do not
    # generate this identifying shortcut in a new case.
    g.lie = g.pick_lie()
    p.heard[0] = {g.lie}
    p.talked.add(0)
    p.place = g.where[0] = "bar"
    assert ("interrogate", 0) not in g.options()
    assert ("confront", 0, "statement") in g.options()
    g.play(("confront", 0, "statement"))
    assert not p.story_resolved
    assert "inventée" in g.view(p)["conversation"]["text"]


def test_being_caught_snooping_blocks_small_talk_not_a_new_document_confrontation():
    g = game()
    read(g, "trace")
    p = g.player
    p.shunned.add(0)
    p.place, p.ap = "bar", 3
    g.where[0] = "bar"
    assert ("confront", 0, "trace") in g.options()
    assert not any(key[0] == "talk_about" and key[1] == 0 for key in g.options())
    g.play(("confront", 0, "trace"))
    assert not p.story_resolved


def test_exact_spoken_notes_survive_loom_close_and_reopen(tmp_path):
    g = game()
    sid = g.suspects_at("bar")[0]
    # Travel is recorded so this history is fully replayable.
    g.play(("move", "bar"))
    g.play(("interrogate", sid))
    g._speak = lambda *_: "Une réponse exacte, pas la réplique modèle."
    g.play(("ask", "life"))
    before = g.view(g.player)["journal"]
    path = str(tmp_path / "notes.loom")
    store = Store(path)
    try:
        store.save("42", g)
    finally:
        store.close()
    store = Store(path)
    try:
        restored = store.load("42")
        assert restored.view(restored.player)["journal"] == before
        assert restored.player.story_profiles == g.player.story_profiles
        assert restored.options() == g.options()
    finally:
        store.close()


def test_second_loom_writer_is_refused_without_damaging_the_case(tmp_path):
    path = str(tmp_path / "exclusive.loom")
    first = Store(path)
    try:
        first.save("42", game(seed=42))
        with pytest.raises(DatabaseLockedError):
            Store(path)
        assert first.load("42").seed == 42
    finally:
        first.close()


def test_android_notes_and_story_resume_exactly_without_local_ui_storage(tmp_path):
    path = tmp_path / "solo.json"
    s = SoloSession(path)
    try:
        receive(s)
        s.send(json.dumps({"type": "equip", "items": ["crowbar", "taxi"], "start": "victim_street"}))
        receive(s)
        for key in (["move", "victim_house"], ["search"]):
            s.send(json.dumps({"type": "play", "key": key}))
            before = receive(s)
        s.close()
        s.worker.join(3)
        s = SoloSession(path)
        after = receive(s)
        assert after["journal"] == before["journal"]
        assert after["story"] == before["story"]
        assert after["notebook"] == before["notebook"]
        assert after["options"] == before["options"]
    finally:
        s.close()
        s.worker.join(3)


def test_targeted_questions_reveal_relationships_not_guilt_and_are_private():
    g = game(players=("Ada", "Bob"))
    p = g.player
    from genotype import LinkToVictim
    innocent, witness = next((target, sid) for sid, contacts in g.story.link_contacts.items()
                              for target in contacts if target != 0
                              and g.case[target][LinkToVictim] != LinkToVictim.UNKNOWN
                              and g.case[sid][LinkToVictim] != LinkToVictim.UNKNOWN)
    for sid in (innocent, witness):
        g.reveal(p, sid, [], name=True)
    g.answer_link(p, innocent)
    before = g.view(g.players[1])["notebook"]
    p.place = g.where[witness] = "bar"
    g.play(("talk_about", witness, innocent))
    row = next(r for r in g.view(p)["notebook"] if r["id"] == innocent)
    assert not row["relationship"]["contradiction"]
    assert row["relationship"]["witnesses"] == [g.name(witness)]
    assert not p.facts and not p.heard and not p.cleared and not p.story_resolved
    assert g.view(g.players[1])["notebook"] == before
    assert ("talk_about", witness, innocent) not in g.options()
    p.place, p.ap = "bar", 3
    g.where[innocent] = "bar"
    assert ("confront", innocent, "relationship") not in g.options()
    assert not g.story.link_view(p, innocent)["contradiction"]
    assert not p.story_resolved and g.winner is None
    assert ("confront", innocent, "relationship") not in g.options()


def test_unknown_relationships_are_not_invented_and_unknown_targets_not_selectable():
    g = game()
    p = g.player
    speaker = g.story.access[0]
    target = next(s for s in range(g.n) if s != speaker and s not in g.story.link_contacts[speaker])
    g.reveal(p, speaker, [], name=True)
    p.place = g.where[speaker] = "bar"
    assert ("talk_about", speaker, target) not in g.options()
    g.reveal(p, target, [], name=True)
    events = g.play(("talk_about", speaker, target))
    assert "Ce nom ne me dit rien" in events[0]
    assert target not in p.link_witnesses
    assert not p.facts and not p.cleared
