"""Experimental causal sampler: motive -> context -> concrete stake.

This authored grammar is NOT a universal criminological classification. A pair
can be unsupported even if a more elaborate story could make it plausible.
The catalogue defines obligations, not actual actors or clues. CLI steps 4–7
delegate to the private kernel, physical execution, discovery and witnesses.
Game/CaseStory does not use this prototype; existing games/RNGs are unchanged.

Run: python scenario_sampler.py --seed 42 --count 10
     python scenario_sampler.py --catalogue
"""
import argparse
import json
import random
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType


CATALOGUE_VERSION = 2


class Motive(Enum):
    ACQUIRE = "acquire"
    AVOID_LOSS = "avoid_loss"
    SILENCE = "silence"
    REMOVE_OBSTACLE = "remove_obstacle"
    CONTROL = "control"
    REVENGE = "revenge"
    REMOVE_THREAT = "remove_threat"
    PREDATION = "predation"
    CONVICTION = "conviction"


class Context(Enum):
    WORK = "work"
    FAMILY = "family"
    ROMANCE = "romance"
    NEIGHBORHOOD = "neighborhood"
    CRIMINAL_WORLD = "criminal_world"
    COMMUNITY = "community"
    CHANCE_ENCOUNTER = "chance_encounter"


class _LabelledEnum(Enum):
    def __new__(cls, code, label):
        member = object.__new__(cls)
        member._value_ = code
        member.label = label
        return member


class Stake(_LabelledEnum):
    CASH = "cash", "Argent détenu par la victime"
    VALUABLE = "valuable", "Objet de valeur"
    INHERITANCE = "inheritance", "Héritage"
    PROPERTY = "property", "Bien immobilier ou partagé"
    DEBT = "debt", "Dette à régler"
    HOUSING = "housing", "Logement menacé ou convoité"
    JOB = "job", "Emploi menacé ou convoité"
    CONTRACT = "contract", "Contrat menacé ou convoité"
    ARTISTIC_ROLE = "artistic_role", "Rôle artistique convoité"
    POWER_POSITION = "power_position", "Position de pouvoir convoitée"
    FRAUD = "fraud", "Fraude"
    EXPLOITATION = "exploitation", "Exploitation de personnes"
    PERSONAL_SECRET = "personal_secret", "Secret personnel"
    AFFAIR = "affair", "Liaison dissimulée"
    PAST_CRIME = "past_crime", "Crime antérieur"
    ROMANTIC_RIVAL = "romantic_rival", "Rivalité sentimentale"
    SEPARATION = "separation", "Séparation annoncée"
    DEPARTURE = "departure", "Départ annoncé"
    REFUSAL = "refusal", "Refus de se soumettre"
    HUMILIATION = "humiliation", "Humiliation antérieure"
    BETRAYAL = "betrayal", "Trahison antérieure"
    HARM_TO_RELATIVE = "harm_to_relative", "Tort fait à un proche"
    SELF_SAFETY = "self_safety", "Sécurité de l'auteur"
    RELATIVE_SAFETY = "relative_safety", "Sécurité d'un proche"
    VIOLENCE = "violence", "Violence recherchée pour elle-même"
    DOMINATION = "domination", "Domination recherchée pour elle-même"
    IDEOLOGICAL_OPPOSITION = "ideological_opposition", "Opposition de convictions"
    REPRESENTED_IDENTITY = "represented_identity", "Identité que l'auteur prend pour cible"


