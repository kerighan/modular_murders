"""Offline structural diversity audit; not an investigation solver or fun score."""
import argparse
import json
import math
from collections import Counter

from scenario_crime import CrimeBuilder
from scenario_kernel import KernelBuilder, romantic_triangles
from scenario_situations import situation_fingerprint


def audit(count=500, seed=0, *, witnesses=False):
    if type(count) is not int or count < 1:
        raise ValueError("positive integer count required")
    if type(witnesses) is not bool:
        raise TypeError("witnesses must be bool")
    situations, methods, motives, signatures = Counter(), Counter(), Counter(), Counter()
    unrelated_triangles = 0
    victim_unrelated_triangles = 0
    memory_kinds, witness_counts, remaining_counts = Counter(), Counter(), Counter()
    total_artifacts = acquired_artifacts = 0
    for index in range(seed, seed + count):
        kernel = KernelBuilder(index).sample()
        crime = CrimeBuilder(f"physical-v4:{index}").build(kernel)
        situations[crime.execution.situation.value] += 1
        methods[crime.method.value] += 1
        motives[kernel.premise.motive.value] += 1
        signatures[situation_fingerprint(crime)] += 1
        by_id = {r.id: r for r in kernel.world.relationships}
        innocent_triangles = []
        for center, former, current in romantic_triangles(kernel.world):
            actors = set(by_id[former].people) | set(by_id[current].people)
            if kernel.roles.author not in actors:
                innocent_triangles.append(actors)
        unrelated_triangles += bool(innocent_triangles)
        victim_unrelated_triangles += any(kernel.roles.victim in actors for actors in innocent_triangles)
        if witnesses:
            from scenario_observations import project, walkthrough, with_witnesses
            from scenario_witnesses import WitnessBuilder
            layer = WitnessBuilder(f"{index}:0").build(crime)
            plan = with_witnesses(project(crime), layer)
            replay = walkthrough(plan)["audit"]
            total_artifacts += replay["artifacts_total"]
            acquired_artifacts += replay["artifacts_acquired"]
            events = {e.id: e for e in layer.events}
            memory_kinds.update(events[p.event].kind.value for p in layer.perceptions)
            witness_counts[len(layer.witnesses)] += 1
            remaining_counts[replay["remaining_count"]] += 1
            # Validation against private truth, NEVER manufacture a support using it.
            if kernel.roles.author not in plan.graph().remaining([a.id for a in plan.artifacts]):
                raise ValueError("Projection incorrectly excludes the actual assailant")
    entropy = -sum((n / count) * math.log2(n / count) for n in situations.values())
    result = {"count": count, "seed": seed, "situations": dict(situations), "methods": dict(methods),
            "motives": dict(motives), "structural_fingerprints": len(signatures),
            "largest_fingerprint_fraction": max(signatures.values()) / count,
            "largest_situation_fraction": max(situations.values()) / count,
            "situation_entropy_bits": round(entropy, 4),
            "cases_with_triangle_without_killer": unrelated_triangles,
            "cases_with_victim_triangle_without_killer": victim_unrelated_triangles,
            "note": "Structural authoring diversity only: not resolution diversity, solvability or player enjoyment."}
    if witnesses:
        result["witness_projection"] = {"memory_kinds": dict(memory_kinds),
            "witness_counts": dict(witness_counts), "remaining_after_all_sources": dict(remaining_counts),
            "artifacts_total": total_artifacts, "artifacts_acquired": acquired_artifacts,
            "note": "Offline identity compatibility assumes cast appearances known. Context/handling is not guilt; not complete reconstruction or movement/AP validation."}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--witnesses", action="store_true", help="Audit bounded witness memories and discovery projection")
    args = parser.parse_args()
    try:
        result = audit(args.count, args.seed, witnesses=args.witnesses)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
