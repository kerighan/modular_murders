"""Step 6: discoverable artifacts, not omniscient narration or a solved case.

Sources/supports are authoring metadata. Client payloads never contain them.
The base projection handles physical findings and stock checks; with_witnesses()
adds bounded memories. Never infer visits from access or guilt from missing stock.
"""
from dataclasses import dataclass
from enum import Enum

from scenario_crime import TraceKind, validate_crime
from scenario_graph import Observation, ScenarioGraph
from scenario_means import Method, ToolKind, inventory_observations


class Operation(Enum):
    INSPECT = "inspect"
    COLLECT = "collect"
    EXAMINE = "examine"
    ANALYZE = "analyze"
    ASK_STOCK = "ask_stock"
    INTERVIEW = "interview"
    READ = "read"
    VERIFY = "verify"
    CAMERA = "camera"
    SEARCH = "search"


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: str
    text: str
    sources: tuple[str, ...]  # private causal lineage, not player-visible
    candidates: frozenset[str]  # private compatibility, never identified visitors

    def public(self):
        return {"id": self.id, "kind": self.kind, "text": self.text}


@dataclass(frozen=True)
class DiscoveryAction:
    id: str
    operation: Operation
    label: str
    place: str
    actor: str  # physical fixture or service person, not an abstract place menu
    reveals: tuple[str, ...]
    requires: tuple[str, ...] = ()
    available_at: int = 0
    processing_minutes: int = 0
    windows: tuple[tuple[int, int | None], ...] = ((0, None),)

    def public(self):
        return {"id": self.id, "operation": self.operation.value, "label": self.label,
                "place": self.place, "actor": self.actor}


@dataclass(frozen=True)
class DiscoveryState:
    known: tuple[tuple[str, int], ...] = ()
    completed: tuple[str, ...] = ()


class UnavailableAction(ValueError):
    pass


