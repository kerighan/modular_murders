import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from scenario_crime import CrimeBuilder, Walk
from scenario_kernel import KernelBuilder, SUPPORTED_PREMISES
from scenario_means import Method
from scenario_observations import (DiscoveryState, Operation, UnavailableAction,
                                   project, walkthrough, with_witnesses)
from scenario_situations import SituationKind
from scenario_witnesses import (Appearance, Aspect, Attention, Coat, EventKind,
    Height, InvalidWitness, Perception, Sense, WitnessBuilder, matching,
    reply_to, sample_appearances, scene_events, statements, validate)


ROOT = Path(__file__).resolve().parents[1]


def crime(seed=42, **choices):
    kernel = KernelBuilder(seed).sample()
    return CrimeBuilder(f"physical-v4:{seed}").build(kernel, **choices)


def find_layer(kind=EventKind.ASSAULT, aspect=None):
    choices = {"situation": SituationKind.AGREED_MEETING} if kind is EventKind.MEETING else {}
    base = crime(method=Method.BLUNT, **choices)
    for seed in range(100):
        layer = WitnessBuilder(seed).build(base)
        by_id = {e.id: e for e in layer.events}
        for p in layer.perceptions:
            if by_id[p.event].kind is kind and (aspect is None or p.aspect is aspect):
                return layer, p
    raise AssertionError("Fixture missing")


@pytest.mark.parametrize("seed", range(100))
def test_corpus_reproducible_truth_preserved_and_whole_interviews_ambiguous(seed):
    base = crime(seed)
    original = base.as_dict()
    layer = WitnessBuilder(seed).build(base)
    assert layer == WitnessBuilder(seed).build(base)
    assert base.as_dict() == original
    assert layer.events == scene_events(base)
    plan = with_witnesses(project(base), layer)
    output = walkthrough(plan)
    assert output["audit"]["artifacts_acquired"] == len(plan.artifacts)
    for action in plan.actions:
        support = plan.population
        for key in action.reveals:
            support &= next(a.candidates for a in plan.artifacts if a.id == key)
        assert len(support) >= 2 and base.kernel.roles.author in support
    for w in layer.witnesses:
        for row in statements(layer, w.id):
            assert len(row.candidates) >= 2 and base.kernel.roles.author in row.candidates
            assert not any(p.name in row.text for p in base.kernel.world.people
                           if p.id != base.kernel.roles.victim)


@pytest.mark.parametrize("premise", SUPPORTED_PREMISES)
@pytest.mark.parametrize("situation", list(SituationKind))
def test_all_roots_and_situations_have_legal_witness_layer(premise, situation):
    kernel = KernelBuilder(42).build(premise)
    base = CrimeBuilder("physical-v4:42").build(kernel, situation=situation)
    layer = WitnessBuilder(42).build(base)
    plan = with_witnesses(project(base), layer)
    assert walkthrough(plan)["audit"]["artifacts_acquired"] == len(plan.artifacts)
    assert plan.projection_version == 2


def test_staff_serves_without_automatically_seeing_addition_or_knowing_killer():
    base = crime(method=Method.POISONED)
    layer = WitnessBuilder(42).build(base)
    server = next(w for w in layer.witnesses if w.role == "keeper")
    rows = statements(layer, server.id)
    assert len(rows) == 1 and "servi un verre" in rows[0].text
    assert rows[0].candidates == layer.population
    assert not any(word in rows[0].text for word in ("ajouté", "poison", "tueur", "table ensuite"))
    assert next(p for p in layer.perceptions if p.witness == server.id).actor is None
    assert "Je ne sais pas" in reply_to(layer, server.id, EventKind.DRINK_ADDITION)[0]
    assert "servi un verre" in reply_to(layer, server.id, EventKind.SERVICE)[0]


def test_presence_is_not_attention_and_gaps_or_remote_views_are_rejected():
    layer, perception = find_layer()
    event = next(e for e in layer.events if e.id == perception.event)
    attention = next(a for a in layer.attention if a.id == perception.attention)
    for altered in (replace(attention, start=event.minute + 1, end=event.minute + 1),
                    replace(attention, place="police"), replace(attention, occluded=True),
                    replace(attention, visible=(event.target,)), replace(attention, recognizable=())):
        with pytest.raises(InvalidWitness):
            replace(layer, attention=tuple(altered if a.id == attention.id else a for a in layer.attention))
    with pytest.raises(InvalidWitness):
        replace(layer, attention=tuple(a for a in layer.attention if a.id != perception.attention))


def test_presence_with_no_attention_produces_no_memory_or_accusation():
    layer, p = find_layer()
    unobservant = replace(layer,
        perceptions=tuple(view for view in layer.perceptions if view.witness != p.witness),
        attention=tuple(view for view in layer.attention if view.witness != p.witness))
    assert any(span.witness == p.witness for span in unobservant.presences)
    assert statements(unobservant, p.witness) == ()
    assert reply_to(unobservant, p.witness, EventKind.ASSAULT) == ("Je ne sais pas. Je ne peux rien vous dire là-dessus.",)


