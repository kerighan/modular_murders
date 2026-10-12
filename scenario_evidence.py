"""Local cameras, searchable containers, contacts and corroborated whereabouts.

All records refer to immutable physical events. New background presences are
explicit authored facts, not masks randomly intersected with the guilty ID.
Partial fingerprints are contact leads, never identity-of-the-killer proofs.
"""
import random
from dataclasses import dataclass

from scenario_crime import NodeKind, ToolFate
from scenario_witnesses import Aspect, EventKind, scene_events, sample_appearances


@dataclass(frozen=True)
class Camera:
    place: str
    aspect: Aspect
    online: bool


@dataclass(frozen=True)
class Clip:
    id: str
    place: str
    minute: int
    event: str
    actor: str
    aspect: Aspect


@dataclass(frozen=True)
class Disposal:
    tool: str
    place: str
    minute: int
    actor: str
    container: str  # bin or cupboard; coarse truth's HIDDEN is refined, not moved


@dataclass(frozen=True)
class Contact:
    id: str
    person: str
    object: str
    place: str
    minute: int
    ridge: str  # intentionally incomplete fictional pattern, not a real matcher


@dataclass(frozen=True)
class VerifiedPresence:
    id: str
    person: str
    place: str
    start: int
    end: int
    witness: str
    basis: str


@dataclass(frozen=True)
class SurfaceTrace:
    object: str
    kind: str
    created_at: int
    event: str


def compatible_presence(crime, presence):
    """A corroborator may be authored, but never against an existing movement."""
    from types import SimpleNamespace
    from scenario_evening import physical_schedule
    for person, place, start, end in physical_schedule(crime, SimpleNamespace(presences=())):
        if person != presence.person or place == presence.place:
            continue
        path = crime.streets.path(place, presence.place)
        travel = sum(crime.streets.duration(a, b) for a, b in zip(path, path[1:]))
        if end + travel <= presence.start or presence.end + travel <= start:
            continue
        return False
    return True


