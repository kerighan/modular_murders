import json

import pytest

from scenario_play import PlaySession, sample_playable
from scenario_playtest import play
from scenario_threads import balanced, excluded_by, family_lengths, guide, render

SEEDS = range(12)


def names_in(step):
    return " ".join(step["actions"])


@pytest.mark.parametrize("seed", SEEDS)
def test_family_lengths_never_exclude_the_author_and_mixte_is_the_cheapest(seed):
    case = sample_playable(seed)
    author = case.crime.kernel.roles.author
    lengths = family_lengths(case)
    for key in case.claims:
        if "description" in case.claims[key]:
            assert author not in excluded_by(case, key)
    complete = [lengths[f] for f in ("signalement", "horaires") if lengths[f] is not None]
    assert lengths["mixte"] is not None and all(lengths["mixte"] <= c for c in complete)
    assert lengths["mixte"] >= 3 + 1  # the spine, then at least one source


def test_balanced_needs_two_complete_families_apart():
    assert balanced({"signalement": 12, "horaires": 21, "mixte": 12})
    assert not balanced({"signalement": 12, "horaires": None, "mixte": 12})
    assert not balanced({"signalement": 12, "horaires": 13, "mixte": 12})


@pytest.mark.parametrize("seed", SEEDS)
def test_guide_is_symmetric_across_candidates(seed):
    """Suggestions depend on public knowledge only: every remaining unknown person is
    offered the same way, and verifications only follow accounts the player heard."""
    session = PlaySession(sample_playable(seed))
    people = session.case.life.people
    view = guide(session)
    json.dumps(view)
    assert view["remaining"] == 7 and not view["accusable"]
    signalement, horaires, materiel = view["threads"]
    assert signalement["steps"][0]["state"] == "next"  # the scene first
    session.do("inspect_scene")
    view = guide(session)
    compare = next(s for s in guide(session)["threads"][0]["steps"] if s["title"].startswith("Comparer"))
    assert compare["state"] == "later"  # no description yet: meeting people is not suggested as a filter
    hear = next(s for s in view["threads"][1]["steps"] if s["title"].startswith("Recueillir les récits"))
    listed = hear["actions"][-1]
    assert all(people[pid].name in listed for pid in session.case.plan.population)  # everyone, nobody singled out
    checks = next(s for s in view["threads"][1]["steps"] if s["title"].startswith("Vérifier"))
    assert checks["actions"] == []


@pytest.mark.parametrize("seed", range(4))
def test_guide_follows_a_full_investigation(seed):
    session = PlaySession(sample_playable(seed))
    report = play(session, guided=True)
    assert report["won"]
    view = guide(session)
    assert view["remaining"] == 1 and view["accusable"] and not view["missing"]
    text = render(view)
    assert "dossier prêt à déposer" in text and "Lire l'agenda" not in text.split("Le matériel")[1].split("\n")[1]


def test_guide_names_the_diary_home_even_when_the_victim_lived_with_someone():
    seed = next(s for s in range(60) if any(
        p.home == sample_playable(s).life.people[sample_playable(s).crime.kernel.roles.victim].home
        and p.id != sample_playable(s).crime.kernel.roles.victim for p in sample_playable(s).life.people.values()))
    session = PlaySession(sample_playable(seed))
    diary = next(s for s in guide(session)["threads"][2]["steps"] if s["title"].startswith("Lire l'agenda"))
    assert diary["state"] == "next" and diary["actions"] and "Logement" in diary["actions"][0]


def test_meeting_someone_gives_their_look_and_their_evening():
    session = PlaySession(sample_playable(0))
    pid = sorted(session.case.plan.population)[0]
    session.go(session.case.life.people[pid].home)
    session.do("meet:" + pid)
    known = dict(session.state.known)
    assert "profile:" + pid in known and "evening:" + pid in known


