"""Triangles are facts, meetings have agreements, poisoning changes consequences."""
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import scenario_crime as c
import scenario_kernel as k
from scenario_diversity import audit
from scenario_sampler import Context, CrimePremise, Motive, Stake
from scenario_situations import SituationKind as S, venue_observations
from scenario_victim import VictimGoal as G, candidate_plans

ROOT = Path(__file__).resolve().parents[1]
TRIANGLE = CrimePremise(Motive.REMOVE_OBSTACLE, Context.ROMANCE, Stake.ROMANTIC_RIVAL)


def setup(premise=TRIANGLE, seed=42):
    world = k.KernelBuilder(seed).build(premise)
    builder = c.CrimeBuilder(seed)
    streets, inventory = builder.prepare(world)
    author = next(p for p in world.world.people if p.id == world.roles.author)
    inventory = tuple(t for t in inventory if t.owner != author.id) + tuple(
        c.Tool(f"fixture_{kind.value}", kind, author.id, author.home, -100, "usage domestique fictif")
        for kind in c.ToolKind)
    return world, builder, streets, inventory


def poisoned(premise=TRIANGLE, venue="restaurant", acquisition=c.AcquisitionKind.TAKEN,
             fate=c.ToolFate.RETAINED):
    world, builder, streets, inventory = setup(premise)
    plan = next(p for p in candidate_plans(world, goal=G.GO_OUT) if p.destination == venue)
    return builder.execute(world, streets, inventory, plan=plan, situation=S.VENUE,
        method=c.Method.POISONED, acquisition=acquisition, fate=fate, mundane=False,
        source_place="home" if acquisition is c.AcquisitionKind.OWNED else venue)


def test_triangle_is_three_bound_people_with_actual_relationships_and_knowledge():
    world = k.KernelBuilder(7).build(TRIANGLE)
    a, v, other = world.roles.author, world.roles.victim, world.roles.other
    assert world.intent.goal is k.GoalKind.REMOVE_ROMANTIC_RIVAL
    assert world.intent.expected_effect is k.ExpectedEffect.DEATH_REMOVES_RIVAL
    assert k.link_to_victim(world, other) == ("partner",)
    assert k.link_to_victim(world, a) == ("acquaintances",)
    assert world.world.incidents == world.world.dependencies == ()
    assert k.romantic_triangles(world.world)
    assert {w.requirement for w in k.validate_kernel(world)} == set(TRIANGLE.required_facts)


@pytest.mark.parametrize("relation,change", [
    ("former_couple", {"until": None}),
    ("former_couple", {"until": -10 * k.DAY}),
    ("current_couple", {"people": ("p0", "p0")}),
    ("current_couple", {"since": -1}),
])
def test_triangle_rejects_wrong_participants_unended_couple_and_undisclosed_relationship(relation, change):
    world = k.KernelBuilder(42).build(TRIANGLE)
    with pytest.raises(k.InvalidKernel):
        replace(world, world=replace(world.world, relationships=tuple(
            replace(r, **change) if r.id == relation else r for r in world.world.relationships)))


def test_current_partner_can_belong_to_a_triangle_without_any_killer_connection():
    found, absent = [], []
    premise = k.SUPPORTED_PREMISES[0]
    for seed in range(30):
        world = k.KernelBuilder(seed).build(premise)
        couples = {r.id: r for r in world.world.relationships}
        triangles = [set(couples[former].people) | set(couples[current].people)
                     for center, former, current in k.romantic_triangles(world.world)]
        innocents = [actors for actors in triangles if world.roles.victim in actors
                     and world.roles.author not in actors]
        (found if innocents else absent).append(world)
        if innocents:
            assert world.world.rivalries == () and world.intent.goal is k.GoalKind.STOP_DISCLOSURE
            assert "partner" in k.link_to_victim(world, world.roles.other)
    assert found and absent  # Optional life event, never a permanent red herring.


@pytest.mark.parametrize("premise", k.SUPPORTED_PREMISES)
@pytest.mark.parametrize("method", [c.Method.EDGED, c.Method.BLUNT])
@pytest.mark.parametrize("fate", list(c.ToolFate))
def test_agreed_meetings_start_at_home_and_do_not_require_workplace_surveillance(premise, method, fate):
    world, builder, streets, inventory = setup(premise)
    crime = builder.execute(world, streets, inventory, situation=S.AGREED_MEETING,
                           method=method, fate=fate, acquisition=c.AcquisitionKind.OWNED, mundane=False)
    x, plan = crime.execution, crime.victim_plan
    victim = next(p for p in world.world.people if p.id == world.roles.victim)
    assert plan.origin == victim.home and plan.goal is G.MEET_AUTHOR
    assert plan.informed_people == (world.roles.victim, world.roles.author)
    assert crime.workplace_disclosure is None and crime.missed_appointments == ()
    assert x.victim_walk == x.intended_journey and len(x.following.nodes) == 1
    assert x.attack_at > plan.expected_arrival_at and x.method is method
    assert c.validate_crime(crime) is crime


