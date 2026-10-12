from itertools import permutations

import pytest

from investigation_solver import InvestigationAction as Action, InvestigationSolver
from scenario_graph import Observation, ScenarioGraph


def graph():
    return ScenarioGraph(range(4), [
        Observation("access", "opportunity", {0, 1, 2}),
        Observation("motive", "motive", {0, 1, 3}),
        Observation("camera", "chronology", {0, 2, 3}),
        Observation("clock", "chronology", range(4)),
    ])


def actions():
    return [Action("keys", "search", ("access",)),
            Action("papers", "search", ("motive",)),
            Action("scene", "search", ("clock",)),
            Action("video", "analyse", ("camera",), ("clock", "motive"))]


def test_clock_has_no_information_gain_but_cannot_be_pruned_as_a_state():
    result = InvestigationSolver(graph(), actions()).audit()
    assert result["minimum_cost"] == 4
    assert result["optimal_plan_count"] == 8
    assert result["minimal_proofs"] == [["access", "camera", "motive"]]
    assert result["kind_metrics"]["unavoidable"] == ["analyse", "search"]
    assert result["optimal_action_inclusion"]["scene"] == 1
    assert result["kind_metrics"]["closing_share"] == {"analyse": .75, "search": .25}
    assert sum(result["kind_metrics"]["candidate_reduction_bits"].values()) == pytest.approx(2)


def test_alternative_source_is_not_collapsed_and_necessity_differs_from_optimality():
    alternative = Action("witness", "interrogate", ("camera",), cost=5)
    result = InvestigationSolver(graph(), actions() + [alternative]).audit()
    metrics = result["kind_metrics"]
    assert metrics["optimal_inclusion"]["analyse"] == 1
    assert "analyse" not in metrics["unavoidable"]
    assert metrics["minimum_cost_without"]["analyse"] == 7
    assert metrics["optimal_inclusion"]["interrogate"] == 0


def test_bundled_source_changes_minimum_cost_and_hides_a_shortcut():
    bundled = Action("single_paper", "search", ("access", "motive", "camera"))
    result = InvestigationSolver(graph(), actions() + [bundled]).audit()
    assert result["minimum_cost"] == 1
    assert result["optimal_plan_count"] == 1
    assert result["optimal_action_inclusion"] == {"single_paper": 1}


def test_source_centrality_is_not_a_measure_of_being_mandatory():
    g = ScenarioGraph(range(3), [Observation("a", "x", {0, 1}), Observation("b", "y", {0, 2})])
    result = InvestigationSolver(g, [Action("a", "search", ("a",)), Action("b", "talk", ("b",))]).audit()
    assert result["dependency_action_betweenness"] == {"a": 0, "b": 0}
    assert result["kind_metrics"]["unavoidable"] == ["search", "talk"]


def test_parallel_sources_count_paths_not_only_distinct_states():
    result = InvestigationSolver(graph(), actions() + [Action("papers2", "search", ("motive",))]).audit()
    assert result["optimal_plan_count"] == 16
    assert result["optimal_action_inclusion"]["papers"] == .5
    assert result["optimal_action_inclusion"]["papers2"] == .5
    assert len(result["optimal_method_patterns"]) == 1


def test_inaccessible_logical_proof_is_not_a_playable_solution():
    result = InvestigationSolver(graph(), actions()[:-1]).audit()
    assert not result["solvable"] and result["minimum_cost"] is None
    assert result["minimal_proofs"] == [["access", "camera", "motive"]]


def test_initial_knowledge_and_reconstruction_requirements():
    result = InvestigationSolver(graph(), actions(), initial=("access", "camera", "motive")).audit()
    assert result["minimum_cost"] == 0 and result["optimal_plan_count"] == 1
    assert not result["kind_metrics"]["unavoidable"]
    assert result["kind_metrics"]["step_share"] == {}
    result = InvestigationSolver(graph(), actions(), initial=("access", "camera", "motive"), required=("clock",)).audit()
    assert result["minimum_cost"] == 1
    assert result["optimal_action_inclusion"] == {"scene": 1}


@pytest.mark.parametrize("cost", [0, -1, 1.5, True])
def test_bad_costs_rejected(cost):
    with pytest.raises(ValueError, match="positive integers"):
        Action("x", "search", ("access",), cost=cost)


def test_bad_ids_and_references_fail_instead_of_being_ignored():
    with pytest.raises(ValueError, match="Duplicate action"):
        InvestigationSolver(graph(), actions() + actions())
    with pytest.raises(ValueError, match="Unknown observation"):
        InvestigationSolver(graph(), [Action("x", "search", ("missing",))])
    with pytest.raises(ValueError, match="Unknown observation"):
        InvestigationSolver(graph(), actions(), required=("missing",))
    with pytest.raises(ValueError, match="limit exceeded"):
        InvestigationSolver(graph(), actions(), max_states=1).audit()


def test_dp_matches_brute_force_legal_orderings():
    g, options = graph(), actions()
    winning = []
    for plan in permutations(options):
        known = set()
        for action in plan:
            if not set(action.requires) <= known:
                break
            known.update(action.reveals)
        else:
            if len(g.remaining(known)) == 1:
                winning.append(plan)
    result = InvestigationSolver(g, options).audit()
    assert result["optimal_plan_count"] == len(winning)
    for kind in ("search", "analyse"):
        share = sum(plan[-1].kind == kind for plan in winning) / len(winning)
        assert result["kind_metrics"]["closing_share"][kind] == pytest.approx(share)


@pytest.mark.parametrize("seed", [0, 4, 7, 42, 93])
def test_real_story_projection_bundles_sources_and_includes_verified_alibi(seed):
    from game import Game
    from scenario_audit import audit_story, narrative_projection
    g = Game(seed)
    before = g.view(g.player)
    projected, source_actions = narrative_projection(g.story)
    assert len(projected.observations["verified_alibi"].candidates) == g.n - 1
    assert 0 in projected.observations["verified_alibi"].candidates
    camera = next(action for action in source_actions if action.id == "camera")
    assert set(camera.requires) == {"clock", "trace"}
    report = audit_story(g.story)
    assert report["deduction"]["solvable"] and report["reconstruction_requirements"]["solvable"]
    assert "analyse_video" in report["deduction"]["method_metrics"]["unavoidable"]
    assert len(report["deduction"]["minimal_proofs"]) >= 1
    assert g.view(g.player) == before


def test_verified_alibi_can_replace_opportunity_in_four_person_core():
    from game import Game
    from scenario_audit import audit_story
    report = audit_story(Game(42, n_suspects=4).story)
    assert len(report["deduction"]["minimal_proofs"]) == 2
    assert any("verified_alibi" in proof for proof in report["deduction"]["minimal_proofs"])


def test_corpus_weights_each_case_not_each_path_and_empty_corpus():
    from game import Game
    from scenario_audit import audit_story, summarize
    a, b = audit_story(Game(42).story), audit_story(Game(7).story)
    summary = summarize([a, b])
    assert summary["solvable"] == 2
    assert sum(recipe["case_weighted_share"] for recipe in summary["method_recipe_distribution"]) == pytest.approx(1)
    assert summary["unavoidable_method_case_share"]["analyse_video"] == 1
    assert summarize([])["solvable"] == 0
