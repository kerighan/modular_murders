"""Small offline, causal case generator. World truth is not player knowledge.

Separate RNG: adding the story never changes the original suspect/evidence draws.
Objects and motives point at several people; only crossed sources unlock a
reconstruction. Rumours never enter the engine's certified trait deductions.
"""
import random

from genotype import LinkToVictim
from city import TRAIT_TEXT
from scenario_graph import Observation, ScenarioGraph


LIVES = [
    ("ouvrir un atelier", "un prêt à rembourser", "des relances de créancier"),
    ("obtenir une promotion", "une évaluation professionnelle désastreuse", "un avertissement au travail"),
    ("quitter le quartier", "un départ que personne ne doit encore connaître", "un billet de train réservé"),
    ("protéger un proche", "un service rendu dont je ne suis pas fier", "une lettre demandant de garder un paquet"),
    ("récupérer de l'argent prêté", "des économies qui fondent", "une reconnaissance de dette"),
    ("recommencer ma vie", "une séparation difficile", "un bail pour un autre appartement"),
]

FAMILIES = {
    "theft": {
        "object": "le bracelet serti de la victime", "relay": "den",
        "effect": "Une photo montre un bracelet serti, gravé J-17. La victime l'avait mis à l'abri dans un coffre ; il a disparu.",
        "goal": "rembourser une dette", "pressure": "un créancier qui réclame son argent demain",
        "motive": "Vol pour rembourser une dette urgente",
        "document": "Une mise en demeure exige un remboursement dès demain.",
        "ending": "J'ai pris le bracelet pour régler ma dette. La victime a découvert le vol et m'a demandé de le rendre. Notre dispute dehors a dégénéré.",
    },
    "blackmail": {
        "object": "la clé USB de la victime", "relay": "bar",
        "effect": "La victime conservait une copie du dossier sur une clé USB étiquetée D-08. Elle l'avait mise à l'abri dans un coffre ; la clé a disparu.",
        "goal": "empêcher la divulgation d'un dossier", "pressure": "des documents qui pourraient ruiner ma vie",
        "motive": "Faire taire la victime avant la divulgation d'un dossier",
        "document": "Un courrier annonce que la victime remettra son dossier à un avocat demain.",
        "ending": "J'ai pris la clé USB pour empêcher la divulgation du dossier. Mais la victime comptait quand même parler à son avocat. Je l'ai retrouvée dehors et je l'ai tuée pour la faire taire.",
    },
    "revenge": {
        "object": None, "relay": "cabaret",
        "effect": "Ses notes ne signalent aucun objet disparu. Elles parlent d'une réunion de quartier et d'une demande d'excuses.",
        "goal": "obtenir réparation d'un conflit", "pressure": "une humiliation que je n'arrive pas à oublier",
        "motive": "Vengeance après un conflit personnel",
        "document": "Une lettre de rendez-vous réclame des excuses pour une humiliation publique.",
        "ending": "Je voulais des excuses. Je savais où la retrouver après la réunion. Elle s'est moquée de moi une dernière fois ; je l'ai tuée pendant notre dispute dehors.",
    },
}


def hour(minutes):
    return f"{minutes // 60:02d} h {minutes % 60:02d}"