def test_registers_vouch_for_named_guests_once_the_crime_is_dated():
    for seed in range(40):
        case = sample_playable(seed)
        vouched = {pid for claim in case.claims.values() if "register" in claim for pid in claim["register"]}
        if not vouched:
            continue
        session = PlaySession(case)
        session.do("inspect_scene")
        session.do("request_exam")
        for place in ("bar", "restaurant"):
            session.go(place)
            session.do("venue_guests:" + place)
        assert session.remaining() == session.case.plan.population  # not dated yet: context only
        session.go("morgue")
        session.at += 120
        session.do("read_medical")
        assert vouched.isdisjoint(session.remaining())
        assert all(session.alibi_state(pid) == "confirmed" for pid in vouched)
        assert session.case.crime.kernel.roles.author not in vouched
        return
    pytest.fail("no case with a register memory")


def test_batches_verify_every_collected_account_in_one_visit():
    for seed in range(40):
        case = sample_playable(seed)
        presences = [p for p in case.evidence.presences if p.basis == "continuous_service"]
        venue = next((v for v in ("bar", "restaurant") if sum(p.place == v for p in presences) >= 2), None)
        if venue is None:
            continue
        session = PlaySession(case)
        session.do("inspect_scene")
        people = [p.person for p in presences if p.place == venue][:2]
        for pid in people:
            session.go(session.case.life.people[pid].home)
            session.do("meet:" + pid)
        session.go(venue)
        batch = next(b for b in session.batches() if b["id"] == "batch:verify")
        assert set(batch["members"]) >= {"verify:" + pid for pid in people}
        before = session.at
        session.do("batch:verify")
        assert session.at - before <= 5 and all("alibi:" + pid in dict(session.state.known) for pid in people)
        return
    pytest.fail("no venue with two served guests")


def test_free_mode_accuses_at_own_risk_against_the_clock():
    case = sample_playable(3)
    session = PlaySession(case, strict=False, difficulty="normal")
    assert session.deadline and session.time_left >= 180
    author = case.crime.kernel.roles.author
    innocent = sorted(case.plan.population - {author})[0]
    left = session.time_left
    won, text = session.accuse(innocent)
    assert not won and not session.finished and innocent in session.cleared
    assert session.time_left == left - 90 and innocent not in session.remaining()
    with pytest.raises(ValueError):
        session.accuse(innocent)
    won, text = session.accuse(author)
    assert won and session.finished and "aveu" in text  # nothing collected: the confession carried the file
    strict = PlaySession(case)
    assert strict.accuse(author)[0] is False and not strict.finished  # the classic rules still refuse


def test_the_deadline_closes_the_case():
    session = PlaySession(sample_playable(2), strict=False, difficulty="difficile")
    session._advance(session.time_left)
    assert session.finished and session.journal[-1]["id"] == "closed"
    with pytest.raises(ValueError):
        session.go("bar")


# ---------------------------------------------------------------- turn-based clock

def test_turn_mode_freezes_the_clock_until_the_turn_ends():
    from scenario_play import sample_playable, PlaySession
    case = sample_playable(0)
    s = PlaySession(case, ("search", "rapport"), strict=False, difficulty="normal", turn_minutes=30)
    start, turns = s.at, s.turns_left
    s.do("inspect_scene")
    s.go("bar")
    assert s.at == start and s.turns_left == turns  # actions and trips take no clock time
    s.end_turn()
    assert s.at == start + 30 and s.turns_left == turns - 1
    while s.turns_left > 1:
        s.end_turn()
    assert not s.finished
    s.end_turn()
    assert s.finished and any(r["id"] == "closed" for r in s.journal)


