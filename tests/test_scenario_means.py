"""Spatial acquisition, custody, benign events and public inventory ambiguity."""
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import scenario_crime as c
import scenario_kernel as k
from scenario_means import AcquisitionKind as A, ToolKind, TransferKind, access_people, inventory_observations
from scenario_victim import VictimGoal, candidate_plans


ROOT = Path(__file__).resolve().parents[1]


def fixture(premise=k.SUPPORTED_PREMISES[0]):
    world = k.KernelBuilder(42).build(premise)
    builder = c.CrimeBuilder(42)
    streets, inventory = builder.prepare(world)
    author = next(p for p in world.world.people if p.id == world.roles.author)
    victim = next(p for p in world.world.people if p.id == world.roles.victim)
    exit = streets.neighbors(victim.workplace.value)[0][0]
    far = next(n.id for n in streets.nodes if n.kind is c.NodeKind.STREET and n.id != exit)
    edges = tuple(replace(e, b=far) if e.a == victim.home else
                  replace(e, b=exit) if e.a in ("bar", "restaurant") else e for e in streets.edges)
    streets = replace(streets, edges=edges)
    inventory = tuple(replace(t, pickup_point=exit) if t.owner in ("bar", "restaurant") and t.point != t.place
                      else t for t in inventory if t.owner != author.id)
    inventory += tuple(c.Tool(f"test_{kind.value}", kind, author.id, author.home, -100, "usage domestique")
                       for kind in ToolKind)
    plan = candidate_plans(world, goal=VictimGoal.RETURN_HOME)[0]
    return world, builder, streets, inventory, plan


def execute(acquisition=A.TAKEN, *, method=c.Method.EDGED, fate=c.ToolFate.RETAINED, mundane=False,
            source="restaurant", premise=k.SUPPORTED_PREMISES[0]):
    world, builder, streets, inventory, plan = fixture(premise)
    return builder.execute(world, streets, inventory, plan=plan, method=method, fate=fate,
                           acquisition=acquisition, mundane=mundane,
                           source_place="home" if acquisition is A.OWNED else source)


@pytest.mark.parametrize("premise", k.SUPPORTED_PREMISES)
@pytest.mark.parametrize("method", [c.Method.EDGED, c.Method.BLUNT])
@pytest.mark.parametrize("fate", list(c.ToolFate))
@pytest.mark.parametrize("acquisition", list(A))
def test_all_roots_methods_sources_and_fates_when_physically_feasible(premise, method, fate, acquisition):
    crime = execute(acquisition, method=method, fate=fate, premise=premise)
    assert crime.method is method and crime.execution.acquisition is acquisition
    assert crime.execution.tool_fate is fate and crime.kernel.method is None
    tool = next(t for t in crime.inventory if t.id == crime.execution.tool)
    state = next(s for s in crime.tool_states if s.tool == tool.id)
    assert not state.in_original_storage
    assert state.concealed == (fate is c.ToolFate.HIDDEN)
    assert len(crime.tool_states) == len(crime.inventory)
    assert len({s.tool for s in crime.tool_states}) == len(crime.inventory)
    assert crime.execution.acquired_at < crime.execution.attack_at
    if acquisition is A.OWNED:
        assert tool.owner == crime.kernel.roles.author and crime.inventory_checks == ()
    else:
        assert tool.owner == tool.place == "restaurant" and crime.inventory_checks
        check = crime.inventory_checks[0]
        assert check.expected - check.present == 1
        assert check.authorized_out == (acquisition is A.BORROWED)
        observations = inventory_observations(crime, place="restaurant", discovered_at=check.observed_at)
        assert len(observations) == 1 and len(observations[0]["candidates"]) >= 2


def test_taken_weapon_adds_real_detour_before_observation():
    crime = execute()
    x = crime.execution
    tool = next(t for t in crime.inventory if t.id == x.tool)
    assert x.preparation.nodes[0] == x.escape.nodes[-1]
    assert x.preparation.nodes[-1] == tool.point == x.approach.nodes[0]
    assert x.preparation.times[-1] == x.acquired_at == x.approach.times[0] - 1
    assert x.acquired_at < x.observation_at


def test_opportunistic_means_are_acquired_after_observation_on_actual_route():
    crime = execute(A.OPPORTUNISTIC)
    x = crime.execution
    tool = next(t for t in crime.inventory if t.id == x.tool)
    assert x.observation_at <= x.acquired_at < x.attack_at
    assert (tool.point, x.acquired_at) in tuple(zip(x.following.nodes, x.following.times))
    assert x.preparation.nodes == (x.approach.nodes[0],)
    assert tool.owner == "restaurant" and x.permission_by is None


