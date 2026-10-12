from dataclasses import replace

import pytest

from scenario_crime import NodeKind, ToolFate
from scenario_evidence import crime_window
from scenario_kernel import romantic_triangles
from scenario_life import Link, Message
from scenario_evening import validate_evenings, validate_registrations, remembered_times, spoken_time
from scenario_observations import DiscoveryState
from scenario_play import thread_profile, PlaySession, build_case, sample_playable, context_is_refutable
from scenario_playtest import play


@pytest.fixture(scope="module")
def cases():
    return tuple(build_case(seed) for seed in range(100))


@pytest.mark.parametrize("seed", range(100))
def test_social_and_physical_facts_are_coherent(cases, seed):
    case = cases[seed]
    case.life.validate()
    case.evidence.validate()
    assert case.life.crime is case.crime
    assert case.witnesses.crime is case.crime
    assert case.evidence.crime is case.crime
    for p in case.life.people.values():
        if p.id == case.crime.kernel.roles.victim:
            continue
        answer = case.life.answer(p.id)
        if not case.life.knows(p.id, case.crime.kernel.roles.victim):
            assert "Je ne connaissais pas" in answer
            assert case.life.answer(p.id, "messages") == "Non, aucun échange avec cette personne." or "Nous n'avons jamais échangé directement" in case.life.answer(p.id, "messages")
    for bond in case.life.bonds:
        if bond.kind is Link.NEIGHBORS:
            a, b = (case.life.people[p] for p in bond.people)
            assert case.crime.streets.neighbors(a.home)[0][0] == case.crime.streets.neighbors(b.home)[0][0]


def test_filling_covers_no_link_family_friend_neighbors_and_innocent_triangles(cases):
    assert {b.kind for case in cases for b in case.life.bonds} == set(Link)
    assert any(not case.life.knows(p, case.crime.kernel.roles.victim)
               for case in cases for p in case.plan.population)
    assert any(case.crime.kernel.roles.author not in triangle for case in cases
               for triangle in romantic_triangles(case.crime.kernel.world))
    assert any(sum(f.kind == "heard_late_music" for f in case.life.ordinary) == 2 for case in cases)


def test_friends_and_family_sometimes_meet_the_partner_without_omniscience(cases):
    introduced, not_introduced = [], []
    for case in cases:
        life, victim = case.life, case.crime.kernel.roles.victim
        for couple in (b for b in life.bonds if b.kind is Link.PARTNERS and victim in b.people):
            partner = next(p for p in couple.people if p != victim)
            for close in (b for b in life.bonds if b.kind in (Link.FRIENDS, Link.SIBLINGS) and victim in b.people):
                contact = next(p for p in close.people if p != victim)
                fact = next((f for f in life.ordinary if f.kind == "social_introduction"
                             and set(f.people) == {contact, partner}), None)
                if fact:
                    introduced.append(fact)
                    assert life.knows(contact, partner) and life.knows(partner, contact)
                    assert "présentés" in life.answer_about(contact, partner)
                    assert "présentés" in life.answer_about(partner, contact)
                    assert "étaient ensemble" in life.answer_about(contact, partner)
                    with pytest.raises(ValueError, match="Introduction"):
                        replace(life, ordinary=tuple(replace(f, disclosed_bond="invented") if f.id == fact.id else f for f in life.ordinary))
                else:
                    not_introduced.append((contact, partner))
    assert introduced and not_introduced


