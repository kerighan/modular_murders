"""Investigation threads: the ball of string, Hitman-style, without the hand-holding.

Two faces. `family_lengths(case)` is authoring-side: it knows the culprit and
measures how long each family of proof is for a case (signalement, horaires,
mixte), so the generator and the audits can refuse cases where one recipe always
wins. `guide(session)` is player-side: it reads only what the detective has
already acquired and the public action catalogue, and lays out three threads
with their next concrete step. It never ranks or filters by the hidden truth:
every suggestion is symmetric across the remaining candidates.

Run: python scenario_threads.py --count 200
"""
import argparse
import json
from collections import Counter
from itertools import combinations

from scenario_means import Method
from scenario_observations import Operation
from scenario_play import clock

FAMILIES = ("signalement", "horaires", "mixte")
BASE_STEPS = 3  # request the exam, read the report, read the diary: the spine of any file
PER_ALIBI = 1  # one conversation gives the look and the evening; verifications are one visit per venue
RECORDS = 2  # learn the names somewhere, then the police records of everybody named in one visit
PER_PRINT = 1  # searching a home lifts its mug on the spot, with the kit
MATERIAL = 2  # the lab ties the object to the crime, then its print is lifted


# ------------------------------------------------------------------ authoring side

def description_sources(case):
    """Assailant descriptions the case holds: artifact key -> (acquiring action, aspect, value)."""
    rows = {}
    for key, claim in case.claims.items():
        if "description" in claim:
            action = next(a for a in case.plan.actions if key in a.reveals)
            rows[key] = (action.id, claim["description"], claim["value"])
    return rows


def excluded_by(case, key):
    """People whose real appearance contradicts one description (truth, authoring only)."""
    _, aspect, value = description_sources(case)[key]
    looks = {a.person: a for a in case.evidence.appearances}
    return {p for p in case.plan.population if getattr(looks[p], aspect).value != value}


def remembered(case):
    """People the venue registers vouch for unprompted: person -> register key."""
    return {pid: key for key, claim in case.claims.items() if "register" in claim for pid in claim["register"]}


def print_excluded(case):
    """Innocents whose partial pattern differs from the author's (truth, authoring only)."""
    author = case.crime.kernel.roles.author
    ridges = {c.person: c.ridge for c in case.evidence.contacts if c.object.startswith("mug:")}
    return {p for p in case.plan.population if p != author and ridges[p] != ridges[author]}


def material_setup(case):
    """Finding the hidden object: half the containers on average, then the lab and the print."""
    containers = sum(a.id.startswith(("search_bin:", "search_cupboard:")) for a in case.plan.actions)
    return (containers + 1) // 2 + MATERIAL if case.evidence.disposal else None


