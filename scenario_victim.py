"""Victim agency, independent of weapons, crime locations and player evidence.

Typed goals are expanded from true relations/events/knowledge. The small
catalogue returns candidate plans without RNG: physical feasibility comes next.
"""
from dataclasses import dataclass

from scenario_kernel import (DAY, EventKind, IncidentKind, LabelledEnum,
                             RelationKind, SUPPORTED_PREMISES)
from scenario_sampler import Context, Motive, Stake


class InvalidVictimPlan(ValueError):
    pass


class VictimGoal(LabelledEnum):
    RETURN_HOME = "return_home", "rentrer chez soi"
    MEET_PERSON = "meet_person", "retrouver une connaissance"
    REPORT_INCIDENT = "report_incident", "signaler un fait à la police"
    MEET_AUTHOR = "meet_author", "discuter avec une personne impliquée dans le conflit"
    GO_OUT = "go_out", "sortir boire un verre ou dîner"


class PlanReason(LabelledEnum):
    REST = "rest", "se reposer après le travail"
    SHARED_MEAL = "shared_meal", "partager un repas"
    SEEK_SUPPORT = "seek_support", "chercher du soutien après le conflit"
    REPORT_KNOWN_INCIDENT = "report_known_incident", "signaler un fait découvert"
    DISCUSS_CONFLICT = "discuss_conflict", "s'expliquer au sujet du conflit"
    EVENING_OUT = "evening_out", "prendre un repas ou un verre après sa journée"


ARRIVAL_SLOTS = tuple(range(18 * 60, 21 * 60 + 1, 30))
# Authored fictional branches, not a legal classification of all workplace harm.
REPORTABLE_INCIDENTS = (IncidentKind.DIVERTED_WAGES, IncidentKind.PREVIOUS_THEFT)


def allowed_goals(premise):
    """CLI upper bound for the five authored roots; actual facts are checked later."""
    if premise not in SUPPORTED_PREMISES:
        return ()
    goals = (VictimGoal.RETURN_HOME, VictimGoal.MEET_PERSON, VictimGoal.GO_OUT)
    if premise.motive is not Motive.PREDATION:
        goals += (VictimGoal.MEET_AUTHOR,)  # a stranger is never an appointment
    if (premise.motive is Motive.SILENCE and premise.context is Context.WORK
            and premise.stake in (Stake.FRAUD, Stake.PAST_CRIME)):
        goals += (VictimGoal.REPORT_INCIDENT,)
    return goals


@dataclass(frozen=True)
class Appointment:
    id: str
    visitor: str
    host: str
    place: str
    agreed_at: int
    starts_at: int
    # Explicit stationary presence at home; not a complete host-day trajectory.
    host_present_from: int
    host_present_until: int


@dataclass(frozen=True)
class VictimPlan:
    id: str
    person: str
    goal: VictimGoal
    reason: PlanReason
    origin: str
    destination: str
    formed_at: int
    expected_arrival_at: int
    sources: tuple[str, ...]
    informed_people: tuple[str, ...]
    appointment: Appointment | None = None


@dataclass(frozen=True)
class MissedAppointment:
    appointment: str
    observer: str
    visitor: str
    place: str
    observed_at: int
    # Only nonarrival is known: no guilt, cause of death or murderer identity.


def require(condition, message):
    if not condition:
        raise InvalidVictimPlan(message)


def contact_basis(kernel, host):
    """Concrete known acquaintance, never an arbitrary person drawn from the cast."""
    v = kernel.roles.victim
    friends = [r for r in kernel.world.relationships
               if r.kind in (RelationKind.FRIENDS, RelationKind.ROMANTIC)
               and r.active_at(0) and set(r.people) == {v, host}]
    if friends:
        return (friends[0].id,)
    # The intended disclosure recipient is an established contact. Same-employer
    # coincidence alone is NOT enough to assume acquaintanceship.
    disclosure = next((d for d in kernel.world.disclosures
                       if d.speaker == v and d.recipient == host), None)
    people = {p.id: p for p in kernel.world.people}
    if disclosure and host in people and people[host].workplace is people[v].workplace:
        return (disclosure.id,)
    return None