def test_innocent_loan_can_create_absence_without_any_venue_murder_weapon():
    crime = execute(A.OWNED, mundane=True)
    loan = crime.mundane_borrowings[0]
    assert loan.actor not in (crime.kernel.roles.author, crime.kernel.roles.victim)
    assert loan.tool != crime.execution.tool
    assert loan.inbound.nodes[-1] == loan.outbound.nodes[0]
    assert loan.inbound.times[-1] < 17 * 60
    assert crime.inventory_checks and all(check.authorized_out == 1 for check in crime.inventory_checks)
    rows = [row for place in ("bar", "restaurant")
            for row in inventory_observations(crime, place=place, discovered_at=k.DAY + 8 * 60)]
    assert rows and all(row["interpretation"] == "lead_not_proof" for row in rows)
    text = json.dumps(rows)
    assert loan.actor in text  # Still one of several possibilities, not identified as a taker.
    assert "innocent_loan" not in text and "weapon_pickup" not in text and "transfers" not in text


def test_ordinary_loans_are_optional_and_reproducible_not_permanent_red_herrings():
    outcomes, sources, fates = set(), set(), set()
    for seed in range(80):
        world = k.KernelBuilder(seed).sample()
        crime = c.CrimeBuilder(seed).build(world)
        assert crime == c.CrimeBuilder(seed).build(world)
        outcomes.add(bool(crime.mundane_borrowings))
        sources.add(crime.execution.acquisition)
        fates.add(crime.execution.tool_fate)
    assert outcomes == {False, True} and sources == set(A) and fates == set(c.ToolFate)


def test_discovery_is_gated_by_check_time_and_actual_place():
    crime = execute()
    when = crime.inventory_checks[0].observed_at
    assert inventory_observations(crime, place="restaurant", discovered_at=when - 1) == ()
    assert inventory_observations(crime, place="bar", discovered_at=when) == ()
    assert inventory_observations(crime, place="restaurant", discovered_at=when)


def test_public_inventory_does_not_expose_guilt_exact_tool_or_private_origins():
    crime = execute()
    row = inventory_observations(crime, place="restaurant", discovered_at=k.DAY + 8 * 60)[0]
    assert not {"author", "actor", "tool", "method", "acquisition", "sources", "transfers", "holder"} & row.keys()
    assert crime.kernel.roles.author in row["candidates"] and len(row["candidates"]) >= 2
    assert row["expected"] == 3 and row["present"] == 2 and row["authorized_out"] == 0
    assert crime.execution.tool not in json.dumps(row)


def test_public_count_and_loan_context_are_a_single_ambiguous_artifact():
    crime = execute(A.BORROWED, mundane=True)
    rows = inventory_observations(crime, place="restaurant", discovered_at=k.DAY + 8 * 60)
    assert all(len(row["candidates"]) >= 2 for row in rows)
    assert any(row["authorized_out"] >= 1 for row in rows)
    assert all("arme du crime" not in row["text"] for row in rows)


@pytest.mark.parametrize("field,value,message", [
    ("acquisition", "taken", "typed execution"),
    ("permission_by", "imaginary_keeper", "permission"),
    ("acquired_at", 1439, "actual source"),
    ("hidden_at", "restaurant", "hiding"),
])
def test_forged_criminal_acquisition_is_rejected(field, value, message):
    crime = execute(A.BORROWED)
    with pytest.raises(c.InvalidCrime, match=message):
        replace(crime, execution=replace(crime.execution, **{field: value}))


def test_unobserved_or_off_route_opportunistic_pickup_is_rejected():
    crime = execute(A.OPPORTUNISTIC)
    for time in (crime.execution.observation_at - 1, crime.execution.attack_at + 1):
        with pytest.raises(c.InvalidCrime, match="opportunistic pickup"):
            replace(crime, execution=replace(crime.execution, acquired_at=time))


def test_source_access_cannot_be_invented_or_narrowed_to_the_killer():
    crime = execute()
    for access in ((crime.kernel.roles.author,), ("unknown",)):
        inventory = tuple(replace(t, access=access) if t.id == crime.execution.tool else t for t in crime.inventory)
        with pytest.raises(c.InvalidCrime, match="access holders|two eligible"):
            replace(crime, inventory=inventory)


def test_shared_tool_cannot_be_teleported_to_a_different_pickup_point():
    crime = execute()
    inventory = tuple(replace(t, pickup_point="police") if t.id == crime.execution.tool else t for t in crime.inventory)
    with pytest.raises(c.InvalidCrime, match="actual pickup point"):
        replace(crime, inventory=inventory)


def test_missing_stock_cannot_be_invented_independently_of_movements():
    crime = execute()
    check = crime.inventory_checks[0]
    for check_change in ({"present": 3}, {"expected": 20}, {"observed_at": 0}, {"transfers": ("fake",)}, {"keeper": "unknown"}):
        with pytest.raises(c.InvalidCrime, match="inventory observations derive"):
            replace(crime, inventory_checks=(replace(check, **check_change),))


def test_tool_ownership_does_not_change_and_custody_cannot_be_forged():
    crime = execute()
    tool = next(t for t in crime.inventory if t.id == crime.execution.tool)
    assert tool.owner == "restaurant"
    state = next(s for s in crime.tool_states if s.tool == tool.id)
    assert state.holder == crime.kernel.roles.author and state.place == crime.execution.escape.nodes[-1]
    states = tuple(replace(s, in_original_storage=True) if s.tool == tool.id else s for s in crime.tool_states)
    with pytest.raises(c.InvalidCrime, match="conservation"):
        replace(crime, tool_states=states)
    with pytest.raises(c.InvalidCrime, match="object transfers derive"):
        replace(crime, transfers=crime.transfers[1:])


