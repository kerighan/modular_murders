# Passation : client Godot

## État actuel — solo 0.9 : objets facultatifs (9 octobre 2026)

`builds/nexus-city-solo-debug-v9.apk`. Suppression de la chaîne de consigne /
intermédiaire / remise : le reçu ambigu de Marius ne peut plus être généré.
Bracelet = effet d'un vol ; USB = copie à faire disparaître ; vengeance sans
objet artificiel. Objet caché anonymement dans un lieu public ou introuvable,
jamais requis pour gagner. `sources.access` / `sources.meeting` ouvrent des
groupes d'occasion, `loss` / `cache` n'identifient personne. `view.story.object_status`
est privé et limité à ce qui a été appris. Même lounge / ville qu'en v8.

`RULES_VERSION=9`, nouvelle préparation après mise à jour, anciens fichiers
préservés. Aucun changement de schéma Loom. Retour d'accusation erronée sans
inventer un alibi. 723 tests ; 3 affaires CLI terminées / reprises (42, 7, 4),
aucun objet récupéré sur ces chemins. Audit 1 000 générations : 390 objets
introuvables, 369 caches, 241 sans objet. Contrôles carnet / dialogue en 18:9
et 20:9, captures `story-notes-phone-v9*.png`, plus fixtures cache / sans objet.
Voir [contrats](SCENARIO_GRAPH.md) et [rapport CLI](PLAYTEST_CLI.md).

APK final signé, 10 modules Python / 27 assets Godot identiques aux sources.
Modules embarqués exécutés sous CPython 3.13 sur 0 / 3 / 4 / 7 / 42 / 93,
y compris découverte précoce d'une cache à identifier, sans serveur ni Loom.
SHA256 v9 : `262d69bfa08e5d68efaa3c5ef2a74526fb37fb1b58c13de9ead808768b935b08`.

## État actuel — solo 0.8 (9 octobre 2026)

`builds/nexus-city-solo-debug-v8.apk`. Les paragraphes v7 et précédents ci-dessous
sont historiques : ils ne décrivent plus les règles de mensonge actuelles.

- **Intérieur global** : `interior_lounge.gd` est un Node3D dans le même World3D
  que la ville, à (2048, 0, 2048), échelle 1,5. Même caméra téléportée à l'entrée,
  restaurée à la sortie ; aucun SubViewport ni panneau de pièce. Bar, rideaux,
  scène et espace libre pour peupler plus tard. Détective cyan / chapeau,
  suspects dorés, halos tactiles : toucher commence directement l'interrogatoire.
- Le glissement et le zoom restent disponibles dedans. Le far clip intérieur
  exclut la ville distante. Trois lumières locales sans ombres ; géométrie groupée.
- Ville : zoom initial rapproché d'un tiers, crime sur trois parcelles extérieures
  possibles, même graphe et grille pour la logique / rendu ; gouttes voxel au sol.
- **Graphe d'enquête** : chaque observation incriminante et chaque artefact physique
  garde ≥2 candidats. À 12 suspects : trois axes partagés, toute paire ≥2, leur
  intersection seule isole le meurtrier. Ensembles de taille variable, pas « deux
  partout ». Les rôles de relais ne sont pas des preuves de culpabilité.
  Contrats détaillés : [SCENARIO_GRAPH.md](SCENARIO_GRAPH.md).
- Plus de mensonges d'innocents, de faux liens ni de mensonge qui désigne à lui
  seul le meurtrier. Les inconnus de la victime n'inventent pas de rumeurs.
  Témoins parcimonieux, connaissances rattachées à leurs vrais liens / conflits.
- Carnet **Pistes** : motif de la piste, prochain objectif, destinations déjà
  apprises ; facultatif, aucune navigation forcée. Notes exactes conservées.
- Fouille physique + documents réunis dans « Fouiller les lieux ». Documents
  lisibles dès le premier écran, choix volumineux regroupés en sous-menus.
  `talk_about` pendant une conversation consomme une question, pas un autre PA.
- `RULES_VERSION=8` protège les reprises : anciens scénarios refusés par Loom,
  ancienne sauvegarde Android conservée en `.invalid-*` puis nouvelle préparation.
  Pas de migration de collection : version dans le JSON existant.
