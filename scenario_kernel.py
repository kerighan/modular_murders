"""Private pre-crime truth, built from an abstract CrimePremise.

Step 4 prototype: six explicitly supported premises, typed people/resources,
relationships, causally ordered events and intentions. No murder has happened
yet. Method, travel, witnesses, manifestations and player evidence are later
layers; this developer CLI is NOT a public game view.

python scenario_kernel.py --motive control --context romance --stake separation
python scenario_kernel.py --motive silence --context work --stake fraud --json
"""
import argparse
import json
import random
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from types import MappingProxyType

from scenario_sampler import (CONTEXTS, RULES, Context, CrimePremise, Motive,
                              RequiredFact, Stake, allowed_premises)


KERNEL_VERSION = 3
DAY = 24 * 60


class UnsupportedPremise(ValueError):
    pass


class InvalidKernel(ValueError):
    pass


class LabelledEnum(Enum):
    def __new__(cls, code, label):
        member = object.__new__(cls)
        member._value_ = code
        member.label = label
        return member


class Workplace(LabelledEnum):
    PALACE = "cabaret", "Le Palace"
    BAR = "bar", "Le Néon Bleu"
    HOSPITAL = "hospital", "L'hôpital"
    VIDEO = "cctv", "La Régie vidéo"
    RESTAURANT = "restaurant", "Le Comptoir"


class Occupation(LabelledEnum):
    DANCE = "dance", "danse"
    STAGE_MANAGEMENT = "stage_management", "régie de scène"
    TABLE_SERVICE = "table_service", "service en salle"
    BAR_MANAGEMENT = "bar_management", "gestion du bar"
    NURSING = "nursing", "soins infirmiers"
    HOSPITAL_ADMIN = "hospital_admin", "administration hospitalière"
    VIDEO_TECHNICIAN = "video_technician", "maintenance vidéo"
    VIDEO_MANAGEMENT = "video_management", "gestion de la Régie"
    ACCOUNTING = "accounting", "comptabilité"
    COOKING = "cooking", "cuisine"
    RESTAURANT_MANAGEMENT = "restaurant_management", "gestion du restaurant"


# (employee, supervisor, other lawful employees). These are authoring roles,
# not occupational risk statistics and not indicators of guilt.
JOBS = MappingProxyType({
    Workplace.RESTAURANT: (Occupation.COOKING, Occupation.RESTAURANT_MANAGEMENT, Occupation.ACCOUNTING),
    Workplace.PALACE: (Occupation.DANCE, Occupation.STAGE_MANAGEMENT, Occupation.ACCOUNTING),
    Workplace.BAR: (Occupation.TABLE_SERVICE, Occupation.BAR_MANAGEMENT, Occupation.ACCOUNTING),
    Workplace.HOSPITAL: (Occupation.NURSING, Occupation.HOSPITAL_ADMIN, Occupation.ACCOUNTING),
    Workplace.VIDEO: (Occupation.VIDEO_TECHNICIAN, Occupation.VIDEO_MANAGEMENT, Occupation.ACCOUNTING),
})


class RelationKind(LabelledEnum):
    ROMANTIC = "romantic", "relation sentimentale"
    FRIENDS = "friends", "amitié"
    COLLEAGUES = "colleagues", "collègues"
    ACQUAINTANCES = "acquaintances", "connaissance personnelle"


class ResourceKind(Enum):
    HOME = "home"
    SUPPORT_BUDGET = "support_budget"
    MONEY = "money"
    LABOR = "labor"
    VALUABLE = "valuable"


class ControlMechanism(LabelledEnum):
    FINANCIAL = "financial", "dépendance financière"
    HOUSING = "housing", "dépendance au logement"


class DemandKind(LabelledEnum):
    PHONE_ACCESS = "phone_access", "exiger l'accès au téléphone personnel"
    STOP_SEEING_FRIEND = "stop_seeing_friend", "exiger la rupture d'une amitié"


class IncidentKind(LabelledEnum):
    DIVERTED_WAGES = "diverted_wages", "rémunération détournée"
    UNPAID_WORK = "unpaid_work", "heures imposées et non payées"
    PREVIOUS_THEFT = "previous_theft", "vol antérieur"


class EventKind(LabelledEnum):
    CONTROL_ESTABLISHED = "control_established", "La dépendance se met en place"
    DEMAND_MADE = "demand_made", "Une exigence est formulée"
    SEPARATION_ANNOUNCED = "separation_announced", "La séparation est annoncée"
    REFUSAL_EXPRESSED = "refusal_expressed", "L'exigence est refusée"
    AUTONOMY_REJECTED = "autonomy_rejected", "L'auteur refuse l'autonomie de la victime"
    MISCONDUCT = "misconduct", "La faute est commise"
    DISCOVERY = "discovery", "La victime découvre la faute"
    DISCLOSURE_ANNOUNCED = "disclosure_announced", "La victime annonce qu'elle va en parler"
    DISCLOSURE_FEARED = "disclosure_feared", "L'auteur redoute la divulgation"
    INTENT_FORMED = "intent_formed", "L'auteur décide de tuer"
    RELATIONSHIP_DISCLOSED = "relationship_disclosed", "La nouvelle relation est annoncée à l'ancien partenaire"
    RECONCILIATION_REFUSED = "reconciliation_refused", "Le partenaire refuse de reprendre l'ancienne relation"
    RIVAL_BLAMED = "rival_blamed", "L'auteur attribue son échec sentimental au rival"
    TARGET_NOTICED = "target_noticed", "L'auteur remarque la victime, qu'il ne connaît pas"
    TARGET_WATCHED = "target_watched", "L'auteur observe la victime à distance"


class GoalKind(LabelledEnum):
    DENY_AUTONOMY = "deny_autonomy", "empêcher la victime d'exercer son autonomie"
    STOP_DISCLOSURE = "stop_disclosure", "empêcher la divulgation de la faute"
    REMOVE_ROMANTIC_RIVAL = "remove_romantic_rival", "éliminer le rival pour tenter de renouer avec son ancien partenaire"
    SEEK_THE_ACT = "seek_the_act", "commettre l'acte lui-même, sans rien attendre de la victime"


class ExpectedEffect(Enum):
    DEATH_BLOCKS_AUTONOMY = "death_blocks_autonomy"
    DEATH_BLOCKS_DISCLOSURE = "death_blocks_disclosure"
    DEATH_REMOVES_RIVAL = "death_removes_rival"
    DEATH_IS_THE_ACT = "death_is_the_act"


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    occupation: Occupation
    workplace: Workplace
    home: str
    monthly_income: int
    monthly_expenses: int


