"""Post-crime authoring: observers, attention and bounded truthful memories.

Added witnesses have real commutes on an extended authoring map. Presence alone
never creates knowledge. Descriptions are sampled independently of criminal
roles; a unique descriptor is not selected as an incriminating perception.
No game state, persistence, or APK integration in this experimental layer.
"""
import random
from dataclasses import dataclass
from enum import Enum

from scenario_crime import (Edge, ExecutedCrime, Node, NodeKind, StreetMap, Walk, make_walk,
                            validate_crime, validate_walk)
from scenario_situations import SituationKind


class InvalidWitness(ValueError):
    pass


class EventKind(Enum):
    SHARED_ROUTE = "shared_route"
    NEARBY = "nearby"
    MEETING = "meeting"
    SERVICE = "service"
    DRINK_ADDITION = "drink_addition"
    ASSAULT = "assault"
    DEPARTURE = "departure"
    NONARRIVAL = "nonarrival"
    ORDINARY_ROUTE = "ordinary_route"


class Sense(Enum):
    VISUAL = "visual"
    PARTICIPATION = "participation"


class Aspect(Enum):
    SILHOUETTE = "silhouette"
    COAT = "coat"
    HEIGHT = "height"
    HAIR = "hair"


class Coat(Enum):
    DARK = "sombre"
    LIGHT = "clair"
    COLOURED = "coloré"


class Height(Enum):
    SHORT = "plutôt petite"
    AVERAGE = "de taille moyenne"
    TALL = "plutôt grande"


class Hair(Enum):
    BLACK = "noirs"
    BROWN = "bruns"
    BLOND = "blonds"
    RED = "roux"


@dataclass(frozen=True)
class Appearance:
    person: str
    coat: Coat
    height: Height
    hair: Hair = Hair.BLACK


def sample_appearances(person_ids, seed):
    """No author/victim arguments, no retries or reassignment to create a decoy."""
    rng = random.Random(f"appearance-v1:{seed}")
    return tuple(Appearance(person, rng.choice(tuple(Coat)), rng.choice(tuple(Height)),
                            random.Random(f"hair-v1:{seed}:{person}").choice(tuple(Hair)))
                 for person in sorted(person_ids))


@dataclass(frozen=True)
class SceneEvent:
    id: str
    kind: EventKind
    place: str
    minute: int
    actors: tuple[str, ...]
    target: str | None


def scene_events(crime):
    """Observable acts only; never intentions, goals, guilt or private relations."""
    x, roles = crime.execution, crime.kernel.roles
    a, v = roles.author, roles.victim
    rows = []
    if x.situation is SituationKind.TRACKING:
        kind = EventKind.SHARED_ROUTE if len(x.following.nodes) > 1 else EventKind.NEARBY
        rows.append(SceneEvent(kind.value, kind, x.following.nodes[0],
                               x.following.times[0], (a,), v))
    elif x.situation is SituationKind.AGREED_MEETING:
        rows.append(SceneEvent("meeting", EventKind.MEETING, crime.scene,
                               x.observation_at + 1, (a,), v))
    else:
        exposure = x.exposure
        rows.extend((SceneEvent("service", EventKind.SERVICE, crime.scene, exposure.served_at,
                                (exposure.served_by,), v),
                     SceneEvent("drink_addition", EventKind.DRINK_ADDITION, crime.scene,
                                exposure.altered_at, (a,), v)))
    if x.situation is not SituationKind.VENUE:
        rows.append(SceneEvent("assault", EventKind.ASSAULT, crime.scene, x.attack_at, (a,), v))
    # Departure on a node actually visited, not a CCTV on an intended route.
    index = 1 if len(x.escape.nodes) > 2 else 0
    rows.append(SceneEvent("departure", EventKind.DEPARTURE, x.escape.nodes[index],
                           x.escape.times[index], (a,), None))
    for missed in crime.missed_appointments:
        rows.append(SceneEvent("nonarrival:" + missed.appointment, EventKind.NONARRIVAL,
            missed.place, missed.observed_at, (missed.observer,), missed.visitor))
    # Genuine innocent passages, outside the crime: wrong-hour footage must
    # not secretly describe only the culprit. No fabricated suspicious acts.
    for index, borrowing in enumerate(crime.mundane_borrowings):
        for tag, walk in (("out", borrowing.outbound), ("back", borrowing.inbound)):
            for hop, (place, minute) in enumerate(zip(walk.nodes, walk.times)):
                if crime.streets.kind(place) is NodeKind.STREET:
                    rows.append(SceneEvent(f"ordinary_route:{index}:{tag}:{hop}", EventKind.ORDINARY_ROUTE,
                                           place, minute, (borrowing.actor,), None))
    return tuple(rows)