- Validation : 679 tests Python ; voir le [playtest v8](PLAYTEST_CLI.md).
  Captures téléphone réelles 1080×540 et 1200×540, taps natifs et retour caméra
  vérifiés. Pas de mesure de performance sur appareil Android physique.
- APK final : mêmes sources vérifiées octet par octet (10 modules Python,
  27 assets Godot). Exécution des modules embarqués sous CPython 3.13 : graines
  0 / 3 / 7 / 42 / 93, contrats du graphe et import solo sans serveur / Loom.
  Signature debug identique aux anciennes versions, ARM64 / API 24 minimum.
  SHA256 : `9ed7ed14280c545dcd5fae553b0ca5d36fbb10c3b62fcd7c08879c3fa53d3212`.

## Historique v7

> Version solo 0.7 : `builds/nexus-city-solo-debug-v7.apk`. Première couche
> narrative offline (`narrative.py`, RNG distinct pour préserver les indices
> physiques) : vol / chantage / vengeance, objet disparu, pression partagée
> avec un innocent, intermédiaire, reçu, fenêtre du crime, ticket et caméra.
> Pas de mobile unique qui résout l'affaire : cinq pièces recoupées avant la
> confrontation finale. L'attestation d'un innocent doit être vérifiée ailleurs.
> Les domiciles innocents contiennent désormais des papiers et des pistes.
>
> Questionner une personne sur une autre : `talk_about, speaker, target` (1 PA),
> regroupé dans le dialogue sous « Parler de quelqu'un… ». Les voisins / proches
> ne connaissent pas tout le monde ; leurs récits restent des témoignages,
> jamais des traits certifiés. Meurtrier ET innocent peuvent nier un vrai lien
> avec la victime. Après témoignage contraire : `confront, sid, relationship`.
> Aveu du lien ≠ aveu du meurtre. `notebook[].relationship` sépare la déclaration,
> les sources et la contradiction. Pas d'inférence de culpabilité automatique.
>
> Carnet : onglets Personnes / Notes. `view.journal` est privé, chronologique,
> avec tour/type/titre/texte/source/personnes/pistes. Affichage récent en premier,
> textes complets, boutons « Repérer » = caméra seulement. Projet/pression si
> appris, pas si identité inconnue. Les notes exactes sont sauvegardées en JSON
> dans le champ Loom existant et dans la sauvegarde solo ; replay de l'état,
> puis restauration du texte réellement affiché, y compris une voix personnalisée.
> Nouveaux progrès publics : documents / recoupements, distincts des traits.
> Store Loom = writer exclusif : refuser une seconde ouverture en écriture.
> Une invitation permet aussi d'ouvrir la porte sans outil lorsque l'hôte est absent.
> Être surpris en train de fouiller bloque les conversations ordinaires, mais pas
> une confrontation sur un nouveau document : pas d'impasse narrative permanente.
>
> Android : première affaire aléatoire (tests `--seed=42`), module `narrative.py`
> embarqué ; toujours aucun serveur, Loom ou LLM requis. Géométrie 3D inchangée.
> CLI : `--offline --perfect --compact`, `n` Notes, `q` sauvegarder/quitter ;
> `NEXUS_SAVE=/chemin/test.loom` pour isoler les essais. Voir le nouvel ajout au
> [rapport CLI](PLAYTEST_CLI.md), distinct de l'audit v6 ci-dessous.
> Validation finale : 575 tests Python ; `rpg_smoke.gd` et
> `story_notes_smoke.gd` passent en 18:9 et 20:9 (rendu desktop, taps natifs).
> APK ARM64 signé avec le certificat des versions précédentes, 9 modules Python
> et 13 scripts Godot vérifiés octet par octet contre les sources. SHA256 APK :
> `c535fbe78d9455c17a8c6b5fab48c341ab4557f9664d061bcc993634467b2257`.
> Moteur réellement importé depuis le ZIP de l'APK sous CPython 3.13 :
> création des affaires 7 / 42 / 93 et import du transport solo OK.