def test_real_commutes_cannot_be_teleported_or_overlap():
    layer, perception = find_layer()
    presence = next(p for p in layer.presences if p.witness == perception.witness and p.arrival)
    impossible = replace(presence, arrival=Walk(presence.witness,
        (presence.arrival.nodes[0], presence.place), (presence.start - 1, presence.start)))
    with pytest.raises(ValueError):
        replace(layer, presences=tuple(impossible if p.id == presence.id else p for p in layer.presences))
    with pytest.raises(InvalidWitness, match="overlap"):
        replace(layer, presences=layer.presences + (replace(presence, id="duplicate_interval"),))


def test_wrong_event_actor_kind_and_future_memory_are_rejected():
    layer, perception = find_layer()
    event = next(e for e in layer.events if e.id == perception.event)
    with pytest.raises(InvalidWitness, match="physical truth"):
        replace(layer, events=tuple(replace(e, minute=e.minute + 1) if e.id == event.id else e for e in layer.events))
    for changes in ({"actor": layer.crime.kernel.roles.victim}, {"event": "invented"},
                    {"aspect": "coat"}):
        with pytest.raises(InvalidWitness):
            replace(layer, perceptions=tuple(replace(p, **changes) if p.id == perception.id else p for p in layer.perceptions))


def test_neutral_descriptions_never_rewrite_an_innocent_as_an_alibi_decoy():
    ids = ("a", "b", "c", "d")
    first = sample_appearances(ids, 7)
    assert first == sample_appearances(reversed(ids), 7)
    # Adding other people doesn't alter the signature of existing earlier IDs.
    assert first == sample_appearances(ids + ("z",), 7)[:4]
    assert first != sample_appearances(ids, 8)


def test_unique_description_is_refused_not_padded_with_an_unmatching_innocent():
    layer, perception = find_layer(aspect=Aspect.COAT)
    actor = perception.actor
    roster = tuple(replace(a, coat=Coat.DARK if a.person == actor else Coat.LIGHT)
                   for a in layer.appearances)
    with pytest.raises(InvalidWitness, match="at least two"):
        replace(layer, appearances=roster)


def test_whole_witness_cannot_combine_two_descriptions_into_a_singleton():
    layer, p = find_layer()
    actor = p.actor
    others = sorted(layer.population - {actor})
    roster = tuple(Appearance(a.person,
        Coat.DARK if a.person in (actor, others[0]) else Coat.LIGHT,
        Height.TALL if a.person in (actor, others[1]) else Height.SHORT) for a in layer.appearances)
    first = replace(p, aspect=Aspect.COAT)
    second = replace(p, id="second_memory", aspect=Aspect.HEIGHT)
    with pytest.raises(InvalidWitness, match="whole witness"):
        replace(layer, appearances=roster,
                perceptions=tuple(first if view.id == p.id else view for view in layer.perceptions) + (second,))


def test_context_descriptions_do_not_accuse_a_person_for_being_nearby():
    layer, p = find_layer(kind=EventKind.MEETING)
    statement, = statements(layer, p.witness)
    assert statement.relevance == "context" and statement.candidates == layer.population
    assert not any(word in statement.text for word in ("tueur", "meurtrier", "jalous", "horaire à vérifier"))


def test_shared_route_requires_actual_following_and_does_not_imply_known_employment():
    from scenario_crime import Encounter
    base = crime(encounter=Encounter.AT_EXIT)
    layer = WitnessBuilder(42).build(base)
    assert EventKind.SHARED_ROUTE not in {e.kind for e in layer.events}
    assert EventKind.NEARBY in {e.kind for e in layer.events}
    for w in layer.witnesses:
        assert all("travail" not in row.text for row in statements(layer, w.id))


def test_only_witness_homes_can_extend_map_not_a_shortcut_between_existing_streets():
    from scenario_crime import Edge, StreetMap
    layer, _ = find_layer()
    original = layer.crime.streets
    streets = [n.id for n in original.nodes if n.kind.value == "street"]
    a, b = next((a, b) for a in streets for b in streets if a != b and original.duration(a, b) is None)
    changed = StreetMap(layer.streets.nodes, layer.streets.edges + (Edge(a, b, 1),))
    with pytest.raises(InvalidWitness, match="shortcut"):
        replace(layer, streets=changed)


def test_assailant_support_is_a_real_shared_appearance_predicate():
    layer, p = find_layer(aspect=Aspect.COAT)
    row, = statements(layer, p.witness)
    assert row.relevance == "assailant_description" and row.candidates == matching(layer, p)
    by_id = {a.person: a for a in layer.appearances}
    assert all(by_id[person].coat is by_id[p.actor].coat for person in row.candidates)