class RequiredFact(_LabelledEnum):
    """Unbound obligations, NOT assertions about actual people or player proof.

    Future world-building must supply actors/resources/events and verify these
    predicates. An enum token on its own is not sufficient to establish a fact.
    """
    WORK_LINK = "work_link", "Un lien professionnel relie les enjeux des acteurs."
    FAMILY_LINK = "family_link", "Un lien familial relie les acteurs."
    ROMANTIC_LINK = "romantic_link", "Une histoire sentimentale relie les enjeux des acteurs."
    NEIGHBOR_LINK = "neighbor_link", "Un espace partagé ou le voisinage relie les acteurs."
    CRIMINAL_LINK = "criminal_link", "Une activité criminelle relie les enjeux des acteurs."
    COMMUNITY_LINK = "community_link", "Un collectif relie les enjeux des acteurs."
    NO_SHARED_HISTORY = "no_shared_history", "Les acteurs n'ont pas d'histoire commune avant la rencontre."
    VICTIM_CONTROLS_RESOURCE = "victim_controls_resource", "La victime contrôle la ressource visée."
    AUTHOR_WANTS_RESOURCE = "author_wants_resource", "L'auteur veut s'approprier cette ressource."
    LOSS_EXPECTED = "loss_expected", "L'auteur anticipe une perte ou une obligation concrète."
    VICTIM_CAN_CAUSE_LOSS = "victim_can_cause_loss", "La victime peut provoquer cette perte ou faire valoir cette obligation."
    VICTIM_KNOWS_SECRET = "victim_knows_secret", "La victime détient l'information compromettante."
    DISCLOSURE_POSSIBLE = "disclosure_possible", "La victime peut transmettre cette information."
    DISCLOSURE_FEARED = "disclosure_feared", "L'auteur craint les conséquences de cette divulgation."
    AUTHOR_HAS_GOAL = "author_has_goal", "L'auteur poursuit un objectif concret."
    VICTIM_BLOCKS_GOAL = "victim_blocks_goal", "La victime fait obstacle à cet objectif."
    PRIOR_CONTROL = "prior_control", "Une emprise préexiste au crime."
    VICTIM_SEEKS_AUTONOMY = "victim_seeks_autonomy", "La victime tente de s'affranchir de cette emprise."
    AUTONOMY_REJECTED = "autonomy_rejected", "L'auteur refuse cette autonomie."
    PRIOR_HARM = "prior_harm", "Un tort antérieur existe."
    AUTHOR_BLAMES_VICTIM = "author_blames_victim", "L'auteur attribue ce tort à la victime."
    RETRIBUTION_WANTED = "retribution_wanted", "L'auteur veut lui faire payer ce tort."
    THREAT_PERCEIVED = "threat_perceived", "L'auteur perçoit une menace concrète."
    VICTIM_SEEN_AS_THREAT = "victim_seen_as_threat", "L'auteur considère la victime comme la source de cette menace."
    ACT_SOUGHT = "act_sought", "L'auteur recherche l'acte lui-même, sans conflit personnel nécessaire."
    CONVICTION_HELD = "conviction_held", "L'auteur agit au nom d'une conviction."
    VICTIM_REPRESENTS_OPPOSITION = "victim_represents_opposition", "La victime représente ce que l'auteur combat."
    DEATH_EXPECTED_TO_SERVE_GOAL = "death_expected_to_serve_goal", "L'auteur estime que la mort de la victime sert son objectif."
    CASH_EXISTS = "cash_exists", "Une somme d'argent détenue par la victime existe."
    VALUABLE_EXISTS = "valuable_exists", "Un objet de valeur précis existe."
    ESTATE_EXISTS = "estate_exists", "Un patrimoine et ses bénéficiaires potentiels sont à définir."
    PROPERTY_EXISTS = "property_exists", "Un bien et ses droits de propriété sont à définir."
    DEBT_EXISTS = "debt_exists", "Une dette, un débiteur et un créancier sont à définir."
    HOUSING_EXISTS = "housing_exists", "Un logement et ses occupants sont à définir."
    JOB_EXISTS = "job_exists", "Un emploi et son employeur sont à définir."
    CONTRACT_EXISTS = "contract_exists", "Un contrat et ses parties sont à définir."
    ROLE_EXISTS = "role_exists", "Un rôle artistique et son attribution sont à définir."
    POSITION_EXISTS = "position_exists", "Une position de pouvoir et son attribution sont à définir."
    FRAUD_EXISTS = "fraud_exists", "Une fraude concrète et ses participants sont à définir."
    EXPLOITATION_EXISTS = "exploitation_exists", "Une situation d'exploitation et les personnes concernées sont à définir."
    SECRET_EXISTS = "secret_exists", "Un secret précis existe."
    AFFAIR_EXISTS = "affair_exists", "Une liaison dissimulée et ses participants sont à définir."
    PAST_CRIME_EXISTS = "past_crime_exists", "Un crime antérieur existe."
    ROMANTIC_RIVAL_EXISTS = "romantic_rival_exists", "Une rivalité sentimentale implique une troisième personne."
    SEPARATION_ANNOUNCED = "separation_announced", "La victime a annoncé une séparation."
    DEPARTURE_ANNOUNCED = "departure_announced", "La victime a annoncé son départ."
    REFUSAL_EXPRESSED = "refusal_expressed", "La victime a exprimé un refus."
    HUMILIATION_OCCURRED = "humiliation_occurred", "Une humiliation antérieure et son contexte sont à définir."
    BETRAYAL_OCCURRED = "betrayal_occurred", "Une trahison antérieure et son contexte sont à définir."
    RELATIVE_HARMED = "relative_harmed", "Un proche a subi un tort."
    SELF_THREATENED = "self_threatened", "La menace perçue concerne la sécurité de l'auteur."
    RELATIVE_THREATENED = "relative_threatened", "La menace perçue concerne la sécurité d'un proche."
    VIOLENCE_DESIRED = "violence_desired", "La violence est recherchée comme une fin."
    DOMINATION_DESIRED = "domination_desired", "La domination est recherchée comme une fin."
    IDEOLOGICAL_DISAGREEMENT = "ideological_disagreement", "Une opposition de convictions est à définir."
    IDENTITY_TARGETED = "identity_targeted", "L'auteur cible une identité qu'il attribue à la victime."


@dataclass(frozen=True)
class MotiveRule:
    label: str
    contexts: tuple[Context, ...]
    # Human authoring summary. The typed contract below remains unbound:
    # neither the summary nor enum tokens establish facts in a real world.
    premise: str


