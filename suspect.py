"""Manage suspects and deduction logic for the murder mystery game."""

import itertools
import random
from pprint import pprint

import networkx as nx

from clue import AlibiClue, clues, location
from genotype import (
    Alibi,
    BloodType,
    EyeColor,
    Gender,
    HairColor,
    Hand,
    Height,
    LinkToVictim,
    criterions,
    get_random_blood_type,
    get_random_eye_color,
    get_random_gender,
    get_random_hair_color,
    get_random_hand,
    get_random_height,
    get_random_link,
)
from routine import (
    VictimPhoneLockRoutine,
    get_random_murder_weapon_routine,
    get_random_victim_phone_lock_routine,
    get_random_victim_phone_routine,
)


class Suspect:
    """A person of interest with randomly generated characteristics."""

    def __init__(self):
        # Start as innocent until proven guilty.
        self.guilty = False
        # Generate a random profile using weighted distributions.
        self.gender = get_random_gender()
        self.eye_color = get_random_eye_color()
        self.hair_color = get_random_hair_color()
        self.height = get_random_height()
        self.blood_type = get_random_blood_type()
        self.hand = get_random_hand()
        self.link = get_random_link()

    @property
    def identity(self):
        """Return a dictionary representation of the suspect's traits."""

        return {
            "guilty": self.guilty,
            "gender": self.gender,
            "eye_color": self.eye_color,
            "hair_color": self.hair_color,
            "height": self.height,
            "blood_type": self.blood_type,
            "hand": self.hand,
            "link_to_victim": self.link,
        }

    def __repr__(self):
        return str(self.identity)