@dataclass(frozen=True)
class DiscoveryPlan:
    population: frozenset[str]
    artifacts: tuple[Artifact, ...]
    actions: tuple[DiscoveryAction, ...]
    locations: tuple[tuple[str, str], ...]
    source_ids: frozenset[str]
    projection_version: int = 1

    def __post_init__(self):
        by_id = {a.id: a for a in self.artifacts}
        if len(by_id) != len(self.artifacts) or len({a.id for a in self.actions}) != len(self.actions):
            raise ValueError("Duplicate artifact/action")
        places = dict(self.locations)
        if len(places) != len(self.locations):
            raise ValueError("Duplicate location")
        for artifact in self.artifacts:
            if (not artifact.id or not artifact.text or not artifact.sources
                    or not set(artifact.sources) <= self.source_ids
                    or not artifact.candidates <= self.population or len(artifact.candidates) < 2):
                raise ValueError("Artifact needs real sources and at least two compatible people")
        produced = set()
        for action in self.actions:
            if (type(action.operation) is not Operation or not action.id or not action.label
                    or not action.actor or action.place not in places or not action.reveals
                    or len(set(action.reveals)) != len(action.reveals)
                    or len(set(action.requires)) != len(action.requires)
                    or not set(action.reveals + action.requires) <= by_id.keys()
                    or type(action.available_at) is not int or action.available_at < 0
                    or type(action.processing_minutes) is not int or action.processing_minutes < 0
                    or not action.windows or any(type(start) is not int or start < 0
                                                or (end is not None and (type(end) is not int or start > end))
                                                for start, end in action.windows)):
                raise ValueError("Invalid discovery action")
            # Validate the entire bundle: two individually ambiguous paragraphs
            # must not become a singleton when delivered by ONE tap.
            support = self.population.intersection(*(by_id[key].candidates for key in action.reveals))
            if len(support) < 2:
                raise ValueError("Action bundle singles out a person")
            produced.update(action.reveals)
        if produced != by_id.keys():
            raise ValueError("Every artifact needs an acquisition action")
        reached = set()
        while True:
            added = set().union(*(set(a.reveals) for a in self.actions if set(a.requires) <= reached))
            if added <= reached:
                break
            reached.update(added)
        if reached != by_id.keys():
            raise ValueError("Cyclic/unreachable acquisition requirements")

    def _check_state(self, state):
        if type(state) is not DiscoveryState:
            raise TypeError("DiscoveryState required")
        artifacts, actions = {a.id for a in self.artifacts}, {a.id for a in self.actions}
        if (len(dict(state.known)) != len(state.known)
                or any(key not in artifacts or type(time) is not int or time < 0 for key, time in state.known)
                or len(set(state.completed)) != len(state.completed) or not set(state.completed) <= actions):
            raise ValueError("Invalid discovery state")
        produced = {key for a in self.actions if a.id in state.completed for key in a.reveals}
        if produced != dict(state.known).keys():
            raise ValueError("Knowledge needs a completed acquisition action")
        by_id, known, reached, clock = {a.id: a for a in self.actions}, dict(state.known), set(), 0
        for key in state.completed:
            action = by_id[key]
            if not set(action.requires) <= reached:
                raise ValueError("Completed actions must respect acquisition prerequisites")
            fresh = set(action.reveals) - reached
            if fresh:
                dates = {known[key] for key in fresh}
                if len(dates) != 1:
                    raise ValueError("One artifact bundle has one acquisition date")
                at, = dates
                ready = max(clock, action.available_at,
                            max((known[key] for key in action.requires), default=0) + action.processing_minutes)
                if at < ready or not any(start <= at and (end is None or at <= end) for start, end in action.windows):
                    raise ValueError("Acquisition dates must respect processing and presence")
                clock = at
            reached.update(action.reveals)

    def next_time(self, action, state, *, after=0):
        self._check_state(state)
        if type(after) is not int or after < 0:
            raise TypeError("Nonnegative integer time required")
        if action not in self.actions:
            raise ValueError("Unknown action")
        known = dict(state.known)
        if action.id in state.completed or not set(action.requires) <= known.keys():
            return None
        ready = max(after, action.available_at,
                    max((known[key] for key in action.requires), default=0) + action.processing_minutes,
                    max(known.values(), default=0))
        return next((max(ready, start) for start, end in sorted(action.windows, key=lambda row: row[0])
                     if end is None or max(ready, start) <= end), None)

    def available(self, state, *, place, at):
        if type(at) is not int or at < 0:
            raise TypeError("Nonnegative integer time required")
        self._check_state(state)
        return tuple(a.public() for a in self.actions if a.place == place
                     and (ready := self.next_time(a, state)) is not None and ready <= at
                     and any(start <= at and (end is None or at <= end) for start, end in a.windows))

    def perform(self, state, action_id, *, place, at):
        legal = {row["id"] for row in self.available(state, place=place, at=at)}
        if action_id not in legal:
            raise UnavailableAction("Action inaccessible : lieu, prérequis, délai ou présence.")
        action = next(a for a in self.actions if a.id == action_id)
        by_id = {a.id: a for a in self.artifacts}
        known = dict(state.known)
        for key in action.reveals:
            known.setdefault(key, at)
        result = DiscoveryState(tuple(sorted(known.items())), state.completed + (action_id,))
        return result, tuple(by_id[key].public() for key in action.reveals)

    def graph(self):
        return ScenarioGraph(self.population, (Observation(a.id, a.kind, a.candidates) for a in self.artifacts))

    def solver_actions(self):
        """Existing offline solver contract, without travel/time-window costs.

This adapter alone does NOT certify that a chronological playthrough is legal.
The runtime gates remain authoritative. Delays are not disguised as PA costs.
"""
        from investigation_solver import InvestigationAction
        return tuple(InvestigationAction(a.id, a.operation.value, a.reveals, a.requires,
                                         method=a.operation.value) for a in self.actions)

    def public_catalogue(self):
        """Developer preview of future content, NOT a player's current journal."""
        return {"visibility": "public_content_catalogue", "projection_version": self.projection_version,
                "locations": dict(self.locations),
                "artifacts": [a.public() for a in self.artifacts],
                "actions": [dict(a.public(), requires=list(a.requires),
                                 processing_minutes=a.processing_minutes) for a in self.actions],
                "note": ("Catalogue auteur, pas un carnet joueur. CLI expérimentale dans scenario_play.py ; pas encore intégrée à Godot."
                         if self.projection_version >= 3 else
                         "Prototype offline : pas encore une enquête résoluble ni une partie Godot.")}


