"""The city map and the labels the client needs to describe it."""

from genotype import BloodType, EyeColor, Gender, HairColor, Hand, Height, LinkToVictim
from modality import Location

# the city is a grid; streets join horizontal and vertical neighbours
GRID = [
    ["alley", "crime_scene", "victim_street", "victim_house"],
    ["cctv", "bar", "police", None],
    ["theater", "pool", "hospital", None],
]
LABELS = {
    "crime_scene": "Scène de crime", "alley": "Ruelle", "victim_street": "Rue Verlaine",
    "victim_house": "Chez la victime", "police": "Commissariat", "hospital": "Hôpital",
    "bar": "Bar", "cctv": "Local CCTV", "theater": "Théâtre", "pool": "Piscine",
}


def _streets():
    adj = {p: [] for row in GRID for p in row if p}
    for r, row in enumerate(GRID):
        for c, p in enumerate(row):
            for rr, cc in ((r, c + 1), (r + 1, c)):
                q = p and rr < len(GRID) and cc < len(GRID[rr]) and GRID[rr][cc]
                if q:
                    adj[p].append(q)
                    adj[q].append(p)
    return {p: (LABELS[p], n) for p, n in adj.items()}


STREETS = _streets()
START = "crime_scene"
HANGOUTS = ["bar", "theater", "pool", "hospital"]
RESIDENTIAL = ["victim_street", "alley", "theater", "pool"]

LOCKED = {"victim_house"}  # plus every suspect's house
TAPED = {"crime_scene"}  # police tape: authorization or stealth
SECURED = {"cctv"}  # authorization or hacking kit

NAMES = {
    Gender.FEMALE: ["Ada", "Chloé", "Elsa", "Gaëlle", "Inès", "Léa", "Nadia", "Paloma", "Rose", "Tess",
                    "Vera", "Xenia", "Zoé", "Anaïs", "Capucine", "Maya", "Salomé", "Lison"],
    Gender.MALE: ["Bruno", "Dimitri", "Farid", "Hugo", "Jules", "Karim", "Marius", "Oscar", "Quentin", "Sacha",
                  "Ulysse", "Wassim", "Yann", "Bastien", "Driss", "Elio", "Gaspard", "Noé"],
}

TRAIT_LABELS = {
    Gender: "genre", HairColor: "cheveux", EyeColor: "yeux", Height: "taille",
    BloodType: "sang", Hand: "main", LinkToVictim: "lien",
}
TRAIT_TEXT = {
    Gender.FEMALE: "femme", Gender.MALE: "homme",
    HairColor.BLACK: "noirs", HairColor.BROWN: "châtains", HairColor.BLOND: "blonds", HairColor.RED: "roux",
    EyeColor.BROWN: "marron", EyeColor.BLUE: "bleus", EyeColor.GREY: "gris", EyeColor.GREEN: "verts",
    Height.SMALL: "petite", Height.MEDIUM: "moyenne", Height.TALL: "grande",
    BloodType.A: "A", BloodType.B: "B", BloodType.AB: "AB", BloodType.O: "O",
    Hand.RIGHT: "droite", Hand.LEFT: "gauche",
    LinkToVictim.SIBLING: "famille", LinkToVictim.NEIGHBORHOOD: "voisinage", LinkToVictim.COLLEAGUE: "collègue",
    LinkToVictim.EX: "ex", LinkToVictim.UNKNOWN: "inconnu",
}
LINK_QUOTES = {
    LinkToVictim.SIBLING: "On a grandi ensemble, c'était ma famille.",
    LinkToVictim.NEIGHBORHOOD: "On se croisait dans le quartier, sans plus.",
    LinkToVictim.COLLEAGUE: "On travaillait ensemble.",
    LinkToVictim.EX: "On a été ensemble. C'est fini depuis longtemps.",
    LinkToVictim.UNKNOWN: "Je ne connaissais pas cette personne.",
}
# what a passer-by sees from the street, vs. what needs a closer look
FAR_TRAITS = [Gender, Height, HairColor]


