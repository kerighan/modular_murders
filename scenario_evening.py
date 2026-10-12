"""Personal accounts of authored evening facts, distinct from corroboration.

Ordinary episodes fit BEFORE all constrained movements; they never supply a
whole-evening alibi. A suspect's own account cannot eliminate anybody.
"""
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class EveningEpisode:
    id: str
    person: str
    place: str
    start: int
    end: int
    activity: str


@dataclass(frozen=True)
class VenueRegistration:
    id: str
    person: str
    place: str
    keeper: str
    minute: int


def build_registrations(crime):
    """An authored arrival register, not presence magically granting memory."""
    rows = tuple(VenueRegistration("registration:" + v.person, v.person, v.place,
                 k.id, v.arrival.times[-1]) for v in crime.venue_presences
                 for k in crime.keepers if k.place == v.place and k.present_at(v.arrival.times[-1]))
    validate_registrations(crime, rows)
    return rows


def validate_registrations(crime, rows):
    if len({r.id for r in rows}) != len(rows):
        raise ValueError("Unique venue registrations")
    for r in rows:
        if not any(v.person == r.person and v.place == r.place and v.arrival.times[-1] == r.minute
                   for v in crime.venue_presences) or not any(k.id == r.keeper and k.place == r.place
                   and k.present_at(r.minute) for k in crime.keepers):
            raise ValueError("Registration requires an actual visit and a keeper on shift")


def physical_schedule(crime, evidence):
    x = crime.execution
    walks = [x.preparation, x.approach, x.victim_walk, x.following, x.escape]
    walks.extend(w for b in crime.mundane_borrowings for w in (b.outbound, b.inbound))
    walks.extend(v.arrival for v in crime.venue_presences)
    rows = [(w.person, place, at, at) for w in walks
            for place, at in zip(w.nodes, w.times) if at >= 0]
    rows.extend((p.person, p.place, p.start, p.end) for p in evidence.presences)
    rows.extend((v.person, v.place, v.arrival.times[-1], v.until) for v in crime.venue_presences)
    appointment = crime.victim_plan.appointment
    if appointment:
        rows.append((appointment.host, crime.victim_plan.destination,
                     appointment.host_present_from, appointment.host_present_until))
    rows.extend((t.actor, t.origin, t.minute, t.minute) for t in crime.transfers if t.minute >= 0)
    return tuple(rows)


def validate_evenings(crime, evidence, episodes):
    people = {p.id: p for p in crime.kernel.world.people}
    population = people.keys() - {crime.kernel.roles.victim}
    if {r.person for r in episodes} != population or len(episodes) != len(population):
        raise ValueError("One personal evening episode per suspect")
    schedule = physical_schedule(crime, evidence)
    for r in episodes:
        if (r.place != people[r.person].home or not 0 <= r.start < r.end < 1440
                or not r.activity or r.id != "evening_episode:" + r.person):
            raise ValueError("Concrete bounded domestic episode")
        for person, place, start, end in schedule:
            if person != r.person:
                continue
            path = crime.streets.path(r.place, place)
            duration = sum(crime.streets.duration(a, b) for a, b in zip(path, path[1:]))
            if r.end + duration > start:
                raise ValueError("Personal evening contradicts the physical schedule")


def build_evenings(crime, evidence, seed):
    schedule = physical_schedule(crime, evidence)
    streets = crime.streets

    def home_until(person):
        """At home until it is time to leave for one's own first evening commitment."""
        rows = [(start, place) for who, place, start, _ in schedule if who == person.id and start >= 0]
        if not rows:
            return 22 * 60
        start, place = min(rows)
        path = streets.path(person.home, place)
        travel = sum(streets.duration(a, b) for a, b in zip(path, path[1:]))
        return max(40, ((start - travel - 10) // 15) * 15)
    episodes = []
    activities = ["j'ai préparé quelque chose à manger.",
                  "j'ai écouté un vieux disque, j'avais besoin de décompresser.",
                  "j'ai fait un peu de rangement, rien de passionnant.",
                  "j'ai lu quelques pages sans arriver à me concentrer.",
                  "j'ai essayé de réparer ma vieille radio, elle grésille toujours.",
                  "j'ai trié des photos, j'ai retrouvé de vieux souvenirs.",
                  "j'ai fait une lessive, j'avais laissé le linge s'accumuler.",
                  "j'ai écouté la pluie, je n'avais pas envie de sortir tout de suite."]
    random.Random(f"evening-activities-v2:{seed}").shuffle(activities)
    for person in sorted(crime.kernel.world.people, key=lambda p: p.id):
        if person.id == crime.kernel.roles.victim:
            continue
        end = home_until(person)
        episodes.append(EveningEpisode("evening_episode:" + person.id, person.id,
                                      person.home, end - 20, end, activities[len(episodes) % len(activities)]))
    validate_evenings(crime, evidence, episodes)
    return tuple(episodes)


def spoken_time(minute):
    """Human clock landmarks, not a recollection accurate to five minutes."""
    hour, part = (minute // 60) % 24, minute % 60
    if part == 0:
        return f"{hour} h"
    if part == 15:
        return f"{hour} h et quart"
    if part == 30:
        return f"{hour} h et demie"
    if part == 45:
        return f"{(hour + 1) % 24} h moins le quart"
    raise ValueError("A remembered clock landmark must be a quarter-hour")


def remembered_times(presence):
    """Keep only an interior quarter-hour interval, never invent coverage.

    For the short poison observation, the credible memory is an event sequence
    (drink served -> collapse), not an exact pair of clock readings.
    """
    if presence.basis in ("continuous_noncontact", "on_site"):
        return {}
    start, end = ((presence.start + 14) // 15) * 15, (presence.end // 15) * 15
    if start > end:
        return {}
    return {"start": start, "end": end}


def evening_account(crime, evidence, episodes, pid):
    """One chronological story: at home until a landmark, then where the evening went."""
    episode = next(r for r in episodes if r.person == pid)
    labels = {n.id: n.label for n in crime.streets.nodes}
    def at_place(place):
        label = labels[place]
        return "au " + label[3:] if label.startswith("Le ") else "à " + label
    until = spoken_time((episode.end // 15) * 15)
    activity = episode.activity[0].upper() + episode.activity[1:]  # no digital clock, no colon: spoken landmarks only
    presence = next((p for p in evidence.presences if p.person == pid), None)
    if presence:
        keeper = next(k for k in crime.keepers if k.id == presence.witness)
        times = remembered_times(presence)
        when = f", entre {spoken_time(times['start'])} et {spoken_time(times['end'])}" if times else ", une partie de la soirée"
        return (f"Jusqu'à {until}, j'étais chez moi. {activity}\n"
                f"Ensuite, j'étais {at_place(presence.place)}{when}. {keeper.name} était de service ; il m'a vu à ma table.")
    venue = next((v for v in crime.venue_presences if v.person == pid), None)
    if venue:
        return f"Jusqu'à {until}, j'étais chez moi. {activity}\nEnsuite, je suis passé {at_place(venue.place)}. Il y avait du monde."
    borrowing = next((b for b in crime.mundane_borrowings if b.actor == pid), None)
    if borrowing:
        place = at_place(borrowing.outbound.nodes[-1])
        return f"Dans la journée, je suis passé {place} chercher un objet qu'on m'avait prêté.\nLe soir, je suis resté chez moi. {activity}"
    return f"Je suis resté chez moi toute la soirée. {activity}"