def project(crime):
    """Derive effects from validated truth without changing it or using killer IDs.

Scene/medical facts describe the victim and method, not a suspect's presence.
They remain compatible with the entire population. Stock facts keep access
possibilities, never actual visits. Public glass collection names nobody:
its private access list is NOT a witness statement.
"""
    validate_crime(crime)
    population = frozenset(p.id for p in crime.kernel.world.people if p.id != crime.kernel.roles.victim)
    traces = {t.kind: t for t in crime.traces}
    artifacts, actions = [], []
    source_ids = frozenset(t.id for t in crime.traces) | frozenset(c.id for c in crime.inventory_checks)

    def add(key, kind, text, sources, support=None):
        artifacts.append(Artifact(key, kind, text, tuple(sources), population if support is None else frozenset(support)))

    death = traces[TraceKind.BODY].created_at
    add("scene_body", "scene", "Le corps de la victime se trouve ici.", ("body",))
    actions.append(DiscoveryAction("inspect_scene", Operation.INSPECT, "Examiner la scène",
                                   crime.scene, "fixture:crime_scene", ("scene_body",), available_at=death))
    if TraceKind.VICTIM_BLOOD in traces:
        add("blood_sample", "sample", "Le prélèvement de sang est conservé pour analyse.", ("blood",))
        actions.append(DiscoveryAction("collect_blood", Operation.COLLECT, "Prélever le sang au sol",
            crime.scene, "fixture:blood", ("blood_sample",), ("scene_body",), death))
        add("blood_reference", "sample", "Un prélèvement de comparaison a été effectué sur le corps lors de l'examen médico-légal.", ("body",))
        add("blood_result", "laboratory", "Le sang retrouvé au sol correspond au prélèvement effectué sur le corps de la victime. Aucun sang d'une autre personne n'a été identifié dans cet échantillon.", ("blood", "body"))
        actions.append(DiscoveryAction("analyze_blood", Operation.ANALYZE, "Faire analyser le prélèvement",
            "lab", "staff:lab", ("blood_result",), ("blood_sample", "blood_reference"), death, 30))
    if TraceKind.DRINK in traces:
        add("drink_sample", "sample", "Le verre resté près de la victime est conservé pour analyse. Son contenu n'a pas encore été examiné.", ("drink",))
        actions.append(DiscoveryAction("collect_drink", Operation.COLLECT, "Conserver le verre pour analyse",
            crime.scene, "fixture:drink", ("drink_sample",), ("scene_body",), death))
        add("drink_result", "laboratory", "Une substance toxique a été retrouvée dans le verre. Elle ne fait pas partie de la boisson servie. L'analyse ne permet pas de savoir qui l'a ajoutée.", ("drink", "toxic_effect"))
        actions.append(DiscoveryAction("analyze_drink", Operation.ANALYZE, "Faire analyser le contenu du verre",
            "lab", "staff:lab", ("drink_result",), ("drink_sample",), death, 30))
    # A request at the scene triggers an authored medical-service operation.
    # This is not an inferred NPC trajectory or an automatic source of knowledge.
    add("exam_request", "request", "Le corps est transféré à la morgue, à l'hôpital. Le médecin légiste va procéder à l'examen ; son rapport sera disponible après le délai annoncé.", ("body",))
    actions.append(DiscoveryAction("request_exam", Operation.EXAMINE, "Transférer le corps à la morgue pour examen",
        crime.scene, "fixture:crime_scene", ("exam_request",), ("scene_body",), death))
    medical = {Method.EDGED: "La blessure mortelle est compatible avec une lame. L'examen ne permet pas d'identifier un couteau précis.",
               Method.BLUNT: "La blessure mortelle est compatible avec un objet contondant. L'examen ne permet pas d'identifier un objet précis.",
               Method.POISONED: "Aucune blessure traumatique n'explique le décès. Les analyses indiquent une intoxication. L'examen du corps ne permet pas de savoir comment le poison a été administré."}[crime.method]
    sources = ("body", "toxic_effect") if crime.method is Method.POISONED else ("body", "method_mark")
    add("medical_report", "medical", medical, sources)
    medical_bundle = ("medical_report", "blood_reference") if TraceKind.VICTIM_BLOOD in traces else ("medical_report",)
    actions.append(DiscoveryAction("read_medical", Operation.EXAMINE, "Consulter le médecin légiste",
        "morgue", "staff:medical", medical_bundle, ("exam_request",), death, 60))
    if TraceKind.LEFT_TOOL in traces:
        tool = next(t for t in crime.inventory if t.id == crime.execution.tool)
        name = {ToolKind.KITCHEN_KNIFE: "Un couteau", ToolKind.HAMMER: "Un marteau",
                ToolKind.FICTIONAL_AGENT: "Un flacon de produit d'entretien"}[tool.kind]
        add("scene_object", "scene_object", name + " se trouve sur la scène. Sa présence ne suffit pas à établir qu'il a servi au crime.", ("left_tool",))
        actions.append(DiscoveryAction("collect_object", Operation.COLLECT, "Examiner l'objet au sol",
            crime.scene, "fixture:left_object", ("scene_object",), ("scene_body",), traces[TraceKind.LEFT_TOOL].created_at))
    for check in crime.inventory_checks:
        row = next(r for r in inventory_observations(crime, place=check.place, discovered_at=check.observed_at)
                   if r["id"] == check.id)
        add(check.id, "inventory", row["text"], (check.id,), row["candidates"])
        keeper = next(k for k in crime.keepers if k.id == check.keeper)
        actions.append(DiscoveryAction("ask:" + check.id, Operation.ASK_STOCK, "Demander ce qui manque : " + check.kind.label,
            check.place, keeper.id, (check.id,), available_at=check.observed_at, windows=keeper.shifts))
    locations = tuple((n.id, n.label) for n in crime.streets.nodes) + (("morgue", "La Morgue"), ("lab", "Le Laboratoire"))
    return DiscoveryPlan(population, tuple(artifacts), tuple(actions), locations, source_ids)


