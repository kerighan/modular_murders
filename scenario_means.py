"""Preexisting objects, lawful access and inventory effects, separate from guilt.

No travel imports: the physical planner supplies and validates the walks.
Public inventory observations redact who moved objects and why.
"""
from dataclasses import dataclass
from types import MappingProxyType

from scenario_kernel import DAY, LabelledEnum


class Method(LabelledEnum):
    EDGED = "edged", "arme blanche"
    BLUNT = "blunt", "objet contondant"
    POISONED = "poisoned", "empoisonnement"


class ToolKind(LabelledEnum):
    KITCHEN_KNIFE = "kitchen_knife", "couteau de cuisine"
    HAMMER = "hammer", "marteau de bricolage"
    FICTIONAL_AGENT = "fictional_agent", "produit d'entretien"


METHOD_FOR_TOOL = MappingProxyType({ToolKind.KITCHEN_KNIFE: Method.EDGED, ToolKind.HAMMER: Method.BLUNT,
                                  ToolKind.FICTIONAL_AGENT: Method.POISONED})


class AcquisitionKind(LabelledEnum):
    OWNED = "owned", "objet personnel apporté"
    TAKEN = "taken", "objet pris dans un lieu avant la rencontre"
    BORROWED = "borrowed", "objet emprunté avant la rencontre"
    OPPORTUNISTIC = "opportunistic", "objet saisi en chemin après avoir aperçu la victime"


class TransferKind(LabelledEnum):
    ACQUISITION = "acquisition", "prise de l'objet utilisé"
    DISPOSITION = "disposition", "nouvel emplacement de l'objet"
    INNOCENT_LOAN = "innocent_loan", "emprunt ordinaire, sans lien avec le crime"


@dataclass(frozen=True)
class Tool:
    id: str
    kind: ToolKind
    owner: str  # person OR venue; ownership never silently changes on pickup
    place: str  # source stock / household
    available_since: int
    lawful_use: str
    access: tuple[str, ...] = ()
    pickup_point: str | None = None  # e.g. outdoor table on the venue's street

    @property
    def point(self):
        return self.pickup_point or self.place


def access_people(tool):
    return tool.access or (tool.owner,)


@dataclass(frozen=True)
class Keeper:
    id: str
    place: str
    name: str
    # Authoring presence intervals, not a simulated full day.
    shifts: tuple[tuple[int, int], ...] = ((8 * 60, 22 * 60), (DAY + 7 * 60, 2 * DAY - 1))

    def present_at(self, minute):
        return any(start <= minute <= end for start, end in self.shifts)


@dataclass(frozen=True)
class ToolTransfer:
    id: str
    tool: str
    actor: str
    minute: int
    origin: str
    destination: str
    kind: TransferKind
    permission_by: str | None = None


@dataclass(frozen=True)
class ToolState:
    tool: str
    place: str
    holder: str | None
    in_original_storage: bool
    concealed: bool = False


@dataclass(frozen=True)
class InventoryCheck:
    id: str
    place: str
    keeper: str
    kind: ToolKind
    observed_at: int
    expected: int
    present: int
    authorized_out: int
    transfers: tuple[str, ...]  # private provenance, not exposed to the detective

    @property
    def absent(self):
        return self.expected - self.present


def inventory_checks(inventory, keepers, transfers):
    """Count changed storage, including legitimate loans and dropped objects.

An object dropped on the same coarse street is NOT back in its original rack.
No check of private homes. Checks are authored on the following morning.
"""
    checks = []
    for keeper in keepers:
        for kind in ToolKind:
            stock = tuple(t for t in inventory if t.owner == keeper.place and t.kind is kind)
            removals = tuple(move for move in transfers if move.kind is not TransferKind.DISPOSITION
                             and any(t.id == move.tool for t in stock))
            if not removals:
                continue
            absent = len({move.tool for move in removals})
            authorized = len({move.tool for move in removals if move.permission_by == keeper.id})
            checks.append(InventoryCheck(f"stock:{keeper.place}:{kind.value}", keeper.place,
                                         keeper.id, kind, DAY + 8 * 60, len(stock), len(stock) - absent,
                                         authorized, tuple(move.id for move in removals)))
    return tuple(checks)


def inventory_observations(crime, *, place, discovered_at):
    """First small public projection, gated by place/time, not a solved case graph.

No exact taker, origin ids, weapon match, guilt or count of 'murder weapons'.
Candidate sets are access possibilities, NOT assertions of physical visits.
"""
    if type(discovered_at) is not int:
        raise TypeError("integer discovery time required")
    people = {p.id for p in crime.kernel.world.people} - {crime.kernel.roles.victim}
    rows = []
    for check in crime.inventory_checks:
        if check.place != place or check.observed_at > discovered_at:
            continue
        stock = [t for t in crime.inventory if t.owner == place and t.kind is check.kind]
        candidates = tuple(sorted(set().union(*(set(access_people(t)) for t in stock)) & people))
        if len(candidates) < 2:
            raise ValueError("Inventory artifact must remain compatible with at least two suspects")
        rows.append({"id": check.id, "place": place, "observer": check.keeper,
                     "kind": "inventory_absence", "object_kind": check.kind.value,
                     "expected": check.expected, "present": check.present,
                     "authorized_out": check.authorized_out, "candidates": list(candidates),
                     "text": inventory_text(check), "interpretation": "lead_not_proof"})
    return tuple(rows)


def inventory_text(check):
    objects = {ToolKind.KITCHEN_KNIFE: "couteau", ToolKind.HAMMER: "marteau",
               ToolKind.FICTIONAL_AGENT: "flacon"}[check.kind]
    suffix = "x" if objects == "couteau" and check.absent > 1 else "s" if check.absent > 1 else ""
    count = f"{check.absent} {objects}{suffix}"
    if check.kind is ToolKind.FICTIONAL_AGENT:
        count += " de produit d'entretien"
    text = f"À l'inventaire, il manque {count}."
    if check.authorized_out:
        lent = "un" if check.authorized_out == 1 else str(check.authorized_out)
        text += f" On en a prêté {lent}."
        if check.absent > check.authorized_out:
            text += " Pour le reste, je n'ai pas de prêt noté."
    else:
        text += " Je n'ai pas de prêt noté pour ça."
    return text
