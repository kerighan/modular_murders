import itertools
from enum import Enum
from random import choices


class Gender(Enum):
    FEMALE = 0
    MALE = 1


class EyeColor(Enum):
    BLUE = 0
    BROWN = 1
    GREY = 2


class HairColor(Enum):
    BLACK = 4
    BROWN = 1
    BLOND = 0
    RED = 3


class BloodType(Enum):
    A = 0
    B = 1
    AB = 2


class Height(Enum):
    SMALL = 0
    MEDIUM = 1
    TALL = 2


class Hand(Enum):
    RIGHT = 0
    LEFT = 1


genotypes = [Gender, HairColor, EyeColor, Height, BloodType, Height, Hand]
criterions = list(itertools.chain(*[
    list(genotype) for genotype in genotypes]))


def get_random_enum(enum, p=None):
    data = list(enum)
    if p is None:
        p = [1/len(data) for _ in range(len(data))]
    return choices(data, weights=p, k=1)[0]


def get_random_eye_color():
    return get_random_enum(EyeColor)


def get_random_hair_color():
    return get_random_enum(HairColor, p=[4, 3, 2, 1])


def get_random_gender():
    return get_random_enum(Gender)


def get_random_blood_type():
    return get_random_enum(BloodType)


def get_random_height():
    return get_random_enum(Height, p=[.3, .4, .3])


def get_random_hand():
    return get_random_enum(Hand, p=[.8, .2])
