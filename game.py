"""The engine: a Case dropped into the city, and players acting on it turn by turn.

Pure and deterministic given a seed: no I/O. The client shows the events returned by
`play()`, lists `options()` for the current player, resolves challenges (QTEs) through
`challenge(kind, difficulty) -> bool`, and voices characters through
`speak(persona, dialogue, question, intent) -> str`. Both default to offline stubs.
"""

import random

from city import (FAR_TRAITS, HANGOUTS, LINK_QUOTES, LOCKED, NAMES, PLACE_HINTS, SECURED, START, TAPED, TRAIT_TEXT, build_map,
                  evidence_label, fact_label, glimpse, portrait, statement)
from clue import CLUES
from genotype import TRAITS, BloodType, EyeColor, Gender, Hand, LinkToVictim, get_random_enum
from modality import Location
from routine import MurderWeaponRoutine, VictimPhoneRoutine
from suspect import Case

AP = 3  # action points per turn
PENALTY = 2  # turns lost on a wrong accusation
QUESTIONS_PER_INTERROGATION = 3
MOVE_RATE = .3  # chance a suspect changes place at each turn
ALIBI_ODDS = 2  # a bystander remembers an innocent with 1 chance in ALIBI_ODDS; the murderer never
BYSTANDER = {"bar": "Le barman", "pool": "Le maître-nageur", "theater": "L'ouvreuse", "hospital": "L'infirmière de garde"}
ITEMS = {
    "crowbar": "Pied de biche : ouvre les portes fermées",
    "forensic_kit": "Kit médico-légal : analyse le sang sur place",
    "hacking_kit": "Kit de hacking : téléphone et CCTV sans code ni autorisation",
    "taxi": "Carte taxi : aller n'importe où pour 1 PA",
    "filon": "Filon : un suspect déjà identifié au départ",
}
QUESTIONS = {
    "alibi": "Où étiez-vous le soir du meurtre ?",
    "link": "Vous connaissiez la victime ?",
    "seen": "Vous avez vu ou entendu quelque chose ?",
    "grudge": "Qui aurait pu lui en vouloir ?",
}
NIGHT_TEXT = {"bar": "au bar", "pool": "à la piscine", "theater": "au théâtre", "hospital": "à l'hôpital", "home": "chez moi"}
HOME_RATE = .35  # chance an innocent spent the night at home, where nobody can vouch for them
RECALL = .6  # chance someone remembers a given person who was there with them
GRUDGE = {
    LinkToVictim.SIBLING: "De la famille. Ils ne se parlaient plus, une histoire d'héritage.",
    LinkToVictim.NEIGHBORHOOD: "Quelqu'un du quartier. Des histoires de voisinage qui ont mal tourné.",
    LinkToVictim.COLLEAGUE: "Un collègue. Ça se disputait au travail, tout le monde le savait.",
    LinkToVictim.EX: "Son ex. La rupture n'est jamais vraiment passée.",
}
MOODS = ["bavard et un peu trop content de parler", "méfiant, réponses courtes", "pressé, agacé d'être retenu",
         "blasé, fatigué de cette ville", "amical, veut aider", "nerveux, qui se justifie trop"]
OBJECT_PLACE = {"NEXT_TO_VICTIM": "crime_scene", "TRASH_CAN": "alley", "LOST": None}


