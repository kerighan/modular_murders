"""Suspects, and the Case that picks a murderer and the clues giving them away."""

import itertools
import random

import networkx as nx

from clue import CLUES
from genotype import TRAITS, Alibi, criterions, get_random_enum
from modality import Location
from routine import MurderWeaponRoutine, VictimPhoneLockRoutine, VictimPhoneRoutine


class Suspect:
    """A person of interest with randomly drawn traits."""

    def __init__(self, rng=random):
        self.guilty = False
        for trait, (attr, p) in TRAITS.items():
            setattr(self, attr, get_random_enum(trait, p, rng))

    def __getitem__(self, trait):
        """Value of a trait, e.g. `suspect[HairColor]`."""
        return getattr(self, TRAITS[trait][0])

    @property
    def identity(self):
        return {"guilty": self.guilty, **{attr: getattr(self, attr) for attr, _ in TRAITS.values()}}

    def __repr__(self):
        return str(self.identity)


class Case:
    """A murder case. Suspect 0 is the murderer; `clues` (plus `alibis`) single them out."""

    def __init__(self, seed=None, n_suspects=None):
        self.rng = random.Random(seed)
        self.n_suspects = n_suspects or self.rng.randint(5, 10)
        self.suspects = [Suspect(self.rng) for _ in range(self.n_suspects)]
        self.suspects[0].guilty = True

        self.graph = self.build_graph()
        # murderer's trait value -> ids of the suspects sharing it (always includes 0)
        self.commonalities = {f: set(self.graph.successors(f)) for f in self.graph.predecessors(0)}
        self.facts = self.pick_facts()
        # one piece of evidence per revealed fact
        self.clues = self.pick_clues()
        # innocents matching every clue: they need an alibi to be cleared
        self.alibis = {i: get_random_enum(Alibi, rng=self.rng) for i in self.remaining(self.facts) - {0}}
        self.environment = self.build_environment()

    def __getitem__(self, i):
        return self.suspects[i]

    @property
    def murderer(self):
        return self.suspects[0]

    @property
    def dopplegangers(self):
        """Suspects sharing every trait with the murderer: clues alone can't clear them."""
        return self.remaining(self.commonalities) - {0}

    def build_graph(self):
        """Bipartite digraph: trait value -> suspect id."""
        G = nx.DiGraph()
        G.add_nodes_from(range(self.n_suspects))
        for value in criterions:
            G.add_edges_from((value, i) for i, s in enumerate(self.suspects) if s[type(value)] == value)
        G.remove_nodes_from(list(nx.isolates(G)))
        return G

    def draw(self):
        import matplotlib.pyplot as plt

        nx.draw_networkx(self.graph, pos=nx.bipartite_layout(self.graph, criterions))
        plt.show()

    def remaining(self, facts):
        """Ids of the suspects compatible with all `facts`."""
        return set(range(self.n_suspects)).intersection(*(self.commonalities[f] for f in facts))

    def pick_facts(self):
        """Choose which of the murderer's traits to reveal.

        We want the longest minimal combination isolating the murderer: as many clues
        as possible, none redundant. When dopplegangers make isolation impossible,
        reveal everything and let alibis do the rest.
        """
        values = list(self.commonalities)
        subsets = (c for r in range(1, len(values) + 1) for c in itertools.combinations(values, r))
        isolating = [c for c in subsets if self.remaining(c) == {0}]
        minimal = [c for c in isolating if not any(set(o) < set(c) for o in isolating)]
        if not minimal:
            return tuple(values)
        longest = max(map(len, minimal))
        return self.rng.choice([c for c in minimal if len(c) == longest])

    def pick_clues(self):
        """For each fact, a random clue of the right trait consistent with the other facts."""
        return {
            fact: self.rng.choice([c for c in CLUES if isinstance(fact, c.trait) and c.is_consistent(self.facts)])
            for fact in self.facts
        }

    def build_environment(self):
        """What the player can inspect.

        Locations holding a clue are always available; the others may show up at random
        and lead nowhere.
        """
        rng, where = self.rng, {c.location for c in self.clues.values()}
        env = {
            "can_inspect_murder_weapon": Location.MURDER_WEAPON in where,
            "can_inspect_victim_phone": Location.VICTIM_PHONE in where,
            "can_inspect_cctv": Location.CCTV in where,
            "can_inspect_neighbor": Location.NEIGHBOR in where,
            "can_inspect_houses": [Location.MURDERER_HOUSE in where] + [p(.33, rng) for _ in range(1, self.n_suspects)],
            "can_inspect_victim_house": False,
        }
        env["murder_weapon"] = env["can_inspect_murder_weapon"]
        env["victim_phone"] = env["can_inspect_victim_phone"] or p(.15, rng)
        env["cctv"] = env["can_inspect_cctv"] or p(.33, rng)
        env["neighbor"] = env["can_inspect_neighbor"] or p(.15, rng)

        if env["victim_phone"]:
            env["victim_phone_routine"] = get_random_enum(VictimPhoneRoutine, rng=rng)
            env["victim_phone_lock_routine"] = get_random_enum(VictimPhoneLockRoutine, rng=rng)
            # a locked phone sends the player to the victim's house for the code
            env["can_inspect_victim_house"] = env["victim_phone_lock_routine"] != VictimPhoneLockRoutine.UNLOCK
        if env["murder_weapon"]:
            env["murder_weapon_routine"] = get_random_enum(MurderWeaponRoutine, rng=rng)
        return env


def p(threshold, rng=random):
    """Bernoulli draw."""
    return rng.random() < threshold