@dataclass(frozen=True)
class Evidence:
    crime: object
    appearances: tuple
    cameras: tuple[Camera, ...]
    clips: tuple[Clip, ...]
    disposal: Disposal | None
    contacts: tuple[Contact, ...]
    presences: tuple[VerifiedPresence, ...]
    surfaces: tuple[SurfaceTrace, ...] = ()

    @property
    def population(self):
        return frozenset(p.id for p in self.crime.kernel.world.people if p.id != self.crime.kernel.roles.victim)

    def __post_init__(self):
        self.validate()

    def validate(self):
        c, x = self.crime, self.crime.execution
        people = {p.id: p for p in c.kernel.world.people}
        for items, cls in ((self.cameras, Camera), (self.clips, Clip), (self.contacts, Contact),
                           (self.presences, VerifiedPresence), (self.surfaces, SurfaceTrace)):
            if type(items) is not tuple or not all(type(item) is cls for item in items):
                raise ValueError("Immutable typed evidence records")
            if hasattr(cls, "__dataclass_fields__") and "id" in cls.__dataclass_fields__:
                if len({item.id for item in items}) != len(items):
                    raise ValueError("Unique evidence IDs")
        if not all(type(cam.online) is bool and type(cam.aspect) is Aspect for cam in self.cameras):
            raise ValueError("Typed camera coverage")
        streets = {n.id for n in c.streets.nodes if n.kind is NodeKind.STREET}
        if {r.place for r in self.cameras} != streets or len(self.cameras) != len(streets):
            raise ValueError("One local camera per district")
        if {a.person for a in self.appearances} != people.keys():
            raise ValueError("Independent cast appearances")
        events = {e.id: e for e in scene_events(c)}
        if self.disposal:
            d = self.disposal
            if (x.tool_fate is not ToolFate.HIDDEN or d.place != x.hidden_at
                    or d.tool != x.tool or d.actor != c.kernel.roles.author
                    or d.minute != x.escape.times[x.escape.nodes.index(d.place)]
                    or d.container != ("bin" if d.place in streets else "cupboard")):
                raise ValueError("Disposal on the actual escape, at the actual time")
        for clip in self.clips:
            camera = next(cam for cam in self.cameras if cam.place == clip.place)
            if not camera.online or clip.aspect != camera.aspect:
                raise ValueError("Working camera with a fixed resolution")
            if clip.event == "disposal":
                d = self.disposal
                if d is None or (clip.place, clip.minute, clip.actor) != (d.place, d.minute, d.actor):
                    raise ValueError("No invented disposal footage")
            else:
                e = events.get(clip.event)
                if e is None or (clip.place, clip.minute, clip.actor) != (e.place, e.minute, e.actors[0]):
                    raise ValueError("Footage must show an actual event")
        known_contacts = {(t.actor, t.tool, t.origin, t.minute) for t in c.transfers
                          if t.kind.value in ("acquisition", "innocent_loan")}
        for contact in self.contacts:
            p = people.get(contact.person)
            if p is None or not contact.ridge:
                raise ValueError("Existing fingerprint owner")
            if contact.object.startswith("mug:"):
                if contact.object != "mug:" + p.id or contact.place != p.home or contact.minute >= 0:
                    raise ValueError("A real prior household contact")
            elif (contact.person, contact.object, contact.place, contact.minute) not in known_contacts:
                raise ValueError("A print requires an actual handling event")
        from scenario_means import Method
        expected_surface = "victim_blood" if c.method is not Method.POISONED else "agent_residue"
        if self.surfaces != (SurfaceTrace(x.tool, expected_surface, x.attack_at, "physical_attack"),):
            raise ValueError("Surface trace must derive from the actual weapon's use")
        seen = set()
        for p in self.presences:
            if p.person in seen or p.person not in self.population or p.start > x.attack_at or p.end < x.attack_at:
                raise ValueError("A single corroborated presence covering the criminal act")
            seen.add(p.person)
            # The author cannot be placed elsewhere while executing the real walk.
            if p.person == c.kernel.roles.author:
                raise ValueError("Contradictory alibi")
            if not compatible_presence(c, p):
                raise ValueError("Alibi contradicts an existing physical trajectory")
            keeper = next((k for k in c.keepers if k.id == p.witness), None)
            if keeper is None or keeper.place != p.place or not any(
                    start <= p.start <= p.end <= end for start, end in keeper.shifts):
                raise ValueError("Corroboration requires actual staff on shift at the observed venue")
            venue = next((v for v in c.venue_presences if v.person == p.person), None)
            if venue:
                if p.place != venue.place or p.basis != "continuous_noncontact":
                    raise ValueError("Do not relocate an actual venue visitor")
                if p.start != x.exposure.served_at or p.end != x.death_at:
                    raise ValueError("Must observe the whole glass exposure")
            elif p.basis != "continuous_service":
                raise ValueError("Public service observation, not an anonymous domestic visitor")

    def description(self, clip):
        a = next(a for a in self.appearances if a.person == clip.actor)
        return (f"manteau {a.coat.value}" if clip.aspect is Aspect.COAT else
                f"personne {a.height.value}" if clip.aspect is Aspect.HEIGHT else
                f"cheveux {a.hair.value}" if clip.aspect is Aspect.HAIR else "silhouette indistincte")

    def support(self, clip):
        # Handling a drink or discarding an object is NOT an observed murder.
        if clip.event != "assault":
            return self.population
        true = next(a for a in self.appearances if a.person == clip.actor)
        return frozenset(a.person for a in self.appearances if a.person in self.population and
                         (clip.aspect is Aspect.SILHOUETTE or
                          clip.aspect is Aspect.COAT and a.coat == true.coat or
                          clip.aspect is Aspect.HEIGHT and a.height == true.height or
                          clip.aspect is Aspect.HAIR and a.hair == true.hair))
    def camera_query(self, place, hour):
        if type(hour) is not int or not 0 <= hour < 24:
            raise ValueError("Hour must be between 0 and 23")
        camera = next((c for c in self.cameras if c.place == place), None)
        if camera is None:
            raise ValueError("No camera at this location")
        if not camera.online:
            return (), "La caméra de ce quartier était hors service hier."
        clips = tuple(c for c in self.clips if c.place == place and hour * 60 <= c.minute < (hour + 1) * 60)
        if not clips:
            return (), "Rien d'exploitable sur ce créneau. Cela ne prouve pas que personne n'est passé."
        labels = {n.id: n.label for n in self.crime.streets.nodes}
        texts = []
        for clip in clips:
            act = {"assault": "Une personne attaque la victime.",
                   "disposal": f"Une personne glisse un objet dans la poubelle, {labels[place]}.",
                   "shared_route": "La victime passe; quelqu'un emprunte la même rue.",
                   "nearby": "La victime et une autre personne sont visibles.",
                   "meeting": "La victime discute avec une autre personne.",
                   "departure": "Une personne quitte le champ.",
                   "drink_addition": "Une personne ajoute quelque chose au verre. Le contenu ajouté est indiscernable."}.get(clip.event, "Une personne passe dans la rue. Aucune agression n'est visible.")
            texts.append(f"Hier {clip.minute // 60:02d}:{clip.minute % 60:02d} — {act} {self.description(clip)}; visage illisible.")
        return clips, "\n".join(texts)


