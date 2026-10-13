"""Step 5: private physical execution, NOT evidence delivered to the player.

Three methods, victim goals, tracking/meetings/fictional poisoned drinks, graph
walks and derived consequences. Standalone map; does not change the game map.
"""
import argparse
import json
import random
from dataclasses import dataclass
from enum import Enum
from heapq import heappop, heappush

from scenario_kernel import (CausalKernel, KernelBuilder, LabelledEnum, ResourceKind,
                             Workplace, _encode, validate_kernel)
from scenario_sampler import CONTEXTS, RULES, Context, Motive, Stake
from scenario_means import (AcquisitionKind, InventoryCheck, Keeper, METHOD_FOR_TOOL, Method,
                            Tool, ToolKind, ToolState, ToolTransfer, TransferKind, access_people,
                            inventory_checks, inventory_observations, inventory_text)
from scenario_victim import (MissedAppointment, PlanReason, VictimGoal, VictimPlan, absence_text,
                             allowed_goals, candidate_plans, missed_appointments, purpose_text, validate_plan)
from scenario_situations import DrinkExposure, SituationKind, VenuePresence, venue_observations


class InvalidCrime(ValueError):
    pass


class NoFeasibleCrime(ValueError):
    pass


class NodeKind(Enum):
    STREET = "street"
    WORKPLACE = "workplace"
    HOME = "home"
    SERVICE = "service"


class Encounter(LabelledEnum):
    AT_EXIT = "at_exit", "à la sortie du travail"
    FOLLOWED = "followed", "sur le trajet de la victime"
    AT_MEETING = "at_meeting", "pendant le rendez-vous convenu"
    AT_VENUE = "at_venue", "pendant la sortie au bar ou au restaurant"


class ToolFate(Enum):
    RETAINED = "retained"
    LEFT_AT_SCENE = "left_at_scene"
    HIDDEN = "hidden"


class TraceKind(Enum):
    BODY = "body"
    VICTIM_BLOOD = "victim_blood"
    METHOD_MARK = "method_mark"
    LEFT_TOOL = "left_tool"
    DRINK = "drink"
    TOXIC_EFFECT = "toxic_effect"


@dataclass(frozen=True)
class Node:
    id: str
    kind: NodeKind
    label: str


@dataclass(frozen=True)
class Edge:
    a: str
    b: str
    minutes: int


@dataclass(frozen=True)
class StreetMap:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]  # undirected; positive integer walking times

    def __post_init__(self):
        check(type(self.nodes) is tuple and type(self.edges) is tuple, "immutable map")
        check(all(type(n) is Node and type(n.kind) is NodeKind
                  and type(n.id) is str and n.id and type(n.label) is str and n.label
                  for n in self.nodes), "typed nodes")
        ids = {n.id for n in self.nodes}
        check(len(ids) == len(self.nodes) and bool(ids), "unique map nodes")
        seen = set()
        for e in self.edges:
            check(type(e) is Edge and e.a in ids and e.b in ids and e.a != e.b
                  and type(e.minutes) is int and e.minutes > 0, "valid walking edge")
            key = frozenset((e.a, e.b))
            check(key not in seen, "unique walking edges")
            seen.add(key)
        adjacency = {id: [] for id in ids}
        for e in self.edges:
            adjacency[e.a].append((e.b, e.minutes))
            adjacency[e.b].append((e.a, e.minutes))
        # Derived read-only caches are deliberately not dataclass/export fields.
        from types import MappingProxyType
        object.__setattr__(self, "_adjacency", MappingProxyType({id: tuple(values) for id, values in adjacency.items()}))
        reached, pending = {self.nodes[0].id}, [self.nodes[0].id]
        while pending:
            for node, _ in self.neighbors(pending.pop()):
                if node not in reached:
                    reached.add(node)
                    pending.append(node)
        check(reached == ids, "connected map")
        # An indoor node is an endpoint, never an accidental public shortcut.
        check(all(len(self.neighbors(n.id)) == 1 and
                  self.kind(self.neighbors(n.id)[0][0]) is NodeKind.STREET
                  for n in self.nodes if n.kind is not NodeKind.STREET), "street entrances")
        paths = {}
        for start in sorted(ids):
            pending, visited = [(0, (start,))], set()
            while pending:
                cost, path = heappop(pending)
                if path[-1] in visited:
                    continue
                visited.add(path[-1])
                paths[start, path[-1]] = path
                for node, duration in self.neighbors(path[-1]):
                    if node not in visited:
                        heappush(pending, (cost + duration, path + (node,)))
        object.__setattr__(self, "_paths", MappingProxyType(paths))

    def kind(self, id):
        return next(n.kind for n in self.nodes if n.id == id)

    def neighbors(self, id):
        return self._adjacency.get(id, ())

    def duration(self, a, b):
        return next((cost for neighbor, cost in self.neighbors(a) if neighbor == b), None)

    def path(self, start, end):
        """Dijkstra with deterministic lexical tie-breaking, not simple-path enumeration."""
        check(start in {n.id for n in self.nodes} and end in {n.id for n in self.nodes},
              "known path endpoints")
        return self._paths[start, end]


@dataclass(frozen=True)
class Walk:
    person: str
    nodes: tuple[str, ...]
    times: tuple[int, ...]


@dataclass(frozen=True)
class Execution:
    method: Method
    tool: str
    acquired_at: int
    encounter: Encounter
    # The journey is intended. The actual victim walk stops at the crime.
    intended_journey: Walk
    approach: Walk
    observation_at: int
    victim_walk: Walk
    following: Walk
    attack_at: int
    death_at: int
    escape: Walk
    tool_fate: ToolFate
    acquisition: AcquisitionKind
    preparation: Walk
    permission_by: str | None = None
    hidden_at: str | None = None
    situation: SituationKind = SituationKind.TRACKING
    exposure: DrinkExposure | None = None


@dataclass(frozen=True)
class MundaneBorrowing:
    tool: str
    actor: str
    outbound: Walk
    inbound: Walk
    permission_by: str


@dataclass(frozen=True)
class WorkplaceDisclosure:
    """Authored background fact, NOT inferred universally from being a couple."""
    speaker: str
    recipient: str
    workplace: Workplace
    minute: int
    relationship: str


@dataclass(frozen=True)
class Trace:
    id: str
    kind: TraceKind
    place: str
    created_at: int
    source: str  # execution event, not a made-up eyewitness
    subject: str  # private true origin; never a public singleton clue
    detail: str


@dataclass(frozen=True)
class ExecutedCrime:
    kernel: CausalKernel
    streets: StreetMap
    inventory: tuple[Tool, ...]
    workplace_disclosure: WorkplaceDisclosure | None
    victim_plan: VictimPlan
    execution: Execution
    traces: tuple[Trace, ...]
    missed_appointments: tuple[MissedAppointment, ...]
    keepers: tuple[Keeper, ...]
    mundane_borrowings: tuple[MundaneBorrowing, ...]
    transfers: tuple[ToolTransfer, ...]
    tool_states: tuple[ToolState, ...]
    inventory_checks: tuple[InventoryCheck, ...]
    venue_presences: tuple[VenuePresence, ...] = ()

    def __post_init__(self):
        validate_crime(self)

    @property
    def scene(self):
        return self.execution.victim_walk.nodes[-1]

    @property
    def method(self):
        return self.execution.method

    def as_dict(self):
        return {"crime_version": 4, "visibility": "private_executed_truth",
                "kernel": self.kernel.as_dict(), "streets": _encode(self.streets),
                "inventory": _encode(self.inventory),
                "workplace_disclosure": _encode(self.workplace_disclosure),
                "victim_plan": _encode(self.victim_plan),
                "execution": _encode(self.execution),
                "traces": _encode(self.traces),
                "missed_appointments": _encode(self.missed_appointments),
                "keepers": _encode(self.keepers), "mundane_borrowings": _encode(self.mundane_borrowings),
                "transfers": _encode(self.transfers), "tool_states": _encode(self.tool_states),
                "inventory_checks": _encode(self.inventory_checks),
                "venue_presences": _encode(self.venue_presences)}