@dataclass(frozen=True)
class ContextDescription:
    label: str
    short_label: str
    meaning: str


CONTEXTS = MappingProxyType({
    Context.WORK: ContextDescription("Professionnel", "Travail", "Une activité professionnelle relie les enjeux des acteurs."),
    Context.FAMILY: ContextDescription("Familial", "Famille", "Une relation familiale relie les acteurs."),
    Context.ROMANCE: ContextDescription("Amoureux", "Amour", "Une relation amoureuse, passée ou présente, relie les enjeux des acteurs."),
    Context.NEIGHBORHOOD: ContextDescription("Voisinage", "Voisins", "La cohabitation ou un espace partagé relie les acteurs."),
    Context.CRIMINAL_WORLD: ContextDescription("Milieu criminel", "Milieu", "Une activité criminelle relie les enjeux des acteurs."),
    Context.COMMUNITY: ContextDescription("Collectif", "Collectif", "Une association, un groupe ou une institution relie les enjeux des acteurs."),
    Context.CHANCE_ENCOUNTER: ContextDescription("Rencontre fortuite", "Rencontre", "Le crime naît de la rencontre, sans histoire commune préalable."),
})


# Enum values determine the legal domain, not just the text displayed afterwards.
# The broad families allow several contexts; narrower ones constrain the branch.
# Explicit membership makes extending either enum fail closed until authored.
RULES = MappingProxyType({
    Motive.ACQUIRE: MotiveRule("S'approprier quelque chose", (
        Context.WORK, Context.FAMILY, Context.ROMANCE, Context.NEIGHBORHOOD,
        Context.CRIMINAL_WORLD, Context.COMMUNITY, Context.CHANCE_ENCOUNTER,
    ), "La victime détient une ressource que l'auteur veut obtenir ; la violence doit servir cette appropriation."),
    Motive.AVOID_LOSS: MotiveRule("Éviter une perte ou une obligation", (
        Context.WORK, Context.FAMILY, Context.ROMANCE, Context.NEIGHBORHOOD,
        Context.CRIMINAL_WORLD, Context.COMMUNITY,
    ), "Une obligation ou une perte identifiable préexiste au crime ; l'auteur croit pouvoir l'éviter par la mort de la victime."),
    Motive.SILENCE: MotiveRule("Empêcher une révélation", (
        Context.WORK, Context.FAMILY, Context.ROMANCE, Context.NEIGHBORHOOD,
        Context.CRIMINAL_WORLD, Context.COMMUNITY, Context.CHANCE_ENCOUNTER,
    ), "La victime détient une information compromettante ; l'auteur craint qu'elle la divulgue. Elle peut être un témoin fortuit."),
    Motive.REMOVE_OBSTACLE: MotiveRule("Éliminer un obstacle ou un rival", (
        Context.WORK, Context.FAMILY, Context.ROMANCE, Context.NEIGHBORHOOD,
        Context.CRIMINAL_WORLD, Context.COMMUNITY,
    ), "Un objectif préexiste au crime ; la victime en bloque l'accès et sa disparition doit lever cet obstacle."),
    Motive.CONTROL: MotiveRule("Maintenir une emprise", (
        Context.WORK, Context.FAMILY, Context.ROMANCE, Context.CRIMINAL_WORLD,
    ), "Une emprise préexiste au crime ; la victime tente de s'y soustraire et l'auteur refuse cette autonomie."),
    Motive.REVENGE: MotiveRule("Punir ou se venger", (
        Context.WORK, Context.FAMILY, Context.ROMANCE, Context.NEIGHBORHOOD,
        Context.CRIMINAL_WORLD, Context.COMMUNITY,
    ), "Un tort antérieur est attribué à la victime ; l'auteur veut le lui faire payer. Cette grammaire exclut la simple altercation fortuite."),
    Motive.REMOVE_THREAT: MotiveRule("Supprimer une menace perçue", (
        Context.WORK, Context.FAMILY, Context.ROMANCE, Context.NEIGHBORHOOD,
        Context.CRIMINAL_WORLD, Context.COMMUNITY, Context.CHANCE_ENCOUNTER,
    ), "L'auteur perçoit une menace contre lui ou un proche et décide de supprimer sa source ; cela ne présume pas une légitime défense."),
    Motive.PREDATION: MotiveRule("Rechercher la violence ou la domination", (
        Context.CHANCE_ENCOUNTER,
    ), "L'acte lui-même est recherché. Cette grammaire couvre la rencontre sans histoire commune ; la répétition sera un axe distinct."),
    Motive.CONVICTION: MotiveRule("Agir au nom d'une conviction", (
        Context.COMMUNITY, Context.CHANCE_ENCOUNTER,
    ), "La victime représente ce que l'auteur combat. Cette grammaire couvre le contexte collectif et une cible rencontrée fortuitement."),
})


