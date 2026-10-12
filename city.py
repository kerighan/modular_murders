"""The city map and the labels the client needs to describe it."""

from genotype import BloodType, EyeColor, Gender, HairColor, Hand, Height, LinkToVictim
from modality import Location

# the city is a grid; streets join horizontal and vertical neighbours
GRID = [
    ["alley", "crime_scene", "victim_street", None, "victim_house"],
    ["cctv", "bar", "police", None, None],
    ["cabaret", "den", "hospital", None, None],
    [None, None, "restaurant", None, None],
]
# Empty cells can be occupied by a neighboring building's extended footprint.
# The suspended bridge connects the residential places across the enlarged parcel.
SKYBRIDGES = (("victim_street", "victim_house"),)
LABELS = {
    "crime_scene": "Scène de crime", "alley": "Ruelle", "victim_street": "Rue Verlaine",
    "victim_house": "Chez la victime", "police": "Commissariat", "hospital": "Hôpital",
    "bar": "Le Néon Bleu", "cctv": "Régie vidéo", "cabaret": "Le Palace", "den": "Le Tripot",
    "restaurant": "Le Comptoir",
}


def _streets(grid=None):
    grid = GRID if grid is None else grid
    adj = {p: [] for row in grid for p in row if p}
    for r, row in enumerate(grid):
        for c, p in enumerate(row):
            for rr, cc in ((r, c + 1), (r + 1, c)):
                q = p and rr < len(grid) and cc < len(grid[rr]) and grid[rr][cc]
                if q:
                    adj[p].append(q)
                    adj[q].append(p)
    for a, b in SKYBRIDGES:
        if b not in adj[a]:
            adj[a].append(b)
            adj[b].append(a)
    return {p: (LABELS[p], n) for p, n in adj.items()}


STREETS = _streets()
START = "victim_street"  # default start, right outside the crime scene
HANGOUTS = ["bar", "cabaret", "den", "hospital", "restaurant"]
HANGOUT_WEIGHTS = [4, 3, 3, 1, 3]  # the hospital is nobody's idea of a night out, but someone works there
RESIDENTIAL = ["victim_street", "alley", "cabaret", "den"]

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
    LinkToVictim.PARTNER: "partenaire amoureux",
}
LINK_QUOTES = {
    LinkToVictim.SIBLING: "On a grandi ensemble, c'était ma famille.",
    LinkToVictim.NEIGHBORHOOD: "On se croisait dans le quartier, sans plus.",
    LinkToVictim.COLLEAGUE: "On travaillait ensemble.",
    LinkToVictim.EX: "On a été ensemble. C'est fini depuis longtemps.",
    LinkToVictim.UNKNOWN: "Je ne connaissais pas cette personne.",
    LinkToVictim.PARTNER: "On était ensemble. C'était mon amour.",
}
# what a passer-by sees from the street, vs. what needs a closer look
FAR_TRAITS = [Gender, Height, HairColor]


def fact_label(fact):
    return f"{TRAIT_LABELS[type(fact)]} {TRAIT_TEXT[fact]}"


LINK_SENTENCE = {
    LinkToVictim.SIBLING: "fait probablement partie de la famille de la victime",
    LinkToVictim.NEIGHBORHOOD: "est probablement du voisinage de la victime",
    LinkToVictim.COLLEAGUE: "est probablement un collègue de la victime",
    LinkToVictim.EX: "est probablement un ex de la victime",
    LinkToVictim.UNKNOWN: "ne connaissait probablement pas la victime",
    LinkToVictim.PARTNER: "était en couple avec la victime",
}


def fact_sentence(fact):
    """What a clue tells: 'le meurtrier a probablement les yeux marron'."""
    value = TRAIT_TEXT[fact]
    tail = {
        Gender: f"est probablement {'une femme' if fact is Gender.FEMALE else 'un homme'}",
        HairColor: f"a probablement les cheveux {value}", EyeColor: f"a probablement les yeux {value}",
        Height: f"est probablement de {value} carrure", BloodType: f"est probablement du groupe sanguin {value}",
        Hand: f"se sert probablement de la main {value}", LinkToVictim: LINK_SENTENCE.get(fact),
    }[type(fact)]
    return f"le meurtrier {tail}"


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


# what gives the dominant hand away, depending on where you meet them
HAND_SCENES = {
    "restaurant": ["tient sa fourchette de la main {}", "verse de l'eau de la main {}",
                   "replie sa serviette de la main {}"],
    "bar": ["tient son verre de la main {}", "fait tourner un briquet dans sa main {}", "signe l'ardoise de la main {}",
            "lance les dés sur le comptoir de la main {}"],
    "den": ["pousse ses jetons de la main {}", "abat ses cartes de la main {}", "fait rouler les dés de la main {}",
            "tient la queue de billard de la main {}"],
    "cabaret": ["tient sa cigarette de la main {}", "lève son verre de la main {}", "tend son billet de la main {}",
                "griffonne un mot sur une serviette de la main {}"],
    "hospital": ["signe le registre de la main {}", "remplit un formulaire de la main {}",
                 "tient son gobelet de café de la main {}"],
    "home": ["tient sa tasse de café de la main {}", "signe le reçu du livreur de la main {}",
             "rattrape son chat de la main {}", "retire la chaîne de la porte de la main {}",
             "tient une cigarette au coin de la fenêtre, de la main {}"],
}


