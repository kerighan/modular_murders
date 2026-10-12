"""Human-facing clarity must not become a shortcut or expose private facts."""
import json

import pytest

from game import FAR_TRAITS, Game, SERVICE_STAFF
from genotype import LinkToVictim


def fresh(seed=1, players=("Ada",)):
    g = Game(seed, players=players, challenge=lambda *_: 1.0)
    g.equip(0, ["taxi", "crowbar"])
    g.start()
    return g


@pytest.mark.parametrize("seed", range(30))
def test_partial_rumours_never_name_a_private_pressure_group(seed):
    g = fresh(seed)
    p = g.player
    for sid, knowledge in g.story.knowledge.items():
        if knowledge != "pressure":
            continue
        before = set(p.names)
        text, _ = g.answer_grudge(p, sid)
        assert p.names == before
        assert all(g.name(target) not in text for target in range(g.n))
        assert "horaires" not in text and "ce problème" not in text
        leads = g.story.leads_view(p)
        assert all(not lead["destinations"] for lead in leads)
        assert not p.facts and not p.cleared


def test_reflection_is_private_uncertain_and_separate_from_npc_reply():
    g = fresh(players=("Ada", "Bob"))
    p, other = g.players
    sid = next(s for s in range(g.n) if g.story.knowledge[s] == "pressure")
    p.place = g.where[sid] = "bar"
    g.play(("interrogate", sid))
    before = (set(p.facts), set(p.cleared), set(p.names))
    events = g.play(("ask", "grudge"))
    cue = g.view(p)["conversation"]
    assert cue["thought"]["person"]["detective"]
    assert cue["thought"]["person"]["name"] == p.name
    assert cue["thought"]["text"] not in cue["text"]
    assert (p.facts, p.cleared, p.names) == before
    assert p.journal[-1]["kind"] == "réflexion"
    assert "pensée" in events[-1]
    assert not other.journal and not g.view(other)["conversation"]
    g.play(("stop",))
    # Another informed person on the same topic should not repeat the thought.
    second = next(s for s in range(g.n) if s != sid and g.case[s][LinkToVictim] != LinkToVictim.UNKNOWN)
    g.story.knowledge[second] = "pressure"
    p.ap = 3
    g.where[second] = p.place
    g.play(("interrogate", second))
    g.play(("ask", "grudge"))
    assert "thought" not in g.view(p)["conversation"]


def test_partial_confrontation_has_no_secret_culprit_coaching():
    g = fresh()
    p = g.player
    innocent = g.story.rival
    assert g.story._personal_document_reply(0) == g.story._personal_document_reply(innocent)
    text = g.story.confront(p, 0, "trace")[0]
    assert not any(word in text.lower() for word in ("recouper", "vérifiez", "croiser", "il faut"))
    assert not p.story_resolved


def test_blood_already_known_does_not_queue_a_second_analysis():
    g = fresh(5)
    p = g.player
    blood = [e for e in g.evidence if e.blood]
    assert blood
    p.facts.add(blood[0].fact)
    for e in blood:
        result = g.examine(p, e)
        assert "ne m'apprendra rien de plus" in result[0]
    assert not g.lab


def test_new_morgue_blood_is_analysed_on_site_without_return_trip():
    g = fresh(5)
    p = g.player
    p.place = "hospital"
    blood = next(e for e in g.evidence if e.blood)
    result = g.examine(p, blood)
    assert "sur place" in result[0]
    assert blood.fact in p.facts and not g.lab
    assert not any("prochain tour" in line for line in result)


def test_named_alibi_does_not_invent_additional_people():
    g = fresh()
    sid = next(s for s in range(g.n) if g.recall[s])
    text, _ = g.answer_alibi(g.player, sid)
    assert "Il y avait peut-être d'autres gens." in text


@pytest.mark.parametrize("seed", range(12))
def test_each_local_action_is_anchored_to_a_person_object_or_door(seed):
    g = fresh(seed)
    p = g.player
    for sid in range(g.n):
        g.reveal(p, sid, FAR_TRAITS, name=True)
        g.answer_alibi(p, sid)
    for place in g.map:
        p.place, p.ap = place, 3
        v = g.view(p)
        assert len(v["notebook"]) == g.n
        staff_ids = {s["id"] for s in v["staff"]}
        assert not staff_ids & {s["id"] for s in v["present"]}
        anchored = {tuple(key) for group in v["staff"] + v["fixtures"] + v["doors"] for key, _ in group["actions"]}
        for key, _ in v["options"]:
            if key[0] in {"move", "walk", "end"}:
                continue
            if key[0] == "listen":
                assert v["arrival_scene"]["key"] == list(key)
                assert set(v["arrival_scene"]["people"]) <= {s["id"] for s in v["present"]}
                continue
            if len(key) > 1 and key[0] in {"interrogate", "observe", "confront", "talk_about"} and key[1] in {s["id"] for s in v["present"]}:
                continue
            assert tuple(key) in anchored, (place, key)
        json.dumps(v)


def test_palace_usher_is_not_a_suspect_and_voices_only_real_memories():
    g = fresh()
    p = g.player
    p.place = "cabaret"
    v = g.view(p)
    assert v["staff"][0]["id"] == "staff:cabaret"
    assert v["staff"][0]["name"] == "L'ouvreuse"
    assert not v["staff"][0]["actions"]
    sid = next(s for s in range(1, g.n) if g.night[s] == "cabaret")
    g.reveal(p, sid, [], name=True)
    p.alibis[sid] = False
    g.play(("verify", sid))
    cue = g.view(p)["conversation"]
    assert cue["person"]["id"] == "staff:cabaret" and not cue["active"]
    assert "ne me souviens pas" in cue["text"] or "Je m'en souviens bien" in cue["text"]


def test_leads_do_not_guess_a_hidden_motive_from_a_key_register():
    g = fresh()
    p = g.player
    p.story_found.add("access")
    for sid in g.story.access:
        g.reveal(p, sid, [], name=True)
    motive = next(lead for lead in g.story.leads_view(p) if lead["id"] == "motive")
    assert "Pourquoi cette disparition" in motive["title"]
    assert "avocat" not in motive["reason"] and "dette" not in motive["reason"]