# The third domain is authored per PAIR, not an independent list of stakes.
# An affair is possible for romantic revenge, but not for workplace theft;
# separation is possible for romantic control, but not for acquiring a resource.
STAKE_BRANCHES = MappingProxyType({
    (Motive.ACQUIRE, Context.WORK): (Stake.CASH, Stake.VALUABLE),
    (Motive.ACQUIRE, Context.FAMILY): (Stake.CASH, Stake.VALUABLE, Stake.INHERITANCE, Stake.PROPERTY),
    (Motive.ACQUIRE, Context.ROMANCE): (Stake.CASH, Stake.VALUABLE, Stake.PROPERTY),
    (Motive.ACQUIRE, Context.NEIGHBORHOOD): (Stake.CASH, Stake.VALUABLE, Stake.PROPERTY),
    (Motive.ACQUIRE, Context.CRIMINAL_WORLD): (Stake.CASH, Stake.VALUABLE),
    (Motive.ACQUIRE, Context.COMMUNITY): (Stake.CASH, Stake.VALUABLE, Stake.PROPERTY),
    (Motive.ACQUIRE, Context.CHANCE_ENCOUNTER): (Stake.CASH, Stake.VALUABLE),
    (Motive.AVOID_LOSS, Context.WORK): (Stake.DEBT, Stake.JOB, Stake.CONTRACT),
    (Motive.AVOID_LOSS, Context.FAMILY): (Stake.INHERITANCE, Stake.PROPERTY, Stake.DEBT),
    (Motive.AVOID_LOSS, Context.ROMANCE): (Stake.PROPERTY, Stake.DEBT),
    (Motive.AVOID_LOSS, Context.NEIGHBORHOOD): (Stake.DEBT, Stake.HOUSING),
    (Motive.AVOID_LOSS, Context.CRIMINAL_WORLD): (Stake.DEBT, Stake.CONTRACT),
    (Motive.AVOID_LOSS, Context.COMMUNITY): (Stake.PROPERTY, Stake.DEBT, Stake.CONTRACT),
    (Motive.SILENCE, Context.WORK): (Stake.FRAUD, Stake.EXPLOITATION, Stake.PAST_CRIME),
    (Motive.SILENCE, Context.FAMILY): (Stake.FRAUD, Stake.PERSONAL_SECRET, Stake.PAST_CRIME),
    (Motive.SILENCE, Context.ROMANCE): (Stake.PERSONAL_SECRET, Stake.AFFAIR, Stake.PAST_CRIME),
    (Motive.SILENCE, Context.NEIGHBORHOOD): (Stake.FRAUD, Stake.PAST_CRIME),
    (Motive.SILENCE, Context.CRIMINAL_WORLD): (Stake.FRAUD, Stake.PAST_CRIME),
    (Motive.SILENCE, Context.COMMUNITY): (Stake.FRAUD, Stake.EXPLOITATION, Stake.PERSONAL_SECRET),
    (Motive.SILENCE, Context.CHANCE_ENCOUNTER): (Stake.FRAUD, Stake.PAST_CRIME),
    (Motive.REMOVE_OBSTACLE, Context.WORK): (Stake.JOB, Stake.CONTRACT, Stake.ARTISTIC_ROLE),
    (Motive.REMOVE_OBSTACLE, Context.FAMILY): (Stake.INHERITANCE, Stake.PROPERTY),
    (Motive.REMOVE_OBSTACLE, Context.ROMANCE): (Stake.ROMANTIC_RIVAL,),
    (Motive.REMOVE_OBSTACLE, Context.NEIGHBORHOOD): (Stake.PROPERTY, Stake.HOUSING),
    (Motive.REMOVE_OBSTACLE, Context.CRIMINAL_WORLD): (Stake.CONTRACT, Stake.POWER_POSITION),
    (Motive.REMOVE_OBSTACLE, Context.COMMUNITY): (Stake.CONTRACT, Stake.POWER_POSITION),
    (Motive.CONTROL, Context.WORK): (Stake.DEPARTURE, Stake.REFUSAL),
    (Motive.CONTROL, Context.FAMILY): (Stake.DEPARTURE, Stake.REFUSAL),
    (Motive.CONTROL, Context.ROMANCE): (Stake.SEPARATION, Stake.REFUSAL),
    (Motive.CONTROL, Context.CRIMINAL_WORLD): (Stake.DEPARTURE, Stake.REFUSAL),
    (Motive.REVENGE, Context.WORK): (Stake.FRAUD, Stake.HUMILIATION, Stake.BETRAYAL),
    (Motive.REVENGE, Context.FAMILY): (Stake.BETRAYAL, Stake.HARM_TO_RELATIVE),
    (Motive.REVENGE, Context.ROMANCE): (Stake.AFFAIR, Stake.HUMILIATION, Stake.BETRAYAL),
    (Motive.REVENGE, Context.NEIGHBORHOOD): (Stake.HUMILIATION, Stake.HARM_TO_RELATIVE),
    (Motive.REVENGE, Context.CRIMINAL_WORLD): (Stake.BETRAYAL, Stake.HARM_TO_RELATIVE),
    (Motive.REVENGE, Context.COMMUNITY): (Stake.HUMILIATION, Stake.BETRAYAL),
    (Motive.REMOVE_THREAT, Context.WORK): (Stake.SELF_SAFETY, Stake.RELATIVE_SAFETY),
    (Motive.REMOVE_THREAT, Context.FAMILY): (Stake.SELF_SAFETY, Stake.RELATIVE_SAFETY),
    (Motive.REMOVE_THREAT, Context.ROMANCE): (Stake.SELF_SAFETY, Stake.RELATIVE_SAFETY),
    (Motive.REMOVE_THREAT, Context.NEIGHBORHOOD): (Stake.SELF_SAFETY, Stake.RELATIVE_SAFETY),
    (Motive.REMOVE_THREAT, Context.CRIMINAL_WORLD): (Stake.SELF_SAFETY, Stake.RELATIVE_SAFETY),
    (Motive.REMOVE_THREAT, Context.COMMUNITY): (Stake.SELF_SAFETY, Stake.RELATIVE_SAFETY),
    (Motive.REMOVE_THREAT, Context.CHANCE_ENCOUNTER): (Stake.SELF_SAFETY, Stake.RELATIVE_SAFETY),
    (Motive.PREDATION, Context.CHANCE_ENCOUNTER): (Stake.VIOLENCE, Stake.DOMINATION),
    (Motive.CONVICTION, Context.COMMUNITY): (Stake.IDEOLOGICAL_OPPOSITION, Stake.REPRESENTED_IDENTITY),
    (Motive.CONVICTION, Context.CHANCE_ENCOUNTER): (Stake.REPRESENTED_IDENTITY,),
})

