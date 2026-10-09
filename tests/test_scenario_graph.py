"""Generation contracts, not just a few fortunate hand-picked stories."""
from collections import defaultdict
from itertools import combinations

import networkx as nx
import pytest

from game import Game
from genotype import LinkToVictim
from scenario_graph import Observation, ScenarioGraph


def test_singleton_evidence_is_rejected_and_supports_are_not_exactly_two():
    with pytest.raises(ValueError, match="invariant"):
        ScenarioGraph(range(4), [Observation("bad", "object", frozenset({0}))])
    graph = ScenarioGraph(range(4), [Observation("shared", "object", frozenset({0, 1, 2}))])
    assert graph.remaining(["shared"]) == {0, 1, 2}


@pytest.mark.parametrize("batch", range(50))
def test_thousand_scenarios_have_no_single_evidence_shortcut(batch):
    for seed in range(batch * 20, batch * 20 + 20):
        g = Game(seed)
        story = g.story
        for evidence in story.graph.observations.values():
            assert len(evidence.candidates) >= 2
            assert 0 in evidence.candidates
        assert story.graph.remaining(story.graph.observations) == {0}
        assert all(len(story.graph.remaining(pair)) >= 2 for pair in combinations(story.graph.observations, 2))
        assert story.graph.minimum_depth() == 3
        # This includes the combined information from a weapon, phone, CCTV
        # recording or a single witness, not just each individual trait.
        artifacts = defaultdict(set)
        for evidence in g.evidence:
            assert len(g.case.commonalities[evidence.fact]) >= 2
            artifacts[(evidence.place, evidence.who, evidence.label, evidence.portable)].add(evidence.fact)
        for facts in artifacts.values():
            assert len(g.case.remaining(facts)) >= 2
        assert g.case.remaining(g.case.facts) == {0}
        assert not story.link_deniers and g.lie is None
        assert all(source["place"] in g.map for source in story.sources.values())
        assert sum(row.count("crime_scene") for row in g.grid) == 1
        assert g.view(g.player)["crime_site"]["outdoors"]
        graph = nx.Graph((place, other) for place, (_, neighbors) in g.map.items() for other in neighbors)
        assert nx.is_connected(graph)


@pytest.mark.parametrize("count", [3, 4, 6, 12])
@pytest.mark.parametrize("seed", range(12))
def test_smaller_populations_keep_minimum_two_and_converge(count, seed):
    g = Game(seed, n_suspects=count)
    assert g.story.graph.minimum_depth() == (2 if count == 3 else 3)
    assert all(len(o.candidates) >= 2 for o in g.story.graph.observations.values())
    assert g.story.graph.remaining(g.story.graph.observations) == {0}


def test_strangers_cannot_supply_victim_gossip_in_either_question_order():
    strangers = 0
    for seed in range(50):
        g = Game(seed)
        p = g.player
        for sid in range(g.n):
            if g.case[sid][LinkToVictim] != LinkToVictim.UNKNOWN:
                continue
            strangers += 1
            before = set(p.names)
            text, notes = g.answer_grudge(p, sid)
            assert "ne connaissais pas" in text and not notes
            assert p.names == before and sid not in p.story_rumours
            g.answer_link(p, sid)
            assert g.answer_grudge(p, sid) == (text, notes)
            target = next(t for t in range(g.n) if t != sid)
            g.story.link_contacts[sid].add(target)
            g.story.talk_about(p, sid, target)
            assert sid not in p.link_witnesses.get(target, set())
    assert strangers > 30


def test_gossip_is_sparse_and_work_leads_have_real_multiple_colleagues():
    informed, speakers, work = 0, 0, 0
    for seed in range(100):
        g = Game(seed)
        for sid, knowledge in g.story.knowledge.items():
            if g.case[sid][LinkToVictim] != LinkToVictim.UNKNOWN:
                speakers += 1
                informed += knowledge is not None
        if g.story.work_conflict:
            work += 1
            assert len(g.story.work_conflict) >= 2
            assert all(g.case[s][LinkToVictim] == LinkToVictim.COLLEAGUE for s in g.story.work_conflict)
            assert g.story.workplace in g.map
    assert .20 < informed / speakers < .60
    assert work > 10


