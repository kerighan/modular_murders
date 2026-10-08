"""Random routines: how the physical evidence ends up in the world."""

from enum import Enum


class VictimPhoneRoutine(Enum):
    """Where the victim's phone is after the murder."""

    NEXT_TO_VICTIM = 0
    TRASH_CAN = 1
    LOST = 2


class VictimPhoneLockRoutine(Enum):
    """How the victim's phone is locked (the code is found at the victim's house)."""

    LOCK_BIRTHDAY = 0
    LOCK_PET = 1
    LOCK_MEMO = 3
    UNLOCK = 2


class MurderWeaponRoutine(Enum):
    """Where the murder weapon is left."""

    NEXT_TO_VICTIM = 0
    TRASH_CAN = 1
    LOST = 2
