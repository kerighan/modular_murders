"""Step 3 constrains concrete stakes and declares obligations, never evidence."""
import json
import random
from collections import Counter
from dataclasses import FrozenInstanceError, fields
from itertools import product

import pytest

import scenario_sampler as s
from test_scenario_sampler import run_cli


def test_every_pair_has_a_nonempty_branch_and_all_stakes_are_reachable():
    s.validate_catalogue()
    assert set(s.STAKE_BRANCHES) == {(p.motive, p.context) for p in s.allowed_pairs()}
    assert {p.stake for p in s.allowed_premises()} == set(s.Stake)
    assert len(s.Stake) == 28
    assert len(s.allowed_premises()) == 105
    assert [f.name for f in fields(s.CrimePremise)] == ["motive", "context", "stake"]


@pytest.mark.parametrize("motive,context", list(product(s.Motive, s.Context)))
def test_all_1764_triples_are_validated_including_unsupported_parents(motive, context):
    sampler = s.ScenarioSampler(42)
    branch = s.STAKE_BRANCHES.get((motive, context), ())
    for stake in s.Stake:
        if stake in branch:
            premise = s.CrimePremise(motive, context, stake)
            assert sampler.sample_premise(motive=motive, context=context, stake=stake) == premise
            assert s.allowed_premises(motive=motive, context=context, stake=stake) == (premise,)
        else:
            with pytest.raises(ValueError):
                s.CrimePremise(motive, context, stake)
            with pytest.raises(ValueError, match="No compatible premise"):
                sampler.sample_premise(motive=motive, context=context, stake=stake)
            assert s.allowed_premises(motive=motive, context=context, stake=stake) == ()


@pytest.mark.parametrize("premise", s.allowed_premises())
def test_each_contract_has_correct_typed_requirements_and_no_evidence(premise):
    facts = premise.required_facts
    expected = {*s.MOTIVE_FACTS[premise.motive], s.CONTEXT_FACTS[premise.context],
                s.STAKE_FACTS[premise.stake], s.RequiredFact.DEATH_EXPECTED_TO_SERVE_GOAL}
    assert set(facts) == expected
    assert len(facts) == len(expected)
    assert all(type(f) is s.RequiredFact for f in facts)
    assert facts == tuple(f for f in s.RequiredFact if f in expected)
    assert not {"photo", "letter", "witness", "culprit", "candidates", "proof"} & premise.as_dict().keys()
    assert s.CrimePremise.from_dict(premise.as_dict()) == premise


def test_romantic_control_requires_causal_history_but_not_photos_or_a_letter():
    premise = s.CrimePremise(s.Motive.CONTROL, s.Context.ROMANCE, s.Stake.SEPARATION)
    assert {s.RequiredFact.ROMANTIC_LINK, s.RequiredFact.PRIOR_CONTROL,
            s.RequiredFact.VICTIM_SEEKS_AUTONOMY, s.RequiredFact.SEPARATION_ANNOUNCED} <= set(premise.required_facts)
    assert all("photo" not in f.value and "letter" not in f.value for f in premise.required_facts)


def test_stranger_witness_can_be_silenced_without_a_personal_relationship():
    premise = s.CrimePremise(s.Motive.SILENCE, s.Context.CHANCE_ENCOUNTER, s.Stake.PAST_CRIME)
    assert {s.RequiredFact.NO_SHARED_HISTORY, s.RequiredFact.PAST_CRIME_EXISTS,
            s.RequiredFact.VICTIM_KNOWS_SECRET, s.RequiredFact.DISCLOSURE_POSSIBLE} <= set(premise.required_facts)
    assert s.RequiredFact.ROMANTIC_LINK not in premise.required_facts


def test_predation_is_not_automatically_serial_or_given_a_personal_conflict():
    premise = s.CrimePremise(s.Motive.PREDATION, s.Context.CHANCE_ENCOUNTER, s.Stake.DOMINATION)
    assert {s.RequiredFact.NO_SHARED_HISTORY, s.RequiredFact.ACT_SOUGHT,
            s.RequiredFact.DOMINATION_DESIRED} <= set(premise.required_facts)
    assert not {s.RequiredFact.PRIOR_HARM, s.RequiredFact.PAST_CRIME_EXISTS,
                s.RequiredFact.ROMANTIC_LINK} & set(premise.required_facts)