def family_lengths(case):
    """Minimal number of investigative actions per family, travel excluded.

    None means the family cannot conclude on its own. `mixte` picks, for every
    innocent, the cheapest of a description, a register or a verified alibi."""
    author = case.crime.kernel.roles.author
    innocents = case.plan.population - {author}
    sources = description_sources(case)
    covered = {key: excluded_by(case, key) & innocents for key in sources}
    # A partial visit clears nobody; neither does merely being in the poisoning room.
    alibis = {p.person: p.basis for p in case.evidence.presences if p.basis not in ("partial_service", "on_site")}
    registers = remembered(case)
    poison = 2 if any(basis == "continuous_noncontact" for basis in alibis.values()) else 0  # the glass, then the lab

    presences = {p.person: p.place for p in case.evidence.presences}
    by_prints, setup = print_excluded(case), material_setup(case)

    def alibi_cost(people):
        """Registers are one question per venue; the rest is one conversation per person,
        then one verification visit per venue."""
        venues = {registers[p] for p in people if p in registers}
        rest = [p for p in people if p not in registers]
        cost = len(venues) + PER_ALIBI * len(rest) + len({presences[p] for p in rest})
        return cost + (poison if any(alibis[p] == "continuous_noncontact" for p in rest) else 0)

    keys = sorted(covered)
    signalement, mixte = None, None
    for size in range(len(keys) + 1):
        for group in combinations(keys, size):
            union = set().union(*(covered[k] for k in group)) if group else set()
            actions = {sources[k][0] for k in group}  # one interview delivers a witness's whole memory
            shared = BASE_STEPS + (1 if group else 0) + len(actions)  # the scene, then each source
            if union == innocents:
                cost = shared + RECORDS
                signalement = cost if signalement is None else min(signalement, cost)
            if all(p in union or p in alibis for p in innocents):
                # Either everyone the description covers is compared to the records, or the
                # register's guests are left to the register: keep the cheaper assignment.
                for by_description in ({p for p in innocents if p in union},
                                       {p for p in innocents if p in union and p not in registers}):
                    cost = shared + (RECORDS if by_description else 0) + alibi_cost([p for p in innocents if p not in by_description])
                    mixte = cost if mixte is None else min(mixte, cost)
            if setup is not None and all(p in union or p in alibis or p in by_prints for p in innocents):
                # Prints first: the lab ties the found object to the crime, mugs of the
                # excludable people are lifted, the rest falls to descriptions or alibis.
                rest = [p for p in innocents if p not in by_prints]
                by_description = {p for p in rest if p in union}
                cost = shared + setup + PER_PRINT * len(by_prints) + (RECORDS if by_description else 0) + alibi_cost([p for p in rest if p not in by_description])
                mixte = cost if mixte is None else min(mixte, cost)
    horaires = BASE_STEPS + alibi_cost(sorted(innocents)) if innocents <= alibis.keys() else None
    return {"signalement": signalement, "horaires": horaires, "mixte": mixte,
            "innocents": len(innocents), "sources": len(sources), "alibis": len(alibis),
            "prints": len(by_prints), "method": case.crime.method.value}


def deadline_minutes(case, factor):
    """How long the detective gets: the shortest thread, in minutes, times a difficulty factor.
    An action takes about five minutes, and a trip between two sources about eight."""
    lengths = family_lengths(case)
    shortest = min(length for length in (lengths[f] for f in FAMILIES) if length is not None)
    return max(180, int(round(shortest * 13 * factor / 15.0)) * 15)


def balanced(lengths, *, spread=2):
    """At least two complete families, and not the same length: no single recipe."""
    complete = {family: length for family, length in lengths.items() if family in FAMILIES and length is not None}
    return len(complete) >= 2 and max(complete.values()) - min(complete.values()) >= spread


# ------------------------------------------------------------------ player side

def _step(title, state, actions=(), note=None):
    row = {"title": title, "state": state, "actions": list(actions)}
    if note:
        row["note"] = note
    return row


