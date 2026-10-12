import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from scenario_crime import CrimeBuilder, TraceKind
from scenario_kernel import KernelBuilder, SUPPORTED_PREMISES
from scenario_means import Method
from scenario_observations import (Artifact, DiscoveryState, UnavailableAction,
                                   project, walkthrough)
from scenario_situations import SituationKind


ROOT = Path(__file__).resolve().parents[1]


def make(seed=42, **choices):
    kernel = KernelBuilder(seed).sample()
    return CrimeBuilder(f"physical-v4:{seed}").build(kernel, **choices)


@pytest.mark.parametrize("seed", range(100))
def test_projection_is_reachable_ambiguous_and_never_changes_truth(seed):
    crime = make(seed)
    before = crime.as_dict()
    plan = project(crime)
    result = walkthrough(plan)
    assert result["audit"]["artifacts_acquired"] == len(plan.artifacts)
    assert all(crime.kernel.roles.author in a.candidates and len(a.candidates) >= 2 for a in plan.artifacts)
    # These sources describe methods/stock, NOT who actually carried out a crime.
    assert result["audit"]["remaining_count"] >= 2
    assert not result["audit"]["unique_deduction"]
    assert before == crime.as_dict()
    expected = {t.id for t in crime.traces} | {c.id for c in crime.inventory_checks}
    assert all(set(a.sources) <= expected for a in plan.artifacts)


@pytest.mark.parametrize("premise", SUPPORTED_PREMISES)
@pytest.mark.parametrize("situation", list(SituationKind))
def test_all_causal_roots_and_situations_have_obtainable_content(premise, situation):
    kernel = KernelBuilder(42).build(premise)
    crime = CrimeBuilder("physical-v4:42").build(kernel, situation=situation)
    plan = project(crime)
    assert walkthrough(plan)["audit"]["artifacts_acquired"] == len(plan.artifacts)
    assert all(a.actor.startswith(("fixture:", "staff:")) for a in plan.actions)


def test_samples_are_real_prerequisites_and_results_wait_for_collection():
    crime = make(method=Method.POISONED)
    plan = project(crime)
    empty, at = DiscoveryState(), 1440 + 8 * 60
    assert not plan.available(empty, place="lab", at=at)
    with pytest.raises(UnavailableAction):
        plan.perform(empty, "analyze_drink", place="lab", at=at)
    state, _ = plan.perform(empty, "inspect_scene", place=crime.scene, at=at)
    state, received = plan.perform(state, "collect_drink", place=crime.scene, at=at)
    assert "substance" not in received[0]["text"] and "candidates" not in received[0]
    with pytest.raises(UnavailableAction):
        plan.perform(state, "analyze_drink", place="lab", at=at + 29)
    with pytest.raises(UnavailableAction):
        plan.perform(state, "analyze_drink", place=crime.scene, at=at + 30)
    state, received = plan.perform(state, "analyze_drink", place="lab", at=at + 30)
    assert "substance toxique" in received[0]["text"]
    assert "fictive" not in received[0]["text"]
    with pytest.raises(UnavailableAction):
        plan.perform(state, "analyze_drink", place="lab", at=at + 60)


def test_medical_report_waits_from_actual_request_not_hidden_death():
    crime, now = make(), 3 * 1440
    plan = project(crime)
    state, _ = plan.perform(DiscoveryState(), "inspect_scene", place=crime.scene, at=now)
    state, _ = plan.perform(state, "request_exam", place=crime.scene, at=now)
    with pytest.raises(UnavailableAction):
        plan.perform(state, "read_medical", place="morgue", at=now + 59)
    state, report = plan.perform(state, "read_medical", place="morgue", at=now + 60)
    assert report[0]["id"] == "medical_report"


def test_blood_comparison_cannot_identify_victim_without_a_body_reference():
    crime, now = make(method=Method.BLUNT), 1440 + 8 * 60
    plan = project(crime)
    state, _ = plan.perform(DiscoveryState(), "inspect_scene", place=crime.scene, at=now)
    state, _ = plan.perform(state, "collect_blood", place=crime.scene, at=now)
    with pytest.raises(UnavailableAction):
        plan.perform(state, "analyze_blood", place="lab", at=now + 500)
    state, _ = plan.perform(state, "request_exam", place=crime.scene, at=now)
    state, _ = plan.perform(state, "read_medical", place="morgue", at=now + 60)
    with pytest.raises(UnavailableAction):
        plan.perform(state, "analyze_blood", place="lab", at=now + 89)
    _, result = plan.perform(state, "analyze_blood", place="lab", at=now + 90)
    assert "correspond" in result[0]["text"]


def test_existing_solver_can_read_new_sources_but_does_not_invent_a_solution():
    from investigation_solver import InvestigationSolver
    plan = project(make(method=Method.POISONED))
    solver = InvestigationSolver(plan.graph(), plan.solver_actions())
    assert solver.minimal_proofs() == []
    result = solver.audit()
    assert result["minimum_cost"] is None