def validate_plan(kernel, plan):
    require(type(plan) is VictimPlan and plan.id == "victim_plan", "typed victim plan")
    people = {p.id: p for p in kernel.world.people}
    v = people[kernel.roles.victim]
    require(plan.person == v.id and type(plan.goal) is VictimGoal
            and type(plan.reason) is PlanReason
            and plan.origin == (v.home if plan.goal in (VictimGoal.MEET_AUTHOR, VictimGoal.GO_OUT)
                                else v.workplace.value),
            "plan belongs to the actual victim leaving work")
    require(type(plan.formed_at) is int and type(plan.expected_arrival_at) is int
            and plan.formed_at < plan.expected_arrival_at < DAY
            and 17 * 60 <= plan.expected_arrival_at <= 21 * 60,
            "plan chronology and arrival window")
    require(type(plan.sources) is tuple and type(plan.informed_people) is tuple,
            "immutable sources and informed people")
    if plan.goal is VictimGoal.RETURN_HOME:
        require(plan.reason is PlanReason.REST and plan.destination == v.home
                and plan.sources == (v.id,) and plan.informed_people == (v.id,)
                and plan.appointment is None, "ordinary home goal has no invented appointment")
    elif plan.goal is VictimGoal.MEET_PERSON:
        meeting = plan.appointment
        require(type(meeting) is Appointment and meeting.id == "victim_appointment"
                and meeting.visitor == v.id and meeting.host in people
                and meeting.host not in (v.id, kernel.roles.author), "real distinct appointment host")
        basis = contact_basis(kernel, meeting.host)
        require(basis is not None and meeting.place == people[meeting.host].home == plan.destination
                and plan.informed_people == (v.id, meeting.host), "known contact and agreed home destination")
        require(all(type(t) is int for t in (meeting.agreed_at, meeting.starts_at,
                                             meeting.host_present_from, meeting.host_present_until))
                and meeting.agreed_at == plan.formed_at and meeting.starts_at == plan.expected_arrival_at
                and 0 <= meeting.host_present_from <= meeting.starts_at
                and meeting.starts_at + 15 <= meeting.host_present_until < DAY,
                "host actually present to notice a missed agreed appointment")
        if plan.reason is PlanReason.SHARED_MEAL:
            require(plan.sources == basis, "meal uses a real acquaintance, not a murder requirement")
        elif plan.reason is PlanReason.SEEK_SUPPORT:
            autonomy = next((e for e in kernel.world.events
                             if e.kind in (EventKind.SEPARATION_ANNOUNCED, EventKind.REFUSAL_EXPRESSED)
                             and e.actor == v.id), None)
            require(autonomy is not None and any(r.kind is RelationKind.FRIENDS
                    and set(r.people) == {v.id, meeting.host} for r in kernel.world.relationships)
                    and plan.sources == basis + (autonomy.id,) and autonomy.minute < plan.formed_at,
                    "support follows a real conflict and an actual friendship")
        else:
            require(False, "unsupported meeting reason")
        for id in basis:
            source = next((r for r in kernel.world.relationships if r.id == id), None)
            if source:
                since = source.since
            else:
                disclosure = next(d for d in kernel.world.disclosures if d.id == id)
                since = next(e.minute for e in kernel.world.events if e.id == disclosure.announced_by)
            require(since < plan.formed_at, "contact established before agreement")
    elif plan.goal is VictimGoal.MEET_AUTHOR:
        meeting = plan.appointment
        a = kernel.roles.author
        basis = tuple(r.id for r in kernel.world.relationships
                      if set(r.people) == {v.id, a} and r.active_at(plan.formed_at))
        require(type(meeting) is Appointment and meeting.id == "conflict_appointment"
                and meeting.visitor == v.id and meeting.host == a and basis
                and plan.reason is PlanReason.DISCUSS_CONFLICT
                and plan.destination in ("alley", "crime_scene", "victim_street", "promenade")
                and meeting.place == plan.destination and plan.sources == (basis[0],)
                and plan.informed_people == (v.id, a), "agreed conflict meeting requires known actors and a public destination")
        require(all(type(t) is int for t in (meeting.agreed_at, meeting.starts_at,
                                            meeting.host_present_from, meeting.host_present_until))
                and meeting.agreed_at == plan.formed_at and meeting.starts_at == plan.expected_arrival_at
                and 0 <= meeting.host_present_from <= meeting.starts_at
                and meeting.starts_at + 15 <= meeting.host_present_until < DAY,
                "agreed meeting has a real time and expected host presence")
    elif plan.goal is VictimGoal.GO_OUT:
        require(plan.reason is PlanReason.EVENING_OUT and plan.destination in ("bar", "restaurant")
                and plan.sources == (v.id,) and plan.informed_people == (v.id,)
                and plan.appointment is None, "ordinary outing is the victim's own plan, not a secret communicated to the author")
    else:
        require(plan.reason is PlanReason.REPORT_KNOWN_INCIDENT and plan.destination == "police"
                and plan.appointment is None and plan.informed_people == (v.id,),
                "police walk-in, not an invented person awaiting the victim")
        incident = next((i for i in kernel.world.incidents if i.kind in REPORTABLE_INCIDENTS), None)
        knowledge = next((k for k in kernel.world.knowledge
                          if incident and k.person == v.id and k.incident == incident.id), None)
        require(incident is not None and knowledge is not None
                and plan.sources == (incident.id, knowledge.learned_by),
                "report requires an existing incident actually known to the victim")
        discovery = next(e for e in kernel.world.events if e.id == knowledge.learned_by)
        require(discovery.minute < plan.formed_at, "knowledge precedes reporting intention")
    return plan


