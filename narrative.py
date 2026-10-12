"""Small offline, causal case generator. World truth is not player knowledge.

Separate RNG: adding the story never changes the original suspect/evidence draws.
Objects and motives point at several people; only crossed sources unlock a
reconstruction. Rumours never enter the engine's certified trait deductions.
"""
import random

from genotype import Gender, LinkToVictim
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
                        f"{self._names(self.work_conflict)}. Le planning ne couvre pas la soirée du meurtre.",
                "people": sorted(self.work_conflict), "leads": [f"house_{s}" for s in game.order if s in self.work_conflict]}

    def _names(self, people):
        return ", ".join(self.game.name(s) for s in self.game.order if s in people)

    def observed(self, p):
        return {"trace" if k.startswith("trace_") else k for k in p.story_found}

    def scenes_at(self, place, people):
        """Provider hook: world-authored exchanges, with no player/UI state.

        Ids are stable per pair/topic, independent of place and arrival count.
        These remarks reveal a social connection, not a certified murder fact.
        Only actual connections generate exchanges; never arbitrary accusations.
        """
        if place not in ("bar", "cabaret", "den", "hospital", "restaurant"):
            return []
        g, scenes = self.game, []
        for position, a in enumerate(people):
            for b in people[position + 1:]:
                relation = self.relations[a] if self.relations[a]["target"] == b else self.relations[b] if self.relations[b]["target"] == a else None
                colleagues = g.case[a][LinkToVictim] == g.case[b][LinkToVictim] == LinkToVictim.COLLEAGUE
                neighbours = g.map[f"house_{a}"][1][0] == g.map[f"house_{b}"][1][0]
                if relation:
                    first, second = (a, b) if self.relations[a]["target"] == b else (b, a)
                    reason = relation["reason"]
                    lines = {
                        "une dette jamais remboursée": ("Cette histoire d'argent me reste en travers de la gorge.", "Pas ici. On peut en parler ailleurs ?"),
                        "une place convoitée au travail": ("Tu pourrais au moins arrêter de parler de cette place devant moi.", "D'accord. Pas ce soir."),
                        "un service qui a mal tourné": ("La dernière fois que j'ai voulu rendre service, ça m'est retombé dessus.", "Je sais. Je ne te demande plus rien."),
                        "une dispute entendue dans l'escalier": ("On vous entendait jusque dans l'escalier, l'autre soir.", "Je n'avais pas envie que tout l'immeuble soit au courant."),
                    }[reason]
                    topic = "relation"
                elif colleagues:
                    first, second, topic = a, b, "colleagues"
                    lines = ("Depuis sa mort, je n'arrive plus à me concentrer au travail.", "Moi non plus. J'ai encore du mal à réaliser.")
                elif neighbours:
                    first, second, topic = a, b, "neighbours"
                    lines = ("Je n'ai pas envie de rentrer. Tout me rappelle ce qui s'est passé dans le quartier.", "Je comprends. Je vais rester encore un peu, moi aussi.")
                else:
                    continue
                scenes.append({"id": f"exchange:{min(a, b)}:{max(a, b)}:{topic}", "topic": topic,
                               "actors": [first, second],
                               "beats": [{"actor": first, "text": lines[0]}, {"actor": second, "text": lines[1]}]})
        return scenes

    def _sources(self):
        g, spec = self.game, self.spec
        rival = g.name(self.rival)
        names = self._names(self.object_people)
        item = spec["object"]
        docs = {
            "clock": {"place": "crime_scene", "title": "La fenêtre du crime",
                      "text": f"Le rapport de police situe la mort {self.window}. Aucun agresseur n'y est identifié.",
                      "people": [], "leads": []},
            "trace": {"place": "house_0", "title": {"theft": "Les relances du créancier", "blackmail": "Le courrier à l'avocat", "revenge": "Une demande d'excuses"}[self.family],
                      "text": f"{spec['document']} Plusieurs noms reviennent dans les courriers : {self._names(self.pressure_people)}. "
                              "Aucun de ces courriers ne raconte la soirée du meurtre. La rue où la victime a été retrouvée est couverte par une caméra de la Régie vidéo.",
                      "people": sorted(self.pressure_people), "leads": ["crime_scene", "cctv"], "target": 0},
            "rival": {"place": f"house_{self.rival}", "title": f"Une attestation pour {rival}",
                      "text": f"{spec['document']} {rival} partage cette pression avec {self._names(self.pressure_people - {self.rival})}. "
                              f"Une attestation indique sa présence {'à son domicile' if g.night[self.rival] == 'home' else 'à ' + g.label(g.night[self.rival])}, {self.window}. "
                              f"Le document porte la mention : « Original conservé — {g.label(self.check_place)} ».",
                      "people": [self.rival], "leads": [self.check_place], "target": self.rival},
        }
        if item:
            docs["loss"] = {"place": "victim_house", "title": "Un objet manque",
                "text": f"{spec['effect']} Ses notes situent ce coffre à {g.label(spec['relay'])}. "
                        "Il sert à plusieurs usagers du lieu, qui ne se connaissent pas forcément. "
                        "Les doubles de clé sont inscrits dans un registre conservé sur place.",
                "people": [], "leads": [spec["relay"]]}
            docs["access"] = {"place": spec["relay"], "title": "Qui pouvait ouvrir le coffre ?",
                "text": f"Le registre signale la disparition de {item}, que la victime avait rangé dans ce coffre. "
                        "Le coffre a été ouvert sans être forcé. "
                        f"Le registre indique que plusieurs usagers détenaient un double de sa clé : {names}. "
                        "Le registre ne précise pas qui a ouvert le coffre ce soir-là.",
                "people": self.access, "leads": [f"house_{s}" for s in self.access]}
            if self.cache_place:
                docs["cache"] = {"place": self.cache_place, "title": "L'objet retrouvé dans une cache",
                    "text": f"Derrière une grille descellée, vous retrouvez {item}. "
                            "Son marquage correspond à celui décrit dans les affaires de la victime. "
                            "Aucun nom, aucune trace exploitable : impossible de savoir qui l'a caché ici.",
                    "people": [], "leads": []}
        else:
            docs["meeting"] = {"place": "victim_house", "title": "Qui connaissait le rendez-vous ?",
                "text": f"{spec['effect']} Une invitation privée indique où retrouver la victime après cette réunion. "
                        f"Des copies ont été envoyées à {names}. Aucun registre de présence n'accompagne les invitations.",
                "people": self.access, "leads": [f"house_{s}" for s in self.access]}
        for sid in self.pressure_people - {0}:
            docs[f"trace_{sid}"] = {**docs["trace"], "place": f"house_{sid}", "target": sid}
        for sid, profile in self.profiles.items():
            if sid in (0, self.rival):
                continue
            docs[f"life_{sid}"] = {
                "place": f"house_{sid}", "title": "Une vie derrière la porte",
                "text": f"Des papiers de {g.name(sid)} évoquent {profile['secret']}. Son projet : {profile['goal']}. "
                        "Ces papiers évoquent sa vie personnelle.",
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
            return ["Vous avez déjà relevé les documents de ce lieu."]
        events = []
        for key in keys:
            doc = self.sources[key]
            if key == "cache" and not p.story_found & {"loss", "access"}:
                # An early discovery does not identify the owner or reveal a
                # storage location from papers the detective has not yet read.
                item = self.spec["object"].removesuffix(" de la victime")
                doc = {**doc, "title": "Un objet caché, à identifier",
                       "text": f"Derrière une grille descellée, vous trouvez {item}. Vous notez son marquage. "
                               "Aucun nom n'indique qui l'a caché là, ni à qui il appartient.",
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
        replies = {
            "ouvrir un atelier": "J'aimerais ouvrir mon atelier. Mais il y a ce prêt… Tant qu'il n'est pas remboursé, je suis coincé.",
            "obtenir une promotion": "J'attendais une promotion. Après ma dernière évaluation, je n'y crois plus trop.",
            "quitter le quartier": "Partir d'ici. C'est ce que je voudrais. Je n'en ai pas encore parlé autour de moi.",
            "protéger un proche": "J'ai voulu aider quelqu'un qui m'est proche. Le service que j'ai rendu… Je ne suis pas fier de ça.",
            "récupérer de l'argent prêté": "J'ai prêté de l'argent et j'en ai besoin maintenant. Mes économies ne vont pas durer éternellement.",
            "recommencer ma vie": "La séparation a été difficile. J'essaie de repartir de zéro, c'est tout.",
            "rembourser une dette": "Je dois rembourser demain. Je n'ai pas l'argent. Ça me réveille la nuit.",
            "empêcher la divulgation d'un dossier": "Il y a des documents que je ne veux pas voir sortir. Si ça arrive, je risque de tout perdre.",
            "obtenir réparation d'un conflit": "Ce qui s'est passé en public… Je n'arrive pas à le laisser derrière moi. J'aurais voulu des excuses.",
        }
        text = replies[profile["goal"]]
        # Agreement is presentation only; neither guilt nor extra knowledge.
        if self.game.case[sid][Gender] == Gender.FEMALE:
            text = text.replace("coincé.", "coincée.").replace("pas fier de", "pas fière de")
        return text, []

    def rumours(self, p, sid):
        g, knowledge = self.game, self.knowledge[sid]
        if not self._knows_victim(p, sid):
            return "Je ne connaissais pas la victime. Non, je ne sais pas qui pouvait lui en vouloir.", []
        if knowledge == "work":
            text = ("Elle m'avait dit que ça se passait mal au travail. Elle ne m'a pas donné de noms. "
                    f"Elle travaillait à {g.label(self.workplace)}.")
            p.story_rumours[sid] = {"kind": "work", "people": []}
            g.record_note(p, "piste", "Un conflit au travail ?", text, g.name(sid), leads=[self.workplace])
            return text, ["Lieu de travail noté dans le carnet."]
        if knowledge == "pressure":
            text = {
                "theft": "Il y a des gens dans le quartier qui doivent de l'argent, et pas qu'un peu. Les créanciers ne sont pas patients. Je n'irai pas raconter leurs histoires à leur place.",
                "blackmail": "Elle parlait d'un dossier qu'elle allait donner à un avocat. Ça inquiétait du monde. Je préfère ne pas en dire plus.",
                "revenge": "Il y a eu une humiliation, en public. Certains lui réclamaient des excuses. C'est tout ce que je peux vous dire.",
            }[self.family]
            # A vague account reveals no identities, including through lead buttons.
            p.story_rumours[sid] = {"kind": "pressure", "people": []}
            g.record_note(p, "piste", "Des dettes dans le quartier ?" if self.family == "theft" else
                          "Un dossier qui inquiétait ?" if self.family == "blackmail" else "Des excuses réclamées ?",
                          text, g.name(sid))
            return text, ["Récit noté · aucune personne nommée."]
        return self._voice(sid, "no_rumour", ["Non… Je ne vois pas qui. Ça me travaille depuis que je l'ai appris.",
                          "Je ne sais pas. On se connaissait, mais elle ne me racontait pas tout.",
                          "Je n'ai entendu parler de rien. Désolé, je ne peux pas vous dire plus."]), []

    def _voice(self, sid, topic, alternatives):
        return random.Random(f"nexus-voice-v1:{self.game.seed}:{sid}:{topic}").choice(alternatives)

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
            text = (f"{g.name(target)} ? Je connais de vue, mais je ne sais rien de ses rapports avec la victime." if target in self.link_contacts[sid]
                    else f"{g.name(target)} ? Ce nom ne me dit rien.")
        else:
            street = g.map[f"house_{sid}"][1][0]
            neighbour = g.map[f"house_{target}"][1][0] == street
            basis = "On habite le même quartier ; je les ai vus se fréquenter" if neighbour else "Je les connais de notre entourage ; ils en ont parlé devant moi"
            descriptions = {
                LinkToVictim.EX: "une ancienne relation amoureuse avec la victime",
                LinkToVictim.PARTNER: "une relation amoureuse avec la victime, toujours en cours avant sa mort",
                LinkToVictim.SIBLING: "un lien de famille avec la victime",
                LinkToVictim.COLLEAGUE: "une relation de travail avec la victime",
                LinkToVictim.NEIGHBORHOOD: "des rapports de voisinage avec la victime",
            }
            text = f"{g.name(target)} ? Oui, {descriptions[link]}. {basis}."
            p.link_witnesses.setdefault(target, set()).add(sid)
            leads = [f"house_{target}"]
            if p.link_claims.get(target) == LinkToVictim.UNKNOWN:
                text += " C'est ce dont je me souviens, en tout cas."
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
                    "Le visage est trop flou pour reconnaître quelqu'un.")
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
            text += "Mes papiers sont chez moi. Si vous voulez les regarder, allez-y. Je n'ai rien volé."
            p.invited.add(sid)
            leads = [f"house_{sid}"]
        elif key == "meeting":
            text = "Oui, j'ai reçu l'invitation. Vous pouvez regarder mes papiers chez moi, si vous y tenez."
            p.invited.add(sid)
            leads = [f"house_{sid}"]
        elif key == "rival":
            text = "Oui, on avait un conflit. Mais à cette heure-là, j'étais ailleurs. L'attestation est là, vous l'avez."
            leads = []
        elif key == "statement":
            text = "D'accord, ma description était inventée. Je voulais détourner vos questions. Ça ne répond pas encore à votre question sur le meurtre."
            leads = [f"house_{sid}"]
        elif key == "relationship":
            link = g.case[sid][LinkToVictim]
            text = (f"D'accord, j'ai caché ce lien : {TRAIT_TEXT[link]}. Je ne voulais pas que notre histoire personnelle devienne publique. "
                    "Je n'avais pas envie que tout le quartier en parle.")
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
                text = self._personal_document_reply(sid)
                leads = []
        else:
            text = self._personal_document_reply(sid)
            leads = []
        g.record_note(p, "déclaration", "Réponse à une preuve", text, g.name(sid), people=[sid], leads=leads)
        g.dialogue_cue(p, sid, text, "reply", question="Que répondez-vous à ce document ?", notes=["Déclaration conservée dans les Notes."])
        return [f"{g.name(sid)} — {text}"]

    def _personal_document_reply(self, sid):
        # Identical construction for guilty/innocent people with the same problem.
        topic = self.profiles[sid]["goal"]
        detail = {
            "rembourser une dette": "Oui, j'ai une dette. Vous avez vu les relances. Je n'arrive plus à penser à autre chose.",
            "empêcher la divulgation d'un dossier": "Ce dossier me fait peur, oui. J'aurais préféré que personne n'en entende parler.",
            "obtenir réparation d'un conflit": "J'attendais des excuses. Ça peut vous paraître dérisoire, mais pas à moi.",
        }.get(topic, "Ce sont mes papiers personnels. Je n'avais pas envie que vous tombiez dessus.")
        return detail

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
                "Le marquage est noté. Les affaires de la victime sont à son domicile." if unidentified else
                f"Le registre des doubles de clé est conservé à {g.label(self.spec['relay'])}." if "access" not in found
                else "L'objet a été retrouvé dans une cache sans nom ni trace exploitable." if "cache" in found
                else "Le registre cite plusieurs détenteurs de clé. Il ne dit pas qui a ouvert le coffre.",
                object_destinations, "access" in found)
        if self.access_key in found or "trace" in found or any(r.get("kind") == "pressure" for r in p.story_rumours.values()):
            people = self.pressure_people if "trace" in found else self.object_people if self.access_key in found else ()
            subject = {"theft": ("Des dettes dans le quartier", "Plusieurs habitants doivent de l'argent."),
                       "blackmail": ("Le dossier de la victime", "Un dossier devait être remis à un avocat."),
                       "revenge": ("Des excuses attendues", "Une humiliation publique a laissé de la rancœur.")}[self.family]
            if "trace" not in found and not any(r.get("kind") == "pressure" for r in p.story_rumours.values()):
                subject = ("Pourquoi cette disparition ?", "Un objet a été pris dans le coffre.") if self.spec["object"] else ("Pourquoi ce rendez-vous ?", "La victime avait envoyé plusieurs invitations.")
            add("motive", subject[0], subject[1],
                "Pour l'instant, aucun nom n'a été donné." if not people else
                "Les personnes citées ont des papiers à leur domicile." if "trace" not in found else
                "Les courriers citent plusieurs personnes. Ils ne racontent pas la nuit du meurtre.",
                [f"house_{s}" for s in g.order if s in people], "trace" in found)
        if "clock" in found or "trace" in found:
            add("time", "Qui était dans la rue ce soir-là ?", f"La mort est située {self.window}." if "clock" in found else "L'heure de la mort n'est pas encore connue.",
                "Le rapport de police est sur la scène de crime. Une caméra filme cette rue ; ses enregistrements sont à la Régie vidéo." if "camera" not in found
                else "Sur la vidéo, on distingue un accessoire, mais pas le visage. Plusieurs habitants possèdent le même.",
                (["crime_scene"] if "clock" not in found else []) + ["cctv"], "camera" in found)
        if self.work_conflict and ("work" in found or any(r.get("kind") == "work" for r in p.story_rumours.values())):
            add("work", "Des tensions au travail", "Un proche évoque un conflit sans connaître les noms.",
                "Un planning et les collègues sont rattachés au lieu de travail." if "work" not in found
                else "Le planning cite plusieurs collègues. Leurs déclarations figurent dans les Notes une fois recueillies.",
                [self.workplace] if "work" not in found else [f"house_{s}" for s in g.order if s in self.work_conflict], "work" in found)
        if "rival" in found:
            add("alibi", f"Où était {g.name(self.rival)} ?", "Une attestation indique une présence ailleurs au moment du meurtre.",
                f"L'original du registre est conservé à {g.label(self.check_place)}." if self.rival not in p.timeline_verified
                else "Le registre original confirme sa présence loin du crime.",
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
