from enum import Enum

from clue import get_random_enum


class Routine:
    pass


class VictimPhoneRoutine(Enum):
    NEXT_TO_VICTIM = 0
    TRASH_CAN = 1
    LOST = 2


class VictimPhoneLockRoutine(Enum):
    LOCK_BIRTHDAY = 0
    LOCK_PET = 1
    LOCK_MEMO = 3
    UNLOCK = 2


class MurderWeaponRoutine(Enum):
    NEXT_TO_VICTIM = 0
    TRASH_CAN = 1
    LOST = 2


def get_random_murder_weapon_routine():
    return get_random_enum(MurderWeaponRoutine)


def get_random_victim_phone_routine():
    return get_random_enum(VictimPhoneRoutine)


def get_random_victim_phone_lock_routine():
    return get_random_enum(VictimPhoneLockRoutine)
