"""Social filling and bounded knowledge. An overlay, never a rewrite of the crime.

Relationships are facts; messages are authored transmissions of specific facts.
Neither is an identity proof. Mental events are deliberately not projected.
"""
import random
from dataclasses import dataclass
from enum import Enum

from scenario_kernel import DemandKind, EventKind, IncidentKind, RelationKind


class Link(Enum):
    SIBLINGS = "fratrie"
    FRIENDS = "amis"
    NEIGHBORS = "voisins"
    COLLEAGUES = "collègues"
    ACQUAINTANCES = "connaissances"
    PARTNERS = "couple"
    EXES = "ancien couple"


@dataclass(frozen=True)
class SocialBond:
    id: str
    people: tuple[str, str]
    kind: Link
    source: str
    since: int


@dataclass(frozen=True)
class Message:
    id: str
    sender: str
    recipient: str
    text: str
    sent_at: int
    read_at: int | None
    source: str
    # A forwarded summary may only retain this bounded payload, not its source's
    # entire private incident (including the perpetrator).
    forwarded_from: str | None = None


@dataclass(frozen=True)
class OrdinaryFact:
    id: str
    people: tuple[str, str]
    kind: str
    minute: int
    detail: str
    amount: int = 0
    disclosed_bond: str | None = None


def message_payload(source, kernel):
    """The allowed fact payload, shared by construction AND validation. No
    freely authored text can silently acquire the incident's hidden culprit.
    """
    world, roles = kernel.world, kernel.roles
    people = {p.id: p for p in world.people}
    kind = source.kind
    if kind is EventKind.SEPARATION_ANNOUNCED:
        return "Je veux qu'on se sépare. Je ne veux plus vivre comme ça."
    if kind in (EventKind.DEMAND_MADE, EventKind.REFUSAL_EXPRESSED):
        d = next(d for d in world.demands if d.id == source.subject)
        if kind is EventKind.DEMAND_MADE:
            return ("Donne-moi accès à ton téléphone." if d.kind is DemandKind.PHONE_ACCESS else
                    f"Je ne veux plus que tu voies {people[d.third_person].name}.")
        return "Non. Mon téléphone, c'est privé." if d.kind is DemandKind.PHONE_ACCESS else "Non. Je décide qui je vois."
    if kind is EventKind.RELATIONSHIP_DISCLOSED:
        return f"Je suis avec {people[roles.victim].name} maintenant."
    if kind is EventKind.RECONCILIATION_REFUSED:
        return "Notre histoire est terminée. Je ne veux pas qu'on recommence."
    if kind is EventKind.DISCLOSURE_ANNOUNCED:
        disclosure = next(d for d in world.disclosures if d.id == source.subject)
        incident = next(i for i in world.incidents if i.id == disclosure.incident)
        return {
            IncidentKind.DIVERTED_WAGES: "Il manque de l'argent sur ma paie. J'ai gardé les relevés et je vais en parler.",
            IncidentKind.UNPAID_WORK: "Mes heures supplémentaires n'ont pas été payées. J'ai gardé les plannings et je vais en parler.",
            IncidentKind.PREVIOUS_THEFT: "J'ai découvert quelque chose sur le vol au travail. Je ne veux pas garder ça pour moi.",
        }[incident.kind]
    if kind == "loan":
        return f"Tu m'avais promis de me rendre les {source.amount} € hier. J'en ai besoin aussi."
    if kind == "cancelled_meeting":
        return "J'avais réservé notre soirée. Prévenir dix minutes avant, ça m'a vraiment blessé."
    if kind == "heard_late_music":
        return "Ta musique porte jusque chez moi. Il est presque minuit, je n'arrive pas à dormir. Tu peux baisser ?"
    return None


