import pytest

from clue import CLUES
from genotype import TRAITS, criterions
from modality import Location
from suspect import Case

SEEDS = range(200)


def matching(case):
    """Suspects compatible with every clue."""
    return {i for i, s in enumerate(case.suspects) if all(s[type(f)] == f for f in case.clues)}


@pytest.mark.parametrize("seed", SEEDS)
def test_clues_and_alibis_isolate_murderer(seed):
    case = Case(seed=seed)
    assert 0 not in case.alibis
    assert matching(case) - set(case.alibis) == {0}


@pytest.mark.parametrize("seed", SEEDS)
def test_facts_are_minimal_unless_dopplegangers(seed):
    case = Case(seed=seed)
    if case.dopplegangers:
        assert set(case.alibis) == case.dopplegangers
    else:
        assert not case.alibis
        for fact in case.facts:
            assert case.remaining([f for f in case.facts if f != fact]) != {0}


def test_every_trait_value_has_a_consistent_clue():
    for value in criterions:
        assert any(isinstance(value, c.trait) and c.is_consistent([value]) for c in CLUES), value


@pytest.mark.parametrize("seed", range(20))
def test_environment_flags_follow_clues(seed):
    case = Case(seed=seed)
    env, where = case.environment, {c.location for c in case.clues.values()}
    assert env["can_inspect_murder_weapon"] is (Location.MURDER_WEAPON in where)
    assert env["can_inspect_victim_phone"] is (Location.VICTIM_PHONE in where)
    assert env["can_inspect_cctv"] is (Location.CCTV in where)
    assert env["can_inspect_neighbor"] is (Location.NEIGHBOR in where)
    assert env["can_inspect_houses"][0] is (Location.MURDERER_HOUSE in where)
    assert len(env["can_inspect_houses"]) == case.n_suspects
    assert ("victim_phone_lock_routine" in env) is env["victim_phone"]
    assert ("murder_weapon_routine" in env) is env["murder_weapon"]


def test_seed_is_deterministic():
    a, b = Case(seed=123), Case(seed=123)
    assert [s.identity for s in a.suspects] == [s.identity for s in b.suspects]
    assert a.clues.keys() == b.clues.keys() and a.environment == b.environment


def test_suspect_count_and_identity():
    case = Case(seed=1, n_suspects=3)
    assert case.n_suspects == len(case.suspects) == 3
    assert case.murderer.guilty and not any(s.guilty for s in case.suspects[1:])
    assert set(case.murderer.identity) == {"guilty", *(attr for attr, _ in TRAITS.values())}
