"""Deduction algebra: immutable evidence supports, separate from player knowledge.

A support is the set of people compatible with an observation *on its own*,
not the shrinking set remaining after earlier observations. Route / identity
information is not incriminating evidence. Conclusions are intersections.
"""
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Observation:
    id: str
    axis: str
    candidates: frozenset

    def __post_init__(self):
        object.__setattr__(self, "candidates", frozenset(self.candidates))


class ScenarioGraph:
    def __init__(self, population, observations, routes=()):
        self.population = frozenset(population)
        observations = list(observations)
        self.observations = {o.id: o for o in observations}
        if len(self.observations) != len(observations):
            raise ValueError("Duplicate observation ID")
        self.routes = tuple(routes)
        for o in self.observations.values():
            if len(o.candidates) < 2 or not o.candidates <= self.population:
                raise ValueError(f"Non-ambiguous evidence invariant violated: {o.id}")
        if any(a not in self.observations or b not in self.observations for a, b in self.routes):
            raise ValueError("Unknown observation in investigation route")

    def remaining(self, observed=()):
        result = set(self.population)
        for key in observed:
            if key in self.observations:
                result.intersection_update(self.observations[key].candidates)
        return result

    def minimum_depth(self):
        keys = list(self.observations)
        for size in range(1, len(keys) + 1):
            if any(len(self.remaining(group)) == 1 for group in combinations(keys, size)):
                return size
        return None

    def validate_solution(self, culprit):
        if self.remaining(self.observations) != {culprit}:
            raise ValueError("Scenario cannot converge to the real culprit")
        if any(culprit not in o.candidates for o in self.observations.values()):
            raise ValueError("A true observation excludes the culprit")