@pytest.mark.parametrize("seed", range(100))
def test_every_suspect_can_recount_real_evening_facts_without_certifying_an_alibi(cases, seed):
    case = cases[seed]
    validate_evenings(case.crime, case.evidence, case.evenings)
    for pid in sorted(case.plan.population):
        s = PlaySession(case)
        s.go(case.life.people[pid].home)
        s.do("meet:" + pid)
        assert "interview:" + pid in {r["id"] for r in s.options()}
        text = s.do("interview:" + pid)
        assert "Je n'ai rien" not in text and "chez moi" in text
        assert s.remaining() == case.plan.population
        assert "evening:" + pid in dict(s.state.known)
        assert "alibi:" + pid not in dict(s.state.known)
    with pytest.raises(ValueError, match="physical schedule"):
        author = case.crime.kernel.roles.author
        replace_row = tuple(replace(e, end=1439) if e.person == author else e for e in case.evenings)
        validate_evenings(case.crime, case.evidence, replace_row)


def test_corroboration_can_be_collected_before_the_medical_window_but_not_certified(cases):
    case = next(c for c in cases if c.evidence.presences)
    presence = case.evidence.presences[0]
    s = PlaySession(case)
    action = next(a for a in case.plan.actions if a.id == "verify:" + presence.person)
    s.go(case.life.people[presence.person].home)
    s.do("meet:" + presence.person)
    s.do("interview:" + presence.person)
    s.go(action.place)
    assert action.id in {r["id"] for r in s.options()}
    s.do(action.id)
    assert s.remaining() == case.plan.population
    claim = case.claims["alibi:" + presence.person]
    s.state = DiscoveryState(s.state.known + tuple((key, s.at) for key in claim["requires"]), s.state.completed)
    assert presence.person not in s.remaining()


def test_notebook_explains_eliminations_only_from_acquired_public_comparisons(cases):
    case = next(c for c in cases if c.evidence.presences)
    s = PlaySession(case)
    assert all(not reasons for reasons in s.deductions().values())
    p = case.evidence.presences[0]
    action = next(a for a in case.plan.actions if a.id == "verify:" + p.person)
    s.go(case.life.people[p.person].home)
    s.do("meet:" + p.person)
    s.do("interview:" + p.person)
    s.go(action.place)
    s.do(action.id)
    assert not s.deductions()[p.person]
    requirements = case.claims["alibi:" + p.person]["requires"]
    s.state = DiscoveryState(s.state.known + tuple((key, s.at) for key in requirements), s.state.completed)
    assert s.deductions()[p.person]
    assert s.marks == {}
    for pid, reasons in s.deductions().items():
        assert bool(reasons) == (pid not in s.remaining())


def test_context_threads_do_not_leak_unread_correspondence_or_auto_mark_suspects(cases):
    case = next(c for c in cases if any(c.life.concerns(p) and c.life.links(p) for p in c.plan.population))
    pid = next(p for p in sorted(case.plan.population) if c_has_concern(case, p))
    s = PlaySession(case)
    assert not s.inquiry_threads()
    s.go(case.life.people[pid].home)
    s.do("meet:" + pid)
    s.ask_context(pid, "motive")
    thread = next(r for r in s.inquiry_threads() if r["person"] == pid)
    # Meeting someone includes their own evening story, so the venue they named is known.
    verification = next((a for a in case.plan.actions if a.id == "verify:" + pid), None)
    assert thread["state"] == "open" and thread["destination"] == (verification.place if verification else None)
    assert thread["details"] == [s.journal[-1]["text"]]
    assert s.marks == {} and s.remaining() == case.plan.population


def c_has_concern(case, pid):
    return bool(case.life.concerns(pid) and case.life.links(pid))


@pytest.mark.parametrize("seed", range(20))
def test_every_sampled_innocent_narrative_hook_can_be_refuted(seed):
    case = sample_playable(seed)
    assert context_is_refutable(case)
    assert all(p.person != case.crime.kernel.roles.author for p in case.evidence.presences)


@pytest.mark.parametrize("seed", range(20))
def test_guided_cli_follows_acquired_trails_and_can_finish_without_exhausting_every_topic(seed):
    s = PlaySession(sample_playable(seed))
    report = play(s, guided=True)
    assert report["won"]
    assert all(row["candidates_after"] <= row["candidates_before"] for row in report["steps"] if "action" in row)
    assert len([row for row in report["steps"] if "action" in row]) < 60