def check(condition, message):
    if not condition:
        raise InvalidCrime(message)


def validate_inventory(kernel, streets, inventory):
    people = {p.id: p for p in kernel.world.people}
    ids = {n.id for n in streets.nodes}
    existing = {obj.id for field in ("people", "relationships", "resources", "events",
                                    "dependencies", "demands", "incidents", "disclosures")
                for obj in getattr(kernel.world, field)}
    check(type(inventory) is tuple and all(type(t) is Tool for t in inventory), "typed inventory")
    check(len({t.id for t in inventory}) == len(inventory), "unique tool IDs")
    for t in inventory:
        check(type(t.id) is str and t.id and t.id not in existing and type(t.kind) is ToolKind
              and t.place in ids and t.point in ids and type(t.available_since) is int and t.available_since < 0
              and type(t.lawful_use) is str and bool(t.lawful_use), "existing lawful tool origin")
        check(type(t.access) is tuple and len(set(t.access)) == len(t.access)
              and all(person in people for person in t.access), "real unique access holders")
        if t.owner in people:
            check(t.place == people[t.owner].home and t.point == t.place
                  and access_people(t) == (t.owner,), "existing lawful tool at owner's home")
        else:
            check(t.owner == t.place and t.owner in ("bar", "restaurant")
                  and streets.kind(t.place) is NodeKind.WORKPLACE
                  and (t.point == t.place or streets.duration(t.place, t.point) is not None)
                  and len(set(t.access) - {kernel.roles.victim}) >= 2,
                  "shared venue tool has an actual pickup point and at least two eligible suspects")


def validate_walk(walk, streets, person):
    check(type(walk) is Walk and walk.person == person and type(walk.nodes) is tuple
          and type(walk.times) is tuple and len(walk.nodes) == len(walk.times) > 0,
          "typed actor walk")
    check(all(node in {n.id for n in streets.nodes} for node in walk.nodes)
          and all(type(t) is int and 0 <= t < 1440 for t in walk.times), "known timed walk")
    for a, b, start, end in zip(walk.nodes, walk.nodes[1:], walk.times, walk.times[1:]):
        duration = streets.duration(a, b)
        check(duration is not None and end - start == duration, "no teleport or impossible walking time")
    check(all(streets.kind(n) is NodeKind.STREET for n in walk.nodes[1:-1]),
          "no indoor transit shortcut")


def consequences(kernel, execution):
    """Deterministic world effects, separate from discovery and interpretation."""
    v = kernel.roles.victim
    scene = execution.victim_walk.nodes[-1]
    mark = "lésion compatible avec une arme blanche" if execution.method is Method.EDGED else "lésion compatible avec un objet contondant (qui écrase sans couper)"
    rows = [Trace("body", TraceKind.BODY, scene, execution.death_at, "death", v, "corps de la victime")]
    if execution.method is Method.POISONED:
        exposure = execution.exposure
        rows.extend((Trace("drink", TraceKind.DRINK, scene, exposure.served_at, exposure.id,
                           v, "verre servi à la victime"),
                     Trace("toxic_effect", TraceKind.TOXIC_EFFECT, scene, execution.death_at,
                           exposure.id, v, "conséquence de l'intoxication fictive, sans blessure sanglante")))
    else:
        rows.extend((
            Trace("blood", TraceKind.VICTIM_BLOOD, scene, execution.attack_at, "attack", v, "sang de la victime"),
            Trace("method_mark", TraceKind.METHOD_MARK, scene, execution.attack_at, "attack", v, mark)))
    if execution.tool_fate is ToolFate.LEFT_AT_SCENE:
        rows.append(Trace("left_tool", TraceKind.LEFT_TOOL, scene, execution.escape.times[0],
                          "tool_left", execution.tool, "objet utilisé laissé sur place"))
    return tuple(rows)


def default_keepers():
    return (Keeper("staff:bar", "bar", "Le barman"),
            Keeper("staff:restaurant", "restaurant", "Le serveur"))


def tool_effects(kernel, inventory, x, mundane, keepers):
    """Ledger/state are derived, never independent random clue decorations."""
    tools = {t.id: t for t in inventory}
    tool, author = tools[x.tool], kernel.roles.author
    moves = [ToolTransfer("weapon_pickup", tool.id, author, x.acquired_at, tool.point,
                          tool.point, TransferKind.ACQUISITION, x.permission_by)]
    final_place = x.victim_walk.nodes[-1] if x.tool_fate is ToolFate.LEFT_AT_SCENE else x.hidden_at if x.tool_fate is ToolFate.HIDDEN else x.escape.nodes[-1]
    final_time = (x.escape.times[0] if x.tool_fate is ToolFate.LEFT_AT_SCENE else
                  x.escape.times[x.escape.nodes.index(x.hidden_at)] if x.tool_fate is ToolFate.HIDDEN else x.escape.times[-1])
    moves.append(ToolTransfer("weapon_disposition", tool.id, author, final_time, tool.point,
                              final_place, TransferKind.DISPOSITION))
    states = {t.id: ToolState(t.id, t.point, None, True) for t in inventory}
    states[tool.id] = ToolState(tool.id, final_place,
                               author if x.tool_fate is ToolFate.RETAINED else None, False,
                               x.tool_fate is ToolFate.HIDDEN)
    for borrowing in mundane:
        other_tool = tools[borrowing.tool]
        moves.extend((ToolTransfer("ordinary_pickup", borrowing.tool, borrowing.actor,
                                   borrowing.outbound.times[-1], other_tool.point, other_tool.point,
                                   TransferKind.INNOCENT_LOAN, borrowing.permission_by),
                      ToolTransfer("ordinary_disposition", borrowing.tool, borrowing.actor,
                                   borrowing.inbound.times[-1], other_tool.point, borrowing.inbound.nodes[-1],
                                   TransferKind.DISPOSITION)))
        states[borrowing.tool] = ToolState(borrowing.tool, borrowing.inbound.nodes[-1], borrowing.actor, False)
    transfers = tuple(sorted(moves, key=lambda move: (move.minute, move.id)))
    return transfers, tuple(states[t.id] for t in inventory), inventory_checks(inventory, keepers, transfers)


def validate_mundane(crime):
    check(type(crime.mundane_borrowings) is tuple and len(crime.mundane_borrowings) <= 1,
          "at most one typed ordinary borrowing in this prototype")
    people = {p.id: p for p in crime.kernel.world.people}
    tools = {t.id: t for t in crime.inventory}
    keepers = {k.id: k for k in crime.keepers}
    for borrowing in crime.mundane_borrowings:
        check(type(borrowing) is MundaneBorrowing and borrowing.actor in people
              and borrowing.actor not in (crime.kernel.roles.author, crime.kernel.roles.victim)
              and borrowing.tool in tools and borrowing.tool != crime.execution.tool,
              "innocent borrows a different real object")
        tool = tools[borrowing.tool]
        check(tool.owner in ("bar", "restaurant") and borrowing.actor in access_people(tool)
              and borrowing.permission_by in keepers and keepers[borrowing.permission_by].place == tool.place,
              "ordinary loan has real access and granting keeper")
        validate_walk(borrowing.outbound, crime.streets, borrowing.actor)
        validate_walk(borrowing.inbound, crime.streets, borrowing.actor)
        check(borrowing.outbound.nodes[0] == people[borrowing.actor].home
              and borrowing.outbound.nodes[-1] == tool.point == borrowing.inbound.nodes[0]
              and borrowing.inbound.nodes[-1] == people[borrowing.actor].home
              and borrowing.inbound.times[0] == borrowing.outbound.times[-1] + 1
              and tool.available_since <= borrowing.outbound.times[-1]
              and borrowing.inbound.times[-1] < 17 * 60
              and keepers[borrowing.permission_by].present_at(borrowing.outbound.times[-1]),
              "ordinary loan follows continuous daytime walks before any evening appointment")


