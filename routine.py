"""Random routines describing how evidence might appear in the world."""

from enum import Enum

# Import the random Enum selector directly from the genetics module to avoid
# leaking it through ``clue``.
from genotype import get_random_enum


class Routine:
    """Base class reserved for future routine-related behaviours."""

    pass


class VictimPhoneRoutine(Enum):
    """Where the victim's phone ends up after the murder."""

    NEXT_TO_VICTIM = 0
    TRASH_CAN = 1
    LOST = 2


class VictimPhoneLockRoutine(Enum):
    """Describes how the victim's phone is locked."""

    LOCK_BIRTHDAY = 0
    LOCK_PET = 1
    LOCK_MEMO = 3
    UNLOCK = 2


class MurderWeaponRoutine(Enum):
    """Where the murder weapon is left."""

    NEXT_TO_VICTIM = 0
    TRASH_CAN = 1
    LOST = 2


def get_random_murder_weapon_routine():
    """Randomly choose a routine for the murder weapon."""

    return get_random_enum(MurderWeaponRoutine)


def get_random_victim_phone_routine():
    """Randomly choose where the victim's phone is found."""

    return get_random_enum(VictimPhoneRoutine)


def get_random_victim_phone_lock_routine():
    """Randomly choose how the victim's phone is locked."""

    return get_random_enum(VictimPhoneLockRoutine)