@pytest.mark.parametrize("premise", k.SUPPORTED_PREMISES)
@pytest.mark.parametrize("venue", ["bar", "restaurant"])
@pytest.mark.parametrize("acquisition", list(c.AcquisitionKind))
@pytest.mark.parametrize("fate", list(c.ToolFate))
def test_poisoned_venue_has_no_blood_and_real_ambiguous_access(premise, venue, acquisition, fate):
    crime = poisoned(premise, venue, acquisition, fate)
    x = crime.execution
    assert crime.scene == venue and crime.method is c.Method.POISONED
    assert c.TraceKind.VICTIM_BLOOD not in {t.kind for t in crime.traces}
    assert c.TraceKind.METHOD_MARK not in {t.kind for t in crime.traces}
    assert {c.TraceKind.DRINK, c.TraceKind.TOXIC_EFFECT} <= {t.kind for t in crime.traces}
    assert x.exposure.served_at < x.attack_at < x.death_at
    assert x.escape.times[0] < x.death_at
    assert len(x.exposure.access_people) == 2 and len(crime.venue_presences) == 2
    assert crime.kernel.roles.author in x.exposure.access_people
    assert all(p.arrival.times[-1] <= x.attack_at <= p.until for p in crime.venue_presences)
    assert crime.workplace_disclosure is None
    assert c.validate_crime(crime) is crime


@pytest.mark.parametrize("change", [
    {"served_by": "imaginary_server"}, {"served_at": 0}, {"altered_at": 0},
    {"effect_at": 0}, {"recipient": "unknown"}, {"access_people": ("p0",)},
])
def test_forged_drink_exposure_is_rejected(change):
    crime = poisoned()
    with pytest.raises(c.InvalidCrime):
        replace(crime, execution=replace(crime.execution, exposure=replace(crime.execution.exposure, **change)))


def test_drink_access_holder_cannot_be_teleported_or_leave_before_the_event():
    crime = poisoned()
    other = crime.venue_presences[1]
    with pytest.raises(c.InvalidCrime):
        replace(crime, venue_presences=(crime.venue_presences[0], replace(other, until=crime.execution.attack_at - 1)))
    with pytest.raises(c.InvalidCrime):
        replace(crime, venue_presences=crime.venue_presences[:1])


def test_poisoning_cannot_inherit_a_blood_trace_from_another_method():
    crime = poisoned()
    blood = c.Trace("blood", c.TraceKind.VICTIM_BLOOD, crime.scene, crime.execution.attack_at,
                    "attack", crime.kernel.roles.victim, "sang")
    with pytest.raises(c.InvalidCrime, match="consequences"):
        replace(crime, traces=crime.traces + (blood,))


def test_public_drink_artifact_does_not_reveal_method_perpetrator_or_exact_times():
    crime = poisoned()
    assert venue_observations(crime, place="bar", discovered_at=1440) == ()
    assert venue_observations(crime, place=crime.scene, discovered_at=crime.execution.death_at - 1) == ()
    row, = venue_observations(crime, place=crime.scene, discovered_at=crime.execution.death_at)
    assert len(row["candidates"]) == 2 and row["interpretation"] == "lead_not_proof"
    assert not {"author", "method", "actor", "tool", "altered_at", "effect_at", "access_people"} & row.keys()
    assert "empoison" not in row["text"] and "analyse" not in row["text"]


def test_forced_poisoning_outside_a_venue_fails_before_rng():
    world, builder, streets, inventory = setup()
    before = builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(world, streets, inventory, situation=S.TRACKING, method=c.Method.POISONED)
    assert builder.rng.getstate() == before


def test_structural_audit_has_three_families_without_a_dominant_work_exit():
    result = audit(120, 0)
    assert set(result["situations"]) == {s.value for s in S}
    assert result["largest_situation_fraction"] < .55
    assert result["structural_fingerprints"] > 30
    assert result["cases_with_victim_triangle_without_killer"] > 0
    assert "solvability" in result["note"]


def test_cli_can_force_triangle_poisoning_and_redact_scene():
    args = ["--seed", "42", "--motive", "remove_obstacle", "--context", "romance",
            "--stake", "romantic_rival", "--method", "poisoned", "--public-scene"]
    direct = subprocess.check_output([sys.executable, "scenario_crime.py", *args], cwd=ROOT)
    wrapped = subprocess.check_output([sys.executable, "scenario_sampler.py", "--step", "5", *args], cwd=ROOT)
    assert direct == wrapped
    row, = json.loads(direct)
    assert row["visibility"] == "public_scene_preview" and len(row["observations"][0]["candidates"]) >= 2


def test_live_partner_trait_has_labels_dialogue_and_no_automatic_grudge():
    from city import LINK_QUOTES, LINK_SENTENCE, TRAIT_TEXT
    from genotype import LinkToVictim, TRAITS
    from game import GRUDGE
    partner = LinkToVictim.PARTNER
    assert len(TRAITS[LinkToVictim][1]) == len(LinkToVictim)
    assert partner in LINK_QUOTES and partner in LINK_SENTENCE and partner in TRAIT_TEXT
    assert partner not in GRUDGE
