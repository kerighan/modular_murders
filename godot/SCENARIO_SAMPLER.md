# Sampler causal — moteur, contexte, enjeu

Prototype indépendant : [scenario_sampler.py](../scenario_sampler.py).
Il ne remplace pas encore `Game` / `CaseStory`, n'est pas embarqué dans l'APK et
ne touche ni aux sauvegardes ni à leur version. Il n'utilise que la bibliothèque
standard Python.

Catalogue V2 : les 46 couples initiaux sont conservés. Le troisième tirage
ouvre 105 triplets autorisés, sur 1 764 combinaisons brutes (9 × 7 × 28).

L'étape 4 est maintenant disponible : [noyau causal instancié](SCENARIO_KERNEL.md),
six triplets effectivement construits et vérifiés. Les autres étapes et le
catalogue V2 sont inchangés.

L'étape 5 physique est en V4 : [objectifs de la victime](SCENARIO_VICTIM.md),
[exécution](SCENARIO_CRIME.md), puis [provenance des moyens et aperçu d'inventaire](SCENARIO_MEANS.md).
Le sampler reste indépendant du jeu ; seul le nouveau restaurant a aussi été
ajouté au moteur existant. Sources maintenant en règles 13 avec le lien partenaire.
Voir [triangles et situations](SCENARIO_SITUATIONS.md) pour les rendez-vous,
empoisonnements fictifs et l'audit de répétition. Six noyaux sont construits.

L'étape 6 projette maintenant les [sources découvrables](SCENARIO_OBSERVATIONS.md) :
`--step 6 --walkthrough`, scène/prélèvements/analyses/inventaires avec conditions
d'accès. Ce n'est pas encore une enquête résoluble : témoins et preuves sociales
restent à construire, sans casser l'ambiguïté ≥2 personnes par artefact/action.

L'étape 7 ajoute maintenant les [témoins bornés par leurs souvenirs](SCENARIO_WITNESSES.md) :
`--step 7 --walkthrough`, présence ≠ attention ≠ connaissance. Textes sourcés,
entretiens complets ≥2 candidats, pas d'accusation déduite d'une simple présence.
Les communications sociales et la certification d'enquêtes restent à construire.

## Amorce : deux éléments

Un `CrimeSeed` immuable contient exactement deux enums :

```python
from scenario_sampler import Context, Motive, ScenarioSampler

sampler = ScenarioSampler(seed=42)
amorce = sampler.sample()
branche = sampler.sample(motive=Motive.SILENCE)
fixe = sampler.sample(motive=Motive.SILENCE, context=Context.CHANCE_ENCOUNTER)
print(fixe.as_dict())
# {'motive': 'silence', 'context': 'chance_encounter'}
```

Le contexte désigne **le cadre causal**, pas le métier de la victime. Une danseuse
peut être victime dans une affaire familiale ou une rencontre fortuite ; son
métier n'impose pas `WORK`.

`CHANCE_ENCOUNTER` signifie que le crime naît de cette rencontre, sans histoire
commune préalable. Ce n'est pas synonyme de « la victime ne connaît pas l'auteur » :
une personne peut sélectionner et suivre une cible inconnue personnellement.
Le ciblage et la répétition/sérialité seront des dimensions ultérieures.

## Domaine combinatoire V1

`RULES[motive].contexts` est le domaine autorisé du deuxième tirage. Les cellules
vides sont **non prises en charge par notre grammaire V1**, pas impossibles dans
la réalité. La table est une décision d'auteur, pas une typologie scientifique.

| Moteur | Travail | Famille | Amour | Voisinage | Milieu criminel | Collectif | Rencontre fortuite |
|---|---|---|---|---|---|---|---|
| S'approprier | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Éviter une perte | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Empêcher une révélation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Éliminer un obstacle | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Maintenir une emprise | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Se venger | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Supprimer une menace perçue | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Prédation | — | — | — | — | — | — | ✓ |
| Conviction | — | — | — | — | — | ✓ | ✓ |

46 couples autorisés / 63 possibles ; 17 exclus. L'emprise demande une relation
préalable ; la vengeance V1 un tort antérieur. Une révélation peut au contraire
impliquer un témoin fortuit. Prédation et conviction sont volontairement bornées
à quelques contextes pour cette première exploration, à élargir explicitement.

Chaque règle contient aussi une `premise` lisible. C'est une indication d'auteur,
pas un fait du monde. La compatibilité des enums est exécutable ; les obligations
causales typées ci-dessous restent à instancier dans un monde réel.

## Développement : troisième élément conditionnel

`Stake` décrit l'enjeu : héritage, fraude, exploitation, séparation, dette, rôle
artistique, etc. `STAKE_BRANCHES[(motive, context)]` donne son domaine exact.
Il dépend **des deux choix précédents**, pas seulement du moteur.

```python
from scenario_sampler import CrimeSeed, Stake

amorce = CrimeSeed(Motive.SILENCE, Context.WORK)
developpee = sampler.develop(amorce, stake=Stake.FRAUD)
print(developpee.as_dict())
# {'motive': 'silence', 'context': 'work', 'stake': 'fraud'}

developpee = sampler.sample_premise()  # les trois tirages successifs
```

`CrimeSeed` garde ses deux champs. `CrimePremise` en a exactement trois, est
immuable et valide le triplet à la construction comme à l'import JSON.
`develop()` conserve les parents : il ne relance jamais l'amorce. Un enjeu imposé
et incompatible est refusé avant de consommer du hasard.

Quelques domaines :

| Moteur | Contexte | Enjeux autorisés |
|---|---|---|
| Révélation | Professionnel | Fraude, exploitation, crime antérieur |
| Révélation | Amoureux | Secret personnel, liaison dissimulée, crime antérieur |
| Emprise | Amoureux | Séparation annoncée, refus de se soumettre |
| Emprise | Professionnel | Départ annoncé, refus de se soumettre |
| Appropriation | Familial | Argent, objet de valeur, héritage, bien partagé |
| Appropriation | Rencontre fortuite | Argent, objet de valeur |
| Prédation | Rencontre fortuite | Violence ou domination recherchée pour elle-même |

Un contrat convoité relève ici de l'obstacle à éliminer, pas de l'appropriation
professionnelle : on ne suppose pas qu'un contrat devient automatiquement la
propriété de celui qui tue. Les branches sont volontairement bornées ; les rôles
et mécanismes concrets devront encore justifier ce que l'auteur espère obtenir.

## Contrat causal dérivé, pas preuves

`CrimePremise.required_facts` compose les obligations de trois tables explicites :
`CONTEXT_FACTS`, `MOTIVE_FACTS` et `STAKE_FACTS`, plus le fait que l'auteur estime
que la mort sert son objectif. Les obligations sont des enums `RequiredFact`,
dédupliqués et ordonnés. Elles ne sont **pas un quatrième tirage**.

Pour emprise × amoureux × séparation : histoire sentimentale, emprise préalable,
tentative d'autonomie, autonomie refusée, séparation annoncée et objectif de
l'auteur. Pour révélation × travail × fraude : lien professionnel, fraude,
information détenue par la victime, possibilité de divulgation et crainte de
l'auteur, avec l'objectif qui motive le passage à l'acte.

Ces tokens sont un **cahier des charges non lié à des acteurs**. Ils ne constituent
pas des faits établis et ne prouvent pas la cohérence d'événements qui n'existent
pas encore. L'étape suivante devra assigner des personnes/ressources/événements
et vérifier réellement ces prédicats. Un générateur ne pourra pas se contenter
de recopier cette liste pour prétendre avoir validé un monde.

Il n'y a ni photo obligatoire, ni lettre, ni témoin, ni liste de suspects. Une
relation ordinaire pourra plus tard produire une photo chez deux proches,
indépendamment du mobile, de la culpabilité ou de l'existence d'un conflit.
Une manifestation de relation ne sera pas automatiquement une preuve de meurtre.

Prédation n'implique toujours pas sérialité : aucune ancienne attaque obligatoire.
À l'inverse, révélation × rencontre fortuite × crime antérieur exige bien le crime
antérieur et l'information détenue par son témoin, sans relation préalable.

## Politique de tirage

Sans filtre : moteur uniforme, puis contexte uniforme parmi les contextes
autorisés de ce moteur. Ainsi, un moteur ayant un seul contexte n'est pas sept
fois moins probable qu'un moteur en ayant sept. Les couples ne sont donc pas
équiprobables. Ce n'est pas une estimation des fréquences réelles des crimes.

Avec un contexte imposé : moteur uniforme parmi les moteurs compatibles. Avec
un moteur imposé : contexte uniforme dans sa branche. Avec les deux imposés :
validation sans consommer le RNG. Un couple interdit échoue immédiatement.

Au troisième tirage, même politique parent-first : moteur uniforme, contexte
uniforme dans sa branche, puis enjeu uniforme dans le domaine du couple. Les
moteurs possédant davantage de feuilles ne sont pas favorisés. Un enjeu imposé
restreint **les deux parents** avant les tirages, et chaque niveau conserve son
uniformité dans le domaine restant. Un domaine vide est une erreur explicite.

Le RNG est privé. L'ordre des enums/branches est explicite et indépendant du
hash Python. Même graine + même version de catalogue + même suite d'appels =
mêmes sorties. Modifier le catalogue peut modifier les tirages : son numéro de
version devra être incrémenté avant de servir à des histoires sauvegardées.

Les membres d'enum ajoutés exigent une entrée explicite ; le contrôle du
catalogue échoue si une entrée manque, qu'un contexte est invalide ou inaccessible.
Construction manuelle et import JSON appliquent la même validation que le tirage.
Chaque couple doit aussi posséder une branche d'enjeux non vide, et chaque
contexte/moteur/enjeu un contrat causal explicite. Les enjeux inaccessibles,
contrats incomplets et tokens non typés sont refusés.

## Voir les sorties

```bash
python scenario_sampler.py --seed 42 --count 12
python scenario_sampler.py --catalogue
python scenario_sampler.py --motive silence --context work --catalogue
python scenario_sampler.py --motive control --context romance --requirements
python scenario_sampler.py --stake separation --count 3 --json
python scenario_sampler.py --context chance_encounter --count 12 --json
python scenario_sampler.py --step 2 --catalogue --json
python scenario_sampler.py --step 4 --motive control --context romance --stake separation --requirements
python scenario_sampler.py --motive control --context chance_encounter
# erreur : couple non pris en charge
python scenario_sampler.py --motive acquire --stake separation
# erreur : aucun triplet compatible
python -m pytest -q tests/test_scenario_sampler.py tests/test_scenario_development.py
```

La CLI utilise maintenant l'étape 3 par défaut. `--step 2` retrouve l'amorce
initiale. `--requirements` affiche le contrat ; en JSON, `required_facts` est une
métadonnée dérivée, pas des faits observés par un détective.

À cette étape, il y a **105 amorces développées distinctes**, pas 500 affaires,
et les tirages peuvent se répéter. Aucun acteur, métier, chronologie, indice
ou témoin n'est généré. La règle « au moins deux suspects par indice » ne s'applique
pas encore : il n'existe ni suspects ni indices dans ce prototype.

356 tests dédiés : examen exhaustif des 1 764 triplets, couverture du domaine sur
9 000 tirages, contrats, filtres, absence de consommation du RNG sur les erreurs,
équivalence génération directe/par étapes, import/export et CLI entre processus.

## Instanciation disponible, suite du développement

Mise à jour : une [CLI jouable du nouveau générateur](SCENARIO_PLAYABLE.md) est
disponible via `python scenario_sampler.py --play --seed 7`. Les étapes 2–7
restent les aperçus d'auteur historiques décrits dans leurs documents.

`scenario_kernel.py` instancie les rôles, relations, ressources et événements
pour emprise amoureuse (séparation/refus) et révélation au travail
(fraude/exploitation/crime antérieur). Les autres 100 triplets restent abstraits.
Voir son document pour les contrôles et limites.

`scenario_crime.py` propose l'[étape 5 : exécution physique](SCENARIO_CRIME.md),
via `python scenario_sampler.py --step 5 --seed 7`. Deux méthodes choisies parmi
les moyens existants, rencontres extérieures sur le retour du travail,
déplacements vérifiés et conséquences dérivées. La projection accessible des
observations et le contrôle des chemins de résolution restent à construire.

L'exécution V2 ajoute les [objectifs de la victime](SCENARIO_VICTIM.md) : retour
au domicile, rendez-vous avec une connaissance ou signalement au commissariat,
selon les faits réels. `--goal meet_person` permet d'examiner un rendez-vous manqué
sans attribuer à l'hôte une connaissance magique du crime.
