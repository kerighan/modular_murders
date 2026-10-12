# Nexus City — direction visuelle

## Allées lisibles au Néon Bleu — version 0.23

Scène de crime dégagée au centre/droite, à distance des clients, du comptoir,
des tables et du billard. Valise à l'avant gauche. Personnages dans des allées
distinctes ; contact éventuel placé après les clients, pas sur le corps.
Sélecteurs tactiles 100 × 64, titres courts, pas de recouvrement objets/personnes
dans le cadrage initial 18:9/20:9 testé. Aucun repositionnement après collecte.
Captures réelles seed 5 avant/après enquête + stress visuel synthétique avec
plusieurs clients/contact. Rendu desktop, pas de téléphone physique.


## Dialogue accessible et coût lisible — version 0.22

Première ligne : relation avec la victime / alibi. Deuxième : observations /
tensions. Les quatre questions sont visibles sans sous-menu ni scroll en
18:9 et 20:9. Métier/habitudes et personnes évoquées restent dans deux dossiers
secondaires. Nouvelle question « 1 PA » ; réponse entendue « gratuit ».
À zéro PA, nouvelle question grisée, relecture disponible, sortie « Revenir à
la ville » et statut « 0 PA · Relecture gratuite ». Dernière réponse conservée
à l'écran jusqu'à son acquittement, aucune interruption de lecture.
Relance générique supprimée des PNJ ; premières questions concrètes au barman.
Captures `guidance-dialogue-*-v22-*.png`, rendu desktop/touches natives.

## Permanence du décor — version 0.21

Un objet appartient au lieu, pas à la liste des actions disponibles. Inspection,
fouille, prélèvement ou lecture ne changent ni sa forme ni sa position. Seuls
les sélecteurs/halos reflètent les possibilités restantes. Slots stables, même
quand un objet est retiré. Valise portable pour le relevé d'empreintes, pas de
bureau qui apparaît dans la rue. Verre, arme et placard ont un modèle distinct.

Le corps reste sur place après constat. Un choix explicite de transfert pour
examen le retire de la scène et le place sur la table de la morgue. Cette table
existe avant la demande ; les autres objets de la scène ne bougent pas.
Captures comparatives natives desktop téléphone 18:9/20:9 :
`guidance-fixtures-*-v21-*.png`. Pas de nouvelle lumière/texture/viewport.

## Carnet de lecture et bar voxel — version 0.20

Carnet en deux zones : large page de lecture à gauche, portraits compacts en
colonne à droite. Onglets fins et soulignés, hiérarchie titre/source/contenu,
texte courant 16–17 px avec interligne. Une seule preuve dépliée ; fiche du
suspect sélectionné séparée de la liste, récit et corroboration prioritaires.
Biographie secondaire repliable. Fermeture en haut et options rares dans « ••• »
libèrent le bas de page. Chaque zone se parcourt au doigt indépendamment.
Fond encre, source ambre/cyan, vert réservé aux états corroborés/confirmés,
priorité personnelle cyan et exclusion atténuée/reléguée : règles inchangées.

Première pièce spécifique au Néon Bleu, référence `../Neon Noir Voxel Barroom.png` :
briques sombres, carrelage serré, contre-jour rouge au comptoir, bouteilles et chat
néon, lampes ambre, banquettes et billard vert. Clients réels dans la salle,
barman derrière le comptoir ; pas de silhouettes de faux suspects pour meubler.
Billard décoratif en attendant des activités réellement générées. Géométrie
fusionnée en deux meshes, trois lumières sans ombres, aucun bitmap/viewport ajouté.
Les autres lieux conservent pour l'instant leur pièce commune.

Captures natives desktop téléphone 18:9 et 20:9 inspectées :
`guidance-notebook-reading-v20-*.png`, `guidance-notebook-dossier-v20-*.png`,
`guidance-notebook-populated-v20-*.png`, `guidance-barroom-v20-*.png`.
APK solo v20, enquêtes précédentes conservées ; pas de test GPU physique Android.