@dataclass(frozen=True)
class Witness:
    id: str
    name: str
    home: str | None
    post: str
    role: str  # keeper / resident / commuter


@dataclass(frozen=True)
class Presence:
    id: str
    witness: str
    place: str
    start: int
    end: int
    arrival: Walk | None = None
    departure: Walk | None = None


@dataclass(frozen=True)
class Attention:
    id: str
    witness: str
    place: str
    start: int
    end: int
    sense: Sense
    visible: tuple[str, ...] = ()  # explicit sightline subjects, not all present people
    occluded: bool = False
    recognizable: tuple[str, ...] = ()  # target can later be matched to a photo


@dataclass(frozen=True)
class Perception:
    id: str
    witness: str
    event: str
    attention: str
    aspect: Aspect
    actor: str | None


@dataclass(frozen=True)
class Statement:
    id: str
    witness: str
    text: str
    sources: tuple[str, ...]
    candidates: frozenset[str]
    relevance: str  # context vs identification of an observed assailant


@dataclass(frozen=True)
class WitnessLayer:
    crime: ExecutedCrime
    streets: StreetMap
    appearances: tuple[Appearance, ...]
    events: tuple[SceneEvent, ...]
    witnesses: tuple[Witness, ...]
    presences: tuple[Presence, ...]
    attention: tuple[Attention, ...]
    perceptions: tuple[Perception, ...]

    def __post_init__(self):
        validate(self)

    @property
    def population(self):
        return frozenset(p.id for p in self.crime.kernel.world.people if p.id != self.crime.kernel.roles.victim)


def _require(condition, text):
    if not condition:
        raise InvalidWitness(text)


def matching(layer, perception):
    """True appearance predicate, NOT a hand-authored suspect mask."""
    if perception.aspect is Aspect.SILHOUETTE:
        return layer.population
    appearance = next(a for a in layer.appearances if a.person == perception.actor)
    field = perception.aspect.value
    return frozenset(a.person for a in layer.appearances if a.person in layer.population
                     and getattr(a, field) is getattr(appearance, field))


