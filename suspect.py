import enum
import itertools

import networkx as nx

from genotype import *


class Suspect:
    def __init__(self):
        self.guilty = False
        self.gender = get_random_gender()
        self.eye_color = get_random_eye_color()
        self.hair_color = get_random_hair_color()
        self.height = get_random_height()
        self.blood_type = get_random_blood_type()
        self.hand = get_random_hand()

    @property
    def identity(self):
        return {
            "guilty": self.guilty,
            "gender": self.gender,
            "eye_color": self.eye_color,
            "hair_color": self.hair_color,
            "height": self.height,
            "blood_type": self.blood_type,
            "hand": self.hand
        }

    def __repr__(self):
        return str(self.identity)


class Case:
    def __init__(self, n_suspects, seed=None):
        if seed is not None:
            import random
            random.seed(seed)

        self.n_suspects = n_suspects
        self.suspects = [Suspect() for i in range(n_suspects)]
        self.suspects[0].guilty = True
        self.suspect2id = {s: i for i, s in enumerate(self.suspects)}

        self.get_graph()
        self.get_commonalities()
        self.get_dopplegangers()
        self.get_maximum_features()

    def __getitem__(self, key):
        return self.suspects[key]

    def get_suspect_identity(self):
        return self.suspects[0].identity

    def filter(self, criteria):
        if isinstance(criteria, Gender):
            return [
                suspect for suspect in self.suspects
                if suspect.gender == criteria]
        elif isinstance(criteria, EyeColor):
            return [
                suspect for suspect in self.suspects
                if suspect.eye_color == criteria]
        elif isinstance(criteria, HairColor):
            return [
                suspect for suspect in self.suspects
                if suspect.hair_color == criteria]
        elif isinstance(criteria, Height):
            return [
                suspect for suspect in self.suspects
                if suspect.blood_type == criteria]
        elif isinstance(criteria, BloodType):
            return [
                suspect for suspect in self.suspects
                if suspect.blood_type == criteria]
        elif isinstance(criteria, Hand):
            return [
                suspect for suspect in self.suspects
                if suspect.hand == criteria]

    def data(self):
        return [s.identity for s in self.suspects]

    def get_graph(self):
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
        features = list(self.G.predecessors(0))
        feature2suspects = {}
        for feature in features:
            feature2suspects[feature] = set(self.G.neighbors(feature))
        self.commonalities = feature2suspects
        return feature2suspects

    def get_dopplegangers(self):
        for i, (_, suspects) in enumerate(self.commonalities.items()):
            if i == 0:
                inter = set(suspects)
            else:
                inter = inter.intersection(suspects)
        inter.remove(0)
        self.dopplegangers = inter
        return inter

    def get_maximum_features(self):
        from pprint import pprint

        cm = self.commonalities
        cm = sorted(cm.items(), key=lambda x: len(x[1]))
        cm = [(a, b) for a, b in cm if len(b) > 1]

        minimum_features = []
        r = 5
        loop = True
        while r > 1:
            for feature_combination in itertools.combinations(cm, r):
                inter = set()
                n_comb = len(feature_combination)
                for i, (feature, suspects) in enumerate(feature_combination):
                    if i == 0:
                        inter = set(suspects)
                    else:
                        inter = inter.intersection(suspects)
                        if len(inter) == 1:
                            if n_comb - 1 == i:
                                minimum_features.append(feature_combination)
                                # loop = False
                                break
                            else:
                                break
            r -= 1
        # print(r + 1)
        pprint(minimum_features)
        if len(minimum_features) == 0:
            print(self.dopplegangers, "dopplegangers")
        print(len(minimum_features[0]))