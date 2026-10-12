"""Clues: a piece of evidence, found somewhere, that reveals one trait of the murderer."""

from genotype import BloodType, EyeColor, Gender, HairColor, Hand, Height, LinkToVictim
from modality import Location


class Clue:
    """Evidence at `location` revealing the murderer's value for `trait`.

    `text` is what the player reads on finding it. `conditions` restricts the clue to
    cases where one of these facts is also revealed (a death-threat letter makes no
    sense if the killer is a stranger).
    """

    trait = None
    name = "clue"

    def __init__(self, location, text, conditions=None):
        self.location, self.text, self.conditions = location, text, conditions

    def is_consistent(self, facts):
        """True if the clue can exist alongside the revealed `facts`."""
        return self.conditions is None or any(c in facts for c in self.conditions)

    def __repr__(self):
        return f"{self.name}_{self.location.name}"


class LinkClue(Clue):
    trait, name = LinkToVictim, "link"


class EyeColorClue(Clue):
    trait, name = EyeColor, "eye_color"


class HairClue(Clue):
    trait, name = HairColor, "hair_color"


class HandClue(Clue):
    trait, name = Hand, "hand"


class GenderClue(Clue):
    trait, name = Gender, "gender"


class BloodTypeClue(Clue):
    trait, name = BloodType, "blood_type"


class HeightClue(Clue):
    trait, name = Height, "height"


KNOWN = [LinkToVictim.SIBLING, LinkToVictim.COLLEAGUE, LinkToVictim.NEIGHBORHOOD, LinkToVictim.PARTNER]

CLUES = [
    GenderClue(Location.WITNESS, "J'ai croisé quelqu'un qui sortait en courant de chez la victime."),
    GenderClue(Location.NEIGHBOR, "J'ai entendu une dispute à travers le mur, et une voix."),
    GenderClue(Location.CCTV, "Une silhouette passe devant la caméra, capuche relevée, mais la démarche ne trompe pas."),
    GenderClue(Location.VICTIM_PHONE, "Un message vocal menaçant est resté sur le répondeur."),

    LinkClue(Location.VICTIM_HOUSE, "Une lettre de menace glissée sous la porte : son auteur connaissait bien la victime.",
             KNOWN + [LinkToVictim.EX]),
    LinkClue(Location.MURDERER_HOUSE, "Des échanges datés évoquent le cercle de la victime, sans identifier son agresseur.", KNOWN),
    LinkClue(Location.MURDERER_HOUSE, "Des annonces et un carnet de contacts rappellent que la victime rencontrait aussi des personnes extérieures à son cercle.",
             [LinkToVictim.UNKNOWN]),
    LinkClue(Location.CRIME_SCENE, "Une violence démesurée. On ne frappe pas comme ça un inconnu : c'est une affaire de famille.",
             [LinkToVictim.SIBLING]),
    LinkClue(Location.CRIME_SCENE, "La victime a écrit quelque chose au mur en mourant : elle connaissait son agresseur.",
             [LinkToVictim.SIBLING, LinkToVictim.EX]),
    LinkClue(Location.CRIME_SCENE, "Un coup froid, la maison fouillée, les objets de valeur envolés. Quelqu'un du quartier.",
             [LinkToVictim.NEIGHBORHOOD]),
    LinkClue(Location.VICTIM_PHONE, "Des SMS de menace, signés d'un membre de la famille.", [LinkToVictim.SIBLING]),
    LinkClue(Location.VICTIM_PHONE, "Des mails de harcèlement, envoyés depuis le travail de la victime.", [LinkToVictim.COLLEAGUE]),

    HandClue(Location.VICTIM_HOUSE, "La lettre de menace est écrite à la main : l'inclinaison des lettres trahit son auteur.", KNOWN),
    HandClue(Location.MURDER_WEAPON, "La prise sur le manche, l'angle du coup : on devine la main qui a tenu l'arme."),
    HandClue(Location.WITNESS, "J'ai vu l'arme, et la main qui la tenait."),

    HairClue(Location.WITNESS, "Je me souviens surtout de la chevelure."),
    HairClue(Location.CRIME_SCENE, "Un cheveu accroché au montant de la porte. Ce n'est pas celui de la victime."),
    HairClue(Location.CCTV, "Sur l'enregistrement, la lumière du lampadaire accroche une chevelure."),
    HairClue(Location.VICTIM, "Le légiste a trouvé un cheveu sous les ongles de la victime."),
    HairClue(Location.MURDER_WEAPON, "Un cheveu collé sur le manche de l'arme."),
    HairClue(Location.VICTIM_PHONE, "Une photo prise par la victime quelques heures avant : quelqu'un de dos, les cheveux bien visibles."),

    EyeColorClue(Location.WITNESS, "J'ai croisé un regard que je n'oublierai pas."),
    EyeColorClue(Location.VICTIM_PHONE, "Une photo sur le téléphone, prise de très près. Un regard."),

    BloodTypeClue(Location.CRIME_SCENE, "La victime s'est défendue. Du sang sur la clôture, qui ne semble pas lui appartenir."),
    BloodTypeClue(Location.VICTIM, "Du sang sous les ongles de la victime : elle a griffé son agresseur."),
    BloodTypeClue(Location.MURDER_WEAPON, "Du sang sur l'arme, là où la main a glissé. Ce n'est pas celui de la victime."),

    HeightClue(Location.WITNESS, "Je me souviens d'une silhouette, de loin."),
    HeightClue(Location.CRIME_SCENE, "Une empreinte de pas dans l'herbe, sous la fenêtre."),
]
