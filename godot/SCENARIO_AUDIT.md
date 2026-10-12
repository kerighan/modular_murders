# Audit des chemins de résolution — 9 octobre 2026

## Solver indépendant du générateur

`investigation_solver.py` prend un `ScenarioGraph` et des actions déclaratives :
identifiant, type moteur, méthode narrative, observations produites, observations
requises (ET), coût entier positif. Aucune dépendance à `Game`, `CaseStory`, aux
sauvegardes ou à Godot. Un autre générateur peut fournir ces mêmes données.

État = observations connues, **pas seulement les suspects restants** : le constat
horaire ne filtre personne, mais débloque la vidéo. Une action peut révéler
plusieurs indices ensemble ; des sources alternatives restent des actions
distinctes. Les flèches de pistes ne deviennent pas des préconditions inventées.

Dijkstra + comptage dynamique de tous les parcours de coût minimal. Le solver
vise une déduction unique, pas un identifiant de coupable fourni comme cible.
Il est toutefois un planificateur offline connaissant les résultats des sources,
**pas un détective aveugle simulé**. Les limites de calcul échouent explicitement,
sans tronquer silencieusement les alternatives.

Mesures : certificats logiques minimaux ; coût et nombre de parcours optimaux ;
part des parcours passant par chaque action/méthode ; action finale ; réduction
du nombre de candidats ; coût après retrait d'un type d'action, ou impossibilité.
Une méthode optimale à 100 % n'est pas forcément obligatoire : une autre voie
plus coûteuse peut subsister. L'ablation les distingue.

La centralité fournie en complément porte sur le graphe dirigé
observation → action → observation. La [betweenness NetworkX](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html)
mesure des chemins courts entre paires de nœuds, pas nécessairement des enquêtes
gagnantes. Elle ne représente pas les préconditions ET ni les sources OU : le
solver est la mesure principale, pas cette projection. Un test montre deux
actions obligatoires ayant pourtant une centralité nulle.

## Projection actuelle et résultats

```sh
python scenario_audit.py --seed 42 --json
python scenario_audit.py --count 1000
```

`scenario_audit.py` est l'adaptateur concret : regroupe les documents obtenus par
une même fouille, normalise leurs copies, reproduit les préconditions réelles de
la vidéo (`trace` ET `clock`) et ajoute l'attestation + alibi original vérifié.
Deux buts séparés : identifier une personne ; satisfaire les observations
requises actuellement pour la reconstitution. La confrontation finale n'est pas
comptée comme un nouvel indice discriminant.

Graines 0–999 : 601 vols, 158 dossiers, 241 vengeances ; 1 000/1 000 résolvables
dans cette projection. Coût minimal toujours quatre actions d'investigation.

| Mesure | Déduction unique | Conditions de reconstitution |
|---|---:|---:|
| Affaires où la vidéo est incontournable | 100 % | 100 % |
| Recette « 3 lectures + 1 vidéo » | 95,64 % | 100 % |
| Recette « 2 lectures + 1 alibi + 1 vidéo » | 4,36 % | 0 % |
| Vidéo comme dernière action optimale | 74,35 % | 75 % |
| Nombre moyen de parcours optimaux | 47,09 | 45,22 |

Chaque affaire pèse autant ; ses parcours optimaux sont pondérés uniformément.
Ces pourcentages ne prédisent pas le comportement réel des joueurs. Les dizaines
de parcours sont surtout des permutations/copies de sources, **pas** autant de
raisonnements différents. Les recettes sont donc regroupées sans leur ordre.

Limites : déplacements, tours, occupants/serrures, autorisations, QTE, témoignages
de traits et indices physiques hors narration exclus. Les lieux sont supposés
accessibles, l'autorisation acquise. Aucun score global de « fun », aucune
affirmation que la vidéo est indispensable à **toutes** les voies du jeu complet.
L'audit ne change pas les règles ni la génération. Il n'est pas embarqué dans
l'APK. Les scènes sociales ajoutées en v11 sont de l'orientation/ambiance, pas
des observations incriminantes certifiées ; elles ne sont pas comptées ici.

## Modularité : frontière stable, moteur encore spécialisé

La séparation est bonne côté rendu, **pas encore complète côté déduction** :

```text
Monde / générateur (CaseStory aujourd'hui)
    → sources, relations, événements et observations
Moteur Python (coûts, connaissances privées, journal, replay)
    → vue publique JSON et options légales
Godot / CLI (lieux, cibles, portraits, dialogues, carnet)
```

Contrat client à préserver : `places` / `adjacency` / `routes`, `present`,
`staff` / `fixtures` / `doors` avec options légales ; `journal` et `leads` ;
répliques `conversation` avec un locuteur public, et maintenant des `beats`.
Les clients ne calculent pas les supports et ne connaissent pas le coupable.

Nouveaux contrats indépendants de la trame :

- `presence.places` et `.districts` : effectif et personnes visibles telles que
  ce détective les connaît. Identité/apparence non découverte → silhouette ;
  pas de relation, culpabilité ni connaissance d'un autre joueur. Les effectifs
  concernent les candidats, pas les PNJ de service. Extension du radar public
  existant (personnes dans les lieux, fenêtres occupées).
- Hook fournisseur `scenes_at(place, people)` : identifiant stable, acteurs,
  répliques `{actor, text}`. Le moteur valide la présence, masque les noms non
  appris, traduit les portraits, et fournit une action `listen` gratuite.
  Godot déclenche à l'entrée effective dans la pièce, **pas** au déplacement
  dans le quartier ni à l'affichage d'une vue. CLI propose l'écoute explicitement.
- `Player.scenes_seen` par détective/enquête : consommation par action légale,
  note privée exacte et replay. La lecture d'une vue ne consomme rien. Un même
  échange ne revient pas dans un autre lieu ni après reprise. Pas d'échange
  déclenché au milieu d'un interrogatoire ou de mouvement des PNJ hors phase.

Encore spécialisés : `CaseStory` construit directement ses trois supports ;
les clés `access/meeting`, `trace`, `clock`, `camera`, la confrontation complète
et quelques règles d'affichage/actions Python restent liées à cette trame.
Un nouveau graphe causal peut conserver le rendu sans réécrire Godot, **mais**
une nouvelle logique de preuve devra remplacer ces règles derrière le contrat.
Ce n'est pas encore un plug-in de générateur entièrement interchangeable.

Prochaine refonte : sources/opérations d'enquête déclaratives à préconditions et
effets ; évaluateur de déduction/reconstitution fourni par le générateur ;
adaptateurs conservant la vue publique. Audit des changements sur un corpus,
en conservant ≥2 candidats par observation/artefact, plusieurs voies légales,
et aucun raccourci d'identité ou de « seul menteur ».