CONTEXT_FACTS = MappingProxyType({
    Context.WORK: RequiredFact.WORK_LINK,
    Context.FAMILY: RequiredFact.FAMILY_LINK,
    Context.ROMANCE: RequiredFact.ROMANTIC_LINK,
    Context.NEIGHBORHOOD: RequiredFact.NEIGHBOR_LINK,
    Context.CRIMINAL_WORLD: RequiredFact.CRIMINAL_LINK,
    Context.COMMUNITY: RequiredFact.COMMUNITY_LINK,
    Context.CHANCE_ENCOUNTER: RequiredFact.NO_SHARED_HISTORY,
})

MOTIVE_FACTS = MappingProxyType({
    Motive.ACQUIRE: (RequiredFact.VICTIM_CONTROLS_RESOURCE, RequiredFact.AUTHOR_WANTS_RESOURCE),
    Motive.AVOID_LOSS: (RequiredFact.LOSS_EXPECTED, RequiredFact.VICTIM_CAN_CAUSE_LOSS),
    Motive.SILENCE: (RequiredFact.VICTIM_KNOWS_SECRET, RequiredFact.DISCLOSURE_POSSIBLE, RequiredFact.DISCLOSURE_FEARED),
    Motive.REMOVE_OBSTACLE: (RequiredFact.AUTHOR_HAS_GOAL, RequiredFact.VICTIM_BLOCKS_GOAL),
    Motive.CONTROL: (RequiredFact.PRIOR_CONTROL, RequiredFact.VICTIM_SEEKS_AUTONOMY, RequiredFact.AUTONOMY_REJECTED),
    Motive.REVENGE: (RequiredFact.PRIOR_HARM, RequiredFact.AUTHOR_BLAMES_VICTIM, RequiredFact.RETRIBUTION_WANTED),
    Motive.REMOVE_THREAT: (RequiredFact.THREAT_PERCEIVED, RequiredFact.VICTIM_SEEN_AS_THREAT),
    Motive.PREDATION: (RequiredFact.ACT_SOUGHT,),
    Motive.CONVICTION: (RequiredFact.CONVICTION_HELD, RequiredFact.VICTIM_REPRESENTS_OPPOSITION),
})

STAKE_FACTS = MappingProxyType({
    Stake.CASH: RequiredFact.CASH_EXISTS,
    Stake.VALUABLE: RequiredFact.VALUABLE_EXISTS,
    Stake.INHERITANCE: RequiredFact.ESTATE_EXISTS,
    Stake.PROPERTY: RequiredFact.PROPERTY_EXISTS,
    Stake.DEBT: RequiredFact.DEBT_EXISTS,
    Stake.HOUSING: RequiredFact.HOUSING_EXISTS,
    Stake.JOB: RequiredFact.JOB_EXISTS,
    Stake.CONTRACT: RequiredFact.CONTRACT_EXISTS,
    Stake.ARTISTIC_ROLE: RequiredFact.ROLE_EXISTS,
    Stake.POWER_POSITION: RequiredFact.POSITION_EXISTS,
    Stake.FRAUD: RequiredFact.FRAUD_EXISTS,
    Stake.EXPLOITATION: RequiredFact.EXPLOITATION_EXISTS,
    Stake.PERSONAL_SECRET: RequiredFact.SECRET_EXISTS,
    Stake.AFFAIR: RequiredFact.AFFAIR_EXISTS,
    Stake.PAST_CRIME: RequiredFact.PAST_CRIME_EXISTS,
    Stake.ROMANTIC_RIVAL: RequiredFact.ROMANTIC_RIVAL_EXISTS,
    Stake.SEPARATION: RequiredFact.SEPARATION_ANNOUNCED,
    Stake.DEPARTURE: RequiredFact.DEPARTURE_ANNOUNCED,
    Stake.REFUSAL: RequiredFact.REFUSAL_EXPRESSED,
    Stake.HUMILIATION: RequiredFact.HUMILIATION_OCCURRED,
    Stake.BETRAYAL: RequiredFact.BETRAYAL_OCCURRED,
    Stake.HARM_TO_RELATIVE: RequiredFact.RELATIVE_HARMED,
    Stake.SELF_SAFETY: RequiredFact.SELF_THREATENED,
    Stake.RELATIVE_SAFETY: RequiredFact.RELATIVE_THREATENED,
    Stake.VIOLENCE: RequiredFact.VIOLENCE_DESIRED,
    Stake.DOMINATION: RequiredFact.DOMINATION_DESIRED,
    Stake.IDEOLOGICAL_OPPOSITION: RequiredFact.IDEOLOGICAL_DISAGREEMENT,
    Stake.REPRESENTED_IDENTITY: RequiredFact.IDENTITY_TARGETED,
})


