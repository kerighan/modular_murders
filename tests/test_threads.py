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
