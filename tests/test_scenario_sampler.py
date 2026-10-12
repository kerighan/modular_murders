"""Step 1 only: authored enum domain, conditional sampling, and inspection CLI."""
import json
import os
import random
import subprocess
import sys
from collections import Counter
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest
import scenario_sampler

from scenario_sampler import (CATALOGUE_VERSION, CONTEXTS, RULES, Context, CrimeSeed, Motive,
                              ScenarioSampler, allowed_pairs, validate_catalogue)


ROOT = Path(__file__).resolve().parents[1]


def test_catalogue_is_exhaustive_and_all_contexts_are_reachable():
    validate_catalogue()
    assert set(RULES) == set(Motive)
    assert set(CONTEXTS) == set(Context)
    assert {pair.context for pair in allowed_pairs()} == set(Context)
    assert len(allowed_pairs()) == 46
    assert len(Motive) * len(Context) - len(allowed_pairs()) == 17


def test_missing_motive_rule_fails_closed(monkeypatch):
    rules = dict(RULES)
    del rules[Motive.REVENGE]
    monkeypatch.setattr(scenario_sampler, "RULES", rules)
    with pytest.raises(ValueError, match="explicit catalogue entry"):
        validate_catalogue()


def test_missing_context_description_fails_closed(monkeypatch):
    contexts = dict(CONTEXTS)
    del contexts[Context.FAMILY]
    monkeypatch.setattr(scenario_sampler, "CONTEXTS", contexts)
    with pytest.raises(ValueError, match="explicit catalogue entry"):
        validate_catalogue()


@pytest.mark.parametrize("changes,match", [
    ({"contexts": ()}, "Incomplete"),
    ({"contexts": (Context.FAMILY, Context.FAMILY)}, "Duplicate"),
    ({"contexts": ("family",)}, "Invalid context"),
    ({"contexts": (Context.FAMILY, Context.WORK)}, "Non-canonical"),
    ({"premise": ""}, "Incomplete"),
])
def test_invalid_rule_definitions_fail_before_sampling(monkeypatch, changes, match):
    rules = dict(RULES)
    rules[Motive.ACQUIRE] = replace(rules[Motive.ACQUIRE], **changes)
    monkeypatch.setattr(scenario_sampler, "RULES", rules)
    with pytest.raises(ValueError, match=match):
        validate_catalogue()


def test_unreachable_context_fails_closed(monkeypatch):
    rules = {motive: replace(rule, contexts=tuple(c for c in rule.contexts if c is not Context.NEIGHBORHOOD))
             for motive, rule in RULES.items()}
    monkeypatch.setattr(scenario_sampler, "RULES", rules)
    with pytest.raises(ValueError, match="Unreachable context"):
        validate_catalogue()


@pytest.mark.parametrize("motive", list(Motive))
@pytest.mark.parametrize("context", list(Context))
def test_full_cartesian_product_is_mechanically_constrained(motive, context):
    sampler = ScenarioSampler(42)
    if context in RULES[motive].contexts:
        pair = CrimeSeed(motive, context)
        assert sampler.sample(motive=motive, context=context) == pair
        assert allowed_pairs(motive=motive, context=context) == (pair,)
    else:
        with pytest.raises(ValueError, match=f"Unsupported V{CATALOGUE_VERSION} pair"):
            CrimeSeed(motive, context)
        with pytest.raises(ValueError, match=f"Unsupported V{CATALOGUE_VERSION} pair"):
            sampler.sample(motive=motive, context=context)
        assert allowed_pairs(motive=motive, context=context) == ()


@pytest.mark.parametrize("seed", [0, 1, 4, 7, 42, 100, 999])
def test_seeded_samples_are_deterministic_valid_and_only_two_fields(seed):
    a, b = ScenarioSampler(seed), ScenarioSampler(seed)
    samples = [a.sample() for _ in range(100)]
    assert samples == [b.sample() for _ in range(100)]
    assert set(samples) <= set(allowed_pairs())
    assert [field.name for field in fields(CrimeSeed)] == ["motive", "context"]
    assert all(set(pair.as_dict()) == {"motive", "context"} for pair in samples)
    assert all(CrimeSeed.from_dict(pair.as_dict()) == pair for pair in samples)


def test_uniform_parent_not_uniform_pairs_and_all_pairs_are_reached():
    sampler = ScenarioSampler(123)
    samples = [sampler.sample() for _ in range(9000)]
    assert set(samples) == set(allowed_pairs())
    counts = Counter(pair.motive for pair in samples)
    # Fixed seed, generous bounds: PREDATION has one allowed context and ACQUIRE
    # seven, but their parent probabilities must be the same, not 1:7.
    assert all(800 < counts[motive] < 1200 for motive in Motive)