def test_all_public_elimination_explanations_are_consistent_and_never_remove_the_author(cases):
    for case in cases:
        s = PlaySession(case)
        s.state = DiscoveryState(tuple((a.id, s.at) for a in case.plan.artifacts), ())
        reasons = s.deductions()
        assert not reasons[case.crime.kernel.roles.author]
        for pid, rows in reasons.items():
            assert bool(rows) == (pid not in s.remaining())
            assert all(r["source"] in dict(s.state.known) for r in rows)


def test_no_unread_message_becomes_a_memory(cases):
    case = cases[0]
    old = case.life.messages[0]
    life = replace(case.life, messages=(replace(old, read_at=None),))
    assert life.inbox(old.recipient) == ()
    assert old.text not in life.answer(old.recipient, "messages")


def test_forwarding_cannot_invent_or_upgrade_knowledge(cases):
    case = cases[0]
    old = case.life.messages[0]
    recipient = next(p for p in case.life.people if p not in (old.sender, old.recipient))
    new = Message("forward", old.recipient, recipient, old.text + " and I know who killed",
                  old.sent_at + 10, old.sent_at + 12, old.source, old.id)
    with pytest.raises(ValueError, match="expand its scope"):
        replace(case.life, messages=case.life.messages + (new,))


def test_venue_registers_are_real_context_not_identity_filters(cases):
    for case in cases:
        validate_registrations(case.crime, case.registrations)
        assert {a.id for a in case.plan.actions if a.id.startswith("venue_guests:")} == {"venue_guests:bar", "venue_guests:restaurant"}
        for record in case.registrations:
            with pytest.raises(ValueError, match="actual visit"):
                validate_registrations(case.crime, (replace(record, minute=record.minute + 1),))
        assert not any(a.id.startswith("ask_messages:") for a in case.plan.actions)


