"""Trait definitions and random generators for murder mystery suspects."""

import itertools
from enum import Enum
from random import choices


# ------------------------------ Enumerations ------------------------------
# Each Enum represents a biological or social trait that can help identify a
# suspect.  Values are arbitrary integers but remain stable across the system.


class Gender(Enum):
    """Biological sex of the suspect."""

    FEMALE = 0
    MALE = 1


class EyeColor(Enum):
    """Possible eye colours."""

    BROWN = 1
    BLUE = 0
    GREY = 2
    GREEN = 3


class HairColor(Enum):
    """Possible hair colours."""

    BLACK = 4
    BROWN = 1
    BLOND = 0
    RED = 3


class BloodType(Enum):
    """Blood groups used to match traces of blood."""

    A = 0
    B = 1
    AB = 2
    O = 3


class Height(Enum):
    """Rough height categories."""

    SMALL = 0
    MEDIUM = 1
    TALL = 2


class Hand(Enum):
    """Dominant hand of the suspect."""

    RIGHT = 0
    LEFT = 1


class LinkToVictim(Enum):
    """Relationship of the suspect to the victim."""

    SIBLING = 0
    NEIGHBORHOOD = 1
    COLLEAGUE = 2
    EX = 4
    UNKNOWN = 5


class Alibi(Enum):
    """Potential alibis offered by suspects."""

    BAR = 0
    POOL = 1
    WITH_FRIENDS = 2


# A flat list of all trait Enums.  This is used to build graphs linking
# features to suspects.
genotypes = [Gender, HairColor, EyeColor, Height, BloodType, Hand, LinkToVictim]
criterions = list(
    itertools.chain(*[list(genotype) for genotype in genotypes])
)


# -------------------------- Randomisation helpers -------------------------


def get_random_enum(enum, p=None):
    """Return a random value from ``enum`` with optional weight ``p``."""

    data = list(enum)
    if p is None:
        # Default to a uniform distribution across all enum values.
        p = [1 / len(data) for _ in range(len(data))]
    return choices(data, weights=p, k=1)[0]


def get_random_eye_color():
    """Return an eye colour biased towards brown."""

    return get_random_enum(EyeColor, p=[7, 1, 1, 1])


def get_random_hair_color():
    """Return a hair colour with decreasing likelihood."""

    return get_random_enum(HairColor, p=[4, 3, 2, 1])


def get_random_gender():
    """Return a gender using a uniform distribution."""

    return get_random_enum(Gender)


def get_random_blood_type():
    """Return a blood type with realistic population ratios."""

    return get_random_enum(BloodType, p=[6, 4, 2, 1])


def get_random_height():
    """Return a height category favouring average builds."""

    return get_random_enum(Height, p=[.3, .5, .3])


def get_random_hand():
    """Return a hand preference biased towards right-handedness."""

    return get_random_enum(Hand, p=[.8, .2])


def get_random_link():
    """Return a relationship to the victim with custom weights."""

    return get_random_enum(LinkToVictim, p=[3, 5, 2, 3, 2])
