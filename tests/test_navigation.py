"""Map navigation costs and multi-step actions remain authoritative on the server."""
import pytest

from game import AP, Game


def fresh_game(**kwargs):
    game = Game(seed=42, **kwargs)
    game.equip(0, [], "victim_street")
    game.start()
    return game


def test_walking_cost_uses_graph_including_suspended_bridge():
    game = fresh_game()
    routes = game.view(game.player)["routes"]
    assert routes["victim_house"]["cost"] == 1  # explicit bridge, two grid columns apart
    assert routes["bar"]["cost"] == 2
    assert routes["cabaret"]["cost"] == 4
    assert routes["cabaret"]["reason"] == "too_far"
    assert routes["cabaret"]["key"] is None
    assert ("walk", "bar") in game.options()


def test_ground_zones_receive_real_adjacency_not_decorative_cells():
    game = fresh_game()
    adjacency = game.view(game.player)["adjacency"]
    assert adjacency == {place: list(neighbors) for place, (_, neighbors) in game.map.items()}
    assert "victim_house" in adjacency["victim_street"]
    assert "hospital" not in adjacency["victim_street"]
    assert all(place in adjacency[neighbor] for place, neighbors in adjacency.items() for neighbor in neighbors)


def test_two_step_walk_charges_two_points_and_arrives():
    game = fresh_game()
    game.play(("walk", "bar"))
    assert game.player.place == "bar"
    assert game.player.ap == AP - 2
    assert game.tick == 0
    assert game.view(game.player)["routes"]["victim_street"]["reason"] == "too_far"


def test_unaffordable_route_is_rejected_without_mutation():
    game = fresh_game()
    game.player.ap = 1
    with pytest.raises(ValueError, match="not an option"):
        game.play(("walk", "bar"))
    assert game.player.place == "victim_street" and game.player.ap == 1
    assert game.history == []


def test_taxi_and_walking_are_separate_options_with_separate_costs():
    game = fresh_game()
    game.player.items.add("taxi")
    assert ("move", "bar") in game.options()  # existing taxi protocol stays compatible
    assert ("walk", "bar") in game.options()
    assert game.view(game.player)["routes"]["bar"]["key"] == ("walk", "bar")
    game.play(("move", "bar"))
    assert game.player.ap == AP - 1


def test_occupied_apartments_are_not_long_distance_destinations():
    game = fresh_game()
    apartment = "house_1"
    game.where[1] = apartment
    route = game.view(game.player)["routes"][apartment]
    assert route["reason"] == "occupied" and route["key"] is None
    assert ("walk", apartment) not in game.options()


def test_only_active_detective_can_follow_a_route():
    game = fresh_game(players=("Ada", "Bob"))
    assert all(not route["available"] for route in game.view(game.players[1])["routes"].values())


def test_exact_cost_waits_for_manual_end_and_replays_deterministically():
    game = fresh_game()
    destination = next(place for place, route in game.view(game.player)["routes"].items()
                       if route["cost"] == AP and route["available"] and game.owner(place) is None)
    game.play(("walk", destination))
    assert game.tick == 0 and game.player.ap == 0 and game.player.place == destination
    assert list(game.options()) == [("end",)]
    game.play(("end",))
    assert game.tick == 1 and game.player.ap == AP
    replay = Game.replay(game.seed, ["Détective"], [[]], game.history, starts=["victim_street"])
    assert replay.player.place == game.player.place and replay.tick == game.tick


def test_failed_final_lock_leaves_you_at_the_doorstep():
    game = fresh_game(challenge=lambda *_: 0.0)
    game.player.place = "crime_scene"
    path = next(path for place, path in game.walking_paths(game.player).items()
                if place.startswith("house_") and len(path) == 3)
    game.where[game.owner(path[-1])] = "bar"
    game.play(("walk", path[-1]))
    assert game.player.place == path[-2] and game.player.ap == AP - 2