class CaseStory:
    def __init__(self, game):
        rng = random.Random(f"nexus-story-v1:{game.seed}")
        self.game = game
        link = game.case[0][LinkToVictim]
        families = ["theft", "blackmail", "revenge"]
        weights = [3, (3 if link == LinkToVictim.COLLEAGUE else 1) if link != LinkToVictim.UNKNOWN else 0,
                   (3 if link in (LinkToVictim.EX, LinkToVictim.SIBLING) else 1) if link != LinkToVictim.UNKNOWN else 0]
        self.family = rng.choices(families, weights)[0]
        self.spec = FAMILIES[self.family]
        innocents = rng.sample(list(range(1, game.n)), game.n - 1)
        # These are mathematical overlaps, not mandatory narrative actors.
        overlap, self.rival = innocents[:2]
        # Four-person core: pairs of axes remain ambiguous, all three converge.
        # Additional residents share zero, one or two axes, never all three.
        if game.n >= 4:
            third = innocents[2]
            pressure = {0, self.rival, third}
            custody = {0, overlap, third}
            appearance = {0, self.rival, overlap}
            for sid in innocents[3:]:
                for axis in rng.sample([pressure, custody, appearance], rng.randint(0, 2)):
                    axis.add(sid)
        else:
            pressure, custody, appearance = {0, self.rival}, {0, overlap}, set(range(game.n))
        self.pressure_people = frozenset(pressure)
        self.object_people = frozenset(custody)
        self.appearance_people = frozenset(appearance)
        self.access = [sid for sid in game.order if sid in custody]
        fate_rng = random.Random(f"nexus-object-v2:{game.seed}")
        self.object_fate = fate_rng.choice(["missing", "hidden"]) if self.spec["object"] else "none"
        self.cache_place = fate_rng.choice([place for place in ("alley", "bar", "cabaret", "den")
                                           if place != self.spec["relay"]]) if self.object_fate == "hidden" else None
        self.access_key = "meeting" if self.object_fate == "none" else "access"
        population = frozenset(range(game.n))
        optional = ([Observation("loss", "object", population)] if self.spec["object"] else [])
        if self.cache_place:
            optional.append(Observation("cache", "object", population))
        self.graph = ScenarioGraph(range(game.n), [
            Observation(self.access_key, "opportunity", self.object_people),
            Observation("trace", "motive", self.pressure_people),
            Observation("camera", "chronology", self.appearance_people),
            Observation("clock", "chronology", frozenset(range(game.n))),
        ] + optional, routes=([("loss", "access")] if self.spec["object"] else []) +
            [(self.access_key, "trace"), ("trace", "camera"), ("clock", "camera")])
        self.graph.validate_solution(0)
        if self.graph.minimum_depth() < (3 if game.n >= 4 else 2):
            raise ValueError("An investigation shortcut escaped generation")
        self.appearance = rng.choice(["une veste de pluie à bandes réfléchissantes", "un sac de coursier à rabat orange",
                                      "des bottes de travail à semelles claires", "un manteau à capuche doublée de violet"])
        self.time = 21 * 60 + rng.randrange(0, 18) * 5
        self.window = f"entre {hour(self.time)} et {hour(self.time + 10)}"
        self.profiles = {}
        self.relations = {}
        for sid in range(game.n):
            goal, pressure, secret = rng.choice(LIVES)
            self.profiles[sid] = {"goal": goal, "pressure": pressure, "secret": secret}
            targets = [i for i in range(game.n) if i != sid]
            target = rng.choice(targets)
            relation = rng.choice(["se méfie de", "envie", "protège", "en veut à"])
            reason = rng.choice(["une dette jamais remboursée", "une place convoitée au travail",
                                 "un service qui a mal tourné", "une dispute entendue dans l'escalier"])
            self.relations[sid] = {"target": target, "relation": relation, "reason": reason}
        # Shared pressures are deliberate. The real motive is not a unique trait.
        for sid in self.pressure_people:
            self.profiles[sid].update(goal=self.spec["goal"], pressure=self.spec["pressure"],
                                      secret=self.spec["document"])
        self.check_place = game.night[self.rival] if game.night[self.rival] != "home" else "police"
        self.sources = self._sources()
        # Private, coherent relationship knowledge. Witnesses know their neighbours
        # and people in their social circle, not every resident of the city.
        # A sole liar would be singleton evidence. Truth or partial knowledge,
        # never an innocent fabricated account or a guaranteed culprit denial.
        self.link_deniers = set()
        self.link_contacts = {}
        for sid in range(game.n):
            street = game.map[f"house_{sid}"][1][0]
            self.link_contacts[sid] = {target for target in range(game.n) if target != sid
                                       and (game.map[f"house_{target}"][1][0] == street
                                            or target == self.relations[sid]["target"])}
        # At least two independent witnesses can expose each hidden relationship.
        for target in sorted(self.link_deniers):
            witnesses = [sid for sid in range(game.n) if sid != target]
            for sid in rng.sample(witnesses, min(2, len(witnesses))):
                self.link_contacts[sid].add(target)
        self.colleagues = frozenset(s for s in range(game.n) if game.case[s][LinkToVictim] == LinkToVictim.COLLEAGUE)
        self.workplace, self.profession = rng.choice([("hospital", "soignante"), ("bar", "employée du Néon Bleu"),
                                                    ("cabaret", "technicienne du Palace"), ("cctv", "technicienne vidéo")])
        self.work_conflict = self.colleagues if len(self.colleagues) >= 2 and rng.random() < .65 else frozenset()
        self.knowledge = {}
        for sid in range(game.n):
            if game.case[sid][LinkToVictim] == LinkToVictim.UNKNOWN:
                self.knowledge[sid] = None
            elif self.work_conflict and rng.random() < .35:
                self.knowledge[sid] = "work"
            else:
                self.knowledge[sid] = "pressure" if rng.random() < .30 else None
        if self.work_conflict:
            self.sources["work"] = {"place": self.workplace, "title": "Le conflit au travail",
                "text": f"La victime travaillait ici comme {self.profession}. Le planning et une note de réunion décrivent un différend avec "
                        f"{self._names(self.work_conflict)}. Rien ici ne les situe à l'heure du crime. "
                        "Leur demander leur version, puis vérifier leurs horaires plutôt que transformer ce conflit en verdict.",
                "people": sorted(self.work_conflict), "leads": [f"house_{s}" for s in game.order if s in self.work_conflict]}

    def _names(self, people):
        return ", ".join(self.game.name(s) for s in self.game.order if s in people)

    def observed(self, p):
        return {"trace" if k.startswith("trace_") else k for k in p.story_found}

    def _sources(self):
        g, spec = self.game, self.spec
        rival = g.name(self.rival)
        names = self._names(self.object_people)
        item = spec["object"]
        docs = {
            "clock": {"place": "crime_scene", "title": "La fenêtre du crime",
                      "text": f"Le constat situe le meurtre {self.window}. Les déplacements et les horaires peuvent départager les récits.",
                      "people": [], "leads": []},
            "trace": {"place": "house_0", "title": "Une trace à replacer dans le temps",
                      "text": f"{spec['document']} La correspondance décrit une même pression concernant {self._names(self.pressure_people)}. "
                              "Ces papiers établissent un mobile possible pour plusieurs personnes, pas une présence sur la scène. "
                              "Une caméra donne sur le lieu du crime : comparer les images avec l'heure du constat.",
                      "people": sorted(self.pressure_people), "leads": ["crime_scene", "cctv"], "target": 0},
            "rival": {"place": f"house_{self.rival}", "title": "Un conflit réel, une autre chronologie",
                      "text": f"{spec['document']} {rival} partage cette pression avec {self._names(self.pressure_people - {self.rival})}. "
                              f"Une attestation prétend couvrir toute la fenêtre du crime. Lieu indiqué : {'son domicile' if g.night[self.rival] == 'home' else g.label(g.night[self.rival])}. "
                              f"Vérifier cette pièce auprès de {g.label(self.check_place)} avant de conclure.",
                      "people": [self.rival], "leads": [self.check_place], "target": self.rival},
        }
        if item:
            docs["loss"] = {"place": "victim_house", "title": "Un objet manque",
                "text": f"{spec['effect']} Ses notes situent ce coffre à {g.label(spec['relay'])}. "
                        "Il sert à plusieurs usagers du lieu, qui ne se connaissent pas forcément. "
                        "Qui pouvait l'ouvrir ? Aller consulter sur place le registre des clés.",
                "people": [], "leads": [spec["relay"]]}
            docs["access"] = {"place": spec["relay"], "title": "Qui pouvait ouvrir le coffre ?",
                "text": f"Le registre signale la disparition de {item}, que la victime avait rangé dans ce coffre. "
                        "Le coffre a été ouvert sans être forcé. "
                        f"Le registre indique que plusieurs usagers détenaient un double de sa clé : {names}. "
                        "Personne n'a vu qui a ouvert le coffre. Détenir une clé ne prouve pas qu'on a volé l'objet, "
                        "encore moins qu'on a tué sa propriétaire. Chercher un mobile, puis vérifier les images du crime.",
                "people": self.access, "leads": [f"house_{s}" for s in self.access]}
            if self.cache_place:
                docs["cache"] = {"place": self.cache_place, "title": "L'objet retrouvé dans une cache",
                    "text": f"Derrière une grille descellée, vous retrouvez {item}. "
                            "Son marquage correspond à celui décrit dans les affaires de la victime. "
                            "Aucun nom, aucune trace exploitable : impossible de savoir qui l'a caché ici. "
                            "La découverte ne désigne personne et n'innocente aucun des suspects.",
                    "people": [], "leads": []}
        else:
            docs["meeting"] = {"place": "victim_house", "title": "Qui connaissait le rendez-vous ?",
                "text": f"{spec['effect']} Une invitation privée indique où retrouver la victime après cette réunion. "
                        f"Des copies ont été envoyées à {names}. Recevoir une invitation n'implique pas de connaître personnellement son organisatrice. "
                        "Plusieurs personnes connaissaient donc ce rendez-vous ; rien ne dit qu'elles s'y sont rendues. "
                        "Chercher le conflit derrière cette rencontre, puis vérifier les images du crime.",
                "people": self.access, "leads": [f"house_{s}" for s in self.access]}
        for sid in self.pressure_people - {0}:
            docs[f"trace_{sid}"] = {**docs["trace"], "place": f"house_{sid}", "target": sid}
        for sid, profile in self.profiles.items():
            if sid in (0, self.rival):
                continue
            docs[f"life_{sid}"] = {
                "place": f"house_{sid}", "title": "Une vie derrière la porte",
                "text": f"Des papiers de {g.name(sid)} évoquent {profile['secret']}. Son projet : {profile['goal']}. "
                        "Ces documents racontent sa vie ; aucun lien avec le meurtre n'est établi. "
                        "Pour avancer, chercher un indice de la scène ou suivre une piste du carnet plutôt qu'un nom au hasard.",
                "people": [sid], "leads": [], "target": sid,
            }
        return docs

    def available_sources(self, p):
        return [key for key, doc in self.sources.items()
                if doc["place"] == p.place and key not in p.story_found]

    def investigate(self, p):
        g = self.game
        keys = self.available_sources(p)
        p.story_examined.add(p.place)
        if not keys:
            return ["Aucun nouveau document à relever ici. Les fouilles d'indices restent distinctes."]
        events = []
        for key in keys:
            doc = self.sources[key]
            if key == "cache" and not p.story_found & {"loss", "access"}:
                # An early discovery does not identify the owner or reveal a
                # storage location from papers the detective has not yet read.
                item = self.spec["object"].removesuffix(" de la victime")
                doc = {**doc, "title": "Un objet caché, à identifier",
                       "text": f"Derrière une grille descellée, vous trouvez {item}. Vous notez son marquage. "
                               "Aucun nom n'indique qui l'a caché là, ni à qui il appartient. "
                               "Comparer ce marquage avec les papiers du domicile de la victime avant de faire un rapprochement.",
                       "leads": ["victim_house"]}
            p.story_found.add(key)
            for sid in doc["people"]:
                g.reveal(p, sid, [], name=True)
            if key in ("trace", "rival") or key.startswith("life_"):
                p.story_profiles.add(doc["target"])
            if key.startswith("trace"):
                p.story_profiles.update(self.pressure_people)
            g.record_note(p, "document", doc["title"], doc["text"], g.place_label(p, p.place),
                          people=doc["people"], leads=doc["leads"])
            events += [f"{doc['title']}\n\n{doc['text']}"]
        return events

    def life(self, p, sid):
        profile = self.profiles[sid]
        p.story_profiles.add(sid)
        return f"Je voudrais {profile['goal']}. En ce moment, j'ai surtout {profile['pressure']} sur le dos.", []

    def rumours(self, p, sid):
        g, knowledge = self.game, self.knowledge[sid]
        if not self._knows_victim(p, sid):
            return "Je ne connaissais pas la victime. Je ne peux pas vous renseigner sur sa vie ou ses conflits.", []
        if knowledge == "work":
            text = ("Elle m'avait parlé de tensions au travail, avec plusieurs personnes. Je ne sais pas lesquelles. "
                    f"Cherchez ses collègues à {g.label(self.workplace)} ; ils pourront expliquer ce qui se passait.")
            p.story_rumours[sid] = {"kind": "work", "people": []}
            g.record_note(p, "piste", "Un conflit au travail ?", text, g.name(sid), leads=[self.workplace])
            return text, ["Piste ouverte : trouver des collègues. Témoignage à recouper."]
        if knowledge == "pressure":
            people = sorted(self.pressure_people)
            for target in people:
                g.reveal(p, target, [], name=True)
            text = (f"J'ai entendu plusieurs personnes parler de ce problème : {self._names(people)}. "
                    "Leur pression était réelle. Mais je n'ai vu personne commettre le crime ; leurs horaires restent à vérifier.")
            p.story_rumours[sid] = {"kind": "pressure", "people": people}
            g.record_note(p, "piste", "Une pression partagée", text, g.name(sid), people=people,
                          leads=[f"house_{s}" for s in g.order if s in people])
            return text, ["Un mobile possible pour plusieurs personnes ; non prouvé."]
        return "Je préfère que chacun vous explique sa propre histoire. Je ne vais pas désigner quelqu'un au hasard.", []

    def _knows_victim(self, p, sid):
        return (self.game.case[sid][LinkToVictim] != LinkToVictim.UNKNOWN
                and p.link_claims.get(sid) != LinkToVictim.UNKNOWN)

    def context_options(self, p, sid):
        if not p.knows(sid):
            return {}
        g, result = self.game, {}
        for key in sorted(p.story_found):
            if key not in self.sources:
                continue
            doc = self.sources[key]
            relevant = doc.get("target") == sid or ((key.startswith("trace") or key == self.access_key) and sid in doc["people"])
            if relevant and (sid, key, self.context_stamp(p, key)) not in p.story_discussed:
                result[("confront", sid, key)] = f"Présenter à {g.name(sid)} : {doc['title']} (1 PA)"
        certain, _ = g.deduce(p)
        for target in g.order:
            if sid not in p.shunned and target != sid and p.knows(target) and (sid, target) not in p.people_discussed:
                result[("talk_about", sid, target)] = f"Demander à {g.name(sid)} : que savez-vous de {g.name(target)} ? (1 PA)"
        if p.link_claims.get(sid) == LinkToVictim.UNKNOWN and p.link_witnesses.get(sid):
            stamp = len(p.link_witnesses[sid])
            if (sid, "relationship", stamp) not in p.story_discussed:
                result[("confront", sid, "relationship")] = f"Confronter {g.name(sid)} aux témoignages sur son lien avec la victime (1 PA)"
        if p.heard.get(sid, set()) and any(type(heard) is type(fact) and heard != fact
                                         for heard in p.heard[sid] for fact in certain):
            if (sid, "statement", 0) not in p.story_discussed:
                result[("confront", sid, "statement")] = f"Confronter {g.name(sid)} à sa description contradictoire (1 PA)"
        return result

    def context_stamp(self, p, key):
        if key == "relationship":
            return 0  # handled with the person ID in confront
        if key != "trace" and not key.startswith("trace_"):
            return 0
        return sum(1 << i for i, fact in enumerate((self.access_key, "clock", "trace", "camera")) if fact in self.observed(p))

    def talk_about(self, p, sid, target):
        g = self.game
        p.people_discussed.add((sid, target))
        link = g.case[target][LinkToVictim]
        leads = []
        if not self._knows_victim(p, sid) or target not in self.link_contacts[sid] or link == LinkToVictim.UNKNOWN:
            text = f"Je connais {g.name(target)} de vue, mais je ne sais rien de ses rapports avec la victime. Ça ne veut pas dire qu'il n'y en avait pas."
        else:
            street = g.map[f"house_{sid}"][1][0]
            neighbour = g.map[f"house_{target}"][1][0] == street
            basis = "On habite le même quartier ; je les ai vus se fréquenter" if neighbour else "Je les connais de notre entourage ; ils en ont parlé devant moi"
            descriptions = {
                LinkToVictim.EX: "une ancienne relation amoureuse avec la victime",
                LinkToVictim.SIBLING: "un lien de famille avec la victime",
                LinkToVictim.COLLEAGUE: "une relation de travail avec la victime",
                LinkToVictim.NEIGHBORHOOD: "des rapports de voisinage avec la victime",
            }
            text = f"{g.name(target)} avait {descriptions[link]}. {basis}. Je peux parler de leur relation, pas de ce qui s'est passé la nuit du crime."
            p.link_witnesses.setdefault(target, set()).add(sid)
            leads = [f"house_{target}"]
            if p.link_claims.get(target) == LinkToVictim.UNKNOWN:
                text += " Ce récit contredit sa déclaration ; il faudra lui demander pourquoi."
        title = f"À propos de {g.name(target)}"
        g.record_note(p, "témoignage", title, text, g.name(sid), people=[sid, target], leads=leads)
        g.dialogue_cue(p, sid, text, "reply", question=f"Que savez-vous de {g.name(target)} ?", notes=["Témoignage conservé ; pas une preuve de meurtre."])
        return [f"{g.name(sid)} — {text}"]

    def check_options(self, p):
        g, options = self.game, {}
        if "rival" in p.story_found and p.place == self.check_place and self.rival not in p.timeline_verified:
            options[("check_timeline", self.rival)] = f"Vérifier les horaires de {g.name(self.rival)} (1 PA)"
        if "trace" in self.observed(p) and "clock" in p.story_found and p.place == "cctv" and "camera" not in p.story_found:
            if p.authorized or "hacking_kit" in p.items:
                options[("check_timeline", 0)] = "Examiner la silhouette dans la fenêtre du crime (1 PA)"
        return options

    def check_timeline(self, p, sid):
        g = self.game
        p.timeline_verified.add(sid)
        if sid == self.rival:
            p.cleared.add(sid)
            text = (f"Le registre original et son témoin confirment la présence de {g.name(sid)} "
                    f"{self.window}, loin de la scène. Son conflit était réel, mais cette piste ne tient pas pour ce crime.")
            leads = []
        else:
            p.story_found.add("camera")
            text = (f"À {hour(self.time + 5)}, une silhouette quitte la scène avec {self.appearance}. Le visage est invisible. "
                    f"Le registre d'équipement et les portraits montrent que {self._names(self.appearance_people)} possèdent cet accessoire. "
                    "Aucun n'est identifié par la vidéo seule. Croiser ce groupe avec le mobile et le parcours de l'objet.")
            for target in self.appearance_people:
                g.reveal(p, target, [], name=True)
            leads = [f"house_{s}" for s in g.order if s in self.appearance_people]
        people = [sid] if sid == self.rival else sorted(self.appearance_people)
        g.record_note(p, "vérification", "Un horaire recoupé", text, g.label(p.place), people=people, leads=leads)
        return [f"Vérification : {text}"]

    def confront(self, p, sid, key):
        g = self.game
        p.story_discussed.add((sid, key, len(p.link_witnesses.get(sid, ())) if key == "relationship" else self.context_stamp(p, key)))
        if key == "access":
            text = "Oui, j'avais une clé de ce coffre partagé. Ça ne signifie pas que je connaissais les autres usagers ou leurs affaires. "
            text += "Vous pouvez venir chez moi consulter mes papiers, plutôt que supposer que j'ai volé quelque chose."
            p.invited.add(sid)
            leads = [f"house_{sid}"]
        elif key == "meeting":
            text = "J'ai reçu cette invitation. Ça ne dit pas où j'étais ensuite. Vous pouvez consulter mes papiers chez moi pour vérifier."
            p.invited.add(sid)
            leads = [f"house_{sid}"]
        elif key == "rival":
            text = "Oui, ce conflit existait. Mais mon attestation couvre l'heure du meurtre. Vérifiez-la là où elle a été établie."
            leads = []
        elif key == "statement":
            text = "D'accord, ma description était inventée. Je voulais détourner vos questions. Ça ne répond pas encore à votre question sur le meurtre."
            leads = [f"house_{sid}"]
        elif key == "relationship":
            link = g.case[sid][LinkToVictim]
            text = (f"D'accord, j'ai caché ce lien : {TRAIT_TEXT[link]}. Je ne voulais pas que notre histoire personnelle devienne publique. "
                    "Mais cacher une relation ne dit pas où j'étais à l'heure du meurtre. Vérifiez les faits.")
            p.link_claims[sid] = link
            g.reveal(p, sid, [LinkToVictim])
            leads = [f"house_{sid}", "crime_scene"]
        elif sid == 0 and (key == "trace" or key.startswith("trace_")):
            required = {self.access_key, "clock", "trace", "camera"}
            if required <= self.observed(p) and self.graph.remaining(self.observed(p)) == {sid}:
                p.story_resolved = True
                text = self.spec["ending"] + f" C'était {self.window}. " + self.object_ending(confession=True)
                leads = ["police"] + ([self.cache_place] if self.cache_place and "cache" not in p.story_found else [])
                g.record_note(p, "reconstitution", "Les pièces convergent", text, g.name(sid), people=[sid], leads=leads)
            else:
                text = "Ce conflit concerne plusieurs personnes. Il faut encore recouper qui en avait l'occasion et ce que montrent les images ; le mobile seul ne prouve pas le meurtre."
                missing = required - self.observed(p)
                leads = list(dict.fromkeys("cctv" if k == "camera" else self.sources[k]["place"] for k in sorted(missing)
                                           if k == "camera" or not self.sources[k]["place"].startswith("house_")
                                           or p.knows(g.owner(self.sources[k]["place"]))))
        else:
            profile = self.profiles[sid]
            text = f"Ces papiers sont personnels. Je cherche à {profile['goal']}. Ce n'est pas une raison pour me traiter en meurtrier."
            leads = []
        g.record_note(p, "déclaration", "Réponse à une preuve", text, g.name(sid), people=[sid], leads=leads)
        g.dialogue_cue(p, sid, text, "reply", question="Que répondez-vous à ce document ?", notes=["Déclaration conservée dans les Notes."])
        return [f"{g.name(sid)} — {text}"]

    def view(self, p):
        g = self.game
        leads = []
        for note in p.journal:
            for place in note.get("leads", []):
                if place not in leads:
                    leads.append(place)
        found = self.observed(p)
        identified = bool(found & {"loss", "access"}) or p.story_resolved
        status = ("not_reported" if "meeting" in found else
                  "found" if "cache" in found and identified else
                  "unidentified" if "cache" in found else
                  "unrecovered" if p.story_resolved and self.object_fate == "missing" else
                  "missing" if found & {"loss", "access"} else "unknown")
        return {"window": self.window if "clock" in p.story_found else None,
                "object": self.spec["object"] if identified else
                          self.spec["object"].removesuffix(" de la victime") if "cache" in found else None,
                "object_status": status,
                "resolved": p.story_resolved,
                "motive": self.spec["motive"] if p.story_resolved else None,
                "leads": [{"place": place, "label": g.place_label(p, place)} for place in leads]}

    def leads_view(self, p):
        """Optional investigation paths, projected from discovered sources only.

        Nothing here changes candidates, travels, spends AP or exposes unseen
        identities. A source is evidence; a destination is a suggested action.
        """
        g, found = self.game, self.observed(p)
        result = []

        def add(key, title, reason, objective, places, complete=False):
            result.append({"id": key, "title": title, "reason": reason, "objective": objective,
                           "complete": complete, "destinations": [
                {"place": place, "label": g.place_label(p, place)} for place in dict.fromkeys(places)
                if place in g.map and (not place.startswith("house_") or p.knows(g.owner(place)))]})

        if found & {"loss", "access", "cache"}:
            unidentified = "cache" in found and not found & {"loss", "access"}
            object_destinations = (["victim_house"] if unidentified else
                                   [self.spec["relay"]] if "access" not in found else
                                   [self.cache_place] if p.story_resolved and self.cache_place and "cache" not in found else [])
            add("object", "Identifier l'objet caché" if unidentified else "Suivre l'objet disparu",
                "Un objet marqué a été retrouvé, mais son propriétaire n'est pas encore établi." if unidentified else self.spec["effect"],
                "Comparer le marquage avec les papiers chez la victime." if unidentified else
                "Consulter le registre des clés là où l'objet était rangé." if "access" not in found
                else "L'objet a été retrouvé, mais personne n'est identifié par cette cache. Recouper les clés, le mobile et les images." if "cache" in found
                else "Plusieurs personnes avaient une clé. Recouper leurs mobiles et les images ; retrouver l'objet n'est pas indispensable.",
                object_destinations, "access" in found)
        if self.access_key in found or "trace" in found or any(r.get("kind") == "pressure" for r in p.story_rumours.values()):
            people = self.object_people if self.access_key in found else self.pressure_people
            add("motive", "Comprendre la pression", "Avoir l'occasion ne signifie pas avoir commis le crime.",
                "Consulter les correspondances : quel problème liait plusieurs personnes à la victime ?" if "trace" not in found
                else "Le mobile est partagé : il faut encore le recouper avec la chronologie.",
                [f"house_{s}" for s in g.order if s in people], "trace" in found)
        if "clock" in found or "trace" in found:
            add("time", "Replacer une silhouette dans la nuit", "Une fenêtre horaire n'identifie pas une personne.",
                "Relever le constat extérieur avant de consulter la caméra à la Régie vidéo." if "camera" not in found
                else "Le visage reste masqué. Plusieurs personnes possèdent l'accessoire visible ; comparer les autres sources.",
                (["crime_scene"] if "clock" not in found else []) + ["cctv"], "camera" in found)
        if self.work_conflict and ("work" in found or any(r.get("kind") == "work" for r in p.story_rumours.values())):
            add("work", "Des tensions au travail", "Un proche évoque un conflit sans connaître les noms.",
                "Trouver le planning et des collègues au lieu de travail." if "work" not in found
                else "Plusieurs collègues partageaient le conflit. Leur demander leurs versions et vérifier les horaires.",
                [self.workplace] if "work" not in found else [f"house_{s}" for s in g.order if s in self.work_conflict], "work" in found)
        if "rival" in found:
            add("alibi", "Vérifier plutôt que croire", "Une attestation peut disculper une personne, mais elle doit être recoupée.",
                "Consulter le registre original et son témoin." if self.rival not in p.timeline_verified
                else "Horaire confirmé loin de la scène. Ce conflit ne suffisait pas à accuser.",
                [self.check_place], self.rival in p.timeline_verified)
        return result

    def profile_view(self, p, sid):
        if not p.knows(sid) or sid not in p.story_profiles:
            return None
        profile = self.profiles[sid]
        return {"goal": profile["goal"], "pressure": profile["pressure"]}

    def link_view(self, p, sid):
        if not p.knows(sid):
            return None
        witnesses = p.link_witnesses.get(sid, set())
        claim = p.link_claims.get(sid)
        if claim is None and not witnesses:
            return None
        return {"claim": TRAIT_TEXT[claim] if claim is not None else None,
                "witnesses": [self.game.name(w) for w in self.game.order if w in witnesses],
                "reported": TRAIT_TEXT[self.game.case[sid][LinkToVictim]] if witnesses else None,
                "contradiction": claim == LinkToVictim.UNKNOWN and bool(witnesses)}

    def reconstruction(self, p):
        if not p.story_resolved:
            return "Le responsable est identifié. Son mobile et les circonstances du crime restent à reconstituer."
        return (f"Reconstitution : meurtre {self.window}. {self.spec['motive']}. "
                f"{self.object_ending()} Les clés ou invitations, le conflit et les images convergent. "
                "Aucune de ces pistes ne suffisait à désigner quelqu'un seule.")

    def object_ending(self, confession=False):
        """World truth, released only by a completed reconstruction/confession."""
        if self.object_fate == "none":
            return ("Je n'ai rien pris. C'était notre conflit qui m'obsédait." if confession else
                    "Le crime vient d'un conflit personnel, pas d'un vol.")
        if self.object_fate == "hidden":
            where = {"alley": "dans la ruelle", "bar": "au Néon Bleu", "cabaret": "au Palace", "den": "au Tripot"}[self.cache_place]
            return ((f"J'ai caché {self.spec['object']}" if confession else f"Le responsable a caché {self.spec['object']}")
                    + f" derrière une grille {where}.")
        if self.family == "blackmail":
            return ("J'ai détruit" if confession else "Le responsable a détruit") + " la clé USB pour faire disparaître cette copie du dossier."
        return (("J'ai emporté" if confession else "Le responsable a emporté")
                + " le bracelet hors du quartier. Il ne peut pas être retrouvé dans ces lieux.")
