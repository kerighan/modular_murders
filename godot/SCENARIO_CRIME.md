# Exécution physique — étape 5

[scenario_crime.py](../scenario_crime.py) prolonge le
[noyau causal](SCENARIO_KERNEL.md) sans le modifier. L'exécution reste **privée**,
hors du moteur d'enquête et hors APK. V3 ajoute les [provenances et inventaires](SCENARIO_MEANS.md),
avec une première projection publique limitée. Bibliothèque standard seulement.

**Version actuelle V4** : [triangles et situations](SCENARIO_SITUATIONS.md).
Les sections de flow ci-dessous décrivent le patron initial de suivi ; V4 ajoute
un rendez-vous extérieur accepté et un empoisonnement fictif au bar/restaurant,
sans sang, avec une boisson et un effet retardé. Le dernier est une exception
intérieure explicite. Méthodes, origines, rencontres, traces et divulgation du
travail dépendent désormais du patron ; `workplace_disclosure` peut être `None`.
`ExecutedCrime` contient aussi les présences dans le lieu et `Execution.exposure`.

## Flow réel

1. Instancier un des cinq noyaux pris en charge : mobile, acteurs, conflit,
   réaction et intention. Le noyau reste inchangé et sa méthode reste `None`.
2. Ajouter une carte abstraite : quatre rues reliées, cinq lieux de travail,
   les vrais domiciles du noyau et le commissariat. Les bâtiments ont une entrée unique ; ils ne
   servent pas de raccourcis entre rues. Un domicile partagé reste partagé.
3. Constituer les moyens **avant** de choisir la méthode. Chaque personne,
   innocents compris, possède un ou deux objets domestiques à son domicile,
   avec propriétaire, disponibilité antérieure et usage ordinaire. Le bar et
   le restaurant possèdent aussi des stocks partagés accessibles explicitement.
4. Développer les [objectifs propres de la victime](SCENARIO_VICTIM.md) à partir
   des faits, connaissances et contacts réels. Calculer le trajet vers chaque
   destination, en respectant l'heure d'arrivée prévue et les engagements.
5. Choisir objectif → raison → plan concret, puis une méthode disponible et
   une rencontre physiquement réalisable. Un plan fourni explicitement n'est
   jamais réécrit pour faciliter le meurtre.
   L'auteur apporte son objet, prend/emprunte un objet dans un lieu, ou saisit
   un objet sur le trajet réellement suivi après observation de la victime.
6. Interrompre le trajet de la victime à une attaque extérieure. La mort suit,
   l'auteur repart vers son domicile ; l'objet est conservé, laissé ou caché
   pendant sa fuite. Un emprunt innocent indépendant peut aussi modifier le stock.
7. Dériver les conséquences physiques, puis l'éventuel rendez-vous manqué :
   quelqu'un devait réellement attendre la victime. Aucun indice destiné au
   détective n'est sélectionné dans le récit privé. Un aperçu des constats
   d'inventaire est disponible séparément avec `--public-inventory`.

La méthode n'est pas une table `mobile → arme`. Les cinq amorces peuvent utiliser
les deux méthodes, **si** l'objet existe et est accessible. Un marteau peut venir
d'un autre lieu : son absence au domicile ne suffit donc plus à exclure cette
méthode. Une provenance incompatible échoue sans inventer ni déplacer l'objet.

## Périmètre et structures

Deux méthodes fictives : arme blanche et objet contondant. Deux variantes d'une
**même famille d'opportunités** : à la sortie du travail, ou sur le trajet après
avoir suivi la victime. Ce ne sont pas deux grandes recettes d'enquête différentes.
L'embuscade, le crime impulsif, le serial killer, les complices
et les autres mobiles ne sont pas implémentés.

`ExecutedCrime` contient :

- le `CausalKernel` initial ;
- une `StreetMap` avec `Node`/`Edge`, temps de marche positifs et Dijkstra ;
- l'inventaire préexistant de `Tool` ;
- un `WorkplaceDisclosure` : la victime a communiqué son lieu de travail à
  l'auteur avant son intention, après le début de leur relation réelle ;
- un `VictimPlan` : objectif, raison, destination, heure prévue, sources,
  personnes informées et éventuel rendez-vous convenu ;
- une `Execution` avec les trajets et heures des événements ;
- les gardiens de stock, emprunts ordinaires, transferts, états et inventaires ;
- les `Trace` et éventuels `MissedAppointment` produits par cette exécution.

La communication du lieu de travail est un **fait de fond ajouté explicitement**
dans ce prototype, pas une implication universelle de « couple » ou « collègues ».
Sa transmission ancienne n'a pas encore de simulation de conversation/perception.
Pour le trajet du crime, en revanche, l'auteur observe physiquement la sortie et
suit le préfixe réellement emprunté : il ne connaît pas magiquement le trajet.

Chaque `Walk` donne les nœuds et les heures de passage. L'attente est l'intervalle
entre arrivée de l'auteur et observation de la sortie. `intended_journey` est
distingué du déplacement effectif, interrompu par le meurtre. Le nom V1
`intended_return` a été remplacé : la destination n'est plus forcément le domicile.
Les autres personnes n'ont **pas encore** de journées complètes simulées : seuls
les emprunteurs ordinaires ont un aller-retour explicite. On ne peut donc pas
les déclarer témoins du crime. Un hôte possède uniquement un intervalle
explicite de présence chez lui, suffisant pour constater un rendez-vous manqué.

