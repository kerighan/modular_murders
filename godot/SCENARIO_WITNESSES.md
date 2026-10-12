# Étape 7 — témoins bornés par les faits (V1)

Prototype offline : `scenario_witnesses.py`. **Pas branché à Game/Godot/APK.**
Le noyau reste V3, l'exécution V4, les règles du jeu 13 et l'APK v11 inchangés.
La projection de découverte avec témoins est V2 ; `--step 6` conserve V1.

## Trois niveaux distincts

1. `SceneEvent` : acte extérieur réellement dérivé de l'exécution physique.
2. `Presence` + `Attention` : position, intervalle, regard, sujets visibles,
   obstruction et possibilité de reconnaître ensuite la victime sur une photo.
3. `Perception` : souvenir portant sur un événement précis et un aspect limité.

Être sur place n'ajoute **aucun souvenir**. Une perception doit correspondre à
un événement vrai, au bon endroit et à la bonne date, pendant une présence et une
attention explicites. Visuel : ligne de vue non obstruée, acteur/target visibles ;
la victime peut être rapprochée de la référence photo, l'autre visage reste non
reconnu. Ce sont des faits de visibilité **déclarés dans le monde d'auteur**,
pas un raycast vérifié sur les meshes Godot.

Un serveur sait qu'il a servi une boisson par participation au service. Il ne
connaît pas automatiquement l'ajout ultérieur. Un hôte connaît son rendez-vous
et l'absence réellement constatée, pas la raison du décès. `reply_to()` répond
« Je ne sais pas » si le sujet n'est pas dans les souvenirs ; poser une question
ne crée ni connaissance, ni accusation, ni nouvelle piste vers un nom aléatoire.

## Catalogue physique actuel

| Événement | Ce qui peut être raconté | Ce qui ne doit pas être inféré |
|---|---|---|
| Même rue empruntée | Victime et autre personne sur le trajet effectivement suivi. | Le témoin connaît son emploi, son objectif ou une intention de filature. |
| Simple coprésence | Deux personnes au même point, notamment attaque dès la sortie. | Un déplacement derrière la victime si aucun suivi réel n'a eu lieu. |
| Rendez-vous | Deux personnes ensemble au lieu réellement atteint. | Leur relation, leur différend ou les mots échangés. |
| Service | Une boisson servie à la personne présentée sur la photo. | Qui a modifié le verre, ou quand cette personne est morte. |
| Ajout à une boisson | Une intervention vue, sans identification du contenu. | Substance reconnue, caractère criminel ou absence de toute autre intervention. |
| Agression | Une personne agresse la victime, avec un signalement partiel. | Nom, visage reconnu, mobile ou modèle exact d'arme. |
| Départ | Une personne sur un point du **vrai** trajet de fuite. | Quelqu'un était forcément coupable parce qu'il est passé là. |
| Non-arrivée | Rendez-vous convenu chez l'hôte, visite interrompue avant destination. | L'hôte a vu le crime ou connaissait le trajet effectif. |