def crime_window(crime):
    """Authored GAME estimate, not a medical model. Includes administration,
    not only death, for delayed fictional poison.
    """
    from scenario_means import Method
    anchor = 15 * (crime.execution.death_at // 15)
    return max(0, anchor - (60 if crime.method is Method.POISONED else 30)), anchor + 30


def build_evidence(crime, seed=0, appearances=None, *, required_alibis=()):
    rng = random.Random(f"evidence-v1:{seed}")
    people, x = crime.kernel.world.people, crime.execution
    appearances = appearances or sample_appearances((p.id for p in people), seed)
    streets = [n.id for n in crime.streets.nodes if n.kind is NodeKind.STREET]
    cameras = tuple(Camera(p, rng.choice(tuple(Aspect)), rng.random() < .85) for p in streets)
    disposal = None
    if x.tool_fate is ToolFate.HIDDEN:
        place = x.hidden_at
        disposal = Disposal(x.tool, place, x.escape.times[x.escape.nodes.index(place)],
                            crime.kernel.roles.author, "bin" if place in streets else "cupboard")
    events = [(e.id, e.place, e.minute, e.actors[0]) for e in scene_events(crime)
              if e.kind not in (EventKind.SERVICE, EventKind.NONARRIVAL)]
    if disposal and disposal.container == "bin":
        events.append(("disposal", disposal.place, disposal.minute, disposal.actor))
    clips = []
    for event, place, minute, actor in events:
        camera = next((cam for cam in cameras if cam.place == place and cam.online), None)
        if camera is None:
            continue
        clip = Clip(f"clip:{len(clips)}", place, minute, event, actor, camera.aspect)
        # Unique descriptions are not blurred by changing the world's profiles.
        # The camera actually records an indistinct silhouette in that case.
        true = next(a for a in appearances if a.person == actor)
        matches = [a for a in appearances if a.person != crime.kernel.roles.victim and
                   (camera.aspect is Aspect.SILHOUETTE or camera.aspect is Aspect.COAT and a.coat == true.coat or
                    camera.aspect is Aspect.HEIGHT and a.height == true.height or
                    camera.aspect is Aspect.HAIR and a.hair == true.hair)]
        if len(matches) < 2:
            # Omit this unusably discriminating criminal view; other footage is
            # still contextual. Rejection is an authoring choice, not a fake mask.
            continue
        clips.append(clip)
    ridges = {p.id: rng.choice(("boucle A", "arc B", "spirale C")) for p in people}
    contacts = [Contact("contact:mug:" + p.id, p.id, "mug:" + p.id, p.home,
                        -1440 + 8 * 60, ridges[p.id]) for p in people]
    for t in crime.transfers:
        if t.kind.value in ("acquisition", "innocent_loan"):
            contacts.append(Contact("contact:" + t.id, t.actor, t.tool, t.origin, t.minute, ridges[t.actor]))
    presences = []
    for p in people:
        if p.id in (crime.kernel.roles.author, crime.kernel.roles.victim):
            continue
        selected = rng.random() <= .72
        if not (selected or p.id in required_alibis):
            continue
        venue = next((v for v in crime.venue_presences if v.person == p.id), None)
        if venue:
            keeper = next(k for k in crime.keepers if k.place == venue.place)
            presence = VerifiedPresence("presence:" + p.id, p.id, venue.place,
                x.exposure.served_at, x.death_at, keeper.id, "continuous_noncontact")
            if compatible_presence(crime, presence):
                presences.append(presence)
        else:
            window_start, window_end = crime_window(crime)
            padding = random.Random(f"service-hours:{seed}:{p.id}")
            padded_start = max(0, window_start - padding.choice((0, 5, 10, 15)))
            padded_end = min(1439, window_end + padding.choice((0, 5, 10, 15)))
            keepers = list(crime.keepers)
            random.Random(f"service-alibi-v1:{seed}:{p.id}").shuffle(keepers)
            found = False
            for start, end in ((padded_start, padded_end), (window_start, window_end)):
                for keeper in keepers:
                    presence = VerifiedPresence("presence:" + p.id, p.id, keeper.place,
                        start, end, keeper.id, "continuous_service")
                    if (any(a <= start <= end <= b for a, b in keeper.shifts)
                            and compatible_presence(crime, presence)):
                        presences.append(presence)
                        found = True
                        break
                if found:
                    break
    from scenario_means import Method
    kind = "victim_blood" if crime.method is not Method.POISONED else "agent_residue"
    surfaces = (SurfaceTrace(x.tool, kind, x.attack_at, "physical_attack"),)
    return Evidence(crime, tuple(appearances), cameras, tuple(clips), disposal, tuple(contacts), tuple(presences), surfaces)
