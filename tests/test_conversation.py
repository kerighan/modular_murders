"""RPG presentation must not alter costs, expose secrets or drop final replies."""
from game import Game, QUESTIONS
import pytest


def conversation_game(players=("Ada",), score=1.0):
    game = Game(seed=42, players=players, challenge=lambda *_: score)
    for i in range(len(players)):
        game.equip(i, ["taxi"], "bar")
    game.start()
    who = game.suspects_at("bar")[0]
    game.play(("interrogate", who))
    return game, who


def test_greeting_is_private_and_only_known_appearance_is_sent():
    game, who = conversation_game(players=("Ada", "Bob"))
    ada, bob = game.players
    cue = game.view(ada)["conversation"]
    assert cue["active"] and cue["remaining"] == 3
    assert cue["person"]["id"] == who and cue["person"]["name"] == game.name(who)
    assert set(cue["person"]) == {"id", "name", "look"}
    assert game.view(bob)["conversation"] is None
    assert ada.ap == 2  # UI selection itself never changes the engine's cost.


def test_answer_is_exact_speech_and_notes_are_separate():
    game, _ = conversation_game()
    events = game.play(("ask", "alibi"))
    cue = game.view(game.player)["conversation"]
    assert events[0] == f'{cue["person"]["name"]} — {cue["text"]}'
    assert cue["question"] == QUESTIONS["alibi"]
    assert cue["notes"] == events[1:]
    assert cue["active"] and cue["remaining"] == 2
    assert game.player.ap == 2


def test_final_reply_survives_pending_clear_without_forcing_a_new_turn():
    game, _ = conversation_game(score=0.3)
    game.player.ap = 0  # Last-PA interrogations finish before the turn changes.
    game.play(("ask", "seen"))
    cue = game.view(game.players[0])["conversation"]
    assert cue["stage"] == "reply" and cue["text"]
    assert not cue["active"] and cue["remaining"] == 0 and game.tick == 0
    assert game.pending is None
    assert list(game.options()) == [("end",)]


def test_stop_and_later_actions_do_not_reopen_old_speech():
    game, _ = conversation_game()
    game.play(("stop",))
    assert game.view(game.player)["conversation"]["stage"] == "farewell"
    game.play(("end",))
    assert game.view(game.player)["conversation"] is None


def test_pending_conversation_replays_and_still_offers_unasked_questions():
    game, _ = conversation_game()
    game.play(("ask", "link"))
    replay = Game.replay(game.seed, ["Ada"], [["taxi"]], game.history, starts=["bar"])
    assert replay.view(replay.player)["conversation"] == game.view(game.player)["conversation"]
    assert ("ask", "link") not in replay.options()
    assert ("ask", "seen") in replay.options()
    assert replay.view(replay.player)["notebook"] == game.view(game.player)["notebook"]


def test_region_is_street_for_apartments_and_public_place_otherwise():
    game, _ = conversation_game()
    assert game.view(game.player)["region"] == "bar"
    house = next(place for place in game.map if place.startswith("house_"))
    game.player.place = house
    assert game.view(game.player)["region"] == game.map[house][1][0]


def test_inhabitants_only_move_after_explicit_end_not_during_last_pa_dialogue(monkeypatch):
    game = Game(42, challenge=lambda *_: 1.0)
    game.equip(0, ["taxi"], "bar")
    game.start()
    calls = []
    original = game.move_suspects

    def move():
        calls.append(game.tick)
        original()

    monkeypatch.setattr(game, "move_suspects", move)
    game.player.ap = 1
    present = game.suspects_at(game.player.place)
    game.play(("interrogate", present[0]))
    assert game.player.ap == 0 and game.tick == 0 and calls == []
    for question in ("alibi", "link", "seen"):
        game.play(("ask", question))
        assert game.suspects_at(game.player.place) == present
        assert game.tick == 0 and calls == []
    game.play(("end",))
    assert calls == [1] and game.tick == 1


def test_unknown_people_do_not_have_an_address_in_the_notebook():
    game = Game(42)
    assert all(row["home"] is None for row in game.view(game.player)["notebook"])


@pytest.mark.parametrize("seed", [0, 7, 42, 93])
def test_identified_people_have_their_actual_apartment_and_region(seed):
    game = Game(seed)
    for sid in game.order:
        game.reveal(game.player, sid, [], name=True)
    for row in game.view(game.player)["notebook"]:
        house = f'house_{row["id"]}'
        region = game.map[house][1][0]
        assert row["home"] == {"place": house, "region": region,
                               "label": game.label(house), "region_label": game.label(region)}
    sid = game.order[0]
    game.move_house(sid, "den")
    assert game.home_view(game.player, sid)["region"] == "den"


def test_identifying_someone_does_not_reveal_their_address_to_another_detective():
    game = Game(42, players=["Ada", "Bob"])
    ada, bob = game.players
    game.reveal(ada, 0, [], name=True)
    assert game.home_view(ada, 0) is not None
    assert game.home_view(bob, 0) is None
    assert next(row for row in game.view(bob)["notebook"] if row["id"] == 0)["home"] is None