@dataclass(frozen=True)
class Relationship:
    id: str
    kind: RelationKind
    people: tuple[str, str]
    since: int
    until: int | None = None

    def active_at(self, minute):
        return self.since <= minute and (self.until is None or minute < self.until)


@dataclass(frozen=True)
class Resource:
    id: str
    kind: ResourceKind
    owner: str
    holder: str
    description: str
    amount: int = 0


@dataclass(frozen=True)
class Event:
    id: str
    kind: EventKind
    minute: int  # relative to an eventual crime day; no murder time selected yet
    actor: str
    target: str  # person concerned, NOT necessarily co-present or a witness
    place: str
    subject: str  # resource, dependency, demand, incident or disclosure id
    causes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dependency:
    id: str
    controller: str
    dependent: str
    mechanism: ControlMechanism
    resource: str
    established_by: str
    monthly_need: int = 0


@dataclass(frozen=True)
class Demand:
    id: str
    kind: DemandKind
    issuer: str
    addressee: str
    event: str
    third_person: str | None = None


@dataclass(frozen=True)
class Incident:
    id: str
    kind: IncidentKind
    perpetrator: str
    affected: str
    resource: str
    event: str
    paid: int = 0


@dataclass(frozen=True)
class Knowledge:
    person: str
    incident: str
    learned_by: str


@dataclass(frozen=True)
class Disclosure:
    id: str
    speaker: str
    recipient: str
    incident: str
    announced_by: str
    scheduled_for: int


@dataclass(frozen=True)
class RomanticRivalry:
    id: str
    claimant: str
    rival: str
    partner: str
    former_relationship: str
    current_relationship: str
    disclosed_by: str
    refused_by: str


@dataclass(frozen=True)
class Fixation:
    """A stranger singled out: noticed once, then watched (studied) or not (chance)."""
    id: str
    author: str
    target: str
    noticed_by: str
    watches: tuple[str, ...]
    studied: bool


@dataclass(frozen=True)
class World:
    people: tuple[Person, ...]
    relationships: tuple[Relationship, ...]
    resources: tuple[Resource, ...]
    events: tuple[Event, ...]
    dependencies: tuple[Dependency, ...] = ()
    demands: tuple[Demand, ...] = ()
    incidents: tuple[Incident, ...] = ()
    knowledge: tuple[Knowledge, ...] = ()
    disclosures: tuple[Disclosure, ...] = ()
    rivalries: tuple[RomanticRivalry, ...] = ()
    fixations: tuple[Fixation, ...] = ()


@dataclass(frozen=True)
class Roles:
    author: str
    victim: str
    other: str  # friend / intended disclosure recipient; never automatically guilty


@dataclass(frozen=True)
class Intent:
    author: str
    target: str
    goal: GoalKind
    expected_effect: ExpectedEffect  # an actor belief, not a guaranteed consequence
    event: str
    subject: str


@dataclass(frozen=True)
class RequirementWitness:
    requirement: RequiredFact
    sources: tuple[str, ...]  # actual world entities/events supporting the predicate


@dataclass(frozen=True)
class CausalKernel:
    premise: CrimePremise
    roles: Roles
    world: World
    intent: Intent

    def __post_init__(self):
        validate_kernel(self)

    @property
    def method(self):
        """Unresolved, rather than a fake randomly selected weapon."""
        return None

    def as_dict(self):
        return {"kernel_version": KERNEL_VERSION, "visibility": "private_precrime_truth",
                "premise": self.premise.as_dict(), "roles": _encode(self.roles),
                "world": _encode(self.world), "intent": _encode(self.intent), "method": None,
                "satisfied_requirements": _encode(validate_kernel(self))}


SUPPORTED_PREMISES = (
    CrimePremise(Motive.SILENCE, Context.WORK, Stake.FRAUD),
    CrimePremise(Motive.SILENCE, Context.WORK, Stake.EXPLOITATION),
    CrimePremise(Motive.SILENCE, Context.WORK, Stake.PAST_CRIME),
    CrimePremise(Motive.CONTROL, Context.ROMANCE, Stake.SEPARATION),
    CrimePremise(Motive.CONTROL, Context.ROMANCE, Stake.REFUSAL),
    CrimePremise(Motive.REMOVE_OBSTACLE, Context.ROMANCE, Stake.ROMANTIC_RIVAL),
    CrimePremise(Motive.PREDATION, Context.CHANCE_ENCOUNTER, Stake.DOMINATION),
    CrimePremise(Motive.PREDATION, Context.CHANCE_ENCOUNTER, Stake.VIOLENCE),
)
PREDATION_SHARE = 0.22  # of unfiltered draws; drawn on its own stream so older seeds keep their cases