def test_paths_are_private_and_never_discover_an_unseen_fact():
    g = Game(42, players=("Ada", "Bob"))
    a, b = g.players
    assert g.story.leads_view(a) == g.story.leads_view(b) == []
    a.story_found.add("loss")
    paths = g.story.leads_view(a)
    assert [path["id"] for path in paths] == ["object"]
    assert not paths[0]["complete"]
    assert paths[0]["destinations"][0]["place"] == g.story.spec["relay"]
    assert g.story.leads_view(b) == []
    assert a.story_found == {"loss"} and not a.story_resolved


def test_object_variants_have_no_forced_intermediary_or_unique_cache_owner():
    seen = set()
    for seed in range(100):
        g = Game(seed)
        story = g.story
        seen.add(story.object_fate)
        assert not hasattr(story, "courier")
        assert not {"handoff", "relay"} & story.sources.keys()
        if story.object_fate == "none":
            assert story.spec["object"] is None
            assert "loss" not in story.sources and "cache" not in story.sources
            assert story.access_key == "meeting"
        elif story.object_fate == "missing":
            assert story.cache_place is None and "cache" not in story.sources
        else:
            doc = story.sources["cache"]
            assert doc["place"] in {"alley", "bar", "cabaret", "den"}
            assert not doc["people"] and not doc.get("target")
            assert story.graph.remaining(["cache"]) == set(range(g.n))
    assert seen == {"none", "missing", "hidden"}


@pytest.mark.parametrize("seed", range(40))
def test_narrative_is_resolvable_without_recovering_or_tracing_a_handoff(seed):
    g = Game(seed, challenge=lambda *_: 1.0)
    g.equip(0, ["taxi", "crowbar"])
    g.start()
    story, p = g.story, g.player
    for key in (story.access_key, "trace", "clock"):
        p.place, p.ap = story.sources[key]["place"], 3
        p.authorized = True
        g.play(("search",))
    p.place, p.ap = "cctv", 3
    g.play(("check_timeline", 0))
    p.place, p.ap = "house_0", 3
    g.where[0] = "house_0"
    g.play(("confront", 0, "trace"))
    assert p.story_resolved
    assert "cache" not in p.story_found
    assert not {"handoff", "relay"} & p.story_found
    assert "confié" not in story.reconstruction(p)


def test_cache_is_anonymous_and_does_not_reveal_the_placer_or_resolve_the_case():
    g = Game(42, players=("Ada", "Bob"))
    g.equip(0, ["taxi", "crowbar"])
    g.start()
    a, b = g.players
    before_b = g.view(b)
    a.place = g.story.cache_place
    g.play(("search",))
    assert "cache" in a.story_found
    note = next(n for n in a.journal if n["title"] == "Un objet caché, à identifier")
    assert note["people"] == [] and note["leads"] == ["victim_house"]
    assert not a.story_resolved and not a.cleared
    assert g.view(a)["story"]["object_status"] == "unidentified"
    assert "de la victime" not in g.view(a)["story"]["object"]
    path = g.story.leads_view(a)[0]
    assert "coffre" not in path["reason"] + path["objective"]
    assert [d["place"] for d in path["destinations"]] == ["victim_house"]
    a.place, a.ap = "victim_house", 3
    g.play(("search",))
    assert g.view(a)["story"]["object_status"] == "found"
    assert g.view(b)["story"] == before_b["story"]


def test_missing_and_hidden_fates_are_not_disclosed_before_discovery():
    for seed in (7, 42):
        g = Game(seed)
        p = g.player
        p.story_found.add("loss")
        public = g.story.view(p)
        assert public["object_status"] == "missing"
        assert "cache_place" not in public and "object_fate" not in public
        assert not any(d["place"] == g.story.cache_place for lead in g.story.leads_view(p)
                       for d in lead["destinations"])


def test_false_accusation_does_not_fabricate_an_alibi():
    g = Game(42)
    g.equip(0, ["taxi"])
    g.start()
    p = g.player
    sid = 3
    g.reveal(p, sid, [], name=True)
    p.place = "police"
    assert sid not in p.alibis and sid not in p.timeline_verified
    events = g.play(("accuse", sid))
    assert "alibi" not in " ".join(events)
    assert "Accusation erronée" in events[0]