def test_required_fact_catalogue_is_exhaustive_and_readable():
    assert {f for p in s.allowed_premises() for f in p.required_facts} == set(s.RequiredFact)
    assert all(f.label and type(f.value) is str for f in s.RequiredFact)
    assert all(stake.label and type(stake.value) is str for stake in s.Stake)


@pytest.mark.parametrize("seed", [0, 1, 7, 42, 100, 999])
def test_direct_and_staged_sampling_are_identical_and_do_not_redraw_parents(seed):
    direct, staged = s.ScenarioSampler(seed), s.ScenarioSampler(seed)
    for _ in range(100):
        pair = staged.sample()
        developed = staged.develop(pair)
        assert developed.seed == pair
        assert developed == direct.sample_premise()
    assert direct.rng.getstate() == staged.rng.getstate()


def test_corpus_covers_domain_and_parent_frequency_is_not_leaf_weighted():
    sampler = s.ScenarioSampler(123)
    samples = [sampler.sample_premise() for _ in range(9000)]
    assert set(samples) == set(s.allowed_premises())
    counts = Counter(p.motive for p in samples)
    assert all(800 < counts[m] < 1200 for m in s.Motive)


@pytest.mark.parametrize("stake", list(s.Stake))
def test_pinned_child_restricts_both_parent_domains(stake):
    sampler = s.ScenarioSampler(17)
    samples = {sampler.sample_premise(stake=stake) for _ in range(500)}
    assert samples == set(s.allowed_premises(stake=stake))


def test_impossible_filters_and_manual_child_fail_before_consuming_rng():
    sampler = s.ScenarioSampler(42)
    before = sampler.rng.getstate()
    seed = s.CrimeSeed(s.Motive.ACQUIRE, s.Context.FAMILY)
    with pytest.raises(ValueError, match="No compatible premise"):
        sampler.sample_premise(motive=s.Motive.ACQUIRE, context=s.Context.FAMILY, stake=s.Stake.SEPARATION)
    assert sampler.rng.getstate() == before
    with pytest.raises(ValueError, match="Unsupported"):
        sampler.develop(seed, stake=s.Stake.SEPARATION)
    assert sampler.rng.getstate() == before
    sampler.develop(seed, stake=s.Stake.INHERITANCE)
    assert sampler.rng.getstate() == before
    sampler.sample_premise(motive=seed.motive, context=seed.context, stake=s.Stake.INHERITANCE)
    assert sampler.rng.getstate() == before


def test_new_sampler_does_not_touch_global_rng():
    before = random.getstate()
    sampler = s.ScenarioSampler(42)
    for _ in range(100):
        sampler.sample_premise()
    assert random.getstate() == before


def test_premise_and_authoring_domains_are_immutable():
    p = s.CrimePremise(s.Motive.CONTROL, s.Context.ROMANCE, s.Stake.SEPARATION)
    with pytest.raises(FrozenInstanceError):
        p.stake = s.Stake.INHERITANCE
    with pytest.raises(TypeError):
        s.STAKE_BRANCHES[s.Motive.CONTROL, s.Context.ROMANCE] = (s.Stake.INHERITANCE,)


@pytest.mark.parametrize("stake", ["fraud", s.Motive.SILENCE, s.Context.WORK])
def test_wrong_enum_or_raw_string_cannot_bypass_child_constraints(stake):
    with pytest.raises(TypeError):
        s.CrimePremise(s.Motive.SILENCE, s.Context.WORK, stake)
    with pytest.raises(TypeError):
        s.ScenarioSampler(42).sample_premise(stake=stake)
    with pytest.raises(TypeError):
        s.allowed_premises(stake=stake)


def test_development_requires_a_typed_existing_seed():
    with pytest.raises(TypeError):
        s.ScenarioSampler(42).develop({"motive": "silence", "context": "work"})


@pytest.mark.parametrize("data", [
    {}, {"motive": "silence", "context": "work"},
    {"motive": "silence", "context": "work", "stake": "fraud", "proof": "photo"},
    {"motive": "silence", "context": "work", "stake": "separation"},
])
def test_imported_premises_cannot_add_proofs_or_bypass_rules(data):
    with pytest.raises(ValueError):
        s.CrimePremise.from_dict(data)