> Audit de gameplay CLI : [PLAYTEST_CLI.md](PLAYTEST_CLI.md). Deux parties
> terminées (42, 93), QTE parfaits pour isoler les déductions ; audit de 1 000
> générations. Sang dans 38,6 % des affaires, toujours dupliqué 2–3 fois ;
> première création APK encore fixée à 42. Priorités proposées : confrontations
> contextuelles, chronologie/provenance, pistes dans les résidences innocentes,
> vraie conclusion. Diagnostic seulement : pas de nouvelles règles implémentées.

> Version solo 0.6 : `builds/nexus-city-solo-debug-v6.apk`. Chaque fiche identifiée
> affiche « Domicile » : nom du quartier et numéro d'appartement. Toucher cette
> adresse ferme le carnet et centre la caméra sur le quartier, sans action de
> jeu, entrée gratuite ou dépense de PA. Les entrées ne s'affichent toujours que
> dans le quartier où le détective se trouve réellement.
> `view.notebook[].home` = `{place, region, label, region_label}` si le détective
> connaît le nom, sinon null. Résidence issue du graphe réel, pas de la position
> actuelle du suspect ; information privée à chaque détective, reconstruite au
> replay, sans changer le format de sauvegarde ni les règles. Les anciens
> serveurs sans ce champ restent affichables (pas de domicile inventé).
> Tests : 522 cas Python, `rpg_smoke.gd` vérifie les adresses connues/inconnues
> et le tap natif qui repère le quartier sans changer la vue moteur. Captures
> `residence-notebook-phone-v6*.png`, `residence-located-phone-v6*.png`.

> Version solo 0.5 : `builds/nexus-city-solo-debug-v5.apk`. Navigation à deux
> niveaux : descriptifs distants des quartiers (`DISTRICT_NAMES`, lieux publics
> et appartements, coût réel en PA), sans cible ni flèche au sol ; entrées
> détaillées uniquement dans le quartier du détective. Pas d'« Entrer » pour
> une rue vide : « Explorer » seulement si une action locale existe. Le bouton
> « Quartiers » garde les trajets accessibles même si un descriptif est masqué
> pour éviter les chevauchements. Le graphe et les clés légales sont inchangés.
>
> Carnet : plus d'écartement automatique depuis `row.out`. « Écarter / Réactiver »
> modifie seulement l'opacité et la mention « Écarté par vous » ; aucune action
> n'est envoyée au moteur, les PA/preuves/accusations restent inchangés. Les notes
> personnelles sont persistées dans `user://case-notes.cfg`, séparées par graine
> solo + détective (ou URL serveur + détective), et réversibles. Pour isoler une
> revue, passer `--notes-path=/tmp/nexus-review.cfg`. Les inconnus gardent leur
> ordre initial aléatoire, pas un tri par identifiant du suspect.
> `tests/rpg_smoke.gd` vérifie désormais le tap d'un quartier, l'absence d'entrées
> distantes, la persistance/réactivation des notes, leur isolation par enquête,
> et l'absence d'écartement automatique, en plus du parcours RPG v4.
> Captures `districts-overview-phone-v5*.png`, `notebook-manual-phone-v5*.png`.