Les heures dites sont approximatives (quart d'heure), pas l'horodatage privé exact.
Les phrases ne conseillent pas le détective et n'affirment pas de motivations.
Pas de scène sonore ou de confidences relationnelles inventées : le noyau ne
modélise pas encore les paroles audibles/canaux de transmission nécessaires.

## Présences construites a posteriori, crime conservé

Le serveur réutilise ses vrais shifts. L'hôte réutilise sa présence au rendez-vous
et reçoit un créneau d'entretien chez lui le lendemain.

Zéro à deux témoins annexes sont ajoutés : vendeuse de nuit/livreur, poste au
point observé, logement propre relié à une rue existante, aller/retour du soir
et aller/retour pour le créneau du lendemain. Distances et chronologie validées,
pas de téléportation ni de double routine simultanée. Seuls les logements des
témoins étendent la carte d'auteur ; aucun raccourci entre les anciennes rues.
Pas encore une simulation de journée complète ou des commerces de ces PNJ.

Deux personnes peuvent avoir observé le même acte avec des souvenirs différents.
Il n'y a **pas** de témoin décisif systématique. Certains cas n'ont que des
souvenirs de contexte, d'autres aucun témoin annexe. La future sélection des
enquêtes résolubles peut ajouter une source, mais ne doit pas modifier le crime.

## Descriptions, ambiguïté et rôle causal

`Appearance` attribue à tout le casting un manteau (sombre/clair/coloré) et une
taille grossière, via un RNG séparé, sans argument coupable/victime. Aucun innocent
n'est repeint pour devenir le double du meurtrier.

Le souvenir peut ne retenir qu'une silhouette, la teinte du manteau ou la taille.
Un détail unique n'est pas sélectionné comme signalement ; on ne fabrique pas un
candidat incompatible pour gonfler le support à deux. Le validateur contrôle
≥2 personnes pour chaque description et pour **le récit entier d'un témoin sur
une même personne**, pas seulement chaque phrase/option de dialogue.

Projection : un entretien donne tous les souvenirs du témoin en un paquet,
vérifié aussi par `DiscoveryPlan`. Deux témoins indépendants peuvent en revanche
se croiser. Exemple graine 235 : manteau clair → deux suspects ; petite taille →
deux suspects ; l'intersection identifie l'agresseur. Aucun des deux récits seuls
n'identifie une personne.

**La simple présence n'est pas une culpabilité.** Les souvenirs de trajet,
rendez-vous, départ et manipulation de boisson sont actuellement contextuels :
leur support reste toute la population. Seul le signalement d'une agression
directement vue peut réduire les personnes compatibles avec l'acte violent.
Une intervention sur le verre + une analyse ne prouve pas encore que c'était la
seule intervention, ni que le témoin a vu la contamination mortelle : ce lien
causal doit être modélisé avant de devenir discriminant.

Les apparences sont des faits latents. L'audit d'identité suppose le casting et
ses apparences connus ; **leur découverte/comparaison par le joueur n'est pas
encore implémentée**. Aucun profil privé, support, intention ou identifiant
d'objet utilisé n'est exporté dans les textes publics. Une identité unique dans
cette projection ne certifie pas la reconstitution du crime ni la jouabilité.

## Acquisition et CLI

L'examen de la scène en étape 7 produit une référence photographique déclarative
de la victime (pas un nouveau bitmap). L'entretien nécessite cette référence et
la présence réelle du témoin à son poste. Il est consommé une seule fois. La
lecture de `public_catalogue` ne modifie jamais le journal.

```bash
python scenario_sampler.py --step 7 --seed 42 --method poisoned --walkthrough
python scenario_sampler.py --step 7 --seed 235 --walkthrough
python scenario_sampler.py --step 7 --seed 17 --situation agreed_meeting --json
python scenario_diversity.py --count 500 --seed 0 --witnesses
python -m pytest -q tests/test_scenario_witnesses.py
```

Le walkthrough attend les délais et respecte les fenêtres de présence, mais
**ne simule ni déplacements du détective, ni PA, ni autorisations**. Les créneaux
des témoins annexes sont limités au lendemain dans cette première version.
L'ancien solver lit les nouvelles actions/sources via l'adaptateur déjà existant ;
pas de nouvelle dépendance mobile ou serveur.

## Audit empirique

500 graines, crime identique à l'étape 5 : 160 suivis, 171 rendez-vous, 169 sorties.
4 806/4 806 artefacts atteints dans le walkthrough. Souvenirs : 169 services,
90 ajouts au verre, 102 agressions, 194 départs, 50 rencontres, 28 trajets communs,
30 coprésences et 85 rendez-vous manqués. Ces comptes sont des souvenirs, pas
autant d'événements distincts (deux témoins peuvent voir le même acte).

Après toutes les sources : 443 cas à cinq candidats, 10 à quatre, 23 à trois,
23 à deux, **un à un**. 57 cas resserrés ; pas 500 enquêtes devenues résolubles.
Le vrai agresseur reste compatible partout ; chaque entretien complet garde ≥2
candidats pris isolément. Ne pas confondre la convergence de l'exemple 235 avec
une certification méthode/mobile/chronologie.

Validation : **141 tests dédiés aux témoins**, corpus seedé de 100 cas dans ces
tests, six noyaux × trois situations, visibilité/attention/commutes invalides,
absence de savoir, ambiguïté du récit entier, croisement indépendant et isolation
du client. **1 316 tests ciblés** sampler/noyau/exécution/moyens/découverte/témoins/
solver passent ; audit externe 500 graines ci-dessus. Compilation Python et
`git diff --check` passent. Pas de nouveaux screenshots : aucun rendu ou UI
modifié dans cette étape offline.

## Prochaine couche

Manifestations sociales et canaux de connaissance : qui a reçu quel message,
qui connaissait une séparation, un conflit ou un rendez-vous. Écrire d'abord les
faits/communications, puis les souvenirs ; la cible d'un événement du noyau
n'est pas automatiquement un témoin coprésent. Ajouter ensuite les liens entre
observations indépendantes, apprendre les apparences, rejeter les crimes parfaits
et les raccourcis, auditer les recettes, puis adapter au moteur du jeu.