## Lisibilité et présence — version 0.10

Service rose à l'accueil, suspects dorés dans la salle, détective cyan.
Les actions sont portées par un objet voxel ou un personnage : coffre, papiers,
terminal, téléphone, table d'examen, poubelles. Les paliers affichent les portes
réelles du quartier et un habitant au seuil si présent. Même World3D/caméra,
pas de viewport ajouté ni de textures ; pièce générique encore assumée.

Questions : bloc augmenté, cinq boutons entièrement visibles en 1080×540 et
1200×540. Réponses ambrées ; pensée du détective sur fond/bord cyan, portrait à
chapeau, italique. Carnet trié par choix personnels avec déplacement animé des
cartes et priorité cyan. Le monde seul se désature à 0 PA ; UI inchangée.

Captures inspectées `questions-full-phone-v10*.png`, `detective-thought-phone-v10*.png`,
`palace-usher-phone-v10*.png`, `apartment-hallway-phone-v10*.png`,
`notebook-following-phone-v10*.png`, `exhausted-monochrome-phone-v10*.png`.
Tests natifs du rendu desktop, pas de validation GPU sur appareil Android.

## Lounge global — version 0.8

Première pièce générique inspirée de `Neon Noir Cabaret Lounge.png` : rideaux
magenta, scène basse, bar rétro-éclairé, tabourets, tables-lampes et plantes voxel.
Environ 25,5 × 19,5 unités, grands espaces libres pour une population future.
Détective côté tables, silhouette à chapeau et halo cyan « VOUS » ; suspects
côté salle, halo doré. Un toucher sur le personnage / halo lance le dialogue.

La pièce n'est **pas une modale** : Node3D du monde global, même caméra et
post-traitement que la ville, téléportation visuelle à l'entrée / retour à la
sortie. Les seuls overlays sont les commandes et le dialogue. Glissement /
zoom dans la pièce. Pas de deuxième viewport, textures, ombres locales ou
simulation autonome ; lumières limitées et matériaux groupés pour Android.

Captures inspectées : `lounge-phone-v8.png` (1080×540) et
`lounge-phone-v8-20x9.png` (1200×540). `lounge_smoke.gd` vérifie le même World3D,
l'absence de SubViewport, le halo tactile et le retour caméra vers la ville.
Le décor est volontairement générique, pas encore un intérieur distinct par lieu.

Carnet : nouvel onglet Pistes, objectifs et lieux révélés uniquement. Menus
longs repliés dans les dialogues ; nom discret aux pieds des personnages.
Ville : cadrage un tiers plus proche ; scène du crime toujours dehors, trois
parcelles possibles, petites traces de sang voxel. Le reste de la ville reste approuvé.

## Enquête incarnée / notes — version 0.7

Ville approuvée inchangée. Onglets Personnes / Notes intégrés au carnet :
portraits et dossiers d'un côté, journal complet récent en premier de l'autre.
Documents / vérifications bord cyan ; déclarations / témoignages bord ambre.
L'aperçu distingue heure, objet, mobile encore à établir. Les pistes sont des
boutons « Repérer », sans téléportation ni PA. Réduction des hauteurs de pied
de page pour garder un document et son bouton visibles en paysage téléphone.
Dialogue : « Parler de quelqu'un… » ouvre seulement les personnes identifiées,
en grille tactile, sans surcharger la première sélection. Le carnet distingue
explicitement relation déclarée / récit des témoins / contradiction à confronter.
Captures `story-notes-phone-v7*.png`, `story-people-questions-phone-v7*.png`,
`story-people-answer-phone-v7*.png`, revues en 18:9 et 20:9.

## Domiciles des personnages — version 0.6

La fiche identifiée donne le domicile avant les traits et l'alibi : quartier
réel + appartement. Ce bloc est touchable pour repérer le quartier par un
glissement de caméra, pas pour se téléporter. Il ne crée pas de nouvelle flèche
distante ; les entrées restent locales au détective. Les inconnus ne montrent
aucune adresse. Captures `residence-notebook-phone-v6*.png` et
`residence-located-phone-v6*.png`, revue en formats téléphone 18:9 / 20:9.