def with_witnesses(plan, layer):
    """One interview = the witness's WHOLE memory, not split singleton tricks.

Visual descriptions of an assailant can narrow an identity. Presence, departures
and drink handling do NOT certify who killed; their current supports stay broad.
Descriptions are latent world facts: offline identity audits assume the cast's
appearances known. Learning/comparing those appearances is not integrated yet.
"""
    from dataclasses import replace
    from scenario_witnesses import statements, validate
    validate(layer)
    # Do not attach memories from a different crime to a compatible-looking map.
    if plan != project(layer.crime):
        raise ValueError("Witness layer requires its exact base discovery plan")
    artifacts, actions = list(plan.artifacts), list(plan.actions)
    artifacts.append(Artifact("victim_reference", "reference",
        "Une photo de la victime a été prise pour la montrer aux témoins.", ("body",), plan.population))
    actions = [replace(action, reveals=action.reveals + ("victim_reference",))
               if action.id == "inspect_scene" else action for action in actions]
    sources = plan.source_ids | frozenset(p.id for p in layer.perceptions)
    for witness in layer.witnesses:
        rows = statements(layer, witness.id)
        if not rows:
            continue
        artifacts.extend(Artifact(row.id, "testimony", row.text, row.sources, row.candidates) for row in rows)
        windows = tuple((p.start, p.end) for p in layer.presences if p.witness == witness.id)
        events = {e.id: e for e in layer.events}
        last_memory = max(events[p.event].minute for p in layer.perceptions if p.witness == witness.id)
        spoken_name = witness.name[0].lower() + witness.name[1:] if witness.name.startswith(("Le ", "La ")) else witness.name
        actions.append(DiscoveryAction("interview:" + witness.id, Operation.INTERVIEW,
            "Interroger " + spoken_name, witness.post, witness.id, tuple(row.id for row in rows),
            ("victim_reference",), last_memory, windows=windows))
    locations = tuple((n.id, n.label) for n in layer.streets.nodes) + tuple(
        (key, label) for key, label in plan.locations if key not in {n.id for n in layer.streets.nodes})
    return replace(plan, artifacts=tuple(artifacts), actions=tuple(actions), locations=locations,
                   source_ids=sources, projection_version=2)


def walkthrough(plan, *, start_at=1440 + 8 * 60):
    """Acquire all possible artifacts offline; no movement/AP simulation.

No killer passed to the deduction algebra. This deliberately reports unresolved
cases, rather than adding arbitrary suspect masks to obtain a happy solver score.
"""
    state, steps = DiscoveryState(), []
    while True:
        choices = [(ready, a.id, a) for a in plan.actions
                   if (ready := plan.next_time(a, state, after=start_at)) is not None]
        if not choices:
            break
        priorities = {Operation.INSPECT: 0, Operation.COLLECT: 1, Operation.EXAMINE: 2,
                      Operation.ANALYZE: 3, Operation.INTERVIEW: 4, Operation.ASK_STOCK: 5}
        at, _, action = min(choices, key=lambda row: (row[0], priorities[row[2].operation], row[1]))
        state, delivered = plan.perform(state, action.id, place=action.place, at=at)
        steps.append({"at": at, "action": action.public(), "received": list(delivered)})
    remaining = plan.graph().remaining(dict(state.known))
    return {"visibility": "offline_discovery_walkthrough", "steps": steps,
            "audit": {"artifacts_acquired": len(state.known), "artifacts_total": len(plan.artifacts),
                      "remaining_count": len(remaining), "unique_deduction": len(remaining) == 1},
            "note": ("Disponibilité et délais testés ; audit d'identité avec apparences supposées connues. Déplacements, PA et reconstitution complète non certifiés."
                     if plan.projection_version >= 2 else
                     "Disponibilité et délais testés ; déplacements, PA et reconstitution complète non certifiés.")}