def validate(layer):
    validate_crime(layer.crime)
    _require(type(layer.streets) is StreetMap, "typed extended map")
    StreetMap(layer.streets.nodes, layer.streets.edges)
    original = layer.crime.streets
    _require(layer.streets.nodes[:len(original.nodes)] == original.nodes
             and layer.streets.edges[:len(original.edges)] == original.edges, "crime map unchanged")
    people = {p.id: p for p in layer.crime.kernel.world.people}
    _require(type(layer.appearances) is tuple and all(type(a) is Appearance
             and type(a.coat) is Coat and type(a.height) is Height and type(a.hair) is Hair for a in layer.appearances)
             and len(layer.appearances) == len(people)
             and {a.person for a in layer.appearances} == people.keys(), "neutral complete appearance roster")
    _require(type(layer.events) is tuple and layer.events == scene_events(layer.crime), "events derive exactly from physical truth")
    for values, expected in ((layer.witnesses, Witness), (layer.presences, Presence),
                             (layer.attention, Attention), (layer.perceptions, Perception)):
        _require(type(values) is tuple and all(type(v) is expected and type(v.id) is str and bool(v.id) for v in values)
                 and len({v.id for v in values}) == len(values), "typed unique witness entities")
    ids = [v.id for values in (layer.witnesses, layer.presences, layer.attention, layer.perceptions) for v in values]
    _require(len(ids) == len(set(ids)), "distinct witness entity IDs")
    witnesses = {w.id: w for w in layer.witnesses}
    events, attentions = {e.id: e for e in layer.events}, {a.id: a for a in layer.attention}
    keepers = {k.id: k for k in layer.crime.keepers}
    for w in layer.witnesses:
        _require(type(w.name) is str and bool(w.name) and w.post in {n.id for n in layer.streets.nodes}, "real witness post")
        if w.role == "keeper":
            _require(w.id in keepers and w.post == keepers[w.id].place and w.home is None
                     and w.name == keepers[w.id].name, "existing keeper")
        elif w.role == "resident":
            _require(w.id in people and w.id not in (layer.crime.kernel.roles.author, layer.crime.kernel.roles.victim)
                     and w.home == w.post == people[w.id].home and w.name == people[w.id].name,
                     "innocent resident witness at their actual home")
        else:
            _require(w.role == "commuter" and w.id.startswith("witness:") and w.id not in people
                     and w.home in {n.id for n in layer.streets.nodes} and layer.streets.kind(w.home) is NodeKind.HOME
                     and w.home not in {n.id for n in original.nodes}, "new commuter with authored home")
    homes = {w.home for w in layer.witnesses if w.role == "commuter"}
    added = layer.streets.nodes[len(original.nodes):]
    _require({n.id for n in added} == homes and all(n.kind is NodeKind.HOME for n in added),
             "only witness homes may extend the crime map")
    for edge in layer.streets.edges[len(original.edges):]:
        _require((edge.a in homes and edge.b in {n.id for n in original.nodes if n.kind is NodeKind.STREET})
                 or (edge.b in homes and edge.a in {n.id for n in original.nodes if n.kind is NodeKind.STREET}),
                 "no shortcut or new crime path from witness authoring")
    for p in layer.presences:
        _require(p.witness in witnesses and type(p.start) is int and type(p.end) is int
                 and 0 <= p.start <= p.end and p.place == witnesses[p.witness].post, "bounded stationary presence")
        w = witnesses[p.witness]
        if w.role == "commuter":
            _require(type(p.arrival) is Walk and type(p.departure) is Walk, "witness must commute")
            # Existing validator uses one-day clocks. Validate actual deltas by
            # normalizing each same-day commute, not wrapping a midnight edge.
            for walk in (p.arrival, p.departure):
                day = walk.times[0] // 1440
                normalized = Walk(walk.person, walk.nodes, tuple(t - day * 1440 for t in walk.times))
                validate_walk(normalized, layer.streets, w.id)
            _require(p.arrival.nodes[0] == w.home and p.arrival.nodes[-1] == p.place
                     and p.departure.nodes[0] == p.place and p.departure.nodes[-1] == w.home
                     and p.arrival.times[-1] == p.start and p.departure.times[0] == p.end,
                     "continuous commute to post and back home")
        else:
            _require(p.arrival is None and p.departure is None, "staff/resident presence does not invent travel")
            if w.role == "keeper":
                _require(any(start <= p.start <= p.end <= end for start, end in keepers[w.id].shifts), "keeper actually on shift")
            else:
                meeting = layer.crime.victim_plan.appointment
                _require(meeting is not None and meeting.host == w.id and
                         (meeting.host_present_from <= p.start <= p.end <= meeting.host_present_until
                          or 1440 + 8 * 60 <= p.start <= p.end <= 1440 + 22 * 60), "resident presence at agreed meeting or authored interview")
    for w in witnesses:
        spans = sorted((p.arrival.times[0] if p.arrival else p.start,
                        p.departure.times[-1] if p.departure else p.end)
                       for p in layer.presences if p.witness == w)
        _require(all(previous[1] < later[0] for previous, later in zip(spans, spans[1:])), "witness routines cannot overlap")
    for attention in layer.attention:
        _require(attention.witness in witnesses and type(attention.start) is int and type(attention.end) is int
                 and type(attention.occluded) is bool and type(attention.visible) is tuple
                 and type(attention.recognizable) is tuple
                 and len(set(attention.visible)) == len(attention.visible)
                 and len(set(attention.recognizable)) == len(attention.recognizable)
                 and set(attention.recognizable) <= set(attention.visible)
                 and set(attention.visible) <= (people.keys() | keepers.keys())
                 and type(attention.sense) is Sense and any(p.witness == attention.witness
                     and p.place == attention.place and p.start <= attention.start <= attention.end <= p.end
                     for p in layer.presences), "attention requires actual co-presence at the observation point")
    for perception in layer.perceptions:
        _require(perception.witness in witnesses and perception.event in events
                 and perception.attention in attentions and type(perception.aspect) is Aspect, "real perception references")
        event, attention = events[perception.event], attentions[perception.attention]
        _require(attention.witness == perception.witness and attention.place == event.place
                 and attention.start <= event.minute <= attention.end, "no remote, blind or future memory")
        if event.kind in (EventKind.SERVICE, EventKind.NONARRIVAL):
            _require(attention.sense is Sense.PARTICIPATION and perception.witness in event.actors
                     and perception.actor is None and perception.aspect is Aspect.SILHOUETTE,
                     "service/nonarrival known only through real participation")
        else:
            _require(attention.sense is Sense.VISUAL and perception.actor in event.actors
                     and perception.actor in people and perception.actor != perception.witness
                     and not attention.occluded and perception.actor in attention.visible
                     and (event.target is None or event.target in attention.visible),
                     "seen actor and target, unobstructed sightline, not a private belief")
            _require(perception.actor not in attention.recognizable
                     and (event.target is None or event.target in attention.recognizable),
                     "unrecognized actor and recognizable photo target")
        if attention.sense is Sense.VISUAL:
            _require(len(matching(layer, perception)) >= 2, "person description must retain at least two candidates")
    # Reject the whole person's testimony, not just each sentence separately.
    for w in witnesses:
        by_actor = {}
        for p in layer.perceptions:
            if p.witness == w and attentions[p.attention].sense is Sense.VISUAL:
                by_actor[p.actor] = by_actor.get(p.actor, layer.population) & matching(layer, p)
        _require(all(len(support) >= 2 for support in by_actor.values()),
                 "whole witness testimony singles out a person")
    return layer


