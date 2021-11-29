from genotype import *


class Clue:
    def __init__(self):
        pass


class HairClue(Clue):
    clue_type = HairColor


class GenderClue(Clue):
    clue_type = Gender


class BloodTypeClue(Clue):
    clue_type = BloodType