## Lecture par quartiers — version 0.5

À distance : un descriptif airy (nom du quartier, ses lieux, coût en PA), sans
icône de déplacement ni cible au sol. Sur place : seulement les entrées locales.
Au-delà de trois lignes, les appartements sont résumés par « autres entrées » ;
la liste complète est accessible sur place. Les labels qui se chevauchent sont
masqués, avec la liste « Quartiers » en solution de secours. Les décors et la
topologie approuvés ne changent pas. Pas d'entrée de bâtiment fictive sur une rue.

Le carnet ne barre plus automatiquement une piste selon la déduction du moteur.
Une commande personnelle « Écarter / Réactiver » diminue l'opacité à 42 %, sans
déplacer la fiche ni modifier la partie. Les choix persistent par enquête. Les
portraits inconnus restent en silhouette et dans l'ordre aléatoire de la vue.
Tests tactiles et captures 18:9 / 20:9 : `districts-overview-phone-v5*.png`,
`notebook-manual-phone-v5*.png`.

## Enquête mobile — version 0.4

La ville 3D reste inchangée. L'interface d'interrogatoire est désormais une
boîte RPG basse : portrait voxel, nom, question, véritable réponse révélée
progressivement, puis choix de questions. On peut toucher pour accélérer la
lecture. Une seule notification discrète en haut à droite remplace le journal
empilé ; les résultats détaillés des autres actions restent lisibles page par
page. Décors d'intérieur dessinés en code, sans textures ni viewport 3D ajouté.

Les trajets aboutissent à l'extérieur du quartier ; bannière courte et pas du
détective à l'arrivée, puis entrée explicite. À 0 PA : dernière réponse,
fondu vers la carte, attente de la fin manuelle. Les routines des habitants ne
changent qu'ensuite : « La ville continue », quelques pas anonymes, nouveau
tour. Aucun trajet secret de suspect n'est montré.

Carnet : preuves certaines et sources fiables dans un volet séparé ; fiches
personnelles avec petits portraits, silhouette générique sans traits cachés
pour les inconnus, pistes ouvertes avant les personnes écartées. Alibis et
déclarations non prouvées sont distincts des preuves. Scroll tactile sur les
fiches. `rpg-*.png` montre les itérations 18:9 / 20:9 ; validation GUI desktop,
pas mesure de performance sur Android matériel.

Référence : `../Nexus City sous la pluie néon.png`. Le rendu est une ville 3D voxel,
avec une caméra en perspective à focale longue (FOV vertical 38°), des matériaux nocturnes, des façades
quadrillées, des fenêtres chaudes et des publicités cyan, bleu électrique et magenta.

Les rues occupent 4,4 unités entre des îlots de 7,6 unités, avec de vrais trottoirs,
bordures et passages piétons. Les bâtiments utilisent six assemblages d'emprises :
barres transversales, barres longitudinales, ailes en L autour d'une cour,
volumes en retrait sur un socle, tours jumelles et immeubles d'angle avec contreforts.
Les façades et toitures s'adaptent aux dimensions réelles de chaque volume, sans
étirer un modèle carré. La majorité des bâtiments de décor restent des immeubles bas.
Un pont à câbles suspendu relie Rue Verlaine et Chez la victime au-dessus de la rue,
avec tablier, suspentes, portiques, garde-corps néon et piétons.

