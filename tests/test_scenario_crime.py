"""Physical truth tests: break access, co-presence, routing and causation."""
import json
import os
import random
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import scenario_crime as c
import scenario_kernel as k


ROOT = Path(__file__).resolve().parents[1]


def sample(seed=42):
    # Historical physical invariants in the owned-weapon branch. Shared-source
    # and opportunistic mutations are covered by test_scenario_means.py.
    return c.CrimeBuilder(seed).build(k.KernelBuilder(seed).sample(),
                                     acquisition=c.AcquisitionKind.OWNED, mundane=False,
                                     situation=c.SituationKind.TRACKING)


def altered(crime, **changes):
    return replace(crime, execution=replace(crime.execution, **changes))


@pytest.mark.parametrize("batch", range(20))
def test_thousand_crimes_are_valid_reproducible_and_preserve_kernel(batch):
    for seed in range(batch * 10, batch * 10 + 10):
        for premise in k.SUPPORTED_PREMISES:
            kernel = k.KernelBuilder(seed).build(premise)
            before = kernel.as_dict()
            crime = c.CrimeBuilder(seed).build(kernel)
            assert crime == c.CrimeBuilder(seed).build(kernel)
            assert c.validate_crime(crime) is crime
            assert crime.kernel is kernel and kernel.as_dict() == before
            assert kernel.method is None
            assert crime.streets.kind(crime.scene) is (c.NodeKind.WORKPLACE if crime.method is c.Method.POISONED else c.NodeKind.STREET)
            if crime.execution.situation is c.SituationKind.TRACKING:
                assert crime.execution.victim_walk.nodes[-1] != crime.execution.intended_journey.nodes[-1]
            assert crime.as_dict()["visibility"] == "private_executed_truth"
            assert not {"candidates", "evidence", "witnesses", "cameras"} & crime.as_dict().keys()


@pytest.mark.parametrize("premise", k.SUPPORTED_PREMISES)
@pytest.mark.parametrize("method", [c.Method.EDGED, c.Method.BLUNT])
@pytest.mark.parametrize("encounter", [c.Encounter.AT_EXIT, c.Encounter.FOLLOWED])
@pytest.mark.parametrize("fate", list(c.ToolFate))
def test_every_supported_root_allows_both_methods_and_encounters(premise, method, encounter, fate):
    kernel = k.KernelBuilder(42).build(premise)
    builder = c.CrimeBuilder(42)
    streets, inventory = builder.prepare(kernel)
    victim = next(p for p in kernel.world.people if p.id == kernel.roles.victim)
    # Construct an explicit authoring fixture with a nontrivial return route.
    exit = streets.path(victim.workplace.value, victim.home)[1]
    far_street = next(n.id for n in streets.nodes if n.kind is c.NodeKind.STREET and n.id != exit)
    streets = replace(streets, edges=tuple(replace(e, b=far_street) if e.a == victim.home else e
                                          for e in streets.edges))
    author = next(p for p in kernel.world.people if p.id == kernel.roles.author)
    inventory = tuple(t for t in inventory if t.owner != author.id) + tuple(
        c.Tool(f"test_{kind.value}", kind, author.id, author.home, -100, "usage domestique")
        for kind in c.ToolKind)
    crime = builder.execute(kernel, streets, inventory, method=method, encounter=encounter, fate=fate)
    assert crime.method is method and crime.execution.encounter is encounter
    assert crime.execution.tool_fate is fate
    assert any(t.kind is c.TraceKind.LEFT_TOOL for t in crime.traces) == (fate is c.ToolFate.LEFT_AT_SCENE)


