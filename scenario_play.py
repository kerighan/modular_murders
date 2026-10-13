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
from scenario_sampler import Motive
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


def build_case(seed=0, *, focus_assault=0, register_memory=0.5, partial_alibis=0.0):
    crime = CrimeBuilder(seed).build(KernelBuilder(seed, people_count=8).sample())
    life = build_life(crime, seed)
    # A poisoning with nobody who saw the glass is only a round of alibis: someone
    # always caught the gesture, at least as a silhouette with one trait.
    if crime.method is Method.POISONED:
        focus_assault = max(1, focus_assault)
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
    decisive = {e.id for e in witnesses.events if e.kind in (EventKind.ASSAULT, EventKind.DRINK_ADDITION)}
    described = {p.aspect for p in witnesses.perceptions if p.event in decisive and p.aspect is not Aspect.SILHOUETTE}
    evidence = build_evidence(crime, seed, witnesses.appearances, required_alibis=narrative_people,
                              partial_alibis=partial_alibis, described=described)
    evenings = build_evenings(crime, evidence, seed)
    registrations = build_registrations(crime)
    plan = with_witnesses(project(crime), witnesses)
    # A shared home is named after everyone who lives there, the victim first.
    victim_id = crime.kernel.roles.victim
    homes = {}
    for p in sorted(life.people.values(), key=lambda p: (p.id != victim_id, p.id)):
        homes.setdefault(p.home, []).append(p.name)
    plan = replace(plan, locations=tuple((key, "Logement " + ("d'" if names[0][0] in "AEIOUÉÈÊÎÔÛH" else "de ") + " et ".join(names)
                                          if key in homes and (names := homes[key]) else label) for key, label in plan.locations))
    labels = dict(plan.locations)
    population = plan.population
    people = life.people
    artifacts, actions, sources = list(plan.artifacts), list(plan.actions), set(plan.source_ids)
    claims, objects = {}, {}

    def add(key, kind, text, source, candidates=None, claim=None):
        sources.add(source)
        artifacts.append(Artifact(key, kind, text, (source,), population if candidates is None else frozenset(candidates)))
        if claim:
            claims[key] = claim

    def at_place_label(label):
        return "au " + label[3:] if label.startswith("Le ") else "à " + label

    def stays(pid):
        """Where this person really sat, as intervals: verified presences, real venue visits, loans."""
        rows = [(p.place, p.start, p.end) for p in evidence.presences if p.person == pid]
        rows += [(v.place, v.arrival.times[-1], v.until) for v in crime.venue_presences if v.person == pid]
        rows += [(b.outbound.nodes[-1], b.outbound.times[-1], b.inbound.times[0]) for b in crime.mundane_borrowings if b.actor == pid]
        return rows

    def sighting_text(rows, rng):
        doing = {"bar": ("un verre à la main", "devant un verre"), "restaurant": ("à table", "devant une assiette")}
        def one(row):
            name, when = people[row["person"]].name, spoken_time(row["minute"])
            where, what = at_place_label(labels[row["place"]]), rng.choice(doing.get(row["place"], ("de passage",)))
            if not row["named"]:
                # A face without a name: one or two traits, the detective matches them to a profile.
                traits = ", ".join(row["traits"].values())
                return rng.choice((f"Il y avait quelqu'un que je ne connais pas {where} vers {when}, {what} : {traits}.",
                                   f"Une personne que je n'avais jamais vue, {what} {where} vers {when}. {traits[0].upper() + traits[1:]}."))
            of = ("d'" if name[0] in "AEIOUÉÈÊÎÔÛH" else "de ") + name
            return rng.choice((f"{name} était {where} vers {when}, {what}. On s'est salués, pas plus.",
                               f"Je me souviens {of}, {what} {where}, vers {when}.",
                               f"J'ai croisé {name} {where} vers {when}, {what}. On n'a pas vraiment parlé."))
        if len(rows) == 2 and rows[0]["place"] == rows[1]["place"] and all(r["named"] for r in rows):
            a, b = (people[r["person"]].name for r in rows)
            when, where = spoken_time(min(r["minute"] for r in rows)), at_place_label(labels[rows[0]["place"]])
            what = rng.choice(doing.get(rows[0]["place"], ("de passage",)))
            return rng.choice((f"{a} et {b} étaient {where} vers {when}, {what}. Je ne les ai pas abordés.",
                               f"Il y avait {a} {where}, vers {when}. {b} aussi, un peu plus loin."))
        return " ".join(one(r) for r in rows)

    def shared_sightings(pid):
        seen = []
        for place, start, end in stays(pid):
            for other in sorted(population):
                if other == pid:
                    continue
                for other_place, other_start, other_end in stays(other):
                    if other_place == place and max(start, other_start) < min(end, other_end):
                        minute = ((max(start, other_start) + 7) // 15) * 15
                        if (other, place) not in {(o, pl) for o, pl, _ in seen}:
                            seen.append((other, place, minute))
        return seen

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
                                       p.home, p.id, (key, "evening:" + p.id)))
        evening = "evening:" + p.id
        presence = next((r for r in evidence.presences if r.person == p.id), None)
        add(evening, "personal_account", evening_account(crime, evidence, evenings, p.id),
            "evening_episode:" + p.id,
            claim={"account": p.id, "place": presence.place,
                   **remembered_times(presence), "source_actor": presence.witness} if presence else None)
        record_key = "police_record:" + p.id
        add(record_key, "police_record", f"Fiche de {p.name}. Domicile : {dict(plan.locations)[p.home]}. Métier : {p.occupation.label}.\n"
            "Aucun antécédent judiciaire renseigné dans cette fiche.", record_key)
        actions.append(DiscoveryAction("record:" + p.id, Operation.READ,
            "Consulter la fiche et le casier de " + p.name, "police", "staff:police",
            (key, record_key)))
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
            observation_text = f"Dans la journée, j'avais emprunté un objet {at_place_label(labels[keeper.place])}. {keeper.name} était là."
        # Who this person really saw: other guests of the same venue at the same time.
        # True for everyone, the author included; a glimpse names people and places,
        # it never clears anyone on its own.
        sightings = [{"person": other, "place": place, "minute": minute} for other, place, minute in shared_sightings(p.id)]
        if sightings:
            # A memory, not a roster: one face, sometimes two, with what they were doing.
            memory = random.Random(f"sightings-v2:{seed}:{p.id}")
            sightings = memory.sample(sightings, min(len(sightings), memory.choice((1, 1, 2))))
            for row in sightings:
                # Only an acquaintance gets a name; a stranger is a coat and a head of hair.
                row["named"] = life.knows(p.id, row["person"])
                seen_look = next(a for a in evidence.appearances if a.person == row["person"])
                traits = {"coat": "manteau " + seen_look.coat.value, "hair": "cheveux " + seen_look.hair.value, "height": seen_look.height.value}
                row["traits"] = {k: traits[k] for k in sorted(memory.sample(sorted(traits), memory.choice((1, 2))))}
            if len(sightings) == 2 and not any(r["named"] for r in sightings):
                sightings = sightings[:1]  # one unknown face per memory, not a parade
            observation_text = (observation_text + "\n" if borrowing else "") + sighting_text(sightings, memory)
        observation_reveals = old.reveals if old else ()
        if borrowing or sightings or not observation_reveals:
            add(observation_key, "personal_account", observation_text, observation_key,
                claim={"sightings": sightings} if sightings else None)
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
                claim={"concerns": romantic, "photos": [[*b.people, b.kind.value] for b in pictures]})
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
        objects["search:" + home] = found + mugs + ("doorbell:" + home,)
        names = [next(t.kind.label for t in crime.inventory if t.id == tool)
                 + (" (" + ("du " if labels[tool.split("_")[0]].startswith("Le ") else "de ") + labels[tool.split("_")[0]].removeprefix("Le ") + ")"
                    if tool.startswith(("bar_", "restaurant_")) else "")  # a venue's property, found here
                 for tool in found]
        add("objects:" + home, "objects", "Objets examinés : " + ", ".join(names + ["tasse personnelle de " + p.name for p in residents] + ["sonnette de l'entrée"]) + ".", "objects:" + home)
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
    # bin in an unrelated street. Every home has a cupboard to search, so the one
    # that hides something never stands out in a menu.
    for n in crime.streets.nodes:
        if n.kind is not NodeKind.HOME:
            continue
        d = evidence.disposal
        found = (d.tool,) if d and d.place == n.id and d.container == "cupboard" else ()
        key = "cupboard:" + n.id
        add(key, "container", "Un objet a été dissimulé derrière le fond d'un placard : "
            + next(t.kind.label for t in crime.inventory if t.id == d.tool) + "." if found else
            "Rien derrière le fond du placard : du linge et des boîtes.", "weapon_disposition" if found else key)
        actions.append(DiscoveryAction("search_cupboard:" + n.id, Operation.SEARCH, "Examiner le fond du placard",
            n.id, key, (key,)))
        objects["search_cupboard:" + n.id] = found
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
        if p.basis == "on_site":
            # Seen in the room where the glass was poisoned: an opportunity, never an alibi.
            text = (f"Oui, {name}. Je m'occupais de sa table, du service du verre jusqu'au malaise. "
                    f"Mais dans la salle, tout le monde pouvait s'approcher du comptoir. Je ne peux pas jurer de ce que chacun a fait.")
            add("alibi:" + p.person, "corroboration", text, p.id,
                claim={"account": p.person, "on_site": True, "place": p.place, "source_actor": p.witness})
            actions.append(DiscoveryAction("verify:" + p.person, Operation.VERIFY, "Vérifier le récit de " + name,
                                           p.place, p.witness, ("alibi:" + p.person,), ("evening:" + p.person,)))
            continue
        if p.basis == "continuous_noncontact":
            # One guest the staff truly never lost sight of: that does clear them.
            text = f"Oui, {name}. Je m'occupais de sa table. Je n'ai pas regardé l'heure, mais du service du verre jusqu'au malaise, cette personne est restée sous mes yeux, sans toucher le verre de la victime."
            requires = ("medical_window", "drink_result")
        elif p.basis == "partial_service":
            times = remembered_times(p)
            if not times:
                raise ValueError("A partial visit still has remembered landmarks")
            beginning, ending = spoken_time(times['start']), spoken_time(times['end'])
            text = (f"Oui, {name}, hier. Entre {beginning} et {ending}, cette personne était à sa table. "
                    f"{'Avant' if p.start > start else 'Après'}, je ne peux rien dire, je ne l'ai pas vue.")
            # True, verified, and silent on part of the crime window: it clears nobody.
            add("alibi:" + p.person, "corroboration", text, p.id,
                claim={"account": p.person, "partial": True, "place": p.place, **times, "source_actor": p.witness})
            actions.append(DiscoveryAction("verify:" + p.person, Operation.VERIFY, "Vérifier le récit de " + name,
                                           p.place, p.witness, ("alibi:" + p.person,), ("evening:" + p.person,)))
            continue
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
    # The keeper's own memory is patchy: half the regulars come to mind unprompted
    # and those named are vouched for directly; the others only when asked by name.
    for keeper in crime.keepers:
        memory = random.Random(f"register-memory:{seed}:{keeper.id}")
        visits = [r for r in registrations if r.keeper == keeper.id]
        texts = [f"{people[v.person].name} est passé, vers {spoken_time(((v.minute + 7) // 15) * 15)}."
                 for v in visits]
        seen = {v.person for v in visits}
        register = {}
        for p in evidence.presences:
            # At most two guests come to mind unprompted: the register narrows, it never closes the case.
            if p.witness != keeper.id or p.person in seen or p.basis == "partial_service" or len(register) >= 2 or memory.random() < 1 - register_memory:
                continue
            times = remembered_times(p)
            when = "entre " + spoken_time(times["start"]) + " et " + spoken_time(times["end"]) if times else "pendant le service"
            texts.append(f"{people[p.person].name} était à une table que je servais {when}.")
            if times and p.basis not in ("continuous_noncontact", "on_site") and keeper.place != crime.scene:
                register[p.person] = {"place": p.place, **times, "requires": ("medical_window",)}
        key = "venue_register:" + keeper.place
        text = " ".join(texts) + " Pour les autres clients, mes souvenirs sont moins précis." if texts else "Je ne peux vous citer personne avec certitude pour cette soirée. Ça ne veut pas dire que personne n'est venu."
        add(key, "venue_register", text, key, claim={"register": register, "source_actor": keeper.id} if register else None)
        if visits:
            sources.update(v.id for v in visits)
            artifacts[-1] = replace(artifacts[-1], sources=tuple(v.id for v in visits))
        sources.update(p.id for p in evidence.presences if p.witness == keeper.id)
        artifacts[-1] = replace(artifacts[-1], sources=artifacts[-1].sources + tuple(
            p.id for p in evidence.presences if p.witness == keeper.id))
        actions.append(DiscoveryAction("venue_guests:" + keeper.place, Operation.INTERVIEW,
            "Demander les clients de la soirée", keeper.place, keeper.id, (key,)))
        # Who works here: the staff knows its own team. A missing tool points at the
        # people with the keys, as a lead and nothing more.
        team = [people[pid] for pid in sorted(population) if people[pid].workplace.value == keeper.place]
        job = {"table_service": "service en salle", "bar_management": "gestion du bar", "cooking": "cuisine",
               "restaurant_management": "gestion du restaurant", "accounting": "comptabilité"}
        roster = ("Dans l'équipe, il y a " + ", ".join(f"{p.name} ({job.get(p.occupation.value, p.occupation.value)})" for p in team) + "."
                  if team else "L'équipe, c'est moi et des extras de passage. Personne d'autre à vous citer.")
        add("venue_staff:" + keeper.place, "venue_staff", roster, "venue_staff:" + keeper.place)
        actions.append(DiscoveryAction("venue_staff:" + keeper.place, Operation.INTERVIEW,
            "Demander qui travaille ici", keeper.place, keeper.id, ("venue_staff:" + keeper.place,)))
    # Extract public semantics of an assailant description, not its hidden mask.
    for w in witnesses.witnesses:
        for row in statements(witnesses, w.id):
            perception = next(p for p in witnesses.perceptions if row.sources == (p.id,))
            event = next(e for e in witnesses.events if e.id == perception.event)
            if event.kind in (EventKind.ASSAULT, EventKind.DRINK_ADDITION) and perception.aspect is not Aspect.SILHOUETTE:
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
    # The days before the crime: a studied prey was watched, and that leaves traces the
    # crime itself does not. Every street camera and the victim's building answer the
    # question; only a stalker's case has something to show.
    fixation = next((f for f in crime.kernel.world.fixations if f.studied), None)
    victim_home = people[victim].home
    victim_street = crime.streets.neighbors(victim_home)[0][0]
    watches = [e for e in crime.kernel.world.events if fixation and e.id in fixation.watches]
    stalker_look = next((a for a in evidence.appearances if fixation and a.person == fixation.author), None)
    def shared(aspect):
        value = getattr(stalker_look, aspect.value)
        return frozenset(a.person for a in evidence.appearances if a.person in population and getattr(a, aspect.value) == value)
    for cam in evidence.cameras:
        key = "camera_past:" + cam.place
        if not cam.online:
            text, support = "La caméra de ce quartier était hors service ces derniers jours.", population
        elif fixation and cam.place == victim_street and any(e.place == victim_home for e in watches):
            lines, support = [], population
            for e in (e for e in watches if e.place == victim_home):
                days, minute = -(e.minute // 1440), e.minute % 1440
                aspect = cam.aspect if cam.aspect is not Aspect.SILHOUETTE and len(shared(cam.aspect)) >= 2 else Aspect.SILHOUETTE
                seen = {"coat": "Manteau " + stalker_look.coat.value, "height": stalker_look.height.value.capitalize(),
                        "hair": "Cheveux " + stalker_look.hair.value}.get(aspect.value, "Silhouette seulement")
                lines.append(f"Il y a {days} jours, {minute // 60:02d}:{minute % 60:02d} — Une personne s'arrête devant {labels[victim_home]}, "
                             f"reste un long moment sans entrer, puis s'éloigne. {seen}; visage illisible.")
                if aspect is not Aspect.SILHOUETTE:
                    support = support & shared(aspect)
                    claims[key] = {"description": aspect.value, "value": getattr(stalker_look, aspect.value).value, "prowler": True}
            text = "\n".join(lines)
        else:
            text, support = "Les jours précédents : les passages habituels, rien d'exploitable.", population
        add(key, "footage", text, key, support)
        actions.append(DiscoveryAction(key, Operation.CAMERA, "Consulter les jours précédents",
            cam.place, "camera:" + cam.place, (key,), ("scene_body",)))
    caretaker_key = "prowler:" + victim_street
    if fixation:
        options = [a for a in (Aspect.COAT, Aspect.HEIGHT, Aspect.HAIR) if len(shared(a)) >= 2]
        camera_aspect = next((c.aspect for c in evidence.cameras if c.place == victim_street), None)
        options = [a for a in options if a is not camera_aspect] or options
        aspect = random.Random(f"prowler-v1:{seed}").choice(options) if options else None
        seen = {"coat": f"Son manteau était {stalker_look.coat.value}.", "height": f"La personne était {stalker_look.height.value}.",
                "hair": f"Ses cheveux étaient {stalker_look.hair.value}."}.get(aspect.value if aspect else "", "Je n'ai pas assez bien vu pour décrire la personne.")
        days = -(min(e.minute for e in watches) // 1440)
        text = (f"Ces derniers soirs, quelqu'un traînait devant l'immeuble sans jamais entrer. La première fois, il y a {days} jours. "
                f"{seen} Je n'ai pas vu son visage, et je n'ai pas pensé à prévenir.")
        support = shared(aspect) if aspect else population
        if aspect:
            claims[caretaker_key] = {"description": aspect.value, "value": getattr(stalker_look, aspect.value).value, "prowler": True}
    else:
        text, support = "Rien d'inhabituel ces derniers soirs. Les habitués, les livreurs, c'est tout.", population
    add(caretaker_key, "testimony", text, caretaker_key, support)
    actions.append(DiscoveryAction(caretaker_key, Operation.INTERVIEW, "Interroger la gardienne de l'immeuble",
        victim_street, "caretaker:" + victim_street, (caretaker_key,), ("scene_body",)))
    # A noted loan has a name: the keeper remembers who took the object. The lab will
    # say whether it served, or whether it was only borrowed.
    for index, artifact in enumerate(artifacts):
        if artifact.id.startswith("stock:") and "On en a prêté un." in artifact.text:
            _, place, kind = artifact.id.split(":", 2)
            borrowers = [people[b.actor].name for b in crime.mundane_borrowings
                         if b.outbound.nodes[-1] == place and next(t.kind.value for t in crime.inventory if t.id == b.tool) == kind]
            if borrowers:
                artifacts[index] = replace(artifact, text=artifact.text.replace("On en a prêté un.", "On en a prêté un à " + borrowers[0] + "."))
    plan = replace(plan, artifacts=tuple(artifacts), actions=tuple(actions), source_ids=frozenset(sources), projection_version=3)
    return PlayCase(seed, crime, life, witnesses, evidence, plan, claims, objects, evenings, registrations)


PROFILES = {  # which thread should be the short one: assault witnesses, keepers' unprompted memory
    "signalement": {"focus_assault": 1, "register_memory": 0.3, "partial_alibis": 0.45},
    "horaires": {"focus_assault": 0, "register_memory": 0.5, "partial_alibis": 0.25},
    "mixte": {"focus_assault": 1, "register_memory": 0.5, "partial_alibis": 0.4},
}


def thread_profile(lengths):
    """The family a case favours, from its thread lengths (None = incomplete)."""
    big = 10 ** 6
    sig, hor, mix = (lengths[f] if lengths[f] is not None else big for f in ("signalement", "horaires", "mixte"))
    if mix >= big:
        return None
    if mix < min(sig, hor):
        return "mixte"
    return "signalement" if sig <= hor else "horaires"


def sample_playable(seed=0, max_attempts=200, *, profile=None):
    """Reject unsolvable identity graphs; do not patch truth or pad clue masks.
    Each seed also draws the thread it favours, so no single recipe wins every case.
    This is NOT a certification of a full causal reconstruction.
    """
    from scenario_threads import family_lengths
    profile = profile or random.Random(f"thread-profile-v1:{seed}").choice(tuple(PROFILES))
    if profile not in PROFILES:
        raise ValueError("Unknown thread profile")
    fallback = None
    for attempt in range(max_attempts):
        candidate_seed = seed if attempt == 0 else f"{seed}:retry:{attempt}"
        try:
            case = build_case(candidate_seed, **PROFILES[profile])
        except ValueError as error:
            if "non-assault crime" not in str(error):
                raise
            continue
        graph = case.plan.graph()
        if not (graph.remaining({a.id for a in case.plan.artifacts}) == {case.crime.kernel.roles.author}
                and len(case.evidence.presences) >= 2 and context_is_refutable(case)):
            continue
        if thread_profile(family_lengths(case)) == profile or case.crime.kernel.premise.motive is Motive.PREDATION:
            return case  # a stranger's case is its own family: no profile to match
        fallback = fallback or case
    if fallback is not None:
        return fallback
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


DIFFICULTY = {"facile": 3.0, "normal": 2.2, "difficile": 1.6, "libre": None}  # deadline, as a multiple of the shortest thread; libre = none


class PlaySession:
    def __init__(self, case, skills=("search", "rapport"), *, strict=True, difficulty="normal", turn_minutes=None,
                 greeting_reveals_evening=True):
        """`strict` keeps the original adjudication: an accusation is refused until the
        file is complete. Otherwise the detective accuses at their own risk, against
        the clock: a wrong accusation costs time and clears the accused.
        With `turn_minutes`, the clock is frozen during a turn: only `end_turn()` moves
        it, and the deadline is only checked then. Mistakes still cost their minutes."""
        if len(set(skills)) != 2 or not set(skills) <= set(SKILLS):
            raise ValueError("Choose exactly two distinct skills: " + ", ".join(SKILLS))
        if difficulty not in DIFFICULTY:
            raise ValueError("Unknown difficulty: " + ", ".join(DIFFICULTY))
        self.case, self.skills = case, frozenset(skills)
        self.state, self.at, self.place = DiscoveryState(), 1440 + 8 * 60, case.crime.scene
        self.strict, self.cleared, self.mistakes = strict, set(), 0
        self.deadline, self.turn_minutes = None, turn_minutes
        # The CLI's greeting covers the look and the evening in one go; a client with an
        # explicit "Où étiez-vous hier soir ?" question keeps the evening for that question.
        self.greeting_reveals_evening = greeting_reveals_evening
        if not strict and DIFFICULTY[difficulty] is not None:
            from scenario_threads import deadline_minutes
            self.deadline = self.at + deadline_minutes(case, DIFFICULTY[difficulty])
        self.journal, self.found, self.prints, self.marks = [], set(), {}, {}
        self.linked = set()  # objects the laboratory tied to the crime
        self.object_places, self.carried = {}, set()
        self.finished = False
        self.person_places = {pid: case.life.people[pid].home for pid in case.plan.population}
        self.doorstep = None
        self.discovery_places = {}

    @property
    def time_left(self):
        return None if self.deadline is None else max(0, self.deadline - self.at)

    @property
    def turns_left(self):
        """Turns the detective can still end before the case is closed."""
        if self.deadline is None or self.turn_minutes is None:
            return None
        return max(0, -(-self.time_left // self.turn_minutes))

    def _advance(self, minutes, *, force=False):
        """The clock moves; past the deadline the case is closed unsolved.
        In turn mode an action takes no time: only turns and penalties (`force`) do,
        and the deadline waits for the end of the turn."""
        if self.turn_minutes is not None and not force:
            return
        self.at += minutes
        if self.turn_minutes is None:
            self._check_deadline()

    def end_turn(self):
        """Turn mode: the clock jumps, and a case past its deadline is closed now."""
        if self.turn_minutes is None:
            raise ValueError("Not a turn-based session")
        self.at += self.turn_minutes
        self._check_deadline()

    def _check_deadline(self):
        if self.deadline is not None and self.at >= self.deadline and not self.finished:
            self.finished = True
            self.journal.append({"id": "closed", "kind": "ending",
                                 "text": "L'échéance est passée : le dossier est classé sans suite."})

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
        actions = []
        for a in self.case.plan.actions:
            if a.actor in self.person_places and a.operation is Operation.INTERVIEW:
                a = replace(a, place=self.person_place(a.actor))
            if a.id.startswith("meet:") and not self.greeting_reveals_evening:
                a = replace(a, reveals=tuple(k for k in a.reveals if not k.startswith("evening:")))
            actions.append(a)
        self._plan_cache = replace(self.case.plan, actions=tuple(actions))
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
        if self.finished:
            raise ValueError("This investigation has ended")
        self._advance(minutes)
        self.place = place
        return f"{self.locations[place]} — {clock(self.at)}, trajet {minutes} min."

    def options(self):
        return tuple(row for row in self.effective_plan.available(self.state, place=self.place, at=self.at)
                     if row["operation"] != Operation.CAMERA.value
                     and not (row["id"] in ("request_exam", "request_exam_morgue")
                              and "exam_request" in dict(self.state.known)))

    BATCHES = {"record:": "Consulter les fiches de {}", "verify:": "Vérifier les récits de {} auprès du personnel"}

    def batches(self):
        """At the police station or a venue, several records or verifications are one visit."""
        rows = []
        named = self.named_people()
        for prefix, label in self.BATCHES.items():
            members = [row for row in self.options() if row["id"].startswith(prefix)
                       and (prefix != "record:" or row["id"].split(":", 1)[1] in named)]
            if len(members) >= 2:
                names = [self.case.life.people[row["id"].split(":", 1)[1]].name for row in members]
                rows.append({"id": "batch:" + prefix.rstrip(":"), "operation": members[0]["operation"],
                             "label": label.format(", ".join(names)), "place": self.place,
                             "actor": members[0]["actor"], "members": [row["id"] for row in members]})
        return tuple(rows)

    def do(self, action):
        if action in ("request_exam", "request_exam_morgue") and "exam_request" in dict(self.state.known):
            raise ValueError("L'examen est déjà demandé ; le rapport sera remis à la morgue.")
        if action.startswith("batch:"):
            batch = next((b for b in self.batches() if b["id"] == action), None)
            if batch is None:
                raise ValueError("Rien à regrouper ici pour l'instant.")
            at, texts = self.at, []
            for member in batch["members"]:
                texts.append(self._discover(member, self.place))
                self.at = at  # one visit, one span of time
            self._advance(3 if "rapport" in self.skills else 5)
            return "\n\n".join(texts)
        return self._discover(action, self.place)

    def register_entries(self, pid=None):
        """People the venue staff vouched for unprompted, once the crime is dated."""
        known = dict(self.state.known)
        rows = {}
        for key, claim in self.case.claims.items():
            if key in known and "register" in claim:
                for person, entry in claim["register"].items():
                    if set(entry["requires"]) <= known.keys():
                        rows[person] = dict(entry, source=key)
        return rows.get(pid) if pid else rows

    def alibi_state(self, pid):
        known = dict(self.state.known)
        key = "alibi:" + pid
        if key in known:
            if self.case.claims[key].get("partial"):
                return "partial"  # true and verified, but silent on part of the crime window
            if self.case.claims[key].get("on_site"):
                return "on_site"  # seen in the room where the poisoning happened
            return "confirmed" if set(self.case.claims[key].get("requires", ())) <= known.keys() else "corroborated"
        if self.register_entries(pid):
            return "confirmed"
        if "evening:" + pid not in known:
            return "unknown"
        # "I stayed home": nobody can confirm or deny it. Say so, instead of "to check".
        return "reported" if any(a.id == "verify:" + pid for a in self.case.plan.actions) else "unverifiable"

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
            elif "register" in claim:
                for pid, entry in claim["register"].items():
                    rows.append({"id": key + ":" + pid, "start": entry["start"], "end": entry["end"], "kind": "alibi",
                        "status": "verified" if set(entry["requires"]) <= known.keys() else "reported",
                        "title": self.case.life.people[pid].name + " · " + labels[entry["place"]] + " · registre",
                        "text": "Cité spontanément par le personnel, à sa table sur cette période.",
                        "place": entry["place"], "person": pid, "alibi_state": self.alibi_state(pid)})
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
        before = dict(self.state.known)
        self.state, rows = self.effective_plan.perform(self.state, action, place=source_place, at=self.at)
        self.discovery_places[action] = source_place
        self.journal.extend(row for row in rows if row["id"] not in before)  # a re-asked question adds no duplicate
        discovered = self.case.objects.get(action, ())
        self.found.update(discovered)
        for obj in discovered:
            self.object_places[obj] = source_place
        if action.startswith(("search_bin:", "search_cupboard:")) or action == "collect_object":
            self.carried.update(discovered)
        if action.startswith("search:"):
            # A venue's tool found in somebody's home leaves with the detective: the lab
            # will say whether it served, or whether it was only borrowed.
            self.carried.update(obj for obj in discovered if obj.startswith(("bar_", "restaurant_")))
        operation = next(a.operation for a in self.case.plan.actions if a.id == action)
        self._advance((3 if "search" in self.skills else 10) if operation is Operation.SEARCH else
                      3 if "rapport" in self.skills and operation in (Operation.INTERVIEW, Operation.VERIFY) else 5)
        text = "\n\n".join(row["text"] for row in rows)
        # With the kit in hand, a household mug is lifted on the spot.
        if "fingerprints" in self.skills:
            for obj in sorted(discovered):
                if obj.startswith("mug:") and obj not in self.prints:
                    text += "\n\n" + self.object_label(obj) + " — " + self.fingerprint(obj)
        return text

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
        self._advance(5)
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

    def fingerprint(self, obj, trained=None):
        if not (self.skills.__contains__("fingerprints") if trained is None else trained):
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
            # On a shared object, only partial patterns shared by >=2 cast members
            # are usable: no unique print becoming a one-step identity oracle.
            # A person's own mug reports their pattern whole; it only ever
            # excludes them from an object they did not touch.
            members = {r.person for r in self.case.evidence.contacts if r.object.startswith("mug:") and r.ridge == c.ridge}
            if obj.startswith("mug:") or len(members & self.case.plan.population) >= 2:
                patterns.append(c.ridge)
        self.prints[obj] = tuple(sorted(set(patterns)))
        text = ("Empreinte partielle : " + ", ".join(self.prints[obj]) +
                ". Comparaison possible avec d'autres objets relevés; un contact ne date pas le geste et ne prouve pas le meurtre."
                if patterns else "Aucune empreinte suffisamment exploitable pour une comparaison.")
        matches = [key for key, value in self.prints.items() if key != obj and set(value) & set(self.prints[obj])]
        if matches:
            text += "\nMotif partiel également présent sur : " + ", ".join(self.object_label(key) for key in matches) + ". Pas une identification certaine."
        self._advance(8)
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
        if surface is not None:
            self.linked.add(obj)
        self._advance(20)
        self.journal.append({"id": key, "kind": "laboratory_contact", "text": self.object_label(obj) + " — " + text})
        return text

    def print_exclusions(self):
        """People whose own partial pattern is absent from an object the lab tied to the crime.

        Public state only: the patterns lifted on that object and on each person's
        household mug. A pattern too rare to compare (unique) excludes nobody."""
        on_crime_objects = {obj: set(self.prints[obj]) for obj in self.linked if self.prints.get(obj)}
        if not on_crime_objects:
            return {}
        patterns = set().union(*on_crime_objects.values())
        result = {}
        for pid in self.case.plan.population:
            own = set(self.prints.get("mug:" + pid, ()))
            if own and not own & patterns:
                objects = ", ".join(self.object_label(obj) for obj in sorted(on_crime_objects))
                result[pid] = (f"Empreinte personnelle : {', '.join(sorted(own))}. Sur {objects}, seulement : "
                               f"{', '.join(sorted(patterns))}. Cette personne n'a pas tenu l'objet.")
        return result

    def object_label(self, obj):
        if obj.startswith("mug:"):
            return "tasse personnelle de " + self.case.life.people[obj.removeprefix("mug:")].name
        if obj.startswith("doorbell:"):
            return "sonnette · " + self.locations[obj.removeprefix("doorbell:")]
        label = next(t.kind.label for t in self.case.crime.inventory if t.id == obj)
        if obj.startswith(("bar_", "restaurant_")):  # a venue's property, wherever it was found
            label += " (" + ("du " if self.locations[obj.split("_")[0]].startswith("Le ") else "de ") + self.locations[obj.split("_")[0]].removeprefix("Le ") + ")"
        return label

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
        remaining = set(self.case.plan.population) - self.cleared - self.register_entries().keys() - self.print_exclusions().keys()
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
        for pid, entry in self.register_entries().items():
            result[pid].append({"source": entry["source"],
                                "text": f"Le personnel de {self.locations[entry['place']]} se souvient de cette personne à sa table pendant toute la période."})
        for pid in self.cleared:
            result[pid].append({"source": "accusation", "text": "Mis hors de cause après une accusation rejetée."})
        for pid, text in self.print_exclusions().items():
            result[pid].append({"source": "prints", "text": text})
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
            corroborated = "alibi:" + pid in known and not any(self.case.claims["alibi:" + pid].get(k) for k in ("partial", "on_site"))
            state = "refuted" if reasons else "awaiting_time" if corroborated else "open"
            # A destination is not privileged knowledge: require a personal
            # story naming the witness before displaying its meeting point.
            destination = verification.place if verification and "evening:" + pid in known and not corroborated else None
            rows.append({"person": pid, "state": state, "details": details,
                         "reasons": reasons, "destination": destination})
        return tuple(rows)

    def social_graph(self):
        """Who knows whom, as the detective heard or read it: an ego graph around the victim.
        Relations come from the answers actually given and the albums actually read; a
        pair someone said they did not know is listed apart. Never the private catalogue."""
        life, victim = self.case.life, self.case.crime.kernel.roles.victim
        population, known = self.case.plan.population, dict(self.state.known)
        ids = {row["id"] for row in self.journal}
        names = {pid: life.people[pid].name for pid in life.people}
        edges, strangers = {}, []

        def add(a, b, kind, source):
            if a == b:
                return
            edge = edges.setdefault(tuple(sorted((a, b))), {"kinds": [], "sources": []})
            if kind not in edge["kinds"]:
                edge["kinds"].append(kind)
            if source not in edge["sources"]:
                edge["sources"].append(source)

        def bonds_between(a, b, source):
            bonds = life.links(a, b)
            for bond in bonds:
                add(a, b, bond.kind.value, source)
            if not bonds and life.knows(a, b):
                add(a, b, "messages", source)
            return bool(bonds) or life.knows(a, b)

        for pid in sorted(population):
            if f"context:{pid}:relation" in ids:
                bonds_between(pid, victim, names[pid])
            if f"context:{pid}:work" in ids:
                for bond in life.bonds:
                    if bond.kind is Link.COLLEAGUES and pid in bond.people:
                        add(*bond.people, "collègues", names[pid])
            if f"context:{pid}:circle" in ids:
                for other in population:
                    if other != pid and life.knows(pid, other) and life.links(other, victim):
                        add(other, victim, "proche", names[pid])
            for other in sorted(population):
                if f"about:{pid}:{other}" in ids:
                    if not bonds_between(pid, other, names[pid]):
                        strangers.append([pid, other])
                    for fact in life.ordinary:
                        if fact.kind in ("ex_and_partner", "sour_breakup") and set(fact.people) == {pid, other}:
                            add(pid, other, "rivalité" if fact.detail == "venom" else "ex en paix", names[pid])
        for key, claim in self.case.claims.items():
            if key in known and "photos" in claim:
                for a, b, kind in claim["photos"]:
                    add(a, b, kind, "album")
        named, remaining = self.named_people(), self.remaining()
        people = {victim} | {pid for pair in edges for pid in pair} | {pid for pair in strangers for pid in pair}
        return {"center": victim,
                "nodes": [{"id": pid, "name": names[pid] if pid == victim or pid in named else "?", "victim": pid == victim,
                           "excluded": pid != victim and pid not in remaining}  # faded once ruled out
                          for pid in sorted(people, key=lambda p: (p != victim, p))],
                "edges": [{"a": a, "b": b, **edge} for (a, b), edge in sorted(edges.items())],
                "strangers": strangers}

    def talk_about(self, person, other):
        if person not in self.case.plan.population or self.person_place(person) != self.place:
            raise ValueError("Il faut rejoindre cette personne pour lui parler.")
        if "profile:" + person not in dict(self.state.known):
            raise ValueError("Commencez la conversation via l'action Parler à…")
        text = self.case.life.answer_about(person, other)
        key = "about:" + person + ":" + other
        if not any(row["id"] == key for row in self.journal):
            self.journal.append({"id": key, "kind": "relationship", "text": self.case.life.people[person].name + " — « " + text + " »"})
            self._advance(3 if "rapport" in self.skills else 5)
        return text

    def ask_context(self, person, topic):
        """Already-authored personal facts, not an invented murder testimony."""
        if topic not in ("relation", "work", "circle", "habits", "messages", "evening", "motive", "appointment"):
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
                if person == self.case.crime.kernel.roles.author:
                    # The killer never admits the meeting took place: the same words an innocent
                    # host uses for a real no-show, or an excuse. A street witness can give the lie.
                    text += random.Random(f"appointment-lie-v1:{self.case.seed}").choice(
                        (" J'ai attendu, mais personne n'est venu.", " Je n'y suis finalement pas allée, j'ai eu un empêchement."))
                else:
                    text += " J'ai attendu, mais personne n'est venu." if any(m.observer == person for m in self.case.crime.missed_appointments) else " On s'est retrouvés dehors pour parler."
            else:
                text = "Ce rendez-vous ne me dit rien. Nous n'en avions pas parlé."
        else:
            text = evening_account(self.case.crime, self.case.evidence, self.case.evenings, person) if topic == "evening" else self.case.life.answer(person, topic)
        key = "context:" + person + ":" + topic
        if not any(row["id"] == key for row in self.journal):
            self.journal.append({"id": key, "kind": "conversation", "text": self.case.life.people[person].name + " — « " + text + " »"})
            self._advance(3 if "rapport" in self.skills else 5)
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

    MISTAKE_MINUTES = 90

    def accuse(self, person, method=None, goal=None):
        known = dict(self.state.known)
        if person not in self.case.plan.population:
            raise ValueError("Choose an existing suspect")
        if self.finished:
            raise ValueError("This investigation has ended")
        if method is not None and method not in {m.value for m in Method}:
            raise ValueError("Unknown method")
        if self.strict:
            if "medical_window" not in known or "victim_diary" not in known:
                return False, "Il manque la méthode ou le dernier projet de la victime. L'accusation n'est pas encore déposée."
            if goal is not None and goal != self.case.claims["victim_diary"]["goal"]:
                return False, "Cette reconstitution du dernier déplacement contredit l'agenda consulté."
            if self.remaining() != {person}:
                return False, "Le dossier laisse encore plusieurs possibilités. L'accusation n'est pas encore déposée."
        elif person in self.cleared:
            raise ValueError("Cette personne a déjà été mise hors de cause.")
        # Only the final adjudicator consults private truth, not the player's bot.
        name = self.case.life.people[person].name
        success = person == self.case.crime.kernel.roles.author and (method is None or method == self.case.crime.method.value)
        if not success and not self.strict:
            # A wrong accusation is not the end: it costs time, and the accused is cleared for good.
            self.mistakes += 1
            self.cleared.add(person)
            self.journal.append({"id": "cleared:" + person, "kind": "accusation",
                                 "text": f"Le commissaire a rejeté le dossier contre {name} : les charges ne tiennent pas. {name} est mis(e) hors de cause."})
            self._advance(self.MISTAKE_MINUTES, force=True)
            if self.finished:
                return False, f"Le commissaire rejette le dossier contre {name}. Le temps vous a manqué : l'affaire est classée sans suite."
            lost = ("une heure et demie" if self.turn_minutes is None else
                    f"{-(-self.MISTAKE_MINUTES // self.turn_minutes)} tours")
            return False, (f"Le commissaire rejette le dossier contre {name} : les charges ne tiennent pas. "
                           f"{name} est hors de cause, et vous avez perdu {lost}.")
        self.finished = True
        if not success:
            return False, "Accusation rejetée : la reconstitution est erronée."
        gaps = [g for key, g in (("medical_window", "sans la période établie par le légiste"),
                                 ("victim_diary", "sans le dernier projet de la victime")) if key not in known]
        return True, ("Dossier établi : " + name + ".\n"
                      "Méthode : " + self.case.crime.method.label + ".\n"
                      + (f"Un dossier retenu {', '.join(gaps)} : l'aveu a fait le reste.\n" if gaps else "")
                      + "Le contexte éclaire le geste, mais les liens et les griefs ne prouvaient pas à eux seuls la culpabilité.")


def menu(session):
    """The CLI's numbered actions: nothing already known, batches instead of their members."""
    known = dict(session.state.known)
    by_id = {a.id: a for a in session.case.plan.actions}
    batches = session.batches()
    grouped = {member for batch in batches for member in batch["members"]}
    named = session.named_people()  # the clerk needs a name: the CLI, like the 3D client, waits for one
    rows = [row for row in session.options() if row["id"] not in grouped
            and any(key not in known for key in by_id[row["id"]].reveals)
            and not (row["id"].startswith("record:") and row["id"].split(":", 1)[1] not in named)]
    return tuple(rows) + batches


HELP = """Commandes :
  lieux                         lieux, habitants et objets accessibles
  aller ID                      se déplacer (ID affiché dans lieux)
  voir                          actions numérotées du lieu
  faire N | faire MOT           effectuer une action affichée (numéro, ou un mot de son libellé)
  demander NOM AUTRE_NOM         questionner quelqu'un sur une autre personne
  question NOM SUJET             mobile / témoin / alibi / lien / métier / rdv
  camera HEURE                  caméra de ce quartier, hier, HEURE à HEURE+1
  objets / empreinte N           objets examinés / relevé avec la compétence
  analyse N                     analyser un objet récupéré, au laboratoire
  fils                          la pelote : trois fils, l'étape suivante de chacun
  carnet / pistes / horaires    notes / pistes recueillies / chronologie acquise
  suspects / recouper            profils connus / recoupements publics
  suivre NOM / ecarter NOM       aide visuelle uniquement
  attendre MINUTES              laisser passer un délai
  accuser NOM                   déposer le dossier, à vos risques : une erreur coûte du temps
  aide / quitter
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Neon Noir — nouveau générateur causal, CLI expérimentale")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--skills", default="search,rapport", help="Deux parmi fingerprints,search,rapport")
    parser.add_argument("--difficulte", default="normal", choices=sorted(DIFFICULTY), help="Échéance : large, serrée, très serrée, ou libre (aucune)")
    parser.add_argument("--classique", action="store_true", help="Règles d'origine : pas d'échéance, accusation refusée tant que le dossier est incomplet")
    args = parser.parse_args(argv)
    try:
        session = PlaySession(sample_playable(args.seed), tuple(args.skills.split(",")), strict=args.classique, difficulty=args.difficulte)
    except ValueError as error:
        parser.error(str(error))
    people, case = session.case.life.people, session.case
    victim = people[case.crime.kernel.roles.victim]
    victim.home  # the victim's door keeps its name: the detective knows whose case this is
    print(f"NEON NOIR — {victim.name} ({victim.occupation.label}, {victim.workplace.label}) : décès suspect.\n"
          f"Vous arrivez le lendemain à 08:00, {session.locations[session.place]}.\n"
          f"Les {len(case.plan.population)} personnes du dossier sont des contacts à vérifier, pas des coupables présumés.\n"
          "Compétences : " + ", ".join(sorted(session.skills)) + "."
          + (f"\nLe dossier sera classé à {clock(session.deadline)} : accusez quand vous êtes sûr, une erreur coûte une heure et demie."
             if session.deadline else "") + "\n" + HELP)
    while not session.finished:
        try:
            left = f" · {session.time_left // 60} h {session.time_left % 60:02d} restantes" if session.deadline else ""
            words = shlex.split(input(f"[{clock(session.at)} {session.locations[session.place]}{left}] > "))
            if not words:
                continue
            cmd, *rest = words
            if cmd in ("quitter", "quit", "exit"):
                break
            if cmd == "aide":
                print(HELP)
            elif cmd == "lieux":
                named = session.named_people()
                for key, label in session.locations.items():
                    residents = [p.name if p.id in named else "quelqu'un" for p in people.values() if p.home == key and p.id != victim.id]
                    if key.startswith("home") and not any(p.id in named for p in people.values() if p.home == key and p.id != victim.id):
                        label = "Logement " + key.removeprefix("home") if key != victim.home else label
                    objects = "; caméra + poubelle" if key in case.crime.streets._adjacency and case.crime.streets.kind(key) is NodeKind.STREET else ""
                    visible = next(row for row in session.board() if row["place"] == key)
                    actors = sorted({r["label"] for r in visible["actions"] if r["operation"] in (Operation.INTERVIEW.value, Operation.VERIFY.value)})
                    print(f"{key:22} {label}" + (" — " + ", ".join(residents) if residents else "") + objects)
                    for actor in actors:
                        print("  " + actor)
            elif cmd == "aller":
                print(session.go(" ".join(rest)))
            elif cmd == "voir":
                options = menu(session)
                for i, row in enumerate(options, 1):
                    print(f"{i}. {row['label']}")
                if not options:
                    print("Pas de nouvelle action disponible maintenant.")
                pending = [a for a in case.plan.actions if a.place == session.place and a.operation is not Operation.CAMERA
                           and a.id not in session.state.completed and set(a.requires) <= dict(session.state.known).keys()
                           and (ready := session.effective_plan.next_time(a, session.state, after=session.at)) is not None and ready > session.at]
                for a in pending:
                    print(f"En attente : {a.label}, disponible à {clock(session.effective_plan.next_time(a, session.state, after=session.at))}.")
                if any(cam.place == session.place for cam in case.evidence.cameras):
                    print("Caméra locale : camera HEURE (hier). Poubelle fouillable ci-dessus.")
            elif cmd == "faire":
                options = menu(session)
                if rest and rest[0].isdigit():
                    i = int(rest[0])
                    if not 1 <= i <= len(options):
                        raise ValueError("Numéro d'action invalide")
                    chosen = options[i - 1]
                else:  # numbers shift as actions are consumed: a word from the label is stable
                    words = [w.lower() for w in rest]
                    hits = [o for o in options if all(w in o["label"].lower() for w in words)]
                    if len(hits) != 1:
                        raise ValueError("Précisez l'action : " + (" / ".join(o["label"] for o in hits) if hits else "aucune ne correspond"))
                    chosen = hits[0]
                print(session.do(chosen["id"]))
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
            elif cmd in ("fils", "guide"):
                from scenario_threads import guide, render
                print(render(guide(session)))
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
                         "alibi": "evening", "lien": "relation", "métier": "work", "metier": "work", "entourage": "circle", "rdv": "appointment"}.get(rest[1].casefold())
                if not pid or not topic:
                    raise ValueError("Personne ou sujet inconnu")
                if topic in ("observations", "evening"):
                    key = ("observations:" if topic == "observations" else "evening:") + pid
                    if key in dict(session.state.known):
                        print(next(r["text"] for r in session.journal if r["id"] == key))
                    else:
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
                    if session.finished and not success and session.deadline is None:
                        pass
                else:
                    session.marks[person] = cmd
                    print("Repère visuel mis à jour; aucune preuve ajoutée.")
            elif cmd == "attendre":
                minutes = int(rest[0])
                if not 1 <= minutes <= 360:
                    raise ValueError("Attendre entre 1 et 360 minutes")
                session._advance(minutes)
            else:
                print("Commande inconnue; aide pour la liste.")
        except (ValueError, IndexError) as error:
            print("Action impossible :", error)
        except (EOFError, KeyboardInterrupt):
            print("\nEnquête interrompue.")
            break
    if session.finished and session.journal and session.journal[-1]["id"] == "closed":
        print(session.journal[-1]["text"])


if __name__ == "__main__":
    main()
