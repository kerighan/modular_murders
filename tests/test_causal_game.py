"""The same causal actions through the protocol consumed by the 3D client."""
import json
import time

import pytest

from causal_game import CausalGame, ITEMS, CAMERA_WINDOWS, QUESTIONS_PER_PA, at_label
from scenario_play import clock
from scenario_evening import remembered_times
from solo_runtime import SoloSession


def receive(session, kind="view", timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = session.messages.get(timeout=max(0.01, deadline - time.monotonic()))
        if message["type"] == kind:
            return message
        if message["type"] == "error":
            raise AssertionError(message["message"])
    raise AssertionError("No " + kind + " received")


def fresh(seed=7, skills=("fingerprints", "lockpick")):
    # Protocol bots are exhaustive, not fast: no deadline for them.
    game = CausalGame(seed, ["Ada"])
    game.equip(0, skills, game.case.crime.scene, "libre")
    return game


def seed_where(predicate, skills=("fingerprints", "lockpick")):
    """The first early seed whose case fits: tests describe a situation, not a seed."""
    for seed in range(40):
        game = fresh(seed, skills)
        if predicate(game):
            return game
    pytest.skip("no fitting case among the first seeds")


def travel(game, target):
    """Read the public address/route, not the authored criminal trajectory."""
    view = game.view(game.player)
    parent = view["places"][target]["street"]
    if parent and game.player.place != parent:
        travel(game, parent)
    if game.player.place == target:
        return
    if target in game.homes:
        for _ in range(96):
            if not game.occupants(target):
                break
            game.play(("end",))
        assert not game.occupants(target), "Could not find an unoccupied apartment"
        if not game.home_open(target):
            if not game.player.ap:
                game.play(("end",))
            if game.occupants(target):
                return travel(game, target)
            game.play(("unlock_home", target))  # picking the lock walks in
            if game.session.place == target:
                return
    while game.cost(target) > game.player.ap:
        game.play(("end",))
    if game.player.place == target:  # an ended turn may have walked you out to this street
        return
    if target in game.homes and game.occupants(target):
        return travel(game, target)
    game.play(("move" if parent else "walk", target))


def approach(game, pid):
    if game.speaker is not None:
        game.play(("stop",))
    place = game.session.person_places[pid]
    if place in game.homes:
        travel(game, game.homes[place])
        if not game.player.ap:
            game.play(("end",))
        # Travel/end may have changed occupancy; look at the current world.
        if game.session.person_places[pid] != place:
            return approach(game, pid)
        game.play(("ring", place))
    else:
        travel(game, place)
        if not game.player.ap:
            game.play(("end",))
        if game.session.person_places[pid] != place:
            return approach(game, pid)
        game.play(("interrogate", int(pid[1:])))
    # The detective's look comes first; then talking costs the point.
    if ("talk",) in game.options():
        game.play(("talk",))


def discover(game, action):
    if not game.player.ap:
        game.play(("end",))
    if action.startswith(("meet:", "interview:p", "observe:p")):
        person = action.split(":", 1)[1]
        approach(game, person)
        if action.startswith(("interview:", "observe:")):
            if not game.player.ap:
                game.play(("stop",))
                game.play(("end",))
                approach(game, person)
            game.play(("ask", "observations" if action.startswith("observe:") else "evening"))
        game.play(("stop",))
    else:
        game.play(("investigate", action))


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("skills", (("fingerprints", "lockpick"), ("search", "rapport")))
def test_public_protocol_allows_a_complete_investigation(seed, skills):
    game = fresh(seed, skills)
    queries = set()
    priority = {"inspect_scene": 0, "request_exam": 1, "read_medical": 2,
                "collect_drink": 3, "analyze_drink": 4, "read_diary": 6}
    for _ in range(200):
        s = game.session
        known = dict(s.state.known)
        if len(s.remaining()) == 1 and {"medical_window", "victim_diary"} <= known.keys():
            person, = s.remaining()
            travel(game, "police")
            if not game.player.ap:
                game.play(("end",))
            game.play(("accuse", int(person[1:])))
            assert game.view(game.player)["winner"] == "Ada"
            assert game.session.finished
            return
        choices = []
        for place in s.board():
            for action in place["actions"]:
                if place["place"] in game.homes and game.occupants(place["place"]) and not action["id"].startswith(("meet:", "interview:p", "observe:p")):
                    continue
                if place["place"] in game.homes and "lockpick" not in game.session.skills and not game.home_open(place["place"]) and not action["id"].startswith(("meet:", "interview:p", "observe:p")):
                    continue
                score = priority.get(action["id"], {"interview": 5, "verify": 7, "read": 8, "collect": 9, "analyze": 10, "search": 15}.get(action["operation"], 12))
                choices.append((score, place["place"] != s.place, place["place"], action["id"]))
        window = next((s.case.claims[k]["window"] for k in known if "window" in s.case.claims.get(k, {})), None)
        if window:
            for place in s.board():
                if place["camera"]:
                    for hour in range(window[0] // 60, window[1] // 60 + 1):
                        if (place["place"], hour) not in queries:
                            choices.append((11, place["place"] != s.place, place["place"], "camera " + str(hour)))
        if not choices:
            game.play(("end",))
            continue
        _, _, place, action = min(choices)
        if action.startswith(("meet:", "interview:p", "observe:p")):
            discover(game, action)
            continue
        travel(game, "cctv" if action.startswith("camera ") else place)
        if not game.player.ap:
            game.play(("end",))
        if action.startswith("camera "):
            hour = int(action.split()[1])
            start = max(start for start in CAMERA_WINDOWS if start <= hour)
            queries.update((place, h) for h in range(start, CAMERA_WINDOWS[start][0]))
            game.play(("camera_menu",))
            game.play(("ask", "camera_district", place))
            known_before = set(dict(s.state.known))
            game.play(("ask", "camera_window", start))
            acquired = set(dict(s.state.known)) - known_before
            packet = [a for a in game.case.plan.artifacts if a.id in acquired]
            assert len(game.case.plan.population.intersection(*(a.candidates for a in packet))) >= 2
            game.play(("stop",))
        elif action in {a["id"] for a in s.options()}:
            discover(game, action)
    pytest.fail(f"Protocol exploration did not resolve seed {seed}; time={clock(s.at)}")


def test_setup_public_projection_does_not_export_future_evidence():
    game = CausalGame(7, ["Ada"])
    view = game.view(game.player)
    assert set(game.setup()["items"]) == set(ITEMS)
    assert not view["journal"] and not view["facts"]
    assert all(row["home"] is None and row["name"] == "?" for row in view["notebook"])
    assert all(q in view["places"] for row in view["grid"] for q in row if q)
    assert {"lab", "morgue", "restaurant", "promenade"} <= view["places"].keys()
    payload = json.dumps(view)
    assert not any(key in payload for key in ('"candidates"', '"tool_states"', '"claims"', '"author"', '"reveals"'))


def test_home_movement_requires_the_real_neighborhood():
    game = fresh()
    home = next(h for h, region in game.homes.items() if region != game.player.place)
    assert ("move", home) not in game.options()
    travel(game, home)
    assert game.player.place == home


def test_medical_delay_is_materialized_and_sang_is_not_duplicate():
    game = fresh()
    discover(game, "inspect_scene")
    discover(game, "request_exam")
    travel(game, "morgue")
    view = game.view(game.player)
    assert any(p["id"] == "staff:medical" for p in view["staff"])
    assert "tour" in game.service_status("staff:medical")
    assert ("investigate", "read_medical") not in game.options()
    while ("investigate", "read_medical") not in game.options():
        game.play(("end",))
    discover(game, "read_medical")
    assert "medical_window" in dict(game.session.state.known)
    assert ("investigate", "read_medical") not in game.options()


@pytest.mark.parametrize("place", ("morgue", "lab"))
def test_no_waiting_button_without_a_real_pending_operation(place):
    game = fresh()
    travel(game, place)
    if not game.player.ap:
        game.play(("end",))
    assert not any(key[0] == "wait" for key in game.options())
    assert not any(f["id"] == "clock" for f in game.view(game.player)["fixtures"])


def test_pending_report_status_does_not_advance_time_or_spend_ap():
    game = fresh()
    discover(game, "inspect_scene")
    discover(game, "request_exam")
    travel(game, "morgue")
    if not game.player.ap:
        game.play(("end",))
    assert not any(key[0] == "wait" for key in game.options())
    before = game.player.ap, game.session.at, game.tick, list(game.session.journal)
    game.play(("service_menu", "staff:medical"))
    assert game.cue["stage"] == "greeting" and not game.cue["text"]
    game.play(("ask", "service_status"))
    assert "tour" in game.cue["text"] and "médecin légiste" in game.cue["text"]
    assert (game.player.ap, game.session.at, game.tick, game.session.journal) == before
    game.play(("stop",))
    for _ in range(4):
        if ("investigate", "read_medical") in game.options():
            break
        game.play(("end",))
    assert ("investigate", "read_medical") in game.options()
    assert not any(key[0] == "wait" for key in game.options())
    discover(game, "read_medical")
    assert not any(f["id"] in ("clock", "exam_wait") for f in game.view(game.player)["fixtures"])


@pytest.mark.parametrize("place,actor", (("morgue", "staff:medical"), ("lab", "staff:lab")))
def test_service_menu_without_request_explains_why_without_empty_greeting(place, actor):
    game = fresh()
    travel(game, place)
    game.play(("service_menu", actor))
    assert ("ask", "service_status") in game.options()
    game.play(("ask", "service_status"))
    assert "examiner le corps" in game.cue["text"] if place == "morgue" else "aucun résultat" in game.cue["text"]
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.view(restored.player) == game.view(game.player)


def test_server_only_reveals_stock_after_a_question():
    game = fresh()
    row = next(a for a in game.case.plan.actions if a.operation.value == "ask_stock")
    travel(game, row.place)
    if not game.player.ap:
        game.play(("end",))
    before = len(game.session.journal)
    game.play(("service_menu", row.actor))
    assert not game.cue["text"] and len(game.session.journal) == before
    assert ("ask", "service_action", row.id) in game.options()
    game.play(("ask", "service_action", row.id))
    assert len(game.session.journal) > before
    assert game.cue["person"]["id"] == row.actor and game.cue["question"]
    game.play(("stop",))
    assert game.cue is None and game.speaker is None


def test_fixture_actions_are_physical_and_remain_at_zero_ap():
    game = seed_where(lambda g: g.case.crime.scene in g.outdoors and any(c.place == g.case.crime.scene and c.online for c in g.case.evidence.cameras))  # a street crime with a live camera
    view = game.view(game.player)
    assert any(f["prop"] == "body" for f in view["fixtures"])
    assert any(f["prop"] == "trash" for f in view["fixtures"])
    game.player.ap = 0
    assert all(key[0] in ("end", "service_menu") for key in game.options())
    view = game.view(game.player)
    assert view["fixtures"] and all(not f["actions"] for f in view["fixtures"])
    assert game.tick == 0
    game.play(("end",))
    assert game.player.ap == 6 and game.tick == 1


def test_camera_requires_scene_and_offers_only_four_direct_windows():
    game = seed_where(lambda g: g.case.crime.scene in g.outdoors and any(c.place == g.case.crime.scene and c.online for c in g.case.evidence.cameras))  # a street crime with a live camera
    assert ("camera_menu",) not in game.options()
    discover(game, "inspect_scene")
    source = game.player.place
    assert ("camera_menu",) not in game.options()
    travel(game, "cctv")
    if not game.player.ap:
        game.play(("end",))
    game.play(("camera_menu",))
    assert len(game.options()) == 5
    game.play(("ask", "camera_district", source))
    assert len(game.options()) == 7  # four windows of yesterday, the previous days, back, close
    assert len([k for k in game.options() if k[:2] == ("ask", "camera_window")]) == 4
    assert not any(k[1:2] in (("camera_hour",), ("camera_block",)) for k in game.options())
    before = game.player.ap, game.session.at
    game.play(("ask", "camera_window", 18))
    assert game.player.ap == before[0] - 1 and game.session.at == before[1] + 5
    assert any(r["kind"] == "footage" for r in game.session.journal)
    assert game.player.place == "cctv"
    game.play(("ask", "camera_window", 18))
    assert game.player.ap == before[0] - 1 and game.session.at == before[1] + 5
    assert game.view(game.player)["pending"] == "terminal vidéo"
    game.play(("stop",))
    assert game.view(game.player)["pending"] is None


def test_searched_bin_keeps_its_mesh_without_an_interaction():
    game = seed_where(lambda g: g.case.crime.scene in g.outdoors and any(c.place == g.case.crime.scene and c.online for c in g.case.evidence.cameras))  # a street crime with a live camera
    before = game.view(game.player)
    bin_before = next(f for f in before["fixtures"] if f["prop"] == "trash")
    assert bin_before["selectable"] and bin_before["actions"]
    discover(game, "search_bin:" + game.player.place)
    after = game.view(game.player)
    bin_after = next(f for f in after["fixtures"] if f["prop"] == "trash")
    assert bin_after["id"] == bin_before["id"]
    assert not bin_after["selectable"] and not bin_after["actions"]
    assert [f["id"] for f in before["fixtures"]].index(bin_before["id"]) == [f["id"] for f in after["fixtures"]].index(bin_after["id"])


def physical_fixtures(game):
    """Appearance/position contract, deliberately excluding changing actions."""
    return {f["id"]: {k: v for k, v in f.items() if k not in ("actions", "selectable", "reason")}
            for f in game.view(game.player)["fixtures"]}


@pytest.mark.parametrize("seed", (7, 5, 0, 1))
def test_crime_scene_objects_stay_identical_until_explicit_body_transfer(seed):
    game = fresh(seed, ("fingerprints", "search"))
    scene = game.player.place
    before = physical_fixtures(game)
    assert before["fixture:crime_scene"]["prop"] == "body"
    assert before["objects"]["prop"] == "kit"
    discover(game, "inspect_scene")
    assert physical_fixtures(game) == before
    for action in ("collect_blood", "collect_drink", "collect_object", "search_bin:" + scene):
        if ("investigate", action) in game.options():
            discover(game, action)
            assert physical_fixtures(game) == before
    if not game.player.ap:
        game.play(("end",))
    discover(game, "request_exam")
    assert "transféré à la morgue" in game.cue["text"]
    survivors = {k: v for k, v in before.items() if k != "fixture:crime_scene"}
    assert physical_fixtures(game) == survivors
    assert game.view(game.player)["body_location"] == "morgue"
    # Removing the first fixture never renumbers/moves the remaining objects.
    assert all(f["slot"] == before[key]["slot"] for key, f in survivors.items())
    saved_ap = game.player.ap
    game.player.ap = 0
    assert physical_fixtures(game) == survivors
    assert all(not f["selectable"] for f in game.view(game.player)["fixtures"])
    game.player.ap = saved_ap
    travel(game, "morgue")
    table = physical_fixtures(game)["fixture:exam_table"]
    assert table["body_present"]
    while ("investigate", "read_medical") not in game.options():
        game.play(("end",))
    discover(game, "read_medical")
    assert physical_fixtures(game)["fixture:exam_table"] == table
    travel(game, scene)
    assert physical_fixtures(game) == survivors
    restored = CausalGame.restore(seed, "Ada", game.snapshot(), True)
    assert restored.view(restored.player) == game.view(game.player)


def test_medical_request_at_hospital_moves_only_body_not_other_scene_props():
    game = fresh()
    scene = game.player.place
    before = physical_fixtures(game)
    discover(game, "inspect_scene")
    travel(game, "morgue")
    empty = physical_fixtures(game)["fixture:exam_table"]
    assert not empty["body_present"]
    discover(game, "request_exam_morgue")
    occupied = physical_fixtures(game)["fixture:exam_table"]
    assert occupied == dict(empty, body_present=True)
    travel(game, scene)
    assert physical_fixtures(game) == {k: v for k, v in before.items() if k != "fixture:crime_scene"}


def test_home_furniture_stays_after_documents_photos_and_search_are_consumed():
    game = fresh(7, ("lockpick", "search"))
    discover(game, "inspect_scene")
    home = game.case.life.people[game.case.crime.kernel.roles.victim].home
    travel(game, home)
    before = physical_fixtures(game)
    completed = []
    for row in game.case.plan.actions:
        if row.place != home or row.actor not in before:
            continue
        if not game.player.ap:
            game.play(("end",))
        if ("investigate", row.id) in game.options():
            discover(game, row.id)
            completed.append(row.id)
            assert physical_fixtures(game) == before
    assert "read_diary" in completed
    assert len(completed) >= 2
    # Only the print kit may still offer something: anyone may try to lift a print on what was found.
    assert all(not f["selectable"] or f["id"] == "objects" for f in game.view(game.player)["fixtures"])


@pytest.mark.parametrize("place", ("alley", "crime_scene", "victim_street", "promenade", "cctv"))
def test_video_reader_exists_only_at_the_control_room(place):
    game = fresh()
    discover(game, "inspect_scene")
    travel(game, place)
    if not game.player.ap:
        game.play(("end",))
    view = game.view(game.player)
    assert any(f["id"] == "camera" for f in view["fixtures"]) == (place == "cctv")
    assert (("camera_menu",) in game.options()) == (place == "cctv")


def test_pending_central_reader_replays_exactly():
    game = seed_where(lambda g: g.case.crime.scene in g.outdoors and any(c.place == g.case.crime.scene and c.online for c in g.case.evidence.cameras))  # a street crime with a live camera
    source = game.player.place
    discover(game, "inspect_scene")
    travel(game, "cctv")
    game.play(("camera_menu",))
    game.play(("ask", "camera_district", source))
    game.play(("ask", "camera_window", 18))
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.view(restored.player) == game.view(game.player)


def test_broad_window_reuses_old_hour_recordings_without_false_empty_answer():
    game = fresh()
    discover(game, "inspect_scene")
    clip = game.case.evidence.clips[0]
    start = max(h for h in CAMERA_WINDOWS if h <= clip.minute // 60)
    end = CAMERA_WINDOWS[start][0]
    for hour in sorted({c.minute // 60 for c in game.case.evidence.clips if c.place == clip.place and start <= c.minute // 60 < end}):
        game.session.camera(hour, place=clip.place)
    before_time = game.session.at
    text, paid = game.session.camera_window(start, end, place=clip.place)
    assert "Hier" in text and "Rien d'exploitable" not in text
    assert not paid and game.session.at == before_time


def test_v14_street_camera_history_is_preserved_and_pending_reader_closed():
    game = seed_where(lambda g: g.case.crime.scene in g.outdoors and any(c.place == g.case.crime.scene and c.online for c in g.case.evidence.cameras))  # a street crime with a live camera
    discover(game, "inspect_scene")
    game._legacy_camera_replay = True
    game.play(("camera_menu",))
    game._legacy_camera_replay = False
    game._legacy_camera_controls = True
    game.play(("ask", "camera_block", 18))
    game.play(("ask", "camera_hour", 18))
    game._legacy_camera_controls = False
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.session.journal == game.session.journal
    assert restored.player.ap == game.player.ap
    assert restored.session.at == game.session.at
    assert restored.player.place == game.player.place
    assert restored.speaker is None and restored.cue is None
    assert ("camera_menu",) not in restored.options()
    travel(restored, "cctv")
    again = CausalGame.restore(game.seed, "Ada", restored.snapshot(), True)
    assert again.view(again.player) == restored.view(restored.player)


@pytest.mark.parametrize("seed", range(8))
def test_every_suspect_has_the_same_menu_and_question_costs(seed):
    game = fresh(seed)
    menu = None
    for pid in sorted(game.case.plan.population):
        approach(game, pid)
        game.play(("stop",))
        game.play(("end",))
        approach(game, pid)
        current = {k: label for k, label in game.options().items() if k[0] == "ask"}
        assert set(k[1] for k in current) == {"relation", "work", "circle", "motive", "observations", "evening"}
        assert list(current)[:4] == [("ask", topic) for topic in ("relation", "evening", "observations", "motive")]
        assert ("ask", "messages") not in game.options()
        if menu is None:
            menu = current
        assert current == menu
        for topic in ("motive", "observations", "evening"):
            # Opening the conversation paid for a batch: a fresh question takes a slot,
            # never a point; a repeat takes nothing at all.
            before, slots = game.player.ap, game.slots
            game.play(("ask", topic))
            assert game.player.ap == before and game.slots == slots - 1
            game.play(("ask", topic))
            assert game.player.ap == before and game.slots == slots - 1
        after = {k: label.split(" (", 1)[0].removesuffix(" · Reposer gratuitement").removesuffix(" ⚡")
                 for k, label in game.options(True).items() if k[0] == "ask"}
        assert after == {k: label.split(" (", 1)[0] for k, label in menu.items()}
        game.play(("stop",))


@pytest.mark.parametrize("place,actor", (("bar", "staff:bar"), ("restaurant", "staff:restaurant"), ("police", "staff:police")))
def test_role_contacts_do_not_offer_empty_add_something_question(place, actor):
    game = fresh()
    discover(game, "inspect_scene")
    travel(game, place)
    if not game.player.ap:
        game.play(("end",))
    game.play(("service_menu", actor))
    assert ("ask", "service_status") not in game.options()
    assert all("quelque chose à ajouter" not in text for text in game.options().values())
    action = next(key for key in game.options() if key[:2] == ("ask", "service_action"))
    game.play(action)
    assert ("ask", "service_status") not in game.options()


def test_former_empty_service_question_replays_but_is_never_available_live():
    game = fresh()
    discover(game, "inspect_scene")
    travel(game, "bar")
    game.play(("service_menu", "staff:bar"))
    saved = game.snapshot()
    saved["history"] = saved["history"] + [["ask", "service_status"]]
    restored = CausalGame.restore(game.seed, "Ada", saved, True)
    assert restored.snapshot() == saved
    assert restored.cue["question"] == "Vous avez quelque chose à ajouter ?"
    assert ("ask", "service_status") not in restored.options()
    with pytest.raises(ValueError, match="pas disponible"):
        restored.play(("ask", "service_status"))


@pytest.mark.parametrize("topic", ("relation", "work", "circle", "evening", "motive", "observations"))
def test_all_suspect_questions_cost_one_pa_once_and_repeat_free_at_zero(topic):
    game = fresh()
    discover(game, "inspect_scene")
    approach(game, sorted(game.case.plan.population)[0])
    game.player.ap, game.slots = 0, 1  # last slot of the batch, no point left
    key = ("ask", topic)
    assert game.question_cost(key) == 0
    game.play(key)
    assert game.player.ap == 0 and game.slots == 0 and game.question_cost(key) == 0
    first = game.cue["text"]
    before = game.session.at, list(game.session.journal), game.tick
    for _ in range(2):
        game.play(key)
        assert game.cue["text"] == first and game.player.ap == 0
        assert (game.session.at, game.session.journal, game.tick) == before
    # Past the budget with no point left, a fresh question is still offered: the dial decides.
    other = next(("ask", t) for t in ("relation", "work", "circle") if t != topic)
    assert game.options()[other].endswith("⚡")
    presentation = {tuple(row[0]): row[2] for row in game.view(game.player)["dialogue_options"]}
    assert presentation[key] == {"cost": 0, "available": True}
    assert presentation[other] == {"cost": 1, "available": True}
    game.challenge = lambda kind, difficulty: 0.0  # a bad hand buys nothing
    game.play(other)
    assert game.cue["text"].startswith("Plus de PA")
    assert game.player.ap == 0 and (game.session.at, game.session.journal, game.tick) == before


def test_questions_about_each_other_person_are_individually_paid_and_repeatable():
    game = fresh()
    discover(game, "inspect_scene")
    a, b, c = sorted(int(pid[1:]) for pid in game.case.plan.population)[:3]
    approach(game, "p%d" % a)
    key = ("talk_about", a, b)
    game.player.ap, game.slots = 0, 1
    game.play(key)
    assert game.player.ap == 0 and game.slots == 0
    first, at, journal = game.cue["text"], game.session.at, list(game.session.journal)
    game.play(key)
    assert (game.cue["text"], game.session.at, game.session.journal) == (first, at, journal)
    assert game.options()[("talk_about", a, c)].endswith("⚡")  # past the budget: the dial
    game.play(("stop",))
    # Already met suspect: with no point left, you may look but not talk.
    home = game.session.person_places["p%d" % a]
    game.play(("ring", home) if home in game.homes else ("interrogate", a))
    assert game.player.ap == 0 and game.options() == {("stop",): "Quitter"}
    game.player.ap = 1
    game.play(("talk",))
    assert game.player.ap == 0 and key in game.options() and game.question_cost(key) == 0


def test_service_answers_are_repeatable_free_without_duplicate_notes_or_analysis():
    game = fresh()
    discover(game, "inspect_scene")
    travel(game, "police")
    game.play(("service_menu", "staff:police"))
    game.player.ap = 1
    key = ("ask", "service_action", "record:" + sorted(game.case.plan.population)[0])
    game.play(key)
    first, at, journal = game.cue["text"], game.session.at, list(game.session.journal)
    assert game.player.ap == 0
    game.play(key)
    assert game.player.ap == 0
    assert (game.cue["text"], game.session.at, game.session.journal) == (first, at, journal)
    disabled = ("ask", "service_action", "record:p2")
    assert disabled not in game.options()
    assert any(row[0] == list(disabled) and not row[2]["available"] for row in game.view(game.player)["dialogue_options"])


def test_legacy_free_biography_history_keeps_old_pa_then_new_questions_are_paid():
    game = fresh()
    discover(game, "inspect_scene")
    approach(game, sorted(game.case.plan.population)[0])
    before = game.player.ap
    game._legacy_question_replay = True
    game.play(("ask", "relation"))
    game._legacy_question_replay = False
    saved = game.snapshot()
    saved.pop("priced_from")
    restored = CausalGame.restore(game.seed, "Ada", saved, True)
    assert restored.player.ap == before
    assert restored.session.journal == game.session.journal
    assert restored.priced_from == len(saved["history"])
    slots = restored.slots
    restored.play(("ask", "work"))  # a fresh question within the batch takes a slot, not a point
    assert restored.player.ap == before and restored.slots == slots - 1
    restored.play(("ask", "work"))
    assert restored.player.ap == before and restored.slots == slots - 1
    again = CausalGame.restore(game.seed, "Ada", restored.snapshot(), True)
    assert again.view(again.player) == restored.view(restored.player)


def test_evening_account_opens_a_public_witness_lead_without_self_certifying_an_alibi():
    game = fresh(7)
    presence = game.case.evidence.presences[0]
    pid = presence.person
    approach(game, pid)
    before = game.session.remaining()
    game.play(("ask", "evening"))
    assert "Je n'ai rien" not in game.cue["text"]
    assert game.session.remaining() == before
    view = game.view(game.player)
    note = next(n for n in view["notebook"] if n["id"] == int(pid[1:]))
    assert note["claim"] and note["alibi"] == "à vérifier"
    lead = next(r for r in view["leads"] if r["id"] == "evening:" + pid)
    assert not lead["complete"] and "vérifier ce récit" in lead["reason"]
    target = lead["destinations"][0]["place"]
    assert target not in game.homes
    game.play(("stop",))
    travel(game, target)
    if not game.player.ap:
        game.play(("end",))
    view = game.view(game.player)
    witness = next(p for p in view["staff"] if p["id"] == presence.witness)
    assert witness["name"] in lead["reason"]
    assert all(p["id"] != presence.witness for p in view["presence"]["places"][target]["people"])
    game.play(("service_menu", presence.witness))
    assert not game.cue["text"]
    game.play(("ask", "service_action", "verify:" + pid))
    assert "alibi:" + pid in dict(game.session.state.known)
    assert game.session.remaining() == before  # Need the medical window as well.
    awaiting = next(r for r in game.view(game.player)["leads"] if r["id"] == "evening:" + pid)
    assert awaiting["complete"] and awaiting["state"] == "corroborated" and "rapport médical" in awaiting["reason"]
    assert next(r for r in game.view(game.player)["notebook"] if r["id"] == int(pid[1:]))["alibi"] == "corroboré"
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.view(restored.player) == game.view(game.player)


@pytest.mark.parametrize("venue,actor", (("bar", "staff:bar"), ("restaurant", "staff:restaurant"), ("police", "staff:police")))
def test_public_staff_exist_even_without_an_inventory_incident(venue, actor):
    game = fresh(7)
    travel(game, venue)
    view = game.view(game.player)
    assert any(p["id"] == actor for p in view["staff"])
    assert ("service_menu", actor) in game.options()
    assert all(p["id"] != actor for p in view["presence"]["places"][venue]["people"])
    game.play(("service_menu", actor))
    assert not game.cue["text"]
    if not game.player.ap:
        game.play(("stop",))
        game.play(("end",))
        game.play(("service_menu", actor))
    assert any(key[:2] == ("ask", "service_action") for key in game.options())


def test_diary_appointment_can_be_asked_of_every_suspect_without_a_menu_tell():
    from scenario_witnesses import EventKind, scene_events
    game = seed_where(lambda g: g.case.crime.victim_plan.appointment is not None
                      and any(e.kind is EventKind.NONARRIVAL for e in scene_events(g.case.crime)))
    appointment = game.case.crime.victim_plan.appointment
    victim = game.case.life.people[game.case.crime.kernel.roles.victim]
    travel(game, victim.home)
    discover(game, "read_diary")
    for pid in sorted(game.case.plan.population):
        approach(game, pid)
        assert ("ask", "appointment") in game.options(True)
        if not game.player.ap:
            game.play(("stop",))
            game.play(("end",))
            approach(game, pid)
        before = game.session.remaining()
        before_ap = game.player.ap
        game.play(("ask", "appointment"))
        assert game.player.ap == before_ap  # within the batch the conversation already paid
        at = game.session.at
        game.play(("ask", "appointment"))
        assert game.player.ap == before_ap and game.session.at == at
        assert game.session.remaining() == before
        if pid == appointment.host:
            assert "rendez-vous" in game.cue["text"] and clock(appointment.starts_at) in game.cue["text"]
            assert "J'ai attendu, mais personne n'est venu" in game.cue["text"]
        else:
            assert "ne me dit rien" in game.cue["text"]
        game.play(("stop",))


@pytest.mark.parametrize("label,expected", (("Le Comptoir", "au Comptoir"),
    ("Le serveur", "au serveur"), ("La Morgue", "à la Morgue"),
    ("Les Appartements", "aux Appartements"), ("L'Hôpital", "à l’Hôpital"),
    ("Place des Enseignes", "à Place des Enseignes")))
def test_lead_location_articles(label, expected):
    assert at_label(label) == expected


def test_glass_trail_is_acquired_not_a_preview_and_closes_after_analysis():
    game = seed_where(lambda g: g.case.crime.method.value == "poisoned")
    assert not any(r["id"] == "drink_analysis" for r in game.view(game.player)["leads"])
    discover(game, "inspect_scene")
    assert not any(r["id"] == "drink_analysis" for r in game.view(game.player)["leads"])
    discover(game, "collect_drink")
    lead = next(r for r in game.view(game.player)["leads"] if r["id"] == "drink_analysis")
    assert not lead["complete"] and lead["destinations"][0]["place"] == "lab"
    assert "tour" in lead["reason"] and "technicienne" in lead["objective"]
    assert "substance" not in lead["reason"]  # No result before it is learned.
    travel(game, "lab")
    while "analyze_drink" not in {r["id"] for r in game.session.options()}:
        game.play(("end",))
    discover(game, "analyze_drink")
    lead = next(r for r in game.view(game.player)["leads"] if r["id"] == "drink_analysis")
    assert lead["complete"] and lead["destinations"] == []
    assert lead["reason"] == next(r["text"] for r in game.session.journal if r["id"] == "drink_result")


def test_police_records_reveal_real_appearance_not_a_guilt_filter():
    game = fresh(7)
    travel(game, "police")
    if not game.player.ap:
        game.play(("end",))
    pid = sorted(game.case.plan.population)[0]
    game.play(("service_menu", "staff:police"))
    before = game.session.remaining()
    game.play(("ask", "service_action", "record:" + pid))
    assert "Cheveux" in game.cue["text"] and "Fiche" in game.cue["text"]
    assert game.session.remaining() == before
    appearance = next(a for a in game.case.evidence.appearances if a.person == pid)
    note = next(n for n in game.view(game.player)["notebook"] if n["id"] == int(pid[1:]))
    assert note["traits"]["Cheveux"] == appearance.hair.value
    assert note["appearance"]["hair"] == appearance.hair.value
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.view(restored.player) == game.view(game.player)


def test_contextual_answers_use_existing_facts_and_do_not_exclude_anyone():
    game = fresh()
    pid = next(iter(sorted(game.case.plan.population)))
    approach(game, pid)
    remaining = game.session.remaining()
    for topic in ("work", "circle"):
        game.play(("ask", topic))
        assert game.case.life.answer(pid, topic) in game.cue["text"]
        assert game.session.remaining() == remaining
    before = len(game.session.journal)
    game.play(("ask", "work"))
    assert len(game.session.journal) == before


def test_remote_clip_and_empty_hour_acquire_from_the_right_street():
    game = seed_where(lambda g: g.case.evidence.clips and g.case.evidence.clips[0].minute >= 18 * 60
                      and not any(c.place == g.case.evidence.clips[0].place and c.minute < 18 * 60 for c in g.case.evidence.clips))
    discover(game, "inspect_scene")
    travel(game, "cctv")
    clip = game.case.evidence.clips[0]
    game.play(("camera_menu",))
    game.play(("ask", "camera_district", clip.place))
    start = max(h for h in CAMERA_WINDOWS if h <= clip.minute // 60)
    game.play(("ask", "camera_window", start))
    assert game.player.place == "cctv"
    assert f"camera:{clip.place}:{clip.minute // 60}" in game.session.state.completed
    game.play(("ask", "camera_window", 0))
    assert any(r["id"] == f"empty_window:{clip.place}:0" for r in game.session.journal)
    assert game.player.place == "cctv"


def test_replay_restores_exact_public_view_and_pending_dialogue():
    game = fresh()
    discover(game, "inspect_scene")
    approach(game, sorted(game.case.plan.population)[0])
    restored = CausalGame.restore(game.seed, "Ada", json.loads(json.dumps(game.snapshot())), True)
    assert restored.view(restored.player) == game.view(game.player)


def test_doorstep_is_not_an_apartment_entry_or_an_automatic_relation_answer():
    game = fresh()
    pid = next(pid for pid, place in game.session.person_places.items() if place in game.homes)
    home = game.case.life.people[pid].home
    travel(game, game.homes[home])
    assert ("move", home) not in game.options()
    assert ("unlock_home", home) not in game.options()
    with pytest.raises(ValueError):
        game.play(("move", home))
    street = game.session.place
    game.play(("ring", home))
    assert game.session.place == street and game.session.doorstep == home
    assert game.cue["stage"] == "approach" and game.cue["text"].startswith("Le suspect") and game.cue["question"] is None
    game.play(("talk",))
    assert game.cue["stage"] == "greeting" and game.cue["text"] == ""
    assert not any("connaiss" in r["text"] for r in game.session.journal)
    door = next(d for d in game.view(game.player)["doors"] if d["place"] == home)
    assert door["answered"] and len(door["people"]) == 1
    assert game.view(game.player)["present"] == []
    game.play(("ask", "relation"))
    assert game.cue["text"] == game.case.life.answer(pid)
    game.play(("stop",))
    assert game.session.doorstep is None
    assert not next(d for d in game.view(game.player)["doors"] if d["place"] == home)["people"]


def test_lockpick_only_opens_an_empty_private_home_and_costs_a_skill_slot():
    game = fresh()
    home = next(h for h in game.homes if not game.occupants(h) and not game.home_open(h))
    travel(game, game.homes[home])
    before = game.player.ap
    assert ("move", home) not in game.options()
    game.play(("unlock_home", home))
    assert game.player.ap == before - 1 and game.session.place == home  # one action, you are inside
    assert not game.view(game.player)["present"]
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.unlocked_homes == game.unlocked_homes
    assert restored.view(restored.player) == game.view(game.player)
    without = fresh(skills=("fingerprints", "search"))
    travel(without, without.homes[home])
    assert "⚡" in without.options()[("unlock_home", home)]  # offered to all, the dial decides without the skill


def test_next_day_positions_change_only_at_manual_turn_boundary():
    game = fresh()
    before = dict(game.session.person_places)
    game.session.at = 1440 + 12 * 60
    assert game.session.person_places == before
    game.play(("end",))
    assert game.session.person_places != before
    for pid, place in game.session.person_places.items():
        assert place == next(r.place_at(game.session.at) for r in game.routines if r.person == pid)


def test_known_people_have_current_and_next_turn_positions_without_unknown_leaks():
    game = fresh()
    assert all(row["whereabouts"] is None for row in game.view(game.player)["notebook"])
    pid = sorted(game.case.plan.population)[0]
    approach(game, pid)
    row = next(r for r in game.view(game.player)["notebook"] if r["id"] == int(pid[1:]))
    assert row["whereabouts"]["current"]["place"] == game.session.person_places[pid]
    promised = row["whereabouts"]["next"]["place"]
    game.play(("stop",))
    game.play(("end",))
    assert game.session.person_places[pid] == promised


def test_daily_life_has_lunch_dinner_drinks_and_real_travel_without_guilt_input():
    game = fresh()
    for routine in game.routines:
        assert routine.stops[0].start == 0 and routine.stops[-1].end == 1440
        assert all(a.end == b.start for a, b in zip(routine.stops, routine.stops[1:]))
        assert all(s.start < s.end for s in routine.stops)
        assert any(s.activity == "déjeune" and s.place in ("bar", "restaurant") for s in routine.stops)
        assert routine.place_at(0) == routine.home
        assert routine.place_at(1439) == routine.home
        for a, b in zip(routine.stops, routine.stops[1:]):
            assert a.place == b.place or b.place in dict(game.case.crime.streets.neighbors(a.place))
    assert any(s.activity == "dîne" for r in game.routines for s in r.stops)
    assert any(s.activity == "prend un verre" for r in game.routines for s in r.stops)


def test_unknown_victim_answers_do_not_imply_previous_contact():
    game = fresh()
    victim = game.case.crime.kernel.roles.victim
    for pid in game.case.plan.population:
        if not game.case.life.knows(pid, victim):
            assert game.case.life.answer(pid) == "Je ne connaissais pas la victime. " + game.case.life.people[victim].name + ", vous dites ?"
            assert game.case.life.answer(pid, "messages") == "Non, aucun échange avec cette personne."


def test_morgue_is_a_custom_hospital_entrance_not_a_palace_neighbor():
    game = fresh()
    assert "morgue" not in game.roots
    assert game.view(game.player)["places"]["morgue"]["street"] == "hospital"
    assert ("move", "morgue") not in game.options()
    travel(game, "hospital")
    assert ("move", "morgue") in game.options()
    game.play(("move", "morgue"))
    assert game.view(game.player)["region"] == "hospital"


def test_staff_remain_interactive_but_only_suspects_count_as_present():
    game = fresh()
    travel(game, "morgue")
    view = game.view(game.player)
    assert any(p["id"] == "staff:medical" for p in view["staff"])
    assert view["presence"]["places"]["morgue"]["count"] == 0
    ids = {int(pid[1:]) for pid in game.case.plan.population}
    for scope in ("districts", "places"):
        assert sum(v["count"] for v in view["presence"][scope].values()) == len(ids)
        assert {p["id"] for v in view["presence"][scope].values() for p in v["people"]} == ids
        assert all(v["scope"] == "suspects" for v in view["presence"][scope].values())


def test_solo_causal_json_roundtrip_and_invalid_action_rollback(tmp_path):
    path = tmp_path / "causal.json"
    session = SoloSession(path, 7, engine="causal")
    try:
        initial = receive(session)
        session.send(json.dumps({"type": "equip", "items": ["fingerprints", "search"], "start": initial["setup"]["default_start"]}))
        receive(session)
        session.send(json.dumps({"type": "play", "key": ["investigate", "inspect_scene"]}))
        view = receive(session)
        session.send(json.dumps({"type": "play", "key": ["investigate", "not-an-action"]}))
        assert "disponible" in receive(session, "error")["message"]
        unchanged = receive(session)
        assert unchanged["journal"] == view["journal"]
        assert unchanged["ap"] == view["ap"]
    finally:
        session.close()
        session.worker.join(3)
    resumed = SoloSession(path, 999, engine="causal")
    try:
        restored = receive(resumed)
        assert restored["solo"]["resumed"]
        assert restored["solo"]["seed"] == 7
        assert restored["journal"] == view["journal"]
    finally:
        resumed.close()
        resumed.worker.join(3)


def test_cited_suspect_is_named_without_disclosing_a_physical_profile():
    game = fresh()
    assert not game.session.named_people()
    speaker, target = sorted(game.case.plan.population)[:2]
    approach(game, speaker)
    before = game.session.remaining()
    game.play(("talk_about", int(speaker[1:]), int(target[1:])))
    view = game.view(game.player)
    card = next(r for r in view["notebook"] if r["id"] == int(target[1:]))
    assert card["name"] == game.case.life.people[target].name
    assert card["profile_known"] is False
    assert card["appearance"] == card["traits"] == {}
    assert card["home"] is None and card["whereabouts"] is not None
    assert card["whereabouts"]["current"]["place"] == game.session.person_places[target]
    assert "profile:" + target not in dict(game.session.state.known)
    assert game.session.remaining() == before
    assert len(view["notebook"]) == 7
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.view(restored.player)["notebook"] == view["notebook"]


def test_named_matching_ignores_unrevealed_sources_and_partial_names():
    game = fresh()
    pid = sorted(game.case.plan.population)[0]
    name = game.case.life.people[pid].name
    assert not game.session.named_people()
    game.session.journal.append({"id": "test:note", "kind": "conversation", "text": name + "ville"})
    assert pid not in game.session.named_people()
    game.session.journal[-1]["text"] = "« " + name + ", vous dites ? »"
    assert game.session.named_people() == {pid}


def test_corroboration_uses_existing_service_staff_not_named_extras():
    # p1 is vouched for by the other venue's staff, not the barman met first.
    game = seed_where(lambda g: any(p.person == "p1" and p.witness == "staff:restaurant" for p in g.case.evidence.presences))
    assert game.view(game.player)["contacts"] == []
    travel(game, "bar")
    game.play(("service_menu", "staff:bar"))
    view = game.view(game.player)
    contact = next(r for r in view["contacts"] if r["id"] == "staff:bar")
    assert contact["role"] == "Personnel" and contact["met"]
    assert view["conversation"]["context"] == "Personnel · Source d'information"
    assert view["conversation"]["person"]["placement"] == "bar_staff"
    assert len(view["notebook"]) == 7
    game.play(("stop",))
    approach(game, "p1")
    if not game.player.ap:
        game.play(("stop",))
        game.play(("end",))
        approach(game, "p1")
    game.play(("ask", "evening"))
    presence = next(p for p in game.case.evidence.presences if p.person == "p1")
    witness = next(r for r in game.view(game.player)["contacts"] if r["id"] == presence.witness)
    assert witness["id"] in ("staff:bar", "staff:restaurant") and witness["role"] == "Personnel"
    assert not witness["met"]
    assert witness["name"] not in {r["name"] for r in game.view(game.player)["notebook"]}
    game.play(("stop",))
    travel(game, witness["place"])
    if not game.player.ap:
        game.play(("end",))
    game.play(("service_menu", witness["id"]))
    view = game.view(game.player)
    assert view["conversation"]["person"]["role"] == "Personnel"
    assert view["conversation"]["person"]["placement"] in ("bar_staff", "restaurant_staff")
    assert next(r for r in view["contacts"] if r["id"] == witness["id"])["met"]
    assert len(view["notebook"]) == 7


def test_solo_case_identity_survives_resume_but_not_restart(tmp_path):
    path = tmp_path / "identity.json"
    session = SoloSession(path, 7, engine="causal")
    try:
        initial = receive(session)
        identity = initial["solo"]["case_id"]
        session.send(json.dumps({"type": "equip", "items": ["search", "rapport"], "start": initial["setup"]["default_start"]}))
        assert receive(session)["solo"]["case_id"] == identity
    finally:
        session.close()
        session.worker.join(3)
    # A v16 save lacks this additive identity; its investigation still resumes.
    data = json.loads(path.read_text())
    data.pop("case_id")
    path.write_text(json.dumps(data))
    resumed = SoloSession(path, 999, engine="causal")
    try:
        view = receive(resumed)
        assert view["solo"]["resumed"] and view["solo"]["seed"] == 7
        upgraded = view["solo"]["case_id"]
        assert json.loads(path.read_text())["case_id"] == upgraded
    finally:
        resumed.close()
        resumed.worker.join(3)
    resumed = SoloSession(path, 999, engine="causal")
    try:
        assert receive(resumed)["solo"]["case_id"] == upgraded
        resumed.send('{"type":"restart"}')
        new = receive(resumed)
        assert "setup" in new and new["solo"]["case_id"] != upgraded
    finally:
        resumed.close()
        resumed.worker.join(3)


def test_morgue_dates_the_crime_reliably_and_repeats_without_cost():
    game = fresh(7)
    assert game.view(game.player)["crime_timing"]["state"] == "unrequested"
    assert game.view(game.player)["timeline"] == []
    discover(game, "inspect_scene")
    travel(game, "morgue")
    if not game.player.ap:
        game.play(("end",))
    game.play(("service_menu", "staff:medical"))
    assert ("ask", "service_action", "request_exam_morgue") in game.options()
    game.play(("ask", "service_action", "request_exam_morgue"))
    timing = game.view(game.player)["crime_timing"]
    assert timing["state"] == "pending" and 0 < timing["turns"] <= 4
    assert "start" not in timing  # No private estimate before receiving the report.
    game.play(("stop",))
    while ("investigate", "read_medical") not in game.options():
        game.play(("end",))
    discover(game, "read_medical")
    view = game.view(game.player)
    start, end = game.case.claims["medical_window"]["window"]
    assert view["crime_timing"]["state"] == "known"
    assert (view["crime_timing"]["start"], view["crime_timing"]["end"]) == (start, end)
    assert any(r["id"] == "medical_window" for r in view["timeline"])
    assert next(r for r in view["leads"] if r["id"] == "medical")["complete"]
    game.play(("service_menu", "staff:medical"))
    before = (game.player.ap, game.session.at, len(game.session.journal))
    for _ in range(3):
        game.play(("ask", "service_status"))
        assert game.cue["text"] == view["crime_timing"]["text"]
        assert (game.player.ap, game.session.at, len(game.session.journal)) == before


def test_timeline_replaces_a_claim_with_independent_corroboration():
    game = fresh(7)
    presence = game.case.evidence.presences[0]
    pid = presence.person
    approach(game, pid)
    game.play(("ask", "evening"))
    view = game.view(game.player)
    row = next(r for r in view["timeline"] if r.get("person") == pid)
    assert row["id"] == "evening:" + pid and row["status"] == "reported"
    assert row["start"] == remembered_times(presence)["start"]
    assert row["end"] == remembered_times(presence)["end"]
    game.play(("stop",))
    travel(game, presence.place)
    if not game.player.ap:
        game.play(("end",))
    game.play(("service_menu", presence.witness))
    game.play(("ask", "service_action", "verify:" + pid))
    view = game.view(game.player)
    rows = [r for r in view["timeline"] if r.get("person") == pid]
    assert len(rows) == 1 and rows[0]["status"] == "verified"
    assert rows[0]["alibi_state"] == "corroborated"
    assert pid in game.session.remaining()
    lead = next(r for r in view["leads"] if r["id"] == "evening:" + pid)
    assert lead["complete"] and lead["destinations"] == []
    assert "Camille" not in json.dumps(view, ensure_ascii=False)


@pytest.mark.parametrize("seed", (0, 5, 7, 19))
def test_seven_suspects_and_at_least_two_service_alibis(seed):
    game = fresh(seed)
    assert len(game.view(game.player)["notebook"]) == 7
    assert len(game.case.evidence.presences) >= 2
    for p in game.case.evidence.presences:
        keeper = next(k for k in game.case.crime.keepers if k.id == p.witness)
        assert p.place == keeper.place
        assert any(start <= p.start <= p.end <= end for start, end in keeper.shifts)
        verification = next(a for a in game.case.plan.actions if a.id == "verify:" + p.person)
        assert verification.actor == keeper.id and verification.place == keeper.place
        assert verification.requires == ("evening:" + p.person,)
    assert not any(a.actor.startswith("observer:") for a in game.case.plan.actions)


@pytest.mark.parametrize("chosen", (0, 1000))
def test_generated_seeds_are_human_readable_at_both_boundaries(tmp_path, monkeypatch, chosen):
    import solo_runtime
    def short_range(self, start, end):
        assert (start, end) == (0, 1001)
        return chosen
    monkeypatch.setattr(solo_runtime.random.SystemRandom, "randrange", short_range)
    session = SoloSession(tmp_path / "short-seed.json", 7, engine="causal")
    try:
        identity = receive(session)["solo"]["case_id"]
        session.send('{"type":"restart"}')
        view = receive(session)
        assert view["solo"]["seed"] == chosen
        assert view["solo"]["case_id"] != identity
    finally:
        session.close()
        session.worker.join(3)


# ---------------------------------------------------------------- free mode (v5)

def name_someone(game, exclude=()):
    """Ring a reachable door until a suspect introduces themself; returns their id."""
    for pid in sorted(game.case.plan.population):
        home = game.case.life.people[pid].home
        if pid not in exclude and game.occupants(home):
            travel(game, game.homes[home])
            game.play(("ring", home))
            game.play(("stop",))
            return pid
    pytest.skip("no suspect at home")


def test_setup_offers_difficulties_and_the_view_carries_the_deadline():
    game = CausalGame(7, ["Ada"])
    setup = game.setup()
    assert set(setup["difficulties"]) == {"facile", "normal", "difficile"} and setup["default_difficulty"] == "normal"
    assert game.view(game.player)["deadline"] is None
    game.equip(0, ("search", "rapport"), game.case.crime.scene, "difficile")
    view = game.view(game.player)
    assert view["difficulty"] == "difficile" and view["time_left"] >= 180 and view["mistakes"] == 0 and view["ended"] is None
    assert view["deadline"] == clock(game.session.deadline)
    with pytest.raises(ValueError):
        game.equip(0, ("search", "rapport"), game.case.crime.scene, "impossible")


def test_wrong_accusation_costs_time_clears_the_accused_and_survives_restore():
    game = CausalGame(0, ["Ada"])
    game.equip(0, ("search", "rapport"), game.case.crime.scene, "facile")
    game.start()
    author = game.case.crime.kernel.roles.author
    wrong = name_someone(game, exclude=(author,))
    travel(game, "police")
    if not game.player.ap:
        game.play(("end",))
    assert ("accuse", int(wrong[1:])) in game.options()
    before = game.session.time_left
    game.play(("accuse", int(wrong[1:])))
    view = game.view(game.player)
    assert view["mistakes"] == 1 and view["time_left"] == before - 90 and view["winner"] is None and view["ended"] is None
    assert view["conversation"]["context"] == "Dossier rejeté"
    assert ("accuse", int(wrong[1:])) not in game.options()
    restored = CausalGame.restore(0, "Ada", game.snapshot(), True)
    assert restored.snapshot()["difficulty"] == "facile"
    assert restored.view(restored.player) == view


def test_deadline_closes_the_case_and_names_the_culprit_only_then():
    game = CausalGame(0, ["Ada"])
    game.equip(0, ("search", "rapport"), game.case.crime.scene, "difficile")
    game.start()
    author = game.case.life.people[game.case.crime.kernel.roles.author].name
    while not game.session.finished:
        assert game.view(game.player)["ended"] is None
        game.play(("end",))
    view = game.view(game.player)
    assert view["ended"]["won"] is False and author in view["ended"]["text"] and view["time_left"] == 0
    assert game.options() == {}
    restored = CausalGame.restore(0, "Ada", game.snapshot(), True)
    assert restored.view(restored.player) == view


def test_right_accusation_wins_without_a_complete_file():
    game = CausalGame(0, ["Ada"])
    game.equip(0, ("search", "rapport"), game.case.crime.scene, "facile")
    game.start()
    author = game.case.crime.kernel.roles.author
    home = game.case.life.people[author].home
    if not game.occupants(home):
        pytest.skip("culprit away from home")
    travel(game, game.homes[home])
    game.play(("ring", home))
    game.play(("stop",))
    travel(game, "police")
    if not game.player.ap:
        game.play(("end",))
    game.play(("accuse", int(author[1:])))
    view = game.view(game.player)
    assert view["winner"] == "Ada" and view["ended"]["won"] is True and "Dossier établi" in view["ended"]["text"]
    restored = CausalGame.restore(0, "Ada", game.snapshot(), True)
    assert restored.view(restored.player) == view


def test_closing_a_conversation_is_always_possible_after_the_case_ends():
    game = CausalGame(0, ["Ada"])
    game.equip(0, ("search", "rapport"), game.case.crime.scene, "difficile")
    game.start()
    pid = next(p for p in sorted(game.case.plan.population) if game.occupants(game.case.life.people[p].home))
    home = game.case.life.people[pid].home
    travel(game, game.homes[home])
    game.play(("ring", home))
    session = game.session
    session.at = session.deadline
    session._check_deadline()
    game.note_turns.append(game.tick + 1)
    assert game.view(game.player)["ended"] is not None and game.view(game.player)["pending"] is not None
    assert game.options() == {}
    game.play(("stop",))  # never refused: the closing card must not be stuck behind a conversation
    assert game.view(game.player)["pending"] is None
    with pytest.raises(ValueError):
        game.play(("end",))


def test_greeting_reveals_the_look_only_and_the_evening_waits_for_the_alibi_question():
    game = fresh(0, ("search", "rapport"))
    pid = sorted(game.case.plan.population)[0]
    approach(game, pid)
    known = dict(game.session.state.known)
    assert "profile:" + pid in known and "evening:" + pid not in known
    game.play(("ask", "relation"))
    assert "evening:" + pid not in dict(game.session.state.known)
    assert next(r["alibi"] for r in game.view(game.player)["notebook"] if r["id"] == int(pid[1:])) is None
    game.play(("ask", "evening"))
    assert "evening:" + pid in dict(game.session.state.known)
    assert next(r["alibi"] for r in game.view(game.player)["notebook"] if r["id"] == int(pid[1:])) in ("à vérifier", "invérifiable")


def test_a_suspect_is_described_first_and_talking_is_the_paid_step():
    game = fresh(0, ("search", "rapport"))
    pid = sorted(game.case.plan.population)[0]
    home = game.case.life.people[pid].home
    travel(game, game.homes[home])
    ap = game.player.ap
    game.play(("ring", home))
    look = game.person(pid)["appearance"]
    assert game.cue["stage"] == "approach" and game.cue["person"]["detective"]
    assert game.cue["text"].startswith("Le suspect s'appelle ") and look["coat"] in game.cue["text"]
    assert game.options() == {("talk",): "Lui parler (1 PA)", ("stop",): "Quitter"}
    assert game.player.ap == ap  # looking is free
    game.play(("talk",))
    assert game.cue["stage"] == "greeting" and game.player.ap == ap - 1 and game.slots == QUESTIONS_PER_PA
    game.play(("ask", "relation"))
    game.play(("ask", "work"))
    game.play(("stop",))
    said = next(r["said"] for r in game.view(game.player)["notebook"] if r["id"] == int(pid[1:]))
    assert [a["question"] for a in said] == ["Lien", "Métier"]
    game.player.ap = 0
    game.play(("ring", home))
    assert game.options() == {("stop",): "Quitter"}  # no point left: a look, no talk, no reread


def test_turn_start_headlines_announce_what_became_possible():
    game = fresh(0, ("search", "rapport"))
    game.play(("investigate", "inspect_scene"))
    game.play(("investigate", "request_exam"))
    assert [a.id for a in game.pending_actions()] == ["read_medical"]
    lines = []
    while not lines and game.tick < 6:
        lines = game.play(("end",))
    assert lines == ["📰 Le légiste a terminé : son rapport vous attend à la Morgue."] and game.tick == 2
    assert not game.pending_actions() and game.play(("end",)) == []  # announced once


def test_an_employer_calls_a_suspect_in_once_you_know_where_they_work():
    game = fresh(0, ("search", "rapport"))
    pid = next(p for p in sorted(game.case.plan.population) if game.case.life.people[p].workplace.value in ("bar", "restaurant"))
    person = game.case.life.people[pid]
    venue = person.workplace.value
    travel(game, venue)
    if not game.player.ap:
        game.play(("end",))
    game.play(("service_menu", "staff:" + venue))
    assert not [k for k in game.options() if k[0] == "summon"]  # nothing established yet
    game.play(("ask", "service_action", "venue_staff:" + venue))  # the roster names the staff
    assert game.workplace_known(pid) and game.options()[("summon", int(pid[1:]))] == "Faire appeler " + person.name + " (1 PA)"
    if not game.player.ap:
        game.play(("stop",)), game.play(("end",)), game.play(("service_menu", "staff:" + venue))
    ap = game.player.ap
    game.play(("summon", int(pid[1:])))
    assert game.player.ap == ap - 1 and person.name in game.cue["text"]
    assert ("summon", int(pid[1:])) not in game.options()  # once per turn
    row = next(r for r in game.view(game.player)["notebook"] if r["id"] == int(pid[1:]))
    assert row["whereabouts"]["next"] == {"place": venue, "activity": "appelé au travail", "label": game.session.locations[venue]}
    game.play(("stop",))
    lines = game.play(("end",))
    assert any(line.startswith("📰") and person.name in line for line in lines)
    assert game.session.person_places[pid] == venue and pid not in game.occupants(person.home)
    assert ("interrogate", int(pid[1:])) in game.options()
    restored = CausalGame.restore(game.seed, "Ada", game.snapshot(), True)
    assert restored.summons == game.summons and restored.view(restored.player) == game.view(game.player)


def test_anyone_may_pick_a_lock_through_the_dial_and_the_score_replays():
    scores = iter([0.2, 0.9])
    game = CausalGame(0, ["Ada"], challenge=lambda kind, difficulty: next(scores))
    game.equip(0, ("search", "rapport"), game.case.crime.scene, "facile")
    game.start()
    home = next(h for h in game.homes if not game.occupants(h) and not game.home_open(h))
    travel(game, game.homes[home])
    assert ("unlock_home", home) in game.options()  # no skill needed to try
    game.play(("unlock_home", home))
    assert game.session.place != home and game.history[-1] == ["unlock_home", home, 0.2]
    game.play(("unlock_home", home))
    assert game.session.place == home and game.history[-1] == ["unlock_home", home, 0.9]
    restored = CausalGame.restore(0, "Ada", game.snapshot(), True, challenge=lambda kind, difficulty: 0.0)
    assert restored.view(restored.player) == game.view(game.player)  # saved scores, no new dial
    skilled = CausalGame(0, ["Ada"], challenge=lambda kind, difficulty: 0.0)
    skilled.equip(0, ("fingerprints", "lockpick"), skilled.case.crime.scene, "facile")
    skilled.start()
    travel(skilled, skilled.homes[home])
    skilled.play(("unlock_home", home))
    assert skilled.session.place == home and skilled.history[-1] == ["unlock_home", home]  # the skill skips the dial


def test_the_video_archive_offers_the_previous_days_once_for_a_point():
    game = fresh(7)
    discover(game, "inspect_scene")
    travel(game, "cctv")
    if not game.player.ap:
        game.play(("end",))
    game.play(("camera_menu",))
    place = next(c.place for c in game.case.evidence.cameras if c.online)
    game.play(("ask", "camera_district", place))
    assert game.options()[("ask", "camera_past")] == "Jours précédents (1 PA)"
    before = game.player.ap
    game.play(("ask", "camera_past"))
    assert game.player.ap == before - 1 and "camera_past:" + place in game.session.state.completed
    assert game.options()[("ask", "camera_past")] == "Jours précédents · consulté"
    text = game.cue["text"]
    game.play(("ask", "camera_past"))
    assert game.cue["text"] == text and game.player.ap == before - 1