class Evidence:
    def __init__(self, id, clue, fact, place):
        self.id, self.clue, self.fact, self.place = id, clue, fact, place
        self.label, self.text = evidence_label(clue), clue.text
        self.person = clue.location in (Location.WITNESS, Location.NEIGHBOR)  # held by a suspect, see `who`
        self.phone = clue.location is Location.VICTIM_PHONE
        self.blood = clue.trait is BloodType
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
        self.alibis = {}  # suspect id -> alibi confirmed? False heard, True confirmed, None checked and backed by nobody
        self.claims = {}  # suspect id -> (place that night, ids they say were with them)
        self.cleared = set()  # suspects proven innocent
        self.opened = set()  # doors forced
        self.authorized = False
        self.code = False  # knows the victim's phone code
        self.lab = []  # (evidence, ready at tick)
        self.visited = set()
        self.exhausted = set()  # places searched through

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
        n = self.n = n_suspects
        pools = {g: iter(rng.sample(names, n)) for g, names in NAMES.items()}
        self.names = [next(pools[self.case[i][Gender]]) for i in range(n)]
        self.order = rng.sample(range(n), n)  # display order: suspect 0 must not come first
        self.map = build_map(rng, n)
        self.hangout = {i: rng.choice(HANGOUTS) for i in range(n)}
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
        self.lie = self.pick_lie()  # the false description the murderer gives
        self.gossip = {i: self.pick_gossip(i) for i in range(n)}  # whom they point at
        self.players = [Player(name) for name in players]
        self.current, self.tick, self.winner = 0, 0, None
        self.pending = None  # ongoing interrogation: {"who", "left", "dialogue"}
        self.where = {}
        self.move_suspects()
        self.log = []  # (tick, author, text): public events, visible to every player
        self.history = []  # (player, key, challenge rolls) for save and replay
        self._challenge = challenge or (lambda kind, difficulty: self.dice.random() > difficulty)
        self._speak = speak or template_speak
        self._replay = None

    # ------------------------------------------------------------------ setup

    def reconstruct(self):
        """The night of the murder. Innocents were home or out, mostly at their usual place;
        the murderer claims a place too, home or public, where nobody saw them."""
        rng, night = self.rng, {}
        for i in range(1, self.n):
            r = rng.random()
            night[i] = "home" if r < HOME_RATE else self.hangout[i] if r < .8 else rng.choice(HANGOUTS)
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
            placed = [(f, c) for f, c in pairs if spots[c.location]]
            # every fact must be provable by something physical: a witness may never be cleared
            if {f for f, c in placed if spots[c.location] != "anyone"} == set(facts):
                break
        evidence = [Evidence(i, c, f, spots[c.location]) for i, (f, c) in enumerate(placed)]
        for e in evidence:
            if e.person:
                e.who = self.neighbor if e.clue.location is Location.NEIGHBOR else self.rng.randrange(1, self.n)
                e.place = None
        return evidence

    def pick_lie(self):
        """A false description, pointing away from the murderer on one revealed trait
        that can be seen or heard (not blood, not the link)."""
        traits = [type(f) for f in self.case.facts if type(f) not in (BloodType, LinkToVictim)] or [Gender]
        trait = self.rng.choice(traits)
        return self.rng.choice([v for v in trait if v != self.case[0][trait]])

    def pick_gossip(self, sid):
        targets = [t for t in range(self.n) if t != sid and self.case[t][LinkToVictim] in GRUDGE]
        return self.rng.choice(targets) if targets else None

    def equip(self, i, items):
        p = self.players[i]
        p.items = set(items)
        if "filon" in items:
            self.reveal(p, self.rng.randrange(self.n), FAR_TRAITS + [EyeColor], name=True)

    def start(self):
        return self.start_turn(self.player)

    @classmethod
    def replay(cls, seed, players, items, history, challenge=None, **kw):
        """Rebuild a game from its seed and action history, reusing the recorded rolls.
        Characters are voiced by the template: no model call during a replay."""
        g = cls(seed, players, challenge=challenge, **kw)
        for i, it in enumerate(items):
            g.equip(i, it)
        g.start()
        for _, key, rolls in history:
            g._replay = iter(rolls)
            g.play(tuple(key))
        g._replay = None
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
        return [e for e in self.evidence if e.place == p.place]

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

    def move_suspects(self):
        """People drift between home and their hangout; most stay put from one turn to the next."""
        for i in range(self.n):
            if i not in self.where or self.rng.random() < MOVE_RATE:
                self.where[i] = self.rng.choice([f"house_{i}", self.hangout[i]])

    def roll(self, kind, difficulty):
        ok = next(self._replay) if self._replay else self._challenge(kind, difficulty)
        self._rolls.append(ok)
        return ok

    def reveal(self, p, sid, traits, name=False):
        p.known.setdefault(sid, set()).update(traits)
        if name:
            p.names.add(sid)

    def who(self, p, sid):
        """How the player can refer to someone: by name, or by what they look like."""
        return self.name(sid) if p.knows(sid) else "cette femme" if self.case[sid][Gender] is Gender.FEMALE else "cet homme"

    def persona(self, sid):
        """The character sheet handed to the model. The intent carries what is said;
        the sheet carries who says it."""
        s = self.case[sid]
        role = "témoin de quelque chose ce soir-là" if self.testimony(sid) else "simple habitant"
        if sid == self.neighbor:
            role = "voisin de la victime, " + role
        if sid == 0:
            role = "le coupable, qui joue l'innocent et ne laisse rien paraître"
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
        """Activity seen from where the player stands, for the current and adjacent places:
        {place: (people in the street, lit houses)}."""
        street = p.place if self.owner(p.place) is None else self.map[p.place][1][0]
        around = {street, *self.map[street][1], *self.map[p.place][1]}
        return {q: (len(self.suspects_at(q)), len(self.lit(q))) for q in around if self.owner(q) is None}

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
            o[("stop",)] = "Laisser partir"
            return o
        if self.winner or p.ap <= 0:
            return {("end",): "Terminer le tour"}
        streets = self.map[p.place][1]
        occupied = {h for h in self.map if self.owner(h) is not None and self.suspects_at(h)}  # someone's home: no entering
        for n in streets:
            if n not in occupied:
                o[("move", n)] = f"Aller : {self.place_label(p, n)}"
        if "taxi" in p.items:
            for n in self.map:
                if n != p.place and n not in streets and n not in occupied:
                    o[("move", n)] = f"Taxi : {self.place_label(p, n)}"
        for h in streets:
            if h in occupied and self.owner(h) not in p.talked:
                o[("ring", self.owner(h))] = f"Sonner : {self.place_label(p, h)}"
        # any house can be searched (so the option betrays nothing), public places only when they hold something
        searchable = self.owner(p.place) is not None or self.here(p) or p.place == "victim_house"
        searchable = searchable and p.place not in p.exhausted
        if searchable and (p.place not in SECURED or p.authorized or "hacking_kit" in p.items):
            o[("search",)] = "Fouiller les lieux"
        for e in self.here(p):
            if e.phone and e.id in p.found and e.fact not in p.facts and (p.code or "hacking_kit" in p.items):
                o[("unlock", e.id)] = "Déverrouiller le téléphone"
        for s in self.suspects_at(p.place):
            if s not in p.talked:
                o[("interrogate", s)] = f"Interroger {self.who(p, s)} ({glimpse(self.case[s])})"
            elif not p.knows(s, Hand):
                o[("observe", s)] = f"Observer {self.name(s)} de plus près"
        for s, confirmed in p.alibis.items():
            if confirmed is False and self.alibi_place(s) == p.place:
                o[("verify", s)] = f"Demander à {BYSTANDER[p.place].lower()} si {self.name(s)} était là ce soir-là"
        if p.place == "hospital":
            for s in self.order:
                if p.knows(s) and not p.knows(s, BloodType):
                    o[("file", s)] = f"Consulter le dossier médical de {self.name(s)}"
        if p.place == "police":
            if not p.authorized:
                o[("authorize",)] = "Demander une autorisation (scène de crime, CCTV, casiers)"
            else:
                for s in self.order:
                    if p.knows(s) and not all(p.knows(s, t) for t in FAR_TRAITS + [LinkToVictim]):
                        o[("record", s)] = f"Consulter le casier de {self.name(s)}"
            for s in self.order:
                if p.knows(s):
                    o[("accuse", s)] = f"Accuser {self.name(s)}"
        o[("end",)] = "Terminer le tour"
        return o

    def play(self, key):
        """Apply an option for the current player; returns the events to show them."""
        if key not in self.options():
            raise ValueError(f"not an option now: {key}")
        p, self._rolls = self.player, []
        events = getattr(self, "do_" + key[0])(p, *key[1:])
        self.history.append((p.name, key, self._rolls))
        if p.ap <= 0 and key[0] != "end" and not self.winner and not self.pending:
            events += self.do_end(p)
        return events

    def do_move(self, p, place):
        p.ap -= 1
        owner = self.owner(place)
        locked = (place in LOCKED or owner is not None) and place not in p.opened
        if locked and owner not in self.suspects_at(place):
            if "crowbar" in p.items:
                ev = ["Le pied de biche fait sauter la serrure."]
            elif self.roll("crochetage", .5):
                ev = ["La serrure cède."]
            else:
                return ["La porte résiste, vous perdez du temps."]
            p.opened.add(place)
        else:
            ev = []
        p.place = place
        if place == "police":
            self.log.append((self.tick, p.name, f"{p.name} entre au commissariat."))
        return ev + self.arrive(p)

    def arrive(self, p, again=False):
        ev = [f"Vous êtes {'toujours ' if again else ''}: {self.label(p.place)}."]
        if p.place not in p.visited and p.place in PLACE_HINTS:
            ev.append(PLACE_HINTS[p.place])
        p.visited.add(p.place)
        owner = self.owner(p.place)
        if owner is not None and not p.knows(owner):
            self.reveal(p, owner, FAR_TRAITS, name=True)  # the name on the door, the photos on the wall
            ev.append(f"C'est chez {self.name(owner)} ({glimpse(self.case[owner])}).")
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
        if p.place in TAPED and not p.authorized and not self.roll("discrétion", .4):
            return ["Un agent vous repère et vous éloigne du ruban."]
        if p.place == "victim_house" and not p.code:
            p.code = True
            return ["Un post-it sur le frigo : le code du téléphone de la victime."]
        pool = [e for e in self.here(p) if e.id not in p.found]
        if not pool:
            p.exhausted.add(p.place)
            return ["Rien d'intéressant ici."]
        e = self.rng.choice(pool)
        p.found.add(e.id)
        if len(pool) == 1:
            p.exhausted.add(p.place)
        left = "D'autres choses traînent encore ici." if len(pool) > 1 else "Vous avez fait le tour des lieux."
        return [f"Vous trouvez : {e.label}. {e.text}"] + self.examine(p, e) + [left]

    def examine(self, p, e):
        if e.blood:
            if "forensic_kit" in p.items:
                return ["Vous sortez le kit médico-légal et analysez le sang sur place."] + self.learn(p, e)
            p.lab.append((e, self.tick + 1))
            return ["Sans kit, l'échantillon part au labo : résultat au prochain tour."]
        if e.phone:
            if "hacking_kit" in p.items:
                return ["Le kit de hacking fait sauter le verrouillage."] + self.learn(p, e)
            if p.code:
                return ["Le code trouvé chez la victime déverrouille le téléphone."] + self.learn(p, e)
            return ["Le téléphone est verrouillé. Le code doit traîner chez la victime."]
        return self.learn(p, e)

    def learn(self, p, e):
        p.facts.add(e.fact)
        return [f"Indice : {fact_label(e.fact)}."]

    def do_unlock(self, p, eid):
        p.ap -= 1
        return self.examine(p, self.evidence[eid])

    def do_observe(self, p, s):
        p.ap -= 1
        self.reveal(p, s, [Hand])
        return [f"{self.name(s)} signe une note de la main {TRAIT_TEXT[self.case[s][Hand]]}."]

    # ----------------------------------------------------------- interrogation

    def do_interrogate(self, p, s):
        """Approach someone: a good look, then up to three questions."""
        p.ap -= 1
        p.talked.add(s)
        self.reveal(p, s, FAR_TRAITS + [EyeColor] + ([Hand] if self.hand_visible[s] else []), name=True)
        ev = [f"{self.name(s)}. {portrait(self.case[s], self.hand_visible[s])}"]
        if not self.roll("persuasion", .3):
            p.talked.discard(s)
            return ev + [f"{self.name(s)} vous tourne le dos. Réessayez plus tard."]
        self.pending = {"who": s, "left": QUESTIONS_PER_INTERROGATION, "dialogue": []}
        return ev + [f"{self.name(s)} accepte de parler. {QUESTIONS_PER_INTERROGATION} questions, pas plus."]

    do_ring = do_interrogate  # same thing, on the doorstep

    def do_ask(self, p, q):
        s = self.pending["who"]
        intent, ev = getattr(self, "answer_" + q)(p, s)
        line = self._speak(self.persona(s), self.pending["dialogue"], QUESTIONS[q], intent)
        self.pending["dialogue"].append((q, line))
        self.pending["left"] -= 1
        ev = [f"{self.name(s)} — {line}"] + ev
        if self.pending["left"] == 0:
            ev.append(f"{self.name(s)} s'éloigne.")
            self.pending = None
        return ev

    def do_stop(self, p):
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
            return "Chez moi, seul. Personne pour le confirmer, je sais.", ["Noté : chez lui ce soir-là, invérifiable."]
        p.alibis.setdefault(s, False)
        names = ", ".join(self.name(t) for t in recalled)
        where = NIGHT_TEXT[self.night[s]]
        if names:
            text = f"Le soir du meurtre, j'étais {where}, avec {names}. Il y avait d'autres gens, je ne saurais pas dire qui."
        elif self.company(s):
            text = f"Le soir du meurtre, j'étais {where}. Il y avait du monde, mais je ne me souviens de personne en particulier."
        else:
            text = f"Le soir du meurtre, j'étais {where}, seul."
        return text, [f"Noté : {where}" + (f", avec {names}…" if names else "") + "."]

    def answer_link(self, p, s):
        self.reveal(p, s, [LinkToVictim])
        return LINK_QUOTES[self.case[s][LinkToVictim]], []

    def answer_seen(self, p, s):
        held = self.testimony(s)
        if s == 0:
            claims, text = [self.lie], f"J'ai vu quelqu'un partir en courant. {statement(self.lie)}"
        elif held:
            claims, text = [e.fact for e in held], " ".join(f"{e.text} {statement(e.fact)}" for e in held)
        else:
            return "Non, rien. J'étais ailleurs, je n'ai rien vu.", []
        p.heard.setdefault(s, set()).update(claims)
        return text, [f"Témoignage noté : {', '.join(fact_label(f) for f in claims)}."]

    def answer_grudge(self, p, s):
        t = self.gossip[s]
        if t is None:
            return "Tout le monde l'aimait bien. Enfin, c'est ce qu'on disait.", []
        self.reveal(p, t, [LinkToVictim], name=True)
        return f"{self.name(t)}. {GRUDGE[self.case[t][LinkToVictim]]}", [f"Noté : {self.name(t)}, {fact_label(self.case[t][LinkToVictim])}."]

    # ----------------------------------------------------------------- others

    def do_verify(self, p, s):
        """Ask around at the alibi place. Memories are patchy: some innocents are remembered,
        the murderer never is. One check per suspect, same answer for everyone."""
        p.ap -= 1
        who = BYSTANDER[p.place]
        if s != 0 and self.alibi_ok[s]:
            p.alibis[s] = True
            p.cleared.add(s)
            return [f"{who} : « {self.name(s)} ? Oui, toute la soirée, jusqu'à la fermeture. »",
                    f"L'alibi de {self.name(s)} tient. Ce qu'il ou elle vous a dit est fiable."]
        p.alibis[s] = None
        return [f"{who} : « {self.name(s)} ? Il y avait du monde ce soir-là... je ne saurais pas dire. »",
                f"L'alibi de {self.name(s)} n'est pas confirmé. Ça ne prouve rien, mais c'est noté."]

    def do_file(self, p, s):
        p.ap -= 1
        if not self.roll("persuasion", .3):
            return ["L'infirmière refuse d'ouvrir les dossiers. Réessayez plus tard."]
        self.reveal(p, s, [BloodType])
        return [f"Dossier médical de {self.name(s)} : groupe {TRAIT_TEXT[self.case[s][BloodType]]}."]

    def do_record(self, p, s):
        p.ap -= 1
        self.reveal(p, s, FAR_TRAITS + [LinkToVictim])
        return [f"Casier de {self.name(s)} : photo d'identité ({glimpse(self.case[s])}). "
                f"Relation avec la victime : {TRAIT_TEXT[self.case[s][LinkToVictim]]}."]

    def do_authorize(self, p):
        p.ap -= 1
        p.authorized = True
        self.log.append((self.tick, p.name, f"{p.name} obtient une autorisation."))
        return ["Le commissaire vous ouvre la scène de crime, les enregistrements et les casiers."]

    def do_accuse(self, p, s):
        p.ap = 0
        if s == 0:
            self.winner = p
            self.log.append((self.tick, p.name, f"{p.name} a démasqué {self.name(s)} !"))
            return [f"{self.name(s)} craque. Affaire classée, bravo."]
        p.skip = PENALTY
        for q in self.players:
            self.reveal(q, s, FAR_TRAITS, name=True)
            q.cleared.add(s)
        self.log.append((self.tick, p.name, f"{p.name} a accusé {self.name(s)} à tort : {self.name(s)} est innocent."))
        return [f"{self.name(s)} avait un alibi en béton. Vous perdez {PENALTY} tours."]

    def do_end(self, p):
        p.ap, self.pending = 0, None
        while True:
            self.current = (self.current + 1) % len(self.players)
            if self.current == 0:
                self.tick += 1
                self.move_suspects()
            q = self.player
            if q.skip:
                q.skip -= 1
                continue
            return [f"— Tour {self.tick + 1}, à {q.name}."] + self.start_turn(q)

    def start_turn(self, q):
        q.ap = AP
        ev = []
        for e, t in list(q.lab):
            if t <= self.tick:
                q.lab.remove((e, t))
                ev += [f"Le labo a rendu son verdict sur {e.label.lower()}."] + self.learn(q, e)
        return ev + self.arrive(q, again=True)