def validate_crime(crime):
    check(type(crime.kernel) is CausalKernel and type(crime.streets) is StreetMap
          and type(crime.execution) is Execution, "typed physical crime")
    validate_kernel(crime.kernel)
    k, m, x = crime.kernel, crime.streets, crime.execution
    # Recheck the map even if deserialization bypassed normal construction.
    StreetMap(m.nodes, m.edges)
    people = {p.id: p for p in k.world.people}
    a, v = people[k.roles.author], people[k.roles.victim]
    check(all(any(n.id == p.home and n.kind is NodeKind.HOME for n in m.nodes)
              and any(n.id == p.workplace.value and n.kind is NodeKind.WORKPLACE for n in m.nodes)
              for p in people.values()), "world homes and workplaces in map")
    validate_inventory(k, m, crime.inventory)
    plan = validate_plan(k, crime.victim_plan)
    destination_kind = {VictimGoal.REPORT_INCIDENT: NodeKind.SERVICE, VictimGoal.MEET_AUTHOR: NodeKind.STREET,
                        VictimGoal.GO_OUT: NodeKind.WORKPLACE}.get(plan.goal, NodeKind.HOME)
    check(any(n.id == plan.destination and n.kind is destination_kind
              for n in m.nodes), "plan destination exists with the correct kind")
    tool = next((t for t in crime.inventory if t.id == x.tool), None)
    check(tool is not None and a.id in access_people(tool) and type(x.method) is Method
          and METHOD_FOR_TOOL[tool.kind] is x.method, "method requires actual accessible tool")
    check(type(x.encounter) is Encounter and type(x.tool_fate) is ToolFate
          and type(x.situation) is SituationKind
          and type(x.acquisition) is AcquisitionKind, "typed execution choices")
    check(all(type(t) is int for t in (x.acquired_at, x.observation_at, x.attack_at, x.death_at)),
          "integer event times")
    for walk, person in ((x.intended_journey, v.id), (x.victim_walk, v.id),
                         (x.preparation, a.id), (x.approach, a.id), (x.following, a.id), (x.escape, a.id)):
        validate_walk(walk, m, person)
    journey = x.intended_journey
    check(journey.nodes[0] == plan.origin and journey.nodes[-1] == plan.destination
          and journey.nodes == m.path(plan.origin, plan.destination)
          and journey.times[-1] == plan.expected_arrival_at and plan.formed_at < journey.times[0],
          "actual journey serves the victim plan at the agreed time")
    check(x.preparation.nodes[0] == a.home and x.preparation.nodes[-1] == x.approach.nodes[0]
          and x.preparation.times[-1] == x.approach.times[0] - 1,
          "continuous preparation before approach")
    check(tool.available_since <= x.acquired_at, "tool available before actual acquisition")
    check(type(crime.keepers) is tuple and crime.keepers == default_keepers(), "real venue keepers with authored shifts")
    keeper = next((k for k in crime.keepers if k.place == tool.owner), None)
    if x.acquisition is AcquisitionKind.OWNED:
        check(tool.owner == a.id and x.preparation.nodes == (a.home,)
              and x.acquired_at == x.preparation.times[-1] and x.permission_by is None,
              "owned tool acquired before departure at home")
    elif x.acquisition in (AcquisitionKind.TAKEN, AcquisitionKind.BORROWED):
        check(keeper is not None and x.preparation.nodes[-1] == tool.point
              and x.acquired_at == x.preparation.times[-1], "venue tool acquired at actual source before departure")
        check((x.acquisition is AcquisitionKind.TAKEN and x.permission_by is None)
              or (x.acquisition is AcquisitionKind.BORROWED and x.permission_by == keeper.id
                  and keeper.present_at(x.acquired_at)), "borrowing requires an actual keeper's permission")
    elif x.situation is SituationKind.VENUE:
        check(keeper is not None and tool.point == crime.scene
              and x.preparation.nodes == (a.home,) and x.permission_by is None
              and x.acquired_at == x.observation_at < x.attack_at,
              "venue opportunistic pickup is on site after observing the victim")
    else:
        check(keeper is not None and x.preparation.nodes == (a.home,) and x.permission_by is None
              and any(node == tool.point and time == x.acquired_at
                      for node, time in zip(x.following.nodes, x.following.times))
              and x.observation_at <= x.acquired_at < x.attack_at,
              "opportunistic pickup is on the observed route, before attack, not a teleport")
    intent = next(e for e in k.world.events if e.id == k.intent.event)
    check(0 <= x.acquired_at and intent.minute < x.acquired_at, "intent precedes preparation on crime day")
    stop = len(x.victim_walk.nodes)
    check(x.victim_walk.nodes == journey.nodes[:stop]
          and x.victim_walk.times == journey.times[:stop] and stop >= 2,
          "actual victim walk is a prefix of the planned journey")
    if x.situation is SituationKind.TRACKING:
        disclosure = crime.workplace_disclosure
        if k.world.fixations:
            # A stranger knows the exit because he noticed her there: the fixation, not a confidence.
            check(disclosure is None and k.world.fixations[0].target == v.id, "a stalker learns the workplace by watching, never by confidence")
        else:
            check(type(disclosure) is WorkplaceDisclosure, "typed workplace disclosure")
            relationship = next((r for r in k.world.relationships if r.id == disclosure.relationship), None)
            check(relationship is not None and set(relationship.people) == {a.id, v.id}
                  and disclosure.speaker == v.id and disclosure.recipient == a.id
                  and disclosure.workplace is v.workplace and type(disclosure.minute) is int
                  and relationship.since < disclosure.minute < intent.minute,
                  "author knows workplace through an actual prior disclosure, not omniscience")
        check(plan.origin == v.workplace.value and x.approach.nodes[-1] == journey.nodes[1]
              and x.approach.times[-1] <= x.observation_at and x.observation_at == journey.times[1],
              "author observes victim at actual outdoor exit")
        check(x.following.nodes == x.victim_walk.nodes[1:]
              and x.following.times == x.victim_walk.times[1:], "following is co-present, not a magic interception")
        check((x.encounter is Encounter.AT_EXIT and stop == 2)
              or (x.encounter is Encounter.FOLLOWED and stop > 2), "encounter matches route")
        check(x.method is not Method.POISONED and m.kind(crime.scene) is NodeKind.STREET
              and x.attack_at == x.victim_walk.times[-1] and x.death_at == x.attack_at + 1,
              "outdoor attack and resulting death")
        check(x.exposure is None and crime.venue_presences == (), "tracking cannot invent a venue exposure")
    else:
        check(crime.workplace_disclosure is None and x.victim_walk == journey
              and x.observation_at == journey.times[-1] and x.approach.nodes[-1] == crime.scene
              and x.approach.times[-1] <= x.observation_at
              and x.following == Walk(a.id, (crime.scene,), (x.observation_at,))
              and 3 <= x.attack_at - x.observation_at <= 15,
              "social encounter requires actual arrival and co-presence, not workplace tracking")
        if x.situation is SituationKind.AGREED_MEETING:
            check(plan.goal is VictimGoal.MEET_AUTHOR and x.encounter is Encounter.AT_MEETING
                  and m.kind(crime.scene) is NodeKind.STREET and x.method is not Method.POISONED
                  and x.death_at == x.attack_at + 1 and x.exposure is None
                  and crime.venue_presences == () and plan.appointment.host == a.id
                  and plan.appointment.host_present_from <= x.approach.times[-1]
                  and x.death_at <= plan.appointment.host_present_until,
                  "meeting needs a real agreement and host physically present at the outdoor meeting")
        else:
            validate_venue(crime)
    escape_after = x.attack_at if x.method is Method.POISONED else x.death_at
    check(x.escape.nodes[0] == crime.scene and x.escape.nodes[-1] == a.home
          and x.escape.times[0] == escape_after + 1, "continuous escape after death or fictional exposure")
    check((x.tool_fate is ToolFate.HIDDEN and x.hidden_at in x.escape.nodes)
          or (x.tool_fate is not ToolFate.HIDDEN and x.hidden_at is None), "hiding must occur on actual escape route")
    check(all(d.scheduled_for > x.death_at for d in k.world.disclosures), "death before planned disclosure")
    check(type(crime.traces) is tuple and all(type(t) is Trace for t in crime.traces)
          and crime.traces == consequences(k, x), "consequences must derive exactly from execution")
    check(type(crime.missed_appointments) is tuple
          and crime.missed_appointments == missed_appointments(plan, x.victim_walk, x.death_at),
          "missed appointment derives from agreed meeting, actual absence and waiting host")
    validate_mundane(crime)
    transfers, states, checks = tool_effects(k, crime.inventory, x, crime.mundane_borrowings, crime.keepers)
    check(crime.transfers == transfers and type(crime.transfers) is tuple, "object transfers derive exactly from actual acquisitions and travel")
    check(crime.tool_states == states and type(crime.tool_states) is tuple, "conservation of objects and custody")
    check(crime.inventory_checks == checks and type(crime.inventory_checks) is tuple
          and all(keeper.present_at(check.observed_at) for check in checks for keeper in crime.keepers if keeper.id == check.keeper),
          "inventory observations derive from real missing stock at a keeper's check")
    return crime


