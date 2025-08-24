import io
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from suspect import Case
from clue import AlibiClue
from genotype import (
    Gender,
    EyeColor,
    HairColor,
    Height,
    BloodType,
    Hand,
    LinkToVictim,
)
from modality import location

trait_map = {
    Gender: "gender",
    EyeColor: "eye_color",
    HairColor: "hair_color",
    Height: "height",
    BloodType: "blood_type",
    Hand: "hand",
    LinkToVictim: "link",
}


def test_generated_clues_isolate_murderer():
    case = Case(seed=0)
    suspects = list(range(len(case.suspects)))
    for fact, clue_cls in case.clues.items():
        if clue_cls is AlibiClue:
            continue
        attr = trait_map[clue_cls.clue_type]
        suspects = [i for i in suspects if getattr(case[i], attr) == fact]
    assert suspects == [0]


def test_environment_flags_follow_clues():
    for seed in range(3):
        case = Case(seed=seed)
        env = case.environment
        clue_locs = [c.location for c in case.clues.values() if hasattr(c, "location")]
        mapping = {
            location.MURDER_WEAPON: "can_inspect_murder_weapon",
            location.VICTIM_PHONE: "can_inspect_victim_phone",
            location.CCTV: "can_inspect_cctv",
            location.NEIGHBOR: "can_inspect_neighbor",
        }
        for loc, key in mapping.items():
            if loc in clue_locs:
                assert env[key] is True
            else:
                assert env[key] is False
        if location.MURDERER_HOUSE in clue_locs:
            assert env["can_inspect_houses"][0] is True
        else:
            assert env["can_inspect_houses"][0] is False


def test_seed_yields_deterministic_suspects():
    case1 = Case(seed=123)
    case2 = Case(seed=123)
    profiles1 = [s.identity for s in case1.suspects]
    profiles2 = [s.identity for s in case2.suspects]
    assert profiles1 == profiles2