def validate_stake_catalogue():
    expected = {(m, c) for m in Motive for c in RULES[m].contexts}
    if set(STAKE_BRANCHES) != expected:
        raise ValueError("Every allowed pair needs exactly one explicit stake branch")
    if set(CONTEXT_FACTS) != set(Context) or set(MOTIVE_FACTS) != set(Motive) or set(STAKE_FACTS) != set(Stake):
        raise ValueError("Every enum member needs an explicit causal contract")
    reachable = set()
    for pair, stakes in STAKE_BRANCHES.items():
        if not stakes or any(type(stake) is not Stake for stake in stakes):
            raise ValueError(f"Invalid or empty stake branch: {pair}")
        if len(set(stakes)) != len(stakes):
            raise ValueError(f"Duplicate stake in branch: {pair}")
        if stakes != tuple(stake for stake in Stake if stake in stakes):
            raise ValueError(f"Non-canonical stake order: {pair}")
        reachable.update(stakes)
    if reachable != set(Stake):
        raise ValueError("Unreachable stake in catalogue")
    facts = [*CONTEXT_FACTS.values(), *STAKE_FACTS.values(), RequiredFact.DEATH_EXPECTED_TO_SERVE_GOAL]
    for requirements in MOTIVE_FACTS.values():
        if not requirements or len(set(requirements)) != len(requirements):
            raise ValueError("Empty or duplicate motive contract")
        facts.extend(requirements)
    if any(type(fact) is not RequiredFact for fact in facts) or set(facts) != set(RequiredFact):
        raise ValueError("Invalid or unreachable required fact")


def validate_catalogue():
    """Fail on enum extensions with missing/invalid rules, never silently allow."""
    if set(RULES) != set(Motive) or set(CONTEXTS) != set(Context):
        raise ValueError("Every enum member needs an explicit catalogue entry")
    reachable = set()
    for motive, rule in RULES.items():
        if not rule.label or not rule.premise or not rule.contexts:
            raise ValueError(f"Incomplete motive rule: {motive.value}")
        if len(set(rule.contexts)) != len(rule.contexts):
            raise ValueError(f"Duplicate allowed context: {motive.value}")
        if any(type(context) is not Context for context in rule.contexts):
            raise ValueError(f"Invalid context: {motive.value}")
        # Sampling order must follow enum order rather than a set/hash order.
        if rule.contexts != tuple(context for context in Context if context in rule.contexts):
            raise ValueError(f"Non-canonical context order: {motive.value}")
        reachable.update(rule.contexts)
    if reachable != set(Context):
        raise ValueError("Unreachable context in catalogue")
    validate_stake_catalogue()


validate_catalogue()


def _check_filters(motive, context):
    if motive is not None and type(motive) is not Motive:
        raise TypeError("motive must be a Motive enum member")
    if context is not None and type(context) is not Context:
        raise TypeError("context must be a Context enum member")


@dataclass(frozen=True)
class CrimeSeed:
    """Exactly two sampled dimensions; constructing a forbidden pair also fails."""
    motive: Motive
    context: Context

    def __post_init__(self):
        _check_filters(self.motive, self.context)
        if self.motive is None or self.context is None:
            raise TypeError("CrimeSeed requires both enum members")
        if self.context not in RULES[self.motive].contexts:
            raise ValueError(f"Unsupported V{CATALOGUE_VERSION} pair: {self.motive.value} / {self.context.value}")

    def as_dict(self):
        return {"motive": self.motive.value, "context": self.context.value}

    @classmethod
    def from_dict(cls, data):
        if set(data) != {"motive", "context"}:
            raise ValueError("CrimeSeed expects exactly motive and context")
        return cls(Motive(data["motive"]), Context(data["context"]))