@dataclass(frozen=True)
class Life:
    crime: object
    bonds: tuple[SocialBond, ...]
    ordinary: tuple[OrdinaryFact, ...]
    messages: tuple[Message, ...]
    habits: tuple[tuple[str, str], ...]

    def __post_init__(self):
        self.validate()

    @property
    def people(self):
        return {p.id: p for p in self.crime.kernel.world.people}

    def links(self, person, other=None):
        other = other or self.crime.kernel.roles.victim
        return tuple(b for b in self.bonds if set(b.people) == {person, other})

    def knows(self, person, other):
        return bool(self.links(person, other)) or any(
            {m.sender, m.recipient} == {person, other} and m.read_at is not None
            for m in self.messages)

    def inbox(self, person):
        return tuple(m for m in self.messages if person == m.sender or
                     person == m.recipient and m.read_at is not None)

    def concerns(self, person):
        """Concrete grounds to ask about, never a list of guilty people.

        A forwarded message does not make its recipient a party to the dispute.
        This catalogue is private until its correspondence/answer is acquired.
        """
        victim = self.crime.kernel.roles.victim
        rows = []
        for fact in self.ordinary:
            if fact.kind in ("loan", "cancelled_meeting", "heard_late_music") and set(fact.people) == {person, victim}:
                rows.append((fact.id, fact.detail))
        events = {e.id: e for e in self.crime.kernel.world.events}
        for message in self.messages:
            event = events.get(message.source)
            if event and person in (event.actor, event.target) and victim in (event.actor, event.target):
                pair = (event.id, message.text)
                if pair not in rows:
                    rows.append(pair)
        return tuple(rows)

    def answer(self, person, topic="relation"):
        p, v = self.people[person], self.people[self.crime.kernel.roles.victim]
        links = self.links(person)
        if topic == "motive":
            # Summaries of experienced/received facts, not a document dump and
            # never an omniscient list of people who "must" have a motive.
            ordinary_reply = None
            for fact in self.ordinary:
                if fact.kind == "loan" and fact.people[0] == person and fact.people[1] == v.id:
                    ordinary_reply = f"J'avais avancé {fact.amount} € à {v.name}. Le remboursement promis n'était pas arrivé. Ça m'agaçait, oui."
                    break
                if fact.kind == "heard_late_music" and fact.people == (v.id, person):
                    ordinary_reply = "Je lui avais demandé de baisser sa musique. Ça m'empêchait de dormir."
                    break
                if fact.kind == "cancelled_meeting" and fact.people == (person, v.id):
                    ordinary_reply = "On avait prévu une soirée ensemble, puis tout a été annulé au dernier moment. Je l'avais mal pris."
                    break
            events = {e.id: e for e in self.crime.kernel.world.events}
            for message in reversed(self.inbox(person)):
                event = events.get(message.source)
                if event is None:
                    continue
                if event.kind is EventKind.DISCLOSURE_ANNOUNCED:
                    disclosure = next(d for d in self.crime.kernel.world.disclosures if d.id == event.subject)
                    incident = next(i for i in self.crime.kernel.world.incidents if i.id == disclosure.incident)
                    problem = {IncidentKind.DIVERTED_WAGES: "de l'argent manquant sur sa paie",
                               IncidentKind.UNPAID_WORK: "des heures supplémentaires non payées",
                               IncidentKind.PREVIOUS_THEFT: "un vol au travail"}[incident.kind]
                    reply = (f"{v.name} m'avait écrit à propos de {problem}."
                             if message.sender == v.id and event.target == person else
                             f"On m'avait parlé d'un problème concernant {v.name} : {problem}. Je n'en sais pas davantage.")
                    return reply + ("\n" + ordinary_reply if ordinary_reply else "")
                if event.kind in (EventKind.SEPARATION_ANNOUNCED, EventKind.RECONCILIATION_REFUSED,
                                  EventKind.RELATIONSHIP_DISCLOSED, EventKind.REFUSAL_EXPRESSED, EventKind.DEMAND_MADE):
                    reply = ("On avait des désaccords dans notre couple. Je ne vais pas prétendre le contraire."
                            if any(b.kind in (Link.PARTNERS, Link.EXES) for b in links) else
                            f"J'avais entendu parler de tensions dans la vie sentimentale de {v.name}. Je ne connaissais pas tous les détails.")
                    return reply + ("\n" + ordinary_reply if ordinary_reply else "")
            if ordinary_reply:
                return ordinary_reply
            return "Je ne savais pas de qui vous parliez avant aujourd'hui." if not self.knows(person, v.id) else "Je ne sais pas qui aurait pu vouloir sa mort."
        if topic == "work":
            where = {"cabaret": "au Palace", "bar": "au Néon Bleu", "hospital": "à l'hôpital",
                     "cctv": "à la Régie vidéo", "restaurant": "au Comptoir"}[p.workplace.value]
            job = {"dance": "Je danse", "stage_management": "Je m'occupe de la régie de scène",
                   "table_service": "Je fais le service en salle", "bar_management": "Je gère le bar",
                   "nursing": "Je m'occupe des soins infirmiers", "hospital_admin": "Je travaille à l'administration",
                   "video_technician": "Je fais la maintenance des caméras", "video_management": "Je dirige la Régie",
                   "accounting": "Je tiens la comptabilité", "cooking": "Je travaille en cuisine",
                   "restaurant_management": "Je gère le restaurant"}[p.occupation.value]
            # Naming the people one works with: a lead for whoever suspects the workplace.
            colleagues = sorted(self.people[other].name for b in self.bonds if b.kind is Link.COLLEAGUES and person in b.people
                                for other in b.people if other != person)
            if not colleagues:
                return job + ", " + where + "."
            named = colleagues[0] if len(colleagues) == 1 else ", ".join(colleagues[:-1]) + " et " + colleagues[-1]
            return job + ", " + where + ", avec " + named + "."
        if topic == "circle":
            # Who the victim kept company with, as far as this person knows: names to follow up,
            # never somebody else's private history.
            close = sorted(self.people[other].name for other in self.people if other not in (person, v.id)
                           and self.knows(person, other) and self.links(other, v.id))
            if not close:
                return f"Je ne saurais pas dire qui {v.name} fréquentait."
            named = close[0] if len(close) == 1 else ", ".join(close[:-1]) + " et " + close[-1]
            return f"Les gens que je savais proches de {v.name} : {named}."
        if topic == "habits":
            return {"Aime marcher le long du canal après le travail.": "Après le travail, j'aime marcher le long du canal. Ça me permet de souffler.",
                    "Collectionne les vieux disques.": "Je collectionne les vieux disques. J'aime bien fouiller les bacs pour trouver quelque chose que je ne connais pas.",
                    "Cuisine pour ses amis le dimanche.": "Le dimanche, je cuisine pour mes amis. C'est un peu notre rendez-vous à nous.",
                    "Préfère les petits concerts aux grandes soirées.": "Je préfère les petits concerts aux grandes soirées. On s'y sent mieux."}[dict(self.habits)[person]]
        if topic == "relation":
            phrasing = {
                Link.SIBLINGS: f"{v.name}, c'était " + ("mon frère." if v.name in ("Oscar", "Marius", "Bruno", "Farid", "Karim") else "ma sœur."),
                Link.FRIENDS: f"On était amis, {v.name} et moi. On se connaissait depuis longtemps.",
                Link.NEIGHBORS: f"On habitait dans la même rue, {v.name} et moi. On se croisait dehors.",
                Link.COLLEAGUES: "On travaillait ensemble " + {
                    "cabaret": "au Palace", "bar": "au Néon Bleu", "hospital": "à l'hôpital",
                    "cctv": "à la Régie vidéo", "restaurant": "au Comptoir"}[p.workplace.value] + ".",
                Link.ACQUAINTANCES: f"Je connaissais {v.name}, mais on n'était pas proches.",
                Link.PARTNERS: f"{v.name} et moi, nous étions ensemble.",
                Link.EXES: f"J'ai été en couple avec {v.name}. C'était terminé depuis un moment.",
            }
            if links:
                return " ".join(phrasing[b.kind] for b in links)
            if self.knows(person, v.id):
                return "Nous avions échangé quelques messages, sans être proches."
            return f"Je ne connaissais pas la victime. {v.name}, vous dites ?"
        if topic == "messages":
            rows = tuple(m for m in self.inbox(person) if v.id in (m.sender, m.recipient)
                         or m.forwarded_from is not None)
            if not rows:
                return "On ne s'était pas écrit récemment." if self.knows(person, v.id) else "Non, aucun échange avec cette personne."
            prefix = "Nous n'avons jamais échangé directement. On m'a seulement transmis ce message.\n" if not self.knows(person, v.id) else ""
            return prefix + "\n".join(f"{self.people[m.sender].name} m'a écrit : « {m.text} »"
                             if m.recipient == person else f"J'ai écrit : « {m.text} »" for m in rows)
        raise ValueError("Unknown conversation topic")

    def answer_about(self, person, other):
        """Own relationship only. A shared contact does not grant omniscience
        about somebody else's relationship with the victim.
        """
        if person not in self.people or other not in self.people or person == other:
            raise ValueError("Two distinct existing people")
        if other == self.crime.kernel.roles.victim:
            return self.answer(person)
        bonds = self.links(person, other)
        name = self.people[other].name
        rivalry = next((f for f in self.ordinary if f.kind == "ex_and_partner" and set(f.people) == {person, other}), None)
        if rivalry:
            victim = self.people[self.crime.kernel.roles.victim].name
            asking_ex = rivalry.people[0] == person
            feminine = name not in ("Oscar", "Marius", "Bruno", "Farid", "Karim")
            if asking_ex:  # the ex, about the one who came next
                return name + " ? " + {
                    "venom": ("Celle" if feminine else "Celui") + f" qui a pris la suite. On s'est croisés, sans plus. Je ne vais pas faire semblant d'avoir apprécié.",
                    "grace": f"Je savais qu'ils étaient ensemble. {victim} avait l'air heureux. Tant mieux, sincèrement.",
                    "neutral": f"On se connaît de vue, par {victim}. Je n'ai rien de particulier à en dire.",
                }[rivalry.detail]
            return name + " ? " + {  # the partner, about the ex
                "venom": f"L'ex de {victim}. On s'est croisés deux ou trois fois. Jamais chaleureux.",
                "grace": f"L'ex de {victim}. C'était fini depuis longtemps ; il n'y avait pas de gêne entre nous.",
                "neutral": f"L'ex de {victim}. On se connaît de vue, c'est tout.",
            }[rivalry.detail]
        breakup = next((f for f in self.ordinary if f.kind == "sour_breakup" and set(f.people) == {person, other}), None)
        if breakup:
            victim = self.people[self.crime.kernel.roles.victim]
            moved_on = person if self.links(person, victim.id) and any(b.kind is Link.PARTNERS for b in self.links(person, victim.id)) else other
            feminine = name not in ("Oscar", "Marius", "Bruno", "Farid", "Karim")
            if moved_on == person:  # the one who left, about the ex who did not accept it
                return name + " ? " + ("Mon ex. Ça s'est mal fini : " + ("elle" if feminine else "il") + " n'acceptait pas que je passe à autre chose."
                                       if breakup.detail == "venom" else "Mon ex. C'est terminé, et je préfère ne pas m'étendre.")
            return name + " ? " + (f"On a été ensemble. {name} est passé{'e' if feminine else ''} à autre chose, avec {victim.name}. Je ne vais pas prétendre que ça m'a fait plaisir."
                                   if breakup.detail == "venom" else f"On a été ensemble. C'est fini ; {name} a refait sa vie. Voilà.")
        phrases = {
            Link.SIBLINGS: "Nous sommes de la même fratrie.", Link.FRIENDS: "On est amis.",
            Link.NEIGHBORS: "On habite dans la même rue.", Link.COLLEAGUES: "On travaille ensemble.",
            Link.ACQUAINTANCES: "On se connaît, sans être proches.", Link.PARTNERS: "Nous sommes ensemble.",
            Link.EXES: "Nous avons été ensemble. C'est terminé.",
        }
        if bonds:
            introduction = next((f for f in self.ordinary if f.kind == "social_introduction"
                                 and set(f.people) == {person, other}), None)
            if introduction:
                shared = next(b for b in self.bonds if b.id == introduction.disclosed_bond)
                victim = self.people[self.crime.kernel.roles.victim].name
                detail = f" {name} et {victim} étaient ensemble." if other in shared.people else ""
                return name + f" ? {victim} nous avait présentés." + detail
            return name + " ? " + " ".join(phrases[b.kind] for b in bonds)
        if self.knows(person, other):
            return name + " ? Nous avons échangé quelques messages."
        if any(name in m.text for m in self.inbox(person)):
            return name + " ? On m'en avait parlé, mais je ne connais pas cette personne personnellement."
        return name + " ? Je ne connais pas cette personne."

    def validate(self):
        people, streets = self.people, self.crime.streets
        ids = [x.id for x in self.bonds + self.ordinary + self.messages]
        if len(set(ids)) != len(ids):
            raise ValueError("Unique social facts")
        world = self.crime.kernel.world
        sources = {x.id: x for field in ("relationships", "events") for x in getattr(world, field)}
        sources.update({x.id: x for x in self.ordinary})
        for fact in self.ordinary:
            if (len(set(fact.people)) != 2 or not set(fact.people) <= people.keys()
                    or type(fact.minute) is not int or fact.minute >= 0 or not fact.detail
                    or fact.kind == "loan" and (type(fact.amount) is not int or fact.amount <= 0)):
                raise ValueError("Concrete ordinary facts")
            if fact.kind == "social_introduction":
                victim = self.crime.kernel.roles.victim
                disclosed = next((b for b in self.bonds if b.id == fact.disclosed_bond), None)
                if (disclosed is None or disclosed.kind is not Link.PARTNERS or victim not in disclosed.people
                        or victim in fact.people):
                    raise ValueError("Introduction must disclose a real partner of the victim")
                partner = next(p for p in disclosed.people if p != victim)
                contact = next((p for p in fact.people if p != partner), None)
                close = next((b for b in self.links(contact, victim)
                              if b.kind in (Link.FRIENDS, Link.SIBLINGS)), None)
                if (partner not in fact.people or close is None
                        or fact.minute <= max(disclosed.since, close.since)):
                    raise ValueError("Introduction follows both existing relationships")
            elif fact.disclosed_bond is not None:
                raise ValueError("Only an introduction discloses somebody else's relationship")
        for b in self.bonds:
            if len(set(b.people)) != 2 or not set(b.people) <= people.keys():
                raise ValueError("Two existing people per bond")
            a, c = (people[x] for x in b.people)
            if b.kind is Link.NEIGHBORS and (a.home == c.home or
                    streets.neighbors(a.home)[0][0] != streets.neighbors(c.home)[0][0]):
                raise ValueError("Neighbors really live on the same street")
            if b.kind is Link.COLLEAGUES and a.workplace != c.workplace:
                raise ValueError("Actual shared workplace")
            if b.kind is Link.SIBLINGS and any(other.kind in (Link.EXES, Link.PARTNERS)
                    and set(other.people) == set(b.people) for other in self.bonds):
                raise ValueError("No siblings who are also a couple")
            if b.kind is Link.PARTNERS:
                for member in b.people:
                    if sum(member in other.people and other.kind is Link.PARTNERS for other in self.bonds) != 1:
                        raise ValueError("No unexplained simultaneous couples")
            if b.source not in sources:
                raise ValueError("A bond needs a real source")
        # Kinship is transitive. A and B cannot silently become siblings through
        # the victim if their pre-existing romance would make that contradictory.
        family = {p: {p} for p in people}
        for b in self.bonds:
            if b.kind is Link.SIBLINGS:
                group = family[b.people[0]] | family[b.people[1]]
                for p in group:
                    family[p] = group
        for b in self.bonds:
            if b.kind in (Link.PARTNERS, Link.EXES) and b.people[1] in family[b.people[0]]:
                raise ValueError("Romance inside a sibling component")
        messages = {m.id: m for m in self.messages}
        for m in self.messages:
            if (m.sender == m.recipient or not {m.sender, m.recipient} <= people.keys()
                    or not m.text or m.sent_at >= self.crime.execution.attack_at
                    or m.read_at is not None and not m.sent_at <= m.read_at < self.crime.execution.attack_at):
                raise ValueError("Chronological real communication")
            if m.forwarded_from:
                parent = messages.get(m.forwarded_from)
                if (parent is None or parent.recipient != m.sender or parent.read_at is None
                        or parent.read_at > m.sent_at or m.text != parent.text):
                    raise ValueError("Cannot forward unread knowledge or expand its scope")
            else:
                source = sources.get(m.source)
                if source is None or getattr(source, "minute", m.sent_at) > m.sent_at:
                    raise ValueError("Communication must follow its source")
                if hasattr(source, "kind") and source.kind in (
                    EventKind.INTENT_FORMED, EventKind.AUTONOMY_REJECTED,
                    EventKind.DISCLOSURE_FEARED, EventKind.RIVAL_BLAMED):
                    raise ValueError("Private mental events are not testimony")
                if m.text != message_payload(source, self.crime.kernel):
                    raise ValueError("Message expanded its source's bounded payload")
                if hasattr(source, "actor") and m.sender != source.actor:
                    raise ValueError("The sender did not experience this source fact")
                if isinstance(source, OrdinaryFact):
                    # Complaints are sent by the hearer; loans/cancellations by
                    # the lender or person left waiting, not an unrelated actor.
                    sender = source.people[1] if source.kind == "heard_late_music" else source.people[0]
                    if m.sender != sender:
                        raise ValueError("The sender did not experience this ordinary fact")