def test_turn_mode_mistake_costs_minutes_but_closes_only_at_the_turn_end():
    from scenario_play import sample_playable, PlaySession
    case = sample_playable(0)
    s = PlaySession(case, ("search", "rapport"), strict=False, difficulty="difficile", turn_minutes=30)
    author = case.crime.kernel.roles.author
    wrong = next(p for p in sorted(case.plan.population) if p != author)
    s.place = case.life.people[wrong].home
    s.do("meet:" + wrong)
    while s.time_left > 60:
        s.end_turn()
    won, text = s.accuse(wrong)
    assert not won and "3 tours" in text and s.time_left == 0 and not s.finished  # penalty pushed past the deadline
    s.end_turn()
    assert s.finished


# ---------------------------------------------------------------- partial alibis, colleagues

def test_partial_visits_are_true_verified_and_clear_nobody_including_the_author():
    from scenario_play import sample_playable, PlaySession
    seen_author = seen_innocent = False
    for seed in range(40):
        case = sample_playable(seed)
        author = case.crime.kernel.roles.author
        partial = [p for p in case.evidence.presences if p.basis == "partial_service"]
        if not partial:
            continue
        s = PlaySession(case, ("search", "rapport"), strict=False, difficulty="libre")
        s.do("inspect_scene")
        s.do("request_exam")
        s.place, s.at = "morgue", 10 ** 6
        s.do("read_medical")
        for p in partial:
            s.place = case.life.people[p.person].home
            s.do("meet:" + p.person)
            s.place = p.place
            text = s.do("verify:" + p.person)
            assert "je ne l'ai pas vue" in text and s.alibi_state(p.person) == "partial"
            assert p.person in s.remaining() and p.person not in s.register_entries()
            seen_author |= p.person == author
            seen_innocent |= p.person != author
        assert author in s.remaining()
        if seen_author and seen_innocent:
            break
    assert seen_author and seen_innocent  # a short true story is never a tell


def test_work_answer_names_colleagues_who_then_have_police_records():
    from scenario_play import sample_playable, PlaySession
    case = sample_playable(242)
    life = case.life
    pairs = [(a, b) for a in life.people for b in life.people if a < b
             and life.people[a].workplace == life.people[b].workplace]
    assert pairs
    for a, b in pairs:
        assert life.knows(a, b)
        if case.crime.kernel.roles.victim not in (a, b):
            assert life.people[b].name in life.answer(a, "work") and life.people[a].name in life.answer(b, "work")
            assert "On travaille ensemble" in life.answer_about(a, b)


def test_an_ex_and_the_current_partner_know_each_other_with_a_tone_regardless_of_guilt():
    from scenario_play import sample_playable
    from scenario_life import Link
    seen = 0
    for seed in range(60):
        case = sample_playable(seed)
        life, victim = case.life, case.crime.kernel.roles.victim
        for fact in life.ordinary:
            if fact.kind != "ex_and_partner":
                continue
            ex, partner = fact.people
            assert any(b.kind is Link.EXES for b in life.links(ex, victim))
            assert any(b.kind is Link.PARTNERS for b in life.links(partner, victim))
            assert life.knows(ex, partner) and fact.detail in ("venom", "grace", "neutral")
            assert life.people[partner].name in life.answer_about(ex, partner)
            assert "L'ex de" in life.answer_about(partner, ex)
            seen += 1
    assert seen >= 3


def test_circle_question_names_only_people_the_speaker_knows_who_were_close_to_the_victim():
    from scenario_play import sample_playable
    case = sample_playable(225)
    life, victim = case.life, case.crime.kernel.roles.victim
    for pid in case.plan.population:
        text = life.answer(pid, "circle")
        for other in case.plan.population:
            name = life.people[other].name
            if other == pid:
                continue
            expected = life.knows(pid, other) and bool(life.links(other, victim))
            assert (name in text) == expected, (pid, other, text)


