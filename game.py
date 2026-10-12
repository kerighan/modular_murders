"""The engine: a Case dropped into the city, and players acting on it turn by turn.

Pure and deterministic given a seed: no I/O. The client shows the events returned by
`play()`, lists `options()` for the current player, resolves challenges (QTEs) through
`challenge(kind, difficulty) -> score in [0, 1]`, and voices characters through
`speak(persona, dialogue, question, intent) -> str`. Both default to offline stubs.
A binary obstacle is passed when the score reaches its difficulty; an interrogation
grants one question per quarter of score.
"""

import random
from collections import deque

from city import (FAR_TRAITS, GRID, HANGOUT_WEIGHTS, HANGOUTS, LINK_QUOTES, TRAIT_LABELS, LOCKED, NAMES, PLACE_HINTS, SEARCH, SEARCH_DEFAULT, SECURED, START, TAPED,
                  TRAIT_TEXT, build_map,
                  evidence_label, fact_label, fact_sentence, glimpse, hand_scene, portrait, statement)
from clue import CLUES
from genotype import TRAITS, BloodType, EyeColor, Gender, Hand, LinkToVictim, get_random_enum
from modality import Location
from routine import MurderWeaponRoutine, VictimPhoneLockRoutine, VictimPhoneRoutine
from suspect import Case
from narrative import CaseStory

AP = 3  # action points per turn
RULES_VERSION = 13  # Current-partner trait changes seeded cases; never replay v12 as v13.
PENALTY = 2  # turns lost on a wrong accusation
QUESTIONS_PER_INTERROGATION = 3
ROUTINE_HOME = (1, 4)  # turns spent at home per cycle, drawn once per suspect: homebodies and night owls
ROUTINE_OUT = (1, 4)  # turns spent at the hangout per cycle
ALIBI_ODDS = 2  # a bystander remembers an innocent with 1 chance in ALIBI_ODDS; the murderer never
BYSTANDER = {"bar": "Le barman", "den": "Le croupier", "cabaret": "L'ouvreuse", "hospital": "L'infirmière de garde", "restaurant": "Le serveur"}
SERVICE_STAFF = {
    "restaurant": ("Le serveur", "cheveux noirs", -27, {"verify", "check_timeline"}),
    "bar": ("Le barman", "cheveux noirs", -21, {"verify", "check_timeline"}),
    "den": ("Le croupier", "cheveux blonds", -22, {"verify", "check_timeline"}),
    "cabaret": ("L'ouvreuse", "cheveux roux", -23, {"verify", "check_timeline"}),
    "hospital": ("L'infirmière de garde", "cheveux noirs", -24, {"verify", "file", "lab", "victim_file", "check_timeline"}),
    "police": ("Le commissaire", "cheveux blonds", -25, {"authorize", "record", "accuse", "check_timeline"}),
    "cctv": ("La technicienne vidéo", "cheveux roux", -26, {"check_timeline"}),
}
ITEMS = {
    "crowbar": "Pied de biche : ouvre les portes fermées",
    "forensic_kit": "Kit médico-légal : analyse le sang sur place",
    "hacking_kit": "Kit de hacking : téléphone et CCTV sans code ni autorisation",
    "taxi": "Carte taxi : aller n'importe où pour 1 PA",
    "filon": "Filon : un suspect déjà identifié au départ",
    "contact_police": "Contact au commissariat : commencer sur place, et 4 casiers au lieu de 2",
    "contact_hospital": "Contact à l'hôpital : commencer sur place, et 4 dossiers médicaux au lieu de 2",
    "victim_key": "Clé de la victime : commencer chez elle, porte ouverte",
}
FREE_STARTS = ["victim_street", "alley", "bar", "cabaret", "den", "restaurant"]  # never the crime scene: too good a spot
PAID_STARTS = {"police": "contact_police", "hospital": "contact_hospital", "victim_house": "victim_key"}  # place -> item
QUESTIONS = {
    "alibi": "Où étiez-vous le soir du meurtre ?",
    "link": "Vous connaissiez la victime ?",
    "seen": "Vous avez vu ou entendu quelque chose ?",
    "grudge": "Qui aurait pu lui en vouloir ?",
    "life": "Qu'est-ce qui vous préoccupe en ce moment ?",
}
NIGHT_TEXT = {"bar": "au Néon Bleu", "den": "au Tripot", "cabaret": "au Palace", "hospital": "à l'hôpital", "restaurant": "au Comptoir", "home": "chez moi"}
HOME_RATE = .35  # chance an innocent spent the night at home, where nobody can vouch for them
RECALL = .6  # chance someone remembers a given person who was there with them
GOSSIP_WEIGHT = 2  # how much more often rumours point at the murderer than at any innocent
GOSSIP_RATE = .5  # chance someone who knew the victim is willing to name a name
LIE_RATE = .5  # chance the murderer invents a description rather than claiming to have seen nothing
FAVORS = 2  # files the nurse (and records the police) will pull for you per window; 4 with a contact
FAVOR_RESET = 3  # turns before they forget your last requests
GRUDGE = {
    LinkToVictim.SIBLING: "de la famille, et ils ne se parlaient plus, une histoire d'héritage",
    LinkToVictim.NEIGHBORHOOD: "des histoires de voisinage qui ont mal tourné",
    LinkToVictim.COLLEAGUE: "ça se disputait au travail, tout le monde le savait",
    LinkToVictim.EX: "son ex, et la rupture n'est jamais vraiment passée",
}
MOODS = ["bavard et un peu trop content de parler", "méfiant, réponses courtes", "pressé, agacé d'être retenu",
         "blasé, fatigué de cette ville", "amical, veut aider", "nerveux, qui se justifie trop"]
OBJECT_PLACE = {"NEXT_TO_VICTIM": "crime_scene", "TRASH_CAN": "alley", "LOST": None}
PETS = ["Rex", "Mimi", "Pixel", "Nova", "Caramel", "Tango", "Biscotte", "Luna"]
SECRET_LABELS = {"birthday": "date de naissance", "pet": "nom de l'animal", "memo": "mémo"}


class Evidence:
    def __init__(self, id, clue, fact, place):
        self.id, self.clue, self.fact, self.place = id, clue, fact, place
        self.label, self.text = evidence_label(clue), clue.text
        self.person = clue.location in (Location.WITNESS, Location.NEIGHBOR)  # held by a suspect, see `who`
        self.phone = clue.location is Location.VICTIM_PHONE
        self.blood = clue.trait is BloodType
        self.portable = clue.location in (Location.VICTIM_PHONE, Location.MURDER_WEAPON)  # the finder pockets it
        self.who = None

    def __repr__(self):
        return f"{self.label} ({self.place})"


class Player:
    def __init__(self, name):
        self.name, self.place, self.ap, self.skip = name, START, AP, 0
        self.items = set()
        self.facts = set()  # murderer's trait values proven by physical evidence
        self.heard = {}  # suspect id -> facts they claimed; true unless they are the murderer
        self.found = set()  # evidence ids found, examined or not
        self.known = {}  # suspect id -> traits learned about them
        self.names = set()  # suspects whose name the player knows
        self.talked = set()  # suspects interrogated
        self.shunned = set()  # suspects who caught you in their house: they won't talk
        self.alibis = {}  # suspect id -> alibi confirmed? False heard, True confirmed, None checked and backed by nobody
        self.claims = {}  # suspect id -> (place that night, ids they say were with them)
        self.cleared = set()  # suspects proven innocent
        self.opened = set()  # doors forced
        self.authorized = False
        self.favor_max = {"hospital": FAVORS, "police": FAVORS}  # per window of FAVOR_RESET turns
        self.favors = dict(self.favor_max)  # files and records still owed to you in this window
        self.secrets = {}  # what they learned of the victim's life: kind -> value, possible phone codes
        self.tried = set()  # codes already refused
        self.unlocked = False  # cracked the victim's phone
        self.collected = set()  # lab results already read
        self.visited = set()
        self.exhausted = set()  # places searched through
        self.sneaked = set()  # taped places already searched without authorization: once only
        self.journal = []  # private notes, rebuilt by replay and saved verbatim
        self.story_found = set()
        self.story_examined = set()
        self.story_profiles = set()
        self.story_rumours = {}
        self.story_discussed = set()
        self.story_resolved = False
        self.timeline_verified = set()
        self.link_claims = {}
        self.link_witnesses = {}
        self.people_discussed = set()
        self.invited = set()
        self.thought_topics = set()  # private presentation, never certified evidence
        self.scenes_seen = set()  # private one-shot exchanges, restored by replay

    def knows(self, sid, trait=None):
        """Does the player know this trait of the suspect, or without a trait, their name?"""
        return trait in self.known.get(sid, ()) if trait else sid in self.names