def test_no_diagnosis_from_glass_and_no_blood_in_poison_projection():
    crime = make(method=Method.POISONED)
    plan = project(crime)
    assert not any("blood" in a.id for a in plan.artifacts)
    assert TraceKind.VICTIM_BLOOD not in {t.kind for t in crime.traces}
    for key in ("scene_body", "drink_sample"):
        artifact = next(a for a in plan.artifacts if a.id == key)
        assert not any(word in artifact.text.lower() for word in ("empoison", "intoxication", "altér"))
        assert artifact.candidates == plan.population  # Private presence is NOT a testimony.


def test_stock_requires_a_real_present_keeper_and_does_not_name_the_taker():
    crime = make(seed=42, method=Method.POISONED)
    plan = project(crime)
    action = next(a for a in plan.actions if a.id.startswith("ask:"))
    assert plan.next_time(action, DiscoveryState()) == 1440 + 8 * 60
    with pytest.raises(UnavailableAction):
        plan.perform(DiscoveryState(), action.id, place=action.place, at=2 * 1440)
    _, rows = plan.perform(DiscoveryState(), action.id, place=action.place, at=1440 + 8 * 60)
    assert set(rows[0]) == {"id", "kind", "text"}
    assert not any(p.name in rows[0]["text"] for p in crime.kernel.world.people)


def test_public_payload_has_no_private_ids_supports_source_or_exact_crime_time():
    crime = make(method=Method.POISONED)
    plan = project(crime)
    exported = plan.public_catalogue()
    assert "available_at" not in json.dumps(exported)
    for artifact in exported["artifacts"]:
        assert set(artifact) == {"id", "kind", "text"}
    text = json.dumps(exported)
    assert crime.execution.tool not in text and "candidates" not in text and "sources" not in text
    assert crime.kernel.roles.author not in text
    assert str(crime.execution.attack_at) not in text


def test_singular_whole_artifact_and_singular_one_tap_bundle_are_rejected():
    plan = project(make())
    person, second, third = sorted(plan.population)[:3]
    with pytest.raises(ValueError, match="at least two"):
        replace(plan, artifacts=(replace(plan.artifacts[0], candidates=frozenset((person,))),) + plan.artifacts[1:])
    first = replace(plan.artifacts[0], candidates=frozenset((person, second)))
    other = Artifact("extra", "example", "Autre paragraphe", first.sources, frozenset((person, third)))
    with pytest.raises(ValueError, match="bundle"):
        replace(plan, artifacts=(first,) + plan.artifacts[1:] + (other,), actions=(
            replace(plan.actions[0], reveals=(first.id, other.id)),) + plan.actions[1:])


def test_forged_sources_and_cycles_are_rejected():
    plan = project(make())
    with pytest.raises(ValueError, match="real sources"):
        replace(plan, artifacts=(replace(plan.artifacts[0], sources=("invented",)),) + plan.artifacts[1:])
    with pytest.raises(ValueError, match="Cyclic"):
        replace(plan, actions=(replace(plan.actions[0], requires=plan.actions[0].reveals),) + plan.actions[1:])
    with pytest.raises(ValueError, match="Knowledge"):
        plan.available(DiscoveryState((("scene_body", 0),)), place="lab", at=100)
    with pytest.raises(ValueError, match="prerequisites"):
        medical = next(a for a in plan.actions if a.id == "read_medical")
        plan.available(DiscoveryState(tuple((key, 2000) for key in medical.reveals), ("read_medical",)), place="lab", at=3000)


def test_forged_completed_analysis_cannot_bypass_processing_delay():
    crime = make(method=Method.POISONED)
    plan = project(crime)
    now = 1440 + 8 * 60
    forged = DiscoveryState((("scene_body", now), ("drink_sample", now), ("drink_result", now)),
                            ("inspect_scene", "collect_drink", "analyze_drink"))
    with pytest.raises(ValueError, match="processing"):
        plan.available(forged, place="lab", at=now + 30)


def test_runtime_rejects_future_and_noninteger_clock():
    crime = make()
    plan = project(crime)
    with pytest.raises(UnavailableAction):
        plan.perform(DiscoveryState(), "inspect_scene", place=crime.scene, at=crime.execution.death_at - 1)
    with pytest.raises(TypeError):
        plan.available(DiscoveryState(), place=crime.scene, at=True)


def test_cli_stage6_walkthrough_is_public_deterministic_and_not_falsely_solved():
    command = [sys.executable, "scenario_sampler.py", "--step", "6", "--seed", "42", "--method", "poisoned", "--walkthrough", "--json"]
    first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout == first
    row, = json.loads(first)
    assert not row["audit"]["unique_deduction"] and row["steps"]
    assert "candidates" not in first and "private" not in first
    assert "19 h 15" not in first


@pytest.mark.parametrize("flags", [
    ["--step", "5", "--walkthrough"],
    ["--step", "6", "--public-inventory"],
    ["--step", "6", "--public-scene"],
    ["--step", "6", "--requirements"],
])
def test_incompatible_cli_modes_fail_explicitly(flags):
    result = subprocess.run([sys.executable, "scenario_sampler.py", *flags], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0 and "error:" in result.stderr
