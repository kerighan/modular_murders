# Noyau causal — instanciation, étape 4

[scenario_kernel.py](../scenario_kernel.py) transforme une `CrimePremise` du
[sampler](SCENARIO_SAMPLER.md) en un petit monde **privé, avant le crime**.
Ce noyau reste indépendant du moteur Godot/Python et n'est pas inclus dans l'APK.
Version 3 : relations avec fin, rivalité sentimentale et triangles ordinaires.
Le restaurant et ses métiers, ajoutés en V2, sont conservés.
L'ajout du lieu au jeu existant est décrit séparément dans [SCENARIO_MEANS.md](SCENARIO_MEANS.md).

## Périmètre effectif

| Mobile | Contexte | Enjeux instanciés |
|---|---|---|
| Emprise | Amoureux | Séparation annoncée, refus de se soumettre |
| Révélation | Professionnel | Fraude, exploitation, crime antérieur |
| Éliminer un rival | Amoureux | Rivalité sentimentale |

6 triplets sur les 105 amorces abstraites. Les autres lèvent `UnsupportedPremise` ;
ils ne donnent pas une histoire générique. La liste implémentée est explicite :
ajouter une feuille au sampler ne la rend pas automatiquement constructible.

Les branches instanciées ont actuellement une intention de tuer formulée avant
l'exécution. Ni la méthode ni la date/trajectoire du meurtre ne sont fixées.
Les dates relatives sont une chronologie provisoire du noyau, pas une simulation
de déplacements. Les crimes impulsifs et les autres mobiles restent à ajouter.

## Structures concrètes

Toutes les structures sont des dataclasses immuables :

- `Person` : identité, métier, lieu de travail, domicile, revenus et charges.
- `Relationship` : même type pour le lien central et les amitiés/relations
  sentimentales ordinaires, sans indicateur de culpabilité.
- `Resource` : objet/bien/quantité, propriétaire et détenteur **distincts**.
- `Dependency` : contrôleur, personne dépendante, ressource réellement contrôlée.
- `Demand` : exigence réelle, destinataire, éventuel ami concerné.
- `Incident` : faute précise, responsable, personne affectée et ressource.
- `Knowledge` : personne informée, fait appris et événement de découverte.
- `Disclosure` : information concernée, personne qui veut parler, destinataire et
  rendez-vous futur.
- `Event` : acteur, personne concernée, lieu, sujet et causes antérieures.
- `Intent` : auteur/cible, objectif et **effet attendu par l'auteur**, pas résultat
  garanti du meurtre.

`Roles` lie l'auteur, la victime et une troisième personne à trois identités
existantes et distinctes. Le générateur crée six personnes : les trois autres ont
aussi des métiers, domiciles et liens ordinaires, mais pas de mobile ajouté par
le simple fait d'être proches. Les identités des rôles ne sont pas toujours p0/p1.

`Event.target` désigne la personne concernée, pas nécessairement une personne
présente ni un témoin. Le module ne certifie pas de coprésence physique, de trajet,
de perception ou de moyen de communication. Ces détails sont des contraintes de
la couche suivante, pas des connaissances gratuites à attribuer aux PNJ.

## Construction et vérification

Le builder construit un **monde neuf** autour du noyau. La réutilisation et
l'enrichissement d'un monde préexistant ne sont pas encore implémentés ; aucun
fait d'une partie existante n'est écrasé.

Exemple d'emprise financière : les charges de la victime dépassent ses revenus,
un budget détenu et contrôlé par l'auteur couvre le déficit, et l'auteur dispose
effectivement des revenus pour financer cette aide. Une séparation ou un refus
survient après l'établissement de cette dépendance, puis une réaction et une
décision. Variante logement : domicile partagé contrôlé par l'auteur, sans autre
logement possédé par la victime dans ce petit monde.

Exemple professionnel : les acteurs travaillent réellement au même endroit,
avec des métiers compatibles. Un responsable détourne une partie de la
rémunération, impose des heures non payées ou commet un vol antérieur. Une
découverte donne effectivement cette connaissance à la victime ; une annonce
prévoit un destinataire, puis la crainte et l'intention suivent cette annonce.