def template_speak(persona, dialogue, question, intent):
    return intent


class Game:
    def __init__(self, seed=None, players=("Détective",), n_suspects=12, challenge=None, speak=None):
        self.seed = seed
        rng = self.rng = random.Random(seed)
        self.dice = random.Random(rng.random())  # default challenge rolls, kept apart so replays don't drift
        self.case = Case(seed=rng.random(), n_suspects=n_suspects)
        while self.blood_candidates() > FAVORS + 1:  # blood checks are scarce: they must only settle the last few
            self.case = Case(seed=rng.random(), n_suspects=n_suspects)
        n = self.n = n_suspects
        pools = {g: iter(rng.sample(names, n)) for g, names in NAMES.items()}
        self.names = [next(pools[self.case[i][Gender]]) for i in range(n)]
        self.order = rng.sample(range(n), n)  # display order: suspect 0 must not come first
        self.grid = [list(row) for row in GRID]
        city_rng = random.Random(f"nexus-city-v1:{seed}")
        self.crime_site = city_rng.choice(["canal", "traverses", "jeux"])
        if self.crime_site == "traverses":
            self.grid[0][0], self.grid[0][1] = self.grid[0][1], self.grid[0][0]
        elif self.crime_site == "jeux":
            self.grid[0][1], self.grid[3][1] = None, "crime_scene"
        self.map = build_map(rng, n, self.grid)
        self.hangout = {i: rng.choices(HANGOUTS, HANGOUT_WEIGHTS)[0] for i in range(n)}
        # daily routine: so many turns at home, so many out, cycles of different lengths and phases
        self.routine = {i: (rng.randint(*ROUTINE_HOME), rng.randint(*ROUTINE_OUT), rng.randrange(7)) for i in range(n)}
        self.night = self.reconstruct()  # where everyone was that night, by their own account
        # patchy memories: whom each one remembers among the people who were really there
        self.recall = {i: [t for t in self.company(i) if rng.random() < RECALL] for i in range(n)}
        self.mood = {i: rng.choice(MOODS) for i in range(n)}
        self.hand_visible = {i: rng.random() < .5 for i in range(n)}  # does their hand show up close?
        # whether the bystander remembers them that night: rolled once, the same answer for every player
        self.alibi_ok = {i: rng.randrange(ALIBI_ODDS) == 0 for i in range(n)}
        self.neighbor = rng.randrange(1, n)  # an innocent living next to the victim
        self.move_house(self.neighbor, "victim_street")
        self.evidence = self.place_evidence()
        self.secrets = self.victim_life()  # (kind, how it is found, value); one of them opens the phone
        self.lock = get_random_enum(VictimPhoneLockRoutine, rng=rng)
        self.code = {"LOCK_BIRTHDAY": "birthday", "LOCK_PET": "pet", "LOCK_MEMO": "memo", "UNLOCK": None}[self.lock.name]
        # With truthful innocents, exposing a fabricated account would itself
        # identify the sole liar. Refusals and partial knowledge replace that
        # unintended singleton evidence route.
        self.lie = None
        self.gossip = {i: self.pick_gossip(i) for i in range(n)}  # whom they point at
        self.players = [Player(name) for name in players]
        self.starts_chosen = [START] * len(self.players)
        self.current, self.tick, self.winner = 0, 0, None
        self.auto_end = False  # Used only to replay the automatic-turn legacy format.
        self.legacy_auto_end = 0
        self.pending = None  # ongoing interrogation: {"who", "left", "dialogue"}
        # Private, structured presentation of the last spoken line. Rules and the
        # legacy textual events remain unchanged; replay rebuilds this as well.
        self.dialogue_cues = {name: None for name in players}
        self.taken = {}  # evidence id -> player who pocketed it
        self.lab = []  # (evidence, who sent it, ready at tick): the hospital lab, open to anyone
        self.where = {}
        self.move_suspects()
        self.log = []  # (tick, author, text): the public record of what detectives did
        self.inbox = {name: [] for name in players}  # notifications waiting for each detective
        self.history = []  # (player, key, challenge rolls) for save and replay
        self._challenge = challenge or (lambda kind, difficulty: self.dice.random())
        self._speak = speak or template_speak
        self._replay = None
        self.story = CaseStory(self) if self.n >= 3 else None

    # ------------------------------------------------------------------ setup

    def reconstruct(self):
        """The night of the murder. Innocents were home or out, mostly at their usual place;
        the murderer claims a place too, home or public, where nobody saw them."""
        rng, night = self.rng, {}
        for i in range(1, self.n):
            r = rng.random()
            night[i] = "home" if r < HOME_RATE else self.hangout[i] if r < .8 else rng.choices(HANGOUTS, HANGOUT_WEIGHTS)[0]
        night[0] = "home" if rng.random() < .5 else self.hangout[0]
        return night

    def company(self, sid):
        """Who really shared the place `sid` claims for that night: innocents only."""
        place = self.night[sid]
        return [t for t in self.order if t != sid and t != 0 and place != "home" and self.night[t] == place]

    def move_house(self, sid, street):
        house = f"house_{sid}"
        self.map[self.map[house][1][0]][1].remove(house)
        self.map[house] = (self.map[house][0], [street])
        self.map[street][1].append(house)

    def blood_candidates(self):
        """Suspects still standing once every fact but the blood type is known."""
        facts = self.case.facts
        if not any(isinstance(f, BloodType) for f in facts):
            return 0
        return len(self.case.remaining([f for f in facts if not isinstance(f, BloodType)]))

    def place_evidence(self):
        """One piece of evidence per consistent clue. The phone and the weapon land where
        their routine says, maybe nowhere: reroll until every fact can still be found.
        Testimonies are given to innocent suspects."""
        facts = self.case.facts
        pairs = [(f, c) for f in facts for c in CLUES if isinstance(f, c.trait) and c.is_consistent(facts)]
        while True:
            self.weapon = get_random_enum(MurderWeaponRoutine, rng=self.rng)
            self.phone = get_random_enum(VictimPhoneRoutine, rng=self.rng)
            spots = {
                Location.CRIME_SCENE: "crime_scene", Location.VICTIM: "hospital",
                Location.VICTIM_HOUSE: "victim_house", Location.MURDERER_HOUSE: "house_0",
                Location.WITNESS: "anyone", Location.NEIGHBOR: "anyone", Location.CCTV: "cctv",
                Location.MURDER_WEAPON: OBJECT_PLACE[self.weapon.name],
                Location.VICTIM_PHONE: OBJECT_PLACE[self.phone.name],
            }
            placed, groups = [], {}
            # One physical object or witness must not hide an identifying
            # combination. Prioritise facts with few physical sources (eyes,
            # hand), then admit further details only while the whole artifact
            # remains compatible with at least two residents.
            rarity = {f: sum(c.location not in (Location.WITNESS, Location.NEIGHBOR)
                             and bool(spots[c.location]) for fact, c in pairs if fact == f) for f in facts}
            for f, c in sorted(pairs, key=lambda pair: rarity[pair[0]]):
                if not spots[c.location]:
                    continue
                group = (spots[c.location], evidence_label(c), c.location in (Location.MURDER_WEAPON, Location.VICTIM_PHONE))
                shared = groups.get(group, set(range(self.n))) & self.case.commonalities[f]
                if len(shared) >= 2:
                    placed.append((f, c))
                    groups[group] = shared
            # every fact must be provable by something physical: a witness may never be cleared
            if {f for f, c in placed if spots[c.location] != "anyone"} == set(facts):
                break
        evidence = []
        for f, c in placed:
            # Finding paperwork at one home must not reveal the unique house
            # specially chosen for the culprit. The same shared relationship
            # observation has sources at each compatible resident's home.
            places = [f"house_{sid}" for sid in self.order if sid in self.case.commonalities[f]] if c.location is Location.MURDERER_HOUSE else [spots[c.location]]
            for place in places:
                evidence.append(Evidence(len(evidence), c, f, place))
        for e in evidence:
            if e.person:
                e.who = self.neighbor if e.clue.location is Location.NEIGHBOR else self.rng.randrange(1, self.n)
                e.place = None
        return evidence

    def victim_life(self):
        rng = self.rng
        birthday = f"{rng.randint(1, 28):02d}{rng.randint(1, 12):02d}"
        pet, memo = rng.choice(PETS), f"{rng.randint(0, 9999):04d}"
        return [
            ("birthday", f"Une carte d'anniversaire : la victime est née un {birthday[:2]}/{birthday[2:]}.", birthday),
            ("pet", f"Un collier gravé, des photos partout : l'animal de la victime s'appelait {pet}.", pet),
            ("memo", f"Un post-it griffonné sur le frigo : {memo}.", memo),
        ]

    def pick_lie(self):
        """A false description, pointing away from the murderer on one revealed trait
        that can be seen or heard (not blood, not the link)."""
        traits = [type(f) for f in self.case.facts if type(f) not in (BloodType, LinkToVictim)] or [Gender]
        trait = self.rng.choice(traits)
        return self.rng.choice([v for v in trait if v != self.case[0][trait]])

    def pick_gossip(self, sid):
        """Whom they point at when asked who had a grudge. Rumours lean towards the murderer,
        GOSSIP_WEIGHT times more than any innocent, without ever being sure."""
        # strangers to the victim know nothing of her life, and many of the others won't point fingers
        if self.case[sid][LinkToVictim] is LinkToVictim.UNKNOWN or self.rng.random() > GOSSIP_RATE:
            return None
        targets = [t for t in range(self.n) if t != sid and self.case[t][LinkToVictim] in GRUDGE]
        weights = [GOSSIP_WEIGHT if t == 0 else 1 for t in targets]
        return self.rng.choices(targets, weights)[0] if targets else None

    def starts(self, items):
        """Where a player with these items may begin."""
        return FREE_STARTS + [place for place, item in PAID_STARTS.items() if item in items]

    def equip(self, i, items, start="victim_street"):
        p = self.players[i]
        p.items = set(items)
        for place, item in PAID_STARTS.items():
            if item in items and place in p.favors:
                p.favor_max[place] = p.favors[place] = 2 * FAVORS
        if start not in self.starts(items):
            raise ValueError(f"{start} needs {PAID_STARTS.get(start)}")
        p.place = self.starts_chosen[i] = start
        if start == "victim_house":
            p.opened.add(start)
        if "filon" in items:
            self.reveal(p, self.rng.randrange(self.n), FAR_TRAITS + [EyeColor], name=True)

    def start(self):
        self.player.ap = AP
        if not self.player.journal:
            self.record_note(self.player, "affaire", "Début de l'enquête",
                             "Identifier le responsable, mais aussi comprendre le mobile et le déroulement. "
                             "Les documents chez la victime et le constat sur la scène peuvent ouvrir des pistes. "
                             "Un conflit ou un objet manquant ne désigne pas à lui seul un meurtrier.",
                             "Dossier initial", leads=["victim_house", "crime_scene"])
        return self.arrive(self.player)

    @classmethod
    def replay(cls, seed, players, items, history, challenge=None, starts=None, legacy_auto_end=0, **kw):
        """Rebuild a game from its seed and action history, reusing the recorded rolls.
        Characters are voiced by the template: no model call during a replay."""
        g = cls(seed, players, challenge=challenge, **kw)
        g.legacy_auto_end = legacy_auto_end
        for i, it in enumerate(items):
            g.equip(i, it, (starts or ["victim_street"] * len(items))[i])
        g.start()
        for index, (_, key, rolls) in enumerate(history):
            g.auto_end = index < legacy_auto_end
            g._replay = iter(rolls)
            g.play(tuple(key))
        g._replay = None
        g.auto_end = False
        return g

    # ---------------------------------------------------------------- helpers

    @property
    def player(self):
        return self.players[self.current]

    def label(self, place):
        return self.map[place][0]

    def name(self, sid):
        return self.names[sid]

    def place_label(self, p, place):
        """The place as this player knows it: a house gets its owner's name once met."""
        owner = self.owner(place)
        return f"{self.label(place)} ({self.name(owner)})" if owner is not None and p.knows(owner) else self.label(place)

    def owner(self, place):
        return int(place[6:]) if place.startswith("house_") else None

    def here(self, p):
        """Evidence still to be found here by this player."""
        return [e for e in self.evidence if e.place == p.place and self.taken.get(e.id, p.name) == p.name]

    def pocket(self, p):
        """The victim's phone, if this player carries it and hasn't read it yet."""
        return [e for e in self.evidence if e.phone and self.taken.get(e.id) == p.name and e.fact not in p.facts]

    def testimony(self, sid):
        return [e for e in self.evidence if e.who == sid]

    def suspects_at(self, place):
        return [i for i in self.order if self.where[i] == place]

    def alibi_place(self, sid):
        """Where a claim can be checked, None for a night at home."""
        return None if self.night[sid] == "home" else self.night[sid]

    def deduce(self, p):
        """What the player can hold for certain, by fixpoint: proven facts rule suspects out,
        innocents' words become reliable (their testimony, the people they vouch for), repeat.
        Returns (certain facts, innocents)."""
        facts, innocents = set(p.facts), set(p.cleared)
        while True:
            for s in list(innocents):
                facts |= p.heard.get(s, set())
                innocents.update(p.claims.get(s, (None, []))[1])
            ruled = {i for i in range(self.n) if any(p.knows(i, type(f)) and self.case[i][type(f)] != f for f in facts)}
            if ruled <= innocents:
                return facts, innocents
            innocents |= ruled

    def place_at(self, i, tick):
        """Where suspect `i` is at a given turn, by their routine."""
        home, out, offset = self.routine[i]
        return f"house_{i}" if (tick + offset) % (home + out) < home else self.hangout[i]

    def move_suspects(self):
        self.where = {i: self.place_at(i, self.tick) for i in range(self.n)}

    def roll(self, kind, difficulty):
        """The client's score at a challenge, recorded for replays."""
        score = next(self._replay) if self._replay else self._challenge(kind, difficulty)
        self._rolls.append(score)
        return score

    def passes(self, kind, difficulty):
        return self.roll(kind, difficulty) >= difficulty

    def notify(self, p, text):
        """A private notification, delivered at the start of the player's next turn."""
        self.inbox[p.name].append(f"🔔 {text}")

    def broadcast(self, p, text):
        """A public event: on the record, and in every other detective's inbox."""
        self.log.append((self.tick, p.name, text))
        for q in self.players:
            if q is not p:
                self.inbox[q.name].append(f"📰 {text}")

    def reveal(self, p, sid, traits, name=False):
        p.known.setdefault(sid, set()).update(traits)
        if name:
            p.names.add(sid)

    def who(self, p, sid):
        """How the player can refer to someone: by name, or by what they look like."""
        return self.name(sid) if p.knows(sid) else "cette femme" if self.case[sid][Gender] is Gender.FEMALE else "cet homme"

    def persona(self, sid):
        """The character sheet handed to the model. The intent carries what is said;
        the sheet carries who says it, and never whether they are guilty."""
        s = self.case[sid]
        # the model is never told who did it: the lie lives in the intent, the tone stays innocent
        role = "témoin de quelque chose ce soir-là" if self.testimony(sid) else "simple habitant"
        if sid == self.neighbor:
            role = "voisin de la victime, " + role
        return {
            "nom": self.name(sid), "genre": TRAIT_TEXT[s[Gender]],
            "apparence": ", ".join(fact_label(s[t]) for t in FAR_TRAITS + [EyeColor]),
            "lien avec la victime": LINK_QUOTES[s[LinkToVictim]],
            "soirée du meurtre, selon lui": NIGHT_TEXT[self.night[sid]],
            "lieu favori": self.label(self.hangout[sid]),
            "caractère": self.mood[sid], "rôle": role,
        }

    def lit(self, street):
        """Houses of a street with someone inside."""
        return [h for h in self.map[street][1] if self.owner(h) is not None and self.suspects_at(h)]

    def glance(self, p):
        """Where the city's life is tonight, for every public place: {place: (people there,
        lit windows on that street)}. The city is small and word travels: everyone sees it."""
        return {q: (len(self.suspects_at(q)), len(self.lit(q))) for q in self.map if self.owner(q) is None}

    def presence_view(self, p):
        """Public city-life radar: counts everywhere, only learned identities.

        Like glance's public/lit-house counts; never leaks unseen faces, traits,
        relationships, guilt or another detective's knowledge. Service staff are
        not counted as suspects. Positions change only during the NPC phase.
        """
        places, districts = {}, {}
        for place in self.map:
            people = [{"id": sid, "name": self.name(sid) if p.knows(sid) else None,
                       "look": glimpse(self.case[sid]) if all(p.knows(sid, trait) for trait in FAR_TRAITS) else "",
                       "known": p.knows(sid)} for sid in self.suspects_at(place)]
            places[place] = {"count": len(people), "people": people}
            region = self.map[place][1][0] if self.owner(place) is not None else place
            district = districts.setdefault(region, {"count": 0, "people": []})
            district["people"].extend(people)
            district["count"] += len(people)
        for district in districts.values():
            district["people"].sort(key=lambda person: self.order.index(person["id"]))
        return {"places": places, "districts": districts}

    def arrival_scene(self, p):
        """Translate a provider scene to public, client-neutral speaker beats.

        Reading a view never consumes the scene. A free listen action records
        consumption, so re-entry, restart and save replay cannot repeat it.
        """
        if not self.story or not hasattr(self.story, "scenes_at") or self.pending or self.winner or p is not self.player:
            return None
        people = self.suspects_at(p.place)
        for scene in self.story.scenes_at(p.place, people):
            if scene["id"] in p.scenes_seen:
                continue
            if len(set(scene["actors"])) < 2 or not set(scene["actors"]) <= set(people):
                continue
            if any(beat["actor"] not in scene["actors"] for beat in scene["beats"]):
                continue
            beats = [{"person": {"id": beat["actor"], "name": self.name(beat["actor"]) if p.knows(beat["actor"]) else None,
                                 "look": glimpse(self.case[beat["actor"]])}, "text": beat["text"]}
                     for beat in scene["beats"]]
            if not beats:
                continue
            return {"id": scene["id"], "title": "Une conversation à " + self.label(p.place),
                    "beats": beats, "people": list(scene["actors"]), "key": ["listen", scene["id"]]}
        return None

    def progress(self, p):
        """How far a detective is, in numbers the scoreboard can show to everyone without
        giving the content away: proven facts, trusted words, suspects ruled out, candidates left."""
        certain, innocents = self.deduce(p)
        return {
            "preuves": len(p.facts), "témoignages fiables": len(certain - p.facts),
            "écartés": len(innocents), "identifiés": len(p.names), "restants": self.n - len(innocents),
            "documents": sum(note["kind"] == "document" for note in p.journal),
            "recoupements": sum(note["kind"] == "vérification" for note in p.journal),
        }

    def walking_paths(self, p):
        """Shortest routes on the real movement graph, not the decorative tile grid."""
        paths, queue = {p.place: [p.place]}, deque([p.place])
        while queue:
            place = queue.popleft()
            for neighbor in self.map[place][1]:
                if neighbor not in paths:
                    paths[neighbor] = paths[place] + [neighbor]
                    queue.append(neighbor)
        return paths

    def navigation_routes(self, p, options):
        """Read-only walking costs, including unavailable places for the map UI."""
        routes = {}
        for place, path in self.walking_paths(p).items():
            cost = len(path) - 1
            occupied = self.owner(place) is not None and bool(self.suspects_at(place))
            key = ("move" if cost == 1 else "walk", place)
            if cost == 0:
                reason = "current"
            elif p is not self.player:
                reason = "not_your_turn"
            elif self.pending or self.winner:
                reason = "busy"
            elif occupied:
                reason = "occupied"
            elif cost > p.ap:
                reason = "too_far"
            else:
                reason = "" if key in options else "unavailable"
            routes[place] = {"cost": cost, "available": not reason,
                             "reason": reason, "key": key if not reason else None}
        return routes

    def view(self, p):
        """Everything a client needs to draw this detective's screen, as plain data: no
        Enum, no engine object. The CLI, a pygame window or a phone all read this."""
        facts, _ = self.deduce(p)
        options = self.options() if p is self.player else {}
        return {
            "player": p.name, "tick": self.tick, "ap": p.ap, "place": p.place, "items": sorted(p.items),
            "active_player": self.player.name,
            "winner": self.winner and self.winner.name,
            "grid": self.grid,
            "crime_site": {"place": "crime_scene", "district": {"canal": "Quartier du Canal", "traverses": "Quartier des Traverses", "jeux": "Quartier des Jeux"}[self.crime_site], "outdoors": True},
            "region": self.map[p.place][1][0] if self.owner(p.place) is not None else p.place,
            # Public movement topology for ground-zone borders, including bridges.
            "adjacency": {q: list(neighbors) for q, (_, neighbors) in self.map.items()},
            "places": {q: {"label": self.place_label(p, q), "street": self.map[q][1][0] if self.owner(q) is not None else None,
                           "searched": q in p.exhausted, "lit": self.owner(q) is not None and bool(self.suspects_at(q))}
                       for q in self.map},
            "glance": {q: list(v) for q, v in self.glance(p).items()},
            "presence": self.presence_view(p),
            "arrival_scene": self.arrival_scene(p),
            "options": list(options.items()),
            "routes": self.navigation_routes(p, options),
            "pending": self.pending and self.name(self.pending["who"]),
            "conversation": self.conversation_view(p),
            "journal": [{**note, "people": list(note["people"]), "leads": list(note["leads"])} for note in p.journal],
            "story": self.story.view(p) if self.story else {},
            "leads": self.story.leads_view(p) if self.story else [],
            "present": [{"id": s, "name": self.name(s) if p.knows(s) else None, "look": glimpse(self.case[s])}
                        for s in self.suspects_at(p.place)],
            "staff": self.staff_view(p, options),
            "fixtures": self.fixture_view(p, options),
            "doors": self.doors_view(p, options),
            "detectives": [{"name": q.name, "place": q.place, "you": q is p} for q in self.players],
            "can_try_code": bool(self.pocket(p) and not p.unlocked and not self.pending),
            "facts": [fact_label(f) for f in p.facts], "trusted": [fact_label(f) for f in facts - p.facts],
            "notebook": [{
                "id": r["id"], "name": r["name"], "out": r["out"],
                "home": self.home_view(p, r["id"]),
                "life": self.story.profile_view(p, r["id"]) if self.story else None,
                "relationship": self.story.link_view(p, r["id"]) if self.story else None,
                "traits": {TRAIT_LABELS[t]: TRAIT_TEXT[v] for t, v in r["traits"].items()},
                "alibi": {True: "confirmé", False: "à vérifier", None: "invérifiable"}[r["alibi"]] if r["claim"] else None,
                "claim": r["claim"], "with": r["with"], "said": [fact_label(f) for f in r["said"]],
            } for r in self.notebook(p)],
            "progress": self.progress(p),
            "scoreboard": [{"name": q.name, **self.progress(q)} for q in self.players],
        }

    def home_view(self, p, sid):
        """An identified person's address, never their current whereabouts."""
        if not p.knows(sid):
            return None
        place = f"house_{sid}"
        region = self.map[place][1][0]
        return {"place": place, "region": region, "label": self.label(place),
                "region_label": self.label(region)}

    def staff_view(self, p, options):
        """Public service characters, never members of the suspect population."""
        if p.place not in SERVICE_STAFF:
            return []
        name, look, portrait_id, kinds = SERVICE_STAFF[p.place]
        return [{"id": f"staff:{p.place}", "name": name, "look": look,
                 "portrait_id": portrait_id, "service": True,
                 "actions": [(key, label) for key, label in options.items() if key[0] in kinds]}]

    def fixture_view(self, p, options):
        """Every place action belongs to a visible person or object."""
        fixtures = []
        descriptions = {
            "crime_scene": ("Traces sur le sol", "blood"), "alley": ("Poubelles", "trash"),
            "hospital": ("Table d'examen · morgue", "morgue"), "cctv": ("Terminal vidéo", "terminal"),
            "victim_house": ("Bureau de la victime", "desk"), "bar": ("Coffre & papiers", "safe"),
            "den": ("Coffre & papiers", "safe"), "cabaret": ("Papiers du Palace", "desk"),
        }
        searches = [(key, label) for key, label in options.items() if key[0] in {"search", "investigate"}]
        if searches:
            title, prop = descriptions.get(p.place, ("Affaires personnelles", "desk"))
            fixtures.append({"id": "object:search", "name": title, "prop": prop, "object": True, "actions": searches})
        phone = [(key, label) for key, label in options.items() if key[0] in {"unlock", "try_code"}]
        if phone:
            fixtures.append({"id": "object:phone", "name": "Téléphone récupéré", "prop": "phone", "object": True, "actions": phone})
        return fixtures

    def doors_view(self, p, options):
        if self.owner(p.place) is not None:
            return []
        doors = []
        person_kinds = {"ring", "observe", "confront", "talk_about", "interrogate"}
        for place in self.map[p.place][1]:
            sid = self.owner(place)
            if sid is None:
                continue
            occupant = sid in self.suspects_at(place)
            actions = [(key, label) for key, label in options.items()
                       if key == ("move", place) or (occupant and len(key) > 1 and key[0] in person_kinds and key[1] == sid)]
            doors.append({"place": place, "label": self.place_label(p, place), "door": True,
                          "id": sid, "name": self.name(sid) if p.knows(sid) else None,
                          "look": glimpse(self.case[sid]) if sid in p.known else "",
                          "occupied": occupant, "actions": actions,
                          "reason": "Plus de PA pour agir ce tour-ci." if p.ap == 0 else
                                    "La personne a déjà répondu à vos questions et n'a pas autorisé l'entrée." if occupant else
                                    "Aucune action disponible à cette porte pour le moment."})
        return doors

    def staff_cue(self, p, text, question=None, notes=()):
        staff = self.staff_view(p, {})
        if staff:
            self.dialogue_cues[p.name] = {
                "id": len(self.history) + 1, "stage": "reply", "text": text,
                "question": question, "notes": list(notes), "person": staff[0],
            }

    def conversation_view(self, p):
        cue = self.dialogue_cues[p.name]
        if cue is None:
            return None
        active = p is self.player and self.pending is not None and self.pending["who"] == cue["person"]["id"]
        return {**cue, "active": active, "remaining": self.pending["left"] if active else 0}

    def record_note(self, p, kind, title, text, source, people=(), leads=()):
        p.journal.append({"id": len(p.journal) + 1, "turn": self.tick + 1,
                          "kind": kind, "title": title, "text": text, "source": source,
                          "people": list(people), "leads": list(leads)})

    def dialogue_cue(self, p, s, text, stage, question=None, notes=()):
        self.dialogue_cues[p.name] = {
            "id": len(self.history) + 1, "stage": stage, "text": text,
            "question": question, "notes": list(notes),
            "person": {"id": s, "name": self.name(s) if p.knows(s) else None,
                       "look": glimpse(self.case[s]) if s in p.known else ""},
        }

    def resume(self):
        """Events to show when a saved game is picked up again."""
        return self.arrive(self.player, again=True)

    def notebook(self, p):
        """One row per suspect: what the player knows, what they claimed, and whether
        they are ruled out by certain facts."""
        rows, (certain, innocents) = [], self.deduce(p)
        for i in self.order:
            traits = {t: self.case[i][t] for t in TRAITS if p.knows(i, t)}
            place, company = p.claims.get(i, (None, []))
            rows.append({"id": i, "name": self.name(i) if p.knows(i) else "?", "traits": traits, "out": i in innocents,
                         "alibi": p.alibis.get(i), "claim": place and ("à la maison" if place == "home" else NIGHT_TEXT[place]), "with": [self.name(t) for t in company],
                         "said": sorted(p.heard.get(i, ()), key=str)})
        return rows

    # ---------------------------------------------------------------- actions

    def options(self):
        """What the current player can do now: {key: label}."""
        p, o = self.player, {}
        if self.pending:  # an interrogation runs to its end, even on the turn's last point
            asked = {q for q, _ in self.pending["dialogue"]}
            o = {("ask", q): text for q, text in QUESTIONS.items() if q not in asked}
            if self.story:
                sid = self.pending["who"]
                for key, label in self.story.context_options(p, sid).items():
                    if key[0] == "talk_about":
                        o[key] = label.removesuffix(" (1 PA)")
            o[("stop",)] = "Laisser partir"
            return o
        if self.winner:
            return {("end",): "Terminer le tour"}
        scene = self.arrival_scene(p)
        if scene:
            o[tuple(scene["key"])] = "Écouter la conversation · sans PA"
        if p.ap <= 0:
            return {**o, ("end",): "Terminer le tour"}
        streets = self.map[p.place][1]
        occupied = {h for h in self.map if self.owner(h) is not None and self.suspects_at(h)
                    and self.owner(h) not in p.invited}  # entering an occupied home needs explicit consent
        done = lambda n: " · déjà fouillée" if n in p.exhausted else ""  # noqa: E731
        for n in streets:
            if n not in occupied:
                o[("move", n)] = f"Aller : {self.place_label(p, n)}{done(n)}"
        for n, path in self.walking_paths(p).items():
            cost = len(path) - 1
            if 1 < cost <= p.ap and n not in occupied:
                o[("walk", n)] = f"Aller : {self.place_label(p, n)} ({cost} PA){done(n)}"
        if "taxi" in p.items:
            for n in self.map:
                if n != p.place and n not in streets and n not in occupied:
                    o[("move", n)] = f"Taxi : {self.place_label(p, n)}{done(n)}"
        for h in streets:
            owner = self.owner(h)
            if h in occupied and owner not in p.talked:
                o[("ring", owner)] = f"Sonner : {self.place_label(p, h)}" + (
                    " · vous a surpris chez lui" if owner in p.shunned else "")
            elif h in occupied and not p.knows(owner, Hand):
                o[("observe", owner)] = f"Sonner chez {self.name(owner)} pour l'observer de plus près"
        # any house can be searched (so the option betrays nothing), public places only when they hold something
        documents = bool(self.story and self.story.available_sources(p))
        searchable = ((self.owner(p.place) is not None or self.here(p) or (p.place == "victim_house" and len(p.secrets) < 3))
                      and p.place not in p.exhausted) or documents
        if p.place in SECURED and not p.authorized and "hacking_kit" not in p.items:
            searchable = False
        if p.place in TAPED and not p.authorized and p.place in p.sneaked:
            searchable = False  # one discreet look was all you could afford
        if searchable:
            label = "Fouiller l'appartement" if self.owner(p.place) is not None else SEARCH.get(p.place, SEARCH_DEFAULT)[0]
            o[("search",)] = label + (" (en discret)" if p.place in TAPED and not p.authorized else " · indices et documents") + " (1 PA)"
        if self.pocket(p) and not p.unlocked:
            if "hacking_kit" in p.items:
                o[("unlock",)] = "Déverrouiller le téléphone de la victime (kit de hacking)"
            for kind, value in p.secrets.items():
                if value not in p.tried:
                    o[("try_code", value)] = f"Essayer le code {value} ({SECRET_LABELS[kind]}) sur le téléphone"
        if p.place == "hospital" and "birthday" not in p.secrets:
            o[("victim_file",)] = "Consulter le dossier de la victime"
        if p.place == "hospital" and self.lab_results(p):
            o[("lab",)] = "Consulter les résultats du labo"
        for s in self.suspects_at(p.place):
            if s not in p.talked:
                o[("interrogate", s)] = f"Interroger {self.who(p, s)} ({glimpse(self.case[s])})" + (
                    " · vous a surpris chez lui" if s in p.shunned else "")
            elif not p.knows(s, Hand):
                o[("observe", s)] = f"Observer {self.name(s)} de plus près"
        for s, confirmed in p.alibis.items():
            if confirmed is False and self.alibi_place(s) == p.place:
                o[("verify", s)] = f"Demander à {BYSTANDER[p.place].lower()} si {self.name(s)} était là ce soir-là"
        if self.story:
            accessible = set(self.suspects_at(p.place))
            accessible.update(self.owner(h) for h in streets if h.startswith("house_") and self.suspects_at(h))
            for sid in self.order:
                if sid in accessible:
                    o.update(self.story.context_options(p, sid))
            o.update(self.story.check_options(p))
        if p.place == "hospital" and p.favors["hospital"]:
            for s in self.order:
                if p.knows(s) and not p.knows(s, BloodType):
                    o[("file", s)] = f"Demander le dossier médical de {self.name(s)} ({p.favors['hospital']} faveurs restantes)"
        if p.place == "police":
            if not p.authorized:
                o[("authorize",)] = "Demander une autorisation (scène de crime, CCTV, casiers)"
            elif p.favors["police"]:
                for s in self.order:
                    if p.knows(s) and not all(p.knows(s, t) for t in FAR_TRAITS + [LinkToVictim]):
                        o[("record", s)] = f"Consulter le casier de {self.name(s)} ({p.favors['police']} faveurs restantes)"
            for s in self.order:
                if p.knows(s):
                    o[("accuse", s)] = f"Accuser {self.name(s)}"
        o[("end",)] = "Terminer le tour"
        return o

    def play(self, key):
        """Apply an option for the current player; returns the events to show them."""
        free_code = key[0] == "try_code" and self.pocket(self.player) and not self.player.unlocked and not self.pending
        legacy_documents = key == ("investigate",) and self._replay is not None and self.story is not None
        if key not in self.options() and not free_code and not legacy_documents:
            raise ValueError(f"not an option now: {key}")
        p, self._rolls = self.player, []
        self.dialogue_cues[p.name] = None
        events = getattr(self, "do_" + key[0])(p, *key[1:])
        if key[0] not in ("move", "walk", "end", "investigate", "confront", "talk_about", "check_timeline", "stop", "listen"):
            cue = self.dialogue_cues[p.name]
            if key[0] == "ask":
                kind = "soupçon" if key[1] == "grudge" else "déclaration"
                self.record_note(p, kind, QUESTIONS[key[1]], "\n".join(events),
                                 self.name(cue["person"]["id"]), people=[cue["person"]["id"]])
            else:
                note_events = events
                if key[0] == "search" and self.story:
                    # A document already has its exact, structured journal note.
                    # Keep the extra physical findings, not a duplicate paragraph.
                    note_events = [e for e in events if not any(e.startswith(doc["title"] + "\n\n")
                                                               for doc in self.story.sources.values())]
                if note_events:
                    self.record_note(p, "preuve" if any(e.startswith("Indice :") for e in note_events) else "observation",
                                 {"search": "Fouille", "interrogate": "Rencontre", "ring": "Rencontre",
                                  "file": "Dossier médical", "record": "Casier", "observe": "Observation",
                                  "accuse": "Conclusion"}.get(key[0], "Avancée de l'enquête"),
                                     "\n".join(note_events), self.place_label(p, p.place))
        cue = self.dialogue_cues[p.name]
        if cue and cue.get("thought"):
            thought = cue["thought"]["text"]
            self.record_note(p, "réflexion", "Mon impression", thought, p.name)
            events.append(f"{p.name} (pensée) — {thought}")
        self.history.append((p.name, key, self._rolls))
        if self.auto_end and p.ap <= 0 and key[0] != "end" and not self.winner and not self.pending:
            events += self.do_end(p)
        return events

    def do_walk(self, p, place):
        path = self.walking_paths(p)[place]
        cost = len(path) - 1
        # Crossing places does not grant free searches or conversations. A failed
        # final lock leaves the detective at the doorstep, after paying the route.
        p.ap -= cost - 1
        p.place = path[-2]
        return [f"Trajet à pied : {self.label(place)} ({cost} PA)."] + self.do_move(p, place)

    def do_listen(self, p, scene_id):
        scene = self.arrival_scene(p)
        if not scene or scene["id"] != scene_id:
            raise ValueError("Conversation unavailable")
        p.scenes_seen.add(scene_id)
        lines = [f"{beat['person']['name'] or beat['person']['look'].capitalize()} — {beat['text']}" for beat in scene["beats"]]
        self.record_note(p, "conversation", scene["title"], "\n".join(lines), self.label(p.place), people=scene["people"])
        self.dialogue_cues[p.name] = {"id": len(self.history) + 1, "stage": "scene", "text": scene["beats"][0]["text"],
                                     "person": scene["beats"][0]["person"], "question": None, "notes": [],
                                     "title": scene["title"], "beats": scene["beats"]}
        return ["Vous surprenez une conversation."] + lines

    def do_investigate(self, p):
        p.ap -= 1
        return self.story.investigate(p)

    def do_confront(self, p, sid, evidence):
        p.ap -= 1
        return self.story.confront(p, sid, evidence)

    def do_check_timeline(self, p, sid):
        p.ap -= 1
        return self.story.check_timeline(p, sid)

    def do_talk_about(self, p, sid, target):
        in_conversation = self.pending is not None and self.pending["who"] == sid
        if in_conversation:
            self.pending["left"] -= 1
        else:
            p.ap -= 1
        events = self.story.talk_about(p, sid, target)
        if in_conversation:
            self.pending["dialogue"].append((f"about_{target}", events[0]))
            if self.pending["left"] == 0:
                self.pending = None
                events.append(f"{self.name(sid)} s'éloigne.")
        return events

    def do_move(self, p, place):
        p.ap -= 1
        owner = self.owner(place)
        locked = (place in LOCKED or owner is not None) and place not in p.opened and owner not in p.invited
        if locked and owner not in self.suspects_at(place):
            if "crowbar" in p.items:
                ev = ["Le pied de biche fait sauter la serrure."]
            elif self.passes("crochetage", .5):
                ev = ["La serrure cède."]
            else:
                return ["La porte résiste, vous perdez du temps."]
            p.opened.add(place)
        else:
            ev = []
        p.place = place
        if place == "police":
            self.broadcast(p, f"{p.name} entre au commissariat.")
        return ev + self.arrive(p)

    def arrive(self, p, again=False):
        ev = [f"Vous êtes {'toujours ' if again else ''}: {self.label(p.place)}."]
        if p.place not in p.visited and p.place in PLACE_HINTS:
            ev.append("Votre autorisation permet de relever librement les indices et les documents." if p.place == "crime_scene" and p.authorized else PLACE_HINTS[p.place])
        p.visited.add(p.place)
        owner = self.owner(p.place)
        if owner is not None and not p.knows(owner):
            self.reveal(p, owner, FAR_TRAITS, name=True)  # the mail on the table, the photos on the wall
            ev.append(f"Dans les papiers et les photos qui traînent, on devine qu'ici habite {self.name(owner)}. "
                      f"{glimpse(self.case[owner]).capitalize()}. Personne pour l'instant.")
        elif owner is not None:
            ev.append(f"Chez {self.name(owner)}." + (" Vous avez son accord pour entrer." if owner in p.invited else " Personne pour l'instant."))
        for s in self.suspects_at(p.place):
            look = glimpse(self.case[s])
            if not p.knows(s):
                ev.append(f"Vous remarquez quelqu'un ({look}).")
            elif s not in p.known:  # a name you were given, now a face
                ev.append(f"Vous reconnaissez {self.name(s)}, dont on vous a parlé ({look}).")
            else:
                ev.append(f"Il y a {self.name(s)} ({look}).")
            self.reveal(p, s, FAR_TRAITS)
        if self.owner(p.place) is None and self.lit(p.place):
            ev.append("Fenêtres éclairées : " + ", ".join(self.place_label(p, h) for h in self.lit(p.place)) + ".")
        if p.place in SECURED and not p.authorized and "hacking_kit" not in p.items:
            ev.append("Le vigile garde les enregistrements : il faut une autorisation ou un kit de hacking.")
        if p.place in TAPED and not p.authorized:
            ev.append("Le ruban de police est en place : fouiller sans autorisation demande de la discrétion.")
        return ev

    def do_search(self, p):
        p.ap -= 1
        sneaking = p.place in TAPED and not p.authorized
        if sneaking and not self.passes("discrétion", .4):
            return ["Un agent vous repère et vous éloigne du ruban."]
        documents = self.story.investigate(p) if self.story and not sneaking and self.story.available_sources(p) else []
        pool = [e for e in self.here(p) if e.id not in p.found]
        secrets = [x for x in self.secrets if x[0] not in p.secrets] if p.place == "victim_house" else []
        if not pool and not secrets:
            p.exhausted.add(p.place)
            return documents or ["La fouille est terminée : aucun nouvel indice dans ce lieu."]
        if secrets and self.rng.randrange(len(pool) + len(secrets)) < len(secrets):
            kind, text, value = self.rng.choice(secrets)
            p.secrets[kind] = value
            left = len(pool) + len(secrets) > 1
            return documents + [f"Vous trouvez : {text}", "Cette information peut servir à déverrouiller le téléphone de la victime."] + (
                ["D'autres choses traînent encore ici."] if left else ["Vous avez fait le tour des lieux."])
        if sneaking:  # a quick look under the tape: traces only, nothing you could walk away with
            p.sneaked.add(p.place)
            reachable = [e for e in pool if not e.portable]
            if not reachable:
                return ["Des objets sont derrière le ruban de police. Il me faut une autorisation du commissariat pour les récupérer."]
        e = self.rng.choice(reachable if sneaking else pool)
        group = [x for x in pool if x.label == e.label and x.portable == e.portable]  # one object, every clue it carries
        for x in group:
            p.found.add(x.id)
            if x.portable:
                self.taken[x.id] = p.name
        if len(pool) == len(group) and not secrets:
            p.exhausted.add(p.place)
        ev = [f"{SEARCH.get(p.place, SEARCH_DEFAULT)[1]} : {e.label}."]
        if e.portable:
            ev.append("Vous l'emportez.")
            self.broadcast(p, f"{p.name} a récupéré {e.label.lower()}.")
        if e.phone:
            ev += self.unlock(p)
        else:
            for x in group:
                ev += [x.text] + self.examine(p, x)
        if len(pool) > len(group):
            remaining = ("D'autres objets sont derrière le ruban. Il me faut une autorisation du commissariat pour les récupérer."
                         if sneaking else "La fouille n'est pas terminée : vous pouvez encore examiner ce lieu (1 PA).")
        else:
            remaining = "Vous avez fait le tour des lieux."
        return documents + ev + [remaining]

    def examine(self, p, e):
        if e.blood:
            if e.fact in p.facts:
                return [f"Le groupe sanguin {TRAIT_TEXT[e.fact]} est déjà connu. Ce prélèvement ne m'apprendra rien de plus."]
            if "forensic_kit" in p.items:
                return ["Vous sortez le kit médico-légal et analysez le sang sur place."] + self.learn(p, e)
            if p.place == "hospital":
                return ["Le prélèvement est analysé sur place au laboratoire de l'hôpital."] + self.learn(p, e)
            if any(sample.id == e.id for sample, _, _ in self.lab):
                return ["Ce prélèvement est déjà au laboratoire ; son résultat n'est pas encore disponible."]
            self.lab.append((e, p.name, self.tick + 1))
            return ["L'échantillon est envoyé au laboratoire de l'hôpital. Résultat disponible au prochain tour."]
        return self.learn(p, e)

    def learn(self, p, e):
        p.facts.add(e.fact)
        return [f"Indice : {fact_sentence(e.fact)}."]

    def unlock(self, p, how=None):
        """Read the phone in the pocket, if it is open. Locked, it tells nothing."""
        if self.code is None:
            ev = ["Il n'est même pas verrouillé."]
        elif how:
            ev = [how]
        elif p.unlocked:
            ev = ["Le téléphone s'ouvre."]
        elif "hacking_kit" in p.items:
            ev = ["Le kit de hacking fait sauter le verrouillage."]
        else:
            return ["Il est verrouillé. Il faudra trouver de quoi deviner le code : la vie de la victime doit en garder la trace."]
        p.unlocked = True
        for e in self.pocket(p):
            ev += [e.text] + self.learn(p, e)
        return ev

    def do_unlock(self, p):
        p.ap -= 1
        return self.unlock(p, "Le kit de hacking fait sauter le verrouillage.")

    def do_try_code(self, p, code):
        p.ap -= 1
        answer = {"birthday": self.secrets[0][2], "pet": self.secrets[1][2], "memo": self.secrets[2][2]}.get(self.code)
        if str(code).strip().lower() == str(answer).lower():
            return self.unlock(p, f"Le code {answer} déverrouille le téléphone.")
        p.tried.add(code)
        return [f"Code {code} refusé."]

    def lab_results(self, p):
        """Analyses ready at the lab that this player hasn't read yet, theirs or not."""
        return [(e, who) for e, who, ready in self.lab if ready <= self.tick and e.id not in p.collected]

    def do_lab(self, p):
        p.ap -= 1
        ev = []
        for e, who in self.lab_results(p):
            p.collected.add(e.id)
            if who == p.name:
                ev.append(f"Votre échantillon de sang ({e.label.lower()}) donne le groupe {TRAIT_TEXT[e.fact]}.")
            else:
                ev.append(f"{who} a déposé un échantillon de sang ({e.label.lower()}). Il donne le groupe {TRAIT_TEXT[e.fact]}.")
            ev += self.learn(p, e)
        return ev

    def do_victim_file(self, p):
        p.ap -= 1
        if not self.passes("persuasion", .3):
            return ["L'infirmière refuse d'ouvrir les dossiers. Réessayez plus tard."]
        _, _, birthday = self.secrets[0]
        p.secrets["birthday"] = birthday
        return [f"Dossier de la victime : née un {birthday[:2]}/{birthday[2:]}.", "Ça peut servir. On ne sait jamais."]

    def do_observe(self, p, s):
        p.ap -= 1
        self.reveal(p, s, [Hand])
        scene = "home" if self.owner(self.where[s]) is not None else self.where[s]
        return [f"Vous observez {self.name(s)} un moment. {hand_scene(self.case[s], scene, self.rng)}"]

    # ----------------------------------------------------------- interrogation

    def do_interrogate(self, p, s):
        """Approach someone: a good look, then up to three questions."""
        p.ap -= 1
        if s in p.shunned:
            self.dialogue_cue(p, s, "Je n'ai rien à vous dire.", "refused")
            return [f"{self.name(s)} — Je n'ai rien à vous dire."]
        p.talked.add(s)
        self.reveal(p, s, FAR_TRAITS + [EyeColor] + ([Hand] if self.hand_visible[s] else []), name=True)
        scene = "home" if self.owner(self.where[s]) is not None else self.where[s]
        ev = [f"{self.name(s)}. {portrait(self.case[s], self.hand_visible[s], scene, self.rng)}"]
        score = self.roll("persuasion", .3)
        questions = sum(score >= t for t in (.25, .5, .75))  # the better the approach, the longer they stay
        if not questions:
            p.talked.discard(s)
            self.dialogue_cue(p, s, "", "refused", notes=[f"{self.name(s)} vous tourne le dos. Réessayez plus tard."])
            return ev + [f"{self.name(s)} vous tourne le dos. Réessayez plus tard."]
        self.pending = {"who": s, "left": questions, "dialogue": []}
        self.dialogue_cue(p, s, "", "greeting", notes=ev)
        return ev + [f"{self.name(s)} accepte de parler. {questions} question{'s' if questions > 1 else ''}, pas plus."]

    do_ring = do_interrogate  # same thing, on the doorstep

    def do_ask(self, p, q):
        s = self.pending["who"]
        intent, ev = getattr(self, "answer_" + q)(p, s)
        line = self._speak(self.persona(s), self.pending["dialogue"], QUESTIONS[q], intent)
        self.pending["dialogue"].append((q, line))
        self.pending["left"] -= 1
        self.dialogue_cue(p, s, line, "reply", question=QUESTIONS[q], notes=ev)
        if q == "grudge" and s in p.story_rumours:
            kind = p.story_rumours[s]["kind"]
            if kind not in p.thought_topics:
                p.thought_topics.add(kind)
                thought = ("Des ennuis au travail… Elle n'en disait peut-être pas autant à tout le monde." if kind == "work" else
                           {"theft": "Des dettes, donc. Pour l'instant, je n'ai que des bruits de quartier.",
                            "blackmail": "Ce dossier faisait peur. Qu'est-ce qu'elle comptait révéler ?",
                            "revenge": "Des excuses attendues… Il reste quelque chose de cette histoire."}[self.story.family])
                self.dialogue_cues[p.name]["thought"] = {"text": thought, "person": {
                    "name": p.name, "id": self.players.index(p), "look": "", "detective": True}}
        ev = [f"{self.name(s)} — {line}"] + ev
        if self.pending["left"] == 0:
            ev.append(f"{self.name(s)} s'éloigne.")
            self.pending = None
        return ev

    def do_stop(self, p):
        self.dialogue_cue(p, self.pending["who"], "", "farewell")
        self.pending = None
        return ["Vous laissez partir votre interlocuteur."]

    def answer_alibi(self, p, s):
        """Where they say they were, and with whom. Innocents name each other; nobody names
        the murderer, who names people who were really there to sound credible."""
        recalled = self.recall[s]
        p.claims[s] = (self.night[s], recalled)
        for t in recalled:
            self.reveal(p, t, [], name=True)  # a name to put in the notebook
        if self.night[s] == "home":
            p.alibis.setdefault(s, None)
            she = self.case[s][Gender] is Gender.FEMALE
            return (f"Chez moi. Seul{'e' if she else ''}.",
                    [f"Noté : chez {'elle' if she else 'lui'} ce soir-là, invérifiable."])
        p.alibis.setdefault(s, False)
        names = ", ".join(self.name(t) for t in recalled)
        where = NIGHT_TEXT[self.night[s]]
        if names:
            text = f"Le soir du meurtre, j'étais {where}, avec {names}. Il y avait peut-être d'autres gens."
        elif self.company(s):
            text = f"Le soir du meurtre, j'étais {where}. Il y avait du monde, mais je ne me souviens de personne en particulier."
        else:
            text = f"Le soir du meurtre, j'étais {where}, seul{'e' if self.case[s][Gender] is Gender.FEMALE else ''}."
        return text, [f"Noté : {where}" + (f", avec {names}…" if names else "") + "."]

    def answer_link(self, p, s):
        if self.story and s in self.story.link_deniers:
            p.link_claims[s] = LinkToVictim.UNKNOWN
            return "Non. Je ne connaissais pas la victime personnellement.", ["Déclaration à vérifier, pas un lien établi."]
        p.link_claims[s] = self.case[s][LinkToVictim]
        self.reveal(p, s, [LinkToVictim])
        return LINK_QUOTES[self.case[s][LinkToVictim]], []

    def answer_seen(self, p, s):
        held = self.testimony(s)
        if s == 0 and self.lie is not None:
            claims, text = [self.lie], f"J'ai vu quelqu'un partir en courant. {statement(self.lie)}"
        elif held:
            claims, text = [e.fact for e in held], " ".join(f"{e.text} {statement(e.fact)}" for e in held)
        else:
            return "Cette nuit-là… Je n'ai rien à vous raconter.", []
        p.heard.setdefault(s, set()).update(claims)
        return text, [f"Témoignage noté : {', '.join(fact_label(f) for f in claims)}."]

    def answer_grudge(self, p, s):
        if self.story:
            return self.story.rumours(p, s)
        t = self.gossip[s]
        if t is None:
            if self.case[s][LinkToVictim] is LinkToVictim.UNKNOWN:
                return "Je ne la connaissais pas. Je ne sais rien de sa vie.", []
            return "Tout le monde l'aimait bien. Enfin, c'est ce qu'on disait. Je ne vais pas accuser quelqu'un comme ça.", []
        self.reveal(p, t, [LinkToVictim], name=True)
        text = f"{self.name(t)} avait des raisons de lui en vouloir : {GRUDGE[self.case[t][LinkToVictim]]}. Mais de là à tuer…"
        return text, [f"Noté : {self.name(t)}, {fact_label(self.case[t][LinkToVictim])}. Un mobile, pas une preuve."]

    def answer_life(self, p, s):
        return self.story.life(p, s) if self.story else ("Je voudrais une vie plus tranquille.", [])

    # ----------------------------------------------------------------- others

    def do_verify(self, p, s):
        """Ask around at the alibi place. Memories are patchy: some innocents are remembered,
        the murderer never is. One check per suspect, same answer for everyone."""
        p.ap -= 1
        who = BYSTANDER[p.place]
        if s != 0 and self.alibi_ok[s]:
            p.alibis[s] = True
            p.cleared.add(s)
            line = f"{self.name(s)} ? Oui, toute la soirée, jusqu'à la fermeture. Je m'en souviens bien."
            note = f"Présence de {self.name(s)} confirmée à l'heure du meurtre."
            self.staff_cue(p, line, question=f"Vous avez vu {self.name(s)} ce soir-là ?", notes=[note])
            return [f"{who} : « {line} »", note]
        p.alibis[s] = None
        line = f"{self.name(s)} ? Il y avait du monde ce soir-là… Non, je ne me souviens pas."
        note = f"Pas de confirmation pour {self.name(s)}."
        self.staff_cue(p, line, question=f"Vous avez vu {self.name(s)} ce soir-là ?", notes=[note])
        return [f"{who} : « {line} »", note]

    def do_file(self, p, s):
        p.ap -= 1
        if not self.passes("persuasion", .3):
            return ["L'infirmière refuse d'ouvrir les dossiers. Réessayez plus tard."]
        p.favors["hospital"] -= 1
        self.reveal(p, s, [BloodType])
        return [f"Dossier médical de {self.name(s)} : groupe {TRAIT_TEXT[self.case[s][BloodType]]}.",
                f"L'infirmière vous doit encore {p.favors['hospital']} faveur{'s' if p.favors['hospital'] > 1 else ''}." if p.favors["hospital"]
                else "L'infirmière ne vous doit plus rien. Laissez-lui quelques jours."]

    def do_record(self, p, s):
        p.ap -= 1
        p.favors["police"] -= 1
        self.reveal(p, s, FAR_TRAITS + [LinkToVictim])
        return [f"Casier de {self.name(s)} : photo d'identité ({glimpse(self.case[s])}). "
                f"Relation avec la victime : {TRAIT_TEXT[self.case[s][LinkToVictim]]}.",
                f"Le commissaire tolérera encore {p.favors['police']} consultation{'s' if p.favors['police'] > 1 else ''}." if p.favors["police"]
                else "Le commissaire ferme ses archives. Repassez dans quelques jours."]

    def do_authorize(self, p):
        p.ap -= 1
        p.authorized = True
        self.broadcast(p, f"{p.name} obtient une autorisation.")
        self.staff_cue(p, "Voilà votre autorisation. Elle couvre la scène, les vidéos et nos archives. Gardez-la sur vous.")
        return ["Le commissaire vous ouvre la scène de crime, les enregistrements et les casiers."]

    def do_accuse(self, p, s):
        p.ap = 0
        if s == 0:
            self.winner = p
            self.broadcast(p, f"{p.name} a démasqué {self.name(s)} !")
            return [f"{self.name(s)} craque. Affaire classée, bravo."] + ([self.story.reconstruction(p)] if self.story else [])
        p.skip = PENALTY
        for q in self.players:
            self.reveal(q, s, FAR_TRAITS, name=True)
            q.cleared.add(s)
        self.broadcast(p, f"{p.name} a accusé {self.name(s)} à tort : {self.name(s)} est innocent.")
        return [f"Accusation erronée : {self.name(s)} n'est pas responsable de ce meurtre. Vous perdez {PENALTY} tours."]

    def do_end(self, p):
        p.ap, self.pending = 0, None
        while True:
            self.current = (self.current + 1) % len(self.players)
            if self.current == 0:
                self.tick += 1
                self.move_suspects()
                self.new_day()
            q = self.player
            if q.skip:
                q.skip -= 1
                continue
            return [f"— Tour {self.tick + 1}, à {q.name}."] + self.start_turn(q)

    def new_day(self):
        """What a new turn brings to each detective: lab results, favours owed again."""
        for q in self.players:
            if any(who == q.name and ready == self.tick for _, who, ready in self.lab):
                self.notify(q, "Le labo a fini vos analyses : passez à l'hôpital.")
            if self.tick % FAVOR_RESET == 0:
                if q.favors["hospital"] < q.favor_max["hospital"]:
                    self.notify(q, "L'infirmière accepte à nouveau de vous rendre service.")
                if q.favors["police"] < q.favor_max["police"]:
                    self.notify(q, "Le commissaire a rouvert ses archives.")
                q.favors = dict(q.favor_max)

    def start_turn(self, q):
        q.ap = AP
        ev, self.inbox[q.name] = self.inbox[q.name], []
        return ev + self.caught_inside(q) + self.arrive(q, again=True)

    def caught_inside(self, q):
        """The owner comes home while you are in their house: slip out, or get thrown out."""
        owner = self.owner(q.place)
        if owner is None or owner in q.invited or owner not in self.suspects_at(q.place):
            return []
        street = self.map[q.place][1][0]
        name = self.name(owner)
        q.place = street
        if self.passes("discrétion", .4):
            return [f"Une clé dans la serrure : {name} rentre. Vous filez par la fenêtre de derrière, sans être vu."]
        q.shunned.add(owner)  # no more questions from this one
        self.broadcast(q, f"{q.name} s'est fait jeter de chez {name}.")
        return [f"{name} rentre et vous surprend chez lui. Dehors, sans ménagement. "
                f"{name} ne vous adressera plus la parole."]