def allowed_pairs(*, motive=None, context=None):
    """Enumerate the authored domain, optionally restricted, in stable order."""
    _check_filters(motive, context)
    return tuple(CrimeSeed(m, c) for m in Motive for c in RULES[m].contexts
                 if (motive is None or m is motive) and (context is None or c is context))


@dataclass(frozen=True)
class CrimePremise:
    """Three sampled dimensions; requirements are derived, not further draws."""
    motive: Motive
    context: Context
    stake: Stake

    def __post_init__(self):
        CrimeSeed(self.motive, self.context)
        if type(self.stake) is not Stake:
            raise TypeError("stake must be a Stake enum member")
        if self.stake not in STAKE_BRANCHES[self.motive, self.context]:
            raise ValueError(f"Unsupported V{CATALOGUE_VERSION} triple: {self.motive.value} / {self.context.value} / {self.stake.value}")

    @property
    def seed(self):
        return CrimeSeed(self.motive, self.context)

    @property
    def required_facts(self):
        facts = {*MOTIVE_FACTS[self.motive], CONTEXT_FACTS[self.context],
                 STAKE_FACTS[self.stake], RequiredFact.DEATH_EXPECTED_TO_SERVE_GOAL}
        return tuple(fact for fact in RequiredFact if fact in facts)

    def as_dict(self):
        return {**self.seed.as_dict(), "stake": self.stake.value}

    @classmethod
    def from_dict(cls, data):
        if set(data) != {"motive", "context", "stake"}:
            raise ValueError("CrimePremise expects exactly motive, context and stake")
        return cls(Motive(data["motive"]), Context(data["context"]), Stake(data["stake"]))


def allowed_premises(*, motive=None, context=None, stake=None):
    if stake is not None and type(stake) is not Stake:
        raise TypeError("stake must be a Stake enum member")
    return tuple(CrimePremise(pair.motive, pair.context, s)
                 for pair in allowed_pairs(motive=motive, context=context)
                 for s in STAKE_BRANCHES[pair.motive, pair.context] if stake is None or s is stake)


class ScenarioSampler:
    """Uniform motive, then uniform allowed context, with a private RNG.

    Uniform *pairs* would favour motives supporting more contexts. If the
    context is pinned, choose uniformly among motives supporting that context.
    This is an authoring/exploration policy, not real-world crime frequencies.
    An invalid pinned pair fails before consuming any randomness.
    """

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def sample(self, *, motive=None, context=None):
        _check_filters(motive, context)
        if motive is not None and context is not None:
            return CrimeSeed(motive, context)
        if motive is None:
            motives = tuple(m for m in Motive if context is None or context in RULES[m].contexts)
            motive = self.rng.choice(motives)
        if context is None:
            context = self.rng.choice(RULES[motive].contexts)
        return CrimeSeed(motive, context)

    def develop(self, seed, *, stake=None):
        """Expand an existing two-element seed without redrawing its parents."""
        if type(seed) is not CrimeSeed:
            raise TypeError("seed must be a CrimeSeed")
        if stake is not None:
            return CrimePremise(seed.motive, seed.context, stake)
        return CrimePremise(seed.motive, seed.context,
                            self.rng.choice(STAKE_BRANCHES[seed.motive, seed.context]))

    def sample_premise(self, *, motive=None, context=None, stake=None):
        """Parent-first policy; a pinned stake restricts both parent domains.

        A pinned child must never redraw/reject arbitrary parents or weight a
        motive by its number of matching contexts/leaves. Empty domains fail
        before RNG consumption. develop() is the explicit staged entry point.
        """
        domain = allowed_premises(motive=motive, context=context, stake=stake)
        if not domain:
            raise ValueError("No compatible premise for these filters")
        if motive is None:
            motive = self.rng.choice(tuple(m for m in Motive if any(p.motive is m for p in domain)))
        if context is None:
            context = self.rng.choice(tuple(c for c in Context if any(p.motive is motive and p.context is c for p in domain)))
        return self.develop(CrimeSeed(motive, context), stake=stake)


