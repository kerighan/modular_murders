"""Victim goals must have true causes, destinations and epistemic boundaries."""
import json
import os
import random
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import scenario_crime as c
import scenario_kernel as k
import scenario_victim as v
from scenario_sampler import CrimePremise, Context, Motive, Stake


ROOT = Path(__file__).resolve().parents[1]
CONTROL = CrimePremise(Motive.CONTROL, Context.ROMANCE, Stake.SEPARATION)
FRAUD = CrimePremise(Motive.SILENCE, Context.WORK, Stake.FRAUD)
EXPLOITATION = CrimePremise(Motive.SILENCE, Context.WORK, Stake.EXPLOITATION)


def kernel(premise=CONTROL, seed=42):
    return k.KernelBuilder(seed).build(premise)


def plan_for(world, goal=v.VictimGoal.MEET_PERSON, reason=None):
    return next(plan for plan in v.candidate_plans(world, goal=goal)
                if reason is None or plan.reason is reason)


def meeting_changes(plan, **changes):
    return replace(plan, appointment=replace(plan.appointment, **changes))


@pytest.mark.parametrize("premise", k.SUPPORTED_PREMISES)
def test_goal_domains_expand_only_from_actual_supported_facts(premise):
    world = kernel(premise)
    global_state, original = random.getstate(), world.as_dict()
    plans = v.candidate_plans(world)
    assert plans == v.candidate_plans(world)
    assert {p.goal for p in plans} == set(v.allowed_goals(premise))
    assert all(v.validate_plan(world, p) is p for p in plans)
    assert world.as_dict() == original and random.getstate() == global_state
    assert all("decision" not in p.sources and
               (world.roles.author in p.informed_people) == (p.goal is v.VictimGoal.MEET_AUTHOR) for p in plans)
    assert not {"guilty", "murderer", "candidates", "death"} & v.MissedAppointment.__dataclass_fields__.keys()


@pytest.mark.parametrize("premise", k.SUPPORTED_PREMISES)
@pytest.mark.parametrize("goal", list(v.VictimGoal))
def test_all_compatible_goals_execute_with_exact_destination_and_existing_truth(premise, goal):
    for seed in range(10):
        world = kernel(premise, seed)
        original = world.as_dict()
        builder = c.CrimeBuilder(seed)
        if goal not in v.allowed_goals(premise):
            streets, inventory = builder.prepare(world)
            state = builder.rng.getstate()
            with pytest.raises(c.NoFeasibleCrime):
                builder.execute(world, streets, inventory, goal=goal)
            assert state == builder.rng.getstate()
            continue
        crime = builder.build(world, goal=goal)
        assert crime.victim_plan.goal is goal
        assert crime.kernel is world and world.as_dict() == original
        assert crime.execution.intended_journey.nodes[-1] == crime.victim_plan.destination
        assert crime.execution.intended_journey.times[-1] == crime.victim_plan.expected_arrival_at
        assert (crime.execution.victim_walk.nodes[-1] == crime.victim_plan.destination) == (goal in (v.VictimGoal.MEET_AUTHOR, v.VictimGoal.GO_OUT))
        assert (len(crime.missed_appointments) == 1) == (goal is v.VictimGoal.MEET_PERSON)


def test_social_meal_is_independent_of_the_crime_and_support_has_a_real_cause():
    world = kernel()
    meal = plan_for(world, reason=v.PlanReason.SHARED_MEAL)
    support = plan_for(world, reason=v.PlanReason.SEEK_SUPPORT)
    assert meal.sources == ("victim_friend",)
    assert support.sources == ("victim_friend", "autonomy")
    assert meal.destination == support.destination
    assert support.formed_at > next(e.minute for e in world.world.events if e.id == "autonomy")
    assert "séparation" in v.purpose_text(support, {p.id: p for p in world.world.people}, world)


def test_no_family_or_friendship_is_invented_for_colleagues():
    world = kernel(FRAUD)
    # No ordinary romance in this explicit coworkers-only fixture. Other worlds
    # legitimately let the victim dine with their independently authored partner.
    world = replace(world, world=replace(world.world, relationships=tuple(
        r for r in world.world.relationships if not r.id.startswith("background_"))))
    plan = plan_for(world)
    assert plan.reason is v.PlanReason.SHARED_MEAL and plan.sources == ("disclosure",)
    assert not any(p.reason is v.PlanReason.SEEK_SUPPORT for p in v.candidate_plans(world))


