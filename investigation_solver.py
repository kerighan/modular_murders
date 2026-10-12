"""Offline source-planning audit, not a player bot or an Android dependency.

States are sets of acquired observations, not just remaining suspects: a
non-filtering observation can unlock a decisive action. Actions have AND
preconditions and may reveal several observations at once. Suggested routes
in ScenarioGraph are deliberately NOT interpreted as access restrictions.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import combinations
from math import log2

import networkx as nx


@dataclass(frozen=True)
class InvestigationAction:
    id: str
    kind: str
    reveals: tuple
    requires: tuple = ()
    cost: int = 1
    method: str = ""

    def __post_init__(self):
        object.__setattr__(self, "reveals", tuple(self.reveals))
        object.__setattr__(self, "requires", tuple(self.requires))
        if not self.id or not self.kind or not self.reveals:
            raise ValueError("Actions need an id, kind and observations")
        if type(self.cost) is not int or self.cost < 1:
            raise ValueError("Action costs must be positive integers")
        if not self.method:
            object.__setattr__(self, "method", self.kind)


class InvestigationSolver:
    """Exact finite-state planner; all minimum-cost paths counted with DP.

    It knows each source's possible output, like an offline level validator.
    It never picks a culprit as its goal: solving means exactly one candidate
    remains, plus optional required observations (e.g. reconstruction rules).
    Limits fail explicitly instead of returning partial/approximate metrics.
    """

    def __init__(self, graph, actions, *, initial=(), required=(), max_states=65536):
        self.graph = graph
        self.actions = tuple(actions)
        self.keys = tuple(sorted(graph.observations))
        self.bits = {key: 1 << i for i, key in enumerate(self.keys)}
        self.max_states = max_states
        if max_states < 1:
            raise ValueError("max_states must be positive")
        if len({a.id for a in self.actions}) != len(self.actions):
            raise ValueError("Duplicate action id")
        self.initial = self._mask(initial)
        self.required = self._mask(required)
        self.compiled = [(a, self._mask(a.requires), self._mask(a.reveals)) for a in self.actions]
        self._candidates = {}

    def _mask(self, keys):
        mask = 0
        for key in keys:
            if key not in self.bits:
                raise ValueError(f"Unknown observation: {key}")
            mask |= self.bits[key]
        return mask

    def _keys(self, mask):
        return tuple(key for key in self.keys if mask & self.bits[key])

    def _remaining(self, mask):
        if mask not in self._candidates:
            self._candidates[mask] = self.graph.remaining(self._keys(mask))
        return self._candidates[mask]

    def _goal(self, mask):
        return len(self._remaining(mask)) == 1 and mask & self.required == self.required

    def _transitions(self, mask, disabled_kind=None, disabled_method=None):
        if self._goal(mask) or not self._remaining(mask):
            return
        for action, needs, yields in self.compiled:
            if action.kind == disabled_kind or action.method == disabled_method:
                continue
            target = mask | yields
            if needs & mask == needs and target != mask:
                yield action, target

    def _search(self, disabled_kind=None, disabled_method=None):
        distances = {self.initial: 0}
        queue = [(0, self.initial)]
        edges = defaultdict(list)
        while queue:
            distance, state = heappop(queue)
            if distance != distances[state]:
                continue
            for action, target in self._transitions(state, disabled_kind, disabled_method):
                edges[state].append((action, target))
                cost = distance + action.cost
                if cost < distances.get(target, float("inf")):
                    distances[target] = cost
                    if len(distances) > self.max_states:
                        raise ValueError("Knowledge-state limit exceeded; audit not completed")
                    heappush(queue, (cost, target))
        goals = [state for state in distances if self._goal(state)]
        best = min((distances[state] for state in goals), default=None)
        return distances, edges, best, [state for state in goals if distances[state] == best]

    def minimal_proofs(self, max_checks=100000):
        """Inclusion-minimal logical certificates, separate from acquisition.

        A certificate may be inaccessible through supplied actions. Gates and
        required reconstruction observations are not evidence of guilt.
        """
        proofs, masks, checked = [], [], 0
        for size in range(len(self.keys) + 1):
            for group in combinations(self.keys, size):
                checked += 1
                if checked > max_checks:
                    raise ValueError("Proof enumeration limit exceeded; audit not completed")
                mask = self._mask(group)
                if any(mask & earlier == earlier for earlier in masks):
                    continue
                if len(self._remaining(mask)) == 1:
                    masks.append(mask)
                    proofs.append(list(group))
        return proofs

    def audit(self):
        distances, edges, best, goals = self._search()
        proofs = self.minimal_proofs()
        signatures = Counter(tuple(sorted(self.graph.observations[key].axis for key in proof)) for proof in proofs)
        result = {
            "solvable": best is not None,
            "minimum_cost": best,
            "reachable_knowledge_states": len(distances),
            "minimal_proofs": proofs,
            "proof_axis_patterns": [{"axes": list(pattern), "count": n} for pattern, n in sorted(signatures.items())],
            "optimal_plan_count": 0,
        }
        if best is None:
            return result

        # Keep all action-labelled optimal edges. Parallel sources with identical
        # outputs remain distinct choices; nx.DiGraph would collapse them.
        optimal = defaultdict(list)
        for state, transitions in edges.items():
            for action, target in transitions:
                if distances[state] + action.cost == distances[target] <= best:
                    optimal[state].append((action, target))
        ordered = sorted(distances, key=lambda state: (distances[state], state))
        forward = defaultdict(int, {self.initial: 1})
        for state in ordered:
            for _, target in optimal[state]:
                forward[target] += forward[state]
        backward = defaultdict(int, {state: 1 for state in goals})
        for state in reversed(ordered):
            if state not in goals:
                backward[state] = sum(backward[target] for _, target in optimal[state])
        total = sum(forward[state] for state in goals)
        result["optimal_plan_count"] = total

        action_inclusion, expected_costs = Counter(), Counter()
        expected = {dimension: Counter() for dimension in ("kind", "method")}
        closing = {dimension: Counter() for dimension in expected}
        gains = {dimension: Counter() for dimension in expected}
        goal_set = set(goals)
        for state in ordered:
            for action, target in optimal[state]:
                weight = forward[state] * backward[target] / total
                if not weight:
                    continue
                action_inclusion[action.id] += weight
                expected_costs[action.kind] += weight * action.cost
                before, after = len(self._remaining(state)), len(self._remaining(target))
                gain = log2(before / after)
                for dimension in expected:
                    label = getattr(action, dimension)
                    expected[dimension][label] += weight
                    gains[dimension][label] += weight * gain
                    if target in goal_set:
                        closing[dimension][label] += weight
        result["optimal_action_inclusion"] = dict(sorted(action_inclusion.items()))
        result["optimal_expected_cost_by_kind"] = dict(sorted(expected_costs.items()))

        for dimension in expected:
            labels = sorted({getattr(a, dimension) for a in self.actions})
            inclusion, without = {}, {}
            for label in labels:
                avoiding = defaultdict(int, {self.initial: 1})
                for state in ordered:
                    for action, target in optimal[state]:
                        if getattr(action, dimension) != label:
                            avoiding[target] += avoiding[state]
                inclusion[label] = 1 - sum(avoiding[state] for state in goals) / total
                kwargs = {"disabled_" + dimension: label}
                without[label] = self._search(**kwargs)[2]
            counts = expected[dimension]
            steps = sum(counts.values())
            shares = {key: value / steps for key, value in counts.items()} if steps else {}
            entropy = -sum(p * log2(p) for p in shares.values() if p)
            result[dimension + "_metrics"] = {
                "optimal_inclusion": inclusion,
                "minimum_cost_without": without,
                "unavoidable": [key for key in labels if without[key] is None],
                "expected_count": dict(sorted(counts.items())),
                "step_share": dict(sorted(shares.items())),
                "closing_share": dict(sorted(closing[dimension].items())),
                "candidate_reduction_bits": dict(sorted(gains[dimension].items())),
                "entropy_bits": entropy,
                "concentration_hhi": sum(p * p for p in shares.values()),
            }

        # Count action-type multisets, not just permutations of the same recipe.
        patterns = defaultdict(Counter)
        patterns[self.initial][()] = 1
        for state in ordered:
            for action, target in optimal[state]:
                if not backward[target]:
                    continue
                for pattern, count in patterns[state].items():
                    updated = dict(pattern)
                    updated[action.method] = updated.get(action.method, 0) + 1
                    patterns[target][tuple(sorted(updated.items()))] += count
                if len(patterns[target]) > 10000:
                    raise ValueError("Action-pattern limit exceeded; audit not completed")
        recipes = Counter()
        for state in goals:
            recipes.update(patterns[state])
        result["optimal_method_patterns"] = [
            {"counts": dict(pattern), "plans": count, "share": count / total}
            for pattern, count in sorted(recipes.items())
        ]
        # Supplemental all-pairs dependency centrality, NOT an AND/OR solver.
        dependency = nx.DiGraph()
        dependency.add_nodes_from(("observation", key) for key in self.keys)
        for action in self.actions:
            node = ("action", action.id)
            dependency.add_node(node)
            dependency.add_edges_from((("observation", key), node) for key in action.requires)
            dependency.add_edges_from((node, ("observation", key)) for key in action.reveals)
        centrality = nx.betweenness_centrality(dependency)
        result["dependency_action_betweenness"] = {a.id: centrality[("action", a.id)] for a in self.actions}
        return result