La grille de `city.py` est maintenant de 5 × 4 cases. Trois complexes s'étendent
réellement sur plusieurs parcelles : hôpital 2 × 1, résidence Verlaine 2 × 1 et
Palace en L 1 × 2. Leurs trottoirs sont continus et les carrefours de la rue
intérieure sont supprimés. Ce regroupement est calculé à partir des cases libres
de la grille reçue ; aucune case portant un autre lieu n'est absorbée.
Le passage Verlaine–victime reste une arête du graphe, explicitement déclarée
dans `SKYBRIDGES`, même si ces deux lieux ne sont plus voisins dans la grille.
Les immeubles et placettes décoratifs sont assombris avec des matériaux partagés
à visibilité 0,18 ; leurs enseignes sont aussi atténuées. Il ne s'agit pas de
brouillard volumétrique coûteux.
Une placette arborée ouvre le quartier. Les toits comportent des gaines, ventilations,
antennes, escaliers, retraits et panneaux publicitaires. Le mobilier, les habitants,
voitures, arbres lumineux et train sont statiques pour cette première passe.

## Organisation

- `city_visuals.gd` : géométrie, palettes, textures publicitaires en pixels, éclairage.
- `city_navigation.gd` : cibles tactiles, noms de destinations, listes et badges d'avatars.
- `touch_momentum.gd` : arbitrage global tap/drag, inertie carte et menus, pincement.
- `board_zones.gd`, `board_zones.gdshader` : essai optionnel de frontières au sol,
  une seule surface fusionnée, sans lumière ni interception des gestes.
- `voxel_avatar.gd` : petits portraits dessinés en code, sans textures ni vue 3D supplémentaire.
- `voxel_surface.gdshader`, `voxel_light.gdshader` : surfaces opaques et lumineuses.
- `neon_sign.gdshader` : affiches avec mipmaps pour éviter le scintillement au zoom.
- `wet_street.gdshader`, `neon_pool.gdshader` : asphalte et reflets stylisés.
- `city_grade.gdshader` : halo en deux couronnes de huit échantillons et vignette, sous l'interface.
- `entrance_pulse.gdshader` : respiration lumineuse douce des chevrons, période 2,6 s,
  variation de 10 %, sans extinction ; les textes ne clignotent pas.
- `building_fade_*.gdshader` : variantes translucides activées uniquement pour les bâtiments proches.
- `main.gd` : client existant, branchement de l'art et habillage de l'interface.

Les reflets sont une approximation graphique statique, pas une réflexion physique
des objets. Aucun SSR, SDFGI, brouillard volumétrique ou asset IA n'est nécessaire.

## Captures et itérations

Depuis la racine du dépôt :

```bash
bash godot/review.sh
bash godot/review.sh --low-fx
godot --path godot -- --art-preview
godot --path godot -- --art-preview --detail
godot --path godot -- --art-preview --hero
godot --path godot -- --art-preview --bridge
godot --path godot -- --art-preview --campus
godot --path godot -- --art-preview --courtyard
```

`review.sh` produit `art/captures/overview.png`, `detail.png`, `hero.png`, `bridge.png`,
`campus.png`, `courtyard.png` et vérifie
les erreurs de scripts et de shaders. La fixture de revue est indépendante du serveur ;
elle ne constitue jamais une vue ni une liste d'options envoyées au moteur de jeu.
`--wide` offre une vue distante ; `--ortho` permet de comparer l'ancienne projection ;
`--no-transit` masque le viaduc ; `--dump-art` écrit
les textures portrait dans `/tmp/nexus-ad-*.png`.

Les captures `iteration-01.png` et `iteration-06.png` conservent deux étapes de
comparaison : premier rendu encore dense et clair, puis rues élargies et bâtiments
bas avant le passage à la perspective et au contraste nocturne final.
`before-variety.png` conserve la vue avant la diversification des emprises.

Le client normal garde `ws://127.0.0.1:8000/ws/42/Ada`. Pour un serveur de test isolé :

```bash
godot --path godot -- --city --shot \
  --server-url=ws://127.0.0.1:8766/ws/42/Ada --shot-path=/tmp/nexus-game.png
```

Les modes existants `--enter`, `--inside` et `--carnet` restent disponibles.
La caméra se déplace par glissement ; le zoom utilise la molette, le pincement à
deux doigts ou un geste de grossissement. Le zoom en perspective déplace la caméra
en conservant sa focale, et les transitions de lieux interpolent son point de visée.

## Navigation et avatars

