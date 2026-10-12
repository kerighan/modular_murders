"""Bound pre-crime truth: break references/semantics, not only count enum tags."""
import json
import os
import random
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import scenario_kernel as k
from scenario_sampler import Context, CrimePremise, Motive, RequiredFact, Stake, allowed_premises


ROOT = Path(__file__).resolve().parents[1]
CONTROL = CrimePremise(Motive.CONTROL, Context.ROMANCE, Stake.SEPARATION)
REFUSAL = CrimePremise(Motive.CONTROL, Context.ROMANCE, Stake.REFUSAL)
FRAUD = CrimePremise(Motive.SILENCE, Context.WORK, Stake.FRAUD)


def control(seed=42, mechanism=k.ControlMechanism.FINANCIAL):
    return k.KernelBuilder(seed).build(CONTROL, mechanism=mechanism)


def substitute(world, field, id, **changes):
    return replace(world, **{field: tuple(replace(obj, **changes) if obj.id == id else obj
                                         for obj in getattr(world, field))})


def test_only_six_explicitly_supported_premises_not_all_abstract_cases():
    assert len(k.SUPPORTED_PREMISES) == 6
    assert set(k.SUPPORTED_PREMISES) < set(allowed_premises())


@pytest.mark.parametrize("batch", range(20))
def test_thousand_bound_worlds_are_deterministic_and_satisfy_real_contracts(batch):
    for seed in range(batch * 10, batch * 10 + 10):
        for premise in k.SUPPORTED_PREMISES:
            a, b = k.KernelBuilder(seed).build(premise), k.KernelBuilder(seed).build(premise)
            assert a == b
            assert a.as_dict() == b.as_dict()
            proof = k.validate_kernel(a)
            assert {p.requirement for p in proof} == set(premise.required_facts)
            assert all(p.sources for p in proof)
            assert len({a.roles.author, a.roles.victim, a.roles.other}) == 3
            assert len(a.world.people) == 6
            assert a.method is None
            assert all(event.minute < 0 for event in a.world.events)
            assert a.as_dict()["visibility"] == "private_precrime_truth"


@pytest.mark.parametrize("premise", k.SUPPORTED_PREMISES)
def test_no_method_evidence_or_witness_is_generated(premise):
    kernel = k.KernelBuilder(42).build(premise)
    data = kernel.as_dict()
    assert data["method"] is None
    assert not {"evidence", "clues", "witnesses", "candidates", "proofs"} & data.keys()
    assert not {"murder", "death", "attack"} & {e.kind.value for e in kernel.world.events}


def test_ordinary_relationships_do_not_generate_intentions_or_guilt():
    kernel = control()
    a, v = kernel.roles.author, kernel.roles.victim
    neutral = [r for r in kernel.world.relationships if r.id.startswith("ordinary")]
    assert {r.kind for r in neutral} == {k.RelationKind.FRIENDS, k.RelationKind.ROMANTIC}
    assert all(not {a, v} & set(r.people) for r in neutral)
    assert all("guilty" not in row for row in kernel.as_dict()["world"]["people"])
    assert kernel.intent.author == a


def test_financial_control_requires_an_actual_deficit_and_funded_support():
    kernel = control()
    dep = kernel.world.dependencies[0]
    people = {p.id: p for p in kernel.world.people}
    resource = next(r for r in kernel.world.resources if r.id == dep.resource)
    assert people[dep.dependent].monthly_expenses - people[dep.dependent].monthly_income == dep.monthly_need > 0
    assert people[dep.controller].monthly_income - people[dep.controller].monthly_expenses >= resource.amount >= dep.monthly_need


def test_housing_control_requires_shared_home_not_merely_a_label():
    kernel = control(mechanism=k.ControlMechanism.HOUSING)
    people = {p.id: p for p in kernel.world.people}
    dep = kernel.world.dependencies[0]
    assert people[dep.controller].home == people[dep.dependent].home == dep.resource
    assert not any(r.kind is k.ResourceKind.HOME and r.owner == dep.dependent for r in kernel.world.resources)