Les temps sont des conventions de jeu, pas des estimations médicales ou une
simulation fine d'agression. La carte est une topologie d'auteur indépendante,
pas la géométrie Godot ni une modification des quartiers du jeu existant.

## Invariants

`ExecutedCrime` valide automatiquement sa construction. `validate_crime()`
revérifie aussi le noyau causal :

- carte connectée, entrées distinctes des rues, domiciles et métiers existants ;
- objet existant et accessible, prise à son vrai emplacement et à la bonne heure ;
- prêt autorisé par un gardien présent ; prise opportuniste sur le suivi réel ;
- intention avant préparation, moyens compatibles avec la méthode ;
- passages sur des arêtes réelles, durée exacte, pas de traversée de bâtiment ;
- arrivée de l'auteur avant la sortie, observation et suivi coprésents ;
- scène extérieure sur le trajet réel ; mort puis départ et retour continus ;
- objectif fondé sur les faits ; destination et heure conformes au plan ;
- hôte réel, rendez-vous convenu, présence à l'heure du constat de non-arrivée ;
- dans les cas de silence, mort avant la divulgation prévue ;
- conséquences, mouvements, conservation des objets et inventaires exactement dérivés.

Le domaine des rencontres est filtré **avant le tirage** par la disponibilité
des moyens et les contraintes horaires. Une requête sans solution lève
`NoFeasibleCrime`, sans consommer le RNG d'exécution. Ce planner traite ce patron
précis, pas tous les emplois du temps et contraintes d'un monde général.

## Conséquences ≠ preuves

Ce prototype produit corps, sang de la victime, lésion liée à la méthode et,
si abandonné, objet utilisé. Les sources `attack`, `death`, `tool_left` désignent
les événements représentés par les champs de `Execution`. La provenance, le
lieu et l'heure sont contrôlés ; ajouter une empreinte ou attribuer une trace
à une caméra inexistante doit échouer.

La sortie est marquée `private_executed_truth`. Elle contient l'auteur réel :
**ne pas l'envoyer au client**. Le marqueur n'est pas un contrôle d'accès.
Une trace privée exacte n'est pas encore un indice incriminant public.

Hormis le premier aperçu des inventaires, la prochaine projection devra décider
ce qui est découvert, où et comment,
avec au moins **deux suspects compatibles par indice/artifact incriminant**.
Elle devra vérifier la convergence de leurs combinaisons. Aucun témoin du crime
ni caméra n'est ajouté pour l'instant, et aucune enquête résoluble n'est garantie.
Le constat de rendez-vous manqué reste privé ; la CLI montre seulement un aperçu
de ce que l'hôte pourra dire, sans lui attribuer la connaissance du meurtre.
Une future CCTV devra couvrir un vrai segment du trajet au bon instant.

## Essayer

```bash
python scenario_sampler.py --step 5 --seed 7
python scenario_sampler.py --step 5 --seed 7 --goal meet_person
python scenario_sampler.py --step 5 --seed 7 --goal report_incident
python scenario_sampler.py --step 5 --seed 7 --goal return_home
python scenario_sampler.py --step 5 --motive control --context romance --stake separation
python scenario_sampler.py --step 5 --motive silence --context work --stake fraud --requirements
python scenario_crime.py --seed 42 --count 3 --json
python scenario_sampler.py --step 5 --catalogue
```

Les étapes 4/5 produisent un exemple par défaut. Les étapes 2/3 restent identiques.
La CLI utilise un RNG physique séparé : la sélection de la méthode ne change
pas le prochain noyau produit par le builder causal. Sans `--goal`, les mêmes
noyaux restent produits pour une même graine/suite d'appels. Un objectif imposé
filtre le domaine causal avant le tirage, sans relances aléatoires ni repli sur
un autre objectif. La sortie privée passe à `crime_version: 4` ; le RNG physique
utilise le namespace V4. Le noyau passe en V3 avec les relations/triangles :
les snapshots seedés des versions précédentes ne sont pas conservés.

```python
from scenario_kernel import KernelBuilder
from scenario_crime import CrimeBuilder, Method, NoFeasibleCrime

kernel = KernelBuilder(7).sample()
builder = CrimeBuilder(7)
streets, inventory = builder.prepare(kernel)
try:
    crime = builder.execute(kernel, streets, inventory, method=Method.BLUNT)
except NoFeasibleCrime:
    # Ne pas inventer un marteau : choisir un moyen existant, ou rejeter.
    crime = builder.execute(kernel, streets, inventory)
assert crime.kernel is kernel
assert kernel.method is None
```

## Tests

```bash
python -m pytest -q tests/test_scenario_victim.py tests/test_scenario_crime.py tests/test_scenario_kernel.py tests/test_scenario_sampler.py tests/test_scenario_development.py tests/test_case.py tests/test_scenario_graph.py
```

Corpus physique de 1 000 générations : 200 graines × 5 noyaux, conservation des
faits antérieurs et reproductibilité. Matrice de 60 fixtures : 5 noyaux × 2
méthodes × 2 rencontres × 3 devenirs de l'objet ; 120 fixtures supplémentaires
croisent les cinq noyaux, deux méthodes, trois devenirs et quatre acquisitions.
Mutations négatives sur moyens,
connaissances, carte, horaires, coprésence, fuite et provenance des traces.
Tests dédiés aux objectifs, contacts, accords, présence de l'hôte, non-arrivée,
compatibilité des engagements antérieurs et CLI avec objectifs imposés.
Ce n'est pas un corpus de 1 000 recettes de résolution.
