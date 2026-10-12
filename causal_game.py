"""Public Godot projection of the causal CLI, without a second rules engine.

Only PlaySession performs discoveries and adjudicates accusations. This adapter
adds the existing mobile turn/navigation/dialogue protocol and replay saves.
"""
import math
from types import SimpleNamespace

from scenario_crime import NodeKind
from scenario_observations import Operation
from scenario_play import PlaySession, DIFFICULTY, clock, sample_playable, SERVICE_PARENTS
from scenario_access import next_day_routines
from scenario_means import Method
from scenario_evening import spoken_time
from scenario_threads import guide


VERSION = "causal-3d-v9"  # social fabric, partial alibis, poisoning room, lockpick walks in; new investigations required
TURN_MINUTES = 30  # one turn of six actions on the case clock
DIFFICULTIES = {"facile": "Échéance large", "normal": "Échéance serrée", "difficile": "Échéance très serrée"}
ITEMS = {"fingerprints": "Relevé d'empreintes · comparer les contacts sur les objets",
         "search": "Fouille minutieuse · examiner les objets plus rapidement",
         "rapport": "Contact humain · recueillir les témoignages plus rapidement",
         "lockpick": "Crochetage · entrer dans les appartements inoccupés"}
GRID = [["alley", "crime_scene", "victim_street", None, "promenade"],
        ["cctv", "bar", "police", None, None],
        ["cabaret", "lab", "hospital", None, None],
        [None, None, "restaurant", None, None]]
CAMERA_WINDOWS = {0: (18, "Avant 18 h"), 18: (20, "18 h – 20 h"),
                  20: (22, "20 h – 22 h"), 22: (24, "22 h – minuit")}


def at_label(label):
    if label.startswith("Le "):
        return "au " + label[3:]
    if label.startswith("La "):
        return "à la " + label[3:]
    if label.startswith("Les "):
        return "aux " + label[4:]
    if label.startswith(("L'", "L’")):
        return "à l’" + label[2:]
    return "à " + label


LOCKPICK_DIFFICULTY = 0.55  # the dial's arc width and needle speed, 0 easy .. 1 hard
PASS_MARK = 0.5  # inside the arc