def test_refusal_concerns_a_real_demand_and_a_real_friend_when_needed():
    seen = set()
    for seed in range(30):
        kernel = k.KernelBuilder(seed).build(REFUSAL)
        demand = kernel.world.demands[0]
        seen.add(demand.kind)
        if demand.kind is k.DemandKind.STOP_SEEING_FRIEND:
            assert demand.third_person == kernel.roles.other
            assert any(r.kind is k.RelationKind.FRIENDS and set(r.people) == {kernel.roles.victim, demand.third_person}
                       for r in kernel.world.relationships)
    assert seen == set(k.DemandKind)


@pytest.mark.parametrize("seed", range(15))
def test_silencing_uses_actual_employees_and_targeted_information(seed):
    kernel = k.KernelBuilder(seed).build(FRAUD)
    people = {p.id: p for p in kernel.world.people}
    author, victim, other = (people[id] for id in (kernel.roles.author, kernel.roles.victim, kernel.roles.other))
    assert author.workplace is victim.workplace is other.workplace
    assert author.occupation is k.JOBS[author.workplace][1]
    assert victim.occupation is k.JOBS[victim.workplace][0]
    assert other.occupation is k.Occupation.ACCOUNTING
    knowledge = kernel.world.knowledge[0]
    disclosure = kernel.world.disclosures[0]
    assert knowledge.person == victim.id and knowledge.incident == disclosure.incident
    assert disclosure.speaker == victim.id and disclosure.recipient == other.id
    assert kernel.intent.expected_effect is k.ExpectedEffect.DEATH_BLOCKS_DISCLOSURE


def test_missing_relation_cannot_be_satisfied_by_the_requirement_token():
    kernel = control()
    world = replace(kernel.world, relationships=tuple(r for r in kernel.world.relationships if r.id != "root_romance"))
    with pytest.raises(k.InvalidKernel, match="real romantic relation"):
        replace(kernel, world=world)


def test_other_peoples_relationship_cannot_satisfy_the_bound_roles():
    kernel = control()
    world = substitute(kernel.world, "relationships", "root_romance",
                       people=(kernel.roles.victim, kernel.roles.other))
    with pytest.raises(k.InvalidKernel, match="real romantic relation"):
        replace(kernel, world=world)


def test_financial_independence_breaks_the_dependency_predicate():
    kernel = control()
    victim = next(p for p in kernel.world.people if p.id == kernel.roles.victim)
    world = substitute(kernel.world, "people", victim.id, monthly_expenses=victim.monthly_income)
    with pytest.raises(k.InvalidKernel, match="real income/expense deficit"):
        replace(kernel, world=world)


def test_unfunded_aid_is_rejected():
    kernel = control()
    dep = kernel.world.dependencies[0]
    world = substitute(kernel.world, "resources", dep.resource, amount=dep.monthly_need - 1)
    with pytest.raises(k.InvalidKernel, match="funded support"):
        replace(kernel, world=world)


def test_controller_cannot_spend_money_they_do_not_have():
    kernel = control()
    author = next(p for p in kernel.world.people if p.id == kernel.roles.author)
    world = substitute(kernel.world, "people", author.id, monthly_expenses=author.monthly_income)
    with pytest.raises(k.InvalidKernel, match="able to fund"):
        replace(kernel, world=world)


def test_an_independent_home_breaks_housing_dependency():
    kernel = control(mechanism=k.ControlMechanism.HOUSING)
    house = k.Resource("independent_home", k.ResourceKind.HOME, kernel.roles.victim,
                       kernel.roles.victim, "Logement indépendant")
    with pytest.raises(k.InvalidKernel, match="independently owned home"):
        replace(kernel, world=replace(kernel.world, resources=(*kernel.world.resources, house)))


def test_wrong_controller_of_resource_is_rejected():
    kernel = control()
    dep = kernel.world.dependencies[0]
    world = substitute(kernel.world, "resources", dep.resource, holder=kernel.roles.other)
    with pytest.raises(k.InvalidKernel, match="actually control"):
        replace(kernel, world=world)


