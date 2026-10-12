"""Read-only audit of the narrative projection; no saves or engine mutations.

Run: python scenario_audit.py --count 100
     python scenario_audit.py --seed 42 --json
This is NOT the complete PA/travel/QTE/trait-evidence game solver.
"""
import argparse
import json
from collections import Counter, defaultdict
from math import fsum

from investigation_solver import InvestigationAction, InvestigationSolver
from scenario_graph import Observation, ScenarioGraph


def narrative_projection(story):
    """Reflect source bundles and real camera/alibi preconditions.

    Access to rooms and police permission are assumed acquired. A source visit
    costs one investigative action, not its travel PA. Duplicate trace papers
    produce the same observation; one search collects all papers in a room.
    """
    population = story.graph.population
    observations = list(story.graph.observations.values()) + [
        Observation("rival_document", "orientation", population),
        Observation("verified_alibi", "alibi", population - {story.rival}),
    ]
    graph = ScenarioGraph(population, observations, story.graph.routes)
    bundles = defaultdict(set)
    for key, source in story.sources.items():
        observation = "trace" if key.startswith("trace_") else "rival_document" if key == "rival" else key
        if observation in graph.observations:
            bundles[source["place"]].add(observation)
    actions = [InvestigationAction("search:" + place, "search", tuple(sorted(keys)), method="read_documents")
               for place, keys in sorted(bundles.items())]
    actions += [
        InvestigationAction("camera", "check_timeline", ("camera",), ("clock", "trace"), method="analyse_video"),
        InvestigationAction("verify_alibi", "check_timeline", ("verified_alibi",), ("rival_document",), method="verify_alibi"),
    ]
    return graph, actions


def audit_story(story):
    graph, actions = narrative_projection(story)
    deduction = InvestigationSolver(graph, actions).audit()
    reconstruction = InvestigationSolver(graph, actions, required=(story.access_key, "clock", "trace", "camera")).audit()
    return {
        "seed": story.game.seed,
        "family": story.family,
        "object_fate": story.object_fate,
        "scope": "narrative sources + verified rival alibi; rooms/permission assumed; no travel, QTE or physical traits",
        "deduction": deduction,
        "reconstruction_requirements": reconstruction,
    }


def summarize(reports, goal="deduction"):
    """Each seed weighs equally, not each permutation/source-rich case."""
    reports = list(reports)
    solved = [report[goal] for report in reports if report[goal]["solvable"]]
    result = {"cases": len(reports), "solvable": len(solved), "goal": goal}
    if not solved:
        return result
    n = len(solved)
    unavoidable = Counter()
    closing, shares = Counter(), Counter()
    recipes = Counter()
    for audit in solved:
        metrics = audit["method_metrics"]
        unavoidable.update(metrics["unavoidable"])
        closing.update(metrics["closing_share"])
        shares.update(metrics["step_share"])
        for recipe in audit["optimal_method_patterns"]:
            recipes[tuple(sorted(recipe["counts"].items()))] += recipe["share"]
    recipe_total = fsum(recipes.values())
    recipe_shares = {pattern: weight / recipe_total for pattern, weight in recipes.items()}
    result.update({
        "family_counts": dict(Counter(report["family"] for report in reports)),
        "minimum_cost_counts": dict(Counter(audit["minimum_cost"] for audit in solved)),
        "unavoidable_method_case_share": {key: value / n for key, value in sorted(unavoidable.items())},
        "mean_closing_method_share": {key: value / n for key, value in sorted(closing.items())},
        "mean_method_step_share": {key: value / n for key, value in sorted(shares.items())},
        "method_recipe_distribution": [{"counts": dict(pattern), "case_weighted_share": share}
                                       for pattern, share in sorted(recipe_shares.items())],
        "recipe_concentration_hhi": fsum(share * share for share in recipe_shares.values()),
        "mean_optimal_plan_count": sum(audit["optimal_plan_count"] for audit in solved) / n,
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, help="Audit one seed")
    parser.add_argument("--start-seed", type=int, default=0)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")
    from game import Game  # The generic solver does not depend on the generator.
    seeds = [args.seed] if args.seed is not None else range(args.start_seed, args.start_seed + args.count)
    reports = [audit_story(Game(seed).story) for seed in seeds]
    output = {
        "scope": reports[0]["scope"],
        "deduction_summary": summarize(reports),
        "reconstruction_summary": summarize(reports, "reconstruction_requirements"),
    }
    if args.seed is not None:
        output["case"] = reports[0]
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return
    print("Audit narratif — déplacements, permissions et indices physiques exclus")
    for title, summary in (("Déduction unique", output["deduction_summary"]),
                           ("Conditions de reconstitution actuelles", output["reconstruction_summary"])):
        print(f"\n{title}: {summary['solvable']}/{summary['cases']} résolvables")
        print("Coûts minimaux (actions d'investigation):", summary.get("minimum_cost_counts", {}))
        for method, share in summary.get("unavoidable_method_case_share", {}).items():
            print(f"  {method}: incontournable dans {share:.1%} des affaires")
        print("Dernière action des parcours optimaux:")
        for method, share in summary.get("mean_closing_method_share", {}).items():
            print(f"  {method}: {share:.1%}")
        print("Recettes, sans compter les permutations comme de la diversité:")
        for recipe in summary.get("method_recipe_distribution", []):
            print(f"  {recipe['counts']}: {recipe['case_weighted_share']:.1%}")


if __name__ == "__main__":
    main()
