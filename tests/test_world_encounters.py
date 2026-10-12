import json

import pytest

from city import FAR_TRAITS
from game import Game
from genotype import LinkToVictim


def fresh(seed=5, players=("Ada",)):
    g = Game(seed, players=players, challenge=lambda *_: 1)
    for i in range(len(players)):
        g.equip(i, ["taxi", "crowbar"], "bar")
    g.start()
    return g


@pytest.mark.parametrize("seed", range(20))
def test_presence_counts_every_actor_once_per_place_and_district(seed):
    g = fresh(seed)
    p = g.player
    before = (set(p.names), dict(p.known), list(p.journal), list(g.history))
    presence = g.view(p)["presence"]
    assert sum(row["count"] for row in presence["places"].values()) == g.n
    assert sum(row["count"] for row in presence["districts"].values()) == g.n
    for place, row in presence["places"].items():
        assert [person["id"] for person in row["people"]] == g.suspects_at(place)
        assert row["count"] == len(row["people"])
        for person in row["people"]:
            assert person["name"] is None and not person["known"]
            if person["id"] not in p.known:
                assert person["look"] == ""
    for region, row in presence["districts"].items():
        expected = {sid for sid, place in g.where.items()
                    if (g.map[place][1][0] if g.owner(place) is not None else place) == region}
        assert {person["id"] for person in row["people"]} == expected
    assert (set(p.names), dict(p.known), list(p.journal), list(g.history)) == before
    json.dumps(presence)


def test_presence_learned_identity_is_private_and_face_not_invented():
    g = fresh(players=("Ada", "Bob"))
    a, b = g.players
    sid = next(i for i in g.order if i not in a.known)
    g.reveal(a, sid, [], name=True)
    pa = next(person for row in g.presence_view(a)["places"].values() for person in row["people"] if person["id"] == sid)
    pb = next(person for row in g.presence_view(b)["places"].values() for person in row["people"] if person["id"] == sid)
    assert pa["name"] == g.name(sid) and pa["look"] == ""
    assert pb["name"] is None and not pb["known"] and pb["look"] == ""


def test_scene_is_consumed_only_by_listen_free_and_kept_in_private_notes():
    g = fresh(players=("Ada", "Bob"))
    a, b = g.players
    scene = g.view(a)["arrival_scene"]
    assert scene and len(scene["people"]) == 2
    assert g.view(a)["arrival_scene"] == scene  # no view side effects
    assert not a.scenes_seen
    before = (a.ap, g.tick, dict(g.where), set(a.facts), set(a.cleared), set(a.names), dict(a.heard))
    g.play(tuple(scene["key"]))
    assert scene["id"] in a.scenes_seen and not b.scenes_seen
    assert (a.ap, g.tick, dict(g.where), set(a.facts), set(a.cleared), set(a.names), dict(a.heard)) == before
    assert len([note for note in a.journal if note["kind"] == "conversation"]) == 1
    assert not b.journal
    assert g.view(a)["conversation"]["stage"] == "scene"
    assert len(g.view(a)["conversation"]["beats"]) == 2
    assert all(beat["person"]["name"] is None for beat in scene["beats"])
    assert g.arrival_scene(a) is None
    with pytest.raises(ValueError, match="not an option"):
        g.play(tuple(scene["key"]))


def test_scene_survives_replay_and_cannot_repeat_in_another_room():
    g = fresh()
    scene = g.arrival_scene(g.player)
    g.play(tuple(scene["key"]))
    restored = Game.replay(g.seed, [p.name for p in g.players], [sorted(p.items) for p in g.players], g.history,
                           starts=g.starts_chosen)
    assert restored.player.scenes_seen == g.player.scenes_seen
    assert restored.player.journal == g.player.journal
    assert restored.arrival_scene(restored.player) is None
    for sid in scene["people"]:
        restored.where[sid] = "cabaret"
    restored.player.place = "cabaret"
    next_scene = restored.arrival_scene(restored.player)
    assert next_scene is None or next_scene["id"] != scene["id"]


def test_scene_available_at_zero_ap_but_not_during_an_interrogation():
    g = fresh()
    scene = g.arrival_scene(g.player)
    g.player.ap = 0
    assert tuple(scene["key"]) in g.options()
    g.play(tuple(scene["key"]))
    assert g.player.ap == 0 and g.tick == 0
    g = fresh()
    sid = g.suspects_at("bar")[0]
    g.play(("interrogate", sid))
    assert g.pending and g.arrival_scene(g.player) is None
    assert not any(key[0] == "listen" for key in g.options())


