"""Suspect traits and their sampling distributions."""

import random
from enum import Enum


class Gender(Enum):
    FEMALE = 0
    MALE = 1


class EyeColor(Enum):
    BROWN = 1
    BLUE = 0
    GREY = 2
    GREEN = 3


class HairColor(Enum):
    BLACK = 4
    BROWN = 1
    BLOND = 0
    RED = 3


class BloodType(Enum):
    A = 0
    B = 1
    AB = 2
    O = 3


class Height(Enum):
    SMALL = 0
    MEDIUM = 1
    TALL = 2


class Hand(Enum):
    RIGHT = 0
    LEFT = 1


class LinkToVictim(Enum):
    SIBLING = 0
    NEIGHBORHOOD = 1
    COLLEAGUE = 2
    EX = 4
    UNKNOWN = 5


class Alibi(Enum):
    BAR = 0
    POOL = 1
    WITH_FRIENDS = 2


# trait -> (attribute name on Suspect, sampling weights in enum order)
TRAITS = {
    Gender: ("gender", None),
    HairColor: ("hair_color", [4, 3, 2, 1]),
    EyeColor: ("eye_color", [7, 1, 1, 1]),
    Height: ("height", [3, 5, 3]),
    BloodType: ("blood_type", [6, 4, 2, 1]),
    Hand: ("hand", [8, 2]),
    LinkToVictim: ("link", [3, 5, 2, 3, 2]),
}

# every trait value, flattened: the feature nodes of the case graph
criterions = [value for trait in TRAITS for value in trait]


def get_random_enum(enum, p=None, rng=random):
    """Pick a value of `enum`, uniformly or with weights `p` (in enum order)."""
    return rng.choices(list(enum), weights=p, k=1)[0]