La caméra de jeu est plus rapprochée (hauteur visible 27 unités, contre 36 auparavant).
Les noms sont posés près des entrées sans trait de liaison ni boîte permanente ;
un fond translucide apparaît au survol ou au focus. Les anciennes étiquettes de
toiture sont masquées pour éviter les doublons. Chevrons et libellés sont cliquables.
Les zones des repères au sol sont réservées lors du placement des libellés voisins.

Les appartements d'une même rue sont regroupés dans une liste tactile, ainsi que
le lieu public correspondant quand on vient d'une autre rue. Le taxi a sa propre
liste, plutôt que des dizaines de destinations simultanées sur la carte. Les lieux
à plusieurs pas indiquent leur coût ; ceux qui dépassent les PA restants n'ont
plus de pancarte. Les textes restent près des entrées réellement dans le champ ;
en cas de collision, le texte disparaît mais le repère au sol reste touchable.
Aucune pancarte n'est rappelée en bord d'écran. Les notifications sont intégrées
à la page intérieure sans recouvrir les actions.
Les notifications de carte sont masquées lorsque le carnet ou une liste de
destinations est ouvert : elles ne peuvent pas intercepter leurs boutons.

Le drag tactile démarre aussi depuis les pancartes et les boutons de menu : au-delà
de 10 pixels logiques, la pression du bouton est annulée et le geste prend le relais.
L'inertie décroît exponentiellement (indépendante du framerate), s'arrête aux
limites des menus et au toucher suivant. Le tap d'arrêt ne déclenche pas l'action
sous le doigt. La vitesse de déplacement utilise la taille logique de l'interface,
pas la résolution physique du téléphone. Le pincement reste distinct du drag.

### Essai de lecture « plateau »

Contours fins posés sur l'asphalte, or pour le quartier occupé et cyan pour les
voisins publics accessibles à 1 PA. Les grandes parcelles restent une seule zone :
pas de frontière au milieu de Verlaine, du Palace ou de l'hôpital. Les ouvertures
et petits chevrons indiquent uniquement les passages du vrai graphe transmis dans
`view.adjacency`, dont le pont Verlaine–victime. Deux parcelles qui se touchent sans
être reliées dans le graphe n'obtiennent pas de passage. Les appartements gardent
leurs entrées regroupées : les frontières représentent les quartiers publics,
pas une nouvelle règle de déplacement. Aucun changement de topologie du jeu.

La première version en traits très fins est conservée dans `zones-first-phone.png`.
Après comparaison à 18:9, les traits ont été légèrement élargis et les passages
voisins renforcés. Captures finales : `zones-near-phone.png`, `zones-overview-phone.png`,
`zones-off-phone.png` et `zones-20x9.png`. Actif par défaut pour le test, retirable
dans Carnet → « Frontières · essai », ou avec `--no-board-zones` sur desktop.
Une seule surface, aucun label/lumière ajouté ; elle respecte l'occlusion 3D.

Le détective joué a un manteau contrasté, un halo doré au sol et un badge
translucide « VOUS » avec avatar ; les autres détectives ont leur couleur propre.
Les portraits de personnages utilisent uniquement l'identité et la description
publique transmise dans `present.look`, sans révéler de traits cachés.