@pytest.mark.parametrize("motive", list(Motive))
def test_pinned_motive_explores_only_its_allowed_contexts(motive):
    sampler = ScenarioSampler(71)
    samples = [sampler.sample(motive=motive) for _ in range(250)]
    assert {pair.motive for pair in samples} == {motive}
    assert {pair.context for pair in samples} == set(RULES[motive].contexts)


@pytest.mark.parametrize("context", list(Context))
def test_pinned_context_explores_only_compatible_motives(context):
    sampler = ScenarioSampler(71)
    samples = [sampler.sample(context=context) for _ in range(250)]
    assert {pair.context for pair in samples} == {context}
    assert {pair.motive for pair in samples} == {pair.motive for pair in allowed_pairs(context=context)}


def test_forbidden_pair_and_fixed_pair_do_not_consume_rng():
    sampler = ScenarioSampler(42)
    before = sampler.rng.getstate()
    with pytest.raises(ValueError):
        sampler.sample(motive=Motive.CONTROL, context=Context.CHANCE_ENCOUNTER)
    assert sampler.rng.getstate() == before
    sampler.sample(motive=Motive.SILENCE, context=Context.CHANCE_ENCOUNTER)
    assert sampler.rng.getstate() == before


def test_sampler_does_not_touch_global_rng():
    before = random.getstate()
    sampler = ScenarioSampler(42)
    for _ in range(30):
        sampler.sample()
    assert random.getstate() == before


def test_seed_is_immutable():
    pair = CrimeSeed(Motive.CONTROL, Context.ROMANCE)
    with pytest.raises(FrozenInstanceError):
        pair.context = Context.CHANCE_ENCOUNTER
    with pytest.raises(TypeError):
        RULES[Motive.CONTROL] = RULES[Motive.ACQUIRE]


@pytest.mark.parametrize("kwargs", [{"motive": "control"}, {"context": "romance"},
                                  {"motive": Context.FAMILY}, {"context": Motive.ACQUIRE}])
def test_raw_strings_and_wrong_enum_types_cannot_bypass_rules(kwargs):
    with pytest.raises(TypeError):
        ScenarioSampler(42).sample(**kwargs)
    with pytest.raises(TypeError):
        allowed_pairs(**kwargs)


@pytest.mark.parametrize("motive,context", [(None, Context.WORK), (Motive.ACQUIRE, None),
                                         ("acquire", Context.WORK), (Motive.ACQUIRE, "work")])
def test_constructed_seed_requires_two_typed_enum_members(motive, context):
    with pytest.raises(TypeError):
        CrimeSeed(motive, context)


@pytest.mark.parametrize("data", [
    {}, {"motive": "control"}, {"motive": "control", "context": "romance", "weapon": "knife"},
    {"motive": "unknown", "context": "work"}, {"motive": "control", "context": "chance_encounter"},
])
def test_imported_pairs_are_validated_too(data):
    with pytest.raises(ValueError):
        CrimeSeed.from_dict(data)


def run_cli(*args, hash_seed=None):
    env = dict(os.environ)
    if hash_seed is not None:
        env["PYTHONHASHSEED"] = str(hash_seed)
    return subprocess.run([sys.executable, str(ROOT / "scenario_sampler.py"), *args],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)


def test_cli_is_deterministic_across_process_hash_seeds():
    args = ("--seed", "42", "--count", "20", "--step", "2", "--json")
    a, b = run_cli(*args, hash_seed=1), run_cli(*args, hash_seed=999)
    assert a.returncode == b.returncode == 0
    assert a.stdout == b.stdout
    assert len(json.loads(a.stdout)) == 20


def test_cli_catalogue_exposes_exactly_the_allowed_domain():
    result = run_cli("--catalogue", "--step", "2", "--json")
    assert result.returncode == 0
    assert tuple(CrimeSeed.from_dict(pair) for pair in json.loads(result.stdout)) == allowed_pairs()


def test_cli_can_pin_a_motive_to_explore_the_next_branch():
    result = run_cli("--motive", "control", "--count", "30", "--json")
    assert result.returncode == 0
    assert all(pair["motive"] == "control" for pair in json.loads(result.stdout))


@pytest.mark.parametrize("extra", [(), ("--catalogue",)])
def test_cli_explains_forbidden_fixed_pairs(extra):
    result = run_cli("--motive", "control", "--context", "chance_encounter", *extra)
    assert result.returncode == 2
    assert f"Unsupported V{CATALOGUE_VERSION} pair: control / chance_encounter" in result.stderr
    assert not result.stdout


@pytest.mark.parametrize("args", [("--count", "0"), ("--count", "-1"),
                                 ("--motive", "not_a_motive"), ("--context", "not_a_context")])
def test_invalid_cli_arguments_fail(args):
    assert run_cli(*args).returncode == 2