def validate_venue(crime):
    """Fictional drink event, delayed effect, at least two physically present access holders."""
    x, plan, kernel = crime.execution, crime.victim_plan, crime.kernel
    check(x.situation is SituationKind.VENUE and x.encounter is Encounter.AT_VENUE
          and x.method is Method.POISONED and plan.goal is VictimGoal.GO_OUT
          and crime.scene == plan.destination and crime.scene in ("bar", "restaurant"),
          "fictional poisoning belongs to an actual bar/restaurant outing")
    exposure = x.exposure
    check(type(exposure) is DrinkExposure and exposure.id == "victim_drink"
          and exposure.recipient == kernel.roles.victim and exposure.place == crime.scene
          and exposure.served_by == f"staff:{crime.scene}"
          and exposure.served_at == x.observation_at + 1 and exposure.altered_at == x.attack_at
          and exposure.effect_at == x.death_at and 10 <= x.death_at - x.attack_at <= 40,
          "fictional drink exposure is served before alteration, with a delayed effect")
    keeper = next(k for k in crime.keepers if k.id == exposure.served_by)
    check(keeper.present_at(exposure.served_at), "drink requires a present server")
    people = {p.id: p for p in kernel.world.people}
    check(type(crime.venue_presences) is tuple and len(crime.venue_presences) == 2
          and len({p.person for p in crime.venue_presences}) == 2,
          "venue has two distinct real access holders, not a single suspect")
    for presence in crime.venue_presences:
        check(type(presence) is VenuePresence and presence.person in people
              and presence.person != kernel.roles.victim and presence.place == crime.scene
              and type(presence.until) is int and bool(presence.purpose), "real venue presence")
        validate_walk(presence.arrival, crime.streets, presence.person)
        check(presence.arrival.nodes[0] == (x.approach.nodes[0] if presence.person == kernel.roles.author
                                          else people[presence.person].home)
              and presence.arrival.nodes[-1] == crime.scene
              and presence.arrival.times[-1] <= x.attack_at <= presence.until < 1440,
              "drink access holder must physically arrive and remain during the event")
        if presence.person == kernel.roles.author:
            check(presence.arrival == x.approach and presence.until == x.escape.times[0],
                  "author venue presence derives from actual preparation and approach")
        for loan in crime.mundane_borrowings:
            if loan.actor == presence.person:
                start = x.preparation.times[0] if presence.person == kernel.roles.author else presence.arrival.times[0]
                check(loan.inbound.times[-1] <= start, "ordinary loan cannot overlap venue travel")
    check(type(exposure.access_people) is tuple and len(set(exposure.access_people)) >= 2
          and set(exposure.access_people) == {p.person for p in crime.venue_presences}
          and kernel.roles.author in exposure.access_people, "drink artifact has at least two actual access possibilities")


def make_walk(person, nodes, start, streets):
    times = [start]
    for a, b in zip(nodes, nodes[1:]):
        duration = streets.duration(a, b)
        check(duration is not None, "known walking edge")
        times.append(times[-1] + duration)
    return Walk(person, tuple(nodes), tuple(times))