Les bâtiments les plus proches, situés devant le point de visée, s'estompent
progressivement ; le complexe du lieu courant est protégé. Au plus trois nouveaux
bâtiments sont ciblés à la fois. Façades, fenêtres et affiches s'atténuent ensemble,
puis retrouvent leurs matériaux opaques quand on recule. Les trottoirs, personnages
et repères restent visibles. Cette adaptation est compatible OpenGL : elle n'utilise
pas `GeometryInstance3D.transparency`, ignorée par Compatibility selon la
[documentation Godot](https://docs.godotengine.org/en/stable/classes/class_geometryinstance3d.html).

Références de navigation consultées : marquages intégrés de
[Monument Valley, galerie officielle](https://monumentvalleygame.squarespace.com/portfolio),
petits nœuds de chemin de
[Lara Croft GO, captures officielles](https://play.google.com/store/apps/details?hl=en&id=com.squareenixmontreal.lcgo).
Leur logique de discrétion est adaptée au thème néon, pas copiée telle quelle.

### Revue téléphone et interactions

Android utilise une base UI 960 × 540, des textes et contrôles agrandis, et un aspect
`expand` : le 20:9 est réellement rempli, pas recadré en 16:9. `--phone-ui` simule
ce réglage sur PC. Captures conservées : `phone-20x9.png` (2400 × 1080),
`routes-18x9.png` (1440 × 720), ainsi que `navigation.png`, `mobile.png`,
`destinations.png`, `taxi.png` et `interior.png` pour les itérations de l'interface.

Sur un serveur de revue isolé, et non une partie utilisateur :

```bash
xvfb-run -a -s '-screen 0 2400x1080x24' godot --path godot --resolution 2400x1080 \
  --log-file /tmp/nexus-phone.log --rendering-driver opengl3 -- \
  --city --shot --phone-ui --server-url=ws://127.0.0.1:8766/ws/142/Ada \
  --shot-path=/tmp/nexus-phone.png
```

`--route-overview` dézoome pour inspecter tous les coûts ; `--close-camera` rapproche
encore la caméra. `--destinations` ouvre la liste d'appartements ; `--taxi-list` ouvre le taxi.

Un test GUI avec clics simulés vérifie l'estompage/restauration des matériaux,
le chevron tactile, la liste d'appartements, l'avatar et un trajet réel de 2 PA :

```bash
xvfb-run -a godot --path godot --log-file /tmp/nexus-ui-test.log \
  --rendering-driver opengl3 --script res://tests/navigation_smoke.gd -- \
  --city --server-url=ws://127.0.0.1:8766/ws/42/Ada
```

Ce test modifie la partie de revue ; utiliser une table neuve. Le rendu GUI est
requis pour tester les véritables zones de clic, pas seulement leurs callbacks.

## Android

Le projet utilise Compatibility / OpenGL ES 3, MSAA 2× et une seule lumière avec
ombres. Trois petits éclairages colorés sans ombres complètent le rendu normal.
Les boîtes et faces sont fusionnées par bâtiment et matériau ; les trottoirs et le
mobilier partagent quatre surfaces pour la ville entière (deux normales, deux assombries).
Les faces inférieures et le
volume des marquages au sol sont supprimés. Les affiches utilisent seize petites
textures partagées, générées une seule fois, sans dépendance externe.

`--low-fx` désactive les ombres, les trois éclairages colorés et le halo plein écran,
en conservant les bâtiments, enseignes, fenêtres et reflets stylisés.

Les captures affichent triangles, meshes, appels de rendu et durée de frame.
Les chiffres PC en rendu logiciel llvmpipe ne prédisent pas les performances Android :
le budget final et le choix du profil demandent une mesure sur téléphone réel.
L'export Android et les interactions tactiles restent à valider sur appareil.
Les cibles font 72 pixels logiques ; ce ne sont pas automatiquement des dp Android.
Leur taille finale, les zones sûres des encoches et la charge des surfaces translucides
doivent être mesurées sur appareil. La référence Android recommande au moins
[48 dp de cible tactile](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views).

Le protocole WebSocket reste celui de `HANDOFF.md`, avec deux ajouts rétrocompatibles :
`view.routes` fournit les coûts/états/clés de marche et `['walk', destination]` suit
un plus court chemin en consommant autant de PA que d'arêtes. Les clés `move`
existantes restent valides (voisin à pied ou taxi à 1 PA). Le serveur valide les PA,
les portes, l'occupation, les conversations et le tour actif ; le client ne calcule
ni n'invente de clé. Les nouveaux trajets sont rejouables dans l'historique.
Voir `tests/test_navigation.py` pour les coûts, refus, taxi, pont et replay.
`Box` reste le marqueur du seuil et `Label` l'étiquette masquée du lieu ;
la sélection ne recolore plus tout l'immeuble.