def fact_label(fact):
    return f"{TRAIT_LABELS[type(fact)]} {TRAIT_TEXT[fact]}"


def glimpse(suspect):
    """Seen from afar: 'femme, carrure moyenne, cheveux blonds'."""
    return f"{TRAIT_TEXT[suspect[Gender]]}, carrure {TRAIT_TEXT[suspect[Height]]}, cheveux {TRAIT_TEXT[suspect[HairColor]]}"


def statement(fact):
    """A fact as someone would state it: 'C'était une femme.'"""
    value = TRAIT_TEXT[fact]
    return {
        Gender: f"C'était {'une femme' if fact is Gender.FEMALE else 'un homme'}.",
        HairColor: f"Les cheveux {value}, ça j'en suis sûr.", EyeColor: f"Des yeux {value}.",
        Height: f"Une {value} carrure.", Hand: f"L'arme était dans la main {value}.",
    }[type(fact)]


def portrait(suspect, hand_noticed):
    """Up close: a short written impression."""
    she = suspect[Gender] is Gender.FEMALE
    text = (f"Je vois {'une femme' if she else 'un homme'} aux cheveux {TRAIT_TEXT[suspect[HairColor]]} "
            f"et aux yeux {TRAIT_TEXT[suspect[EyeColor]]}. {TRAIT_TEXT[suspect[Height]].capitalize()} carrure.")
    if hand_noticed:
        text += f" {'Elle' if she else 'Il'} tient son verre de la main {TRAIT_TEXT[suspect[Hand]]}."
    return text


# said once, the first time a player gets there
PLACE_HINTS = {
    "police": "Ici on demande les autorisations, on consulte les casiers, et on accuse quand on est sûr : une erreur coûte 2 tours.",
    "hospital": "La morgue, et les dossiers médicaux des suspects si l'infirmière se laisse convaincre.",
    "crime_scene": "Le ruban de police n'empêche pas de fouiller, mais sans autorisation il faut être discret.",
    "cctv": "Les enregistrements de la rue. Autorisation ou kit de hacking.",
    "victim_house": "Lettres, affaires personnelles, et sans doute le code du téléphone.",
    "alley": "Les poubelles de la ruelle. Ce qu'on jette en partant vite finit ici.",
    "bar": "On y croise du monde.",
}

EVIDENCE_LABELS = {
    Location.WITNESS: "Un témoignage", Location.NEIGHBOR: "Un témoignage", Location.CCTV: "Enregistrement CCTV",
    Location.VICTIM_PHONE: "Téléphone de la victime", Location.VICTIM_HOUSE: "Lettre de menace",
    Location.VICTIM: "Le corps, à la morgue", Location.MURDER_WEAPON: "L'arme du crime",
    Location.MURDERER_HOUSE: "Quelque chose de louche", Location.CRIME_SCENE: "Traces sur les lieux",
}


def evidence_label(clue):
    if clue.trait is BloodType:
        return "Traces de sang"
    if clue.trait is HairColor and clue.location in (Location.CRIME_SCENE, Location.MURDER_WEAPON):
        return "Un cheveu"
    if clue.trait is Height and clue.location is Location.CRIME_SCENE:
        return "Empreinte de pas"
    return EVIDENCE_LABELS[clue.location]


def build_map(rng, n_suspects):
    """Copy the static map and hook one house per suspect onto a residential street."""
    places = {k: (label, list(v)) for k, (label, v) in STREETS.items()}
    for number, i in enumerate(rng.sample(range(n_suspects), n_suspects), 1):  # shuffled: n°1 is not the murderer
        street = rng.choice(RESIDENTIAL)
        places[f"house_{i}"] = (f"Maison n°{number}", [street])
        places[street][1].append(f"house_{i}")
    return places
