# Objectifs de la victime — base V2, extension V4

[scenario_victim.py](../scenario_victim.py) décrit l'intention de la victime,
indépendamment de l'arme, de l'endroit où l'auteur attaque et des futures preuves.
Il est utilisé par l'[étape 5](SCENARIO_CRIME.md), sans changer le noyau causal,
le jeu actuel, les sauvegardes ou l'APK.

V4 ajoute `meet_author` (accord réel de rendez-vous extérieur pour discuter du
conflit) et `go_out` (sortie ordinaire au bar/restaurant), avec départ du domicile.
Les partenaires amoureux actuels deviennent des contacts possibles pour dîner.
Ces extensions et leurs validations sont décrites dans [SCENARIO_SITUATIONS.md](SCENARIO_SITUATIONS.md).
Les sections suivantes décrivent les trois objectifs initiaux depuis le travail.

## Domaine initial

| Objectif | Raison | Conditions concrètes |
|---|---|---|
| Rentrer chez soi | Se reposer après le travail | Domicile réel de la victime |
| Retrouver quelqu'un | Dîner ensemble | Ami réel ou collègue déjà établi comme destinataire d'une divulgation ; accord de visite distinct |
| Retrouver quelqu'un | Chercher du soutien | Ami réel + séparation/refus effectivement survenu avant l'accord |
| Aller au commissariat | Signaler un fait découvert | Incident de détournement/vol réellement connu de la victime avant son intention de le signaler |

Le dîner ne prouve ni conflit ni culpabilité. Un lien sentimental n'impose pas
une demande de soutien. Un emploi dans le même bâtiment ne suffit pas pour
supposer une connaissance réciproque. Aucun membre de famille n'est inventé :
le noyau devra d'abord posséder ce type de relation.

La sélection d'incidents pouvant mener au commissariat est un choix d'auteur
du prototype, pas une classification juridique générale. Les heures imposées
non payées n'ouvrent pas cette branche pour l'instant ; les futures destinations
professionnelles/syndicales restent à construire.

## Structures et déroulé

`VictimPlan` possède un objectif, une raison, un point de départ, une destination,
la date de formation, l'heure prévue d'arrivée, les références des faits qui le
fondent et les personnes à qui le plan a été communiqué.

Une visite ajoute `Appointment` : visiteur, hôte, lieu réel, accord préalable,
heure et intervalle de présence de l'hôte chez lui. Cet intervalle est un fait
de fond ajouté explicitement, pas une déduction issue de son métier ni une
simulation de toute sa journée. L'hôte n'est ni l'auteur ni la victime.

`candidate_plans()` développe ces candidats **sans RNG et sans mutation**.
Le planner physique élimine les plans et rencontres impossibles avant le
tirage : objectif → raison → plan → moyen → point de rencontre. Les variantes
de destination et la longueur des trajets ne multiplient donc pas artificiellement
le poids d'un objectif. Un `plan` explicitement fourni est validé et conservé.

Le trajet part encore du lieu de travail : d'autres origines, étapes intermédiaires,
horaires dépendants des métiers et rencontres avec le meurtrier restent hors
périmètre. Les heures prévues sont pour l'instant des créneaux de 18 h à 21 h,
à la demi-heure, sur une seule journée abstraite.

Le trajet prévu est `Execution.intended_journey`. Le trajet effectif est son
préfixe, interrompu à une scène **extérieure**. L'auteur observe la sortie et
suit ce préfixe ; il ne reçoit pas automatiquement l'objectif privé de la victime.
Aller à la police ne force pas le crime devant la police : tout point extérieur
réalisable du trajet peut convenir. Si le trajet ne traverse qu'une rue, il n'y
a naturellement qu'un point possible sur cette petite carte.

## Rendez-vous manqué ≠ témoignage du meurtre

Quand la victime meurt avant de rejoindre un rendez-vous convenu, l'hôte présent
constate la non-arrivée quinze minutes après l'heure prévue. C'est un
`MissedAppointment` dérivé du rendez-vous, du déplacement effectif et de la mort.
Mourir à l'heure exacte du rendez-vous, devant la destination, produit aussi
cette absence. Une visite spontanée au commissariat ne crée pas d'agent qui
attendrait magiquement la victime.

La CLI prévisualise une réplique limitée à ce que l'hôte peut savoir :

> On devait dîner ensemble vers 20 h 00. J'ai attendu, mais on ne s'est pas vus.

L'hôte ne connaît ainsi ni l'attaque, ni la cause de la mort, ni l'identité de
l'auteur. Ce fait est encore **privé** : il n'est pas un dialogue déjà intégré
au jeu, ni une preuve qui identifie un coupable. La future projection publique
devra conserver au moins deux suspects compatibles par indice incriminant et
vérifier la convergence de leurs combinaisons.

Les anciens engagements ne sont pas effacés. Dans les noyaux professionnels,
la victime peut décider d'aller à la police aujourd'hui tout en ayant déjà
prévu de parler à son collègue un jour suivant. Ces deux plans compatibles sont
distincts ; le crime empêche leur accomplissement. Le dîner chez ce collègue
n'est pas transformé silencieusement en la divulgation prévue ultérieurement.

## API et CLI

```python
from scenario_kernel import KernelBuilder
from scenario_crime import CrimeBuilder
from scenario_victim import VictimGoal, candidate_plans

kernel = KernelBuilder(7).sample()
plans = candidate_plans(kernel, goal=VictimGoal.MEET_PERSON)
builder = CrimeBuilder(7)
streets, inventory = builder.prepare(kernel)
crime = builder.execute(kernel, streets, inventory, plan=plans[0])
assert crime.victim_plan is plans[0]
```

```bash
python scenario_sampler.py --step 5 --seed 7 --goal meet_person
python scenario_sampler.py --step 5 --seed 7 --goal report_incident
python scenario_sampler.py --step 5 --seed 7 --goal return_home --json
python scenario_sampler.py --step 5 --motive control --goal report_incident
# erreur explicite : aucun noyau compatible ; pas de repli aléatoire
```

`--goal` n'est disponible qu'à l'étape 5. Le filtre police restreint le domaine
causal aux amorces implémentées qui permettent ce plan, avant le tirage.
`validate_plan()` vérifie ensuite les faits concrets : ces métadonnées de domaine
ne suffisent pas à autoriser une visite dans un monde qui ne les satisfait pas.

Tous ces exports restent `private_executed_truth`. Ne pas les envoyer au client.