def _encode(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _encode(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    return value


def _require(condition, message):
    if not condition:
        raise InvalidKernel(message)


def _index(items):
    return {item.id: item for item in items}


def _related(world, a, b, kind):
    return tuple(r for r in world.relationships if r.kind is kind and set(r.people) == {a, b})


def romantic_triangles(world):
    """Social motifs from real relationships; no motive, rivalry or guilt implied."""
    return tuple((person.id, former.id, current.id)
                 for person in world.people
                 for former in world.relationships if former.kind is RelationKind.ROMANTIC
                 and person.id in former.people and former.until is not None
                 for current in world.relationships if current.kind is RelationKind.ROMANTIC
                 and person.id in current.people and current.until is None
                 and former.until <= current.since
                 and set(former.people) != set(current.people))


def link_to_victim(kernel, person):
    """Derived relationship, independent of murderer role. May return several real links."""
    if person not in {p.id for p in kernel.world.people} or person == kernel.roles.victim:
        raise ValueError("A distinct existing person is required")
    links = []
    for relation in kernel.world.relationships:
        if set(relation.people) != {person, kernel.roles.victim}:
            continue
        if relation.kind is RelationKind.ROMANTIC:
            links.append("partner" if relation.active_at(0) else "ex")
        elif relation.active_at(0):
            links.append(relation.kind.value)
    return tuple(dict.fromkeys(links)) or ("unknown",)


def validate_kernel(kernel):
    """Check real references, resources, participants, order and causal links.

    Never accepts a supplied list of RequiredFact tokens as proof. Witnesses are
    computed from the world, and fail closed on unsupported construction rules.
    This validates pre-crime motivation, not physical feasibility of a murder.
    """
    _require(type(kernel.premise) is CrimePremise, "A typed premise is required")
    if kernel.premise not in SUPPORTED_PREMISES:
        raise UnsupportedPremise(f"Kernel not implemented for {kernel.premise.as_dict()}")
    w, roles, intent = kernel.world, kernel.roles, kernel.intent
    _require(type(w) is World and type(roles) is Roles and type(intent) is Intent, "Typed world, roles and intent required")
    collections = ((w.people, Person), (w.relationships, Relationship), (w.resources, Resource),
                   (w.events, Event), (w.dependencies, Dependency), (w.demands, Demand),
                   (w.incidents, Incident), (w.disclosures, Disclosure), (w.rivalries, RomanticRivalry),
                   (w.fixations, Fixation))
    for items, cls in collections:
        _require(type(items) is tuple and all(type(item) is cls for item in items), f"Immutable typed {cls.__name__} collection required")
    _require(type(w.knowledge) is tuple and all(type(k) is Knowledge for k in w.knowledge), "Typed knowledge required")
    ids = [item.id for items, _ in collections for item in items]
    _require(all(type(id) is str and id for id in ids) and len(set(ids)) == len(ids), "World entity IDs must be globally unique")
    people, resources, events = _index(w.people), _index(w.resources), _index(w.events)
    deps, demands, incidents, disclosures = map(_index, (w.dependencies, w.demands, w.incidents, w.disclosures))
    _require(len({roles.author, roles.victim, roles.other}) == 3 and all(id in people for id in (roles.author, roles.victim, roles.other)), "Roles require three distinct existing people")
    _require(len({p.name for p in w.people}) == len(w.people) and all(p.name for p in w.people), "People need distinct names")
    for person in w.people:
        _require(type(person.workplace) is Workplace and type(person.occupation) is Occupation
                 and person.occupation in JOBS[person.workplace], "Occupation must fit workplace")
        _require(type(person.monthly_income) is int and person.monthly_income > 0, "Income must be positive")
        _require(type(person.monthly_expenses) is int and person.monthly_expenses >= 0, "Expenses must be nonnegative")
        _require(person.home in resources and resources[person.home].kind is ResourceKind.HOME, "Person must have a real home")
    for resource in w.resources:
        _require(type(resource.kind) is ResourceKind and resource.owner in people and resource.holder in people, "Resource ownership/holder must exist")
        _require(type(resource.amount) is int and resource.amount >= 0 and bool(resource.description), "Resource quantities/descriptions must be valid")
    for relation in w.relationships:
        _require(type(relation.kind) is RelationKind and type(relation.people) is tuple
                 and len(relation.people) == 2 and len(set(relation.people)) == 2
                 and all(id in people for id in relation.people) and type(relation.since) is int, "Relationship endpoints must exist and differ")
        _require(relation.until is None or type(relation.until) is int and relation.since < relation.until < 0,
                 "Ended relationships require a valid end after their start")
        if relation.kind is RelationKind.COLLEAGUES:
            _require(people[relation.people[0]].workplace is people[relation.people[1]].workplace, "Colleagues must share a workplace")
    subjects = (set(resources) | set(deps) | set(demands) | set(incidents) | set(disclosures)
                | {r.id for r in w.relationships} | {r.id for r in w.rivalries} | {f.id for f in w.fixations})
    valid_places = {p.home for p in w.people} | {place.value for place in Workplace}
    for event in w.events:
        _require(type(event.kind) is EventKind and type(event.minute) is int and event.minute < 0, "Events must precede the unresolved crime day")
        _require(event.actor in people and event.target in people and event.actor != event.target, "Event participants must exist and differ")
        _require(event.place in valid_places and event.subject in subjects, "Event place/subject must exist")
        _require(type(event.causes) is tuple and len(set(event.causes)) == len(event.causes), "Causal references must be immutable and unique")
        _require(all(id in events and events[id].minute < event.minute for id in event.causes), "Causal parents must exist and strictly precede events")
    def producer(id, kind, actor, target, subject):
        _require(id in events, "Missing producer event")
        e = events[id]
        _require(e.kind is kind and (e.actor, e.target, e.subject) == (actor, target, subject), "Producer event does not match its fact")
        return e
    for dep in w.dependencies:
        _require(type(dep.mechanism) is ControlMechanism and dep.controller in people and dep.dependent in people
                 and dep.controller != dep.dependent and dep.resource in resources, "Dependency endpoints/resource must exist")
        producer(dep.established_by, EventKind.CONTROL_ESTABLISHED, dep.controller, dep.dependent, dep.id)
        resource = resources[dep.resource]
        _require(resource.owner == resource.holder == dep.controller, "Controller must actually control the resource")
        _require(type(dep.monthly_need) is int, "Dependency need must be an integer")
        if dep.mechanism is ControlMechanism.FINANCIAL:
            _require(resource.kind is ResourceKind.SUPPORT_BUDGET and 0 < dep.monthly_need <= resource.amount, "Financial dependency needs funded support")
            dependent, controller = people[dep.dependent], people[dep.controller]
            _require(dependent.monthly_expenses - dependent.monthly_income == dep.monthly_need,
                     "Financial dependency requires a real income/expense deficit")
            _require(controller.monthly_income - controller.monthly_expenses >= resource.amount,
                     "Controller must actually be able to fund the support")
        else:
            _require(resource.kind is ResourceKind.HOME and dep.monthly_need == 0
                     and people[dep.controller].home == people[dep.dependent].home == resource.id, "Housing dependency requires actual shared housing")
            _require(not any(r.kind is ResourceKind.HOME and r.owner == dep.dependent for r in w.resources), "Housing dependency contradicts an independently owned home")
    for demand in w.demands:
        _require(type(demand.kind) is DemandKind, "Typed demand required")
        producer(demand.event, EventKind.DEMAND_MADE, demand.issuer, demand.addressee, demand.id)
        if demand.kind is DemandKind.STOP_SEEING_FRIEND:
            _require(demand.third_person in people and bool(_related(w, demand.addressee, demand.third_person, RelationKind.FRIENDS)), "Contact restriction must concern a real friend")
        else:
            _require(demand.third_person is None, "Phone-access demand has no third-person target")
    for incident in w.incidents:
        _require(type(incident.kind) is IncidentKind and incident.resource in resources
                 and type(incident.paid) is int and incident.paid >= 0, "Typed incident/resource required")
        e = producer(incident.event, EventKind.MISCONDUCT, incident.perpetrator, incident.affected, incident.id)
        r = resources[incident.resource]
        _require(r.owner == incident.affected and r.holder == incident.perpetrator and r.amount > 0, "Misconduct must have a real affected owner and appropriation")
        expected_kind = {IncidentKind.DIVERTED_WAGES: ResourceKind.MONEY,
                         IncidentKind.UNPAID_WORK: ResourceKind.LABOR,
                         IncidentKind.PREVIOUS_THEFT: ResourceKind.VALUABLE}[incident.kind]
        _require(r.kind is expected_kind and incident.paid == 0, "Resource/payment must match misconduct")
        _require(people[incident.perpetrator].workplace.value == people[incident.affected].workplace.value == e.place, "Work misconduct must concern actual employees at this workplace")
        _require(people[incident.perpetrator].occupation is JOBS[people[incident.perpetrator].workplace][1], "Work misconduct requires the authored supervisory role")
    for knowledge in w.knowledge:
        _require(knowledge.person in people and knowledge.incident in incidents and knowledge.learned_by in events, "Knowledge references must exist")
        incident = incidents[knowledge.incident]
        e = producer(knowledge.learned_by, EventKind.DISCOVERY, knowledge.person, incident.perpetrator, incident.id)
        _require(incident.event in e.causes and e.place == people[knowledge.person].workplace.value, "Discovery must follow this incident at the workplace")
    for disclosure in w.disclosures:
        _require(disclosure.recipient in people and disclosure.recipient != disclosure.speaker
                 and disclosure.incident in incidents, "Disclosure recipient/incident must exist")
        incident = incidents[disclosure.incident]
        e = producer(disclosure.announced_by, EventKind.DISCLOSURE_ANNOUNCED, disclosure.speaker, incident.perpetrator, disclosure.id)
        known = [k for k in w.knowledge if k.person == disclosure.speaker and k.incident == disclosure.incident and k.learned_by in e.causes]
        _require(bool(known) and type(disclosure.scheduled_for) is int and disclosure.scheduled_for > 0, "Disclosure needs actual knowledge and a future appointment")
    relations = _index(w.relationships)
    for rivalry in w.rivalries:
        _require(len({rivalry.claimant, rivalry.rival, rivalry.partner}) == 3
                 and all(p in people for p in (rivalry.claimant, rivalry.rival, rivalry.partner))
                 and rivalry.former_relationship in relations and rivalry.current_relationship in relations,
                 "Romantic rivalry requires three real people and two real relationships")
        former, current = relations[rivalry.former_relationship], relations[rivalry.current_relationship]
        _require(former.kind is current.kind is RelationKind.ROMANTIC
                 and set(former.people) == {rivalry.claimant, rivalry.partner}
                 and set(current.people) == {rivalry.rival, rivalry.partner}
                 and former.until is not None and former.until <= current.since and current.until is None,
                 "Rivalry concerns an ended couple and a distinct current couple, not an invented affair")
        disclosed = producer(rivalry.disclosed_by, EventKind.RELATIONSHIP_DISCLOSED,
                             rivalry.partner, rivalry.claimant, current.id)
        refusal = producer(rivalry.refused_by, EventKind.RECONCILIATION_REFUSED,
                           rivalry.partner, rivalry.claimant, rivalry.id)
        _require(current.active_at(disclosed.minute) and disclosed.id in refusal.causes
                 and bool(_related(w, rivalry.claimant, rivalry.rival, RelationKind.ACQUAINTANCES)),
                 "Rival must be personally known and the current relationship actually disclosed before refusal")
    _require(intent.author == roles.author and intent.target == roles.victim, "Intent must match bound roles")
    _require(type(intent.goal) is GoalKind and type(intent.expected_effect) is ExpectedEffect, "Intent and belief must be typed")
    decision = producer(intent.event, EventKind.INTENT_FORMED, intent.author, intent.target, intent.subject)
    _require(len(decision.causes) == 1, "Intent needs its concrete triggering reaction")
    supports = {}
    def witness(requirement, *sources):
        _require(all(source in ids for source in sources), "Requirement support must refer to actual world entities")
        supports[requirement] = RequirementWitness(requirement, tuple(sources))
    a, v = roles.author, roles.victim
    if kernel.premise.motive is Motive.CONTROL:
        relationships = _related(w, a, v, RelationKind.ROMANTIC)
        dependencies = [d for d in w.dependencies if d.controller == a and d.dependent == v and d.id == intent.subject]
        _require(bool(relationships) and len(dependencies) == 1, "Control needs a real romantic relation and resource dependency")
        dep = dependencies[0]
        established = events[dep.established_by]
        _require(any(r.since < established.minute for r in relationships), "Relationship must predate the control")
        reaction = events[decision.causes[0]]
        _require(reaction.kind is EventKind.AUTONOMY_REJECTED and (reaction.actor, reaction.target, reaction.subject) == (a, v, dep.id)
                 and len(reaction.causes) == 1, "Autonomy rejection must concern this dependency and victim")
        autonomy = events[reaction.causes[0]]
        expected = EventKind.SEPARATION_ANNOUNCED if kernel.premise.stake is Stake.SEPARATION else EventKind.REFUSAL_EXPRESSED
        _require(autonomy.kind is expected and (autonomy.actor, autonomy.target) == (v, a), "Victim autonomy event must match the concrete stake")
        if expected is EventKind.SEPARATION_ANNOUNCED:
            _require(autonomy.subject == dep.id and dep.established_by in autonomy.causes, "Separation must follow existing control")
            witness(RequiredFact.SEPARATION_ANNOUNCED, autonomy.id)
        else:
            _require(autonomy.subject in demands, "Refusal needs a real demand")
            demand = demands[autonomy.subject]
            _require((demand.issuer, demand.addressee) == (a, v) and demand.event in autonomy.causes
                     and dep.established_by in events[demand.event].causes, "Refusal must reject the author's demand under existing control")
            witness(RequiredFact.REFUSAL_EXPRESSED, autonomy.id, demand.id)
        _require(intent.goal is GoalKind.DENY_AUTONOMY and intent.expected_effect is ExpectedEffect.DEATH_BLOCKS_AUTONOMY, "Control intent/belief must concern denied autonomy")
        witness(RequiredFact.ROMANTIC_LINK, relationships[0].id)
        witness(RequiredFact.PRIOR_CONTROL, dep.id, dep.resource, dep.established_by)
        witness(RequiredFact.VICTIM_SEEKS_AUTONOMY, autonomy.id)
        witness(RequiredFact.AUTONOMY_REJECTED, reaction.id)
    elif kernel.premise.motive is Motive.REMOVE_OBSTACLE:
        candidates = [r for r in w.rivalries if r.id == intent.subject
                      and (r.claimant, r.rival, r.partner) == (a, v, roles.other)]
        _require(len(candidates) == 1, "Intent needs the actual bound romantic rivalry")
        rivalry = candidates[0]
        reaction = events[decision.causes[0]]
        _require(reaction.kind is EventKind.RIVAL_BLAMED
                 and (reaction.actor, reaction.target, reaction.subject) == (a, v, rivalry.id)
                 and reaction.causes == (rivalry.refused_by,), "Rival blaming follows the actual refusal")
        _require(intent.goal is GoalKind.REMOVE_ROMANTIC_RIVAL
                 and intent.expected_effect is ExpectedEffect.DEATH_REMOVES_RIVAL,
                 "Rivalry intent is the author's belief, not guaranteed reconciliation")
        witness(RequiredFact.ROMANTIC_LINK, rivalry.former_relationship, rivalry.current_relationship)
        witness(RequiredFact.ROMANTIC_RIVAL_EXISTS, rivalry.id, rivalry.disclosed_by)
        witness(RequiredFact.AUTHOR_HAS_GOAL, rivalry.refused_by, decision.id)
        witness(RequiredFact.VICTIM_BLOCKS_GOAL, rivalry.current_relationship, reaction.id)
    elif kernel.premise.motive is Motive.PREDATION:
        _require(not any(set(r.people) == {a, v} for r in w.relationships)
                 and people[a].workplace is not people[v].workplace, "A chance encounter has no shared history: no relationship, no shared workplace")
        candidates = [f for f in w.fixations if f.id == intent.subject and (f.author, f.target) == (a, v)]
        _require(len(candidates) == 1, "Intent needs the actual fixation on this victim")
        fixation = candidates[0]
        noticed = producer(fixation.noticed_by, EventKind.TARGET_NOTICED, a, v, fixation.id)
        _require(noticed.causes == () and noticed.place == people[v].workplace.value, "The victim is first noticed where she works, out of nowhere")
        previous = noticed
        for watch_id in fixation.watches:
            watch = producer(watch_id, EventKind.TARGET_WATCHED, a, v, fixation.id)
            _require(watch.causes == (previous.id,) and watch.place in (people[v].home, people[v].workplace.value), "Each watch follows the previous one, at the victim's home or workplace")
            previous = watch
        _require(fixation.studied == bool(fixation.watches) and decision.causes == (previous.id,), "A studied prey was watched; the decision follows the last sighting")
        _require(intent.goal is GoalKind.SEEK_THE_ACT and intent.expected_effect is ExpectedEffect.DEATH_IS_THE_ACT, "Predation seeks the act itself")
        witness(RequiredFact.NO_SHARED_HISTORY, fixation.id)
        witness(RequiredFact.ACT_SOUGHT, decision.id, noticed.id)
        witness(RequiredFact.DOMINATION_DESIRED if kernel.premise.stake is Stake.DOMINATION else RequiredFact.VIOLENCE_DESIRED, fixation.id, noticed.id)
    else:
        relationships = _related(w, a, v, RelationKind.COLLEAGUES)
        candidates = [d for d in w.disclosures if d.id == intent.subject and d.speaker == v and d.recipient == roles.other]
        _require(bool(relationships) and len(candidates) == 1, "Disclosure needs actual colleagues and an intended recipient")
        disclosure = candidates[0]
        incident = incidents[disclosure.incident]
        _require(incident.perpetrator == a, "Disclosure must implicate this author")
        expected = {Stake.FRAUD: IncidentKind.DIVERTED_WAGES, Stake.EXPLOITATION: IncidentKind.UNPAID_WORK,
                    Stake.PAST_CRIME: IncidentKind.PREVIOUS_THEFT}[kernel.premise.stake]
        _require(incident.kind is expected, "Actual incident must match the concrete stake")
        _require(any(r.since < events[incident.event].minute for r in relationships), "Work relation must precede misconduct")
        reaction = events[decision.causes[0]]
        _require(reaction.kind is EventKind.DISCLOSURE_FEARED and (reaction.actor, reaction.target, reaction.subject) == (a, v, disclosure.id)
                 and reaction.causes == (disclosure.announced_by,), "Disclosure fear must follow the real announcement")
        _require(intent.goal is GoalKind.STOP_DISCLOSURE and intent.expected_effect is ExpectedEffect.DEATH_BLOCKS_DISCLOSURE, "Silencing intent/belief must concern disclosure")
        knowledge = next(k for k in w.knowledge if k.person == v and k.incident == incident.id)
        witness(RequiredFact.WORK_LINK, relationships[0].id)
        witness(RequiredFact.VICTIM_KNOWS_SECRET, incident.id, knowledge.learned_by)
        witness(RequiredFact.DISCLOSURE_POSSIBLE, disclosure.id, disclosure.announced_by)
        witness(RequiredFact.DISCLOSURE_FEARED, reaction.id)
        requirement = {Stake.FRAUD: RequiredFact.FRAUD_EXISTS, Stake.EXPLOITATION: RequiredFact.EXPLOITATION_EXISTS,
                       Stake.PAST_CRIME: RequiredFact.PAST_CRIME_EXISTS}[kernel.premise.stake]
        witness(requirement, incident.id, incident.resource, incident.event)
    witness(RequiredFact.DEATH_EXPECTED_TO_SERVE_GOAL, decision.id)
    _require(set(supports) == set(kernel.premise.required_facts), "Bound facts do not satisfy the entire premise contract")
    return tuple(supports[f] for f in kernel.premise.required_facts)


class KernelBuilder:
    """Construct a fresh small world; reuse of an existing world is not yet added.

    Constructors validate the actual results. Unsupported premises/filter errors
    are detected before drawing anything. No mutation of Game or saved states.
    """
    def __init__(self, seed=42, *, people_count=6):
        if type(people_count) is not int or not 6 <= people_count <= 12:
            raise ValueError("A cast of 6 to 12 people, including the victim")
        self.people_count = people_count
        self.seed = seed
        self.rng = random.Random(seed)

    def sample(self, *, motive=None, context=None, stake=None):
        domain = tuple(p for p in allowed_premises(motive=motive, context=context, stake=stake)
                       if p in SUPPORTED_PREMISES)
        if not domain:
            raise UnsupportedPremise("No implemented kernel for these filters (control, workplace silencing, romantic rivalry or predation)")
        if motive is None and context is None and stake is None:
            # Predation on its own stream: the relational draws below stay exactly as they were.
            chance = random.Random(f"predation-v1:{str(self.seed).split(':retry:')[0]}")  # retries keep the kind of case
            if chance.random() < PREDATION_SHARE:
                stake = Stake.DOMINATION if chance.random() < 0.65 else Stake.VIOLENCE
                return self.build(CrimePremise(Motive.PREDATION, Context.CHANCE_ENCOUNTER, stake))
            domain = tuple(p for p in domain if p.motive is not Motive.PREDATION)
        rng = self.rng
        m = rng.choice(tuple(m for m in Motive if any(p.motive is m for p in domain))) if motive is None else motive
        c = rng.choice(tuple(c for c in Context if any(p.motive is m and p.context is c for p in domain))) if context is None else context
        candidates = tuple(p for p in domain if p.motive is m and p.context is c)
        premise = rng.choice(candidates) if stake is None else candidates[0]
        return self.build(premise)

    def build(self, premise, *, mechanism=None):
        if type(premise) is not CrimePremise:
            raise TypeError("A typed CrimePremise is required")
        if premise not in SUPPORTED_PREMISES:
            raise UnsupportedPremise(f"Kernel not implemented for {premise.as_dict()}")
        if mechanism is not None and (type(mechanism) is not ControlMechanism or premise.motive is not Motive.CONTROL):
            raise ValueError("A control mechanism is only valid for the control branch")
        rng = self.rng
        names = rng.sample(("Oscar", "Lina", "Marius", "Salomé", "Ada", "Bruno", "Chloé", "Farid", "Inès", "Karim", "Nadia", "Tess"), self.people_count)
        people, resources = [], []
        for index, name in enumerate(names):
            place = rng.choice(tuple(Workplace))
            id, home = f"p{index}", f"home{index}"
            income = rng.randrange(12, 31) * 100
            people.append(Person(id, name, rng.choice(JOBS[place]), place, home, income,
                                 income - rng.randrange(3, 8) * 100))
            resources.append(Resource(home, ResourceKind.HOME, id, id, f"Logement de {name}"))
        a, v, other = rng.sample(range(self.people_count), 3)
        roles = Roles(people[a].id, people[v].id, people[other].id)
        neutral = [p.id for p in people if p.id not in (roles.author, roles.victim, roles.other)]
        # Ordinary relationships, authored with the SAME Relationship type as the
        # root's link. These imply neither conflict nor guilt nor an automatic clue.
        relationships = [Relationship("ordinary_friendship", RelationKind.FRIENDS, tuple(neutral[:2]), -500 * DAY),
                         Relationship("ordinary_romance", RelationKind.ROMANTIC, tuple(neutral[1:3]), -250 * DAY)]
        # The ordinary couple lives together half the time, on its own stream so that
        # existing cases keep their draws: a shared home must never point at the culprit.
        housing = random.Random(f"cohabitation-v1:{self.seed}")
        if housing.random() < 0.5:
            x, y = (next(i for i, p in enumerate(people) if p.id == pid) for pid in neutral[1:3])
            resources = [r for r in resources if r.id != people[y].home]
            people[y] = replace(people[y], home=people[x].home)
        # ... and the victim's friend is sometimes their flatmate: someone living with the
        # victim is a lead, never a verdict.
        if housing.random() < 0.35 and premise.motive is not Motive.CONTROL:
            resources = [r for r in resources if r.id != people[other].home]
            people[other] = replace(people[other], home=people[v].home)
        if premise.motive is Motive.CONTROL:
            mechanism = mechanism or rng.choice(tuple(ControlMechanism))
            relationships.extend((Relationship("root_romance", RelationKind.ROMANTIC, (roles.author, roles.victim), -rng.randrange(500, 1000) * DAY),
                                  Relationship("victim_friend", RelationKind.FRIENDS, (roles.victim, roles.other), -400 * DAY)))
            since, autonomy_time = -rng.randrange(40, 180) * DAY + 18 * 60, -rng.randrange(1, 5) * DAY + 19 * 60
            if mechanism is ControlMechanism.FINANCIAL:
                need = rng.randrange(3, 8) * 100
                resource = Resource("controlled_resource", ResourceKind.SUPPORT_BUDGET, roles.author, roles.author,
                                    f"Aide mensuelle de {need} € dont dépend {people[v].name}", need + rng.randrange(0, 4) * 100)
                resources.append(resource)
                people[v] = replace(people[v], monthly_expenses=people[v].monthly_income + need)
                people[a] = replace(people[a], monthly_expenses=people[a].monthly_income - resource.amount)
                dependency = Dependency("dependency", roles.author, roles.victim, mechanism, resource.id, "established", need)
            else:
                original = people[v].home
                resources = [r for r in resources if r.id != original]
                people[v] = replace(people[v], home=people[a].home)
                dependency = Dependency("dependency", roles.author, roles.victim, mechanism, people[a].home, "established")
            events = [Event("established", EventKind.CONTROL_ESTABLISHED, since, roles.author, roles.victim,
                            people[v].home, dependency.id)]
            demands = ()
            if premise.stake is Stake.SEPARATION:
                autonomy = Event("autonomy", EventKind.SEPARATION_ANNOUNCED, autonomy_time, roles.victim,
                                 roles.author, people[v].home, dependency.id, ("established",))
            else:
                kind = rng.choice(tuple(DemandKind))
                demand = Demand("demand", kind, roles.author, roles.victim, "demand_made",
                                roles.other if kind is DemandKind.STOP_SEEING_FRIEND else None)
                demands = (demand,)
                events.append(Event("demand_made", EventKind.DEMAND_MADE, autonomy_time - 60, roles.author,
                                    roles.victim, people[v].home, demand.id, ("established",)))
                autonomy = Event("autonomy", EventKind.REFUSAL_EXPRESSED, autonomy_time, roles.victim,
                                 roles.author, people[v].home, demand.id, ("demand_made",))
            events.extend((autonomy, Event("reaction", EventKind.AUTONOMY_REJECTED, autonomy_time + 30,
                                         roles.author, roles.victim, people[v].home, dependency.id, (autonomy.id,)),
                           Event("decision", EventKind.INTENT_FORMED, autonomy_time + 60, roles.author,
                                 roles.victim, people[a].home, dependency.id, ("reaction",))))
            world = World(tuple(people), tuple(relationships), tuple(resources), tuple(events), (dependency,), demands)
            intent = Intent(roles.author, roles.victim, GoalKind.DENY_AUTONOMY, ExpectedEffect.DEATH_BLOCKS_AUTONOMY, "decision", dependency.id)
        elif premise.motive is Motive.REMOVE_OBSTACLE:
            relationships.extend((
                Relationship("former_couple", RelationKind.ROMANTIC, (roles.author, roles.other), -600 * DAY, -60 * DAY),
                Relationship("current_couple", RelationKind.ROMANTIC, (roles.victim, roles.other), -30 * DAY),
                Relationship("root_acquaintance", RelationKind.ACQUAINTANCES, (roles.author, roles.victim), -100 * DAY),
                Relationship("victim_friend", RelationKind.FRIENDS, (roles.victim, neutral[0]), -200 * DAY),
            ))
            rivalry = RomanticRivalry("rivalry", roles.author, roles.victim, roles.other,
                                     "former_couple", "current_couple", "new_relationship", "refusal")
            announced = -rng.randrange(2, 6) * DAY + 18 * 60
            events = (
                Event("new_relationship", EventKind.RELATIONSHIP_DISCLOSED, announced, roles.other,
                      roles.author, people[other].home, "current_couple"),
                Event("refusal", EventKind.RECONCILIATION_REFUSED, announced + 15, roles.other,
                      roles.author, people[other].home, rivalry.id, ("new_relationship",)),
                Event("reaction", EventKind.RIVAL_BLAMED, announced + 30, roles.author,
                      roles.victim, people[a].home, rivalry.id, ("refusal",)),
                Event("decision", EventKind.INTENT_FORMED, announced + 60, roles.author,
                      roles.victim, people[a].home, rivalry.id, ("reaction",)),
            )
            world = World(tuple(people), tuple(relationships), tuple(resources), events, rivalries=(rivalry,))
            intent = Intent(roles.author, roles.victim, GoalKind.REMOVE_ROMANTIC_RIVAL,
                            ExpectedEffect.DEATH_REMOVES_RIVAL, "decision", rivalry.id)
        elif premise.motive is Motive.PREDATION:
            # A stranger: no relationship, another workplace. Domination is a studied prey
            # (days of watching, which leave traces); violence is a face noticed once.
            if people[a].workplace is people[v].workplace:
                place = rng.choice(tuple(w for w in Workplace if w is not people[v].workplace))
                people[a] = replace(people[a], occupation=rng.choice(JOBS[place]), workplace=place)
            relationships.append(Relationship("victim_friend", RelationKind.FRIENDS, (roles.victim, roles.other), -400 * DAY))
            studied = premise.stake is Stake.DOMINATION
            noticed_at = (-rng.randrange(4, 8) if studied else -rng.randrange(1, 3)) * DAY + 18 * 60
            events = [Event("noticed", EventKind.TARGET_NOTICED, noticed_at, roles.author, roles.victim, people[v].workplace.value, "fixation")]
            if studied:
                for i in range(rng.randrange(2, 4)):
                    place = people[v].home if i % 2 == 0 else people[v].workplace.value
                    events.append(Event(f"watch{i}", EventKind.TARGET_WATCHED, noticed_at + (i + 1) * DAY + rng.randrange(-30, 31),
                                        roles.author, roles.victim, place, "fixation", (events[-1].id,)))
            events.append(Event("decision", EventKind.INTENT_FORMED, events[-1].minute + 60, roles.author, roles.victim,
                                people[a].home, "fixation", (events[-1].id,)))
            fixation = Fixation("fixation", roles.author, roles.victim, "noticed", tuple(e.id for e in events if e.kind is EventKind.TARGET_WATCHED), studied)
            world = World(tuple(people), tuple(relationships), tuple(resources), tuple(events), fixations=(fixation,))
            intent = Intent(roles.author, roles.victim, GoalKind.SEEK_THE_ACT, ExpectedEffect.DEATH_IS_THE_ACT, "decision", "fixation")
        else:
            place = rng.choice(tuple(Workplace))
            people[a] = replace(people[a], occupation=JOBS[place][1], workplace=place)
            people[v] = replace(people[v], occupation=JOBS[place][0], workplace=place)
            people[other] = replace(people[other], occupation=Occupation.ACCOUNTING, workplace=place)
            relationships.append(Relationship("root_colleagues", RelationKind.COLLEAGUES, (roles.author, roles.victim), -600 * DAY))
            kind = {Stake.FRAUD: IncidentKind.DIVERTED_WAGES, Stake.EXPLOITATION: IncidentKind.UNPAID_WORK,
                    Stake.PAST_CRIME: IncidentKind.PREVIOUS_THEFT}[premise.stake]
            affected = roles.other if kind is IncidentKind.PREVIOUS_THEFT else roles.victim
            if kind is IncidentKind.DIVERTED_WAGES:
                amount = rng.randrange(2, people[v].monthly_income // 100) * 100
                resource = Resource("incident_resource", ResourceKind.MONEY, affected, roles.author,
                                    f"{amount} € de rémunération dus à {people[v].name}, détournés par {people[a].name}", amount)
            elif kind is IncidentKind.UNPAID_WORK:
                hours = rng.randrange(12, 41)
                resource = Resource("incident_resource", ResourceKind.LABOR, affected, roles.author,
                                    f"{hours} heures supplémentaires imposées à {people[v].name}, sans rémunération", hours)
            else:
                item = rng.choice(("une montre gravée", "un pendentif en argent", "une bague ancienne"))
                resource = Resource("incident_resource", ResourceKind.VALUABLE, affected, roles.author,
                                    f"{people[a].name} a volé {item} à {people[other].name}", rng.randrange(3, 12) * 100)
            resources.append(resource)
            incident = Incident("incident", kind, roles.author, affected, resource.id, "misconduct")
            incident_time = -rng.randrange(90, 300) * DAY if kind is IncidentKind.PREVIOUS_THEFT else -rng.randrange(10, 40) * DAY
            discovery_time, announcement_time = -rng.randrange(5, 9) * DAY + 10 * 60, -rng.randrange(1, 4) * DAY + 15 * 60
            disclosure = Disclosure("disclosure", roles.victim, roles.other, incident.id, "announcement", rng.randrange(1, 4) * DAY)
            events = (Event("misconduct", EventKind.MISCONDUCT, incident_time, roles.author, affected, place.value, incident.id),
                      Event("discovery", EventKind.DISCOVERY, discovery_time, roles.victim, roles.author, place.value, incident.id, ("misconduct",)),
                      Event("announcement", EventKind.DISCLOSURE_ANNOUNCED, announcement_time, roles.victim, roles.author, place.value, disclosure.id, ("discovery",)),
                      Event("reaction", EventKind.DISCLOSURE_FEARED, announcement_time + 30, roles.author, roles.victim, place.value, disclosure.id, ("announcement",)),
                      Event("decision", EventKind.INTENT_FORMED, announcement_time + 60, roles.author, roles.victim, people[a].home, disclosure.id, ("reaction",)))
            world = World(tuple(people), tuple(relationships), tuple(resources), events, incidents=(incident,),
                          knowledge=(Knowledge(roles.victim, incident.id, "discovery"),), disclosures=(disclosure,))
            intent = Intent(roles.author, roles.victim, GoalKind.STOP_DISCLOSURE, ExpectedEffect.DEATH_BLOCKS_DISCLOSURE, "decision", disclosure.id)
        # Ordinary triangles use the same relationship model and create no intent.
        # In work cases a triangle may concern the victim and two innocents;
        # the killer's workplace motive remains completely separate.
        if rng.random() < .5:
            if premise.motive is Motive.SILENCE:
                extra = (Relationship("background_former_couple", RelationKind.ROMANTIC,
                                      (roles.victim, neutral[0]), -500 * DAY, -100 * DAY),
                         Relationship("background_current_couple", RelationKind.ROMANTIC,
                                      (roles.victim, roles.other), -50 * DAY))
            else:
                extra = (Relationship("background_former_couple", RelationKind.ROMANTIC,
                                      (neutral[0], neutral[2]), -700 * DAY, -300 * DAY),)
            world = replace(world, relationships=world.relationships + extra)
        return CausalKernel(premise, roles, world, intent)


def describe(kernel):
    """Developer-readable private truth. This text is not NPC speech."""
    people, resources = _index(kernel.world.people), _index(kernel.world.resources)
    a, v = people[kernel.roles.author], people[kernel.roles.victim]
    p = kernel.premise
    lines = [f"{RULES[p.motive].label} × {CONTEXTS[p.context].label} → {p.stake.label}",
             f"Auteur : {a.name} — {a.occupation.label}, {a.workplace.label}.",
             f"Victime : {v.name} — {v.occupation.label}, {v.workplace.label}."]
    if p.motive is Motive.CONTROL:
        dep = kernel.world.dependencies[0]
        lines.append(f"Emprise : {dep.mechanism.label}. {resources[dep.resource].description}.")
        if kernel.world.demands:
            lines.append(f"Exigence refusée : {kernel.world.demands[0].kind.label}.")
    elif p.motive is Motive.REMOVE_OBSTACLE:
        partner = people[kernel.roles.other]
        lines.extend((f"Triangle : {partner.name} a quitté {a.name} ; sa relation actuelle est avec {v.name}.",
                      f"{partner.name} a annoncé cette relation et refusé de reprendre le couple avec {a.name}.",
                      f"{a.name} connaît {v.name} et lui attribue ce refus. Rien ne garantit que {partner.name} reviendrait."))
    elif p.motive is Motive.PREDATION:
        fixation = kernel.world.fixations[0]
        lines.append(f"Aucun lien : {a.name} a remarqué {v.name} {'et l’a observée plusieurs jours' if fixation.studied else 'une seule fois'} ({len(fixation.watches)} repérages).")
    else:
        incident = kernel.world.incidents[0]
        disclosure = kernel.world.disclosures[0]
        lines.extend((f"Faute : {resources[incident.resource].description}.",
                      f"{v.name} a découvert cette faute et annonce vouloir en parler à {people[disclosure.recipient].name}."))
    lines.append("Événements (dates relatives, pas encore le trajet du meurtre) :")
    for event in sorted(kernel.world.events, key=lambda e: e.minute):
        day, minute = divmod(event.minute, DAY)
        lines.append(f"  J{day:+d}, {minute // 60:02d} h {minute % 60:02d} · {people[event.actor].name} → {people[event.target].name} : {event.kind.label}.")
    lines.extend((f"Intention : {a.name} veut {kernel.intent.goal.label}. L'effet de la mort est sa croyance, pas une conséquence garantie.",
                  f"Contrat validé : {len(validate_kernel(kernel))}/{len(p.required_facts)} prédicats sur des entités/événements réels.",
                  "Méthode : non choisie. Aucun meurtre exécuté, aucun indice ni témoin ajouté."))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--motive", choices=[m.value for m in Motive])
    parser.add_argument("--context", choices=[c.value for c in Context])
    parser.add_argument("--stake", choices=[s.value for s in Stake])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--requirements", action="store_true", help="Show actual world references supporting each predicate")
    parser.add_argument("--catalogue", action="store_true", help="List implemented kernels, not all abstract premises")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be positive")
    filters = dict(motive=Motive(args.motive) if args.motive else None,
                   context=Context(args.context) if args.context else None,
                   stake=Stake(args.stake) if args.stake else None)
    domain = tuple(p for p in allowed_premises(**filters) if p in SUPPORTED_PREMISES)
    if not domain:
        parser.error("No implemented kernel for these filters (currently romantic control or workplace silencing)")
    if args.catalogue:
        print(json.dumps([p.as_dict() for p in domain], ensure_ascii=False, indent=2))
        return
    builder = KernelBuilder(args.seed)
    kernels = [builder.sample(**filters) for _ in range(args.count)]
    if args.json:
        print(json.dumps([k.as_dict() for k in kernels], ensure_ascii=False, indent=2))
        return
    print(f"Noyau causal V{KERNEL_VERSION} — VÉRITÉ PRIVÉE, stade avant le crime\n")
    for index, kernel in enumerate(kernels, 1):
        print(f"{index:02d}. {describe(kernel)}\n")
        if args.requirements:
            for proof in validate_kernel(kernel):
                print(f"  {proof.requirement.value} ← {', '.join(proof.sources)}")
            print()


if __name__ == "__main__":
    main()
