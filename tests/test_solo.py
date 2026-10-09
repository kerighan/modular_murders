"""The APK's Python adapter, exercised without FastAPI, loom or remote AI."""
import json
import time

import pytest

from game import Game, RULES_VERSION
from solo_runtime import SoloSession


def receive(session, kind="view", timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        for msg in json.loads(session.poll()):
            if msg["type"] == kind:
                return msg
            if msg["type"] == "error":
                raise AssertionError(msg["message"])
        time.sleep(0.01)
    raise AssertionError(f"no {kind} message")


@pytest.fixture
def session(tmp_path):
    s = SoloSession(tmp_path / "solo.json")
    yield s
    s.close()
    s.worker.join(3)
    assert not s.worker.is_alive()


def equip(s):
    receive(s)
    s.send(json.dumps({"type": "equip", "items": ["taxi", "forensic_kit"], "start": "victim_street"}))
    return receive(s)


def test_setup_and_walk_use_engine_rules(session):
    view = equip(session)
    key = view["routes"]["bar"]["key"]
    assert key == ["walk", "bar"]
    session.send(json.dumps({"type": "play", "key": key}))
    after = receive(session)
    assert after["place"] == "bar"
    assert after["ap"] == 1


def test_resume_exact_state_and_no_setup(session):
    view = equip(session)
    session.send(json.dumps({"type": "play", "key": ["move", "bar"]}))
    before = receive(session)
    session.close()
    session.worker.join(3)
    resumed = SoloSession(session.path)
    try:
        after = receive(resumed)
        assert "setup" not in after
        assert after["solo"]["resumed"]
        for key in ("place", "ap", "tick", "options", "notebook", "routes", "present"):
            assert after[key] == before[key]
    finally:
        resumed.close()
        resumed.worker.join(3)


def test_qte_does_not_block_poll_or_score(session):
    view = equip(session)
    # Entering the victim's locked apartment requires a real client score.
    session.send(json.dumps({"type": "play", "key": ["move", "victim_house"]}))
    challenge = receive(session, "challenge")
    assert "difficulty" in challenge
    assert session.waiting_score.is_set()
    assert json.loads(session.poll()) == []
    session.send('{"type":"score","score":1.0}')
    after = receive(session)
    assert after["place"] == "victim_house"
    data = json.loads(session.path.read_text())
    assert data["history"][-1][2] == [1.0]
    replay = Game.replay(data["seed"], [data["name"]], data["items"], data["history"], starts=data["starts"])
    assert replay.players[0].place == "victim_house"


def test_bad_action_preserves_game_and_save(session):
    before = equip(session)
    saved = session.path.read_bytes()
    session.send('{"type":"play","key":["walk","not_a_place"]}')
    receive(session, "error")
    assert session.path.read_bytes() == saved
    assert session.game.view(session.game.players[0])["ap"] == before["ap"]
    assert not session.game.history


def test_invalid_setup_rejected(session):
    receive(session)
    session.send('{"type":"equip","items":["victim_key"],"start":"police"}')
    receive(session, "error")
    assert not session.equipped
    assert session.game.players[0].items == set()
    assert not session.path.exists()


def test_corrupt_save_kept_and_fresh_setup(tmp_path):
    save = tmp_path / "solo.json"
    save.write_text("broken")
    s = SoloSession(save)
    try:
        receive(s, "error")
        # Error and view may arrive together; inspect the worker's recovered state.
        assert not s.equipped
        assert list(tmp_path.glob("solo.json.invalid-*"))[0].read_text() == "broken"
    finally:
        s.close()
        s.worker.join(3)


def test_restart_saved_before_relaunch(session):
    equip(session)
    old_seed = session.seed
    session.send('{"type":"restart"}')
    after = receive(session)
    assert "setup" in after
    assert after["solo"]["seed"] != old_seed
    assert json.loads(session.path.read_text())["equipped"] is False


def test_close_cancels_pending_qte(session):
    equip(session)
    session.send('{"type":"play","key":["move","victim_house"]}')
    receive(session, "challenge")
    session.close()
    session.worker.join(3)
    assert not session.worker.is_alive()


def test_end_turn_uses_supplied_key_and_saves(session):
    before = equip(session)
    key = next(key for key, _ in before["options"] if key == ["end"])
    session.send(json.dumps({"type": "play", "key": key}))
    after = receive(session)
    assert after["tick"] == before["tick"] + 1
    assert after["ap"] == 3
    assert json.loads(session.path.read_text())["history"][-1][1] == key


def test_legacy_automatic_turn_save_migrates_without_reset(tmp_path):
    game = Game(seed=42, players=["Ada"])
    game.auto_end = True
    game.equip(0, ["taxi", "forensic_kit"], "victim_street")
    game.start()
    for destination in ["bar", "police", "alley", "bar"]:
        game.play(("move", destination))
    before = game.view(game.player)
    data = {"version": 1, "rules_version": RULES_VERSION, "seed": 42, "name": "Ada", "equipped": True,
            "items": [["taxi", "forensic_kit"]], "starts": ["victim_street"], "history": game.history}
    save = tmp_path / "legacy.json"
    save.write_text(json.dumps(data))
    session = SoloSession(save)
    try:
        after = receive(session)
        for field in ["place", "ap", "tick", "notebook"]:
            assert after[field] == before[field]
        assert not session.game.auto_end
        for destination in ["police", "bar"]:
            session.send(json.dumps({"type": "play", "key": ["move", destination]}))
            after = receive(session)
        assert after["ap"] == 0 and after["tick"] == before["tick"]
        migrated = json.loads(save.read_text())
        assert migrated["version"] == 2 and migrated["legacy_auto_end"] == len(data["history"])
        session.close()
        session.worker.join(3)
        session = SoloSession(save)
        assert receive(session)["ap"] == 0
        session.send('{"type":"play","key":["end"]}')
        assert receive(session)["tick"] == before["tick"] + 1
    finally:
        session.close()
        session.worker.join(3)


def test_old_scenario_save_is_preserved_not_replayed_into_another_world(tmp_path):
    data = {"version": 2, "seed": 7, "name": "Ada", "equipped": True,
            "items": [["taxi"]], "starts": ["bar"], "history": [],
            "journals": [[{"text": "An obsolete, incompatible clue"}]]}
    save = tmp_path / "old-rules.json"
    raw = json.dumps(data)
    save.write_text(raw)
    session = SoloSession(save)
    try:
        error = receive(session, "error")
        assert "ancienne génération" in error["message"]
        assert session.equipped is False
        assert session.game.player.journal == []
        backups = list(tmp_path.glob("old-rules.json.invalid-*"))
        assert len(backups) == 1 and backups[0].read_text() == raw
    finally:
        session.close()
        session.worker.join(3)