def candidate_plans(kernel, *, goal=None):
    """Goal domains constrain destinations/reasons; no sampling or changes to kernel."""
    if goal is not None and type(goal) is not VictimGoal:
        raise TypeError("expected VictimGoal")
    people = {p.id: p for p in kernel.world.people}
    v = people[kernel.roles.victim]
    plans = []

    def add(selected, reason, destination, formed_at, sources, host=None):
        if goal is not None and selected is not goal:
            return
        for arrival in ARRIVAL_SLOTS:
            meeting = (Appointment("victim_appointment", v.id, host, destination, formed_at,
                                   arrival, arrival - 30, arrival + 45) if host else None)
            plan = VictimPlan("victim_plan", v.id, selected, reason, v.workplace.value,
                              destination, formed_at, arrival, sources,
                              (v.id, host) if host else (v.id,), meeting)
            plans.append(validate_plan(kernel, plan))

    add(VictimGoal.RETURN_HOME, PlanReason.REST, v.home, 12 * 60, (v.id,))
    autonomy = next((e for e in kernel.world.events
                     if e.kind in (EventKind.SEPARATION_ANNOUNCED, EventKind.REFUSAL_EXPRESSED)
                     and e.actor == v.id), None)
    for host in kernel.world.people:
        if host.id in (v.id, kernel.roles.author):
            continue
        basis = contact_basis(kernel, host.id)
        if basis is None:
            continue
        # Social meal independent of murder; agreement made earlier on crime day.
        add(VictimGoal.MEET_PERSON, PlanReason.SHARED_MEAL, host.home, 10 * 60, basis, host.id)
        if autonomy and any(r.kind is RelationKind.FRIENDS and set(r.people) == {v.id, host.id}
                            for r in kernel.world.relationships):
            add(VictimGoal.MEET_PERSON, PlanReason.SEEK_SUPPORT, host.home, autonomy.minute + 15,
                basis + (autonomy.id,), host.id)
    incident = next((i for i in kernel.world.incidents if i.kind in REPORTABLE_INCIDENTS), None)
    knowledge = next((k for k in kernel.world.knowledge
                      if incident and k.person == v.id and k.incident == incident.id), None)
    if knowledge:
        discovery = next(e for e in kernel.world.events if e.id == knowledge.learned_by)
        add(VictimGoal.REPORT_INCIDENT, PlanReason.REPORT_KNOWN_INCIDENT, "police", discovery.minute + 15,
            (incident.id, knowledge.learned_by))
    # These leave home, not a mandatory workplace. Concrete agreement is a new
    # authoring fact, explicitly known to both parties, not inferred from a link.
    a = kernel.roles.author
    basis = next((r for r in kernel.world.relationships
                  if set(r.people) == {v.id, a} and r.active_at(10 * 60)), None)
    for arrival in ARRIVAL_SLOTS:
        if basis and goal in (None, VictimGoal.MEET_AUTHOR):
            for street in ("alley", "crime_scene", "victim_street", "promenade"):
                meeting = Appointment("conflict_appointment", v.id, a, street, 10 * 60,
                                      arrival, arrival - 30, arrival + 45)
                plans.append(validate_plan(kernel, VictimPlan("victim_plan", v.id, VictimGoal.MEET_AUTHOR,
                    PlanReason.DISCUSS_CONFLICT, v.home, street, meeting.agreed_at,
                    arrival, (basis.id,), (v.id, a), meeting)))
        if goal in (None, VictimGoal.GO_OUT):
            for venue in ("bar", "restaurant"):
                plans.append(validate_plan(kernel, VictimPlan("victim_plan", v.id, VictimGoal.GO_OUT,
                    PlanReason.EVENING_OUT, v.home, venue, 12 * 60, arrival, (v.id,), (v.id,))))
    return tuple(plans)