class CrimeBuilder:
    def __init__(self, seed=42):
        self.seed = seed
        self.rng = random.Random(seed)

    def prepare(self, kernel):
        """Add neutral means/map before knowing which method will be selected."""
        validate_kernel(kernel)
        streets = ("alley", "crime_scene", "victim_street", "promenade")
        labels = ("Ruelle du Palace", "Place des Enseignes", "Rue Verlaine", "Promenade du Canal")
        nodes = [Node(id, NodeKind.STREET, label) for id, label in zip(streets, labels)]
        edges = [Edge(streets[i], streets[(i + 1) % 4], self.rng.randint(3, 7)) for i in range(4)]
        for i, workplace in enumerate(Workplace):
            nodes.append(Node(workplace.value, NodeKind.WORKPLACE, workplace.label))
            edges.append(Edge(workplace.value, streets[i % len(streets)], 1))
        homes = [r for r in kernel.world.resources if r.kind is ResourceKind.HOME]
        for home in homes:
            nodes.append(Node(home.id, NodeKind.HOME, home.description))
            edges.append(Edge(home.id, self.rng.choice(streets), 1))
        nodes.append(Node("police", NodeKind.SERVICE, "Le Commissariat"))
        edges.append(Edge("police", "promenade", 1))
        inventory = []
        for person in kernel.world.people:
            # Ordinary tools also belong to innocents. Presence is not guilt.
            kinds = self.rng.sample((ToolKind.KITCHEN_KNIFE, ToolKind.HAMMER), self.rng.randint(1, 2))
            if self.rng.random() < .5:
                kinds.append(ToolKind.FICTIONAL_AGENT)
            for kind in kinds:
                use = {ToolKind.KITCHEN_KNIFE: "préparation des repas", ToolKind.HAMMER: "petits travaux domestiques",
                       ToolKind.FICTIONAL_AGENT: "entretien domestique, produit entièrement fictif"}[kind]
                inventory.append(Tool(f"{person.id}_{kind.value}", kind, person.id, person.home,
                                      -30 * 1440, use))
        for venue in ("bar", "restaurant"):
            entrance = next(e.b for e in edges if e.a == venue)
            for number, kind in enumerate((ToolKind.KITCHEN_KNIFE, ToolKind.KITCHEN_KNIFE,
                                            ToolKind.KITCHEN_KNIFE, ToolKind.HAMMER, ToolKind.HAMMER,
                                            ToolKind.FICTIONAL_AGENT, ToolKind.FICTIONAL_AGENT)):
                point = venue if number in (0, 3, 5, 6) else entrance
                use = ("préparation et service des repas" if kind is ToolKind.KITCHEN_KNIFE
                       else "entretien du mobilier")
                if kind is ToolKind.FICTIONAL_AGENT:
                    use = "entretien du lieu, produit entièrement fictif"
                # Shared front-of-house objects, not magically unlocked kitchens.
                inventory.append(Tool(f"{venue}_{kind.value}_{number}", kind, venue, venue,
                                      -30 * 1440, use, tuple(p.id for p in kernel.world.people), point))
        return StreetMap(tuple(nodes), tuple(edges)), tuple(inventory)

    def execute(self, kernel, streets, inventory, *, method=None, encounter=None, fate=None,
                goal=None, plan=None, acquisition=None, mundane=None, source_place=None, situation=None):
        """Never alter existing truth to satisfy a forced method or encounter."""
        validate_kernel(kernel)
        check(type(streets) is StreetMap, "typed map")
        StreetMap(streets.nodes, streets.edges)
        validate_inventory(kernel, streets, inventory)
        for value, enum in ((method, Method), (encounter, Encounter), (fate, ToolFate),
                            (goal, VictimGoal), (acquisition, AcquisitionKind), (situation, SituationKind)):
            if value is not None and type(value) is not enum:
                raise TypeError(f"expected {enum.__name__}")
        if mundane is not None and type(mundane) is not bool:
            raise TypeError("mundane must be bool or None")
        if source_place is not None and type(source_place) is not str:
            raise TypeError("source_place must be a place ID or home")
        keepers = default_keepers()
        people = {p.id: p for p in kernel.world.people}
        a, v = people[kernel.roles.author], people[kernel.roles.victim]
        plans = (validate_plan(kernel, plan),) if plan is not None else candidate_plans(kernel, goal=goal)
        if plan is not None and goal is not None and plan.goal is not goal:
            raise NoFeasibleCrime("Pinned victim plan conflicts with requested goal")
        domain = []
        for victim_plan in plans:
            if victim_plan.goal in (VictimGoal.MEET_AUTHOR, VictimGoal.GO_OUT):
                domain.extend(self._social_options(kernel, streets, inventory, victim_plan,
                    method, encounter, acquisition, mundane, source_place, situation))
                continue
            if situation not in (None, SituationKind.TRACKING):
                continue
            destination_kind = NodeKind.SERVICE if victim_plan.goal is VictimGoal.REPORT_INCIDENT else NodeKind.HOME
            if not any(n.id == victim_plan.destination and n.kind is destination_kind for n in streets.nodes):
                continue
            route = streets.path(victim_plan.origin, victim_plan.destination)
            offsets = make_walk(v.id, route, 0, streets).times
            departure = victim_plan.expected_arrival_at - offsets[-1]
            if not (17 * 60 <= departure <= 21 * 60 and victim_plan.formed_at < departure):
                continue
            for tool in inventory:
                if METHOD_FOR_TOOL[tool.kind] is Method.POISONED:
                    continue
                if a.id not in access_people(tool) or (method is not None and METHOD_FOR_TOOL[tool.kind] is not method):
                    continue
                if mundane is True and not self._ordinary_choices(kernel, streets, inventory, tool.id):
                    continue
                if source_place is not None and not (tool.owner == a.id if source_place == "home" else tool.place == source_place):
                    continue
                for index, place in enumerate(route[1:], 1):
                    if streets.kind(place) is not NodeKind.STREET:
                        continue
                    mode = Encounter.AT_EXIT if index == 1 else Encounter.FOLLOWED
                    if encounter is not None and mode is not encounter:
                        continue
                    escape_nodes = streets.path(place, a.home)
                    escape_duration = sum(streets.duration(u, w) for u, w in zip(escape_nodes, escape_nodes[1:]))
                    death = departure + offsets[index] + 1
                    if not (death + 1 + escape_duration < 1440 and all(d.scheduled_for > death for d in kernel.world.disclosures)):
                        continue
                    kinds = (AcquisitionKind.OWNED,) if tool.owner == a.id else tuple(
                        kind for kind in AcquisitionKind if kind is not AcquisitionKind.OWNED
                    ) if tool.owner in ("bar", "restaurant") else ()
                    for source in kinds:
                        if acquisition is not None and source is not acquisition:
                            continue
                        if source is AcquisitionKind.OPPORTUNISTIC:
                            pickup = next((i for i in range(1, index) if route[i] == tool.point), None)
                            if pickup is None:
                                continue
                            approach_nodes = streets.path(a.home, route[1])
                            prep_nodes = (a.home,)
                        else:
                            pickup = None
                            approach_nodes = streets.path(tool.point, route[1])
                            prep_nodes = streets.path(a.home, tool.point)
                        approach_cost = sum(streets.duration(u, w) for u, w in zip(approach_nodes, approach_nodes[1:]))
                        prep_cost = sum(streets.duration(u, w) for u, w in zip(prep_nodes, prep_nodes[1:]))
                        keeper = next((k for k in keepers if k.place == tool.place), None)
                        waits = []
                        for wait in range(2, 21):
                            pickup_time = (departure + offsets[pickup] if pickup is not None else
                                           departure + offsets[1] - wait - approach_cost - 1)
                            if (departure + offsets[1] - wait - approach_cost - 1 - prep_cost >= 0
                                    and tool.available_since <= pickup_time
                                    and (source is not AcquisitionKind.BORROWED
                                         or keeper is not None and keeper.present_at(pickup_time))):
                                waits.append(wait)
                        if not waits:
                            continue
                        domain.append((tool, index, mode, victim_plan, departure, route,
                                       approach_nodes, prep_nodes, source, pickup, tuple(waits), SituationKind.TRACKING, ((0, 1),)))
        if not domain:
            raise NoFeasibleCrime("No compatible victim plan / existing tool / outdoor encounter; truth unchanged")
        # Situation first: adding many route/stock variants cannot make stalking
        # drown out the structurally different meeting and venue branches.
        selected_situation = situation or self.rng.choice(tuple(s for s in SituationKind if any(row[11] is s for row in domain)))
        domain = [row for row in domain if row[11] is selected_situation]
        # Goal -> reason -> concrete plan before weapon and meeting point. Route
        # length / number of arrival slots must not bias the victim's goal.
        available_plans = tuple(dict.fromkeys(row[3] for row in domain))
        selected_goal = goal or self.rng.choice(tuple(g for g in VictimGoal if any(p.goal is g for p in available_plans)))
        reasons = tuple(r for r in PlanReason if any(p.goal is selected_goal and p.reason is r for p in available_plans))
        reason = self.rng.choice(reasons)
        selected_plan = self.rng.choice(tuple(p for p in available_plans if p.goal is selected_goal and p.reason is reason))
        domain = [row for row in domain if row[3] == selected_plan]
        methods = tuple(m for m in Method if any(METHOD_FOR_TOOL[row[0].kind] is m for row in domain))
        chosen = method or self.rng.choice(methods)
        domain = [row for row in domain if METHOD_FOR_TOOL[row[0].kind] is chosen]
        sources = tuple(kind for kind in AcquisitionKind if any(row[8] is kind for row in domain))
        selected_source = acquisition or self.rng.choice(sources)
        rows = [row for row in domain if row[8] is selected_source]
        picked = self.rng.choice(rows)
        # Someone who works where a tool is kept reaches for it more often than a visitor
        # would: the "who works here?" lead is then worth following, without being proof.
        at_work = [row for row in rows if row[0].owner in ("bar", "restaurant") and row[0].owner == a.workplace.value]
        if at_work and random.Random(f"workplace-tool-v1:{self.seed}").random() < .7:
            picked = random.Random(f"workplace-tool-v1:{self.seed}:row").choice(at_work)
        tool, index, mode, selected_plan, departure, route, approach_nodes, prep_nodes, source, pickup, waits, selected_situation, outcomes = picked
        duration = sum(streets.duration(u, w) for u, w in zip(approach_nodes, approach_nodes[1:]))
        routine = make_walk(v.id, route, departure, streets)
        observation = routine.times[1] if selected_situation is SituationKind.TRACKING else routine.times[-1]
        approach = make_walk(a.id, approach_nodes, observation - self.rng.choice(waits) - duration, streets)
        prep_cost = sum(streets.duration(u, w) for u, w in zip(prep_nodes, prep_nodes[1:]))
        preparation = make_walk(a.id, prep_nodes, approach.times[0] - 1 - prep_cost, streets)
        acquired_at = routine.times[pickup] if pickup is not None else preparation.times[-1]
        victim = Walk(v.id, routine.nodes[:index + 1], routine.times[:index + 1])
        following = (Walk(a.id, victim.nodes[1:], victim.times[1:]) if selected_situation is SituationKind.TRACKING
                     else Walk(a.id, (victim.nodes[-1],), (observation,)))
        linger, effect_delay = self.rng.choice(outcomes)
        attack = victim.times[-1] + linger
        death = attack + effect_delay
        escape = make_walk(a.id, streets.path(victim.nodes[-1], a.home), attack + (1 if chosen is Method.POISONED else 2), streets)
        selected_fate = fate or self.rng.choice(list(ToolFate))
        hidden_at = self.rng.choice(escape.nodes) if selected_fate is ToolFate.HIDDEN else None
        permission = f"staff:{tool.place}" if source is AcquisitionKind.BORROWED else None
        exposure, presences = None, ()
        if selected_situation is SituationKind.VENUE:
            innocent = self.rng.choice(tuple(p for p in kernel.world.people if p.id not in (a.id, v.id)))
            path = streets.path(innocent.home, victim.nodes[-1])
            cost = sum(streets.duration(u, w) for u, w in zip(path, path[1:]))
            visit = make_walk(innocent.id, path, observation - 10 - cost, streets)
            presences = (VenuePresence(a.id, victim.nodes[-1], approach, escape.times[0], "prendre un verre ou un repas"),
                         VenuePresence(innocent.id, victim.nodes[-1], visit, observation + 45, "prendre un verre ou un repas"))
            exposure = DrinkExposure("victim_drink", v.id, victim.nodes[-1], f"staff:{victim.nodes[-1]}",
                                     observation + 1, attack, death, (a.id, innocent.id))
        execution = Execution(chosen, tool.id, acquired_at, mode, routine,
                              approach, observation, victim, following, attack, death,
                              escape, selected_fate, source, preparation, permission, hidden_at,
                              selected_situation, exposure)
        disclosure = None
        if selected_situation is SituationKind.TRACKING and not kernel.world.fixations:
            relationship = next(r for r in kernel.world.relationships if set(r.people) == {a.id, v.id})
            disclosure = WorkplaceDisclosure(v.id, a.id, v.workplace, relationship.since + 1, relationship.id)
        ordinary = self._ordinary_loan(kernel, streets, inventory, tool.id, mundane)
        transfers, states, checks = tool_effects(kernel, inventory, execution, ordinary, keepers)
        return ExecutedCrime(kernel, streets, inventory, disclosure, selected_plan, execution,
                             consequences(kernel, execution), missed_appointments(selected_plan, victim, death),
                             keepers, ordinary, transfers, states, checks, presences)

    def _social_options(self, kernel, streets, inventory, plan, method, encounter, acquisition,
                        mundane, source_place, situation):
        kind = SituationKind.VENUE if plan.goal is VictimGoal.GO_OUT else SituationKind.AGREED_MEETING
        mode = Encounter.AT_VENUE if kind is SituationKind.VENUE else Encounter.AT_MEETING
        if situation not in (None, kind) or encounter not in (None, mode):
            return []
        if not any(n.id == plan.destination and n.kind is (NodeKind.WORKPLACE if kind is SituationKind.VENUE
                                                         else NodeKind.STREET) for n in streets.nodes):
            return []
        people = {p.id: p for p in kernel.world.people}
        a, v = people[kernel.roles.author], people[kernel.roles.victim]
        route = streets.path(plan.origin, plan.destination)
        offsets = make_walk(v.id, route, 0, streets).times
        departure = plan.expected_arrival_at - offsets[-1]
        if not (17 * 60 <= departure <= 21 * 60 and plan.formed_at < departure):
            return []
        escape_nodes = streets.path(plan.destination, a.home)
        escape_cost = sum(streets.duration(u, w) for u, w in zip(escape_nodes, escape_nodes[1:]))
        outcomes = tuple((linger, delay) for linger in (3, 8, 15)
                         for delay in ((10, 20, 40) if kind is SituationKind.VENUE else (1,))
                         if all(d.scheduled_for > plan.expected_arrival_at + linger + delay for d in kernel.world.disclosures)
                         and plan.expected_arrival_at + linger + delay < 1440
                         and plan.expected_arrival_at + linger + (1 if kind is SituationKind.VENUE else 2) + escape_cost < 1440)
        if not outcomes:
            return []
        results = []
        for tool in inventory:
            poison = METHOD_FOR_TOOL[tool.kind] is Method.POISONED
            if poison != (kind is SituationKind.VENUE) or a.id not in access_people(tool):
                continue
            if method is not None and METHOD_FOR_TOOL[tool.kind] is not method:
                continue
            if source_place is not None and not (tool.owner == a.id if source_place == "home" else tool.place == source_place):
                continue
            if mundane is True and not self._ordinary_choices(kernel, streets, inventory, tool.id):
                continue
            sources = ((AcquisitionKind.OWNED,) if tool.owner == a.id else
                       (AcquisitionKind.TAKEN, AcquisitionKind.BORROWED, AcquisitionKind.OPPORTUNISTIC)
                       if tool.owner in ("bar", "restaurant") else ())
            for source in sources:
                if acquisition is not None and source is not acquisition:
                    continue
                if source is AcquisitionKind.OPPORTUNISTIC:
                    if kind is not SituationKind.VENUE or tool.point != plan.destination:
                        continue
                    prep_nodes, approach_nodes, pickup = (a.home,), streets.path(a.home, plan.destination), len(route) - 1
                else:
                    prep_nodes, approach_nodes, pickup = streets.path(a.home, tool.point), streets.path(tool.point, plan.destination), None
                cost = sum(streets.duration(u, w) for u, w in zip(approach_nodes, approach_nodes[1:]))
                prep_cost = sum(streets.duration(u, w) for u, w in zip(prep_nodes, prep_nodes[1:]))
                keeper = next((k for k in default_keepers() if k.place == tool.place), None)
                waits = tuple(wait for wait in range(2, 21)
                    if plan.expected_arrival_at - wait - cost - 1 - prep_cost >= 0
                    and tool.available_since <= (plan.expected_arrival_at if pickup is not None else plan.expected_arrival_at - wait - cost - 1)
                    and (source is not AcquisitionKind.BORROWED or keeper is not None and keeper.present_at(plan.expected_arrival_at - wait - cost - 1)))
                if waits:
                    results.append((tool, len(route) - 1, mode, plan, departure, route,
                                    approach_nodes, prep_nodes, source, pickup, waits, kind, outcomes))
        return results

    def _ordinary_choices(self, kernel, streets, inventory, weapon):
        """Pure feasibility domain, also used before a forced loan consumes RNG."""
        choices = []
        for tool in inventory:
            if tool.id == weapon or tool.owner not in ("bar", "restaurant") or tool.available_since > 12 * 60:
                continue
            for person in kernel.world.people:
                if person.id in (kernel.roles.author, kernel.roles.victim) or person.id not in access_people(tool):
                    continue
                path = streets.path(person.home, tool.point)
                cost = sum(streets.duration(u, w) for u, w in zip(path, path[1:]))
                if 0 <= 12 * 60 - cost and 12 * 60 + 1 + cost < 17 * 60:
                    choices.append((tool, person, path, cost))
        return choices

    def _ordinary_loan(self, kernel, streets, inventory, weapon, force):
        if force is False or (force is None and self.rng.random() >= .35):
            return ()
        choices = self._ordinary_choices(kernel, streets, inventory, weapon)
        if not choices:
            if force:
                raise NoFeasibleCrime("No feasible independent ordinary loan")
            return ()
        tool, person, path, cost = self.rng.choice(choices)
        # The people who work where the tool is kept borrow it more often than visitors:
        # a missing object is a lead toward the team, and sometimes an honest false one.
        at_work = [row for row in choices if row[1].workplace.value == row[0].owner]
        if at_work and random.Random(f"workplace-loan-v1:{self.seed}").random() < .7:
            tool, person, path, cost = random.Random(f"workplace-loan-v1:{self.seed}:row").choice(at_work)
        outward = make_walk(person.id, path, 12 * 60 - cost, streets)
        inward = make_walk(person.id, tuple(reversed(path)), 12 * 60 + 1, streets)
        return (MundaneBorrowing(tool.id, person.id, outward, inward, f"staff:{tool.place}"),)

    def build(self, kernel, **choices):
        for name, enum in (("method", Method), ("encounter", Encounter), ("fate", ToolFate),
                           ("goal", VictimGoal), ("acquisition", AcquisitionKind), ("situation", SituationKind)):
            if choices.get(name) is not None and type(choices[name]) is not enum:
                raise TypeError(f"expected {enum.__name__}")
        if choices.get("mundane") is not None and type(choices["mundane"]) is not bool:
            raise TypeError("mundane must be bool or None")
        if choices.get("source_place") is not None and type(choices["source_place"]) is not str:
            raise TypeError("source_place must be a place ID or home")
        streets, inventory = self.prepare(kernel)
        return self.execute(kernel, streets, inventory, **choices)


