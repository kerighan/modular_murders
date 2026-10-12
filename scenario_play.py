"""Playable, in-memory CLI of the new causal generator. No legacy Game/DB.

Authoring can see truth. PlaySession and the blind playtester acquire only
public facts, obey movement/time gates, and do not use hidden candidate masks.
Run: python scenario_play.py --seed 7 --skills fingerprints,search
"""
import argparse
import random
import re
import shlex
from dataclasses import dataclass, replace

from scenario_crime import CrimeBuilder, NodeKind, ToolFate
from scenario_evidence import build_evidence, crime_window
from scenario_evening import build_evenings, build_registrations, evening_account, remembered_times, spoken_time
from scenario_kernel import KernelBuilder
from scenario_life import Link, build_life
from scenario_means import Method
from scenario_observations import (Artifact, DiscoveryAction, DiscoveryState,
                                   Operation, project, with_witnesses)
from scenario_victim import purpose_text
from scenario_witnesses import Aspect, EventKind, WitnessBuilder, statements


SKILLS = ("fingerprints", "search", "rapport", "lockpick")
SERVICE_PARENTS = {"lab": "police", "morgue": "hospital"}


def clock(minute):
    return f"{(minute % 1440) // 60:02d}:{minute % 60:02d}"


@dataclass(frozen=True)
class PlayCase:
    seed: object
    crime: object
    life: object
    witnesses: object
    evidence: object
    plan: object
    claims: dict  # authored PUBLIC semantics, not candidate masks
    objects: dict
    evenings: tuple
    registrations: tuple