def missed_appointments(plan, actual_walk, death_at):
    """A later nonarrival, not a witness of death. Public projection still separate."""
    meeting = plan.appointment
    if (meeting is None or plan.goal is VictimGoal.MEET_AUTHOR or actual_walk.nodes[-1] == plan.destination
            or death_at > meeting.starts_at + 15):
        return ()
    return (MissedAppointment(meeting.id, meeting.host, plan.person, meeting.place,
                              meeting.starts_at + 15),)


def purpose_text(plan, people, kernel):
    if plan.goal is VictimGoal.MEET_AUTHOR:
        return f"retrouver {people[plan.appointment.host].name} pour s'expliquer sur leur différend"
    if plan.goal is VictimGoal.GO_OUT:
        return "sortir dîner au Comptoir" if plan.destination == "restaurant" else "sortir prendre un verre au Néon Bleu"
    if plan.goal is VictimGoal.RETURN_HOME:
        return "rentrer chez soi pour se reposer"
    if plan.goal is VictimGoal.REPORT_INCIDENT:
        incident = next(i for i in kernel.world.incidents if i.id == plan.sources[0])
        fact = ("le détournement de sa rémunération" if incident.kind is IncidentKind.DIVERTED_WAGES
                else "un vol découvert au travail")
        return f"aller au commissariat signaler {fact}"
    host = people[plan.appointment.host].name
    if plan.reason is PlanReason.SHARED_MEAL:
        return f"retrouver {host} pour dîner"
    event = next(e for e in kernel.world.events if e.id == plan.sources[-1])
    topic = "de sa séparation" if event.kind is EventKind.SEPARATION_ANNOUNCED else "d'une exigence refusée"
    return f"retrouver {host} pour parler {topic} et chercher du soutien"


def absence_text(plan, people):
    """Developer preview of only what the waiting person can know."""
    arrival = plan.expected_arrival_at
    hour = f"{arrival // 60:02d} h {arrival % 60:02d}"
    name = people[plan.person].name
    return (f"On devait dîner ensemble vers {hour}. J'ai attendu, mais on ne s'est pas vus."
            if plan.reason is PlanReason.SHARED_MEAL else
            f"On avait convenu que {name} passerait me voir vers {hour}, pour parler. J'ai attendu ; le rendez-vous n'a pas eu lieu.")