class CausalGame:
    def __init__(self, seed, names, challenge=None):
        if len(names) != 1:
            raise ValueError("Le générateur causal est actuellement solo.")
        self.seed = seed
        # challenge(kind, difficulty) -> score in [0, 1]: the client's timing dial.
        # Without a client (tests, audits) the hand is perfect.
        self.challenge = challenge or (lambda kind, difficulty: 1.0)
        self.case = sample_playable(seed)
        self.session = PlaySession(self.case)
        self.players = [SimpleNamespace(name=names[0], items=set(), ap=6, place=self.session.place)]
        self.player = self.players[0]
        self.tick, self.history, self.starts_chosen = 0, [], []
        self.winner = None
        self.difficulty, self.ending = "normal", ""
        self.speaker = None
        self.camera_block = None
        self.camera_place = None
        self._legacy_camera_replay = False
        self._legacy_camera_controls = False
        self._legacy_wait_replay = False
        self._legacy_service_status_replay = False
        self.priced_from = 0
        self._legacy_question_replay = False
        self.cue = None
        self.equipped = False
        self.note_turns = []
        self.questions_paid = set()
        self.unlocked_homes = set()
        self.routines = next_day_routines(self.case)
        self.homes = {n.id: next(iter(self.case.witnesses.streets.neighbors(n.id)))[0]
                      for n in self.case.witnesses.streets.nodes if n.kind is NodeKind.HOME}
        self.outdoors = {n.id for n in self.case.crime.streets.nodes if n.kind is NodeKind.STREET}
        self.parents = {**self.homes, "morgue": "hospital"}
        self.roots = [q for row in GRID for q in row if q]

    def starts(self, items):
        return self.roots

    def setup(self):
        return {"items": ITEMS, "slots": 2, "free_starts": self.roots,
                "paid_starts": {}, "default_start": self.case.crime.scene,
                "difficulties": DIFFICULTIES, "default_difficulty": "normal"}

    def equip(self, index, items, start, difficulty="normal"):
        if index != 0 or start not in self.starts(items):
            raise ValueError("Départ indisponible")
        if difficulty not in DIFFICULTY:  # "libre" (no deadline) stays a test hook: setup() never offers it
            raise ValueError("Difficulté inconnue")
        # Free mode: any named person can be accused, a mistake costs time,
        # and the deadline scales with the shortest thread of this case.
        self.session = PlaySession(self.case, tuple(items), strict=False, difficulty=difficulty, turn_minutes=TURN_MINUTES,
                                   greeting_reveals_evening=False)  # the evening is the "Alibi" question, asked on purpose
        self.difficulty = difficulty
        self.session.place = start
        self.player.items, self.player.place = set(items), start
        self.starts_chosen = [start]
        self.equipped = True
        self.update_positions()

    def update_positions(self):
        self.position_at = self.session.at
        self.session.person_places = {r.person: r.place_at(self.session.at) for r in self.routines}

    def occupants(self, home):
        return sorted(pid for pid, place in self.session.person_places.items() if place == home)

    def home_open(self, home):
        # The victim's home is released to the investigation. Private occupied
        # homes cannot be entered, even with the lockpicking skill.
        return not self.occupants(home) and (home in self.unlocked_homes or home == self.case.life.people[self.case.crime.kernel.roles.victim].home)

    def open_questions(self, pid):
        self.speaker = pid
        if "profile:" + pid not in dict(self.session.state.known):
            self.session.do("meet:" + pid)
            self.player.ap -= 1
        self._cue("", person=self.person(pid), active=True)
        self.cue["stage"] = "greeting"

    def ending_view(self):
        """The closing card. Private truth is only consulted once the case is over."""
        s = self.session
        if not s.finished:
            return None
        if self.winner:
            return {"won": True, "title": "Affaire résolue", "text": self.ending, "mistakes": s.mistakes}
        closed = next((r["text"] for r in s.journal if r["id"] == "closed"), "L'affaire est classée sans suite.")
        author = self.case.life.people[self.case.crime.kernel.roles.author]
        return {"won": False, "title": "Affaire classée", "mistakes": s.mistakes,
                "text": closed + "\n" + author.name + " ne sera jamais inquiété(e) : " + self.case.crime.method.label.lower() + ", et personne pour le prouver."}

    def start(self):
        victim = self.case.life.people[self.case.crime.kernel.roles.victim]
        text = f"On a retrouvé {victim.name} sans vie à {self.session.locations[self.case.crime.scene]}.\nLe lendemain, 8 h. Les lieux viennent d'être ouverts aux enquêteurs.\nSon domicile : {self.session.locations[victim.home]}."
        self._cue(text, name=self.player.name)
        self.cue["id"] = 0
        self.cue["context"] = "Votre affaire"
        return []

    def snapshot(self):
        return {"generator": VERSION, "items": sorted(self.player.items),
                "start": self.player.place if not self.starts_chosen else self.starts_chosen[0],
                "history": self.history, "priced_from": self.priced_from, "difficulty": self.difficulty}

    @classmethod
    def restore(cls, seed, name, data, equipped, challenge=None):
        if data.get("generator") != VERSION:
            raise ValueError("Version du générateur causal incompatible")
        game = cls(seed, [name], challenge)
        # Older histories had free biography/about questions. Preserve those
        # past costs, then apply the new rule only to subsequent live questions.
        game.priced_from = data.get("priced_from", len(data["history"]))
        if equipped:
            game.equip(0, data["items"], data["start"], data.get("difficulty", "normal"))
            game.start()
            for index, key in enumerate(data["history"]):
                game._legacy_question_replay = index < game.priced_from
                if key[:2] == ["ask", "testimony"]:
                    key = ["ask", "evening"]
                # v14 history queried a terminal on the source street. Replay
                # those past acquisitions without allowing that access in a
                # new live command, or changing their time/AP/recordings.
                game._legacy_camera_replay = key[0] == "camera_menu" and game.session.place != "cctv"
                game._legacy_wait_replay = key == ["wait"]
                # Old saves can contain this formerly offered no-op question.
                # Replay it faithfully without offering it in live menus.
                game._legacy_service_status_replay = key[:2] == ["ask", "service_status"]
                game._legacy_camera_controls = key[:2] in (["ask", "camera_block"], ["ask", "camera_hour"], ["ask", "camera_back"])
                game.play(tuple(key))
                game._legacy_camera_replay = False
                game._legacy_wait_replay = False
                game._legacy_service_status_replay = False
                game._legacy_question_replay = False
                game._legacy_camera_controls = False
            if game.speaker == "camera" and game.session.place != "cctv":
                game.play(("stop",))
        return game

    def cost(self, place):
        streets = self.case.witnesses.streets
        origin = self.session.place if self.session.place in streets._adjacency else SERVICE_PARENTS[self.session.place]
        target = place if place in streets._adjacency else SERVICE_PARENTS[place]
        path = streets.path(origin, target)
        minutes = sum(streets.duration(a, b) for a, b in zip(path, path[1:]))
        minutes += 3 * (self.session.place not in streets._adjacency) + 3 * (place not in streets._adjacency)
        return max(1, math.ceil(minutes / 6))

    def waiting_for(self):
        """Only an actually requested exam or already-acquired lab sample."""
        s, known = self.session, dict(self.session.state.known)
        pending = []
        for a in self.case.plan.actions:
            if a.place != s.place or not a.processing_minutes or a.id in s.state.completed or not set(a.requires) <= known.keys():
                continue
            ready = max(a.available_at, max((known[k] for k in a.requires), default=0) + a.processing_minutes)
            if ready > s.at:
                pending.append((ready, "le compte rendu du médecin légiste" if a.id == "read_medical" else "le résultat du prélèvement sanguin" if a.id == "analyze_blood" else "le résultat de l'analyse du verre"))
        return min(pending) if pending else None

    def person(self, pid):
        p = self.case.life.people[pid]
        known = pid in self.session.named_people()
        appearance = next(a for a in self.case.evidence.appearances if a.person == pid)
        return {"id": int(pid[1:]), "name": p.name if known else None,
                "activity": next(r.activity_at(getattr(self, "position_at", self.session.at)) for r in self.routines if r.person == pid),
                "look": "cheveux " + appearance.hair.value + " · " + appearance.coat.value + " · " + appearance.height.value,
                "appearance": {"coat": appearance.coat.value, "height": appearance.height.value, "hair": appearance.hair.value}}

    def source_person(self, actor, operation):
        name = next((w.name for w in self.case.witnesses.witnesses if w.id == actor), None)
        if name is None:
            name = next((k.name for k in self.case.crime.keepers if k.id == actor), None)
        name = name or ("Médecin légiste" if actor == "staff:medical" else "Technicienne du laboratoire" if actor == "staff:lab" else "Le commissaire" if actor == "staff:police" else "Témoin de la soirée" if operation is Operation.VERIFY else "Personnel du lieu")
        is_witness = actor.startswith("witness:")
        role = "Témoin" if is_witness else "Personnel"
        placement = "witness" if is_witness else "bar_staff" if actor == "staff:bar" else "restaurant_staff" if actor == "staff:restaurant" else "reception"
        reports = [a for a in self.case.plan.actions if a.actor == actor and a.id.startswith("verify:")
                   and "evening:" + a.id.split(":", 1)[1] in dict(self.session.state.known)]
        done = sum(a.id in self.session.state.completed for a in reports)
        return {"id": actor, "name": name, "look": "", "service": True,
                "role": role, "placement": placement,
                "verification": {"done": done, "total": len(reports)},
                "portrait_id": 20 + sum(map(ord, actor)) % 13, "actions": []}

    def staff_rows(self):
        s, known = self.session, dict(self.session.state.known)
        return [a for a in self.case.plan.actions if a.place == s.place
                and a.actor not in self.case.plan.population
                and (a.operation in (Operation.INTERVIEW, Operation.VERIFY, Operation.ASK_STOCK) or a.actor.startswith("staff:"))
                and any(start <= s.at and (end is None or s.at <= end) for start, end in a.windows)
                and (a.operation is not Operation.VERIFY or set(a.requires) <= known.keys())]

    def notebook_contacts(self, labels):
        """Named witnesses/services, outside the suspect roster and its flags."""
        import re
        s = self.session
        met = {key[1] for key in self.history if key[0] == "service_menu"}
        if self.speaker and self.speaker not in self.case.plan.population:
            met.add(self.speaker)
        text = "\n".join(r["text"] for r in s.journal)
        actors = {}
        for a in self.case.plan.actions:
            if a.actor in self.case.plan.population or not (
                a.operation in (Operation.INTERVIEW, Operation.VERIFY, Operation.ASK_STOCK) or a.actor.startswith("staff:")
            ):
                continue
            person = self.source_person(a.actor, a.operation)
            mentioned = re.search(r"(?<!\w)" + re.escape(person["name"]) + r"(?!\w)", text)
            if not mentioned and a.actor not in met and a.id not in s.state.completed:
                continue
            row = actors.setdefault(a.actor, {"id": a.actor, "name": person["name"], "role": person["role"],
                "met": a.actor in met or a.id in s.state.completed,
                "portrait_id": person["portrait_id"], "place": a.place, "place_label": labels[a.place], "statements": []})
            if a.id in s.state.completed:
                row["met"] = True
                row["statements"].extend(r["text"] for r in s.journal if r["id"] in a.reveals)
        return sorted(actors.values(), key=lambda r: (r["role"], r["name"]))

    def crime_timing(self):
        s, known = self.session, dict(self.session.state.known)
        if "medical_window" in known:
            start, end = self.case.claims["medical_window"]["window"]
            return {"state": "known", "start": start, "end": end,
                    "label": "Hier · " + clock(start) + " – " + clock(end),
                    "text": next(r["text"] for r in s.journal if r["id"] == "medical_window"),
                    "objective": "Rapport conservé dans Horaires et Notes ; le légiste peut le rappeler gratuitement."}
        if "exam_request" in known:
            turns = math.ceil(max(0, known["exam_request"] + 60 - s.at) / 15)
            return {"state": "pending" if turns else "ready", "turns": turns,
                    "label": "Rapport dans %d tour%s au plus" % (turns, "s" if turns != 1 else "") if turns else "Rapport prêt à la morgue",
                    "text": "L'examen est en cours. Le rapport est attendu à la morgue dans %d tour%s au plus." % (turns, "s" if turns != 1 else "") if turns else "Le médecin légiste a terminé l'examen. Le rapport attend à la morgue, à l'hôpital.",
                    "objective": "Sur place · toucher le médecin légiste → Quelle est la période du crime ?"}
        return {"state": "unrequested", "label": "Période du crime inconnue",
                "text": "L'examen du corps à la morgue permet d'estimer la période du crime, pour la comparer aux récits et aux images.",
                "objective": "Examiner la scène, puis à la morgue · toucher le légiste → Faire transférer et examiner le corps (1 PA)."}

    def service_status(self, actor):
        s, known = self.session, dict(self.session.state.known)
        if actor == "staff:medical" and "medical_window" in known:
            return next(r["text"] for r in s.journal if r["id"] == "medical_window")
        rows = [a for a in self.case.plan.actions if a.place == s.place and a.actor == actor]
        if rows and all(a.id in s.state.completed for a in rows):
            return "Je vous ai déjà remis mes conclusions." if actor.startswith("staff:") else "Je vous ai déjà raconté tout ce dont je me souviens."
        if actor in ("staff:medical", "staff:lab"):
            pending = self.waiting_for()
            if pending:
                turns = math.ceil((pending[0] - s.at) / 15)
                return f"C'est encore en préparation. Vous aurez {pending[1]} d'ici {turns} tour{'s' if turns != 1 else ''} au plus."
            if actor == "staff:medical":
                return "Le compte rendu est prêt. Vous pouvez me demander les conclusions de l'examen." if "exam_request" in known else "Je peux examiner le corps dès son transfert ici, et estimer la période du crime. Vous souhaitez que je commence ?"
            return "Je n'ai aucun résultat à vous remettre pour l'instant." if not any(a["actor"] == actor for a in s.options()) else "Les résultats sont prêts."
        if "victim_reference" not in known:
            return "Vous avez une photo de la personne dont vous me parlez ? Sans ça, je ne peux pas vous répondre."
        return "Dites-moi ce que vous voulez savoir."

    def _cue(self, text, name="Carnet d'enquête", person=None, active=False, question=None):
        self.cue = {"id": len(self.history) + 1, "stage": "reply", "text": text,
                    "question": question, "notes": [], "active": active, "remaining_pa": self.player.ap,
                    "context": "Images · " + self.session.locations[self.camera_place] + " · hier" if self.speaker == "camera" and self.camera_place else "Régie vidéo · hier" if self.speaker == "camera" else "Conversation" if active else "Observation consignée",
                    "terminal": self.speaker == "camera",
                    "remaining": 3 if active else 0,
                    "person": person or {"id": -1, "name": name, "look": "", "detective": True}}
        if person and person.get("role"):
            self.cue["context"] = person["role"] + " · Source d'information"

    def question_cost(self, key):
        """First acquisition costs one PA; a heard answer is free to repeat."""
        s = self.session
        if key[0] == "talk_about":
            return int(not self._legacy_question_replay and not any(
                r["id"] == "about:" + self.speaker + ":p" + str(key[2]) for r in s.journal))
        if key[0] != "ask" or key[1] == "service_status":
            return 0
        if key[1] == "service_action":
            return int(key[2] not in s.state.completed)
        if self.speaker == "camera" and key[1] in ("camera_window", "camera_hour"):
            artifact = ("camera_window:" if key[1] == "camera_window" else "camera:") + self.camera_place + ":" + str(key[2])
            return int(not any(r["id"] == artifact for r in s.journal))
        if self.speaker not in self.case.plan.population:
            return 0  # Archive navigation/status are not a fresh deposition.
        topic = key[1]
        action = {"messages": "ask_messages:", "evening": "interview:",
                  "observations": "observe:", "motive": "motive:"}.get(topic)
        heard = ((self.speaker, topic) in self.questions_paid
                 or action is not None and action + self.speaker in s.state.completed
                 or any(r["id"] == "context:" + self.speaker + ":" + topic for r in s.journal))
        legacy_free = self._legacy_question_replay and topic not in ("messages", "evening", "motive", "observations")
        return int(not heard and not legacy_free)

    def options(self, include_unavailable=False):
        s, p = self.session, self.player
        if s.finished:
            return {}
        if self.speaker is not None:
            options = {("stop",): "Fin de conversation"}
            if self.speaker not in self.case.plan.population and self.speaker != "camera":
                rows = list(s.options())
                rows.extend({"id": a.id, "actor": a.actor, "operation": a.operation.value, "label": a.label}
                            for a in self.case.plan.actions if a.actor == self.speaker and a.id in s.state.completed)
                for row in rows:
                    if row["actor"] != self.speaker:
                        continue
                    question = {"ask_stock": "Vous avez remarqué quelque chose d'inhabituel ici ?",
                                "interview": "Qu'avez-vous vu hier soir ?",
                                "verify": "Que s'est-il passé hier soir ?"}.get(row["operation"], row["label"])
                    question = {"read_medical": "Quelle est la période du crime ?",
                                "request_exam_morgue": "Faire transférer et examiner le corps",
                                "analyze_drink": "Que donne l'analyse du verre ?",
                                "analyze_blood": "Que donne le prélèvement sanguin ?"}.get(row["id"], question)
                    if row["id"].startswith("venue_guests:"):
                        question = "Qui est venu hier soir ?"
                    if row["id"].startswith("verify:"):
                        question = "Vérifier le récit de " + self.case.life.people[row["id"].split(":", 1)[1]].name
                    if row["id"].startswith("record:"):
                        pid = row["id"].split(":", 1)[1]
                        question = "Casier · " + (self.case.life.people[pid].name if pid in s.named_people() else "Fiche n°" + str(int(pid[1:]) + 1))
                    options[("ask", "service_action", row["id"])] = question + " (1 PA)"
                # Only actual analysis services have a useful status to recall.
                # Put that recall after the concrete questions, never ahead of
                # the first question asked to a barman/server/witness.
                if self.speaker == "staff:medical":
                    options[("ask", "service_status")] = "Rappeler la période du crime" if "medical_window" in dict(s.state.known) else "Où en est l'examen ?"
                elif self.speaker == "staff:lab":
                    options[("ask", "service_status")] = "Les analyses sont-elles prêtes ?"
                elif self._legacy_service_status_replay:
                    options[("ask", "service_status")] = "Vous avez quelque chose à ajouter ?"
            elif self.speaker == "camera":
                options[("stop",)] = "Fermer les archives vidéo"
                if self.camera_place is None:
                    options.update({("ask", "camera_district", c.place): s.locations[c.place] for c in self.case.evidence.cameras})
                elif not self._legacy_camera_controls:
                    done = {r["id"] for r in s.journal}
                    options.update({("ask", "camera_window", start): "Hier · " + label + (" · consulté" if f"camera_window:{self.camera_place}:{start}" in done else " (1 PA)")
                                    for start, (_, label) in CAMERA_WINDOWS.items()
                                    if p.ap or include_unavailable or f"camera_window:{self.camera_place}:{start}" in done})
                    options[("ask", "camera_district_back")] = "Autre quartier"
                elif self.camera_block is None:
                    options.update({("ask", "camera_block", h): f"Hier · {h:02d} h – {h + 6:02d} h" for h in range(0, 24, 6)})
                    options[("ask", "camera_district_back")] = "Autre quartier"
                else:
                    done = {r["id"] for r in s.journal} | set(s.state.completed)
                    options.update({("ask", "camera_hour", h): f"Hier · {h:02d} h – {h + 1:02d} h (1 PA)"
                                    for h in range(self.camera_block, self.camera_block + 6)
                                    if p.ap and f"camera:{self.camera_place}:{h}" not in done})
                    options[("ask", "camera_back")] = "Autre plage horaire"
            else:
                options[("ask", "relation")] = "Votre relation avec la victime ?"
                # Uniform menu and first-question costs, independent of guilt,
                # relationship, message count and witness role. Replies may
                # differ; the presence/absence of a button cannot be a clue.
                options[("ask", "evening")] = "Alibi · Où étiez-vous hier soir ? (1 PA, une fois)"
                options[("ask", "observations")] = "Témoin · Avez-vous remarqué quelque chose ? (1 PA, une fois)"
                options[("ask", "motive")] = "Mobile · Y avait-il des tensions ? (1 PA, une fois)"
                options[("ask", "work")] = "Votre travail ?"
                options[("ask", "circle")] = "Qui fréquentait " + self.case.life.people[self.case.crime.kernel.roles.victim].name + " ?"
                if "victim_diary" in dict(s.state.known) and self.case.claims["victim_diary"]["appointment"]:
                    options[("ask", "appointment")] = "Le rendez-vous noté dans son agenda ?"
                options.update({("talk_about", int(self.speaker[1:]), int(pid[1:])): person.name
                                for pid, person in self.case.life.people.items() if pid != self.speaker})
            for key in list(options):
                if key[0] not in ("ask", "talk_about") or key[1] == "service_status" or self.speaker == "camera":
                    continue
                cost = self.question_cost(key)
                options[key] = options[key].split(" (", 1)[0] + (" (1 PA)" if cost else " (gratuit)")
                if cost > p.ap and not include_unavailable and not self._legacy_question_replay:
                    del options[key]
            return options
        result = {("end",): "Terminer le tour"}
        result.update({("service_menu", a.actor): "Parler à " + self.source_person(a.actor, a.operation)["name"]
                       for a in self.staff_rows()})
        for pid in self.case.plan.population:
            if s.person_place(pid) == s.place and "profile:" + pid in dict(s.state.known):
                result[("interrogate", int(pid[1:]))] = "Parler"
        for home, street in self.homes.items():
            occupants = self.occupants(home)
            if street == s.place and occupants and "profile:" + occupants[0] in dict(s.state.known):
                result[("ring", home)] = "Sonner"
        if not p.ap:
            return result
        for place in s.locations:
            if place == s.place or self.cost(place) > p.ap:
                continue
            if place in self.parents and self.parents[place] != s.place:
                continue
            if place in self.homes and not self.home_open(place):
                continue
            result[("move" if place in self.parents else "walk", place)] = f"Aller à {s.locations[place]} ({self.cost(place)} PA)"
        for row in s.options():
            if row["id"].startswith("meet:"):
                result[("interrogate", int(row["actor"][1:]))] = row["label"] + " (1 PA)"
            elif not row["id"].startswith("ask_messages:"):
                if not (row["actor"] in self.case.plan.population and row["id"].startswith(("interview:", "observe:"))):
                    result[("investigate", row["id"])] = row["label"] + " (1 PA)"
        # A known suspect remains physically available, even after the profile
        # discovery was consumed. Reopening a conversation does not cost PA.
        for pid in self.case.plan.population:
            if s.person_place(pid) == s.place:
                result[("interrogate", int(pid[1:]))] = "Parler" + (" (1 PA)" if "profile:" + pid not in dict(s.state.known) else "")
        for home, street in self.homes.items():
            if street != s.place:
                continue
            result[("ring", home)] = "Sonner" + (" (1 PA)" if any("profile:" + pid not in dict(s.state.known) for pid in self.occupants(home)) else "")
            if not self.occupants(home) and not self.home_open(home):
                # Anyone may try the lock; the skill skips the timing dial.
                result[("unlock_home", home)] = "Crocheter la porte (1 PA" + (")" if "lockpick" in s.skills else " · adresse)")
        if (s.place == "cctv" or self._legacy_camera_replay) and "scene_body" in dict(s.state.known):
            result[("camera_menu",)] = "Consulter les archives vidéo"
        for obj in sorted(s.found):
            if obj in s.carried or s.object_places[obj] == s.place:
                if "fingerprints" in s.skills and obj not in s.prints:
                    result[("fingerprint", obj)] = "Relever : " + s.object_label(obj) + " (1 PA)"
            if s.place == "lab" and obj in s.carried and not any(r["id"] == "surface:" + obj for r in s.journal):
                surface = next((r for r in self.case.evidence.surfaces if r.object == obj), None)
                required = "blood_reference" if surface and surface.kind == "victim_blood" else "drink_result" if surface else None
                if required is None or required in dict(s.state.known):
                    result[("analyze_object", obj)] = "Analyser : " + s.object_label(obj) + " (1 PA)"
        if s.place == "police":
            result.update({("accuse", int(pid[1:])): "Déposer le dossier : " + person.name
                           for pid, person in self.case.life.people.items()
                           if pid in s.named_people() and pid not in s.cleared})
        if self._legacy_wait_replay:
            result[("wait",)] = "Ancienne attente · 15 minutes"
        return result

    def play(self, key):
        key = tuple(key)
        replayed_score = None
        if key[:1] == ("unlock_home",) and len(key) == 3:  # a saved attempt carries its dial score
            replayed_score = float(key[2])
            key = key[:2]
        if self.session.finished and key == ("stop",):
            # Closing a conversation after the case is closed is always allowed: no dead end.
            self.speaker, self.camera_block, self.camera_place = None, None, None
            self.session.doorstep = None
            self.cue = None
            self.history.append(list(key))
            return []
        options = self.options()
        if key not in options:
            raise ValueError("Cette action n'est pas disponible ici.")
        s, p = self.session, self.player
        action, text = key[0], ""
        before = len(s.journal)
        self.cue = None
        if action in ("walk", "move"):
            p.ap -= self.cost(key[1])
            text = s.go(key[1])
            s.doorstep = None
        elif action == "end":
            self.tick += 1
            p.ap = 6
            s.end_turn()  # the clock only moves here; a case past its deadline closes now
            s.doorstep = None
            self.update_positions()
            if s.place in self.homes and self.occupants(s.place):
                s.go(self.homes[s.place])
                text = "Vous regagnez le couloir avant le retour des habitants."
        elif action == "stop":
            self.speaker, self.camera_block, self.camera_place = None, None, None
            s.doorstep = None
        elif action == "ring":
            people = self.occupants(key[1])
            if people:
                s.doorstep = key[1]
                self.open_questions(people[0])
            else:
                self._cue("Personne ne répond. L'appartement est vide.", name=p.name)
        elif action == "unlock_home":
            # Picking the lock walks you in: one action, no second trip through the menu.
            # Without the skill, the timing dial decides; the score is saved with the move.
            p.ap -= 1
            score = None
            if "lockpick" not in s.skills:
                score = replayed_score if replayed_score is not None else float(self.challenge("lockpick", LOCKPICK_DIFFICULTY))
            if score is None or score >= PASS_MARK:
                self.unlocked_homes.add(key[1])
                s.go(key[1])
                s.doorstep = None
                self._cue("La serrure cède. Vous entrez dans l'appartement." if score is None else
                          "Le pêne glisse au bon moment. Vous entrez dans l'appartement.", name=p.name)
            else:
                self._cue("Le crochet ripe, la serrure tient. Il faudra réessayer.", name=p.name)
            if score is not None:
                key = key + (round(score, 3),)
        elif action == "interrogate":
            self.open_questions("p" + str(key[1]))
        elif action == "service_menu":
            self.speaker = key[1]
            row = next(a for a in self.staff_rows() if a.actor == self.speaker)
            self._cue("", person=self.source_person(self.speaker, row.operation), active=True)
            self.cue["stage"] = "greeting"
        elif action == "ask":
            if self.speaker not in self.case.plan.population and self.speaker != "camera":
                row = next(a for a in self.case.plan.actions if a.actor == self.speaker)
                if key[1] == "service_status":
                    text = self.service_status(self.speaker)
                else:
                    cost = self.question_cost(key)
                    if cost:
                        text = s.do(key[2])
                    else:
                        action_row = next(a for a in self.case.plan.actions if a.id == key[2])
                        text = "\n\n".join(r["text"] for r in s.journal if r["id"] in action_row.reveals)
                    p.ap -= cost
                self._cue(text, person=self.source_person(self.speaker, row.operation), active=True, question=options[key])
            elif self.speaker == "camera":
                if key[1] == "camera_district":
                    self.camera_place, self.camera_block = key[2], None
                    text = "Images de " + s.locations[self.camera_place] + ". Quelle plage horaire de la veille ?"
                elif key[1] == "camera_district_back":
                    self.camera_place, self.camera_block = None, None
                    text = "Quel quartier souhaitez-vous consulter ?"
                elif key[1] == "camera_block":
                    self.camera_block = key[2]
                    text = "Sélectionnez une heure de l'enregistrement d'hier."
                elif key[1] == "camera_back":
                    self.camera_block = None
                    text = "Quelle plage horaire souhaitez-vous consulter ?"
                elif key[1] == "camera_window":
                    text, fresh = s.camera_window(key[2], CAMERA_WINDOWS[key[2]][0], place=self.camera_place)
                    p.ap -= int(fresh)
                else:
                    text = s.camera(key[2], place=self.camera_place)
                    p.ap -= 1
                self._cue(text, "Terminal vidéo", active=True)
            else:
                topic = key[1]
                if topic in ("messages", "evening", "motive", "observations"):
                    action_id = {"messages": "ask_messages:", "evening": "interview:", "observations": "observe:", "motive": "motive:"}[topic] + self.speaker
                    action_row = next((a for a in self.case.plan.actions if a.id == action_id), None)
                    context_id = "context:" + self.speaker + ":" + topic
                    already = action_id in s.state.completed or any(r["id"] == context_id for r in s.journal)
                    paid = (self.speaker, topic) in self.questions_paid or already
                    if not paid and not p.ap:
                        self._cue("Plus de PA pour poursuivre l'interrogatoire. Vous pouvez fermer la conversation et reprendre au prochain tour.", name=p.name, active=True)
                    else:
                        if not paid:
                            p.ap -= 1
                            self.questions_paid.add((self.speaker, topic))
                        if action_row and not already and action_id not in {a["id"] for a in s.options()}:
                            self._cue("Cette déposition sera accessible après le constat sur la scène. Cette question ne vous coûtera pas de nouveau PA.", name=p.name, active=True)
                        elif action_row and not already:
                            text = s.do(action_id)
                            self._cue(text, person=self.person(self.speaker), active=True, question=options[key])
                        elif action_row and already:
                            text = "\n\n".join(r["text"] for r in s.journal if r["id"] in action_row.reveals)
                            self._cue(text, person=self.person(self.speaker), active=True, question=options[key])
                        else:
                            text = s.ask_context(self.speaker, topic)
                            self._cue(text, person=self.person(self.speaker), active=True, question=options[key])
                else:
                    cost = self.question_cost(key)
                    text = s.ask_context(self.speaker, topic)
                    p.ap -= cost
                    self.questions_paid.add((self.speaker, topic))
                    self._cue(text, person=self.person(self.speaker), active=True, question=options[key])
        elif action == "talk_about":
            cost = self.question_cost(key)
            text = s.talk_about(self.speaker, "p" + str(key[2]))
            p.ap -= cost
            self._cue(text, person=self.person(self.speaker), active=True, question="Et " + self.case.life.people["p" + str(key[2])].name + " ?")
        elif action == "camera_menu":
            self.speaker = "camera"
            self.camera_place = s.place if self._legacy_camera_replay else None
            self.camera_block = None
            self._cue("Archives vidéo de la ville. Quel quartier souhaitez-vous consulter ?", "Terminal vidéo", active=True)
        elif action == "wait":
            s._advance(15 if len(key) == 1 else key[1])
            text = "Il est " + clock(s.at) + "."
            if s.place == "morgue":
                text += " Le médecin légiste peut maintenant vous recevoir."
            elif s.place == "lab":
                text += " Le résultat est maintenant disponible au laboratoire."
        elif action == "accuse":
            won, text = s.accuse("p" + str(key[1]))
            if won:
                self.winner, self.ending = p, text
            self._cue(text, "Commissariat")
            self.cue["context"] = "Dossier accepté" if won else "Dossier rejeté"
        else:
            if action == "investigate":
                text = s.do(key[1])
            elif action == "fingerprint":
                text = s.fingerprint(key[1])
            elif action == "analyze_object":
                text = s.analyze_object(key[1])
            p.ap -= 1
            row = next((a for a in self.case.plan.actions if action == "investigate" and a.id == key[1]), None)
            if row and (row.operation in (Operation.INTERVIEW, Operation.VERIFY, Operation.ASK_STOCK) or row.actor.startswith("staff:")):
                self._cue(text, person=self.source_person(row.actor, row.operation), question=options[key])
            else:
                self._cue(text)
        self.note_turns.extend([self.tick + 1] * (len(s.journal) - before))
        p.place = s.place
        self.history.append(list(key))
        return [] if self.cue else ([text] if text else [])

    def fixture_catalogue(self, place):
        """Physical furniture is independent of remaining discovery actions.

        Slots are assigned before filtering the transported body, so removing
        it cannot move another object. Only actions/selectors change on use.
        """
        fixtures = {}
        for row in self.case.plan.actions:
            if (row.place != place or row.actor in self.case.plan.population
                    or row.actor.startswith("staff:") or row.operation in (
                        Operation.INTERVIEW, Operation.VERIFY, Operation.ASK_STOCK, Operation.CAMERA)):
                continue
            prop, title = "desk", "Affaires du lieu"
            if row.id.startswith("search_bin:"):
                prop, title = "trash", "Poubelle"
            elif row.id in ("inspect_scene", "request_exam"):
                prop, title = "body", "Corps de la victime"
            elif row.id == "collect_blood":
                prop, title = "blood", "Traces de sang"
            elif row.id == "collect_drink":
                prop, title = "drink", "Verre près de la victime"
            elif row.id == "collect_object":
                prop, title = "evidence", "Objet au sol"
            elif row.id.startswith("read:"):
                prop, title = "terminal", "Terminal domestique"
            elif row.id.startswith("photos:"):
                prop, title = "album", "Album de photos"
            elif row.id == "read_diary":
                prop, title = "diary", "Agenda de la victime"
            elif row.id.startswith("search:"):
                title = "Objets du logement"
            elif row.id.startswith("search_cupboard:"):
                prop, title = "cupboard", "Placard"
            fixtures.setdefault(row.actor, {"id": row.actor, "name": title, "prop": prop,
                                            "object": True, "actions": []})
        if place == "morgue":
            fixtures["fixture:exam_table"] = {"id": "fixture:exam_table", "name": "Table d'examen",
                                              "prop": "morgue", "object": True, "actions": []}
        if place == "cctv":
            fixtures["camera"] = {"id": "camera", "name": "Archives vidéo · quartiers & heures",
                                   "prop": "terminal", "object": True, "actions": []}
        if place == "police":
            fixtures["police"] = {"id": "police", "name": "Déposer un dossier",
                                   "prop": "desk", "object": True, "actions": []}
        if place == "lab" or "fingerprints" in self.session.skills:
            # A carried kit exists from equipment selection, not only when a
            # first print is available. It is never a desk popping up in a street.
            fixtures["objects"] = {"id": "objects", "name": "Poste d'analyse" if place == "lab" else "Kit de relevé d'empreintes",
                                    "prop": "desk" if place == "lab" else "kit", "object": True, "actions": []}
        for slot, fixture in enumerate(fixtures.values()):
            fixture["slot"] = slot
            if fixture["prop"] == "evidence":
                fixture["shape"] = next(t.kind.value for t in self.case.crime.inventory
                                         if t.id == self.case.crime.execution.tool)
        return fixtures

    def view(self, player):
        s, known = self.session, dict(self.session.state.known)
        options = self.options() if self.equipped else {}
        dialogue_options = [[list(key), label, {"cost": self.question_cost(key),
                             "available": key in options}] for key, label in self.options(True).items()] if self.speaker is not None else []
        labels = dict(s.locations)
        victim = self.case.life.people[self.case.crime.kernel.roles.victim]
        for home in self.homes:
            residents = [p for p in self.case.life.people.values() if p.home == home]
            identified = [p.name for p in residents if p.id == victim.id or "profile:" + p.id in known]
            if residents:
                labels[home] = "Chez " + " et ".join(identified) if identified else "Appartement " + home.removeprefix("home")
        adjacency = {n.id: [q for q, _ in self.case.witnesses.streets.neighbors(n.id)] for n in self.case.witnesses.streets.nodes}
        for service in ("lab", "morgue"):
            parent = SERVICE_PARENTS[service]
            adjacency[service] = [parent]
            adjacency[parent].append(service)
        places = {q: {"label": label, "street": self.parents.get(q), "custom": q == "morgue",
                      "searched": any(a.place == q and a.id in s.state.completed and a.operation is Operation.SEARCH for a in self.case.plan.actions),
                      "lit": any(p.home == q and p.id in self.case.plan.population for p in self.case.life.people.values())}
                  for q, label in labels.items()}
        present_by_place = {q: [self.person(pid) for pid in sorted(self.case.plan.population) if s.person_places[pid] == q] for q in places}
        districts = {q: {"people": [], "count": 0, "scope": "suspects"} for q in self.roots}
        for q, rows in present_by_place.items():
            region = self.parents.get(q, q)
            districts[region]["people"].extend({"id": r["id"], "name": r["name"], "look": r["look"], "known": r["name"] is not None} for r in rows)
            districts[region]["count"] += len(rows)
        presence = {"districts": districts, "places": {q: {"people": [{**r, "known": r["name"] is not None} for r in rows], "count": len(rows), "scope": "suspects"} for q, rows in present_by_place.items()}}
        fixtures, staff = self.fixture_catalogue(s.place), {}
        physical_options = dict(options)
        for row in s.options():
            if not row["id"].startswith(("meet:", "ask_messages:")) and row["actor"] not in self.case.plan.population:
                physical_options.setdefault(("investigate", row["id"]), row["label"])
        if s.place == "cctv":
            physical_options.setdefault(("camera_menu",), "Consulter les archives vidéo")
        for key, label in physical_options.items():
            if key[0] == "investigate":
                row = next(a for a in self.case.plan.actions if a.id == key[1])
                if row.operation in (Operation.INTERVIEW, Operation.VERIFY, Operation.ASK_STOCK) or row.actor.startswith("staff:"):
                    pid = row.actor
                    target = staff.setdefault(pid, self.source_person(pid, row.operation))
                else:
                    target = fixtures[row.actor]
                if key in options:
                    target["actions"].append([list(key), label])
            elif key[0] in ("fingerprint", "analyze_object", "camera_menu", "accuse"):
                fid = "camera" if key[0] == "camera_menu" else "police" if key[0] == "accuse" else "objects"
                target = fixtures[fid]
                if key in options:
                    target["actions"].append([list(key), label])
                if fid == "camera" and "scene_body" not in known:
                    target["reason"] = "Il faut d'abord examiner la scène pour ouvrir le dossier vidéo de l'enquête."
        body_transferred = "exam_request" in known
        for fixture in fixtures.values():
            fixture["selectable"] = bool(fixture["actions"])
            if fixture["prop"] == "morgue":
                fixture["body_present"] = body_transferred
        if body_transferred:
            fixtures.pop("fixture:crime_scene", None)
        # Witnesses stay in the room after being questioned; don't disappear
        # when their once-only discovery is consumed or when AP are exhausted.
        for a in self.case.plan.actions:
            if a.place == s.place and (a.operation in (Operation.INTERVIEW, Operation.VERIFY, Operation.ASK_STOCK) or a.actor.startswith("staff:")) and a.actor not in self.case.plan.population and any(start <= s.at and (end is None or s.at <= end) for start, end in a.windows) and (a.operation is not Operation.VERIFY or set(a.requires) <= known.keys()):
                if a.actor not in staff:
                    staff[a.actor] = self.source_person(a.actor, a.operation)
        for actor, person in staff.items():
            rows = [a for a in self.case.plan.actions if a.place == s.place and a.actor == actor]
            if person["actions"]:
                continue
            if rows and all(a.id in s.state.completed for a in rows):
                person.update(status="Déposition déjà recueillie", idle_text="Je vous ai déjà raconté tout ce dont je me souviens.")
            elif not player.ap:
                person.update(status="Plus de PA · reprendre au prochain tour", idle_text="On reprendra notre échange un peu plus tard.")
            elif actor == "staff:medical":
                person.update(status="Examen en cours" if "exam_request" in known else "Examen non demandé", idle_text=self.service_status(actor))
            elif actor == "staff:lab":
                person.update(status="Analyse indisponible pour l'instant", idle_text="Je n'ai pas encore de résultat à vous remettre pour cette affaire.")
            else:
                person.update(status="Identité de la victime à établir" if "victim_reference" not in known else "Aucune question disponible pour l'instant",
                              idle_text="Sans voir de qui vous parlez, je ne peux pas vous répondre." if "victim_reference" not in known else "Je n'ai rien d'autre à vous dire pour le moment.")
        for actor, person in staff.items():
            person["actions"] = [[["service_menu", actor], "Parler"]]
        # Navigation counts are investigation subjects only. Service staff and
        # annex witnesses still have avatars/actions, but never pad the count.
        doors = []
        for home, region in self.homes.items():
            if region != s.place:
                continue
            people = present_by_place[home]
            answered = s.doorstep == home
            actions = [(k, options[k]) for k in (("ring", home), ("unlock_home", home), ("move", home)) if k in options]
            doors.append({"place": home, "label": labels[home], "door": True,
                          "id": people[0]["id"] if people else -1, "name": people[0]["name"] if people else None,
                          "look": people[0]["look"] if people else "", "occupied": bool(people), "answered": answered,
                          "people": people if answered else [], "unlocked": self.home_open(home),
                          "actions": [[list(k), label] for k, label in actions],
                          "reason": "Un habitant est chez lui : sonnez pour lui parler au seuil." if people else "Porte fermée · compétence Crochetage nécessaire." if not self.home_open(home) else "Pas assez de PA pour entrer."})
        notebook = []
        named = s.named_people()
        deductions = s.deductions()
        next_positions = {r.person: {"place": r.place_at(s.at + 15),
                          "activity": r.activity_at(s.at + 15)} for r in self.routines}
        for pid in sorted(self.case.plan.population):
            p = self.case.life.people[pid]
            profile = self.person(pid)
            identified = pid in named
            profile_known = "profile:" + pid in known
            notebook.append({"id": profile["id"], "name": p.name if identified else "?", "out": False,
                             "profile_known": profile_known,
                             "home": {"place": p.home, "region": self.homes[p.home], "label": labels[p.home], "region_label": labels[self.homes[p.home]]} if profile_known else None,
                             "traits": ({"Cheveux": profile["appearance"]["hair"], "Manteau": profile["appearance"]["coat"], "Taille": profile["appearance"]["height"]} | ({"Métier": p.occupation.label} if "police_record:" + pid in known or any(r["id"] == "context:" + pid + ":work" for r in s.journal) else {})) if profile_known else {},
                             "appearance": profile["appearance"] if profile_known else {},
                             "whereabouts": {"current": {"place": s.person_places[pid], "label": labels[s.person_places[pid]],
                                             "activity": next(r.activity_at(getattr(self, "position_at", s.at)) for r in self.routines if r.person == pid)},
                                             "next": {**next_positions[pid], "label": labels[next_positions[pid]["place"]]}} if identified else None,
                             "deductions": deductions[pid] if identified else [],
                             "life": None, "relationship": {"claim": self.case.life.answer(pid), "reported": None, "witnesses": [], "contradiction": False} if any(r["id"] == "context:" + pid + ":relation" for r in s.journal) else None,
                             "alibi": {"confirmed": "confirmé", "corroborated": "corroboré", "partial": "hors période", "on_site": "sur place", "reported": "à vérifier", "unknown": None}[s.alibi_state(pid)],
                             "corroboration": next((r["text"] for r in s.journal if r["id"] == "alibi:" + pid), None),
                             "claim": next((r["text"] for r in s.journal if r["id"] == "evening:" + pid), None), "with": [], "said": []})
        acquired_places = {key: s.discovery_places.get(a.id, a.place) for a in self.case.plan.actions if a.id in s.state.completed for key in a.reveals}
        kind_labels = {"person": "rencontre", "footage": "images", "diary": "agenda", "testimony": "témoignage",
                       "scene": "constat", "reference": "identification", "sample": "prélèvement", "request": "demande d'examen",
                       "medical": "rapport médical", "chronology": "chronologie", "laboratory": "analyse", "corroboration": "vérification",
                       "conversation": "conversation", "police_record": "casier et identité", "personal_account": "récit de soirée", "venue_register": "souvenirs du service", "correspondence": "correspondance", "relationship": "liens",
                       "container": "fouille", "objects": "objets", "inventory": "inventaire", "contact": "empreinte",
                       "laboratory_contact": "analyse d'objet", "scene_object": "objet au sol"}
        journal = [{"id": i + 1, "turn": self.note_turns[i], "kind": kind_labels.get(row["kind"], row["kind"]), "category": row["kind"],
                    "title": {"person": "Rencontre", "footage": "Caméra locale", "diary": "Agenda de la victime", "testimony": "Témoignage"}.get(row["kind"], kind_labels.get(row["kind"], "observation").capitalize()),
                    "text": row["text"], "source": labels.get(acquired_places.get(row["id"]), "Images · " + labels[row["id"].split(":")[1]] if row["id"].startswith(("camera:", "empty_window:")) else "Notes de terrain"),
                    "people": [], "leads": [q for q, label in s.locations.items() if label in row["text"]]}
                   for i, row in enumerate(s.journal) if row["kind"] != "recording_window"]
        leads = [{"id": "lead:" + str(i), "title": text.split(" — ")[0], "reason": text, "objective": "", "complete": False,
                  "destinations": [{"place": q, "label": labels[q]} for q, label in s.locations.items() if label in text]}
                 for i, text in enumerate(s.leads()) if not text.startswith("Aucune piste organisée")]
        leads.insert(0, {"id": "scene", "title": "Premier constat", "reason": "Le corps de " + victim.name + " a été retrouvé à " + labels[self.case.crime.scene] + ".", "objective": "", "complete": "scene_body" in known,
                            "destinations": [{"place": self.case.crime.scene, "label": labels[self.case.crime.scene]}]})
        if "scene_body" in known:
            # Field contacts, not a preview of their testimony or its relevance.
            for witness in self.case.witnesses.witnesses:
                if witness.role != "commuter":
                    continue
                completed = "interview:" + witness.id in s.state.completed
                leads.append({"id": "contact:" + witness.id, "title": "Entendre " + witness.name.lower(),
                    "reason": witness.name + " peut être rencontré à " + labels[witness.post] + ". Sa déposition "
                              + ("a été recueillie." if completed else "n'a pas encore été recueillie."),
                    "objective": "", "complete": completed,
                    "destinations": [{"place": witness.post, "label": labels[witness.post]}]})
        if "victim_diary" in known and self.case.claims["victim_diary"]["appointment"]:
            appointment = self.case.claims["victim_diary"]["appointment"]
            host = appointment["host"]
            answered = any(r["id"] == "context:" + host + ":appointment" for r in s.journal)
            leads.append({"id": "appointment", "title": "Le rendez-vous avec " + self.case.life.people[host].name,
                "reason": "L'agenda mentionne un rendez-vous à " + clock(appointment["time"]) + ", " + labels[appointment["place"]] + "."
                          + (" Sa réponse est consignée, à recouper avec les autres faits." if answered else "Ce rendez-vous n'a pas encore été abordé avec cette personne."),
                "objective": "", "complete": answered,
                "destinations": [{"place": appointment["place"], "label": labels[appointment["place"]]}]})
        for presence_row in self.case.evidence.presences:
            pid = presence_row.person
            if "evening:" + pid not in known:
                continue
            verification = next(a for a in self.case.plan.actions if a.id == "verify:" + pid)
            collected = "alibi:" + pid in known
            confirmed = s.alibi_state(pid) == "confirmed"
            partial = s.alibi_state(pid) == "partial"
            on_site = s.alibi_state(pid) == "on_site"
            name = self.case.life.people[pid].name
            keeper = self.source_person(verification.actor, verification.operation)
            account = self.case.claims["evening:" + pid]
            when = "entre " + spoken_time(account["start"]) + " et " + spoken_time(account["end"]) if "start" in account else "pendant une partie de la soirée"
            leads.append({"id": "evening:" + pid, "title": "Vérifier le récit de " + name,
                "reason": name + " dit avoir été " + at_label(labels[presence_row.place]) + ", " + when + "."
                    + (" Le témoignage couvre la période du crime : alibi confirmé." if confirmed else
                       " Récit vrai, mais le personnel ne couvre pas toute la période : cela n'écarte personne." if partial else
                       " Cette personne était dans la salle au moment de l'empoisonnement : une occasion, pas un alibi." if on_site else
                       " Récit corroboré. Il reste à comparer ses horaires au rapport médical" + (" et à l'analyse du verre." if self.case.crime.method is Method.POISONED else ".") if collected else
                       " " + keeper["name"] + " peut vérifier ce récit sur place."),
                "objective": "Témoignage recueilli" if collected else "Sur place · parler " + at_label(keeper["name"]) + " → Vérifier le récit de " + name,
                "complete": collected, "state": "confirmed" if confirmed else "partial" if partial else "on_site" if on_site else "corroborated" if collected else "open",
                "destinations": [] if collected else [{"place": verification.place, "label": labels[verification.place]}]})
        for thread in s.inquiry_threads():
            pid = thread["person"]
            if pid not in named:
                continue
            state = thread["state"]
            explanation = ("\n\n" + " ".join(r["text"] for r in thread["reasons"])) if state == "refuted" else (
                "\n\nLe témoignage est recueilli. Le moment du crime ou l'analyse du verre reste à recouper." if state == "awaiting_time" else
                "\n\nUn conflit ou une relation n'établit pas une culpabilité. Sa soirée reste une question ouverte.")
            leads.append({"id": "thread:" + pid, "title": "Le fil de " + self.case.life.people[pid].name,
                "reason": "\n".join(thread["details"]) + explanation,
                "objective": "", "complete": state == "refuted", "state": state,
                "destinations": [{"place": thread["destination"], "label": labels[thread["destination"]]}] if thread["destination"] else []})
        if "victim_diary" not in known:
            leads.append({"id": "victim_home", "title": "Les dernières heures de " + victim.name,
                          "reason": "Son logement est accessible à l'enquête. Ses affaires peuvent raconter ses projets pour ce soir-là.", "objective": "", "complete": False,
                          "destinations": [{"place": victim.home, "label": labels[victim.home]}]})
        timing = self.crime_timing()
        if "drink_sample" in known:
            result = "drink_result" in known
            analysis = next(a for a in self.case.plan.actions if a.id == "analyze_drink")
            ready = s.effective_plan.next_time(analysis, s.state, after=s.at)  # the session's plan, not the raw catalogue
            turns = math.ceil(max(0, ready - s.at) / 15) if ready is not None else 0
            leads.append({"id": "drink_analysis", "title": "Le verre retrouvé près du corps",
                "reason": next(r["text"] for r in s.journal if r["id"] == "drink_result") if result else
                          "Le verre a été prélevé sur la scène. Son contenu peut être analysé au laboratoire."
                          + (" Le résultat sera disponible dans %d tour%s au plus." % (turns, "s" if turns != 1 else "") if turns else " Le résultat est disponible."),
                "objective": "Résultat conservé dans les notes" if result else "Au laboratoire · parler à la technicienne → Que donne l'analyse du verre ?",
                "complete": result, "state": "confirmed" if result else "open",
                "destinations": [] if result else [{"place": "lab", "label": labels["lab"]}]})
        leads.insert(0, {"id": "medical", "title": "Dater le crime", "reason": timing["text"],
            "objective": timing["objective"], "complete": timing["state"] == "known",
            "state": "confirmed" if timing["state"] == "known" else "open",
            "destinations": [{"place": "morgue", "label": labels["morgue"]}]})
        facts = [r["text"] for r in s.journal if r["kind"] in ("medical", "laboratory", "chronology", "laboratory_contact")]
        progress = {"preuves": len(facts), "documents": sum(r["kind"] in ("correspondence", "diary", "relationship") for r in s.journal)}
        return {"engine": VERSION, "player": player.name, "active_player": player.name,
                "tick": self.tick, "ap": player.ap, "clock": clock(s.at), "place": s.place, "region": self.parents.get(s.place, s.place),
                "difficulty": self.difficulty, "deadline": clock(s.deadline) if s.deadline is not None else None, "time_left": s.time_left,
                "turns_left": s.turns_left, "turn_minutes": TURN_MINUTES, "mistakes": s.mistakes,
                "ended": self.ending_view(),
                "items": sorted(player.items), "winner": self.winner.name if self.winner else None,
                "grid": GRID, "adjacency": adjacency, "places": places, "outdoors": s.place in self.outdoors,
                "scene_has_blood": any(t.kind.value == "victim_blood" for t in self.case.crime.traces),
                "crime_site": {"place": self.case.crime.scene, "region": self.parents.get(self.case.crime.scene, self.case.crime.scene), "district": labels[self.case.crime.scene], "outdoors": self.case.crime.scene in self.outdoors},
                "body_location": "morgue" if body_transferred else self.case.crime.scene,
                "crime_timing": timing, "timeline": s.timeline(), "threads": guide(s),
                "glance": {q: [[r["id"] for place, rows in present_by_place.items() if self.homes.get(place, place) == q for r in rows], []] for q in self.roots},
                "presence": presence, "present": present_by_place[s.place], "staff": list(staff.values()), "fixtures": list(fixtures.values()), "doors": doors,
                "doorstep": s.doorstep, "doorstep_label": "Devant chez " + labels[s.doorstep][5:] if s.doorstep and labels[s.doorstep].startswith("Chez ") else "Devant " + labels[s.doorstep] if s.doorstep else None,
                "options": [[list(key), label] for key, label in options.items()],
                "dialogue_options": dialogue_options,
                "routes": {q: {"cost": self.cost(q), "available": ("move" if q in self.parents else "walk", q) in options,
                               "reason": "too_far" if self.cost(q) > player.ap else "", "key": ["move" if q in self.parents else "walk", q]} for q in places},
                "pending": ("terminal vidéo" if self.speaker == "camera" else self.case.life.people[self.speaker].name if self.speaker in self.case.plan.population else self.source_person(self.speaker, Operation.INTERVIEW)["name"]) if self.speaker else None,
                "conversation": self.cue, "notebook": notebook, "contacts": self.notebook_contacts(labels), "journal": journal, "leads": leads,
                "story": {"window": next((r["text"] for r in s.journal if r["id"] == "medical_window"), None), "object": "objets examinés : " + str(len(s.found)) if s.found else None,
                          "object_status": "found" if s.carried else "not_reported"},
                "facts": facts, "trusted": [], "progress": progress,
                "scoreboard": [{"name": player.name, **progress}], "arrival_scene": None, "can_try_code": False,
                "detectives": [{"name": player.name, "place": s.place, "you": True}],
                "briefing": {"victim": victim.name, "scene": labels[self.case.crime.scene]}}