def build_case(seed=0, *, focus_assault=0):
    crime = CrimeBuilder(seed).build(KernelBuilder(seed, people_count=8).sample())
    life = build_life(crime, seed)
    witnesses = WitnessBuilder(seed).build(crime, focus_assault=focus_assault)
    # Loose ends need a possible refutation. Ordinary grievances and romantic
    # context get corroboration where it fits the existing physical truth.
    # Never move somebody or falsify their itinerary to manufacture an alibi.
    victim = crime.kernel.roles.victim
    narrative_people = {p.id for p in life.people.values() if life.concerns(p.id)
                        or any(b.kind in (Link.PARTNERS, Link.EXES) for b in life.links(p.id, victim))}
    neutral = sorted(p.id for p in life.people.values() if p.id not in (
        victim, crime.kernel.roles.author, crime.kernel.roles.other))
    narrative_people.update(random.Random(f"early-progress:{seed}").sample(neutral, 2))
    evidence = build_evidence(crime, seed, witnesses.appearances, required_alibis=narrative_people)
    evenings = build_evenings(crime, evidence, seed)
    registrations = build_registrations(crime)
    plan = with_witnesses(project(crime), witnesses)
    population = plan.population
    people = life.people
    artifacts, actions, sources = list(plan.artifacts), list(plan.actions), set(plan.source_ids)
    claims, objects = {}, {}

    def add(key, kind, text, source, candidates=None, claim=None):
        sources.add(source)
        artifacts.append(Artifact(key, kind, text, (source,), population if candidates is None else frozenset(candidates)))
        if claim:
            claims[key] = claim

    # Player learns appearances by actually meeting people; the offline solver
    # must not lend its omniscient profile table to the player's deductions.
    for p in people.values():
        if p.id == crime.kernel.roles.victim:
            continue
        a = next(a for a in evidence.appearances if a.person == p.id)
        key = "profile:" + p.id
        text = f"{p.name} — Cheveux {a.hair.value}; manteau {a.coat.value}; {a.height.value}."
        add(key, "person", text, key, claim={"profile": p.id, "coat": a.coat.value, "height": a.height.value, "hair": a.hair.value})
        actions.append(DiscoveryAction("meet:" + p.id, Operation.INTERVIEW, "Parler à " + p.name,
                                       p.home, p.id, (key,)))
        record_key = "police_record:" + p.id
        add(record_key, "police_record", f"Fiche de {p.name}. Domicile : {dict(plan.locations)[p.home]}. Métier : {p.occupation.label}.\n"
            "Aucun antécédent judiciaire renseigné dans cette fiche.", record_key)
        actions.append(DiscoveryAction("record:" + p.id, Operation.READ,
            "Consulter la fiche et le casier de " + p.name, "police", "staff:police",
            (key, record_key)))
        evening = "evening:" + p.id
        presence = next((r for r in evidence.presences if r.person == p.id), None)
        add(evening, "personal_account", evening_account(crime, evidence, evenings, p.id),
            "evening_episode:" + p.id,
            claim={"account": p.id, "place": presence.place,
                   **remembered_times(presence), "source_actor": presence.witness} if presence else None)
        old = next((a for a in actions if a.id == "interview:" + p.id), None)
        if old:
            actions.remove(old)
        actions.append(DiscoveryAction("interview:" + p.id, Operation.INTERVIEW,
            "Demander les souvenirs de la soirée", p.home, p.id,
            (evening,), ("profile:" + p.id,)))
        observation_key = "observations:" + p.id
        borrowing = next((b for b in crime.mundane_borrowings if b.actor == p.id), None)
        observation_text = "Je n'ai rien à vous raconter sur ce qui lui est arrivé."
        if borrowing:
            keeper = next(k for k in crime.keepers if k.id == borrowing.permission_by)
            observation_text = f"Dans la journée, j'avais emprunté un objet à {dict(plan.locations)[keeper.place]}. {keeper.name} était là."
        observation_reveals = old.reveals if old else ()
        if borrowing or not observation_reveals:
            add(observation_key, "personal_account", observation_text, observation_key)
            observation_reveals = (observation_key,) + observation_reveals
        actions.append(DiscoveryAction("observe:" + p.id, Operation.INTERVIEW,
            "Demander les observations", p.home, p.id,
            observation_reveals, ("profile:" + p.id,)))
    # Archives are saved correspondence on a home terminal, not a carried phone
    # inexplicably teleported from the corpse to the victim's apartment.
    for home in sorted({p.home for p in people.values()}):
        residents = [p for p in people.values() if p.home == home]
        resident_ids = {p.id for p in residents}
        rows = [m for m in life.messages if m.sender in resident_ids or
                m.recipient in resident_ids and m.read_at is not None]
        texts = [f"{people[m.sender].name} → {people[m.recipient].name}, il y a {-m.sent_at // 1440 + 1} j : « {m.text} »" for m in rows]
        key = "archive:" + home
        concerns = {pid: [detail for source, detail in life.concerns(pid)
                          if any(m.source == source and pid in (m.sender, m.recipient) for m in rows)] for pid in sorted(population)}
        add(key, "correspondence", "Terminal domestique, correspondance conservée.\n" +
            ("\n".join(texts) if texts else "Pas d'échange conservé concernant la victime."), key,
            claim={"concerns": {pid: details for pid, details in concerns.items() if details}})
        actions.append(DiscoveryAction("read:" + home, Operation.READ,
            "Consulter la correspondance du terminal", home, "terminal:" + home, (key,)))
        pictures = [b for b in life.bonds if set(b.people) & resident_ids and
                    b.kind in (Link.PARTNERS, Link.EXES, Link.FRIENDS, Link.SIBLINGS)]
        if pictures:
            captions = []
            for b in pictures:
                names = " et ".join(people[p].name for p in b.people)
                detail = {Link.PARTNERS: "ensemble", Link.EXES: "ensemble sur une ancienne photo, prise avant leur séparation",
                          Link.FRIENDS: "à une sortie entre amis", Link.SIBLINGS: "dans l'album de famille"}[b.kind]
                captions.append(names + " — " + detail + ".")
            key = "photos:" + home
            romantic = {pid: ["Une histoire sentimentale relie cette personne à la victime."]
                        for pid in sorted(population) if any(
                            b.kind in (Link.PARTNERS, Link.EXES) and set(b.people) == {pid, victim} for b in pictures)}
            add(key, "relationship", "Albums et photos conservés.\n" + "\n".join(captions)
                + "\nCes souvenirs ne prouvent pas une implication dans le crime.", key,
                claim={"concerns": romantic})
            actions.append(DiscoveryAction("photos:" + home, Operation.READ,
                "Regarder les albums et photos", home, "album:" + home, (key,)))
        if crime.kernel.roles.victim in resident_ids:
            plan_key = "victim_diary"
            text = purpose_text(crime.victim_plan, people, crime.kernel)
            add(plan_key, "diary", "Agenda privé de la victime — « " + text + " ».\n"
                f"Destination prévue : {dict(plan.locations)[crime.victim_plan.destination]}, {clock(crime.victim_plan.expected_arrival_at)}.",
                crime.victim_plan.id, claim={"goal": "meet_person" if crime.victim_plan.goal.value == "meet_author" else crime.victim_plan.goal.value,
                    "appointment": {"host": crime.victim_plan.appointment.host,
                                    "time": crime.victim_plan.appointment.starts_at,
                                    "place": crime.victim_plan.appointment.place} if crime.victim_plan.appointment else None})
            actions.append(DiscoveryAction("read_diary", Operation.READ, "Lire l'agenda de la victime",
                home, "diary:" + home, (plan_key,)))
        found = tuple(s.tool for s in crime.tool_states if s.place == home and not s.concealed)
        mugs = tuple("mug:" + p.id for p in residents)
        objects["search:" + home] = found + mugs
        names = [next(t.kind.label for t in crime.inventory if t.id == tool) for tool in found]
        add("objects:" + home, "objects", "Objets examinés : " + ", ".join(names + ["tasse personnelle de " + p.name for p in residents]) + ".", "objects:" + home)
        actions.append(DiscoveryAction("search:" + home, Operation.SEARCH, "Examiner les objets du logement",
            home, "fixture:room:" + home, ("objects:" + home,)))
    if "collect_object" in {a.id for a in actions}:
        objects["collect_object"] = (crime.execution.tool,)
    # Every district has a bin, including empty ones. Never label the useful bin.
    for n in crime.streets.nodes:
        if n.kind is not NodeKind.STREET:
            continue
        d = evidence.disposal
        found = (d.tool,) if d and d.place == n.id and d.container == "bin" else ()
        text = ("Dans la poubelle : " + next(t.kind.label for t in crime.inventory if t.id == d.tool) +
                ". Objet récupéré; sa présence ici ne dit pas qui l'a déposé ni s'il a servi au crime."
                if found else "Emballages et déchets courants. Rien à conserver pour cette affaire.")
        add("bin:" + n.id, "container", text, "bin:" + n.id)
        actions.append(DiscoveryAction("search_bin:" + n.id, Operation.SEARCH,
            "Fouiller la poubelle", n.id, "bin:" + n.id, ("bin:" + n.id,)))
        objects["search_bin:" + n.id] = found
    # Coarse HIDDEN indoors really stays indoors, rather than becoming a helpful
    # bin in an unrelated street. A cupboard can also be searched without CCTV.
    if evidence.disposal and evidence.disposal.container == "cupboard":
        d = evidence.disposal
        key = "cupboard:" + d.place
        add(key, "container", "Un objet a été dissimulé derrière le fond d'un placard : " +
            next(t.kind.label for t in crime.inventory if t.id == d.tool) + ".", "weapon_disposition")
        actions.append(DiscoveryAction("search_cupboard", Operation.SEARCH, "Examiner le fond du placard",
            d.place, "cupboard:" + d.place, (key,)))
        objects["search_cupboard"] = (d.tool,)
    start, end = crime_window(crime)
    add("medical_window", "chronology", f"Rapport du médecin légiste — hier, entre {clock(start)} et {clock(end)}.\n"
        + ("L'intoxication s'est produite pendant cette période. Le décès est postérieur à l'administration ; je ne peux pas dater celle-ci à la minute près."
           if crime.method is Method.POISONED else "C'est la période de l'agression mortelle. L'examen du corps ne permet pas de donner une minute exacte."),
        "body", claim={"window": (start, end), "method": crime.method.value})
    actions = [replace(a, reveals=("medical_window",) + a.reveals) if a.id == "read_medical" else a for a in actions]
    # The same medical request can be made directly to the examiner at the morgue.
    request = next(a for a in actions if a.id == "request_exam")
    actions.append(replace(request, id="request_exam_morgue", place="morgue", actor="staff:medical",
                           label="Demander l'examen du corps et la datation du crime"))
    # Existing service staff verify real observed presences, not named extras.
    for p in evidence.presences:
        name = people[p.person].name
        if p.basis == "continuous_noncontact":
            text = f"Oui, {name}. Je m'occupais de sa table. Je n'ai pas regardé l'heure, mais du service du verre jusqu'au malaise, cette personne est restée sous mes yeux, sans toucher le verre de la victime."
            requires = ("medical_window", "drink_result")
        else:
            times = remembered_times(p)
            if not times or not (times["start"] <= start and end <= times["end"]):
                raise ValueError("The remembered service interval cannot certify this medical window")
            beginning, ending = spoken_time(times['start']), spoken_time(times['end'])
            versions = (
                f"Oui, {name}. À {beginning}, cette personne était déjà à sa table. Et à {ending}, encore là. Je faisais le service ; cette personne n'est pas sortie entre les deux.",
                f"{name} ? Oui, hier. Je m'occupais de sa table entre {beginning} et {ending}. Cette personne est restée sous mes yeux tout du long.",
                f"Je me souviens de {name}. Déjà là à {beginning}, toujours à sa table à {ending}. Je faisais le service et cette personne n'est pas sortie entre les deux.",
            )
            text = versions[int(p.person[1:]) % len(versions)]
            requires = ("medical_window",)
        add("alibi:" + p.person, "corroboration", text, p.id, population - {p.person},
            claim={"excludes": p.person, "requires": requires, "place": p.place,
                   **remembered_times(p), "source_actor": p.witness,
                   **({"event_span": ("drink_served", "victim_collapsed")} if p.basis == "continuous_noncontact" else {})})
        actions.append(DiscoveryAction("verify:" + p.person, Operation.VERIFY,
            "Vérifier le récit de " + name,
            p.place, p.witness, ("alibi:" + p.person,), ("evening:" + p.person,)))
    # Both existing keepers have a public conversation, even without a stock
    # incident. The register is post-authored from REAL venue visits on shift.
    for keeper in crime.keepers:
        visits = [r for r in registrations if r.keeper == keeper.id]
        texts = [f"{people[v.person].name} est passé, vers {spoken_time(((v.minute + 7) // 15) * 15)}."
                 for v in visits]
        seen = {v.person for v in visits}
        for p in evidence.presences:
            if p.witness != keeper.id or p.person in seen:
                continue
            times = remembered_times(p)
            when = "entre " + spoken_time(times["start"]) + " et " + spoken_time(times["end"]) if times else "pendant le service"
            texts.append(f"{people[p.person].name} était à une table que je servais {when}.")
        key = "venue_register:" + keeper.place
        text = " ".join(texts) + " Pour les autres clients, mes souvenirs sont moins précis." if texts else "Je ne peux vous citer personne avec certitude pour cette soirée. Ça ne veut pas dire que personne n'est venu."
        add(key, "venue_register", text, key)
        if visits:
            sources.update(v.id for v in visits)
            artifacts[-1] = replace(artifacts[-1], sources=tuple(v.id for v in visits))
        sources.update(p.id for p in evidence.presences if p.witness == keeper.id)
        artifacts[-1] = replace(artifacts[-1], sources=artifacts[-1].sources + tuple(
            p.id for p in evidence.presences if p.witness == keeper.id))
        actions.append(DiscoveryAction("venue_guests:" + keeper.place, Operation.INTERVIEW,
            "Demander les clients de la soirée", keeper.place, keeper.id, (key,)))
    # Extract public semantics of an assailant description, not its hidden mask.
    for w in witnesses.witnesses:
        for row in statements(witnesses, w.id):
            perception = next(p for p in witnesses.perceptions if row.sources == (p.id,))
            event = next(e for e in witnesses.events if e.id == perception.event)
            if event.kind is EventKind.ASSAULT and perception.aspect is not Aspect.SILHOUETTE:
                a = next(a for a in evidence.appearances if a.person == perception.actor)
                aspect = perception.aspect.value
                claims[row.id] = {"description": aspect, "value": getattr(a, aspect).value}
    # Cameras are queried by district AND hour. Empty windows don't materialize
    # huge meaningless solver states; query history lives in the player journal.
    for cam in evidence.cameras:
        for hour in sorted({c.minute // 60 for c in evidence.clips if c.place == cam.place}):
            clips, text = evidence.camera_query(cam.place, hour)
            key = f"camera:{cam.place}:{hour}"
            support = population.intersection(*(evidence.support(c) for c in clips))
            add(key, "footage", text, key, support)
            criminal = next((c for c in clips if c.event == "assault" and c.aspect is not Aspect.SILHOUETTE), None)
            if criminal:
                a = next(a for a in evidence.appearances if a.person == criminal.actor)
                aspect = criminal.aspect.value
                claims[key] = {"description": aspect, "value": getattr(a, aspect).value}
            actions.append(DiscoveryAction(key, Operation.CAMERA, "Consulter la caméra locale",
                cam.place, "camera:" + cam.place, (key,), ("scene_body",)))
    plan = replace(plan, artifacts=tuple(artifacts), actions=tuple(actions), source_ids=frozenset(sources), projection_version=3)
    return PlayCase(seed, crime, life, witnesses, evidence, plan, claims, objects, evenings, registrations)


def sample_playable(seed=0, max_attempts=200, *, proof_family=None):
    """Reject unsolvable identity graphs; do not patch truth or pad clue masks.
    This is NOT a certification of a full causal reconstruction.
    """
    family = proof_family or random.Random(f"proof-policy-v1:{seed}").choice(("accounts", "cross", "open"))
    if family not in ("accounts", "cross", "open"):
        raise ValueError("Unknown proof family")
    for attempt in range(max_attempts):
        candidate_seed = seed if attempt == 0 else f"{seed}:retry:{attempt}"
        try:
            case = build_case(candidate_seed, focus_assault={"accounts": 2, "cross": 1, "open": 0}[family])
        except ValueError as error:
            if "non-assault crime" not in str(error):
                raise
            continue
        graph = case.plan.graph()
        keys = {a.id for a in case.plan.artifacts}
        if family != "open":
            kinds = {"testimony"} if family == "accounts" else {"testimony", "footage"}
            keys = {a.id for a in case.plan.artifacts if a.kind in kinds}
        if (graph.remaining(keys) == {case.crime.kernel.roles.author}
                and len(case.evidence.presences) >= 2 and context_is_refutable(case)):
            return case
    raise ValueError("No playable case found within the rejection budget")


def context_is_refutable(case):
    """Authoring certificate: every innocent narrative hook has an actual exit.

    Use independent corroboration OR incompatible assault descriptions, never
    a fictitious confession/relationship mask. This does not expose the exit to
    the player before its sources have been discovered.
    """
    victim, author = case.crime.kernel.roles.victim, case.crime.kernel.roles.author
    descriptions = [c for c in case.claims.values() if "description" in c]
    for pid in case.plan.population - {author}:
        if not case.life.concerns(pid) and not any(b.kind in (Link.PARTNERS, Link.EXES) for b in case.life.links(pid, victim)):
            continue
        if any(p.person == pid for p in case.evidence.presences):
            continue
        profile = case.claims["profile:" + pid]
        if not any(profile[c["description"]] != c["value"] for c in descriptions):
            return False
    return True


class PlaySession:
    def __init__(self, case, skills=("search", "rapport")):
        if len(set(skills)) != 2 or not set(skills) <= set(SKILLS):
            raise ValueError("Choose exactly two distinct skills: " + ", ".join(SKILLS))
        self.case, self.skills = case, frozenset(skills)
        self.state, self.at, self.place = DiscoveryState(), 1440 + 8 * 60, case.crime.scene
        self.journal, self.found, self.prints, self.marks = [], set(), {}, {}
        self.object_places, self.carried = {}, set()
        self.finished = False
        self.person_places = {pid: case.life.people[pid].home for pid in case.plan.population}
        self.doorstep = None
        self.discovery_places = {}

    def person_place(self, pid):
        place = self.person_places[pid]
        return self.place if place == self.doorstep else place

    @property
    def effective_plan(self):
        # Personal testimony follows its speaker; domestic objects stay home.
        key = tuple((pid, self.person_place(pid)) for pid in sorted(self.person_places))
        if getattr(self, "_plan_cache_key", None) == key:
            return self._plan_cache
        self._plan_cache_key = key
        self._plan_cache = replace(self.case.plan, actions=tuple(
            replace(a, place=self.person_place(a.actor)) if a.actor in self.person_places
            and a.operation is Operation.INTERVIEW else a for a in self.case.plan.actions))
        return self._plan_cache

    @property
    def locations(self):
        return dict(self.case.plan.locations)

    def named_people(self):
        """A name in an acquired statement identifies no physical attribute.

        Match whole names in the actual text received, never in unrevealed
        source records, action catalogues, or the narrator's private facts.
        Profiles still require a meeting or a police record.
        """
        known = dict(self.state.known)
        text = "\n".join(row["text"] for row in self.journal)
        return frozenset(pid for pid in self.case.plan.population
                         if "profile:" + pid in known or re.search(
                             r"(?<!\w)" + re.escape(self.case.life.people[pid].name) + r"(?!\w)", text))

    def go(self, place):
        if place not in self.locations:
            raise ValueError("Unknown location")
        streets = self.case.witnesses.streets
        # Lab is accessed through the police station, morgue through hospital;
        # the physical murder map itself is not changed.
        origin = self.place if self.place in streets._adjacency else SERVICE_PARENTS[self.place]
        target = place if place in streets._adjacency else SERVICE_PARENTS[place]
        minutes = sum(streets.duration(a, b) for a, b in zip(streets.path(origin, target), streets.path(origin, target)[1:]))
        minutes += 3 * (self.place not in streets._adjacency) + 3 * (place not in streets._adjacency)
        self.at += minutes
        self.place = place
        return f"{self.locations[place]} — {clock(self.at)}, trajet {minutes} min."

    def options(self):
        return tuple(row for row in self.effective_plan.available(self.state, place=self.place, at=self.at)
                     if row["operation"] != Operation.CAMERA.value
                     and not (row["id"] in ("request_exam", "request_exam_morgue")
                              and "exam_request" in dict(self.state.known)))

    def do(self, action):
        if action in ("request_exam", "request_exam_morgue") and "exam_request" in dict(self.state.known):
            raise ValueError("L'examen est déjà demandé ; le rapport sera remis à la morgue.")
        return self._discover(action, self.place)

    def alibi_state(self, pid):
        known = dict(self.state.known)
        key = "alibi:" + pid
        if key in known:
            return "confirmed" if set(self.case.claims[key].get("requires", ())) <= known.keys() else "corroborated"
        return "reported" if "evening:" + pid in known else "unknown"

    def timeline(self):
        """Only the timestamps the player has actually heard or read."""
        known, labels = dict(self.state.known), self.locations
        rows = []
        for key, claim in self.case.claims.items():
            if key not in known:
                continue
            if key == "medical_window":
                start, end = claim["window"]
                rows.append({"id": key, "start": start, "end": end, "kind": "medical",
                    "status": "verified", "title": "Période du crime · rapport médical",
                    "text": next(r["text"] for r in self.journal if r["id"] == key), "place": "morgue"})
            elif key.startswith(("evening:", "alibi:")) and "start" in claim:
                pid = claim.get("account", claim.get("excludes"))
                # Replace the unconfirmed row when an independent source is heard.
                if key.startswith("evening:") and "alibi:" + pid in known:
                    continue
                confirmed = key.startswith("alibi:")
                rows.append({"id": key, "start": claim["start"], "end": claim["end"],
                    "kind": "alibi", "status": "verified" if confirmed else "reported",
                    "title": self.case.life.people[pid].name + " · " + labels[claim["place"]],
                    "text": next(r["text"] for r in self.journal if r["id"] == key),
                    "place": claim["place"], "person": pid, "alibi_state": self.alibi_state(pid)})
            elif key == "victim_diary" and claim.get("appointment"):
                ap = claim["appointment"]
                rows.append({"id": key, "start": ap["time"], "end": ap["time"], "kind": "appointment",
                    "status": "planned", "title": "Rendez-vous prévu · " + self.case.life.people[ap["host"]].name,
                    "text": "L'agenda indique un rendez-vous prévu, pas une présence attestée.", "place": ap["place"]})
            elif key.startswith("camera:"):
                _, place, hour = key.split(":")
                clips, text = self.case.evidence.camera_query(place, int(hour))
                lines = {c.id: line for c, line in zip(clips, text.splitlines())}
                for clip in self.case.evidence.clips:
                    if clip.place == place and clip.minute // 60 == int(hour):
                        rows.append({"id": clip.id, "start": clip.minute, "end": clip.minute,
                            "kind": "camera", "status": "verified", "title": "CCTV · " + labels[place],
                            "text": lines[clip.id], "place": place})
        for witness in self.case.witnesses.witnesses:
            for statement in statements(self.case.witnesses, witness.id):
                if statement.id not in known:
                    continue
                perception = next(p for p in self.case.witnesses.perceptions if statement.sources == (p.id,))
                event = next(e for e in self.case.witnesses.events if e.id == perception.event)
                # Match the spoken approximation, not the private exact minute.
                match = re.search(r"vers (\d{1,2}) h(?: (\d{2}))?", statement.text)
                if match:
                    minute = int(match[1]) * 60 + int(match[2] or 0)
                    rows.append({"id": statement.id, "start": minute, "end": minute,
                        "kind": "testimony", "status": "reported", "title": witness.name + " · souvenir",
                        "text": statement.text, "place": event.place})
        return sorted(rows, key=lambda r: (r["start"], r["end"], r["id"]))

    def _discover(self, action, source_place):
        if self.finished:
            raise ValueError("This investigation has ended")
        self.state, rows = self.effective_plan.perform(self.state, action, place=source_place, at=self.at)
        self.discovery_places[action] = source_place
        self.journal.extend(rows)
        discovered = self.case.objects.get(action, ())
        self.found.update(discovered)
        for obj in discovered:
            self.object_places[obj] = source_place
        if action.startswith("search_bin:") or action in ("collect_object", "search_cupboard"):
            self.carried.update(discovered)
        operation = next(a.operation for a in self.case.plan.actions if a.id == action)
        self.at += ((3 if "search" in self.skills else 10) if operation is Operation.SEARCH else
                    3 if "rapport" in self.skills and operation in (Operation.INTERVIEW, Operation.VERIFY) else 5)
        return "\n\n".join(row["text"] for row in rows)

    def camera(self, hour, *, place=None):
        # Camera location is the source of the recording, not a teleport of the
        # detective. CLI defaults to local access; the 3D facade gates remote
        # access at the video control room before calling this acquisition.
        source_place = self.place if place is None else place
        if "scene_body" not in dict(self.state.known):
            raise ValueError("Examine the scene first")
        clips, text = self.case.evidence.camera_query(source_place, hour)
        key = f"camera:{source_place}:{hour}"
        if key in self.state.completed or any(r["id"] == key for r in self.journal):
            raise ValueError("This recording is already in your notebook")
        if clips:
            return self._discover(key, source_place)
        self.at += 5
        self.journal.append({"id": key, "kind": "footage", "text": text})
        return text

    def camera_window(self, start, end, *, place):
        """Broad query; each consultation still has >=2 compatible people.

        Incompatible descriptions require another consultation of the same
        window rather than becoming a one-tap unique identification.
        """
        if "scene_body" not in dict(self.state.known):
            raise ValueError("Examine the scene first")
        if not (0 <= start < end <= 24):
            raise ValueError("Invalid recording window")
        marker = f"camera_window:{place}:{start}"
        cached = next((r for r in self.journal if r["id"] == marker), None)
        if cached:
            return cached["text"], False
        done = {r["id"] for r in self.journal}
        existing = [r["text"] for r in self.journal if r["id"].startswith("camera:" + place + ":")
                    and start <= int(r["id"].split(":")[-1]) < end]
        rows = [a for a in self.case.plan.artifacts if a.id.startswith("camera:" + place + ":")
                and start <= int(a.id.split(":")[-1]) < end and a.id not in done]
        support, chosen = self.case.plan.population, []
        for row in rows:
            compatible = support & row.candidates
            if len(compatible) >= 2:
                support = compatible
                chosen.append(row)
        at, texts = self.at, []
        for row in chosen:
            self.at = at
            texts.append(self.camera(int(row.id.split(":")[-1]), place=place))
        self.at = at + (5 if chosen or not existing else 0)
        fresh = bool(chosen or not existing)
        if not texts and not existing:
            camera = next(c for c in self.case.evidence.cameras if c.place == place)
            text = "La caméra de ce quartier était hors service hier." if not camera.online else "Rien d'exploitable sur ce créneau. Cela ne prouve pas que personne n'est passé."
            self.journal.append({"id": f"empty_window:{place}:{start}", "kind": "footage", "text": text})
            texts.append(text)
        text = "\n\n".join(existing + texts)
        if len(chosen) == len(rows):
            self.journal.append({"id": marker, "kind": "recording_window", "text": text})
        return text, fresh

    def fingerprint(self, obj):
        if "fingerprints" not in self.skills:
            raise ValueError("Il faut la compétence Relevé d'empreintes (un des deux slots).")
        if obj not in self.found:
            raise ValueError("L'objet doit avoir été examiné ou récupéré.")
        if obj not in self.carried and self.object_places[obj] != self.place:
            raise ValueError("Retournez au logement où se trouve l'objet pour relever son empreinte.")
        if obj in self.prints:
            raise ValueError("Déjà relevé; consultez le carnet.")
        contacts = [c for c in self.case.evidence.contacts if c.object == obj]
        patterns = []
        for c in contacts:
            # Only usable partial patterns shared by >=2 actual cast members;
            # no unique print becoming a one-step criminal identity oracle.
            members = {r.person for r in self.case.evidence.contacts if r.object.startswith("mug:") and r.ridge == c.ridge}
            if len(members & self.case.plan.population) >= 2:
                patterns.append(c.ridge)
        self.prints[obj] = tuple(sorted(set(patterns)))
        text = ("Empreinte partielle : " + ", ".join(self.prints[obj]) +
                ". Comparaison possible avec d'autres objets relevés; un contact ne date pas le geste et ne prouve pas le meurtre."
                if patterns else "Aucune empreinte suffisamment exploitable pour une comparaison.")
        matches = [key for key, value in self.prints.items() if key != obj and set(value) & set(self.prints[obj])]
        if matches:
            text += "\nMotif partiel également présent sur : " + ", ".join(self.object_label(key) for key in matches) + ". Pas une identification certaine."
        self.at += 8
        self.journal.append({"id": "print:" + obj, "kind": "contact", "text": self.object_label(obj) + " — " + text})
        return text

    def analyze_object(self, obj):
        if self.place != "lab" or obj not in self.carried:
            raise ValueError("Apportez l'objet récupéré au laboratoire.")
        known = dict(self.state.known)
        surface = next((r for r in self.case.evidence.surfaces if r.object == obj), None)
        key = "surface:" + obj
        if any(r["id"] == key for r in self.journal):
            raise ValueError("Cette analyse est déjà dans le carnet.")
        if surface is not None and surface.kind == "victim_blood":
            if "blood_reference" not in known:
                raise ValueError("Le laboratoire attend le prélèvement de comparaison de la morgue.")
            text = "Du sang correspondant au prélèvement de la victime est présent sur cet objet. Un contact avec son sang est établi; cela ne dit pas qui tenait l'objet."
        elif surface is not None:
            if "drink_result" not in known:
                raise ValueError("Faites d'abord analyser le verre pour disposer d'une comparaison.")
            text = "Le produit restant dans ce flacon est compatible avec la substance retrouvée dans le verre. Plusieurs flacons de ce produit existent : ce résultat n'identifie pas celui qui aurait été utilisé."
        else:
            text = "Aucune trace exploitable reliant cet objet aux prélèvements de l'affaire. Cela ne prouve pas qu'il n'a jamais été manipulé."
        self.at += 20
        self.journal.append({"id": key, "kind": "laboratory_contact", "text": self.object_label(obj) + " — " + text})
        return text

    def object_label(self, obj):
        if obj.startswith("mug:"):
            return "tasse personnelle de " + self.case.life.people[obj.removeprefix("mug:")].name
        return next(t.kind.label for t in self.case.crime.inventory if t.id == obj)

    def leads(self):
        """Detective's organization of already acquired material, not NPC advice.
        Labels deliberately express questions rather than hidden answers.
        """
        known = dict(self.state.known)
        rows = []
        if "exam_request" in known and "medical_window" not in known:
            rows.append("Examen demandé — résultat à consulter à la morgue après le délai annoncé.")
        if "victim_diary" in known:
            rows.append("Dernier déplacement — " + next(r["text"] for r in self.journal if r["id"] == "victim_diary"))
        if any("paie" in r["text"] or "heures supplémentaires" in r["text"] or "vol au travail" in r["text"] for r in self.journal):
            rows.append("Problème au travail — évoqué dans les échanges recueillis. Les contacts professionnels peuvent en connaître une partie, pas forcément tout.")
        if any("sépare" in r["text"] or "Notre histoire" in r["text"] or "Je suis avec" in r["text"] for r in self.journal):
            rows.append("Histoire sentimentale — des liens ou une rupture ont été évoqués. Cela ne dit pas qui a tué.")
        for r in self.journal:
            if r["kind"] == "footage" and "glisse un objet" in r["text"]:
                rows.append("Objet jeté — " + r["text"])
        if self.prints:
            rows.append("Contacts avec les objets — les motifs partiels relevés sont comparables dans le carnet; ils ne datent pas les contacts.")
        return tuple(rows) or ("Aucune piste organisée pour l'instant; le carnet reste vide jusqu'aux premières observations.",)

    def remaining(self):
        """Only learned public semantics. Unknown profiles are not eliminated.
        Visual flags remain player aids and do not alter this calculation.
        """
        known = dict(self.state.known)
        profiles = {c["profile"]: c for key, c in self.case.claims.items() if key in known and "profile" in c}
        remaining = set(self.case.plan.population)
        for key, claim in self.case.claims.items():
            if key not in known:
                continue
            if "excludes" in claim:
                if set(claim.get("requires", ())) <= known.keys():
                    remaining.discard(claim["excludes"])
            if "description" in claim:
                remaining -= {p for p, profile in profiles.items() if profile[claim["description"]] != claim["value"]}
        return frozenset(remaining)

    def deductions(self):
        """Explain public comparisons without hidden profiles or truth masks.

        These are factual notebook annotations, not automatic manual markings.
        A mere passage, relationship or partial print never rules somebody out.
        """
        known = dict(self.state.known)
        profiles = {c["profile"]: c for key, c in self.case.claims.items() if key in known and "profile" in c}
        result = {pid: [] for pid in self.case.plan.population}
        labels = {"hair": "Cheveux", "coat": "Manteau", "height": "Taille"}
        for key, claim in self.case.claims.items():
            if key not in known:
                continue
            if "excludes" in claim and set(claim.get("requires", ())) <= known.keys():
                result[claim["excludes"]].append({"source": key,
                    "text": "Un témoignage indépendant couvre toute la période de l'acte mortel."
                            if self.case.crime.method is not Method.POISONED else
                            "Cette personne était ailleurs pendant toute la période possible de l'intoxication."
                            if claim["place"] != self.case.crime.scene else
                            "Le personnel a observé cette personne sans contact avec le verre, du service jusqu'au malaise."})
            if "description" in claim:
                aspect = claim["description"]
                for pid, profile in profiles.items():
                    if profile[aspect] != claim["value"]:
                        result[pid].append({"source": key,
                            "text": f"{labels[aspect]} : {profile[aspect]}. La description de l'agression indique : {claim['value']}."})
        return result

    def inquiry_threads(self):
        """Named loose ends from acquired correspondence, context and accounts."""
        known = dict(self.state.known)
        concerns = {}
        for key, claim in self.case.claims.items():
            if key in known:
                for pid, details in claim.get("concerns", {}).items():
                    concerns.setdefault(pid, []).extend(details)
        for row in self.journal:
            if not row["id"].startswith("context:"):
                continue
            _, pid, topic = row["id"].split(":", 2)
            if topic == "motive" and self.case.life.concerns(pid):
                # The answer may summarize only one concern. Do not reveal other
                # unseen disputes from the private life catalogue.
                concerns.setdefault(pid, []).append(row["text"])
            elif topic == "relation" and any(b.kind in (Link.PARTNERS, Link.EXES) for b in self.case.life.links(pid)):
                concerns.setdefault(pid, []).append(row["text"])
        deductions = self.deductions()
        rows = []
        for pid in sorted(concerns):
            details = list(dict.fromkeys(concerns[pid]))
            reasons = deductions[pid]
            verification = next((a for a in self.case.plan.actions if a.id == "verify:" + pid), None)
            corroborated = "alibi:" + pid in known
            state = "refuted" if reasons else "awaiting_time" if corroborated else "open"
            # A destination is not privileged knowledge: require a personal
            # story naming the witness before displaying its meeting point.
            destination = verification.place if verification and "evening:" + pid in known and not corroborated else None
            rows.append({"person": pid, "state": state, "details": details,
                         "reasons": reasons, "destination": destination})
        return tuple(rows)

    def talk_about(self, person, other):
        if person not in self.case.plan.population or self.person_place(person) != self.place:
            raise ValueError("Il faut rejoindre cette personne pour lui parler.")
        if "profile:" + person not in dict(self.state.known):
            raise ValueError("Commencez la conversation via l'action Parler à…")
        text = self.case.life.answer_about(person, other)
        key = "about:" + person + ":" + other
        if not any(row["id"] == key for row in self.journal):
            self.journal.append({"id": key, "kind": "relationship", "text": self.case.life.people[person].name + " — « " + text + " »"})
            self.at += 3 if "rapport" in self.skills else 5
        return text

    def ask_context(self, person, topic):
        """Already-authored personal facts, not an invented murder testimony."""
        if topic not in ("relation", "work", "habits", "messages", "evening", "motive", "appointment"):
            raise ValueError("Unknown context topic")
        if person not in self.case.plan.population or self.person_place(person) != self.place:
            raise ValueError("Il faut rejoindre cette personne pour lui parler.")
        if "profile:" + person not in dict(self.state.known):
            raise ValueError("Commencez par rencontrer cette personne.")
        if topic == "messages" and any(a.id == "ask_messages:" + person for a in self.case.plan.actions) and "ask_messages:" + person not in self.state.completed:
            raise ValueError("Recueillez cet échange par son action de découverte.")
        if topic == "appointment":
            if "victim_diary" not in dict(self.state.known) or not self.case.claims["victim_diary"]["appointment"]:
                raise ValueError("Ce rendez-vous n'a pas encore été découvert.")
            appointment = self.case.crime.victim_plan.appointment
            victim = self.case.life.people[self.case.crime.kernel.roles.victim].name
            if person == appointment.host:
                text = f"Oui, {victim} et moi avions rendez-vous vers {clock(appointment.starts_at)}."
                text += " J'ai attendu, mais personne n'est venu." if any(m.observer == person for m in self.case.crime.missed_appointments) else " On s'est retrouvés dehors pour parler."
            else:
                text = "Ce rendez-vous ne me dit rien. Nous n'en avions pas parlé."
        else:
            text = evening_account(self.case.crime, self.case.evidence, self.case.evenings, person) if topic == "evening" else self.case.life.answer(person, topic)
        key = "context:" + person + ":" + topic
        if not any(row["id"] == key for row in self.journal):
            self.journal.append({"id": key, "kind": "conversation", "text": self.case.life.people[person].name + " — « " + text + " »"})
            self.at += 3 if "rapport" in self.skills else 5
        return text

    def board(self):
        """Map of currently visible people/fixtures, never their future replies.
        Used by both the CLI and blind exploratory playtester.
        """
        result = []
        for place, label in self.locations.items():
            rows = [row for row in self.effective_plan.available(self.state, place=place, at=self.at)
                    if row["operation"] != Operation.CAMERA.value]
            result.append({"place": place, "label": label, "actions": rows,
                           "camera": any(c.place == place for c in self.case.evidence.cameras)})
        return tuple(result)

    def accuse(self, person, method=None, goal=None):
        known = dict(self.state.known)
        if person not in self.case.plan.population:
            raise ValueError("Choose an existing suspect")
        if "medical_window" not in known or "victim_diary" not in known:
            return False, "Il manque la méthode ou le dernier projet de la victime. L'accusation n'est pas encore déposée."
        if method is not None and method not in {m.value for m in Method}:
            raise ValueError("Unknown method")
        if goal is not None and goal != self.case.claims["victim_diary"]["goal"]:
            return False, "Cette reconstitution du dernier déplacement contredit l'agenda consulté."
        if self.remaining() != {person}:
            return False, "Le dossier laisse encore plusieurs possibilités. L'accusation n'est pas encore déposée."
        # Only the final adjudicator consults private truth, not the player's bot.
        success = person == self.case.crime.kernel.roles.author and (method is None or method == self.case.crime.method.value)
        self.finished = True
        if not success:
            return False, "Accusation rejetée : la reconstitution est erronée."
        return True, ("Dossier établi : " + self.case.life.people[person].name + ".\n"
                      "Méthode : " + self.case.crime.method.label + ".\n"
                      "Le contexte éclaire le geste, mais les liens et les griefs ne prouvaient pas à eux seuls la culpabilité.")


HELP = """Commandes :
  lieux                         lieux, habitants et objets accessibles
  aller ID                      se déplacer (ID affiché dans lieux)
  voir                          actions numérotées du lieu
  faire N                       effectuer une action affichée
  demander NOM AUTRE_NOM         questionner quelqu'un sur une autre personne
  question NOM SUJET             mobile / témoin / alibi / lien / métier / rdv
  camera HEURE                  caméra de ce quartier, hier, HEURE à HEURE+1
  objets / empreinte N           objets examinés / relevé avec la compétence
  analyse N                     analyser un objet récupéré, au laboratoire
  carnet / pistes / horaires    notes / fils de l'enquête / chronologie acquise
  suspects / recouper            profils connus / recoupements publics
  suivre NOM / ecarter NOM       aide visuelle uniquement
  attendre MINUTES              laisser passer un délai
  accuser NOM                   déposer le dossier si suffisamment recoupé
  aide / quitter
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Neon Noir — nouveau générateur causal, CLI expérimentale")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--skills", default="search,rapport", help="Deux parmi fingerprints,search,rapport")
    args = parser.parse_args(argv)
    try:
        session = PlaySession(sample_playable(args.seed), tuple(args.skills.split(",")))
    except ValueError as error:
        parser.error(str(error))
    people, case = session.case.life.people, session.case
    victim = people[case.crime.kernel.roles.victim]
    print(f"NEON NOIR — {victim.name} ({victim.occupation.label}, {victim.workplace.label}) : décès suspect.\n"
          f"Vous arrivez le lendemain à 08:00, {session.locations[session.place]}.\n"
          f"Les {len(case.plan.population)} personnes du dossier sont des contacts à vérifier, pas des coupables présumés.\n"
          "Compétences : " + ", ".join(sorted(session.skills)) + ".\n" + HELP)
    while not session.finished:
        try:
            words = shlex.split(input(f"[{clock(session.at)} {session.locations[session.place]}] > "))
            if not words:
                continue
            cmd, *rest = words
            if cmd in ("quitter", "quit", "exit"):
                break
            if cmd == "aide":
                print(HELP)
            elif cmd == "lieux":
                for key, label in session.locations.items():
                    residents = [p.name for p in people.values() if p.home == key and p.id != victim.id]
                    objects = "; caméra + poubelle" if key in case.crime.streets._adjacency and case.crime.streets.kind(key) is NodeKind.STREET else ""
                    visible = next(row for row in session.board() if row["place"] == key)
                    actors = sorted({r["label"] for r in visible["actions"] if r["operation"] in (Operation.INTERVIEW.value, Operation.VERIFY.value)})
                    print(f"{key:22} {label}" + (" — " + ", ".join(residents) if residents else "") + objects)
                    for actor in actors:
                        print("  " + actor)
            elif cmd == "aller":
                print(session.go(" ".join(rest)))
            elif cmd == "voir":
                options = session.options()
                for i, row in enumerate(options, 1):
                    print(f"{i}. {row['label']}")
                if not options:
                    print("Pas de nouvelle action disponible maintenant.")
                pending = [a for a in case.plan.actions if a.place == session.place and a.operation is not Operation.CAMERA
                           and a.id not in session.state.completed and set(a.requires) <= dict(session.state.known).keys()
                           and (ready := case.plan.next_time(a, session.state, after=session.at)) is not None and ready > session.at]
                for a in pending:
                    print(f"En attente : {a.label}, disponible à {clock(case.plan.next_time(a, session.state, after=session.at))}.")
                if any(cam.place == session.place for cam in case.evidence.cameras):
                    print("Caméra locale : camera HEURE (hier). Poubelle fouillable ci-dessus.")
            elif cmd == "faire":
                i = int(rest[0])
                options = session.options()
                if not 1 <= i <= len(options):
                    raise ValueError("Numéro d'action invalide")
                print(session.do(options[i - 1]["id"]))
            elif cmd == "camera":
                print(session.camera(int(rest[0])))
            elif cmd == "objets":
                for i, obj in enumerate(sorted(session.found), 1):
                    print(f"{i}. {session.object_label(obj)} — {session.locations[session.object_places[obj]]}" +
                          (" (récupéré)" if obj in session.carried else "") + (" — déjà relevé" if obj in session.prints else ""))
            elif cmd in ("empreinte", "analyse"):
                i = int(rest[0])
                objects = sorted(session.found)
                if not 1 <= i <= len(objects):
                    raise ValueError("Numéro d'objet invalide")
                print(session.fingerprint(objects[i - 1]) if cmd == "empreinte" else session.analyze_object(objects[i - 1]))
            elif cmd == "carnet":
                for row in session.journal:
                    print(f"\n[{row['kind']}] {row['text']}")
            elif cmd in ("horaires", "chronologie"):
                rows = session.timeline()
                if not rows:
                    print("Aucun horaire recueilli. Un récit, un document ou le rapport du légiste peut en apporter.")
                for row in rows:
                    status = {"verified": "corroboré", "reported": "déclaré / approximatif", "planned": "prévu, pas attesté"}[row["status"]]
                    interval = clock(row["start"]) + (" – " + clock(row["end"]) if row["start"] != row["end"] else "")
                    print(f"Hier · {interval} · {row['title']} [{status}]\n  {row['text']}")
            elif cmd == "pistes":
                print("\n\n".join(session.leads()))
                for thread in session.inquiry_threads():
                    print("\n" + people[thread["person"]].name + " — " + {"open": "à recouper", "awaiting_time": "témoignage recueilli, période à établir", "refuted": "hypothèse infirmée"}[thread["state"]])
                    print("\n".join(thread["details"]))
                    for reason in thread["reasons"]:
                        print(reason["text"])
            elif cmd == "demander":
                if len(rest) != 2:
                    raise ValueError("demander NOM AUTRE_NOM")
                a = next((p.id for p in people.values() if p.name.casefold() == rest[0].casefold()), None)
                b = next((p.id for p in people.values() if p.name.casefold() == rest[1].casefold()), None)
                print(session.talk_about(a, b))
            elif cmd == "question":
                if len(rest) != 2:
                    raise ValueError("question NOM mobile|témoin|alibi|lien|métier|rdv")
                pid = next((p.id for p in people.values() if p.name.casefold() == rest[0].casefold()), None)
                topic = {"mobile": "motive", "témoin": "observations", "temoin": "observations",
                         "alibi": "evening", "lien": "relation", "métier": "work", "metier": "work", "rdv": "appointment"}.get(rest[1].casefold())
                if not pid or not topic:
                    raise ValueError("Personne ou sujet inconnu")
                if topic in ("observations", "evening"):
                    print(session.do(("observe:" if topic == "observations" else "interview:") + pid))
                else:
                    print(session.ask_context(pid, topic))
            elif cmd in ("suspects", "recouper"):
                eligible = session.remaining() if cmd == "recouper" else case.plan.population
                for p in sorted(eligible, key=lambda key: (session.marks.get(key) != "suivre", session.marks.get(key) == "ecarter", people[key].name)):
                    profile = "rencontré" if "profile:" + p in dict(session.state.known) else "profil encore inconnu"
                    print(people[p].name + " — " + profile + " " + session.marks.get(p, ""))
                if cmd == "recouper":
                    print("Compatible avec les seuls faits obtenus. Les empreintes et les griefs restent des pistes de contact/contexte.")
                    for pid, reasons in session.deductions().items():
                        if reasons:
                            print(people[pid].name + " — " + " ".join(r["text"] for r in reasons))
            elif cmd in ("suivre", "ecarter", "accuser"):
                name = " ".join(rest).casefold()
                person = next((p.id for p in people.values() if p.id != victim.id and p.name.casefold() == name), None)
                if person is None:
                    raise ValueError("Nom de suspect inconnu")
                if cmd == "accuser":
                    success, text = session.accuse(person)
                    print(text)
                else:
                    session.marks[person] = cmd
                    print("Repère visuel mis à jour; aucune preuve ajoutée.")
            elif cmd == "attendre":
                minutes = int(rest[0])
                if not 1 <= minutes <= 360:
                    raise ValueError("Attendre entre 1 et 360 minutes")
                session.at += minutes
            else:
                print("Commande inconnue; aide pour la liste.")
        except (ValueError, IndexError) as error:
            print("Action impossible :", error)
        except (EOFError, KeyboardInterrupt):
            print("\nEnquête interrompue.")
            break


if __name__ == "__main__":
    main()