def _time(minute):
    rounded = 15 * ((minute + 7) // 15)
    return f"vers {rounded // 60} h" + (f" {rounded % 60:02d}" if rounded % 60 else "")


def statements(layer, witness_id):
    """Truthful bounded speech. No hidden intention, recommendation or guilt label."""
    validate(layer)
    if witness_id not in {w.id for w in layer.witnesses}:
        raise ValueError("Unknown witness")
    events, rows = {e.id: e for e in layer.events}, []
    for perception in layer.perceptions:
        if perception.witness != witness_id:
            continue
        event = events[perception.event]
        if event.kind is EventKind.SERVICE:
            text = f"Oui, cette personne sur la photo, je lui ai servi un verre {_time(event.minute)}."
        elif event.kind is EventKind.NONARRIVAL:
            visitor = next(p.name for p in layer.crime.kernel.world.people if p.id == event.target)
            text = f"Hier soir, {visitor} devait venir chez moi. J'ai attendu pour rien."
        else:
            text = {
                EventKind.SHARED_ROUTE: f"La personne sur votre photo passait ici {_time(event.minute)}. Quelqu'un empruntait la même rue.",
                EventKind.NEARBY: f"Cette personne était ici {_time(event.minute)}. Il y avait aussi quelqu'un d'autre.",
                EventKind.MEETING: f"J'ai vu cette personne avec quelqu'un d'autre ici, {_time(event.minute)}.",
                EventKind.DRINK_ADDITION: f"Quelqu'un a ajouté quelque chose au verre de cette personne, {_time(event.minute)}. Je n'ai pas vu ce que c'était.",
                EventKind.ASSAULT: f"J'ai vu quelqu'un attaquer la personne sur votre photo, {_time(event.minute)}.",
                EventKind.DEPARTURE: f"J'ai vu quelqu'un quitter cet endroit {_time(event.minute)}.",
                EventKind.ORDINARY_ROUTE: f"Une personne passait dans cette rue {_time(event.minute)}. Je n'ai pas vu d'agression.",
            }[event.kind]
            look = next(a for a in layer.appearances if a.person == perception.actor)
            if perception.aspect is Aspect.COAT:
                text += f" Son manteau était {look.coat.value}. Je n'ai pas reconnu son visage."
            elif perception.aspect is Aspect.HEIGHT:
                text += f" La personne était {look.height.value}. Je n'ai pas reconnu son visage."
            elif perception.aspect is Aspect.HAIR:
                text += f" Ses cheveux étaient {look.hair.value}. Je n'ai pas reconnu son visage."
            else:
                text += " Je n'ai pas assez bien vu pour décrire la personne."
        relevance = "assailant_description" if event.kind in (EventKind.ASSAULT, EventKind.DRINK_ADDITION) else "context"
        support = matching(layer, perception) if relevance != "context" else layer.population
        rows.append(Statement("testimony:" + perception.id, witness_id, text, (perception.id,), support, relevance))
    return tuple(rows)


def reply_to(layer, witness_id, topic):
    """A question cannot manufacture knowledge missing from the memory ledger."""
    if type(topic) is not EventKind:
        raise TypeError("EventKind topic required")
    rows = statements(layer, witness_id)
    by_id = {e.id: e for e in layer.events}
    relevant = {"testimony:" + p.id for p in layer.perceptions if p.witness == witness_id
                and by_id[p.event].kind is topic}
    answers = tuple(row.text for row in rows if row.id in relevant)
    return answers or ("Je ne sais pas. Je ne peux rien vous dire là-dessus.",)


class WitnessBuilder:
    def __init__(self, seed=42):
        self.seed = seed
        self.rng = random.Random(f"witness-v1:{seed}")

    def build(self, crime, *, focus_assault=0):
        validate_crime(crime)
        if type(focus_assault) is not int or not 0 <= focus_assault <= 2:
            raise ValueError("focus_assault must be 0, 1 or 2")
        appearances = sample_appearances((p.id for p in crime.kernel.world.people), self.seed)
        events = scene_events(crime)
        witnesses, presences, attention, perceptions = [], [], [], []
        nodes, edges = list(crime.streets.nodes), list(crime.streets.edges)

        def record(w, event, aspect=Aspect.SILHOUETTE):
            sense = Sense.PARTICIPATION if event.kind in (EventKind.SERVICE, EventKind.NONARRIVAL) else Sense.VISUAL
            key = w.id + ":" + event.id
            visible = tuple(dict.fromkeys(event.actors + ((event.target,) if event.target else ()))) if sense is Sense.VISUAL else ()
            recognizable = (event.target,) if sense is Sense.VISUAL and event.target else ()
            attention.append(Attention("attention:" + key, w.id, event.place, event.minute, event.minute,
                                       sense, visible, recognizable=recognizable))
            perceptions.append(Perception("memory:" + key, w.id, event.id, "attention:" + key, aspect,
                                          None if sense is Sense.PARTICIPATION else event.actors[0]))

        for event in events:
            if event.kind is EventKind.SERVICE:
                keeper = next(k for k in crime.keepers if k.id == event.actors[0])
                w = Witness(keeper.id, keeper.name, None, keeper.place, "keeper")
                witnesses.append(w)
                presences.extend(Presence(f"presence:{w.id}:{index}", w.id, keeper.place, start, end)
                                 for index, (start, end) in enumerate(keeper.shifts))
                record(w, event)
            elif event.kind is EventKind.NONARRIVAL:
                resident = next(p for p in crime.kernel.world.people if p.id == event.actors[0])
                meeting = crime.victim_plan.appointment
                w = Witness(resident.id, resident.name, resident.home, resident.home, "resident")
                witnesses.append(w)
                presences.extend((Presence("presence:" + w.id + ":appointment", w.id, w.post,
                    meeting.host_present_from, meeting.host_present_until),
                    Presence("presence:" + w.id + ":interview", w.id, w.post, 1440 + 8 * 60, 1440 + 22 * 60)))
                record(w, event)
        choices = tuple(e for e in events if e.kind not in (EventKind.SERVICE, EventKind.NONARRIVAL))
        # No always-present decisive observer; some scenes have only context or
        # no extra passer-by. Solvability comes later, without changing the crime.
        if focus_assault:
            choices = tuple(e for e in choices if e.kind in (EventKind.ASSAULT, EventKind.DRINK_ADDITION))  # the decisive act, blade or glass
            if not choices:
                raise ValueError("Cannot author an assault witness in a non-assault crime")
        count = focus_assault or self.rng.choice((1, 2, 2))
        # Never two witnesses of the same act: a second witness saw something else.
        selected = tuple(self.rng.sample(choices, min(count, len(choices))))
        population = {p.id for p in crime.kernel.world.people} - {crime.kernel.roles.victim}
        for index, event in enumerate(selected):
            home = f"witness_home:{index}"
            entrance = event.place if crime.streets.kind(event.place) is NodeKind.STREET else crime.streets.neighbors(event.place)[0][0]
            nodes.append(Node(home, NodeKind.HOME, f"Logement du témoin {index + 1}"))
            edges.append(Edge(home, entrance, self.rng.choice((2, 3, 4))))
            names = ("La vendeuse de nuit", "Le livreur")
            w = Witness(f"witness:{index}", names[index], home, event.place, "commuter")
            witnesses.append(w)
        streets = StreetMap(tuple(nodes), tuple(edges))
        for index, event in enumerate(selected):
            w = next(w for w in witnesses if w.id == f"witness:{index}")
            path = streets.path(w.home, w.post)
            cost = sum(streets.duration(a, b) for a, b in zip(path, path[1:]))
            for tag, start, end in (("evening", event.minute - 20, event.minute + 20),
                                    ("interview", 1440 + 8 * 60, 1440 + 22 * 60)):
                presences.append(Presence(f"presence:{w.id}:{tag}", w.id, w.post, start, end,
                    make_walk(w.id, path, start - cost, streets),
                    make_walk(w.id, tuple(reversed(path)), end, streets)))
            look = next(a for a in appearances if a.person == event.actors[0])
            aspects = [Aspect.SILHOUETTE]
            for aspect, field in ((Aspect.COAT, "coat"), (Aspect.HEIGHT, "height"), (Aspect.HAIR, "hair")):
                matching_people = [a for a in appearances if a.person in population
                                   and getattr(a, field) is getattr(look, field)]
                if len(matching_people) >= 2:
                    aspects.append(aspect)
            # One witness of the decisive act keeps one trait when any is shareable: a
            # case is never only silhouettes. Any further witness of it gives the time and
            # a silhouette: the scene alone never hands out two traits.
            if focus_assault and index == 0 and len(aspects) > 1:
                aspects = aspects[1:]
            elif focus_assault and index > 0:
                aspects = [Aspect.SILHOUETTE]
            record(w, event, self.rng.choice(aspects))
        return WitnessLayer(crime, streets, appearances, events, tuple(witnesses), tuple(presences),
                            tuple(attention), tuple(perceptions))