def test_no_invented_police_appointment_or_replacement_of_previous_disclosure():
    world = kernel(FRAUD)
    before = world.world.disclosures
    crime = c.CrimeBuilder(12).build(world, goal=v.VictimGoal.REPORT_INCIDENT)
    assert crime.victim_plan.appointment is None and crime.missed_appointments == ()
    assert world.world.disclosures == before
    assert all(d.scheduled_for >= k.DAY for d in before)
    assert crime.victim_plan.expected_arrival_at < k.DAY
    assert crime.victim_plan.sources == (world.world.incidents[0].id, world.world.knowledge[0].learned_by)
    assert "rémunération" in c.describe(crime)


def test_police_destination_does_not_force_crime_at_police_door():
    worlds = (kernel(FRAUD, seed=seed) for seed in range(20))
    world = next(world for world in worlds if next(p.workplace for p in world.world.people
                 if p.id == world.roles.victim) is not k.Workplace.VIDEO)
    crimes = [c.CrimeBuilder(seed).build(world, goal=v.VictimGoal.REPORT_INCIDENT) for seed in range(40)]
    assert any(crime.scene == "promenade" for crime in crimes)
    assert any(crime.scene != "promenade" for crime in crimes)
    assert all(crime.victim_plan.destination == "police" for crime in crimes)


def test_shared_exit_and_police_entrance_can_have_only_one_outdoor_crime_point():
    worlds = (kernel(FRAUD, seed=seed) for seed in range(20))
    world = next(world for world in worlds if next(p.workplace for p in world.world.people
                 if p.id == world.roles.victim) is k.Workplace.VIDEO)
    crime = c.CrimeBuilder(7).build(world, goal=v.VictimGoal.REPORT_INCIDENT)
    assert crime.execution.intended_journey.nodes == ("cctv", "promenade", "police")
    assert crime.scene == "promenade" and crime.execution.encounter is c.Encounter.AT_EXIT
    builder = c.CrimeBuilder(7)
    streets, inventory = builder.prepare(world)
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(world, streets, inventory, goal=v.VictimGoal.REPORT_INCIDENT,
                        encounter=c.Encounter.FOLLOWED)


def test_appointment_has_only_informed_participants_and_a_present_waiting_host():
    world = kernel()
    crime = c.CrimeBuilder(7).build(world, goal=v.VictimGoal.MEET_PERSON)
    plan, missed = crime.victim_plan, crime.missed_appointments[0]
    meeting = plan.appointment
    assert plan.informed_people == (world.roles.victim, meeting.host)
    assert meeting.host_present_from <= meeting.starts_at < missed.observed_at <= meeting.host_present_until
    assert missed.observer == meeting.host and missed.visitor == world.roles.victim
    assert missed.place == meeting.place and missed.appointment == meeting.id
    assert missed.observed_at > crime.execution.death_at
    text = v.absence_text(plan, {p.id: p for p in world.world.people})
    assert "J'ai attendu" in text
    assert not any(word in text for word in ("tué", "tueur", "meurtre", "police", "horaires à vérifier"))
    assert next(p.name for p in world.world.people if p.id == world.roles.author) not in text


def test_death_at_exact_appointment_time_still_produces_nonarrival():
    world = kernel()
    plan = plan_for(world)
    death = plan.expected_arrival_at
    walk = c.Walk(world.roles.victim, ("alley",), (death - 1,))
    missing = v.missed_appointments(plan, walk, death)
    assert len(missing) == 1 and missing[0].observed_at == death + 15
    reached = c.Walk(world.roles.victim, (plan.destination,), (death - 1,))
    assert v.missed_appointments(plan, reached, death) == ()
    assert v.missed_appointments(plan, walk, death + 16) == ()


@pytest.mark.parametrize("changes,message", [
    ({"person": "unknown"}, "actual victim"),
    ({"origin": "police"}, "actual victim"),
    ({"goal": "meet_person"}, "actual victim"),
    ({"reason": "shared_meal"}, "actual victim"),
    ({"expected_arrival_at": True}, "chronology"),
    ({"formed_at": 1439}, "chronology"),
    ({"sources": ["victim_friend"]}, "immutable"),
    ({"sources": ("ordinary_friendship",)}, "real acquaintance"),
    ({"informed_people": ("unknown",)}, "known contact"),
    ({"destination": "police"}, "home destination"),
    ({"appointment": None}, "appointment host"),
])
def test_bad_meeting_plans_are_rejected(changes, message):
    world = kernel()
    with pytest.raises(v.InvalidVictimPlan, match=message):
        v.validate_plan(world, replace(plan_for(world), **changes))


