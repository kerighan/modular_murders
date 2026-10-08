"""Places of the investigation."""

from enum import Enum


class Location(Enum):
    """Where a clue can be found."""

    CRIME_SCENE = 0
    HOSPITAL = 1
    POLICE = 2
    WITNESS = 4
    VICTIM = 5
    CCTV = 6
    VICTIM_PHONE = 7
    MURDER_WEAPON = 8
    NEIGHBOR = 9
    VICTIM_HOUSE = 10
    MURDERER_HOUSE = 11


class Landmark(Enum):
    """Generic places that may appear on the map."""

    HOSPITAL = 0
    POLICE = 1
    BAR = 2
    THEATER = 3