def test_missing_method_is_rejected_without_inventing_tool_or_consuming_rng():
    crime = sample()
    inventory = tuple(t for t in crime.inventory
                      if t.owner != crime.kernel.roles.author or t.kind is not c.ToolKind.HAMMER)
    builder = c.CrimeBuilder(12)
    state, original = builder.rng.getstate(), crime.kernel.as_dict()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(crime.kernel, crime.streets, inventory, method=c.Method.BLUNT,
                        acquisition=c.AcquisitionKind.OWNED, mundane=False)
    assert builder.rng.getstate() == state and crime.kernel.as_dict() == original


def test_tools_preexist_selection_and_have_lawful_uses_for_innocents_too():
    crime = sample()
    assert {t.owner for t in crime.inventory} == {p.id for p in crime.kernel.world.people} | {"bar", "restaurant"}
    assert all(t.available_since < 0 and t.lawful_use for t in crime.inventory)
    by_person = {p.id: p for p in crime.kernel.world.people}
    assert all(t.place == by_person[t.owner].home for t in crime.inventory if t.owner in by_person)


def test_two_methods_four_outdoor_scenes_both_encounters_and_fates_are_sampled():
    crimes = [sample(seed) for seed in range(150)]
    assert {crime.method for crime in crimes} == {c.Method.EDGED, c.Method.BLUNT}
    assert {crime.scene for crime in crimes} == {"alley", "crime_scene", "victim_street", "promenade"}
    assert {crime.execution.encounter for crime in crimes} == {c.Encounter.AT_EXIT, c.Encounter.FOLLOWED}
    assert {crime.execution.tool_fate for crime in crimes} == set(c.ToolFate)


def test_author_actually_waits_then_follows_victim_no_unobserved_interception():
    crime = sample(7)
    x = crime.execution
    assert x.approach.times[-1] < x.observation_at
    assert x.following.times == x.victim_walk.times[1:]
    assert x.following.nodes == x.victim_walk.nodes[1:]
    assert x.approach.nodes[-1] == x.following.nodes[0]
    assert x.following.nodes[-1] == x.escape.nodes[0]
    assert x.escape.times[0] > x.death_at > x.attack_at


@pytest.mark.parametrize("field,value,message", [
    ("tool", "imaginary_weapon", "actual accessible tool"),
    ("method", "edged", "actual accessible tool"),
    ("acquired_at", -100, "acquired before departure"),
    ("acquired_at", 1439, "acquired before departure"),
    ("observation_at", 0, "observes victim"),
    ("attack_at", 0, "outdoor attack"),
    ("death_at", 1439, "resulting death"),
    ("encounter", "followed", "typed execution"),
    ("tool_fate", "retained", "typed execution"),
])
def test_false_execution_facts_are_rejected(field, value, message):
    with pytest.raises(c.InvalidCrime, match=message):
        altered(sample(), **{field: value})


def test_cannot_take_an_innocents_tool_without_access_and_transfer():
    crime = sample()
    tool = next(t for t in crime.inventory if t.owner != crime.kernel.roles.author)
    with pytest.raises(c.InvalidCrime, match="actual accessible tool"):
        altered(crime, tool=tool.id, method=c.METHOD_FOR_TOOL[tool.kind])


def test_unavailable_tool_and_false_home_are_rejected():
    crime = sample()
    for change in ({"available_since": 1440}, {"place": crime.scene}):
        inventory = tuple(replace(t, **change) if t.id == crime.execution.tool else t for t in crime.inventory)
        with pytest.raises(c.InvalidCrime, match="lawful tool"):
            replace(crime, inventory=inventory)


def test_tool_cannot_change_method_by_renaming_label():
    crime = sample()
    other = next(m for m in c.Method if m is not crime.method)
    with pytest.raises(c.InvalidCrime, match="actual accessible tool"):
        altered(crime, method=other)


def test_teleport_between_nonadjacent_streets_is_rejected():
    crime = sample()
    walk = c.Walk(crime.kernel.roles.author, ("alley", "victim_street"), (1000, 1001))
    with pytest.raises(c.InvalidCrime, match="teleport"):
        altered(crime, approach=walk)