def test_presence_stays_still_in_dialogue_and_updates_during_npc_phase():
    g = fresh()
    before = {place: [person["id"] for person in row["people"]] for place, row in g.presence_view(g.player)["places"].items()}
    sid = g.suspects_at("bar")[0]
    g.play(("interrogate", sid))
    g.play(("ask", "life"))
    assert {place: [person["id"] for person in row["people"]] for place, row in g.presence_view(g.player)["places"].items()} == before
    g.play(("stop",))
    g.play(("end",))
    assert {place: [person["id"] for person in row["people"]] for place, row in g.presence_view(g.player)["places"].items()} != before
    assert sum(row["count"] for row in g.presence_view(g.player)["places"].values()) == g.n


@pytest.mark.parametrize("seed", range(20))
def test_all_generated_exchanges_have_a_real_link_and_no_remote_actor(seed):
    g = fresh(seed)
    for place in g.map:
        present = g.suspects_at(place)
        for scene in g.story.scenes_at(place, present):
            a, b = scene["actors"]
            assert a in present and b in present and a != b
            assert {beat["actor"] for beat in scene["beats"]} == {a, b}
            if scene["topic"] == "relation":
                assert g.story.relations[a]["target"] == b or g.story.relations[b]["target"] == a
            elif scene["topic"] == "colleagues":
                assert g.case[a][LinkToVictim] == g.case[b][LinkToVictim] == LinkToVictim.COLLEAGUE
            else:
                assert g.map[f"house_{a}"][1][0] == g.map[f"house_{b}"][1][0]
            assert not any("Vérifiez" in beat["text"] or "horaires restent" in beat["text"] for beat in scene["beats"])


def test_arbitrary_provider_scene_is_projected_without_relation_specific_ui():
    g = fresh()
    actors = g.suspects_at("bar")[:2]
    g.story.scenes_at = lambda place, people: [{"id": "future-generator:train", "actors": actors,
                                              "beats": [{"actor": actors[0], "text": "Le dernier train est parti."},
                                                        {"actor": actors[1], "text": "Je sais."}]}]
    scene = g.arrival_scene(g.player)
    assert scene["id"] == "future-generator:train"
    g.play(tuple(scene["key"]))
    assert g.view(g.player)["conversation"]["beats"][1]["text"] == "Je sais."


def test_provider_cannot_smuggle_an_absent_speaker_into_a_public_scene():
    g = fresh()
    actors = g.suspects_at("bar")[:2]
    absent = next(i for i in g.order if i not in actors)
    g.story.scenes_at = lambda place, people: [{"id": "bad", "actors": actors,
                                              "beats": [{"actor": absent, "text": "Secret"}]}]
    assert g.arrival_scene(g.player) is None


def test_json_save_reload_keeps_scene_consumption(tmp_path):
    from solo_runtime import SoloSession
    from test_solo import receive
    save = str(tmp_path / "solo.json")
    session = SoloSession(save, 5)
    try:
        receive(session)
        session.send(json.dumps({"type": "equip", "items": ["taxi", "crowbar"], "start": "bar"}))
        view = receive(session)
        scene = view["arrival_scene"]
        assert scene
        session.send(json.dumps({"type": "play", "key": scene["key"]}))
        receive(session)
    finally:
        session.close()
        session.worker.join(3)
    restored = SoloSession(save, 5)
    try:
        view = receive(restored)
        assert view["arrival_scene"] is None
        assert any(note["kind"] == "conversation" for note in view["journal"])
    finally:
        restored.close()
        restored.worker.join(3)


def test_loom_save_reopen_keeps_one_shot_scene_and_exact_notes(tmp_path):
    from store import Store
    g = fresh()
    g.play(tuple(g.arrival_scene(g.player)["key"]))
    path = str(tmp_path / "scene.loom")
    writer = Store(path)
    try:
        writer.save("case", g)
    finally:
        writer.close()
    reader = Store(path)
    try:
        restored = reader.load("case")
        assert restored.player.scenes_seen == g.player.scenes_seen
        assert restored.player.journal == g.player.journal
        assert restored.arrival_scene(restored.player) is None
    finally:
        reader.close()