@pytest.mark.parametrize("changes,match", [
    ({"causes": ("missing",)}, "Causal parents"),
    ({"causes": ("decision",)}, "Causal parents"),
    ({"minute": 1}, "precede the unresolved"),
    ({"subject": "missing"}, "place/subject"),
    ({"actor": "missing"}, "participants"),
    ({"target": "missing"}, "participants"),
    ({"place": "missing_street"}, "place/subject"),
])
def test_bad_event_references_and_chronology_are_rejected(changes, match):
    kernel = control()
    world = substitute(kernel.world, "events", "reaction", **changes)
    with pytest.raises(k.InvalidKernel, match=match):
        replace(kernel, world=world)


def test_a_reaction_cannot_precede_its_trigger():
    kernel = control()
    autonomy = next(e for e in kernel.world.events if e.id == "autonomy")
    world = substitute(kernel.world, "events", "reaction", minute=autonomy.minute - 1)
    with pytest.raises(k.InvalidKernel, match="strictly precede"):
        replace(kernel, world=world)


def test_a_different_event_cannot_substitute_for_separation():
    kernel = control()
    world = substitute(kernel.world, "events", "autonomy", kind=k.EventKind.DISCOVERY)
    with pytest.raises(k.InvalidKernel, match="match the concrete stake"):
        replace(kernel, world=world)


def test_wrong_goal_or_belief_cannot_satisfy_control_intent():
    kernel = control()
    intent = replace(kernel.intent, expected_effect=k.ExpectedEffect.DEATH_BLOCKS_DISCLOSURE)
    with pytest.raises(k.InvalidKernel, match="denied autonomy"):
        replace(kernel, intent=intent)


def test_actual_knowledge_is_required_before_a_disclosure():
    kernel = k.KernelBuilder(42).build(FRAUD)
    with pytest.raises(k.InvalidKernel, match="actual knowledge"):
        replace(kernel, world=replace(kernel.world, knowledge=()))


def test_discovery_cannot_belong_to_somebody_else():
    kernel = k.KernelBuilder(42).build(FRAUD)
    knowledge = replace(kernel.world.knowledge[0], person=kernel.roles.other)
    with pytest.raises(k.InvalidKernel, match="Producer event"):
        replace(kernel, world=replace(kernel.world, knowledge=(knowledge,)))


def test_unrelated_information_cannot_satisfy_silencing_intent():
    kernel = k.KernelBuilder(42).build(FRAUD)
    world = substitute(kernel.world, "disclosures", "disclosure", incident="missing")
    with pytest.raises(k.InvalidKernel, match="recipient/incident"):
        replace(kernel, world=world)


def test_paid_hours_cannot_satisfy_unpaid_work_contract():
    premise = CrimePremise(Motive.SILENCE, Context.WORK, Stake.EXPLOITATION)
    kernel = k.KernelBuilder(42).build(premise)
    world = substitute(kernel.world, "incidents", "incident", paid=100)
    with pytest.raises(k.InvalidKernel, match="Resource/payment"):
        replace(kernel, world=world)


def test_duplicate_ids_fail_before_any_requirement_matching():
    kernel = control()
    world = replace(kernel.world, events=(*kernel.world.events, kernel.world.events[0]))
    with pytest.raises(k.InvalidKernel, match="globally unique"):
        replace(kernel, world=world)


def test_roles_cannot_alias_each_other():
    kernel = control()
    with pytest.raises(k.InvalidKernel, match="three distinct"):
        replace(kernel, roles=replace(kernel.roles, victim=kernel.roles.author))


def test_immutable_typed_collections_and_values():
    kernel = control()
    with pytest.raises(FrozenInstanceError):
        kernel.world.people[0].name = "Changed"
    with pytest.raises(k.InvalidKernel, match="Immutable typed"):
        replace(kernel, world=replace(kernel.world, events=list(kernel.world.events)))
    world = substitute(kernel.world, "events", "reaction", kind="autonomy_rejected")
    with pytest.raises(k.InvalidKernel, match="Events must"):
        replace(kernel, world=world)