> Version solo 0.4 : `builds/nexus-city-solo-debug-v4.apk`. Les échanges passent
> par `rpg_dialogue.gd` : sélection d'une personne, questions autorisées,
> réplique exacte à dévoilement progressif, dernière réponse conservée.
> `view.conversation` est privé ; les événements historiques restent inchangés.
> `case_toasts.gd` signale les mises à jour sans empiler un journal.
> Carnet : fiches à petits portraits procéduraux, silhouettes inconnues,
> pistes actives en premier, preuves/alibis/déclarations séparés.
>
> Changement de règles : plus de passage automatique à 0 PA. Finir les questions,
> lire la dernière réponse, retour fondu à la ville, puis bouton « Terminer le
> tour ». `turn_transition.gd` masque l'intérieur AVANT d'envoyer la clé `end` ;
> les routines avancent uniquement dans `Game.do_end`, à la fin du cycle des
> détectives. Phase « La ville continue », quelques pas anonymes sur les
> trottoirs, puis titre du tour suivant. Les figures ne révèlent aucun trajet
> secret de suspect. QTE calque 8, au-dessus du fondu (propriétaire de retour).
>
> Déplacements : trajets de carte vers les quartiers publics uniquement,
> arrivée à l'extérieur + bannière + pas d'approche du détective. « Entrer »
> ouvre l'interface du bâtiment courant sans PA ; les appartements gardent leurs
> vraies clés/coûts/serrures dans la liste des entrées du quartier. Pas de graphe
> parallèle inventé côté client. La ville 3D approuvée est inchangée.
>
> Sauvegardes : JSON solo v2 conserve `legacy_auto_end`, longueur du préfixe à
> rejouer avec les anciennes règles. Les v1 se reprennent sans réinitialisation.
> Même mécanisme dans le champ JSON `history` de Store, sans migration Loom :
> ancien tableau = préfixe automatique complet ; nouvel objet v2 = actions et
> longueur du préfixe. Tests réouverture ancien/nouveau format.
> Tests : `pytest -q tests` (516 cas), `tests/rpg_smoke.gd` (taps natifs, trois
> questions à 0 PA, positions stables, fin manuelle, carnet et scroll), tests
> preparation/momentum/navigation/solo_mode. Captures `art/captures/rpg-*.png`
> en 18:9 et 20:9, rendues desktop avec UI téléphone, pas sur appareil Android.

> APK solo autonome : `bash godot/build_android_solo.sh` produit
> `builds/nexus-city-solo-debug.apk` (Android 7+, ARM64). Voir
> `android-solo/README.md`. Moteur Python embarqué, JSON par passerelle locale,
> sauvegarde/replay dans le stockage privé et QTE tactiles. Aucun port ni serveur
> externe, aucune permission Internet. Desktop `--solo` permet les tests par pipes ;
> le mode WebSocket desktop existant est conservé. `tests/test_solo.py` vérifie
> les règles, la reprise, les scores et les erreurs de sauvegarde.

> Version solo 0.3 : APK `builds/nexus-city-solo-debug-v3.apk`. Détection Android
> corrigée, scroll/drag avec momentum sur les boutons, suppression des textes
> hors de portée et des traits de liaison. Essai optionnel `board_zones.gd` :
> frontières au sol calculées depuis les parcelles et `view.adjacency`, sans
> changer les règles. Toggle dans le carnet. Revue visuelle `zones-*.png` ;
> test GUI natif tactile `tests/touch_momentum_smoke.gd` avec sauvegarde neuve.

> Mise à jour graphique du 8 octobre 2026 : le blockout a été remplacé par
> `city_visuals.gd` et ses shaders. La caméra est désormais en perspective.
> Voir `ART_DIRECTION.md` pour l'organisation, les contraintes Android et
> `bash godot/review.sh` pour six captures autonomes. Navigation désormais airy,
> avatars voxel et estompage de proximité ; captures téléphone 20:9 et 18:9 dans
> `art/captures/`. Les anciennes descriptions visuelles décrivent le blockout initial.
>
> Ajouts du serveur : `view.routes[lieu]` donne `cost`, `available`, `reason` et
> `key` (null si indisponible). `['walk', lieu]` permet un trajet de plusieurs
> arêtes, avec coût réel en PA ; `move` et le taxi à 1 PA sont conservés.
> Seules les clés fournies par le serveur sont envoyées. Tests :
> `tests/test_navigation.py`, `godot/tests/navigation_smoke.gd`.
>
> Topologie : grille 5 × 4 ; Rue Verlaine et hôpital sur 2 × 1 parcelles, Palace
> sur 1 × 2. `city.SKYBRIDGES` préserve le passage Verlaine–victime. Les cases
> décoratives restent hors du graphe des lieux explorables.

Ce client est un blockout fonctionnel, pas une direction artistique. Tout ce qui est visuel
est à refaire ; tout ce qui est protocole est à conserver.

## Ce qu'il ne faut pas casser