@pytest.mark.parametrize("changes,message", [
    ({"host": "unknown"}, "appointment host"),
    ({"visitor": "unknown"}, "appointment host"),
    ({"place": "police"}, "home destination"),
    ({"agreed_at": 1439}, "host actually present"),
    ({"starts_at": 0}, "host actually present"),
    ({"host_present_from": 1439}, "host actually present"),
    ({"host_present_until": 0}, "host actually present"),
])
def test_host_and_agreement_schedule_cannot_be_faked(changes, message):
    world = kernel()
    with pytest.raises(v.InvalidVictimPlan, match=message):
        v.validate_plan(world, meeting_changes(plan_for(world), **changes))


def test_author_cannot_be_relabelled_as_the_waiting_friend():
    world = kernel()
    with pytest.raises(v.InvalidVictimPlan, match="appointment host"):
        v.validate_plan(world, meeting_changes(plan_for(world), host=world.roles.author))


def test_unrelated_same_employer_does_not_create_a_social_contact():
    world = kernel(FRAUD)
    victim = next(p for p in world.world.people if p.id == world.roles.victim)
    other = next(p for p in world.world.people if p.id not in (world.roles.author, world.roles.victim, world.roles.other))
    people = tuple(replace(p, workplace=victim.workplace, occupation=k.JOBS[victim.workplace][0])
                   if p.id == other.id else p for p in world.world.people)
    world = replace(world, world=replace(world.world, people=people))
    assert v.contact_basis(world, other.id) is None
    assert all(plan.appointment is None or plan.appointment.host != other.id for plan in v.candidate_plans(world))


def test_support_cannot_precede_the_true_conflict():
    world = kernel()
    plan = plan_for(world, reason=v.PlanReason.SEEK_SUPPORT)
    earlier = next(e.minute for e in world.world.events if e.id == "autonomy") - 1
    plan = replace(plan, formed_at=earlier, appointment=replace(plan.appointment, agreed_at=earlier))
    with pytest.raises(v.InvalidVictimPlan, match="support follows"):
        v.validate_plan(world, plan)


def test_meal_agreement_cannot_precede_friendship():
    world = kernel()
    plan = plan_for(world)
    earlier = next(r.since for r in world.world.relationships if r.id == "victim_friend") - 1
    plan = replace(plan, formed_at=earlier, appointment=replace(plan.appointment, agreed_at=earlier))
    with pytest.raises(v.InvalidVictimPlan, match="contact established"):
        v.validate_plan(world, plan)


def test_police_report_requires_actual_victim_knowledge_and_allowed_incident():
    world = kernel(FRAUD)
    plan = plan_for(world, v.VictimGoal.REPORT_INCIDENT)
    for changes in ({"sources": ("fake_incident", "discovery")}, {"formed_at": -1000 * k.DAY}):
        with pytest.raises(v.InvalidVictimPlan, match="actually known|knowledge precedes"):
            v.validate_plan(world, replace(plan, **changes))
    assert v.candidate_plans(kernel(EXPLOITATION), goal=v.VictimGoal.REPORT_INCIDENT) == ()
    assert v.candidate_plans(kernel(), goal=v.VictimGoal.REPORT_INCIDENT) == ()


def test_returning_home_cannot_invent_an_appointment_or_use_somebody_elses_home():
    world = kernel()
    home = plan_for(world, v.VictimGoal.RETURN_HOME)
    for changes in ({"destination": "police"}, {"appointment": plan_for(world).appointment}):
        with pytest.raises(v.InvalidVictimPlan, match="ordinary home goal"):
            v.validate_plan(world, replace(home, **changes))


def test_goal_and_pinned_plan_conflict_is_rejected_without_rng_or_truth_changes():
    world = kernel()
    builder = c.CrimeBuilder(7)
    streets, inventory = builder.prepare(world)
    plan = plan_for(world)
    original, state = world.as_dict(), builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime, match="conflicts"):
        builder.execute(world, streets, inventory, plan=plan, goal=v.VictimGoal.RETURN_HOME)
    assert builder.rng.getstate() == state and world.as_dict() == original