def hand_scene(suspect, place, rng):
    """'Elle tient son verre de la main gauche.'"""
    she = suspect[Gender] is Gender.FEMALE
    scene = rng.choice(HAND_SCENES.get(place, HAND_SCENES["home"])).format(TRAIT_TEXT[suspect[Hand]])
    return f"{'Elle' if she else 'Il'} {scene}."


def portrait(suspect, hand_noticed, place, rng):
    """Up close: a short written impression."""
    she = suspect[Gender] is Gender.FEMALE
    text = (f"Je vois {'une femme' if she else 'un homme'} aux cheveux {TRAIT_TEXT[suspect[HairColor]]} "
            f"et aux yeux {TRAIT_TEXT[suspect[EyeColor]]}. {TRAIT_TEXT[suspect[Height]].capitalize()} carrure.")
    if hand_noticed:
        text += " " + hand_scene(suspect, place, rng)
    return text


# how one searches a place: (menu label, verb used when something turns up)
SEARCH = {
    "hospital": ("Examiner le corps à la morgue", "Vous examinez"),
    "cctv": ("Visionner les enregistrements", "Vous visionnez"),
    "crime_scene": ("Fouiller la scène de crime", "Vous trouvez"),
    "alley": ("Fouiller les poubelles de la ruelle", "Vous trouvez"),
    "victim_house": ("Fouiller l'appartement", "Vous trouvez"),
}
SEARCH_DEFAULT = ("Fouiller les lieux", "Vous trouvez")

# said once, the first time a player gets there
PLACE_HINTS = {
    "restaurant": "Cuisine ouverte, tables serrées et lumière ambrée. On s'attarde au Comptoir après le travail.",
    "police": "Ici on demande les autorisations, on consulte les casiers, et on accuse quand on est sûr : une erreur coûte 2 tours.",
    "hospital": "La morgue, et les dossiers médicaux des suspects si l'infirmière se laisse convaincre.",
    "crime_scene": "Sans autorisation, une seule fouille discrète, et rien de ce qui s'emporte.",
    "cctv": "Les écrans de surveillance du quartier. Autorisation ou kit de hacking.",
    "victim_house": "Lettres, affaires personnelles, et des bribes de la vie de la victime.",
    "alley": "Les poubelles de la ruelle. Ce qu'on jette en partant vite finit ici.",
    "bar": "Un bar mal famé, néon qui grésille. On y croise du monde.",
    "den": "Cartes, jetons et dettes. Le genre d'endroit où personne n'a rien vu.",
    "cabaret": "Rideaux lourds, paillettes fatiguées. On y vient pour voir, et pour être vu.",
}

EVIDENCE_LABELS = {
    Location.WITNESS: "Un témoignage", Location.NEIGHBOR: "Un témoignage", Location.CCTV: "Enregistrement CCTV",
    Location.VICTIM_PHONE: "Téléphone de la victime", Location.VICTIM_HOUSE: "Lettre de menace",
    Location.VICTIM: "Le corps, à la morgue", Location.MURDER_WEAPON: "L'arme du crime",
    Location.MURDERER_HOUSE: "Quelque chose de louche", Location.CRIME_SCENE: "Traces sur les lieux",
}


def evidence_label(clue):
    """One label per physical object: every clue the weapon carries is 'L'arme du crime'."""
    if clue.location in (Location.MURDER_WEAPON, Location.VICTIM_PHONE):
        return EVIDENCE_LABELS[clue.location]
    if clue.trait is BloodType:
        return "Traces de sang"
    if clue.trait is HairColor and clue.location is Location.CRIME_SCENE:
        return "Un cheveu"
    if clue.trait is Height and clue.location is Location.CRIME_SCENE:
        return "Empreinte de pas"
    return EVIDENCE_LABELS[clue.location]


def build_map(rng, n_suspects, grid=None):
    """Copy the static map and hook one house per suspect onto a residential street."""
    streets = STREETS if grid is None else _streets(grid)
    places = {k: (label, list(v)) for k, (label, v) in streets.items()}
    for number, i in enumerate(rng.sample(range(n_suspects), n_suspects), 1):  # shuffled: n°1 is not the murderer
        street = rng.choice(RESIDENTIAL)
        places[f"house_{i}"] = (f"Appart. n°{number}", [street])
        places[street][1].append(f"house_{i}")
    return places