def test_missing_pair_branch_fails_closed(monkeypatch):
    branches = dict(s.STAKE_BRANCHES)
    del branches[s.Motive.CONTROL, s.Context.ROMANCE]
    monkeypatch.setattr(s, "STAKE_BRANCHES", branches)
    with pytest.raises(ValueError, match="explicit stake branch"):
        s.validate_catalogue()


@pytest.mark.parametrize("bad_branch,match", [
    ((), "Invalid or empty"), (("separation",), "Invalid or empty"),
    ((s.Stake.SEPARATION, s.Stake.SEPARATION), "Duplicate stake"),
    ((s.Stake.REFUSAL, s.Stake.SEPARATION), "Non-canonical stake order"),
])
def test_bad_stake_branches_fail_closed(monkeypatch, bad_branch, match):
    branches = dict(s.STAKE_BRANCHES)
    branches[s.Motive.CONTROL, s.Context.ROMANCE] = bad_branch
    monkeypatch.setattr(s, "STAKE_BRANCHES", branches)
    with pytest.raises(ValueError, match=match):
        s.validate_catalogue()


def test_unreachable_stake_fails_closed(monkeypatch):
    branches = {pair: tuple(stake for stake in stakes if stake is not s.Stake.ROMANTIC_RIVAL)
                for pair, stakes in s.STAKE_BRANCHES.items()}
    # Keep this branch nonempty so the reachability check, not emptiness, fires.
    branches[s.Motive.REMOVE_OBSTACLE, s.Context.ROMANCE] = (s.Stake.REFUSAL,)
    monkeypatch.setattr(s, "STAKE_BRANCHES", branches)
    with pytest.raises(ValueError, match="Unreachable stake"):
        s.validate_catalogue()


def test_missing_stake_contract_fails_closed(monkeypatch):
    facts = dict(s.STAKE_FACTS)
    del facts[s.Stake.SEPARATION]
    monkeypatch.setattr(s, "STAKE_FACTS", facts)
    with pytest.raises(ValueError, match="explicit causal contract"):
        s.validate_catalogue()


def test_untyped_fact_cannot_enter_a_contract(monkeypatch):
    facts = dict(s.STAKE_FACTS)
    facts[s.Stake.SEPARATION] = "photo_together"
    monkeypatch.setattr(s, "STAKE_FACTS", facts)
    with pytest.raises(ValueError, match="Invalid or unreachable required fact"):
        s.validate_catalogue()


def test_cli_defaults_to_third_step_and_catalogue_lists_the_exact_domain():
    result = run_cli("--catalogue", "--json")
    assert result.returncode == 0
    assert tuple(s.CrimePremise.from_dict(row) for row in json.loads(result.stdout)) == s.allowed_premises()


def test_cli_contract_is_optional_derived_metadata_not_a_fourth_draw():
    result = run_cli("--motive", "control", "--context", "romance", "--stake", "separation",
                     "--count", "1", "--requirements", "--json")
    assert result.returncode == 0
    row, = json.loads(result.stdout)
    required = row.pop("required_facts")
    premise = s.CrimePremise.from_dict(row)
    assert required == [f.value for f in premise.required_facts]


def test_cli_child_filter_is_supported_without_pinning_its_parents():
    result = run_cli("--stake", "separation", "--count", "5", "--json")
    assert result.returncode == 0
    assert json.loads(result.stdout) == [{"motive": "control", "context": "romance", "stake": "separation"}] * 5


@pytest.mark.parametrize("args", [
    ("--motive", "silence", "--stake", "separation"),
    ("--step", "2", "--stake", "fraud"),
    ("--step", "2", "--requirements"),
    ("--stake", "not_a_stake"),
])
def test_cli_rejects_impossible_filters_or_wrong_step(args):
    result = run_cli(*args)
    assert result.returncode == 2 and not result.stdout


def test_three_step_outputs_are_stable_across_process_hash_seeds():
    args = ("--seed", "42", "--count", "30", "--requirements", "--json")
    a, b = run_cli(*args, hash_seed=1), run_cli(*args, hash_seed=999)
    assert a.returncode == b.returncode == 0
    assert a.stdout == b.stdout