def guide(session):
    """Three threads from the detective's own notebook. Public state only."""
    case, known = session.case, dict(session.state.known)
    people, labels = case.life.people, session.locations
    remaining = session.remaining()
    done_ids = set(session.state.completed)
    plan = session.effective_plan
    by_id = {a.id: a for a in plan.actions}
    journal_ids = {row["id"] for row in session.journal}
    scene = case.crime.scene
    descriptions = [key for key in known if "description" in case.claims.get(key, {})]
    profiled = {pid for pid in case.plan.population if "profile:" + pid in known}
    accounts = {pid for pid in case.plan.population if "evening:" + pid in known}

    def where(action):
        return labels[action.place]

    def when(action):
        ready = plan.next_time(action, session.state, after=session.at)
        if ready is None or ready <= session.at:
            return ""
        return f", dès {clock(ready)}"

    def pending(action_id):
        return action_id in by_id and action_id not in done_ids

    # ---- signalement: what the assailant looked like, compared with the people
    steps = []
    steps.append(_step("Examiner la scène", "done" if "scene_body" in known else "next",
                       [] if "scene_body" in known else [f"Examiner la scène — {labels[scene]}"]))
    witnesses = [a for a in plan.actions if a.actor.startswith("witness:") and a.id not in done_ids]
    cameras = []
    for cam in case.evidence.cameras:
        queried = {int(r.split(":")[-1]) for r in journal_ids if r.startswith(("camera:" + cam.place + ":", "empty_window:" + cam.place + ":"))}
        if "medical_window" in known:
            start, end = case.claims["medical_window"]["window"]
            hours = [h for h in range(start // 60, end // 60 + 1) if h not in queried]
            if hours:
                cameras.append(f"Caméra de {labels[cam.place]} : camera {' / '.join(map(str, hours))}")
        elif not queried:
            cameras.append(f"Caméra de {labels[cam.place]}, créneaux du soir")
    sources = [f"{a.label} — {where(a)}{when(a)}" for a in witnesses] + cameras
    if "scene_body" not in known:
        steps.append(_step("Recueillir un signalement de l'agresseur", "later"))
    else:
        steps.append(_step("Recueillir un signalement de l'agresseur", "done" if descriptions else "next", sources,
                           note=f"{len(descriptions)} description(s) en main" if descriptions else None))
    unknown = sorted(remaining - profiled, key=lambda pid: people[pid].name)
    compare = [f"Rencontrer {people[pid].name} — {labels[session.person_place(pid)]}, ou sa fiche au Commissariat" for pid in unknown]
    steps.append(_step("Comparer le signalement aux personnes encore possibles",
                       "later" if not descriptions else "next" if unknown else "done", compare if descriptions else [],
                       note=None if descriptions else "Sans signalement, rencontrer les gens n'écarte personne."))
    excluded = sum(1 for pid, reasons in session.deductions().items()
                   if any("description" in case.claims.get(r["source"], {}) for r in reasons))
    steps.append(_step("Écarter les incompatibles", "done" if excluded else "later", [],
                       note=f"{excluded} personne(s) écartée(s) par le signalement" if excluded else None))
    threads = [{"family": "signalement", "title": "Le signalement", "steps": steps}]

    # ---- horaires: when it happened, who was seen elsewhere
    steps = []
    if "medical_window" in known:
        steps.append(_step("Dater le crime", "done", [], note=next(r["text"].splitlines()[0] for r in session.journal if r["id"] == "medical_window")))
    elif "exam_request" in known:
        read = by_id["read_medical"]
        steps.append(_step("Dater le crime", "next", [f"Consulter le médecin légiste — La Morgue{when(read)}"]))
    else:
        steps.append(_step("Dater le crime", "next", [f"Transférer le corps pour examen — {labels[scene]}, ou le demander à la morgue"]))
    registers = [a for a in plan.actions if a.id.startswith("venue_guests:") and a.id not in done_ids]
    vouched = len(session.register_entries())
    steps.append(_step("Registres des établissements", "done" if not registers else "next",
                       [f"{a.label} — {where(a)}{when(a)}" for a in registers],
                       note=f"{vouched} personne(s) mise(s) hors de cause par le personnel" if vouched else
                       ("Le personnel cite des clients ; une fois le crime daté, c'est un alibi." if registers or "medical_window" not in known else None)))
    if case.crime.method is Method.POISONED:
        lab = [a for a in plan.actions if a.id in ("collect_drink", "analyze_drink") and a.id not in done_ids]
        steps.append(_step("Analyser le verre", "done" if not lab else "next", [f"{a.label} — {where(a)}{when(a)}" for a in lab],
                           note="Pour un poison, le personnel ne confirme un alibi qu'une fois le verre analysé."))
    to_hear = sorted(remaining - accounts, key=lambda pid: people[pid].name)
    hear = [f"Demander à {people[pid].name} sa soirée — {labels[session.person_place(pid)]}" for pid in to_hear if pid in profiled]
    later = [people[pid].name for pid in to_hear if pid not in profiled]
    if later:
        hear.append(f"Après les avoir rencontrés : {', '.join(later)}")
    steps.append(_step("Recueillir les récits de soirée", "done" if not to_hear else "next", hear))
    checks = []
    for pid in sorted(remaining & accounts, key=lambda pid: people[pid].name):
        verify = by_id.get("verify:" + pid)
        if verify and verify.id not in done_ids:
            checks.append(f"Vérifier le récit de {people[pid].name} — {where(verify)}{when(verify)}")
    confirmed = sum(1 for pid in case.plan.population if session.alibi_state(pid) == "confirmed")
    partial = sum(1 for pid in case.plan.population if session.alibi_state(pid) == "partial")
    on_site = sum(1 for pid in case.plan.population if session.alibi_state(pid) == "on_site")
    note = ", ".join(part for part in (f"{confirmed} alibi(s) confirmé(s)" if confirmed else "",
                                       f"{partial} récit(s) vrai(s) mais hors période" if partial else "",
                                       f"{on_site} personne(s) vue(s) sur les lieux" if on_site else "") if part)
    steps.append(_step("Vérifier auprès du personnel", "next" if checks else "later" if to_hear else "done", checks,
                       note=note or None))
    threads.append({"family": "horaires", "title": "Les emplois du temps", "steps": steps})

    # ---- matériel: the scene, the papers, the lab, the prints
    steps = []
    scene_actions = [a for a in plan.actions if a.place == scene and a.operation in (Operation.COLLECT, Operation.SEARCH)
                     and a.id not in done_ids and "scene_body" in known]
    steps.append(_step("Relever la scène", "done" if "scene_body" in known and not scene_actions else "next",
                       [f"{a.label} — {where(a)}" for a in scene_actions] if "scene_body" in known else [f"Examiner la scène — {labels[scene]}"]))
    diary = by_id.get("read_diary")
    steps.append(_step("Lire l'agenda de la victime", "done" if "victim_diary" in known else "next",
                       [] if "victim_diary" in known else [f"Lire l'agenda — {where(diary)}"],
                       note=None if "victim_diary" in known else
                       "Requis pour déposer une accusation." if session.strict else "Le dernier projet de la victime : la reconstitution complète."))
    papers = {}
    for a in plan.actions:
        if (a.operation is Operation.READ and a.id.startswith(("read:", "photos:")) and a.id not in done_ids
                and any(people[pid].home == a.place for pid in remaining)):
            papers.setdefault(a.place, []).append("correspondance" if a.id.startswith("read:") else "albums")
    steps.append(_step("Correspondance et albums des personnes encore possibles", "done" if not papers else "next",
                       [f"{labels[place]} ({', '.join(kinds)})" for place, kinds in papers.items()],
                       note="Contexte et mobiles : ils orientent, ils n'écartent personne."))
    lab = [a for a in plan.actions if a.operation is Operation.ANALYZE and a.id not in done_ids
           and a.id not in ("analyze_drink",) and set(a.requires) <= known.keys()]
    carried = sorted(obj for obj in session.carried if "surface:" + obj not in journal_ids)
    # The hidden object: every container is worth a look, none is labelled.
    containers = [a for a in plan.actions if a.id.startswith(("search_bin:", "search_cupboard:")) and a.id not in done_ids
                  and (a.id.startswith("search_bin:") or any(people[pid].home == a.place for pid in remaining) or a.place == people[case.crime.kernel.roles.victim].home)]
    found = sorted(obj for obj in session.carried if not obj.startswith("mug:"))
    steps.append(_step("Retrouver l'objet du crime", "done" if session.linked else "next" if found or containers else "later",
                       [] if session.linked else [f"Analyser {session.object_label(obj)} — Le Laboratoire" for obj in carried] +
                       [f"{a.label} — {where(a)}" for a in containers][:6],
                       note="Un objet récupéré ne dit pas qui l'a tenu : le laboratoire et les empreintes parlent." if found and not session.linked else
                       f"{len(containers)} placard(s) ou poubelle(s) encore à fouiller" if containers and not session.linked else None))
    analyses = [f"{a.label} — Le Laboratoire{when(a)}" for a in lab]
    if analyses:
        steps.append(_step("Analyses au laboratoire", "next", analyses))
    if "fingerprints" in session.skills:
        todo = [obj for obj in sorted(session.carried) if obj not in session.prints]  # recovered objects, not household clutter
        prints = [f"Relever {session.object_label(obj)} — {labels[session.object_places[obj]] if obj not in session.carried else 'sur vous'}" for obj in todo]
        steps.append(_step("Empreintes sur les objets", "next" if prints else "done" if session.prints else "later", prints,
                           note="Un motif partagé est un contact, pas une preuve." if session.prints else None))
        on_crime = any(obj in session.prints for obj in session.linked)
        mugs = [pid for pid in sorted(remaining, key=lambda pid: people[pid].name) if "mug:" + pid not in session.prints]
        steps.append(_step("Comparer aux tasses des personnes encore possibles",
                           "later" if not on_crime else "next" if mugs else "done",
                           [f"Fouiller le logement de {people[pid].name} — {labels[people[pid].home]}" for pid in mugs] if on_crime else [],
                           note="Un motif absent de l'objet du crime écarte la personne." if on_crime else
                           "D'abord l'objet du crime, son analyse et son empreinte."))
    threads.append({"family": "matériel", "title": "Le matériel", "steps": steps})

    missing = [name for key, name in (("medical_window", "la période du crime"), ("victim_diary", "l'agenda de la victime")) if key not in known]
    return {"remaining": len(remaining), "accusable": len(remaining) == 1 and (not missing or not session.strict),
            "missing": missing if session.strict else [],
            "deadline": None if session.deadline is None else clock(session.deadline), "time_left": session.time_left,
            "turns_left": session.turns_left,
            "mistakes": session.mistakes, "threads": threads}


def render(view):
    """Plain text for the CLI."""
    marks = {"done": "✓", "next": "▶", "later": "·"}
    lines = [f"Candidats restants : {view['remaining']}" + (" — dossier prêt à déposer" if view["accusable"]
             else f" — il manque {', '.join(view['missing'])}" if view["missing"] else "")]
    if view["deadline"]:
        lines.append(f"Échéance : {view['deadline']}, {view['time_left'] // 60} h {view['time_left'] % 60:02d} restantes"
                     + (f" · {view['mistakes']} accusation(s) rejetée(s)" if view["mistakes"] else ""))
    for thread in view["threads"]:
        lines.append(f"\n{thread['title']}")
        for step in thread["steps"]:
            lines.append(f"  {marks[step['state']]} {step['title']}" + (f" — {step['note']}" if step.get("note") else ""))
            for action in step["actions"] if step["state"] == "next" else ():
                lines.append(f"      {action}")
    return "\n".join(lines)


# ------------------------------------------------------------------ audit

def main(argv=None):
    from scenario_play import sample_playable
    parser = argparse.ArgumentParser(description="Longueur des fils par famille, sur des affaires générées")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rows = [family_lengths(sample_playable(seed)) for seed in range(args.seed, args.seed + args.count)]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    n = len(rows)
    complete = {f: sum(1 for r in rows if r[f] is not None) for f in FAMILIES}
    print(f"{n} affaires — familles complètes : " + ", ".join(f"{f} {complete[f] / n:.0%}" for f in FAMILIES))
    both = sum(1 for r in rows if r["signalement"] is not None and r["horaires"] is not None)
    print(f"signalement et horaires tous deux complets : {both / n:.0%} ; équilibrées (deux fils, écart ≥ 2) : {sum(balanced(r) for r in rows) / n:.0%}")
    for f in FAMILIES:
        lengths = Counter(r[f] for r in rows if r[f] is not None)
        print(f"  {f:12} longueurs : " + ", ".join(f"{k}:{v}" for k, v in sorted(lengths.items())))
    shortest = Counter(min((f for f in FAMILIES if r[f] is not None), key=lambda f: r[f]) for r in rows)
    print("fil le plus court : " + ", ".join(f"{f} {c / n:.0%}" for f, c in shortest.most_common()))
    print("méthodes : " + ", ".join(f"{m} {c}" for m, c in Counter(r["method"] for r in rows).items()))


if __name__ == "__main__":
    main()