def test_wrong_hour_background_footage_is_real_and_never_eliminates_a_suspect(cases):
    ordinary = []
    for case in cases:
        for clip in case.evidence.clips:
            if not clip.event.startswith("ordinary_route:"):
                continue
            ordinary.append(clip)
            assert clip.actor != case.crime.kernel.roles.author
            assert case.evidence.support(clip) == case.plan.population
            assert clip.minute < 17 * 60
            s = PlaySession(case)
            s.do("inspect_scene")
            s.go(clip.place)
            text = s.camera(clip.minute // 60)
            assert "Aucune agression n'est visible" in text
            assert s.remaining() == case.plan.population
    assert ordinary


def test_direct_messages_cannot_gain_hidden_facts_or_false_senders(cases):
    case = cases[0]
    old = case.life.messages[0]
    with pytest.raises(ValueError, match="bounded payload"):
        replace(case.life, messages=(replace(old, text=old.text + " Je sais qui a tué."),))
    sender = next(p for p in case.life.people if p not in (old.sender, old.recipient))
    with pytest.raises(ValueError, match="did not experience"):
        replace(case.life, messages=(replace(old, sender=sender),))


@pytest.mark.parametrize("seed", range(100))
def test_every_whole_action_retains_two_true_candidates(cases, seed):
    case = cases[seed]
    artifacts = {a.id: a for a in case.plan.artifacts}
    for a in case.plan.actions:
        support = case.plan.population.intersection(*(artifacts[k].candidates for k in a.reveals))
        assert len(support) >= 2
        assert case.crime.kernel.roles.author in support
    assert all(a.candidates == case.plan.population for a in case.plan.artifacts
               if a.kind in ("person", "conversation", "correspondence", "diary", "container", "objects"))


@pytest.mark.parametrize("seed", range(100))
def test_local_camera_and_disposal_never_rewrite_the_route(cases, seed):
    case = cases[seed]
    evidence, crime = case.evidence, case.crime
    streets = {n.id for n in crime.streets.nodes if n.kind is NodeKind.STREET}
    assert {c.place for c in evidence.cameras} == streets
    assert {a.place for a in case.plan.actions if a.id.startswith("search_bin:")} == streets
    if evidence.disposal:
        d = evidence.disposal
        assert crime.execution.tool_fate is ToolFate.HIDDEN
        assert d.place == crime.execution.hidden_at
        assert d.place in crime.execution.escape.nodes
        assert d.minute == crime.execution.escape.times[crime.execution.escape.nodes.index(d.place)]
    for cam in evidence.cameras:
        for hour in range(24):
            clips, text = evidence.camera_query(cam.place, hour)
            assert all(c.place == cam.place and c.minute // 60 == hour for c in clips)
            assert all(len(evidence.support(c)) >= 2 for c in clips)
            assert "absent" not in text


def test_wrong_camera_district_or_hour_does_not_find_disposal(cases):
    case = next(c for c in cases if any(clip.event == "disposal" for clip in c.evidence.clips))
    d = case.evidence.disposal
    clips, text = case.evidence.camera_query(d.place, d.minute // 60)
    assert any(c.event == "disposal" for c in clips)
    other = next(c.place for c in case.evidence.cameras if c.place != d.place)
    assert not any(c.event == "disposal" for c in case.evidence.camera_query(other, d.minute // 60)[0])
    assert not any(c.event == "disposal" for c in case.evidence.camera_query(d.place, (d.minute // 60 + 1) % 24)[0])


def test_cannot_forge_disposal_or_footage(cases):
    case = next(c for c in cases if c.evidence.disposal)
    d = case.evidence.disposal
    with pytest.raises(ValueError, match="actual escape"):
        replace(case.evidence, disposal=replace(d, minute=d.minute + 1))
    case = next(c for c in cases if c.evidence.clips)
    clip = case.evidence.clips[0]
    with pytest.raises(ValueError, match="actual event|invented disposal"):
        replace(case.evidence, clips=(replace(clip, minute=clip.minute + 1),))


def test_unknown_appearances_are_not_eliminated_by_private_profiles(cases):
    case = next(c for c in cases if any("description" in claim for claim in c.claims.values()))
    s = PlaySession(case)
    descriptor = next(k for k, c in case.claims.items() if "description" in c)
    # Isolate public semantics without bypassing acquisition in production.
    s.state = DiscoveryState(((descriptor, s.at),), ())
    assert s.remaining() == case.plan.population
    p = next(a for a in case.evidence.appearances if a.person in case.plan.population
             and getattr(a, case.claims[descriptor]["description"]).value != case.claims[descriptor]["value"])
    s.state = DiscoveryState(((descriptor, s.at), ("profile:" + p.person, s.at)), ())
    assert s.remaining() == case.plan.population - {p.person}


def test_fingerprints_require_slot_and_a_physically_available_object(cases):
    case = cases[0]
    s = PlaySession(case)
    p = next(iter(case.plan.population))
    s.go(case.life.people[p].home)
    s.do("search:" + s.place)
    mug = "mug:" + p
    with pytest.raises(ValueError, match="compétence"):
        s.fingerprint(mug)
    s = PlaySession(case, ("fingerprints", "search"))
    with pytest.raises(ValueError, match="examiné"):
        s.fingerprint(mug)
    s.go(case.life.people[p].home)
    before = s.remaining()
    text = s.do("search:" + s.place)  # with the kit, the household mug is lifted on the spot
    assert mug in s.prints and s.remaining() == before
    assert "contact" in text or "Aucune empreinte" in text
    assert set(s.prints[mug]) == {next(r.ridge for r in case.evidence.contacts if r.object == mug)}
    with pytest.raises(ValueError, match="Déjà relevé"):
        s.fingerprint(mug)
    s.go(case.crime.scene)
    other_obj = next(o for o in s.found if o != mug)
    with pytest.raises(ValueError, match="Retournez"):
        s.fingerprint(other_obj)


def test_skills_have_actual_costs_and_no_fingerprint_mandatory_solution(cases):
    case = cases[0]
    with pytest.raises(ValueError):
        PlaySession(case, ("fingerprints", "fingerprints"))
    for skills, expected in ((("search", "rapport"), 3), (("fingerprints", "rapport"), 10)):
        s = PlaySession(case, skills)
        s.go("alley")
        before = s.at
        s.do("search_bin:" + s.place)
        assert s.at - before == expected


def test_manual_marking_never_changes_proof(cases):
    s = PlaySession(cases[0])
    p = next(iter(s.case.plan.population))
    s.marks[p] = "ecarter"
    assert s.remaining() == s.case.plan.population
    assert s.accuse(p)[0] is False
    assert not s.finished


@pytest.mark.parametrize("seed", range(30))
def test_blind_cli_playthrough_can_win_without_truth_or_fingerprints(seed):
    case = sample_playable(seed)
    s = PlaySession(case)
    report = play(s)
    assert report["won"], report
    assert s.finished
    assert s.remaining() == {case.crime.kernel.roles.author}
    assert s.at < 1440 + 22 * 60
    assert not s.prints


def test_deterministic_and_never_certifies_unsolvable_graph(cases):
    assert build_case(3) == build_case(3)
    case = next(c for c in cases if len(c.plan.graph().remaining(a.id for a in c.plan.artifacts)) > 1)
    with pytest.raises(ValueError, match="rejection budget"):
        sample_playable(case.seed, max_attempts=1)
    assert all(c.claims["victim_diary"]["goal"] != "meet_author" for c in cases)


def test_pending_medical_exam_and_no_future_journal(cases):
    s = PlaySession(cases[0])
    assert s.journal == []
    assert not s.leads()[0].startswith("Dernier déplacement")
    s.do("inspect_scene")
    s.do("request_exam")
    s.go("morgue")
    assert "medical_window" not in dict(s.state.known)
    assert "read_medical" not in {r["id"] for r in s.options()}
    s.at += 60
    s.do("read_medical")
    start, end = crime_window(s.case.crime)
    assert start <= s.case.crime.execution.attack_at <= end


def test_questions_about_people_are_bounded_and_not_remote(cases):
    case = cases[0]
    s = PlaySession(case)
    p = next(iter(case.plan.population))
    other = next(person for person in case.plan.population if person != p)
    with pytest.raises(ValueError, match="rejoindre"):
        s.talk_about(p, other)
    s.go(case.life.people[p].home)
    with pytest.raises(ValueError, match="Commencez"):
        s.talk_about(p, other)
    s.do("meet:" + p)
    before = s.remaining()
    text = s.talk_about(p, other)
    assert text == case.life.answer_about(p, other)
    assert s.remaining() == before
    if not case.life.knows(p, other):
        assert "Je ne connais pas" in text


@pytest.mark.parametrize("profile", ("signalement", "horaires", "mixte"))
def test_authoring_can_offer_distinct_proof_routes(profile):
    from scenario_threads import family_lengths
    case = sample_playable(7, profile=profile)
    lengths = family_lengths(case)
    assert thread_profile(lengths) == profile
    if profile != "mixte":
        assert lengths[profile] is not None
    assert case.plan.graph().remaining(a.id for a in case.plan.artifacts) == {case.crime.kernel.roles.author}
    assert play(PlaySession(case))["won"]


def test_surface_traces_require_actual_use_and_lab_comparison(cases):
    case = next(c for c in cases if any(a.id == "collect_object" for a in c.plan.actions)
                and c.crime.method.value != "poisoned")
    surface, = case.evidence.surfaces
    with pytest.raises(ValueError, match="actual weapon"):
        replace(case.evidence, surfaces=(replace(surface, object="invented"),))
    s = PlaySession(case)
    s.do("inspect_scene")
    s.do("collect_object")
    with pytest.raises(ValueError, match="laboratoire"):
        s.analyze_object(surface.object)
    s.go("lab")
    with pytest.raises(ValueError, match="comparaison"):
        s.analyze_object(surface.object)
    s.go(case.crime.scene)
    s.do("request_exam")
    s.at += 60
    s.go("morgue")
    s.do("read_medical")
    s.go("lab")
    before = s.remaining()
    assert "sang" in s.analyze_object(surface.object)
    assert s.remaining() == before


def test_poison_residue_is_comparison_not_a_unique_flask_or_actor(cases):
    case = next(c for c in cases if c.crime.method.value == "poisoned"
                and any(a.id == "collect_object" for a in c.plan.actions))
    s = PlaySession(case)
    s.do("inspect_scene")
    s.do("collect_object")
    s.do("collect_drink")
    s.go("lab")
    with pytest.raises(ValueError, match="verre"):
        s.analyze_object(case.crime.execution.tool)
    s.at += 30
    s.do("analyze_drink")
    assert "Plusieurs flacons" in s.analyze_object(case.crime.execution.tool)
    assert s.remaining() == case.plan.population
def test_poison_corroboration_does_not_invent_a_contact_observation_elsewhere():
    case = next(c for c in map(sample_playable, range(30)) if c.crime.method.value == "poisoned")
    s = PlaySession(case)
    for p in case.evidence.presences:
        s.place = case.life.people[p.person].home
        s.do("meet:" + p.person)
        s.do("interview:" + p.person)
        s.place = p.place
        text = s.do("verify:" + p.person)
        times = remembered_times(p)
        if times:
            assert spoken_time(times["start"]) in text and spoken_time(times["end"]) in text
            row = next(r for r in s.timeline() if r.get("person") == p.person)
            assert row["text"] == text
        else:
            assert "Je n'ai pas regardé l'heure" in text and "service du verre jusqu'au malaise" in text
            assert not any(r.get("person") == p.person for r in s.timeline())
    # Acquire the actual medical and glass results before drawing conclusions.
    s.place = case.crime.scene
    s.do("inspect_scene")
    s.do("request_exam")
    s.do("collect_drink")
    s.at += 60
    s.place = "morgue"
    s.do("read_medical")
    s.place = "lab"
    s.do("analyze_drink")
    for p in case.evidence.presences:
        deduction = s.deductions()[p.person][0]["text"]
        assert ("ailleurs" in deduction) == (p.place != case.crime.scene)


def test_barman_memory_rounds_inward_and_never_leaks_private_minutes(cases):
    for case in cases:
        window_start, window_end = crime_window(case.crime)
        for p in case.evidence.presences:
            expected = remembered_times(p)
            for key in ("evening:" + p.person, "alibi:" + p.person):
                claim = case.claims[key]
                text = next(a.text for a in case.plan.artifacts if a.id == key)
                assert ":" not in text
                if p.basis == "continuous_noncontact":
                    assert "start" not in claim and "end" not in claim
                    continue
                assert p.start <= claim["start"] <= window_start
                assert window_end <= claim["end"] <= p.end
                assert claim["start"] % 15 == claim["end"] % 15 == 0
                assert {k: claim[k] for k in expected} == expected
                assert spoken_time(claim["start"]) in text and spoken_time(claim["end"]) in text


def test_five_minute_memory_example_becomes_an_inner_hour_interval():
    from types import SimpleNamespace
    p = SimpleNamespace(start=19 * 60 + 55, end=21 * 60 + 5, basis="continuous_service")
    assert remembered_times(p) == {"start": 20 * 60, "end": 21 * 60}
    assert spoken_time(20 * 60) == "20 h"
    assert spoken_time(20 * 60 + 15) == "20 h et quart"
    assert spoken_time(20 * 60 + 30) == "20 h et demie"
    assert spoken_time(20 * 60 + 45) == "21 h moins le quart"