def test_walking_times_and_actor_are_validated():
    crime = sample()
    walk = crime.execution.approach
    for bad, message in ((replace(walk, times=tuple(t + i for i, t in enumerate(walk.times))), "walking time"),
                         (replace(walk, person=crime.kernel.roles.victim), "actor walk")):
        with pytest.raises(c.InvalidCrime, match=message):
            altered(crime, approach=bad)


def test_author_cannot_arrive_after_the_observation():
    crime = sample()
    x = crime.execution
    late = replace(x.approach, times=tuple(t + 100 for t in x.approach.times))
    preparation = replace(x.preparation, times=tuple(t + 100 for t in x.preparation.times))
    with pytest.raises(c.InvalidCrime, match="observes victim"):
        altered(crime, approach=late, preparation=preparation, acquired_at=late.times[0] - 1)


def test_following_cannot_be_a_different_street_or_time():
    crime = sample()
    walk = crime.execution.following
    with pytest.raises(c.InvalidCrime, match="co-present"):
        altered(crime, following=replace(walk, times=tuple(t + 1 for t in walk.times)))


def test_victim_routine_does_not_continue_after_death():
    crime = sample()
    routine = crime.execution.intended_journey
    following = c.Walk(crime.kernel.roles.author, routine.nodes[1:], routine.times[1:])
    with pytest.raises(c.InvalidCrime, match="outdoor attack|encounter matches route"):
        altered(crime, victim_walk=routine, following=following, encounter=c.Encounter.FOLLOWED)


@pytest.mark.parametrize("change", [{"speaker": "unknown"}, {"recipient": "unknown"},
                                    {"relationship": "ordinary_romance"}, {"minute": 0}])
def test_author_cannot_know_victims_workplace_without_real_prior_information(change):
    crime = sample()
    with pytest.raises(c.InvalidCrime, match="prior disclosure"):
        replace(crime, workplace_disclosure=replace(crime.workplace_disclosure, **change))


def test_escape_cannot_start_before_death_or_from_a_different_place():
    crime = sample()
    escape = crime.execution.escape
    with pytest.raises(c.InvalidCrime, match="continuous escape"):
        altered(crime, escape=replace(escape, times=tuple(t - 5 for t in escape.times)))


@pytest.mark.parametrize("change", [{"place": "alley"}, {"created_at": 1},
                                    {"source": "nonexistent_camera"}, {"subject": "unknown"},
                                    {"detail": "empreinte du meurtrier"}])
def test_trace_provenance_place_time_origin_and_description_are_derived(change):
    crime = sample()
    trace = replace(crime.traces[0], **change)
    # Ensure the wrong place really is wrong, independently of sampled scene.
    if change == {"place": "alley"} and crime.scene == "alley":
        trace = replace(trace, place="promenade")
    with pytest.raises(c.InvalidCrime, match="derive exactly"):
        replace(crime, traces=(trace,) + crime.traces[1:])


def test_no_trace_can_be_added_or_removed_without_a_world_event():
    crime = sample()
    for traces in (crime.traces[1:], crime.traces + (crime.traces[0],)):
        with pytest.raises(c.InvalidCrime, match="derive exactly"):
            replace(crime, traces=traces)


def test_fate_changes_only_the_matching_physical_consequence():
    crime = sample()
    other = next(f for f in c.ToolFate if f is not crime.execution.tool_fate)
    x = replace(crime.execution, tool_fate=other,
                hidden_at=crime.execution.escape.nodes[-1] if other is c.ToolFate.HIDDEN else None)
    with pytest.raises(c.InvalidCrime, match="derive exactly"):
        replace(crime, execution=x)
    transfers, states, checks = c.tool_effects(crime.kernel, crime.inventory, x, crime.mundane_borrowings, crime.keepers)
    changed = replace(crime, execution=x, traces=c.consequences(crime.kernel, x),
                      transfers=transfers, tool_states=states, inventory_checks=checks)
    assert changed.traces[:3] == crime.traces[:3]


