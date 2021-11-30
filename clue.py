from genotype import *
from modality import *


class Clue:
    def __init__(self, location, conditions=None):
        self.location = location
        self.conditions = conditions


class LinkClue(Clue):
    clue_type = LinkToVictim

class EyeColorClue(Clue):
    clue_type = EyeColor


class HairClue(Clue):
    clue_type = HairColor


class HandClue(Clue):
    clue_type = HairColor


class GenderClue(Clue):
    clue_type = Gender


class BloodTypeClue(Clue):
    clue_type = BloodType


class HeightClue(Clue):
    clue_type = Height


clues = [
    # witness saw gender
    GenderClue(location.WITNESS),
    # neighbors heard screams (gender)
    GenderClue(location.NEIGHBOR),
    # gender caught on CCTV
    GenderClue(location.CCTV),
    # gender caught on phone
    GenderClue(location.VICTIM_PHONE),

    # link to victim revealed in a death-threat letter
    LinkClue(location.VICTIM_HOUSE, [
        LinkToVictim.SIBLING, LinkToVictim.COLLEAGUE, LinkToVictim.NEIGHBORHOOD]),
    # link to victim revealed during a lie
    LinkClue(location.MURDERER_HOUSE, [
        LinkToVictim.SIBLING, LinkToVictim.COLLEAGUE, LinkToVictim.NEIGHBORHOOD]),
    # amount of violence suggests passion
    LinkClue(location.CRIME_SCENE, [
        LinkToVictim.SIBLING]),
    # robbery suggests victim doesn't know the killer
    LinkClue(location.CRIME_SCENE, [
        LinkToVictim.SIBLING]),

    # hand revealed in a death-threat letter
    HandClue(location.VICTIM_HOUSE, [
        LinkToVictim.SIBLING, LinkToVictim.COLLEAGUE, LinkToVictim.NEIGHBORHOOD]),
    # hand revealed in a death-threat letter
    HandClue(location.MURDER_WEAPON),
    # witness saw hand
    HandClue(location.WITNESS),

    # witness saw hair color
    HairClue(location.WITNESS),
    # hair found at the crime scene
    HairClue(location.CRIME_SCENE),
    # hair found at the victim's house
    HairClue(location.VICTIM_HOUSE),
    # hair color caught on CCTV
    HairClue(location.CCTV),
    # hair found under the victim's fingernails
    HairClue(location.VICTIM),
    # hair found on the murder weapon
    HairClue(location.MURDER_WEAPON),
    # hair color caught on phone
    HairClue(location.VICTIM_PHONE),

    # witness saw eye color
    EyeColorClue(location.WITNESS),
    # eye color caught on phone
    EyeColorClue(location.VICTIM_PHONE),

    # murderer blood found at the crime scene (UV light, fences)
    BloodTypeClue(location.CRIME_SCENE),
    # murderer blood found under the victim's fingernails
    BloodTypeClue(location.VICTIM),
    # murderer blood found on the murder weapon
    BloodTypeClue(location.MURDER_WEAPON),
    # victim blood found on the murder weapon
    BloodTypeClue(location.MURDERER_HOUSE),

    # witness saw height
    HeightClue(location.WITNESS),
    # large footstep found in grass
    HeightClue(location.CRIME_SCENE),
]