def describe(crime):
    people = {p.id: p for p in crime.kernel.world.people}
    labels = {n.id: n.label for n in crime.streets.nodes}
    x = crime.execution
    clock = lambda t: f"{t // 60:02d} h {t % 60:02d}"
    a, v = people[crime.kernel.roles.author], people[crime.kernel.roles.victim]
    tool = next(t for t in crime.inventory if t.id == x.tool)
    route = " → ".join(labels[n] for n in x.victim_walk.nodes)
    premise = crime.kernel.premise
    fate = "laissé sur place" if x.tool_fate is ToolFate.LEFT_AT_SCENE else "conservé par l'auteur"
    if x.tool_fate is ToolFate.HIDDEN:
        fate = "caché pendant la fuite, " + labels[x.hidden_at]
    plan = crime.victim_plan
    intended = " → ".join(labels[n] for n in x.intended_journey.nodes)
    near_destination = " (devant " + labels[plan.destination] + ")" if crime.scene == x.intended_journey.nodes[-2] else ""
    if x.situation is SituationKind.TRACKING:
        arrival_text = f"{clock(x.approach.times[-1])} · {a.name} arrive devant {v.workplace.label} et attend."
        observation_text = f"{clock(x.observation_at)} · {v.name} sort du travail ; {a.name} observe sa sortie. Le plan de la victime ne lui a pas été communiqué."
    elif x.situation is SituationKind.AGREED_MEETING:
        arrival_text = f"{clock(x.approach.times[-1])} · {a.name} rejoint le rendez-vous, {labels[crime.scene]}."
        observation_text = f"{clock(x.observation_at)} · {v.name} arrive depuis chez soi. Le lieu et l'heure ont été convenus par les deux personnes ; elles commencent à discuter."
    else:
        arrival_text = f"{clock(x.approach.times[-1])} · {a.name} est sur place, {labels[crime.scene]}."
        observation_text = f"{clock(x.observation_at)} · {v.name} arrive depuis chez soi pour sa sortie. {a.name} remarque sa présence ; aucun plan privé ne lui a été transmis."
    lines = [
        f"{RULES[premise.motive].label} × {CONTEXTS[premise.context].label} → {premise.stake.label}",
        f"{a.name} veut {crime.kernel.intent.goal.label} ; victime : {v.name}.",
        f"Situation : {x.situation.label}.",
        f"Objectif de {v.name} : {purpose_text(plan, people, crime.kernel)}. Arrivée prévue : {clock(plan.expected_arrival_at)}, {labels[plan.destination]}.",
        f"Trajet prévu : {intended}.",
        f"Moyen déjà disponible : {tool.kind.label}, pour {tool.lawful_use}, {labels[tool.place]}.",
        f"Provenance : {x.acquisition.label}. Prise à {clock(x.acquired_at)}, {labels[tool.point]}.",
        arrival_text,
        observation_text,
        f"Trajet effectif : {route}.",
        f"{clock(x.attack_at)} · Crime {x.encounter.label}, {labels[crime.scene]}{near_destination}, avec {x.method.label}.",
    ]
    aftermath = [(x.death_at, f"La victime meurt {'sur place, après un délai fictif ; aucune trace de sang' if x.method is Method.POISONED else '; son projet est interrompu'}."),
                 (x.escape.times[-1], f"L'auteur rentre chez soi. Objet {fate}.")]
    if x.exposure:
        aftermath.append((x.exposure.served_at, "Le personnel sert une boisson à la victime."))
        # Put serving before administration in the chronology, not after death.
        lines.insert(-1, f"{clock(x.exposure.served_at)} · Le personnel sert une boisson à la victime.")
        aftermath = [event for event in aftermath if event[0] != x.exposure.served_at]
        access_names = ", ".join(people[p].name for p in x.exposure.access_people)
        lines.append(f"Accès privé à la boisson : {access_names}, réellement sur place. Cela ne certifie pas qui l'a altérée.")
    lines.extend(f"{clock(time)} · {text}" for time, text in sorted(aftermath))
    lines.append("Conséquences privées : " + ", ".join(t.detail for t in crime.traces) + ".")
    if crime.kernel.world.rivalries:
        partner = people[crime.kernel.roles.other]
        lines.insert(2, f"Triangle causal : {partner.name} est l'ancien partenaire de {a.name} et le partenaire actuel de {v.name}. La réconciliation a été refusée.")
    for missed in crime.missed_appointments:
        lines.append(f"{clock(missed.observed_at)} · {people[missed.observer].name} constate le rendez-vous manqué : « {absence_text(plan, people)} »")
    for borrowing in crime.mundane_borrowings:
        ordinary_tool = next(t for t in crime.inventory if t.id == borrowing.tool)
        lines.append(f"Fait indépendant du crime : {people[borrowing.actor].name} a emprunté un {ordinary_tool.kind.label} à {labels[ordinary_tool.place]}, avec accord, pour un usage domestique.")
    for check in crime.inventory_checks:
        keeper = next(k for k in crime.keepers if k.id == check.keeper)
        lines.append(f"J+1, 08 h 00 · {keeper.name}, {labels[check.place]} : « {inventory_text(check)} » Indice possible, pas preuve du meurtre.")
    lines.append("Aucun témoin du crime ni caméra ajoutés. Aperçu public limité aux inventaires via --public-inventory ; ce n'est pas encore une enquête résoluble.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=1)
    for name, enum in (("motive", Motive), ("context", Context), ("stake", Stake)):
        parser.add_argument("--" + name, choices=[item.value for item in enum])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--requirements", action="store_true")
    parser.add_argument("--catalogue", action="store_true")
    parser.add_argument("--goal", choices=[goal.value for goal in VictimGoal])
    parser.add_argument("--acquisition", choices=[kind.value for kind in AcquisitionKind])
    parser.add_argument("--method", choices=[kind.value for kind in Method])
    parser.add_argument("--weapon-origin", choices=("home", "bar", "restaurant"))
    parser.add_argument("--no-mundane", action="store_true")
    parser.add_argument("--public-inventory", action="store_true", help="Preview only redacted inventory observations, not hidden truth")
    parser.add_argument("--situation", choices=[s.value for s in SituationKind])
    parser.add_argument("--public-scene", action="store_true", help="Redacted scene drink preview, not private truth")
    parser.add_argument("--investigation", action="store_true", help="Step 6 discovery projection, not private truth")
    parser.add_argument("--witnesses", action="store_true", help="Step 7 bounded eyewitness layer, requires --investigation")
    parser.add_argument("--walkthrough", action="store_true", help="Acquire projected artifacts offline, without movement/AP")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be positive")
    if args.public_inventory and args.public_scene:
        parser.error("Choose either --public-inventory or --public-scene")
    if args.investigation and (args.public_inventory or args.public_scene or args.requirements):
        parser.error("Investigation projection is separate from other previews/private requirements")
    if args.walkthrough and not args.investigation:
        parser.error("--walkthrough requires the investigation projection (--step 6)")
    if args.witnesses and not args.investigation:
        parser.error("--witnesses requires the investigation projection")
    kernels, builder = KernelBuilder(args.seed), CrimeBuilder(f"physical-v4:{args.seed}")
    goal = VictimGoal(args.goal) if args.goal else None
    filters = {name: enum(getattr(args, name)) if getattr(args, name) else None
               for name, enum in (("motive", Motive), ("context", Context), ("stake", Stake))}
    try:
        # Validate filters even for catalogue mode, without consuming builder RNG.
        from scenario_kernel import SUPPORTED_PREMISES
        domain = [p for p in SUPPORTED_PREMISES
                  if all(value is None or getattr(p, name) is value for name, value in filters.items())
                  and (goal is None or goal in allowed_goals(p))]
        if not domain:
            raise NoFeasibleCrime("No implemented kernel for these filters / victim goal")
        if args.catalogue:
            print(json.dumps({"premises": [p.as_dict() for p in domain],
                              "methods": [m.value for m in Method],
                              "encounters": [e.value for e in Encounter],
                              "acquisitions": [a.value for a in AcquisitionKind],
                              "weapon_origins": ["home", "bar", "restaurant"],
                              "tool_fates": [f.value for f in ToolFate],
                              "situations": [s.value for s in SituationKind],
                              "goals": [g.value for g in VictimGoal
                                        if (goal is None or g is goal) and any(g in allowed_goals(p) for p in domain)],
                              "note": "Actual availability depends on the constructed world."},
                             ensure_ascii=False, indent=2))
            return
        crimes = []
        for _ in range(args.count):
            if goal is None:
                kernel = kernels.sample(**filters)
            else:
                # Parent-first conditional domain, not retries or a fallback
                # goal that silently changes the requested victim intention.
                motive = filters["motive"] or kernels.rng.choice(tuple(m for m in Motive if any(p.motive is m for p in domain)))
                context = filters["context"] or kernels.rng.choice(tuple(c for c in Context if any(p.motive is motive and p.context is c for p in domain)))
                premise = kernels.rng.choice(tuple(p for p in domain if p.motive is motive and p.context is context))
                kernel = kernels.build(premise)
            crimes.append(builder.build(kernel, goal=goal,
                                        method=Method(args.method) if args.method else None,
                                        acquisition=AcquisitionKind(args.acquisition) if args.acquisition else None,
                                        source_place=args.weapon_origin, mundane=False if args.no_mundane else None,
                                        situation=SituationKind(args.situation) if args.situation else None))
    except ValueError as error:
        parser.error(str(error))
    if args.investigation:
        from scenario_observations import project, walkthrough
        plans = [project(crime) for crime in crimes]
        if args.witnesses:
            from scenario_observations import with_witnesses
            from scenario_witnesses import WitnessBuilder
            plans = [with_witnesses(plan, WitnessBuilder(f"{args.seed}:{index}").build(crime))
                     for index, (plan, crime) in enumerate(zip(plans, crimes))]
        if args.walkthrough:
            rows = [walkthrough(plan) for plan in plans]
        else:
            rows = [plan.public_catalogue() for plan in plans]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print(f"Découverte V{2 if args.witnesses else 1} — prototype offline, reconstitution non certifiée\n")
            for index, (plan, row) in enumerate(zip(plans, rows), 1):
                print(f"{index:02d}. Sources accessibles, sans révélation de la vérité privée")
                if args.walkthrough:
                    for step in row["steps"]:
                        at, action = step["at"], step["action"]
                        day, minute = divmod(at, 1440)
                        print(f"J+{day}, {minute // 60:02d} h {minute % 60:02d} · {dict(plan.locations)[action['place']]} · {action['label']}")
                        for received in step["received"]:
                            print("  " + received["text"])
                    audit = row["audit"]
                    status = "Identité compatible unique dans la projection ; reconstitution non certifiée." if audit["unique_deduction"] else "Enquête non résolue."
                    candidates = audit["remaining_count"]
                    people_text = "personne encore compatible" if candidates == 1 else "personnes encore compatibles"
                    assumption = " (apparences des suspects supposées connues)" if args.witnesses else ""
                    print(f"  Bilan : {audit['artifacts_acquired']}/{audit['artifacts_total']} informations ; {candidates} {people_text}{assumption}. {status}")
                else:
                    for action in plan.actions:
                        needs = ", ".join(action.requires) or "aucun"
                        print(f"  {dict(plan.locations)[action.place]} · {action.label} — prérequis : {needs}")
                print()
    elif args.public_scene:
        print(json.dumps([{"visibility": "public_scene_preview", "observations": list(
            venue_observations(crime, place=crime.scene, discovered_at=crime.execution.death_at))}
            for crime in crimes], ensure_ascii=False, indent=2))
    elif args.public_inventory:
        rows = [{"visibility": "public_inventory_preview", "observations": [row
                 for place in ("bar", "restaurant")
                 for row in inventory_observations(crime, place=place, discovered_at=1440 + 8 * 60)]}
                for crime in crimes]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.json:
        print(json.dumps([crime.as_dict() for crime in crimes], ensure_ascii=False, indent=2))
    else:
        print("Exécution physique V4 — VÉRITÉ PRIVÉE, pas une vue joueur\n")
        for i, crime in enumerate(crimes, 1):
            print(f"{i:02d}. {describe(crime)}\n")
            if args.requirements:
                for proof in validate_kernel(crime.kernel):
                    print(f"  {proof.requirement.value} ← {', '.join(proof.sources)}")
                print()


if __name__ == "__main__":
    main()