def main(argv=None):
    from scenario_victim import VictimGoal
    from scenario_means import AcquisitionKind, Method
    from scenario_situations import SituationKind
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int)
    parser.add_argument("--step", type=int, choices=(2, 3, 4, 5, 6, 7), default=3,
                        help="Seed (2), premise (3), kernel (4), execution (5), artifacts (6), witnesses (7)")
    parser.add_argument("--motive", choices=[m.value for m in Motive])
    parser.add_argument("--context", choices=[c.value for c in Context])
    parser.add_argument("--stake", choices=[s.value for s in Stake])
    parser.add_argument("--requirements", action="store_true", help="Show derived obligations, not established facts")
    parser.add_argument("--catalogue", action="store_true", help="List allowed pairs/triples, optionally filtered")
    parser.add_argument("--json", action="store_true", help="Emit stable enum IDs")
    parser.add_argument("--goal", choices=[goal.value for goal in VictimGoal],
                        help="Constrain the victim goal (step 5, 6 or 7)")
    parser.add_argument("--acquisition", choices=[kind.value for kind in AcquisitionKind])
    parser.add_argument("--method", choices=[kind.value for kind in Method])
    parser.add_argument("--weapon-origin", choices=("home", "bar", "restaurant"))
    parser.add_argument("--no-mundane", action="store_true")
    parser.add_argument("--public-inventory", action="store_true")
    parser.add_argument("--situation", choices=[s.value for s in SituationKind])
    parser.add_argument("--public-scene", action="store_true")
    parser.add_argument("--walkthrough", action="store_true", help="Step 6/7 offline acquisition walkthrough")
    parser.add_argument("--play", action="store_true", help="Play the experimental causal generator in CLI")
    parser.add_argument("--skills", help="With --play: two among fingerprints,search,rapport")
    args = parser.parse_args(argv)
    if args.play:
        if any((args.count is not None, args.motive, args.context, args.stake, args.goal,
                args.acquisition, args.method, args.weapon_origin, args.no_mundane,
                args.public_inventory, args.situation, args.public_scene, args.walkthrough,
                args.requirements, args.catalogue, args.json, args.step != 3)):
            parser.error("--play accepts only --seed and --skills; authoring previews use --step")
        from scenario_play import main as play_main
        return play_main(["--seed", str(args.seed)] + (["--skills", args.skills] if args.skills else []))
    if args.skills:
        parser.error("--skills requires --play")
    if args.count is None:
        args.count = 1 if args.step in (4, 5, 6, 7) else 8
    if args.count < 1:
        parser.error("--count must be positive")
    if args.goal and args.step not in (5, 6, 7):
        parser.error("--goal requires --step 5, 6 or 7")
    if args.step not in (5, 6, 7) and (args.acquisition or args.method or args.weapon_origin or args.no_mundane or args.public_inventory or args.situation or args.public_scene):
        parser.error("Weapon / inventory options require --step 5, 6 or 7")
    if args.walkthrough and args.step not in (6, 7):
        parser.error("--walkthrough requires --step 6 or 7")
    if args.step in (4, 5, 6, 7):
        # Delegate strings through the kernel CLI. Importing this script as
        # scenario_sampler while it runs as __main__ creates different enum
        # classes; passing local enum objects would break strict typing.
        if args.step == 4:
            from scenario_kernel import main as next_main
        else:
            from scenario_crime import main as next_main
        forwarded = ["--seed", str(args.seed), "--count", str(args.count)]
        if args.step in (6, 7):
            forwarded.append("--investigation")
        if args.step == 7:
            forwarded.append("--witnesses")
        for name in ("motive", "context", "stake", "goal", "acquisition", "method", "weapon_origin", "situation"):
            if getattr(args, name) is not None:
                forwarded.extend(("--" + name.replace("_", "-"), getattr(args, name)))
        for name in ("json", "catalogue", "requirements", "no_mundane", "public_inventory", "public_scene", "walkthrough"):
            if getattr(args, name):
                forwarded.append("--" + name.replace("_", "-"))
        return next_main(forwarded)
    if args.step == 2 and (args.stake or args.requirements):
        parser.error("--stake and --requirements require --step 3")
    motive = Motive(args.motive) if args.motive else None
    context = Context(args.context) if args.context else None
    stake = Stake(args.stake) if args.stake else None
    # Reject contradictory filters even in catalogue mode (not an empty success).
    if motive is not None and context is not None:
        try:
            CrimeSeed(motive, context)
        except ValueError as error:
            parser.error(str(error))
    if args.step == 3 and not allowed_premises(motive=motive, context=context, stake=stake):
        parser.error("No compatible premise for these filters")
    if args.catalogue:
        samples = (allowed_pairs(motive=motive, context=context) if args.step == 2 else
                   allowed_premises(motive=motive, context=context, stake=stake))
    else:
        sampler = ScenarioSampler(args.seed)
        samples = tuple(sampler.sample(motive=motive, context=context) if args.step == 2 else
                        sampler.sample_premise(motive=motive, context=context, stake=stake)
                        for _ in range(args.count))
    if args.json:
        output = [sample.as_dict() for sample in samples]
        if args.requirements:
            output = [{**row, "required_facts": [f.value for f in sample.required_facts]}
                      for row, sample in zip(output, samples)]
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return
    dimensions = "moteur + contexte" if args.step == 2 else "moteur → contexte → enjeu"
    print(f"Sampler causal V{CATALOGUE_VERSION} — {dimensions}")
    print(f"{len(allowed_pairs())} couples autorisés ; {len(allowed_premises())} triplets autorisés.\n")
    for index, sample in enumerate(samples, 1):
        rule = RULES[sample.motive]
        suffix = f" → {sample.stake.label}" if args.step == 3 else ""
        print(f"{index:02d}. {rule.label} × {CONTEXTS[sample.context].label}{suffix}")
        print(f"    Condition à construire ensuite : {rule.premise}")
        if args.requirements:
            print("    Contrat — faits à construire, pas preuves :")
            for fact in sample.required_facts:
                print(f"      - {fact.label}")


if __name__ == "__main__":
    main()
