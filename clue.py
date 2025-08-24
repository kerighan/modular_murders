"""Clue objects relating evidence locations to suspect traits."""

from genotype import (
    Alibi,
    BloodType,
    EyeColor,
    Gender,
    HairColor,
    Hand,
    Height,
    LinkToVictim,
)
from modality import location


class Clue:
    """Base class for all clues.

    Each clue has a ``location`` describing where it was found and optional
    ``conditions`` restricting when the clue is valid.
    """

    def __init__(self, location, conditions=None):
        self.location = location
        self.conditions = conditions

    def check_conditions(self, facts):
        """Return ``True`` if this clue is compatible with the given facts."""

        if self.conditions is None:
            return True

        for condition in self.conditions:
            if condition in facts:
                # One satisfied condition is enough to validate the clue.
                return True
        return False

    def __repr__(self):
        return f"{self.clue_name}_{self.location.name}"


class LinkClue(Clue):
    """Clue describing the relationship between suspect and victim."""

    clue_type = LinkToVictim
    clue_name = "link"


class EyeColorClue(Clue):
    """Clue revealing the eye colour of the suspect."""

    clue_type = EyeColor
    clue_name = "eye_color"


class HairClue(Clue):
    """Clue revealing hair colour."""

    clue_type = HairColor
    clue_name = "hair_color"


class HandClue(Clue):
    """Clue revealing dominant hand."""

    clue_type = Hand
    clue_name = "hand"


class GenderClue(Clue):
    """Clue revealing gender."""

    clue_type = Gender
    clue_name = "gender"


class BloodTypeClue(Clue):
    """Clue revealing blood type."""

    clue_type = BloodType
    clue_name = "blood_type"


class HeightClue(Clue):
    """Clue revealing rough height."""

    clue_type = Height
    clue_name = "height"


class AlibiClue(Clue):
    """Special clue representing an alibi offered by a suspect."""

    clue_type = Alibi


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
        LinkToVictim.SIBLING, LinkToVictim.COLLEAGUE, LinkToVictim.NEIGHBORHOOD, LinkToVictim.EX]),
    # link to victim revealed during a lie
    LinkClue(location.MURDERER_HOUSE, [
        LinkToVictim.SIBLING, LinkToVictim.COLLEAGUE, LinkToVictim.NEIGHBORHOOD]),
    # shows a troubled mind that kills strangers
    LinkClue(location.MURDERER_HOUSE, [
        LinkToVictim.UNKNOWN]),
    # amount of violence suggests passion
    LinkClue(location.CRIME_SCENE, [
        LinkToVictim.SIBLING]),
    # victim writing on the wall : victim knows the killer
    LinkClue(location.CRIME_SCENE, [
        LinkToVictim.SIBLING, LinkToVictim.EX]),
    # cold blooded and robbed suggest unknown relation
    LinkClue(location.CRIME_SCENE, [
        LinkToVictim.NEIGHBORHOOD]),
    # victim was threaten by a sibling
    LinkClue(location.VICTIM_PHONE, [
        LinkToVictim.SIBLING]),
    # victim was harcelated and threaten by a coworker
    LinkClue(location.VICTIM_PHONE, [
        LinkToVictim.COLLEAGUE]),

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

    # witness saw height
    HeightClue(location.WITNESS),
    # large footstep found in grass
    HeightClue(location.CRIME_SCENE),
]