def test_missing_agreed_visit_is_known_by_host_not_random_strangers():
    from scenario_victim import VictimGoal
    base = crime(goal=VictimGoal.MEET_PERSON)
    layer = WitnessBuilder(42).build(base)
    missed = base.missed_appointments[0]
    host = next(w for w in layer.witnesses if w.id == missed.observer)
    row, = statements(layer, host.id)
    assert "devait venir chez moi" in row.text and "attendu pour rien" in row.text
    assert row.candidates == layer.population
    assert next(p for p in layer.perceptions if p.witness == host.id).actor is None


def test_interview_requires_identified_scene_and_witness_present_and_is_one_tap():
    layer, p = find_layer()
    plan = with_witnesses(project(layer.crime), layer)
    action = next(a for a in plan.actions if a.actor == p.witness)
    at = 1440 + 8 * 60
    with pytest.raises(UnavailableAction):
        plan.perform(DiscoveryState(), action.id, place=action.place, at=at)
    state, _ = plan.perform(DiscoveryState(), "inspect_scene", place=layer.crime.scene, at=at)
    with pytest.raises(UnavailableAction):
        plan.perform(state, action.id, place=action.place, at=1440 + 23 * 60)
    new_state, rows = plan.perform(state, action.id, place=action.place, at=at)
    assert len(rows) == len(statements(layer, p.witness))
    assert action.operation is Operation.INTERVIEW
    assert all(set(row) == {"id", "kind", "text"} for row in rows)
    with pytest.raises(UnavailableAction):
        plan.perform(new_state, action.id, place=action.place, at=at)


def test_unseen_part_of_route_cannot_create_a_memory_and_no_cross_crime_attachment():
    layer, p = find_layer()
    departed = next(e for e in layer.events if e.kind is EventKind.DEPARTURE)
    assert departed.place in layer.crime.execution.escape.nodes
    assert departed.minute in layer.crime.execution.escape.times
    with pytest.raises(ValueError, match="exact base"):
        with_witnesses(project(crime(8)), layer)


def test_public_witness_payload_has_no_culprit_profile_roster_or_private_provenance():
    layer, _ = find_layer()
    payload = with_witnesses(project(layer.crime), layer).public_catalogue()
    serialized = json.dumps(payload)
    assert "candidates" not in serialized and "sources" not in serialized
    assert "appearances" not in serialized and "attention:" not in serialized
    assert layer.crime.execution.tool not in serialized
    for row in payload["artifacts"]:
        assert set(row) == {"id", "kind", "text"}


def test_appearance_and_event_layers_not_silently_added_to_stage6():
    base = project(crime())
    assert base.projection_version == 1
    assert not any(a.operation is Operation.INTERVIEW for a in base.actions)


def test_cli_stage7_and_legacy_physics_reproducible():
    command = [sys.executable, "scenario_sampler.py", "--step", "7", "--seed", "42", "--method", "poisoned", "--walkthrough", "--json"]
    output = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout == output
    row, = json.loads(output)
    assert any(s["action"]["operation"] == "interview" for s in row["steps"])
    assert "candidates" not in output and "sources" not in output
    assert row["audit"]["artifacts_acquired"] == row["audit"]["artifacts_total"]


def test_two_independent_ambiguous_eyewitnesses_can_cross_without_one_magic_clue():
    base = crime(235)
    for index in range(60):
        layer = WitnessBuilder(f"235:{index}").build(base, focus_assault=2)
        plan = with_witnesses(project(base), layer)
        if plan.graph().remaining(a.id for a in plan.artifacts if a.kind == "testimony") == {base.kernel.roles.author}:
            break
    else:
        pytest.fail("No independent ambiguous descriptions converged")
    interviews = [a for a in plan.actions if a.operation is Operation.INTERVIEW]
    supports = []
    for action in interviews:
        support = plan.population
        for key in action.reveals:
            support &= next(a.candidates for a in plan.artifacts if a.id == key)
        assert len(support) >= 2
        supports.append(support)
    assert plan.population.intersection(*supports) == {base.kernel.roles.author}


def test_witness_audit_optional_and_base_distribution_unchanged():
    from scenario_diversity import audit
    base, extended = audit(20), audit(20, witnesses=True)
    assert base == {key: value for key, value in extended.items() if key != "witness_projection"}
    assert extended["witness_projection"]["artifacts_acquired"] == extended["witness_projection"]["artifacts_total"]


@pytest.mark.parametrize("flags", [["--public-scene"], ["--public-inventory"], ["--requirements"]])
def test_stage7_rejects_other_private_or_public_preview_modes(flags):
    result = subprocess.run([sys.executable, "scenario_sampler.py", "--step", "7", *flags],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0 and "error:" in result.stderr