def test_pinned_plan_is_preserved_not_moved_to_an_easier_place_or_time():
    world = kernel()
    builder = c.CrimeBuilder(7)
    streets, inventory = builder.prepare(world)
    plan = plan_for(world)
    crime = builder.execute(world, streets, inventory, plan=plan)
    assert crime.victim_plan is plan
    assert crime.execution.intended_journey.nodes[-1] == plan.destination
    assert crime.execution.intended_journey.times[-1] == plan.expected_arrival_at
    too_late = replace(plan, formed_at=plan.expected_arrival_at - 1,
                       appointment=replace(plan.appointment, agreed_at=plan.expected_arrival_at - 1))
    state = builder.rng.getstate()
    with pytest.raises(c.NoFeasibleCrime):
        builder.execute(world, streets, inventory, plan=too_late)
    assert builder.rng.getstate() == state


def test_journey_cannot_be_changed_without_updating_the_victim_plan():
    world = kernel()
    crime = c.CrimeBuilder(7).build(world, goal=v.VictimGoal.MEET_PERSON)
    route = crime.execution.intended_journey
    late = replace(route, times=tuple(t + 10 for t in route.times))
    with pytest.raises(c.InvalidCrime, match="serves the victim plan"):
        replace(crime, execution=replace(crime.execution, intended_journey=late))


def test_missed_meeting_cannot_be_added_removed_or_attributed_to_someone_else():
    world = kernel()
    crime = c.CrimeBuilder(7).build(world, goal=v.VictimGoal.MEET_PERSON)
    missed = crime.missed_appointments[0]
    for wrong in ((), (replace(missed, observer=world.roles.author),), (replace(missed, observed_at=0),)):
        with pytest.raises(c.InvalidCrime, match="missed appointment derives"):
            replace(crime, missed_appointments=wrong)
    home = c.CrimeBuilder(7).build(world, goal=v.VictimGoal.RETURN_HOME)
    with pytest.raises(c.InvalidCrime, match="missed appointment derives"):
        replace(home, missed_appointments=(missed,))


def test_immutable_plans_and_invalid_goal_types_do_not_consume_rng():
    world = kernel()
    with pytest.raises(FrozenInstanceError):
        plan_for(world).destination = "police"
    builder = c.CrimeBuilder(7)
    state = builder.rng.getstate()
    with pytest.raises(TypeError):
        builder.build(world, goal="return_home")
    assert state == builder.rng.getstate()


def run_cli(*args):
    return subprocess.run([sys.executable, "scenario_sampler.py", *args], cwd=ROOT,
                          capture_output=True, text=True)


@pytest.mark.parametrize("goal", list(v.VictimGoal))
def test_cli_goal_filters_and_wrapper_produce_valid_private_json(goal):
    args = ["--seed", "7", "--count", "5", "--goal", goal.value, "--json"]
    result = run_cli("--step", "5", *args)
    assert result.returncode == 0, result.stderr
    direct = subprocess.check_output([sys.executable, "scenario_crime.py", *args], cwd=ROOT, text=True)
    assert result.stdout == direct
    rows = json.loads(result.stdout)
    assert len(rows) == 5
    assert all(row["victim_plan"]["goal"] == goal.value and row["crime_version"] == 4 for row in rows)
    assert all(row["visibility"] == "private_executed_truth" for row in rows)


def test_cli_police_filter_restricts_root_before_sampling_instead_of_random_failure():
    result = run_cli("--step", "5", "--seed", "0", "--count", "20", "--goal", "report_incident", "--json")
    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)
    assert all(row["kernel"]["premise"]["motive"] == "silence" for row in rows)
    assert {row["kernel"]["premise"]["stake"] for row in rows} == {"fraud", "past_crime"}


@pytest.mark.parametrize("args", [
    ("--step", "4", "--goal", "meet_person"),
    ("--step", "5", "--motive", "control", "--goal", "report_incident"),
    ("--step", "5", "--stake", "exploitation", "--goal", "report_incident", "--catalogue"),
])
def test_cli_contradictory_filters_fail_explicitly(args):
    assert run_cli(*args).returncode != 0


def test_goal_cli_reproducible_across_process_hash_seeds_and_catalogue_consistent():
    args = [sys.executable, "scenario_crime.py", "--seed", "7", "--count", "3", "--goal", "meet_person", "--json"]
    outputs = [subprocess.check_output(args, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": seed}) for seed in ("1", "42")]
    assert outputs[0] == outputs[1]
    result = run_cli("--step", "5", "--motive", "control", "--catalogue")
    assert json.loads(result.stdout)["goals"] == ["return_home", "meet_person", "meet_author", "go_out"]