- Le client ne contient aucune règle de jeu. Il lit une vue et renvoie des clés.
  - `view` : tout ce qu'il faut dessiner pour un détective. Voir `Game.view()` dans `../game.py`.
  - `play` : une clé d'option telle que la vue l'a donnée, par exemple `["move", "bar"]` ou
    `["interrogate", 3]`. Ne jamais fabriquer une clé.
  - `challenge` : le serveur demande un score entre 0 et 1 pour un QTE ; le client répond `score`.
    Le QTE actuel (barre + Espace, trois paliers) est un placeholder à remplacer.
- Pendant un interrogatoire (`view.pending` non nul), les seules options sont les questions et
  « Laisser partir ». Le serveur refuse tout le reste.
- Les identifiants de suspects sont des entiers. Le serveur convertit les flottants du JSON,
  mais autant envoyer `int`.
- Les appartements sont des lieux `house_<id du suspect>` ; `view.places[id].street` donne la rue.
  `view.places[id].lit` dit si quelqu'un est chez lui.
- Les événements (`events`) sont des phrases à afficher telles quelles. Les notifications
  arrivent dedans, préfixées 🔔 (privé) ou 📰 (public).
- Les positions des autres détectives (`view.detectives`) sont publiques par design.

## Structure actuelle de `main.gd`

Un seul script, la scène se construit dans `_ready()`.

- `_dress_world` / `_lay_city` : nuit, sol, rues continues, tours de remplissage, lampadaires, pluie.
- `_make_place`, `_make_house`, `_windows` : les bâtiments, tout en BoxMesh. À remplacer par les
  assets voxel ; garder les noms de nœuds `Box` et `Label` ou adapter `_draw`.
- `_draw` : appelé à chaque vue. Recolore le lieu courant, place les gens (capsules), les détectives.
- `_draw_actions` : les boutons posés sur la carte (déplacements, « Entrer »). Ils ont un ancrage
  3D dans `anchors` et suivent la caméra à chaque image. Couleur par famille dans `STYLE`.
- `_draw_interior` / `_figure` : la page « intérieur » avec les silhouettes et les actions locales.
  Les silhouettes sont faites de deux rectangles arrondis ; c'est là que viendront les portraits.
- `_show_cards` : les événements du moment en cartes, en bas à gauche.
- Pages plein écran (`_page`) : préparation, intérieur, carnet. Calques : hud 1, intérieur 3,
  carnet 4, cartes 5.
- Caméra orthographique, glisser pour se déplacer, molette pour zoomer, `_focus` pour se poser sur
  un lieu. Les étiquettes 3D sont remises à l'échelle à chaque image selon `cam.size`.

## Itérer sans ouvrir l'éditeur

```
uvicorn server:app                      # dans un terminal, à la racine du dépôt
godot --path godot                      # jouer
godot --headless --path godot --check-only --script res://main.gd    # syntaxe
```

Captures automatiques sous écran virtuel, l'image sort dans le dossier scratch configuré dans
`_shot` (chemin à adapter) :

```
xvfb-run -a -s "-screen 0 1280x720x24" godot --path godot --rendering-driver opengl3 \
  --rendering-method gl_compatibility -- --shot [--city | --enter | --inside | --carnet]
```

`--city` s'équipe et montre la ville, `--enter` entre dans un appartement, `--inside` démarre au
bar et ouvre l'intérieur, `--carnet` ouvre le carnet. En mode `--shot`, les QTE sont réussis
d'office et les messages reçus sont tracés sur la sortie standard.

Avant chaque lancement du serveur de test, libérer le port : `fuser -k -n tcp 8000`. Un serveur
oublié garde en mémoire l'état des tables et fausse les captures.

## Pistes visuelles déjà discutées

- Personnages en voxel riggés via Mixamo, tout le monde dans le même style, portraits du carnet
  rendus en gros plan depuis le même modèle. Traits visibles de loin : genre, carrure, cheveux ;
  de près : yeux, lunettes, etc. Couleurs de cheveux, d'yeux, de peau = entrées de palette.
- Référence d'ambiance : `../Nexus City sous la pluie néon.png`.
- Icônes à la place des glyphes `»`, `¤`, `«»`, `§`, `!` dans `STYLE`.
- Le carnet en vrai tableau, une colonne par trait, comme dans `cli.py`.