def test_map_rejects_disconnected_graph_duplicate_nodes_and_zero_time_edges():
    streets = sample().streets
    for change in ({"nodes": streets.nodes + (streets.nodes[0],)},
                   {"edges": tuple(e for e in streets.edges if streets.nodes[-1].id not in (e.a, e.b))},
                   {"edges": (replace(streets.edges[0], minutes=0),) + streets.edges[1:]}):
        with pytest.raises(c.InvalidCrime):
            replace(streets, **change)


def test_indoor_nodes_cannot_be_used_as_a_public_shortcut():
    streets = sample().streets
    with pytest.raises(c.InvalidCrime, match="street entrances"):
        replace(streets, edges=streets.edges + (c.Edge("bar", "promenade", 1),))


def test_shortest_path_uses_edge_durations_not_number_of_hops():
    streets = c.StreetMap(tuple(c.Node(id, c.NodeKind.STREET, id) for id in ("a", "b", "c")),
                         (c.Edge("a", "b", 12), c.Edge("a", "c", 2), c.Edge("c", "b", 2)))
    assert streets.path("a", "b") == ("a", "c", "b")


def test_infeasible_travel_is_rejected_before_rng_not_fixed_by_teleporting():
    crime = sample()
    streets = replace(crime.streets, edges=tuple(replace(e, minutes=1000) for e in crime.streets.edges))
    builder = c.CrimeBuilder(12)
    state = builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(crime.kernel, streets, crime.inventory)
    assert builder.rng.getstate() == state


def test_silencing_cannot_happen_after_the_planned_disclosure():
    premise = next(p for p in k.SUPPORTED_PREMISES if p.motive.value == "silence")
    kernel = k.KernelBuilder().build(premise)
    builder = c.CrimeBuilder(12)
    streets, inventory = builder.prepare(kernel)
    world = replace(kernel.world, disclosures=tuple(replace(d, scheduled_for=100) for d in kernel.world.disclosures))
    early = replace(kernel, world=world)
    state = builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(early, streets, inventory)
    assert builder.rng.getstate() == state


def test_invalid_choices_fail_before_build_rng_and_global_rng_stays_untouched():
    kernel = k.KernelBuilder().sample()
    builder = c.CrimeBuilder(15)
    state, global_state = builder.rng.getstate(), random.getstate()
    with pytest.raises(TypeError):
        builder.build(kernel, method="edged")
    assert builder.rng.getstate() == state
    builder.build(kernel)
    assert random.getstate() == global_state


def test_cli_step_five_delegates_without_enum_identity_bug_and_preserves_step_four():
    args = ["--seed", "7", "--count", "2", "--motive", "control", "--context", "romance", "--json"]
    direct = subprocess.check_output([sys.executable, "scenario_crime.py", *args], cwd=ROOT)
    wrapped = subprocess.check_output([sys.executable, "scenario_sampler.py", "--step", "5", *args], cwd=ROOT)
    assert direct == wrapped
    rows = json.loads(direct)
    assert len(rows) == 2 and all(row["visibility"] == "private_executed_truth" for row in rows)
    earlier = subprocess.check_output([sys.executable, "scenario_sampler.py", "--step", "4", *args], cwd=ROOT)
    assert all(row["method"] is None for row in json.loads(earlier))


def test_cli_reproducible_across_python_hash_seeds():
    args = [sys.executable, "scenario_crime.py", "--seed", "42", "--count", "3", "--json"]
    outputs = [subprocess.check_output(args, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": seed})
               for seed in ("1", "134", "random")]
    assert len(set(outputs)) == 1


def test_cli_unsupported_root_is_an_explicit_failure_not_generic_story():
    result = subprocess.run([sys.executable, "scenario_sampler.py", "--step", "5", "--motive", "predation"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0 and "No implemented kernel" in result.stderr
