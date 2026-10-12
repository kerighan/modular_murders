"""Typed encounter facts: how actors meet, distinct from motive and method.

Fictional poisoning is an authoring mechanic, never a recipe or real substance.
Travel and co-presence are checked by scenario_crime, not by narrative labels.
"""
from dataclasses import dataclass

from scenario_kernel import LabelledEnum


class SituationKind(LabelledEnum):
    TRACKING = "tracking", "repérage à la sortie du travail et suivi"
    AGREED_MEETING = "agreed_meeting", "rendez-vous accepté pour discuter du conflit"
    VENUE = "venue", "rencontre au cours d'une sortie au bar ou au restaurant"


@dataclass(frozen=True)
class VenuePresence:
    person: str
    place: str
    arrival: "Walk"
    until: int
    purpose: str


@dataclass(frozen=True)
class DrinkExposure:
    id: str
    recipient: str
    place: str
    served_by: str
    served_at: int
    altered_at: int
    effect_at: int
    access_people: tuple[str, ...]
    # No real chemical, quantity or procedure. Exact perpetrator stays in truth.


def situation_fingerprint(crime):
    """Structural axes for authoring audits; names alone never add diversity."""
    plan, execution = crime.victim_plan, crime.execution
    return (crime.kernel.premise.motive.value, execution.situation.value,
            plan.goal.value, execution.method.value, execution.acquisition.value,
            execution.tool_fate.value)


def venue_observations(crime, *, place, discovered_at):
    """Small public artifact, not a diagnosis or an attribution of poisoning.

The preserved scene glass is a lead for future analysis. No real substance,
perpetrator, exact alteration time or departing person's time is disclosed.
"""
    if type(discovered_at) is not int:
        raise TypeError("integer discovery time required")
    exposure = crime.execution.exposure
    if exposure is None or exposure.place != place or discovered_at < exposure.effect_at:
        return ()
    candidates = exposure.access_people
    if len(set(candidates)) < 2:
        raise ValueError("Drink artifact must retain at least two access possibilities")
    return ({"id": exposure.id, "kind": "scene_drink", "place": place,
             "candidates": list(candidates), "interpretation": "lead_not_proof",
             "text": "Le verre servi à la victime est resté sur la table. Plusieurs personnes ont pu s'en approcher. Rien ne permet encore de dire ce qu'il contient."},)
