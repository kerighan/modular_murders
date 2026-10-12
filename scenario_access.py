"""Next-day shifts, independent of last night's crime and culprit.

Positions are committed only at turn boundaries, never during a conversation.
"""
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class DayRoutine:
    person: str
    home: str
    workplace: str
    start: int
    end: int
    stops: tuple = ()

    def place_at(self, minute):
        if self.stops:
            return next(s.place for s in self.stops if s.start <= minute % 1440 < s.end)
        return self.workplace if self.start <= minute % 1440 < self.end else self.home

    def activity_at(self, minute):
        return next((s.activity for s in self.stops if s.start <= minute % 1440 < s.end), "chez soi")


@dataclass(frozen=True)
class DayStop:
    place: str
    start: int
    end: int
    activity: str


def daily_stops(streets, home, workplace, start, end, rng):
    """A complete, contiguous day. Every transition pays actual map travel time.

    Lunch, dinner and drinks are ordinary next-day life, never murder alibis.
    Randomness depends on identity/seed only, not on the criminal role.
    """
    stops = []

    def duration(a, b):
        path = streets.path(a, b)
        return sum(streets.duration(x, y) for x, y in zip(path, path[1:]))

    def stay(place, until, activity):
        at = stops[-1].end if stops else 0
        if until > at:
            stops.append(DayStop(place, at, until, activity))

    def move(a, b):
        path = streets.path(a, b)
        for origin, destination in zip(path, path[1:]):
            # A walking person is outside, never inside an apartment in transit.
            place = destination if streets.kind(destination).value == "street" else origin
            stay(place, stops[-1].end + streets.duration(origin, destination), "en chemin")

    stay(home, start - duration(home, workplace), "chez soi")
    move(home, workplace)
    lunch_place = rng.choice(("bar", "restaurant"))
    lunch = start + rng.choice((150, 180, 210))
    stay(workplace, lunch - duration(workplace, lunch_place), "au travail")
    move(workplace, lunch_place)
    stay(lunch_place, lunch + 45, "déjeune")
    move(lunch_place, workplace)
    stay(workplace, end, "au travail")
    move(workplace, home)
    for place, at, length, activity in (
        ("restaurant", rng.choice((18 * 60 + 30, 19 * 60)), 60, "dîne"),
        ("bar", rng.choice((20 * 60 + 30, 21 * 60)), 75, "prend un verre"),
    ):
        if rng.random() >= .65:
            continue
        stay(home, at - duration(home, place), "chez soi")
        move(home, place)
        stay(place, at + length, activity)
        move(place, home)
    stay(home, 1440, "chez soi")
    if stops[0].start != 0 or stops[-1].end != 1440 or any(
        a.end != b.start for a, b in zip(stops, stops[1:])
    ):
        raise ValueError("A contiguous next-day schedule is required")
    return tuple(stops)


def next_day_routines(case):
    rows = []
    for pid in sorted(case.plan.population):
        p = case.life.people[pid]
        rng = random.Random(f"day-routine-v1:{case.seed}:{pid}")
        start = rng.choice((8, 9, 10, 11)) * 60
        end = start + 6 * 60
        outings = random.Random(f"day-outings-v1:{case.seed}:{pid}")
        rows.append(DayRoutine(pid, p.home, p.workplace.value, start, end,
                               daily_stops(case.crime.streets, p.home, p.workplace.value, start, end, outings)))
    return tuple(rows)