class Case:
    """Encapsulates a murder case with multiple suspects and clues."""

    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)

        # Create a random number of suspects and mark the first as guilty.
        self.n_suspects = random.randint(5, 10)
        self.suspects = [Suspect() for i in range(self.n_suspects)]
        self.suspects[0].guilty = True
        self.suspect2id = {s: i for i, s in enumerate(self.suspects)}

        # Precompute structures used in deduction.
        self.get_graph()
        self.get_commonalities()
        self.get_dopplegangers()
        self.get_maximum_features()
        self.get_clues()
        self.get_environment()

    def __getitem__(self, key):
        return self.suspects[key]

    def get_suspect_identity(self):
        return self.suspects[0].identity

    def filter(self, criteria):
        """Return suspects matching the given criterion."""

        if isinstance(criteria, Gender):
            return [suspect for suspect in self.suspects if suspect.gender == criteria]
        elif isinstance(criteria, EyeColor):
            return [suspect for suspect in self.suspects if suspect.eye_color == criteria]
        elif isinstance(criteria, HairColor):
            return [suspect for suspect in self.suspects if suspect.hair_color == criteria]
        elif isinstance(criteria, Height):
            return [suspect for suspect in self.suspects if suspect.height == criteria]
        elif isinstance(criteria, BloodType):
            return [suspect for suspect in self.suspects if suspect.blood_type == criteria]
        elif isinstance(criteria, Hand):
            return [suspect for suspect in self.suspects if suspect.hand == criteria]
        elif isinstance(criteria, LinkToVictim):
            return [suspect for suspect in self.suspects if suspect.link == criteria]

    def data(self):
        return [s.identity for s in self.suspects]

    def get_graph(self):
        """Build a bipartite graph linking features to suspects."""

        G = nx.DiGraph()
        G.add_nodes_from(criterions + list(range(self.n_suspects)))
        for criteria in criterions:
            for suspect in self.filter(criteria):
                suspect_id = self.suspect2id[suspect]
                G.add_edge(criteria, suspect_id)
        G.remove_nodes_from(list(nx.isolates(G)))
        self.G = G
        return G

    def draw(self):
        import matplotlib.pyplot as plt
        nx.draw_networkx(self.G, pos=nx.bipartite_layout(self.G, criterions))
        plt.show()

    def get_commonalities(self):
        """Map each feature to suspects sharing it with the murderer."""

        features = list(self.G.predecessors(0))
        feature2suspects = {}
        for feature in features:
            feature2suspects[feature] = set(self.G.neighbors(feature))
        self.commonalities = feature2suspects
        return feature2suspects

    def get_dopplegangers(self):
        """Return suspects sharing all common traits with the murderer."""

        for i, (_, suspects) in enumerate(self.commonalities.items()):
            if i == 0:
                inter = set(suspects)
            else:
                inter = inter.intersection(suspects)
        inter.remove(0)
        self.dopplegangers = inter
        return inter

    def get_maximum_features(self):
        """Search for feature combinations that uniquely identify the killer."""

        cm = self.commonalities
        cm = sorted(cm.items(), key=lambda x: len(x[1]))
        cm = [(a, b) for a, b in cm if len(b) > 1]

        possibilities = []
        min_possibilities = None
        min_n_possibilities = float("inf")
        r = 7
        # Try decreasing numbers of features until a unique combination is found.
        while r > 2:
            for feature_combination in itertools.combinations(cm, r):
                inter = set()
                n_comb = len(feature_combination)
                for i, (_, suspects) in enumerate(feature_combination):
                    if i == 0:
                        inter = set(suspects)
                    else:
                        inter = inter.intersection(suspects)
                        if len(inter) == 1:
                            if n_comb - 1 == i:
                                possibilities.append(feature_combination)
                                break
                            else:
                                possibilities.append(feature_combination[:i])
                                break
                if len(inter) < min_n_possibilities:
                    min_n_possibilities = len(inter)
                    min_possibilities = feature_combination
            r -= 1

        possibilities = sorted(possibilities, key=lambda x: len(x), reverse=True)
        print(self.n_suspects, "suspects")
        if len(possibilities) == 0:
            self.possibilities = [min_possibilities]
        else:
            self.possibilities = possibilities
        pprint(self.possibilities[0])

    def get_clues(self):
        """Generate a set of clues based on distinguishing features."""

        from collections import defaultdict

        facts_and_suspects = self.possibilities[0]
        facts = [it for it, _ in facts_and_suspects]
        fact2clues = defaultdict(list)
        for clue in clues:
            for fact in facts:
                if not isinstance(fact, clue.clue_type):
                    continue

                if clue.check_conditions(facts):
                    fact2clues[fact].append(clue)

        # Generate clues and determine which suspects require an alibi.
        generated_clues = {}
        for i, (fact, c) in enumerate(fact2clues.items()):
            generated_clues[fact] = random.choice(c)
            if i == 0:
                alibis = set(self.commonalities[fact])
            else:
                alibis = alibis.intersection(self.commonalities[fact])
        alibis.remove(0)
        if len(alibis) > 0:
            generated_clues[Alibi.BAR] = AlibiClue
        self.clues = generated_clues
        print(self.clues)

    def get_environment(self):
        """Create an environment dict describing available investigative actions."""

        environment = {}
        murder_weapon = False
        can_inspect_murder_weapon = False

        victim_phone = False
        can_inspect_victim_phone = False

        can_inspect_victim_house = False

        can_inspect_houses = [False] * self.n_suspects

        cctv = False
        can_inspect_cctv = False

        neighbor = False
        can_inspect_neighbor = False

        for clue in self.clues.values():
            if not hasattr(clue, "location"):
                continue
            if clue.location == location.MURDER_WEAPON:
                murder_weapon = True
                can_inspect_murder_weapon = True
            elif clue.location == location.VICTIM_PHONE:
                victim_phone = True
                can_inspect_victim_phone = True
            elif clue.location == location.MURDERER_HOUSE:
                can_inspect_houses[0] = True
            elif clue.location == location.CCTV:
                cctv = True
                can_inspect_cctv = True
            elif clue.location == location.NEIGHBOR:
                neighbor = True
                can_inspect_neighbor = True

        # Randomly re-populate optional evidence locations.
        for i in range(1, self.n_suspects):
            can_inspect_houses[i] = p(.33)
        if not cctv:
            cctv = p(.33)
        if not victim_phone:
            victim_phone = p(.15)
        if not neighbor:
            neighbor = p(.15)

        if victim_phone:
            environment["victim_phone_routine"] = get_random_victim_phone_routine()
            environment["victim_phone_lock_routine"] = get_random_victim_phone_lock_routine()
            if (
                environment["victim_phone_lock_routine"]
                != VictimPhoneLockRoutine.UNLOCK
            ):
                can_inspect_victim_house = True
        if murder_weapon:
            environment["murder_weapon_routine"] = get_random_murder_weapon_routine()

        # murder weapon
        environment["murder_weapon"] = murder_weapon
        environment["can_inspect_murder_weapon"] = can_inspect_murder_weapon
        # victim phone
        environment["victim_phone"] = victim_phone
        environment["can_inspect_victim_phone"] = can_inspect_victim_phone
        environment["can_inspect_victim_house"] = can_inspect_victim_house
        # suspects house
        environment["can_inspect_houses"] = can_inspect_houses
        # cctv
        environment["cctv"] = cctv
        environment["can_inspect_cctv"] = can_inspect_cctv
        # neighbor
        environment["neighbor"] = neighbor
        environment["can_inspect_neighbor"] = can_inspect_neighbor

        pprint(environment)
        # Expose the generated environment for external use and return it.
        self.environment = environment
        return environment


def p(threshold):
    return random.random() < threshold