def test_ordinary_actor_and_object_cannot_be_relabelled_as_crime_or_victim():
    crime = execute(A.OWNED, mundane=True)
    loan = crime.mundane_borrowings[0]
    for change in ({"actor": crime.kernel.roles.author}, {"actor": crime.kernel.roles.victim}, {"tool": crime.execution.tool}):
        with pytest.raises(c.InvalidCrime, match="innocent borrows"):
            replace(crime, mundane_borrowings=(replace(loan, **change),))


def test_incompatible_forced_origin_fails_without_rng_or_fact_changes():
    world, builder, streets, inventory, plan = fixture()
    state, before = builder.rng.getstate(), world.as_dict()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(world, streets, inventory, plan=plan, acquisition=A.OWNED, source_place="restaurant")
    assert builder.rng.getstate() == state and world.as_dict() == before


def test_forced_ordinary_loan_without_shared_objects_fails_before_rng():
    world, builder, streets, inventory, plan = fixture()
    inventory = tuple(t for t in inventory if t.owner not in ("bar", "restaurant"))
    state = builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(world, streets, inventory, plan=plan, acquisition=A.OWNED, mundane=True)
    assert builder.rng.getstate() == state


def test_future_shared_objects_are_not_preexisting_and_fail_before_rng():
    world, builder, streets, inventory, plan = fixture()
    inventory = tuple(replace(t, available_since=1439) if t.owner == "restaurant" else t for t in inventory)
    state = builder.rng.getstate()
    with pytest.raises(c.InvalidCrime, match="existing lawful tool origin"):
        builder.execute(world, streets, inventory, plan=plan, acquisition=A.TAKEN, source_place="restaurant")
    assert builder.rng.getstate() == state


def test_closed_lender_is_filtered_before_rng(monkeypatch):
    world, builder, streets, inventory, plan = fixture()
    keepers = tuple(replace(keeper, shifts=((0, 1),)) for keeper in c.default_keepers())
    monkeypatch.setattr(c, "default_keepers", lambda: keepers)
    state = builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(world, streets, inventory, plan=plan, acquisition=A.BORROWED)
    assert builder.rng.getstate() == state


@pytest.mark.parametrize("choices", [{"mundane": "yes"}, {"source_place": 7}])
def test_build_rejects_invalid_option_types_before_world_generation(choices):
    world = k.KernelBuilder(7).sample()
    builder = c.CrimeBuilder(7)
    state = builder.rng.getstate()
    with pytest.raises(TypeError):
        builder.build(world, **choices)
    assert builder.rng.getstate() == state


def test_no_opportunistic_pickup_when_only_one_street_precedes_destination():
    world, builder, streets, inventory, plan = fixture()
    victim = next(p for p in world.world.people if p.id == world.roles.victim)
    exit = streets.neighbors(victim.workplace.value)[0][0]
    streets = replace(streets, edges=tuple(replace(e, b=exit) if e.a == victim.home else e for e in streets.edges))
    state = builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(world, streets, inventory, plan=plan, acquisition=A.OPPORTUNISTIC)
    assert builder.rng.getstate() == state


def test_cli_shared_weapon_and_public_inventory_wrapper():
    args = ["--seed", "7", "--acquisition", "taken", "--weapon-origin", "restaurant",
            "--method", "edged", "--no-mundane", "--public-inventory", "--json"]
    direct = subprocess.check_output([sys.executable, "scenario_crime.py", *args], cwd=ROOT)
    wrapped = subprocess.check_output([sys.executable, "scenario_sampler.py", "--step", "5", *args], cwd=ROOT)
    assert direct == wrapped
    data = json.loads(direct)
    assert data[0]["visibility"] == "public_inventory_preview"
    assert data[0]["observations"][0]["present"] == 2
    assert all(len(row["candidates"]) >= 2 for row in data[0]["observations"])


def test_restaurant_is_a_real_connected_place_in_live_game_and_physical_catalogue():
    from city import GRID, HANGOUTS, HANGOUT_WEIGHTS
    from game import Game, RULES_VERSION
    assert sum(row.count("restaurant") for row in GRID) == 1
    assert len(HANGOUTS) == len(HANGOUT_WEIGHTS) and "restaurant" in HANGOUTS
    for seed in range(12):
        game = Game(seed=seed)
        game.equip(0, ["taxi"], start="restaurant")
        view = game.view(game.player)
        assert RULES_VERSION == 13 and "restaurant" in game.map and game.map["restaurant"][1]
        assert view["place"] == "restaurant" and view["staff"][0]["id"] == "staff:restaurant"
        assert view["staff"][0]["name"] == "Le serveur"
        reached, pending = {"restaurant"}, ["restaurant"]
        while pending:
            for place in game.map[pending.pop()][1]:
                if place not in reached:
                    reached.add(place)
                    pending.append(place)
        assert reached == set(game.map)