`validate_kernel()` ne prend **aucune liste de tags satisfaits** en entrée.
Il vérifie les entités, références, ressources, acteurs concernés, types,
chronologie et liens causaux. Pour chaque requirement, il produit un
`RequirementWitness` qui référence les objets/événements concrets justifiant le
prédicat. `CausalKernel` valide automatiquement sa construction.

Supprimer la relation centrale, financer une aide impossible, payer les heures
supposées non payées, attribuer la découverte à une autre personne ou faire
réagir l'auteur avant l'annonce doit échouer. Un graphe qui contient simplement
les bons mots n'est pas suffisant.

Ce contrôle couvre les deux patrons écrits ; ce n'est ni un solveur général de
contraintes sociales, ni une validation juridique, ni un simulateur complet
d'économie/psychologie. La croyance de l'auteur est modélisée séparément d'un
avantage réel ou d'une réussite future.

## Méthode laissée ouverte

`kernel.method` vaut `None`. Aucun meurtre n'est exécuté et aucune arme, trace,
photo, lettre, caméra ou observation incriminante n'est ajoutée. Une histoire
sentimentale n'impose pas un type de preuve. Plus tard, les mêmes règles de
manifestations pourront produire des photos à partir des liens ordinaires.

La couche [d'exécution physique, étape 5](SCENARIO_CRIME.md), est maintenant
disponible dans `scenario_crime.py`. Elle enveloppe ce noyau inchangé, choisit
parmi les moyens accessibles et construit les déplacements/conséquences de deux
variantes de rencontre extérieure. Un moyen incompatible est rejeté, sans
modifier silencieusement les faits précédents. Les preuves accessibles restent
une étape suivante.

## CLI et API

```bash
python scenario_sampler.py --step 4 --motive control --context romance --stake separation --requirements
python scenario_sampler.py --step 4 --motive control --context romance --stake refusal
python scenario_sampler.py --step 4 --motive silence --context work --stake fraud
python scenario_sampler.py --step 4 --motive silence --context work --stake exploitation
python scenario_sampler.py --step 4 --catalogue
python scenario_kernel.py --seed 7 --count 3 --json
```

L'étape 4 affiche un noyau par défaut, les étapes 2/3 conservent huit tirages.
`--requirements` montre les références concrètes. `--catalogue` ne liste que les
six noyaux implémentés. Les filtres sont appliqués avant le RNG, avec un tirage
parent-first dans le domaine implémenté.

```python
from scenario_sampler import Context, CrimePremise, Motive, Stake
from scenario_kernel import ControlMechanism, KernelBuilder, validate_kernel

premise = CrimePremise(Motive.CONTROL, Context.ROMANCE, Stake.SEPARATION)
kernel = KernelBuilder(42).build(premise, mechanism=ControlMechanism.HOUSING)
witnesses = validate_kernel(kernel)
assert kernel.method is None
```

La sortie JSON est marquée `private_precrime_truth`. **Ne jamais l'envoyer au
client du jeu** : elle contient les rôles, ressources et intentions cachés.
Le marqueur de visibilité est documentaire, pas un mécanisme de sécurité.
Le noyau lui-même n'a ni projection publique ni solver d'enquête ; la règle
« chaque indice compatible avec au moins deux suspects » ne s'applique pas aux
faits privés exacts. L'étape 5 possède maintenant un petit aperçu public des
inventaires ([provenances](SCENARIO_MEANS.md)), pas encore une enquête complète.

## Vérifications

```bash
python -m pytest -q tests/test_scenario_kernel.py tests/test_scenario_sampler.py tests/test_scenario_development.py
```

436 tests sur ces trois modules, dont 80 pour le noyau. Corpus de 1 200
instanciations (200 graines × 6 patrons), reproductibilité, mutations négatives
des faits/références/ordres/quantités, distinctions faits/croyances, liens ordinaires,
filtres, indépendance du RNG global et CLI entre processus/hash seeds.
Ce corpus n'est pas présenté comme 1 000 recettes de résolution différentes.
L'extension V3 est décrite dans [SCENARIO_SITUATIONS.md](SCENARIO_SITUATIONS.md).