def build_life(crime, seed=0):
    rng = random.Random(f"life-v1:{seed}")
    world, roles = crime.kernel.world, crime.kernel.roles
    people = {p.id: p for p in world.people}
    bonds, ordinary, messages = [], [], []
    strangers = {frozenset((f.author, f.target)) for f in world.fixations}  # the chance encounter stays one
    def stranger_pair(pair):
        return frozenset(pair) in strangers
    kinds = {RelationKind.ROMANTIC: Link.PARTNERS, RelationKind.FRIENDS: Link.FRIENDS,
             RelationKind.COLLEAGUES: Link.COLLEAGUES, RelationKind.ACQUAINTANCES: Link.ACQUAINTANCES}
    for r in world.relationships:
        kind = Link.EXES if r.kind is RelationKind.ROMANTIC and not r.active_at(0) else kinds[r.kind]
        bonds.append(SocialBond("bond:" + r.id, r.people, kind, r.id, r.since))
    # The social fabric does not run through the victim: colleagues always know
    # each other, and most people know who lives on their street.
    fabric = random.Random(f"social-fabric-v1:{seed}")
    ids = sorted(people)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            pa, pb = people[a], people[b]
            if stranger_pair({a, b}):
                continue  # a predator and his prey share nothing, not even a street
            if pa.workplace == pb.workplace and not any(x.kind is Link.COLLEAGUES and set(x.people) == {a, b} for x in bonds):
                fact = OrdinaryFact(f"workplace:{a}:{b}", (a, b), "shared_workplace",
                                    -fabric.randrange(120, 1500) * 1440, "Même employeur.")
                ordinary.append(fact)
                bonds.append(SocialBond("bond:" + fact.id, fact.people, Link.COLLEAGUES, fact.id, fact.minute))
            same_street = pa.home != pb.home and crime.streets.neighbors(pa.home)[0][0] == crime.streets.neighbors(pb.home)[0][0]
            if same_street and fabric.random() < .6 and not any(x.kind is Link.NEIGHBORS and set(x.people) == {a, b} for x in bonds):
                fact = OrdinaryFact(f"street:{a}:{b}", (a, b), "same_street",
                                    -fabric.randrange(120, 1500) * 1440, "Même rue.")
                ordinary.append(fact)
                bonds.append(SocialBond("bond:" + fact.id, fact.people, Link.NEIGHBORS, fact.id, fact.minute))
    # A few more direct ties to the victim, independently of criminal role.
    # Most people are not her friends: absence of a relationship is the norm.
    for p in world.people:
        if p.id == roles.victim or any(set(b.people) == {p.id, roles.victim} for b in bonds) or stranger_pair({p.id, roles.victim}):
            continue
        options = [None] * 6 + [Link.FRIENDS, Link.ACQUAINTANCES, Link.SIBLINGS]
        v = people[roles.victim]
        family = {v.id} | {other for b in bonds if b.kind is Link.SIBLINGS and v.id in b.people for other in b.people}
        if any(b.kind in (Link.PARTNERS, Link.EXES) and p.id in b.people
               and any(other in family for other in b.people if other != p.id) for b in bonds):
            options.remove(Link.SIBLINGS)
        kind = rng.choice(options)
        if kind is not None:
            fact = OrdinaryFact("family_or_contact:" + p.id, (p.id, v.id), "social_history",
                                -rng.randrange(365, 2000) * 1440, kind.value)
            ordinary.append(fact)
            bonds.append(SocialBond("bond:" + p.id, fact.people, kind, fact.id, fact.minute))
    family = sorted({other for b in bonds if b.kind is Link.SIBLINGS and roles.victim in b.people for other in b.people})
    for i, a in enumerate(family):
        for b in family[i + 1:]:
            if any(x.kind is Link.SIBLINGS and set(x.people) == {a, b} for x in bonds):
                continue
            fact = OrdinaryFact("kinship:" + a + ":" + b, (a, b), "shared_family", -3000 * 1440, "Même fratrie.")
            ordinary.append(fact)
            bonds.append(SocialBond("bond:" + fact.id, fact.people, Link.SIBLINGS, fact.id, fact.minute))
    # An actual message, not omniscience from a shared employer or friendship.
    def send(sender, recipient, text, at, source, parent=None, read=True):
        messages.append(Message(f"message:{len(messages)}", sender, recipient, text,
                                at, at + 2 if read else None, source, parent))

    for e in world.events:
        text = message_payload(e, crime.kernel)
        if text:
            send(e.actor, e.target, text, e.minute, e.id)
    # An ordinary grievance uses the same transmission mechanism as a root event.
    contacts = [p for p in world.people if p.id != roles.victim and
                any(set(b.people) == {p.id, roles.victim} for b in bonds)]
    rng.shuffle(contacts)
    episode_kinds = rng.sample(("loan", "cancelled_meeting"), 2)
    for index, p in enumerate(contacts[:rng.randrange(0, min(2, len(contacts)) + 1)]):
        at = -rng.randrange(3, 12) * 1440 + 18 * 60
        kind = episode_kinds[index]
        if kind == "loan":
            amount = rng.choice((40, 60, 90, 120))
            detail = f"J'ai avancé {amount} € à {people[roles.victim].name}; remboursement promis hier, pas reçu."
            text = f"Tu m'avais promis de me rendre les {amount} € hier. J'en ai besoin aussi."
        else:
            detail = "Un rendez-vous convenu a été annulé dix minutes avant par la victime."
            text = "J'avais réservé notre soirée. Prévenir dix minutes avant, ça m'a vraiment blessé."
        fact = OrdinaryFact(f"episode:{len(ordinary)}", (p.id, roles.victim), kind, at, detail,
                            amount if kind == "loan" else 0)
        ordinary.append(fact)
        send(p.id, roles.victim, text, at + 1, fact.id)
    # Optional transmission to a real contact. Often no one else knows anything.
    v_messages = [m for m in messages if m.sender == roles.victim]
    for m in v_messages:
        friends = [p for p in contacts if p.id != m.recipient]
        if friends and rng.random() < .45:
            p = rng.choice(friends)
            send(m.sender, p.id, m.text, m.sent_at + 10, m.source, read=rng.random() < .85)
    # Optional ordinary neighborhood dispute: several real neighbors complain
    # about the SAME authored late-night episode. This is not a new murder root.
    v = people[roles.victim]
    neighbors = [p for p in world.people if p.id != v.id and p.home != v.home and
                 crime.streets.neighbors(p.home)[0][0] == crime.streets.neighbors(v.home)[0][0]]
    if len(neighbors) >= 2 and rng.random() < .4:
        for p in rng.sample(neighbors, 2):
            at = -5 * 1440 + 23 * 60 + 45
            if stranger_pair({p.id, v.id}):
                continue
            fact = OrdinaryFact("noise:" + p.id, (v.id, p.id), "heard_late_music", at,
                "Musique forte depuis la fenêtre de la victime, entendue dans le logement voisin à 23 h 45.")
            ordinary.append(fact)
            if not any(b.kind is Link.NEIGHBORS and set(b.people) == {p.id, v.id} for b in bonds):
                bonds.append(SocialBond("neighbor:" + p.id, fact.people, Link.NEIGHBORS, fact.id, at))
            send(p.id, v.id, "Ta musique porte jusque chez moi. Il est presque minuit, je n'arrive pas à dormir. Tu peux baisser ?", at + 1, fact.id)
    habits = tuple((p.id, rng.choice(("Aime marcher le long du canal après le travail.",
                                     "Collectionne les vieux disques.", "Cuisine pour ses amis le dimanche.",
                                     "Préfère les petits concerts aux grandes soirées."))) for p in world.people)
    # A shared friend is not automatic acquaintance. Author a real presentation,
    # independently of guilt and of the old RNG streams, then give BOTH people
    # that bounded memory. No knowledge of the partner's private conflicts.
    introductions = random.Random(f"social-introductions-v1:{seed}")
    partners = [b for b in bonds if b.kind is Link.PARTNERS and roles.victim in b.people]
    close_contacts = [b for b in bonds if b.kind in (Link.FRIENDS, Link.SIBLINGS)
                      and roles.victim in b.people]
    for couple in partners:
        partner = next(p for p in couple.people if p != roles.victim)
        for close in close_contacts:
            contact = next(p for p in close.people if p != roles.victim)
            if contact == partner or introductions.random() >= .65:
                continue
            since = max(couple.since, close.since)
            if since >= -1:
                continue
            minute = introductions.randrange(since + 1, 0)
            fact = OrdinaryFact(f"introduction:{contact}:{partner}", (contact, partner),
                "social_introduction", minute, f"Présentés l'un à l'autre par {v.name}.",
                disclosed_bond=couple.id)
            ordinary.append(fact)
            if not any(set(b.people) == set(fact.people) for b in bonds):
                bonds.append(SocialBond("bond:" + fact.id, fact.people, Link.ACQUAINTANCES,
                                        fact.id, fact.minute))
    # An ex usually knows who came next, and has an opinion about it: venom or
    # grace, drawn regardless of guilt. Both sides remember the encounter.
    rivalry = random.Random(f"ex-and-partner-v1:{seed}")
    for former in [b for b in bonds if b.kind is Link.EXES and roles.victim in b.people]:
        ex = next(p for p in former.people if p != roles.victim)
        for couple in partners:
            partner = next(p for p in couple.people if p != roles.victim)
            since = max(former.since, couple.since)
            if partner == ex or since >= -1 or rivalry.random() >= .8:
                continue
            # A triangle that went sour (the story's own romantic events, innocent or not)
            # tilts the tone toward venom; otherwise grace is the norm.
            sour = any(e.kind in (EventKind.SEPARATION_ANNOUNCED, EventKind.RECONCILIATION_REFUSED,
                                  EventKind.RELATIONSHIP_DISCLOSED, EventKind.REFUSAL_EXPRESSED, EventKind.DEMAND_MADE)
                       and {ex, roles.victim} <= {e.actor, e.target} for e in world.events)
            tone = rivalry.choice(("venom", "venom", "venom", "neutral", "grace") if sour else ("grace", "grace", "grace", "neutral", "venom"))
            fact = OrdinaryFact(f"rivalry:{ex}:{partner}", (ex, partner), "ex_and_partner",
                                rivalry.randrange(since + 1, 0), tone)
            ordinary.append(fact)
            if not any(set(b.people) == {ex, partner} for b in bonds):
                bonds.append(SocialBond("bond:" + fact.id, fact.people, Link.ACQUAINTANCES, fact.id, fact.minute))
    # A couple that broke up inside the story's own romantic events (one of them
    # moved on, a reconciliation was refused): the breakup stays sour for both,
    # in words only. Tone is drawn, never the role.
    sour_kinds = (EventKind.SEPARATION_ANNOUNCED, EventKind.RECONCILIATION_REFUSED,
                  EventKind.RELATIONSHIP_DISCLOSED, EventKind.REFUSAL_EXPRESSED, EventKind.DEMAND_MADE)
    for former in [b for b in bonds if b.kind is Link.EXES and roles.victim not in b.people]:
        x, y = former.people
        if any(e.kind in sour_kinds and {x, y} <= {e.actor, e.target} for e in world.events):
            fact = OrdinaryFact(f"breakup:{x}:{y}", (x, y), "sour_breakup",
                                former.since + 1 if former.since < -1 else -1440, rivalry.choice(("venom", "venom", "neutral")))
            ordinary.append(fact)
    return Life(crime, tuple(bonds), tuple(ordinary), tuple(messages), habits)