def test_unsupported_templates_and_bad_arguments_fail_without_drawing():
    builder = k.KernelBuilder(42)
    before = builder.rng.getstate()
    unsupported = CrimePremise(Motive.ACQUIRE, Context.FAMILY, Stake.INHERITANCE)
    with pytest.raises(k.UnsupportedPremise):
        builder.build(unsupported)
    with pytest.raises(k.UnsupportedPremise):
        builder.sample(stake=Stake.INHERITANCE)
    with pytest.raises(ValueError):
        builder.build(FRAUD, mechanism=k.ControlMechanism.FINANCIAL)
    with pytest.raises(TypeError):
        builder.build(CONTROL.as_dict())
    assert builder.rng.getstate() == before


def test_builders_do_not_touch_global_rng_and_sampling_explores_both_mechanisms():
    before = random.getstate()
    seen = set()
    for seed in range(30):
        kernel = k.KernelBuilder(seed).build(CONTROL)
        seen.add(kernel.world.dependencies[0].mechanism)
    assert seen == set(k.ControlMechanism)
    assert random.getstate() == before


def test_sampled_domain_coverage_and_role_ids_are_not_fixed():
    builder = k.KernelBuilder(42)
    kernels = [builder.sample() for _ in range(100)]
    assert {kernel.premise for kernel in kernels} == set(k.SUPPORTED_PREMISES)
    assert len({kernel.roles.author for kernel in kernels}) > 1


def cli(script, *args, hash_seed=1):
    return subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT,
                          env={**os.environ, "PYTHONHASHSEED": str(hash_seed)},
                          capture_output=True, text=True, timeout=10)


def test_kernel_cli_json_is_deterministic_and_marks_truth_private():
    args = ("--motive", "control", "--context", "romance", "--stake", "separation", "--json")
    a, b = cli("scenario_kernel.py", *args), cli("scenario_kernel.py", *args, hash_seed=999)
    assert a.returncode == b.returncode == 0 and a.stdout == b.stdout
    row, = json.loads(a.stdout)
    assert row["visibility"] == "private_precrime_truth" and row["method"] is None
    assert {r["requirement"] for r in row["satisfied_requirements"]} == {r.value for r in CONTROL.required_facts}


def test_sampler_cli_step4_dispatches_safely_across_main_enum_identity():
    args = ("--motive", "control", "--context", "romance", "--stake", "separation", "--json")
    direct = cli("scenario_kernel.py", *args)
    wrapper = cli("scenario_sampler.py", "--step", "4", *args)
    assert direct.returncode == wrapper.returncode == 0
    assert direct.stdout == wrapper.stdout


def test_sampler_cli_step4_can_show_actual_requirement_references():
    result = cli("scenario_sampler.py", "--step", "4", "--stake", "separation", "--requirements")
    assert result.returncode == 0
    assert "romantic_link ← root_romance" in result.stdout
    assert "Méthode : non choisie" in result.stdout


def test_cli_catalogue_does_not_claim_105_implemented_kernels():
    result = cli("scenario_sampler.py", "--step", "4", "--catalogue")
    assert result.returncode == 0
    assert {CrimePremise.from_dict(row) for row in json.loads(result.stdout)} == set(k.SUPPORTED_PREMISES)


@pytest.mark.parametrize("script", ["scenario_kernel.py", "scenario_sampler.py"])
def test_cli_explains_unimplemented_branch(script):
    extra = ("--step", "4") if script == "scenario_sampler.py" else ()
    result = cli(script, *extra, "--motive", "acquire", "--context", "family", "--stake", "inheritance")
    assert result.returncode == 2 and not result.stdout
    assert "No implemented kernel" in result.stderr


def test_cli_rejects_zero_count():
    assert cli("scenario_kernel.py", "--count", "0").returncode == 2