def test_a_sour_breakup_inside_the_story_gives_both_exes_a_pointed_answer():
    from scenario_play import sample_playable
    from scenario_life import Link
    seen = 0
    for seed in range(40):
        case = sample_playable(seed)
        life, victim = case.life, case.crime.kernel.roles.victim
        for fact in life.ordinary:
            if fact.kind != "sour_breakup":
                continue
            x, y = fact.people
            assert victim not in fact.people and any(b.kind is Link.EXES for b in life.links(x, y))
            moved_on = next(p for p in (x, y) if any(b.kind is Link.PARTNERS for b in life.links(p, victim)))
            left = y if moved_on == x else x
            assert "Mon ex" in life.answer_about(moved_on, left)
            assert "On a été ensemble" in life.answer_about(left, moved_on)
            assert fact.detail in ("venom", "neutral")
            seen += 1
    assert seen >= 3


def test_the_scene_hands_out_one_trait_and_the_camera_shows_another():
    from scenario_play import sample_playable
    from scenario_witnesses import EventKind, Aspect
    checked = 0
    for seed in range(40):
        case = sample_playable(seed)
        witnesses = case.witnesses
        decisive = {e.id for e in witnesses.events if e.kind in (EventKind.ASSAULT, EventKind.DRINK_ADDITION)}
        described = {p.aspect for p in witnesses.perceptions if p.event in decisive and p.aspect is not Aspect.SILHOUETTE}
        assert len(described) <= 1  # never two traits from the scene alone
        camera = next((c for c in case.evidence.cameras if c.place == case.crime.scene), None)
        if camera is not None and camera.online:
            assert camera.aspect is not Aspect.SILHOUETTE and camera.aspect not in described
            checked += 1
    assert checked >= 10


def test_social_graph_only_holds_what_was_heard_or_read_and_fades_the_ruled_out():
    from scenario_play import sample_playable, PlaySession
    case = sample_playable(242)
    life, victim = case.life, case.crime.kernel.roles.victim
    s = PlaySession(case, ("search", "rapport"), strict=False, difficulty="libre")
    assert s.social_graph()["edges"] == [] and [n["id"] for n in s.social_graph()["nodes"]] == [victim]
    a, b = sorted(case.plan.population)[:2]
    for pid in (a, b):
        s.place = life.people[pid].home
        s.do("meet:" + pid)
        s.ask_context(pid, "relation")
    s.place = life.people[a].home
    s.talk_about(a, b)
    graph = s.social_graph()
    pairs = {(e["a"], e["b"]) for e in graph["edges"]}
    for pid in (a, b):
        assert ((min(pid, victim), max(pid, victim)) in pairs) == (bool(life.links(pid, victim)) or life.knows(pid, victim))
    assert ((a, b) in pairs) == (bool(life.links(a, b)) or life.knows(a, b)) or [a, b] in graph["strangers"]
    for edge in graph["edges"]:
        assert edge["kinds"] and edge["sources"]
    assert all(not n["excluded"] for n in graph["nodes"])
    s.cleared.add(a)  # ruled out: still drawn, but faded
    assert next(n for n in s.social_graph()["nodes"] if n["id"] == a)["excluded"]


def test_venue_staff_name_their_team_and_a_workplace_tool_sometimes_points_at_the_culprit():
    from scenario_play import sample_playable, PlaySession
    case = sample_playable(242)
    s = PlaySession(case, ("search", "rapport"), strict=False, difficulty="libre")
    for keeper in case.crime.keepers:
        s.place = keeper.place
        text = s.do("venue_staff:" + keeper.place)
        team = [p for p in case.plan.population if case.life.people[p].workplace.value == keeper.place]
        for pid in team:
            assert case.life.people[pid].name in text and pid in s.named_people()
    at_work = venue = 0
    for seed in range(60):
        c = sample_playable(seed)
        taken = [t for t in c.crime.transfers if t.kind.value == "acquisition"]
        if taken and taken[0].origin in ("bar", "restaurant"):
            venue += 1
            at_work += c.life.people[c.crime.kernel.roles.author].workplace.value == taken[0].origin
    assert venue and 0 < at_work < venue  # a lead worth following, never a certainty
