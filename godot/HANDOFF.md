# Passation : client Godot

## Le commissariat a sa pièce — v41 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v41.apk`, versionCode 41 / `0.41-causal`, même moteur
`causal-3d-v10` et même signature (sauvegardes conservées). Purement visuel. Référence
fournie par Maixent : `art/references/precinct-neon-noir.png`.

- `interior_lounge.gd` : `_build_precinct()` construit un nœud `Precinct` batché
  (`PrecinctStatic`), affiché quand `place == "police"` (`is_police`, le salon générique et la
  salle du bar sont cachés). Sol d'ardoise en damier 0,5 u avec trois nappes (ambre au comptoir,
  cyan aux bureaux, rouge à la cellule) ; murs béton en panneaux, plinthe, deux tubes cyan ;
  comptoir d'accueil (lampe, écran, dossiers, liseré doré) sous l'écusson et deux drapeaux ;
  cellule à barreaux au fond à droite avec couchette et tube rouge ; casiers ; tableau
  d'enquête (photos, punaises, ficelle rouge) ; trois bureaux avec écran cyan allumé, lampe,
  chaise ; deux piliers à lanterne ; fontaine à eau ; trois OmniLight sans ombre.
- Le commissaire se place comme le barman, derrière le comptoir en (-4,8, 0, -2,9) avec le halo
  côté client (`is_police` dans `populate`).
- Smoke natif `tests/precinct_smoke.gd --seed=0` (captures `guidance-precinct-*`).

## Un souvenir, pas un inventaire — v40 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v40.apk`, versionCode 40 / `0.40-causal`, même moteur
`causal-3d-v10` et même signature (sauvegardes conservées ; le texte des réponses « Témoin »
change à la relecture). Retour de Maixent sur la seed 682 : « Au Néon Bleu, j'ai aperçu Nadia
vers 18 h et demie ; au Néon Bleu, j'ai aperçu Chloé… » faisait inventaire, trop de noms, trop froid.

- `scenario_play.py` : `shared_sightings` liste toujours tous les vrais recoupements, mais la
  réponse n'en garde qu'un (2/3) ou deux (1/3), tirés par `random.Random("sightings-v2:…")` ;
  `sighting_text` les raconte avec ce que la personne faisait (bar : « un verre à la main »,
  « devant un verre » ; Comptoir : « à table », « devant une assiette ») sur trois tournures
  (« Lina était au Comptoir vers 18 h moins le quart, à table. On s'est salués, pas plus. »,
  « Je me souviens d'Oscar, à table au Comptoir, vers 20 h. », « J'ai croisé Salomé … On n'a
  pas vraiment parlé. ») et deux pour un duo au même endroit. La claim `sightings` ne contient
  que ce qui est dit. Élision « d'Oscar » ; « emprunté un objet au Néon Bleu » (contraction).
- Audit 120 seeds : 636/815 réponses « Témoin » informatives (une seule personne dans 329 cas,
  deux dans 92) ; le coupable parle d'un aperçu moins souvent (40 contre ~98 attendus) parce
  qu'il est moins souvent client du lieu, inchangé par rapport à la v34.

## Approche réparée, première notification différée — v39 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v39.apk`, versionCode 39 / `0.39-causal`, même moteur
`causal-3d-v10` et même signature (sauvegardes conservées). Retours de Maixent sur la v38.

- **Dialogues cassés sur téléphone** : à l'étape « Approche », `rpg_dialogue._show_options(true)`
  ne gardait que `ask`/`talk_about`/`summon`, donc « Lui parler (1 PA) » n'était jamais affiché
  et la deuxième étape restait vide (les smokes jouaient `["talk"]` directement, sans passer par
  les boutons). Corrigé : `talk` est un bouton, le bouton suivant s'intitule « Quitter » à
  l'approche (`approaching`), texte « Lui parler coûte un point d'action. ». Smoke natif
  `tests/approach_ui_smoke.gd --seed=0` passe par les vrais boutons (captures
  `guidance-approach-*`).
- **Toasts** : `case_toasts.FIRST_DELAY = 2,4 s` ; la première note d'une série attend que le
  titre « TOUR n » s'efface (transition ≈ 2,5 s) avant d'apparaître ; les suivantes s'enchaînent.

## Notifications de début de tour — v38 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v38.apk`, versionCode 38 / `0.38-causal`, même moteur
`causal-3d-v10` et même signature que la v37 (sauvegardes conservées).

- **Moteur** (`causal_game.py`) : `pending_actions()` liste les actions dont les prérequis sont
  acquis mais dont l'heure n'est pas venue (rapport du légiste en cours, analyse au labo, témoin
  ou patron hors service) ; `play(("end",))` compare avant/après et renvoie une ligne `📰 …` par
  action devenue possible (`event_text`) : « Le légiste a terminé : son rapport vous attend à la
  Morgue. », « Les résultats du laboratoire sont disponibles. », « La vendeuse de nuit est de
  retour à … », « Le barman reprend son service … », plus « Lina a rejoint Le Néon Bleu : son
  domicile est vide ce tour-ci. » pour un employé rappelé. `play` renvoie désormais une liste
  d'événements (une par ligne), pas une seule chaîne.
- **Client** : `case_toasts.gd` met les notes en file (`queue`) et les affiche l'une après
  l'autre en haut à droite (2,6 s quand d'autres attendent, 3,3 s sinon) au lieu d'écraser la
  précédente ; `main.gd` affiche chaque ligne `📰` sous le titre « Tour n ».
- **Bug ancien corrigé** (`case_toasts.gd`) : `set_parallel(true)` appelé après `chain()`
  fusionnait le fondu de sortie avec la pause, toute note disparaissait en 0,7 s (d'où des
  toasts jamais vus sur téléphone). Le tween tourne sur les pas physiques pour qu'une image
  bloquée par l'appel Python n'avale pas la note.
- Tests : `test_turn_start_headlines_announce_what_became_possible` ; smoke natif
  `tests/turn_toasts_smoke.gd --seed=0` (capture `guidance-turn-toast-*`).

## Faire appeler un employé — v37 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v37.apk`, versionCode 37 / `0.37-causal`, moteur
`causal-3d-v10` (sauvegardes v36 archivées au lancement, affaire neuve). Idée de Maixent :
déloger un suspect de chez lui pour aller fouiller son appartement.

- `causal_game.py` : `summons` (pid → tour), `expected(pid, at, tick)` donne lieu + activité
  (« appelé au travail » le tour de la convocation, sinon la routine) et alimente
  `update_positions`, `person()`, les `whereabouts` (le « prochain tour » regarde désormais
  `s.at + TURN_MINUTES`). `workplace_known(pid)` : la personne est nommée ET (fiche police
  connue, ou réponse « Métier » au journal, ou `venue_staff:<lieu>` au journal).
  `summonable()` : employés du lieu du gérant (`crime.keepers`), établis, pas déjà sur place,
  pas déjà convoqués pour le tour suivant.
- Menu du barman / serveur : `("summon", id)` « Faire appeler Ada (1 PA) » (si PA > 0).
  `play` : −1 PA, `summons[pid] = tick + 1`, réponse du gérant. À `end` : `📰 Ada répond à
  l'appel du travail et passe le tour au Néon Bleu : domicile vide ce tour-ci.` (toast
  « Information ») ; la personne est au lieu pour ce tour (`interrogate` possible), son
  domicile se fouille/crochète comme un logement vide.
- Client `rpg_dialogue.gd` : les clés `summon` passent le filtre de conversation et sont
  regroupées sous « Faire appeler un employé… » (`_show_people_questions("summon")`).
- Test : `test_an_employer_calls_a_suspect_in_once_you_know_where_they_work` ; smoke natif
  `tests/summon_smoke.gd --seed=0` (captures `guidance-summon-*`).
- Au passage : `slots_total = 0` pour le personnel (la boîte du barman affichait
  « Questions 3/3 » sans budget).
- Smokes liés à une seed précise toujours périmés (pas des régressions) :
  `causal_access_smoke` après le seuil (second résident seed 7), `causal_contacts_smoke`
  (id 0 = victime sur seed 7), `causal_life_smoke`, `causal_services_smoke` (seed 0 n'est
  plus un empoisonnement), `lounge_smoke`/`rpg_smoke` (moteur legacy).

## Portes, questions lisibles, ⚡, couleurs des noms — v36 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v36.apk`, versionCode 36 / `0.36-causal`, même moteur et
signature que la v35. Retours de Maixent après une session sur la v35.

- **Couloir** (`interior_lounge.gd`) : cinq portes sur le mur du fond espacées de 3,3 u, les
  suivantes sur le mur gauche (orientées +x) ; `door_meshes[place]` garde les maillages de
  chaque porte ; `open_door(place, then)` fait coulisser la porte le long de son mur, fait
  apparaître une silhouette sur le seuil puis appelle `then` (le `ring`). `main.gd` passe
  `solo_busy` pendant l'animation.
- **Questions** : libellés `Lien · / Alibi · / Témoin · / Mobile · / Métier · / Entourage · /
  Agenda ·`, plus de « (1 PA, une fois) » ni « (gratuit) » ; `rpg_dialogue.gd` garde le compteur
  « Questions 1/3 · 4 PA » même quand la cue fournit un `context`. Un ⚡ marque les actions qui
  passeront par la jauge (question au-delà du budget sans `rapport`, empreintes sans la
  compétence, crochetage sans la compétence) ; ces questions restent offertes à 0 PA.
- **Couleurs dans le texte** : `view["highlights"]` (`victim`, `suspects` nommés, `evidence` =
  objets en main) ; `rpg_dialogue._highlight` colore en BBCode (victime `#ff7889`, suspects
  `#ffd386`, preuves `#63e1ec`), `bbcode_enabled` activé, crochets échappés.
- **Alibi** : `alibi_state` renvoie `unverifiable` quand la soirée est connue mais qu'aucune
  action `verify:` n'existe (« je suis resté chez moi ») ; vue « invérifiable », client
  « INVÉRIFIABLE ».
- **Ville** : commissariat à 0,72 de hauteur ; parcelles de décor plus petites (7,6 → 6,7 →
  5,8), décalées, et une sur cinq devient un terrain vague (`_vacant_lot`).
- **Approche d'un suspect** (`causal_game.open_questions`) : sonner ou toucher un suspect ouvre
  d'abord une cue `stage = "approach"` : la voix du détective décrit la personne (« Le suspect
  s'appelle Ada. Petite, manteau clair, cheveux blonds. », `describe(pid)`), gratuite, portrait
  du suspect mais couleurs détective (`person.detective`). Options : `("talk",)` « Lui parler
  (1 PA) » (seulement avec un PA) et `("stop",)` « Quitter ». `("talk",)` dépense le point,
  ouvre les 3 questions (stage `greeting`). Pas de relecture dans la conversation : la fiche
  suspect du carnet termine par un déroulant « Conversations passées · n » (`row.said`, liste
  `{question, text}` dans l'ordre du journal). PNJ et personnel inchangés. Contexte client
  « Approche · n PA ».

## Quartiers à identité, parcelles irrégulières — v35 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v35.apk`, versionCode 35 / `0.35-causal`, même moteur et
signature que la v34 (sauvegardes conservées). Purement visuel, `city_visuals.gd` :

- `DISTRICT_STYLES` (par lieu de la grille) : `color`, `accent`, `height` (×), `ground`
  (teinte du trottoir), `theme`. Thèmes : `ondes` (cctv), `central` (police), `palace`
  (cabaret), `traverses` (alley), `neon` (bar), `comptoir` (restaurant), `saint-vital`
  (hospital, lab), `canal` (crime_scene, promenade), `verlaine` (victim_street). Les parcelles
  de décor hors grille empruntent la couleur du quartier le plus proche.
- `_district_dressing(theme, …)` ajoute l'habillage au sol et en façade (canal + garde-fou +
  passerelle, haies + croix, guirlande d'ampoules + arche néon, mâts + parabole + balise,
  mâts de drapeaux + bornes, auvent + terrasse + guirlande, bandes néon, balcons + vélo).
- `_corner_garden` : un coin planté par parcelle (position et taille par hash) ; `_kerb_glow` :
  liseré lumineux à la couleur du quartier ; `_tinted_pool` : flaques de néon à l'accent du
  quartier ; une `OmniLight3D` douce (0,75, portée 9,5) par parcelle stylée, sauf `--low-fx`.
- Cellules vides : `_plaza` tire jardin / `_car_park` / `_basin` selon le hash.
- Rien ne bouge côté jeu : positions, entrées (`entrance` meta), voies des voitures, viaduc.
  Captures `causal-street-life-*-v35-*`.

## Budget de questions, témoins utiles, fausses pistes d'emprunt — v34 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v34.apk`, versionCode 34 / `0.34-causal`, même signature.

- **Budget de questions (suspects seulement)** : `open_questions` (sonner / interroger) coûte 1 PA
  et donne `QUESTIONS_PER_PA` = 3 questions neuves (`self.slots`) ; à 0 PA la conversation
  s'ouvre en relecture seule. `spend_question()` : une question neuve consomme un slot ; à
  épuisement, `rapport` offre une question, sinon jauge « persuasion » (0,5) : réussie → une
  question offerte, ratée → 1 PA pour trois de plus. `question_cost` renvoie 0 tant qu'il reste
  un slot. `stop` remet `slots` à 0. Cue : `remaining` (slots restants), `slots_total` ;
  `rpg_dialogue.gd` affiche « Questions 1/3 · 4 PA ». Les PNJ (personnel, légiste, labo,
  commissariat, témoins) gardent exactement leurs coûts.
- **Jauge pour les empreintes** : `("fingerprint", obj)` offert à tous (« · adresse » sans la
  compétence), jauge « fingerprint » (0,6), raté → « Le relevé est brouillé », réessai possible.
  Les scores des jauges (persuasion, empreintes) sont sauvés en fin de clé d'historique
  (`["ask", "motive", 0.82]`, `["fingerprint", obj, 0.31]`) et rejoués sans jauge.
- **Question « Témoin »** : `observations:X` dit qui X a réellement aperçu, où et quand
  (`shared_sightings`, intervalles partagés entre présences vérifiées, visites réelles et
  emprunts ; claim `sightings`), coupable compris et sincère. Mesure : 307 réponses
  informatives sur 412 contre 16 avant. Un aperçu nomme et oriente, il n'écarte pas.
- **Emprunts** : le serveur nomme l'emprunteur (« On en a prêté un à Tess ») ; l'objet d'un
  établissement trouvé dans un logement est étiqueté « (du Néon Bleu) », emporté (`carried`)
  et analysable au labo (« Aucune trace exploitable ») ; l'emprunteur travaille sur place
  sept fois sur dix quand c'est possible (`workplace-loan-v1`). Fausse piste honnête.

## Onglet Réseau, équipe des établissements — v33 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v33.apk`, versionCode 33 / `0.33-causal`, même signature.

- **Graphe social public** : `PlaySession.social_graph()` → `{center, nodes[{id, name, victim,
  excluded}], edges[{a, b, kinds, sources}], strangers[[a, b]]}`, construit uniquement depuis
  le journal : `context:X:relation` (liens X–victime), `context:X:work` (collègues),
  `context:X:circle` (« proche » de la victime), `about:X:Y` (liens X–Y, ou paire
  `strangers` si « je ne connais pas »), faits `ex_and_partner` / `sour_breakup`
  (« rivalité » / « ex en paix ») et albums lus (claim `photos` ajouté aux artefacts
  `photos:homeX`). `excluded` = plus dans `remaining()`. Vue : `view["network"]` avec ids
  entiers (`network_view`).
- Client : onglet **Réseau** (`ego_graph.gd`, Control dessiné) : victime au centre, les autres
  sur un cercle (jamais deux en opposition), arêtes colorées par type et étiquetées, paires
  « ne se connaissent pas » en pointillés, personnes écartées à 35 % d'opacité
  (« · écarté ») ; toucher un nœud ouvre la fiche (`person_tapped` → `_select_notebook_suspect`).
  Test natif `tests/network_smoke.gd`, capture `causal-network-*`.
- **« Qui travaille ici ? »** : action `venue_staff:<lieu>` chez chaque tenancier (artefact
  `venue_staff`), qui cite l'équipe avec les postes ; les noms entrent dans `named_people()`.
- **Biais crédible** (demande de Maixent : « il manque un marteau → qui bosse ici ? ») : avant,
  le preneur de l'arme travaillait sur place dans 1 cas sur 22 ; `CrimeBuilder.execute`
  préfère maintenant (70 %, flux `workplace-tool-v1`) un outil gardé au lieu de travail du
  coupable quand il en existe un. Mesure : 7 cas sur 27, et un innocent y travaille aussi dans
  21 cas — une piste, jamais une certitude.

## Un seul témoin de l'acte — v32 (13 octobre 2026, côté backend)

APK `builds/nexus-city-solo-debug-v32.apk`, versionCode 32 / `0.32-causal`, même signature.
Seed 853 (Maixent) : deux témoins de la scène disaient la même chose. `WitnessBuilder` tire
désormais des événements *distincts* (`rng.sample`) : jamais deux témoins du même acte ; le
profil « signalement » passe à `focus_assault = 1`. Sur 120 affaires : zéro cas à deux témoins
de l'acte, profils toujours 45 / 33 / 42, 19 empoisonnements.

## Jauge tournante : le crochetage pour tous — v31 (13 octobre 2026)

APK `builds/nexus-city-solo-debug-v31.apk`, versionCode 31 / `0.31-causal`, même signature.
Idée de Maixent : les compétences servent à *sauter* un QTE que tout le monde peut tenter.

- Client : `timing_dial.gd` (Control plein écran, calque 8) remplace la barre « Appuyez vite ».
  `start(kind, difficulty)` : aiguille qui tourne (3,2 → 6 rad/s), arc cible (±0,55 → ±0,22
  rad) tiré au hasard, départ à l'opposé de l'arc, échec automatique après deux tours.
  `hit()` sur touche/clic/`ui_accept` : score = 1 au centre, 0,5 au bord de l'arc, 0 loin ;
  signal `answered(score)` → `_answer_qte` → message `score`. En `--shot`, réponse parfaite.
- Adaptateur : `CausalGame(seed, names, challenge=None)` (le runtime passe `_challenge`, qui
  émet `challenge {kind, difficulty}` et attend `score`). `("unlock_home", home)` est offert à
  tout le monde (libellé « · adresse » sans la compétence) ; sans `lockpick`, le score de la
  jauge décide (`PASS_MARK` 0,5, `LOCKPICK_DIFFICULTY` 0,55) : réussite → entrée directe,
  échec → « Le crochet ripe », 1 PA, réessai possible. Le coup est sauvegardé comme
  `["unlock_home", home, score]` et rejoué sans jauge ; `restore(..., challenge=)`.
  Sans client (tests, audits) la main est parfaite.
- Test natif `tests/lockpick_dial_smoke.gd` (jauge affichée, raté ferme, réussi entre) et
  captures `causal-lockpick-*`. Prochains usages possibles du même mécanisme : fouille
  rapide (compétence `search`), persuasion (`rapport`).

## Un trait sur la scène, un autre à la caméra — v30 (13 octobre 2026, côté backend)

APK `builds/nexus-city-solo-debug-v30.apk`, versionCode 30 / `0.30-causal`, même signature.
Retour de Maixent (seed 836) : deux témoins sur la scène donnaient deux traits, trop
discriminant d'entrée, et la caméra répétait la couleur du manteau.

- `WitnessBuilder` : parmi les témoins de l'acte décisif, seul le premier garde un trait ; les
  suivants ne donnent que l'heure et une silhouette.
- `build_evidence(described=…)` : la caméra de la rue de la scène évite les traits déjà décrits
  par les témoins (et la silhouette) quand un autre trait partageable existe
  (flux `camera-aspect-v1`). `build_case` lui passe les aspects des perceptions de l'acte.
- Mesure sur 120 affaires : au plus un trait de témoin sur la scène (103 cas avec un, 17 sans),
  la caméra de la scène apporte un trait nouveau dans 93 cas sur 93 où elle fonctionne ;
  profils toujours équilibrés (45 / 33 / 42).

## Tissu social — v29 (12 octobre 2026, côté backend)

APK `builds/nexus-city-solo-debug-v29.apk`, versionCode 29 / `0.29-causal`, même signature.
Moteur `causal-3d-v9` : nouvelles affaires. Retour de Maixent sur la seed 242 : deux comptables
de la Régie « ne se connaissaient pas », et tout le monde semblait ami de la victime.

- `build_life` (`scenario_life.py`) ajoute un flux `social-fabric-v1` : lien `COLLEAGUES`
  (fait `shared_workplace`) pour toute paire d'un même lieu de travail, lien `NEIGHBORS`
  (fait `same_street`) pour 60 % des paires d'une même rue, victime comprise. Les réponses
  « demander X Y » les disent : « On travaille ensemble. », « On habite dans la même rue. ».
- Le remplissage des liens directs avec la victime ne propose plus collègues/voisins (déjà
  couverts) et tire `None` deux fois sur trois ; sinon amis / connaissances / fratrie.
- Mesure sur 60 affaires : liens directs avec la victime 5,1 sur 7 en moyenne, dont ~2
  collègues, ~1 voisin, ~1 ami, 0,8 couple, 0,6 connaissances, 0,4 fratrie ; aucune paire de
  collègues qui s'ignore. Le noyau (`scenario_kernel`) fournit toujours ~2 liens narratifs.
- Question « métier » (`Life.answer(pid, "work")`) : « Je tiens la comptabilité, à la Régie
  vidéo, avec Tess et Ada. » Les noms cités entrent dans `named_people()` → fiches au
  Commissariat. Demande de Maixent : remonter une piste « boulot » sans rencontrer tout le monde.
- **Alibis partiels** (`partial_alibis` dans `PROFILES`, 0,25–0,45) : `build_evidence` crée des
  `VerifiedPresence` de base `partial_service` pour des innocents non narratifs et, quand sa
  trajectoire le permet, pour le coupable : visite vraie chevauchant ou précédant/suivant la
  fenêtre du crime. `verify:X` donne « Entre 19 h moins le quart et 19 h et demie, cette personne
  était à sa table. Après, je ne peux rien dire : je ne l'ai pas vue. » Claim sans `excludes`
  (`partial: True`), `alibi_state` → `partial`, le registre ne cite jamais ces visites, la
  famille « horaires » de l'audit les ignore. Vue : `notebook[].alibi == "hors période"`,
  `leads[].state == "partial"` ; client : « VRAI · HORS PÉRIODE ». Sur 80 affaires : 48 avec
  une visite partielle, dont 25 où c'est le coupable. Retour de Maixent : les alibis tombaient
  toujours pile sur la fenêtre, le légiste ne servait à rien.

- **Récit de soirée** (`scenario_evening.evening_account`) : une seule chronologie, « Jusqu'à
  19 h et demie, j'étais chez moi : j'ai lu quelques pages… Ensuite, j'étais au Comptoir, entre
  20 h et 22 h moins le quart. » L'heure vient de l'épisode domestique, calculé par personne
  (sa première présence moins le trajet), plus du minimum global de la ville. Retour de Maixent :
  « resté chez moi » puis un horaire précis dans un bar, sans transition.
- **Pancartes** (`main.gd::_draw_actions`, `city_navigation.add_district`) : un quartier hors de
  portée ce tour (trop loin ou PA insuffisants) garde sa pancarte, bouton désactivé à 55 %
  d'opacité, « 2 PA · hors de portée ce tour ». Le menu « Quartiers » ne liste que les
  destinations atteignables. Retour de Maixent : les pancartes disparaissaient à court de PA.

- **Empoisonnement** (échange avec Maixent) : être vu dans la salle ne disculpe pas. Le client
  réel du lieu (noyau) reçoit soit `continuous_noncontact` (60 %, flux `noncontact-v1`) : le
  personnel « ne l'a pas quitté des yeux, sans toucher le verre », ce qui l'écarte (requiert
  rapport + analyse du verre) ; soit `on_site` : « tout le monde pouvait s'approcher du
  comptoir », claim sans `excludes` (`alibi_state` → `on_site`, vue « sur place », client
  « VU SUR LES LIEUX »). Les alibis de service aléatoires et les registres ne sont jamais
  placés dans le lieu du crime. Les témoins traitent `DRINK_ADDITION` comme l'acte décisif
  (signalement de l'empoisonneur), ce qui garde les affaires résolubles. Sur 80 affaires
  tirées : 25 empoisonnements, 18 avec un client surveillé, 5 avec un client seulement vu.
  Le coupable, client réel du lieu, reçoit lui aussi une présence `on_site` (du service du
  verre jusqu'à son départ réel, `compatible_presence`), donc le même récit de soirée que
  l'autre client et une vérification possible chez le serveur : en v28 il était le seul à dire
  « j'y étais, il y avait du monde » sans horaire ni serveur (Maixent, seed 225).
  Un empoisonnement a toujours au moins un témoin du geste (`build_case` force
  `focus_assault ≥ 1`) et le premier témoin de l'acte décisif garde un trait quand il en
  existe un partageable (`WitnessBuilder`) : plus d'affaire « personne n'a rien vu » (Maixent,
  seed 225 en v28 : six alibis à vérifier, dont trois dans la salle du crime, et rien d'autre).

- **Crochetage** : `("unlock_home", home)` déverrouille et fait entrer (`session.go(home)`) en
  une action de 1 PA ; le client pose `enter_requested` pour ouvrir l'intérieur aussitôt.
  Avant : déverrouiller, puis « Entrer » séparément. Demande de Maixent.

- **Ex et partenaire actuel** (`build_life`, flux `ex-and-partner-v1`) : dans 80 % des cas, un
  fait `ex_and_partner` (détail `venom` / `grace` / `neutral`, tiré indépendamment de la
  culpabilité) et un lien `ACQUAINTANCES`. `answer_about` dans les deux sens : « Celle qui a
  pris la suite… je ne vais pas faire semblant d'avoir apprécié. » / « L'ex de Farid. C'était
  fini depuis longtemps. » Retour de Maixent (seed 225) : une ex jalouse doit au moins connaître
  la nouvelle compagne. L'humeur penche vers le venin si l'ex est partie à une tension
  sentimentale du récit, vers la bienveillance sinon.
- **Rupture amère** (`sour_breakup`) : le triangle que le noyau génère vraiment est victime +
  partenaire actuel + ex de ce partenaire (réconciliation refusée, relation révélée). Ces deux
  ex reçoivent un fait `sour_breakup` (`venom` deux fois sur trois, sinon `neutral`) et des
  réponses dans les deux sens : « Mon ex. Ça s'est mal fini : elle n'acceptait pas que je passe
  à autre chose. » / « Chloé est passée à autre chose, avec Tess. Je ne vais pas prétendre que ça
  m'a fait plaisir. » Même information que la question « mobile », mais en paroles.
- **Question « entourage »** : `("ask", "circle")` remplace `("ask", "habits")` dans le dossier
  biographie du client (`rpg_dialogue.gd` : `["work", "circle"]`). Réponse : « Les gens que je
  savais proches de Farid : Ada et Tess. » (personnes que le locuteur connaît et qui ont un
  lien avec la victime), sinon « Je ne saurais pas dire… ». CLI : `question X entourage`.
  Le « quotidien » ne servait à rien (Maixent).

- **Salutation sans récit** : `PlaySession(greeting_reveals_evening=False)` dans l'adaptateur.
  `meet:X` ne révèle plus que le profil ; la soirée attend « Alibi · Où étiez-vous hier soir ? »
  (`interview:X`). La CLI garde la salutation complète. Retour de Maixent : après quatre
  « quelle est votre relation ? », le carnet affichait leurs alibis « à vérifier » sans qu'il
  les ait demandés.

## Phares — v28 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v28.apk`, versionCode 28 / `0.28-causal`, même moteur et
signature que la v27. `_car(at, h, turn, lit)` : seules les voitures de circulation sont
allumées (feux blanc chaud `fff1c4`, feux arrière `ff2f4f`), les voitures garées ont des
optiques éteintes en matériau opaque. Le faisceau au sol a été retiré : une plaque fine
posée sur la chaussée devant la voiture n'est pas visible depuis l'angle de la caméra
(masquée par la carrosserie), seul un volume épais l'était, et ça faisait un pavé.

## Horloge au tour par tour — v27 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v27.apk`, versionCode 27 / `0.27-causal`, même signature.
Moteur `causal-3d-v7` : les sauvegardes v26 et antérieures repartent sur une nouvelle enquête.

- `PlaySession(..., turn_minutes=30)` (mode tour par tour, utilisé par `causal_game.py`) :
  `_advance` ne fait rien pendant le tour, `end_turn()` avance de 30 minutes et c'est le seul
  moment où l'échéance peut classer l'affaire. Un dossier rejeté avance quand même l'horloge
  de 90 minutes (`force=True`), mais la clôture attend la fin du tour. `turns_left`
  (`ceil(time_left / 30)`) est exposé dans `view["turns_left"]`, `view["turn_minutes"]` et
  dans `view["threads"]`.
- Adaptateur : `end` appelle `s.end_turn()` ; plus aucune action n'avance l'heure. Les délais
  (légiste, laboratoire) se comptent donc en tours : « dès 09:08 » veut dire après le tour où
  l'horloge dépasse 09:08.
- Client : en-tête « 9 tours avant l'échéance », onglet Fils « 9 tours restants (4 h 15) »,
  confirmation d'accusation « vous perdez trois tours ». Textes du guide alignés.
- La CLI (`scenario_play.py`) garde son horloge continue (minutes par action).

## Vie de rue : circulation et train — v26 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v26.apk`, versionCode 26 / `0.26-causal`, même moteur et
même signature que la v25 (sauvegardes conservées). Purement visuel, dans `city_visuals.gd` :

- `_spawn_traffic(n)` crée `n` voitures (9, 4 en `--low-fx`) comme nœuds individuels
  (`Car0…`, maillages `Traffic_*`), chacune sur une ligne de rue libre de la grille
  (`free_vertical` / `free_horizontal`, calculées dans `build()` en excluant les lignes que
  traversent les parcelles fusionnées hôpital / rue Verlaine / cabaret). Circulation à droite :
  la voie est à 0,95 u du centre de la rue, côté droit du sens de marche ; d'un bord de la
  ville à l'autre puis nouvelle ligne tirée au sort. `CAR_SPEED` 1,9 u/s (un pâté en ~6 s).
  Phares : faisceau au sol en matériau lumineux, feux arrière rouges.
- Les voitures garées de `_street_props` serrent maintenant le trottoir (0,45 u du bord)
  pour laisser les deux voies.
- Train : `_transit` garde le nœud `Train` (deux voitures, bandeau de toit cyan, phare) ;
  `animate(delta)` le fait traverser le viaduc à `TRAIN_SPEED` 7,5 u/s, puis attend
  `TRAIN_INTERVAL` 34 s ±20 % et repart dans l'autre sens.
- `main.gd::_process` appelle `visuals.animate(delta)` dès que la ville est posée.
  `--shot-delay=S` règle le délai de la capture `--shot`.
- Test natif `tests/street_life_smoke.gd` : voies respectées, voitures qui avancent, train en
  cours de traversée, captures `causal-street-life-*` (vue quartier et vue large).

## Profils d'affaire, placards partout, empreintes comparables — moteur v6 (12 octobre 2026, côté backend)

APK `builds/nexus-city-solo-debug-v25.apk`, versionCode 25 / `0.25-causal`, même certificat.
`causal_game.py` passe en `causal-3d-v6` : les seeds ne donnent plus les mêmes affaires, nouvelle
enquête requise. Rien à changer dans le client, mais à savoir :

- **Profils d'affaire** : `sample_playable(seed)` tire par seed le fil favorisé (signalement /
  horaires / mixte, `PROFILES` dans `scenario_play.py`) et règle témoins de l'agression et
  mémoire des serveurs en conséquence ; le fil le plus court est maintenant réparti à peu près
  également (audit `python scenario_threads.py --count 120`). Les serveurs citent au plus deux
  clients spontanément par établissement.
- **Placards** : chaque logement a `search_cupboard:homeX` (fixture `cupboard:homeX`, prop
  `cupboard`). Avant, seul le logement qui cachait l'arme avait un placard : c'était une fuite.
- **Empreintes comparables** : avec la compétence `fingerprints`, fouiller un logement relève la
  tasse de l'habitant sur place (motif entier). Un objet récupéré, lié au crime par le
  laboratoire (`analyze_object` → `session.linked`) et relevé, écarte toute personne dont le motif
  n'y figure pas (`session.print_exclusions()`, texte dans `deductions()` source `prints`,
  pris en compte par `remaining()`). Quatre motifs ; celui du coupable est toujours partagé.
  Le fil « Le matériel » du guide expose ces étapes (`view["threads"]`).
- CLI : `faire MOT` choisit une action par un mot de son libellé (les numéros bougent).

## Mode libre dans le client : échéance, fils, accusation — v24 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v24.apk`, versionCode 24 / `0.24-causal`.
Moteur `causal-3d-v5` : les sauvegardes v23 et antérieures demandent une nouvelle enquête
(le runtime le signale et repart proprement). Même certificat.

Côté adaptateur (`causal_game.py`) :

- `setup()` expose `difficulties` (`facile / normal / difficile` avec un libellé) et
  `default_difficulty` ; `equip(0, items, start, difficulty)` crée la `PlaySession` en
  mode libre (`strict=False`). Le message `equip` accepte `"difficulty"`, la sauvegarde
  la conserve (`snapshot()["difficulty"]`) et la rejoue à l'identique. Un niveau caché
  `libre` (aucune échéance) existe pour les bots de test exhaustifs ; `setup()` ne l'offre
  jamais et le runtime refuse ce qui n'est pas dans `difficulties`.
- `view` gagne `difficulty`, `deadline` (heure), `time_left` (minutes), `mistakes` et
  `ended` (`null`, ou `{won, title, text, mistakes}` quand l'affaire est close : dossier
  accepté, échéance dépassée). Le coupable n'est nommé qu'une fois l'affaire close.
- Fin de tour et attente passent par `session._advance` : l'échéance coupe le jeu au tour
  près, `options()` est alors vide.
- Au Commissariat, « Déposer le dossier : X » existe pour toute personne nommée et pas
  encore mise hors de cause. Un dossier rejeté coûte 90 minutes et retire X des options.
  La réponse arrive comme `conversation` avec `context` « Dossier accepté / rejeté ».

Côté client (`main.gd`) :

- Page de préparation : rangée « Difficulté » (un niveau toujours sélectionné, `normal`
  par défaut), envoyée avec `equip`.
- En-tête : « 2 h 45 avant l'échéance » et « n dossier(s) rejeté(s) » le cas échéant.
- Carnet : onglet **Fils** en tête, rendu de `view["threads"]` : ligne d'état (échéance,
  temps restant, personnes encore possibles), puis trois cartes avec les étapes
  ✓ faites / ▶ suivantes (actions en clair) / · à venir. Les onglets existants ne bougent pas.
- Accusation : `_play_local(["accuse", id])` ouvre d'abord une `ConfirmationDialog`
  (« Pas encore » rend la main au dialogue) ; la clé n'est envoyée qu'après confirmation.
- Carte de fin : `view["ended"]` ouvre une page pleine (titre, verdict, tour/heure/erreurs,
  « Nouvelle enquête » → `restart`). Elle disparaît au `reset`.

Test natif : `tests/causal_threads_smoke.gd` (difficulté, compte à rebours, onglet Fils,
confirmation d'accusation, carte de fin) avec captures `art/captures/causal-*-v24-18x9.png`.
`stageNexusPython` embarque désormais `scenario_threads.py`.

## Fils d'enquête, registres, accusation libre — moteur v4 (12 octobre 2026, côté backend)

Changements de règles dans `scenario_play.py`, à répercuter dans le client quand vous voudrez :

- **`view["threads"]`** (via `scenario_threads.guide`) : trois fils, Le signalement, Les emplois du
  temps, Le matériel, chacun avec ses étapes `done / next / later`, l'étape suivante en clair,
  et en tête `remaining`, `accusable`, `missing`, `deadline`, `time_left`, `mistakes`.
  Calculé uniquement sur l'état public du joueur ; symétrique entre candidats. Même donnée
  que la commande CLI `fils`. À afficher comme une page « Pelote » ou l'onglet Pistes.
- **Les registres vouchent** : le personnel cite spontanément une partie des clients (mémoire
  partielle, tirée par seed) ; une fois le crime daté, ces personnes sont hors de cause sans
  rencontre ni vérification (`session.register_entries()`, `alibi_state` renvoie `confirmed`).
  Les autres se vérifient comme avant. Textes de registre modifiés → `VERSION = causal-3d-v4`,
  nouvelle enquête requise.
- **Rencontrer quelqu'un livre sa soirée** : `meet:X` révèle `profile:X` et `evening:X`.
  `interview:X` existe toujours (relecture gratuite côté adaptateur).
- **Fiches du commissariat** : seulement pour les personnes dont le nom a été lu ou entendu
  (`named_people()`), comme dans le client. `session.batches()` propose « Consulter les fiches
  de … » et « Vérifier les récits de … » en une visite ; la CLI les affiche, l'adaptateur peut
  les reprendre ou garder les actions unitaires.
- **Mode libre** : `PlaySession(case, skills, strict=False, difficulty="facile|normal|difficile")`.
  Échéance en minutes (`session.deadline`, `time_left`), calculée depuis le fil le plus court ;
  accusation jamais refusée : une erreur coûte 90 minutes et met l'accusé hors de cause
  (`session.cleared`, `mistakes`), la bonne clôt l'affaire même sans agenda. Le dépassement
  de l'échéance clôt l'affaire (journal `closed`). Depuis la v24, `causal_game.py`
  joue en mode libre (voir la section ci-dessus).

Audit : `python scenario_threads.py --count 200` donne les longueurs par famille.

## Séparation des personnages et indices au Néon Bleu — v23 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v23.apk`, versionCode 23 / `0.23-causal`.
Correction purement visuelle : aucun changement de scénario, PA ou sauvegarde.
Même moteur/signature, compatible avec les enquêtes v18–v22.

Le placement générique superposait témoins/clients et objets de la scène ; une
table empiétait sur le corps. Le bar possède maintenant des emplacements propres :
personnages dans les allées clients/pourtour du billard, barman derrière le
comptoir, corps et indices dans l'allée centrale/droite dégagée. Table avant
replacée à gauche. `_bar_fixture_position()` utilise l'identité physique du
prop, jamais sa position dans la liste d'actions. Valise séparée à l'avant gauche.
Transport du corps, collecte et nouvelle visite conservent les autres meshes.

Cibles du bar 100 × 64 pixels logiques (minimum tactile conservé), libellés courts
« Corps », « Verre », « Objet au sol », titre intégral en tooltip. Marge basse
du bar garde ces cibles au-dessus de la navigation. Framing des autres lieux
inchangé. Décor toujours batché, mêmes trois lumières sans ombres.

`tests/bar_layout_smoke.gd` étend le parcours natif de stabilité : crime réel
seed 5, inspection/collecte/transfert/morgue/revisite ; contrôle des rectangles
tactiles non superposés avec personnes et entre objets, propriétaire du centre
de clic, distance physique > 1.5 unités des personnes. Stress de projection
avec quatre clients et un contact supplémentaire (vue temporaire synthétique,
jamais injectée dans le moteur) avant/après inspection et collecte. Vue réelle
restaurée avant chaque interaction. Passé en 1080×540 et 1200×540 ; captures
`guidance-fixtures-*-v23-{18x9,20x9}.png` et
`guidance-bar-layout-crowded-fixtures-*-v23-*.png` inspectées. Aucun test sur
appareil Android physique. Régression bar/barman natif/restaurant et stabilité
de scène extérieure seed 7 également passées.

APK vérifié : 24 modules Python et quatre scripts Godot byte-identiques aux
sources, certificat inchangé. SHA256 :
`2b348475fb71944c84d4c593fa618f39209ba826cc0b034203a1bec69f80700e`.


## Questions directes, coût uniforme et grisage — v22 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v22.apk`, versionCode 22 / `0.22-causal`.
Menu suspect : relation en premier, puis alibi, observations, tensions, tous
directement accessibles. « Votre quotidien… » ne replie que métier/habitudes ;
« Parler de quelqu'un… » garde la liste des personnes. Les services hors labo/
morgue n'offrent plus « Vous avez quelque chose à ajouter ? ». Suivi/rappel des
analyses conservé, après les questions concrètes du légiste/laboratoire.

`CausalGame.question_cost(key)` : toute nouvelle question informative coûte un
PA, y compris relation, métier, habitudes, rendez-vous et chaque personne évoquée.
Même coût pour une réponse négative/non concluante : aucun indice par tarif ou
nombre de questions. Une réponse déjà obtenue est gratuite à reposer, sans
temps ni note supplémentaire. Services : actions recueillies réaffichées et
réponses relues depuis les artefacts acquis du journal, sans relancer une analyse,
révéler une preuve future ou modifier le monde. Consultation de statut/navigation
de menus gratuite ; ouverture d'un suspect déjà rencontré gratuite, y compris
au seuil à zéro PA. Première identification conserve son coût existant.

Contrat : `options` reste la liste des commandes légales. `dialogue_options`
ajoute la présentation de questions indisponibles, au format
`[key, label, {cost, available}]`. À zéro PA, les premières questions payantes
restent visibles mais grisées ; le bouton et `_choose()` bloquent leur émission.
La dernière réponse reste lisible, puis retour au menu de relecture gratuite
avec « Revenir à la ville ». Pas de fin de tour automatique, ni message de PA
déclenché par un toucher d'une question désactivée. Menus secondaires navigables
gratuitement ; leurs questions individuelles ont le même grisage.

Sauvegardes v18–v21 : moteur/signature inchangés. Nouveau champ `priced_from`
dans le snapshot : index de début des nouvelles règles de tarification.
Un historique sans ce champ conserve ses coûts anciens durant le replay ; les
nouveaux actes sont payants selon la règle actuelle. Ne pas appliquer les nouveaux
coûts rétroactivement : une ancienne fin de tour deviendrait sinon incohérente.
Ancienne relance vide rejouable uniquement pour restaurer une sauvegarde, jamais
proposée/acceptée en commande neuve. Comparaison avec le moteur réellement extrait
de l'APK v21 : PA, temps, vérité, journal et historique conservés sur trois replays.

Tests Python : six sujets payants/relecture à zéro PA, questions par personne,
réponses PNJ, rendez-vous, menu uniforme sur huit seeds, replay ancien/nouveau.
`tests/dialogue_menu_smoke.gd` : touchers natifs, ordre des questions, coût des
questions réelles, grisage/non-émission à zéro PA, relecture inchangée et sortie.
Captures inspectées téléphone desktop 18:9/20:9 :
`guidance-dialogue-{primary,barman,relation-answer,zero-pa,return}-v22-*.png`.
Parcours de corroboration/morgue/frise/redémarrage également passé. Pas de test
sur téléphone Android physique.
APK vérifié : 24 fichiers Python/scripts Godot byte-identiques aux sources,
version 22 et même certificat. Reprise des deux parcours natifs sous CPython
3.13 staged, relecture gratuite à zéro PA et gating des commandes validés.
84 régressions Python passent ; les 40 parcours complets (20 seeds × deux
équipements) restent résolubles. Test de stabilité des objets v21 rejoué et passé
avec le nouveau dialogue. Aucune modification du générateur de crimes.
SHA256 APK : `393f34d9ed81049f2c43ccaf1dbec44229c72f136873a99f8e69eab2fddb08ea`.

## Objets persistants et transfert explicite du corps — v21 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v21.apk`, versionCode 21 / `0.21-causal`.
Même moteur `causal-3d-v3` et signature : sauvegardes v18–v20 conservées.

Cause corrigée : les fixtures étaient déduites des actions encore disponibles,
puis placées selon leur index courant. Consommer une action supprimait son objet,
changeait parfois la représentation du corps et décalait les objets suivants.
`causal_game.fixture_catalogue(place)` décrit désormais le mobilier depuis le
plan physique immuable, avec type/forme et `slot` permanent. Les actions et
`selectable` sont une projection séparée. Godot place les objets selon `slot`,
pas selon leur index après filtrage. Fouilles, prélèvements, lectures, attente,
épuisement des PA et nouvelle visite ne changent plus les meshes du décor.
Les marqueurs disparaissent quand leur action est consommée ; poubelles,
documents, terminaux, traces et objets au sol restent. La valise d'empreintes
est présente dès l'équipement, pas une table surgissant au premier indice.
Stations fixes aux archives vidéo, commissariat et laboratoire.

Seule exception physique : `exam_request` représente le transfert à la morgue.
Le bouton sur le corps l'annonce explicitement et ouvre un choix même s'il
reste l'unique action : retoucher le corps ne le transfère pas implicitement.
La réponse confirme le transfert ; le corps quitte la scène et apparaît sur
la table d'examen déjà présente à la morgue. La demande au légiste produit le
même état, sans duplication ni déplacement des autres objets. Rapport lu ou
retour sur la scène ne recréent pas le corps. Délais/coûts/prérequis inchangés.

Régressions : `test_causal_game.py` compare les descriptions physiques avant/
après toutes les interactions, à zéro PA, après transfert depuis les deux lieux,
lecture du rapport, revisite et replay. Quatre seeds couvrent lame, contondant et
poison. Test appartement : agenda, documents/photos/fouilles et mobilier conservé.
`tests/fixture_stability_smoke.gd` compare les vertices/couleurs/transforms des
meshes effectivement rendus, hors halos, et déclenche de vrais touchers.
Captures téléphone desktop 18:9 (seed 7) et 20:9 (seed 5 poison) :
`guidance-fixtures-{before,inspected,collected,transferred,morgue}-v21-*.png`.
Rendu inspecté ; pas de test sur appareil Android physique.
245 tests Python passent (`test_causal_game.py`, `test_scenario_observations.py`).
Parcours `causal_guidance_smoke.gd` 20:9 passé : source d'alibi, rapport médical,
frise, redémarrage et annotations isolées. APK arm64 vérifié : 24 modules Python
et scripts Godot byte-identiques aux sources, version/signature contrôlées.
SHA256 APK : `e6dda2dc1db7aedab1957b51a6eafe8df5bf05dd48b2052825db620d6ad0d330`.

## Carnet aéré et premier bar distinct — v20 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v20.apk`, versionCode 20 / `0.20-causal`.
Moteur `causal-3d-v3` et certificat inchangés : enquêtes v18/v19 conservées.
Aucune modification des scénarios, horaires, coûts ou règles de déduction.

Carnet : zone de lecture à gauche (environ deux tiers), colonne indépendante
de suspects à droite. Six onglets compacts : Éléments, Pistes, Horaires, Notes,
Contacts, Fiche. Portrait touchable → fiche détaillée à gauche ; récit et source
indépendante avant la navigation et la biographie. Portrait/contexte/déclarations
secondaires dépliables. Éléments acquis en accordéon, un document ouvert à la
fois, source/tour et aperçu. Notes garde le journal intégral. Noms cités sans
profil restent en silhouette ; contacts toujours séparés des suspects.
Annotations et déplacement animé des cartes conservés, aucun PA/temps dépensé.
Chaque colonne possède son propre scroll avec l'arbitrage tap/drag existant.
En-tête compact, fermeture en haut ; nouvelle enquête et frontières dans « ••• ».
Thème local au carnet pour ne pas changer la taille des commandes du monde.
Faits partagés de l'ancien moteur restent accessibles en volet replié.

`interior_lounge.gd` : nouveau `bar_room`, inspiré de
`../Neon Noir Voxel Barroom.png`. Comptoir bas/barman derrière, étagères et
bouteilles, chat néon voxel, briques, entrée rouge, banquettes, billard vert avec
poches/boules/queues et suspension ambre. Deux meshes groupés par matériau,
trois lumières sans ombres ; même World3D/caméra/post-traitement. Les lumières
du lounge générique sont désormais masquées avec son décor. Restaurant et
autres lieux gardent le lounge ; aucun faux client ou objet interactif ajouté.
Le billard est **décoratif** : pas encore d'activité/alibi « joue au billard ».
Pour l'ajouter ensuite, construire une activité réellement observée dans les
présences privées, puis la projeter dans récit/corroboration/frise, sans étendre
artificiellement les bornes attestées.

Validation : `tests/notebook_layout_smoke.gd` rejoue l'enquête réelle seed 7,
touches natives sur onglets/portraits/annotations/documents, scroll indépendant
et absence de mutation du gameplay ; profils cités sans traits, cas rempli par
consultation effective des sept fiches police. `tests/barroom_smoke.gd` vérifie
la pièce distincte, budget de meshes/lumières, toucher du barman et retour au
restaurant générique. Captures inspectées en 1080×540 et 1200×540 :
`guidance-notebook-*-v20-{18x9,20x9}.png` et
`guidance-barroom-v20-{18x9,20x9}.png`. `solo_setup_smoke.gd` teste les options
compactes puis la confirmation de nouvelle enquête ; mode APK embarqué sans
WebSocket vérifié. Replays v18/v19 byte-identiques au snapshot sous CPython 3.13
staged. Régressions legacy `rpg_smoke.gd` et `touch_momentum_smoke.gd` adaptées
au nouveau rail/options et passées (annotations/reprise, localisation sans PA,
frontières, momentum et fin de tour). Rendu desktop, pas de mesure ni de
validation tactile sur Android matériel.
SHA256 APK : `f148860207045dccb995dcbb72b8b8273eaf5685863fce1999e99b88b6ba6914`.

## Souvenirs humains — v19 (12 octobre 2026)

APK `builds/nexus-city-solo-debug-v19.apk`, versionCode 19, même moteur
`causal-3d-v3` / même signature : enquêtes v18 reprenables, sans nouveau tirage.
La vérité physique et les historiques d'actions sont inchangés.

`scenario_evening.remembered_times()` réduit les souvenirs de service à un
intervalle intérieur de quarts d'heure : 19:55–21:05 devient 20:00–21:00, jamais
19:45–21:15. `spoken_time()` donne « 20 h », « 20 h et quart », etc. Récits,
corroborations, registre, pistes et frise utilisent ces mêmes données publiques,
pas les minutes privées des présences. Construction refusée si les bornes ainsi
attestées ne couvrent plus la période médicale ; pas d'alibi produit sur un arrondi
extérieur ou un simple « vers ». Les passages du registre sont au contraire
approximatifs et non éliminatoires.

Observation courte du poison : le serveur se souvient de « du service du verre
jusqu'au malaise », sans heure exacte. Claim `event_span`, pas de start/end privé
inventé dans la frise ; son récit reste aux Notes et à la fiche. Récit personnel
sans créneau précis dans ce cas. Rapport/analyse restent requis pour le recoupement.

20/20 CLI résolues avec mêmes nombres d'actions que v18. 603 tests ciblés passent.
Tests : nouvelles
assertions de sous-intervalle/couverture sur 100 graphes, exemple 19:55–21:05,
horaires effectivement prononcés, absence de minutes pour l'observation du verre.
Parcours natifs 18:9/20:9, captures `guidance-*-v19-{18x9,20x9}.png` ; replays de deux fichiers
de test v18 sous CPython 3.13 staged. SHA256 APK :
`9474147a89c2d45373a0990b32eb1e61ba686e807ad814d1fbadca6af2e1745b`.
Le disque a maintenant 63 Gio libres ; build Android standard à nouveau possible.

## Enquête accompagnée et chronologie — v18 (11 octobre 2026)

APK `builds/nexus-city-solo-debug-v18.apk`, moteur `causal-3d-v3` : nouvelle
enquête nécessaire. Sauvegarde précédente conservée à part ; signature inchangée.
Sept suspects (huit personnages avec la victime), noms cités avec positions
actuelle/prochaine mais sans signalement ni domicile privé appris. Seeds générées
entre 0 et 1000 inclus ; UUID continue d'isoler les annotations.

Les corroborateurs Alex/Camille/etc. ne sont plus générés : vrais serveurs/barman
des lieux publics, observant des présences construites et validées avec les
trajets/rendez-vous existants. Au moins deux corroborations accessibles exigées
par le sampler ; auteur jamais doté d'un alibi. Les contacts de rue existants
gardent un rôle, « La vendeuse de nuit » / « Le livreur », pas une identité de
suspect. Menus de vérification repliés, personnel derrière comptoir et marqueurs
de service placés devant, visibles.

Carnet : déclaration ambre, récit corroboré vert (source recueillie), alibi
confirmé seulement après période médicale / analyse nécessaire. Aucune exclusion
visuelle automatique. Glow des fiches et services selon les vérifications
réellement effectuées. Pistes de soirée : lieu exact et interlocuteur, fermées
après recueil sans demander de revisiter la source. Piste du verre après prélèvement.
Scène du crime : pancarte/entrée corail, autres lieux cyan ou logements violets.

Le légiste peut être sollicité à la morgue après constat ; même demande que sur
la scène, sans double paiement. Délai maximum quatre fins de tour, statut gratuit,
rapport et rappel gratuit répété affichant la même période. Horaire placé en
premier dans sa réponse. Poison : période d'administration, décès ultérieur ;
présence ailleurs distincte d'une observation de non-contact avec le verre.

Nouvel onglet Horaires / `PlaySession.timeline()` : seules données acquises,
intervalles médicaux et récits/corroborations, rendez-vous prévus et images
consultées, souvenirs arrondis comme dans le texte prononcé. Aucun nom d'acteur
privé dévoilé par CCTV. La CLI expose `horaires` / `chronologie`. Traitement de
temps exact vs approximatif/planned explicite ; passage isolé ≠ alibi.

20/20 CLI guidées réussies, 23 actions en moyenne (13–43). Deux poisons restent
longs (43 actions chacun), ainsi qu'un contondant sans description d'agression
(40). Ce n'est pas un score de fun ; la répétition des corroborations demeure
une limite. 905 tests ciblés passent (601 + 304) ; trois parcours natifs
guidance/poison 18:9 et 20:9. Les rapports joueur ne parlent plus de « substance
fictive », sans ajouter de détail chimique. Voir `PLAYTEST_V18.md` pour validation,
captures téléphone et paquet.

Incident disque plein : `causal_game.py` restauré byte-identique depuis le stage
du précédent build avant réapplication des modifications. Seules copies Android
régénérables `intermediates/{merged_native_libs,stripped_native_libs}` supprimées
(~612 Mio), pas de sauvegardes ni d'APK historique. Build final dans un répertoire
temporaire `/dev/shm` pour éviter de remplir à nouveau le disque. Restent environ
50 Mio libres : prochain build normal nécessitera de libérer de l'espace.

## Identités, contacts et carnet — v17

Clarification : les PNJ de service peuvent être sources d'information ; ne pas
multiplier les témoins annexes. Cette passe conserve les corroborateurs existants
pour ne pas casser les alibis, mais rend leur statut « Témoin » explicite dans
le dialogue/monde/carnet. Services = « Personnel ». Onglet Contacts séparé des
cinq suspects, sans marquages d'enquête ni exclusion. Barman/restaurateur placés
derrière le comptoir (hauteur abaissée), suspects en zone clients ; témoins dans
une autre zone, jamais à la place du barman.

`PlaySession.named_people()` : noms entiers dans textes réellement acquis ou
profil connu. `notebook.profile_known` reste distinct : citation = silhouette,
aucun trait/adresse/position ajouté, aucun filtre physique acquis. Nom cité dans
un document ou réponse => fiche nommée, sans lecture de sources privées. Profil
obtenu par rencontre ou casier seulement. Contacts cités/rencontrés mémorisés,
propos déjà acquis regroupés, jamais transformés en suspects.

Isolation des annotations : `SoloSession.case_id` UUID nouveau par enquête,
persisté et conservé à la reprise ; ajouté aux sauvegardes v16 sans les invalider.
Clé carnet = moteur + UUID + détective. Anciennes annotations indexées seulement
par seed laissées dans le fichier mais non réutilisées ; les deux marquages sont
vidés au reset. Le cas exact « Lina déjà écartée » n'a pas été reproduit, mais les
risques de collision entre enquêtes/moteurs et de priorités non vidées sont traités.

645 tests ciblés passent ; `tests/causal_contacts_smoke.gd` vérifie citation sans
profil, Camille Témoin, contacts séparés, taps natifs, bar peuplé et reset des
annotations. Captures desktop téléphone 18:9/20:9, pas de téléphone physique.
APK `builds/nexus-city-solo-debug-v17.apk`, versionCode 17. Détails : `PLAYTEST_V17.md`.

## Fil d'enquête et vie quotidienne — finalisation v16

La v16 inclut aussi les demandes de la nuit : `scenario_access.py` construit une
journée continue domicile/travail, déjeuner, sorties facultatives dîner/verre.
Chaque transition paie le trajet du vrai graphe ; pas d'usage du rôle criminel.
Positions commises en préparation/fin de tour uniquement. Fiches identifiées :
position actuelle, activité et position prévue à la prochaine fin de tour
(`at + 15`, si aucune autre action n'intervient). Inconnus sans ces informations.
Repérage sans PA. Petits sièges/tables/assiettes/verres voxel batchés, aucune
lumière ou interaction d'enquête supplémentaire pour ces accessoires ordinaires.

`PlaySession.deductions()` explique seulement les comparaisons acquises : alibi
indépendant + période médicale/analyse du verre, ou incompatibilité avec une
description d'ASSAUT et profil appris. Passage innocent, photo, colère et
empreinte partielle ne deviennent jamais une exclusion. Carnet : recoupements
remontés, marquages « Écarter / À investiguer » toujours manuels.
`inquiry_threads()` matérialise des fils nommés depuis correspondance effectivement
acquise, réponses entendues et liens sentimentaux appris. Aucun conflit privé
dévoilé par un transfert ; destinataires d'une rumeur non transformés en acteurs.
États ouvert / témoignage à recouper / hypothèse infirmée. Un témoignage recueilli
avant la période médicale ne ferme plus prématurément sa piste.

Contre-enquêtes : corroboration prioritaire des griefs ordinaires/romances quand
elle est physiquement possible ; `compatible_presence()` vérifie aussi les trajets
et rendez-vous préexistants. Sinon, pas d'alibi fabriqué. Le sampler exige une
issue publique pour chaque crochet narratif innocent (`context_is_refutable`) :
corroboration réelle OU description d'agression incompatible. Il rejette plutôt
que modifier le crime. Huit épisodes domestiques distincts par distribution ;
une réponse vide n'est plus préfixée à un vrai témoignage de rendez-vous manqué.
Un grief banal ne masque plus une autre tension déjà connue du personnage.

Validation : 1 682 tests ciblés passent en trois lots (641 + 680 + 361), dont
40 parcours adapter sur 20 seeds avec/sans Crochetage. 20/20 parcours CLI guidés
réussis : 19,55 actions en moyenne contre 28,65 pour l'exploration exhaustive,
avec des exceptions moins efficaces ; ni oracle caché ni mesure objective du fun.
Trois parcours natifs accès/services/vie, captures 18:9 et 20:9 examinées.
`tests/causal_life_smoke.gd` montre explicitement Tess : grief de prêt, témoin
Camille, rapport médical, hypothèse infirmée ; puis suspect au déjeuner.
APK final `builds/nexus-city-solo-debug-v16.apk`, ARM64 42,21 MiB, versionCode 16,
même certificat debug. 16 modules Python et 8 assets Godot comparés aux sources ;
CPython 3.13 staged : 0/1/7/19 (fiches, bar, morgue, positions, replay exact).
Pas de téléphone physique testé. Détails/limites : `PLAYTEST_V16.md`.

## Accès, conversations et entourage v16 (10 octobre 2026)

APK `builds/nexus-city-solo-debug-v16.apk`, moteur `causal-3d-v2` : **nouvelle
enquête nécessaire** ; la sauvegarde v15 incompatible est conservée en `.invalid-*`.
Toucher un suspect ouvre ses questions, sans réponse automatique. La rencontre
ne révèle que son apparence ; lien et métier sont appris lorsqu'on les demande.
Inconnu : « Je ne connaissais pas la victime. Oscar, vous dites ? » ; aucun
« récemment » qui suggérerait une relation passée inexistante.

Couloirs distincts du lounge : portes uniquement, personne visible au seuil après
sonnerie, titre « Devant chez X ». Pas d'entrée si un habitant est présent ;
Crochetage occupe un slot et ouvre les domiciles vides (1 PA puis entrée 1 PA).
Logement de la victime accessible à l'enquête. `scenario_access.py` construit
des horaires domicile/travail indépendants de la culpabilité ; positions changées
uniquement en fin de tour. Cyan = lieux publics ; violet = couloirs d'appartements.
Palace : position d'arrivée corrigée ; morgue = seconde porte physique de l'hôpital.
Les compteurs quartier/lieu et portraits de présence comprennent **les suspects
seulement**, jamais les services ou témoins annexes.

`scenario_life.py` : présentations optionnelles d'amis/fratrie au partenaire de la
victime, fait daté postérieur aux deux liens, mémoire réciproque. Pas de clôture
transitive automatique ni de connaissance des conflits privés.
`scenario_evening.py` : épisode domestique de chaque suspect placé avant les
présences/trajets contraints, marges de déplacement validées. Récits personnels
pour tous, plus visites/sorties/emprunts réellement construits ; aucun alibi prouvé
par sa propre déclaration. Un récit de visite ouvre une piste vers Alex/Camille/…,
PNJ de corroboration rencontré aujourd'hui dans un lieu public. Témoignage possible
avant le rapport ; exclusion seulement avec chronologie médicale (et analyse du
verre pour le poison). Carnet distingue récit non confirmé et alibi confirmé.

Menu recentré Mobile/Témoin/Alibi ; détails personnels et autrui repliés.
Plus de bouton « derniers échanges » : documents aux terminaux domestiques ;
résumés de tensions orales bornés aux faits reçus/expérimentés. Agenda : question
du rendez-vous pour TOUS les suspects après découverte, pas de tell par nombre
de boutons ; piste localisable. Serveurs toujours matérialisés, registre construit
depuis `venue_presences` et le keeper effectivement de garde (`VenueRegistration`
validé), pas d'alibi complet déduit d'une visite. Commissaire physique, fiches/casiers
repliés avec photo, identité, domicile et métier, sans condamnation fabriquée.
Cheveux noirs/bruns/blonds/roux échantillonnés dans un RNG distinct, avatars,
portraits et vrais critères de perceptions/caméras. Passages innocents = vrais
trajets d'emprunt ; seules les descriptions d'ASSAUT filtrent l'identité.
Toute description projetée reste compatible avec >=2 personnes. Au moins un
témoin annexe par cas, plus souvent deux ; entretiens jusqu'à 22 h, contacts
localisables après constat. Seed demandée au HUD (reproduire avec `--seed=<HUD>`
et la même version, pas avec la graine interne de rejet).
Inventaire des mécanismes pas encore portés : `REGRESSION_AUDIT.md`.

Tests actuels : `tests/test_causal_game.py`, `tests/test_scenario_play.py`,
`godot/tests/causal_access_smoke.gd` (18:9/20:9),
`godot/tests/causal_services_smoke.gd` (poison, médecin/labo, 20:9).
Captures `art/captures/access-*-v16-*` et `causal-*-v16-*`.
Tests desktop tactiles, pas de téléphone physique. La CLI pure garde les positions
à domicile et ne simule pas les portes ; la couche d'accès est dans l'adaptateur 3D.

## Correctifs mobiles v15 (9 octobre 2026)

Fermer une conversation sans cue est maintenant explicitement acquitté côté
Godot : plus de bouton « En attente… » persistant. Les services passent par
`service_menu` puis `ask/service_action` : aucun inventaire ni résultat livré
avant une question. `service_status` répond aussi quand l'examen n'est pas demandé,
sans PA ni passage de temps. Pas de fixture d'attente, délai exprimé en tours au
plus, horloge/fin de tour manuelle inchangées. Les suspects ont cinq questions
uniformes, mêmes coûts messages/souvenirs (1 PA une fois) indépendamment du rôle.

Poubelles conservées physiquement après fouille (position stable), halo et cible
retirés. Archives vidéo uniquement à la Régie, quartier puis quatre créneaux
directs ; `PlaySession.camera_window` conserve les acquisitions horaires sourcées,
limite le paquet reçu à >=2 candidats, relecture gratuite. Les anciens historiques
v14 caméra/attente restent rejouables ; un terminal de rue en cours est refermé.
Tests natifs `causal_smoke.gd` couvrent aussi fermeture via toucher réel du footer,
questions du serveur et statut du légiste ; `causal_services_smoke.gd` couvre les
questions avant résultats réels, poison sans sang et délais via fins de tour.
Captures `causal-*-v15-*`. Aucun téléphone physique testé.
Validation : 723 tests ciblés puis 52 tests adapter relancés après finalisation ;
20 enquêtes résolues par le protocole public, paquets CCTV vérifiés >=2 candidats.
Trois parcours natifs réussis (18:9 / 20:9 / poison-services), captures examinées.
APK v15 ARM64 42,2 MiB, même certificat debug que v14 ; sources Python/UI
comparées au paquet, reprises du code staged sous CPython 3.13 pour 0/7/19.

## Raccordement du générateur causal au solo 3D (9 octobre 2026)

`causal_game.py` : façade publique de `PlaySession`, protocole déjà lu par Godot,
sans duplication des règles ni export des artefacts futurs/supports privés.
Desktop par défaut = causal solo ; Android plugin = causal solo. Ancien serveur
WebSocket explicite `--server-url=...` et solo `--legacy-engine` conservés.
Sauvegardes JSON distinctes par moteur, reprise exacte par replay. Pas de migration
Loom, pas de modifications de la logique multijoueur.

Quatre rues physiques, domiciles/voisins attachés à leur vraie rue, restaurant,
laboratoire et morgue distincts. Poubelles/caméras locales, plages horaires repliées,
terminaux/albums/agenda/objets domestiques, témoins et personnel matérialisés avec
halos. Un toucher commence une conversation. Questions sur autrui repliées,
profils/correspondance et signalements au carnet, adresses seulement identifiées.
Empreintes avec compétence dédiée, deux slots ; découvertes/comparaisons aux Notes.
Briefing initial et pistes de départ explicites. Manteaux/tailles des avatars
respectent les apparences du scénario, portraits avec mêmes manteaux.

6 PA/tour, mouvement fondé sur vrais temps de trajet, accès domicile depuis sa rue,
tour manuel et horloge ; pas de déplacements PNJ inventés (suspects à domicile
comme dans le prototype CLI). Corps voxel, sang seulement si réellement produit,
intérieurs génériques globaux existants. Délais médecin/labo, pas de double sang.
Toutes les limites du générateur restent décrites dans SCENARIO_PLAYABLE.md : pas
encore de certificat de mobile complet ou d'empreinte identifiante unique.

Tests natifs/captures : `tests/causal_smoke.gd` (18:9/20:9),
`tests/causal_services_smoke.gd` (poison, labo/morgue, 20:9). Utiliser des
`--solo-save=/tmp/<nouveau>.json` et `--notes-path=/tmp/<nouveau>.json` isolés.
Captures `art/captures/causal-*` ; taps natifs objets, suspects, médecin/technicien.
20 enquêtes achevées via le protocole client avec PA, pas une mesure de fun.
618 tests ciblés passent (adapter + solo + scénario jouable/découverte + ancien
contrat de présentation). APK causal v14, reconstruction et contrôles décrits dans
android-solo/README.md. Aucun push/commit de cette passe.
Relance finale : 38 tests adapter/solo passent ; deux parcours natifs recapturés,
dont empreintes et poison/médecin. APK ARM64 42,2 MiB, versionCode 14, même
certificat que v11. Les 14 modules Python nécessaires et sept scripts de rendu/UI
comparés octet par octet aux sources dans l'APK ; replays du paquet staged sous
CPython 3.13 pour graines 0/7/19. Pas de téléphone physique testé.

## Nouveau générateur — CLI jouable, social et sources locales (9 octobre 2026)

`python scenario_sampler.py --play --seed 7 --skills fingerprints,search`.
Entrée indépendante, sans DB/serveur/LLM ; ancien Game/Godot/APK inchangés.
Social cohérent (liens ou aucun, fratries transitives, voisinage géographique),
communications bornées, albums, agenda, questions sur autrui, carnet/pistes.
Caméras quartier + heure ; poubelles partout, dépôt réel sur la fuite ; empreintes
partielles avec compétence occupant un des deux slots ; comparaison d'objets.
Rapports retardés et analyse d'objets, pas de sang artificiel dans les poisons.

Sélection/rejet avec trois familles de preuve : témoignages croisés, témoin/caméra,
exploration ouverte. Aucun artefact ni paquet reçu en une action n'identifie seul
un suspect. Profils inconnus préservés côté joueur. 100/100 explorations aveugles
terminées, deux parties manuelles ; corroborations indispensables 36/100 contre
99/100 avant diversification. Ce n'est pas une garantie de fun ou de mobile complet.
Le bruit entre voisins est un conflit ordinaire, pas encore une racine meurtrière.
Voir [SCENARIO_PLAYABLE.md](SCENARIO_PLAYABLE.md), notamment ses limites.
Validation finale : 1 664 tests ciblés passent, dont 348 dédiés ; compilation et
`git diff --check` OK. Relance aveugle finale : 100/100 affaires, 1 742 actions.
Pas d'édition 3D/UI, de nouvel APK, de sauvegarde modifiée ni de push de cette passe.

## Prototype — étape 7 de témoins (9 octobre 2026)

`scenario_witnesses.py` : événements physiques, présences/commutes, attention,
visibilité/obstruction/reconnaissance et souvenirs distincts. Serveur : service
seulement ; hôte : rendez-vous manqué ; 0–2 PNJ annexes éventuellement présents.
Réponses sans connaissance = « Je ne sais pas », jamais une accusation inventée.
Descriptions neutres (manteau/taille), supports dérivés des vrais attributs,
≥2 personnes par récit entier ET paquet d'entretien. Pas de noms de coupables.

CLI `--step 7 --walkthrough`, projection V2 ; étape 6/V1 conservée. Référence photo
de la victime déclarée à l'examen, entretien unique, lieu/présence/prérequis réels.
`scenario_diversity.py --witnesses` : 500 crimes inchangés, 4 806 artefacts atteints,
57 cas resserrés, un croisement d'identité unique (graine 235, deux témoins ambigus).
**Pas une reconstitution certifiée** : audit suppose apparences connues ; contexte
et manipulation du verre ne deviennent pas automatiquement de la culpabilité.

Sources règles 13/APK v11 inchangés ; PNJ non ajoutés au monde Godot. Pas de
sauvegarde/base modifiée, pas d'assets ou dépendances Android. Voir
[SCENARIO_WITNESSES.md](SCENARIO_WITNESSES.md) pour contrôles, limites et suite.
Validation : 1 316 tests ciblés passent, dont 141 dédiés ; audit 500 graines,
compilation et `git diff --check` OK. Pas de commit/push de cette passe.

## Prototype — étape 6 de découverte (9 octobre 2026)

`scenario_observations.py`, projection V1 : artefacts sourcés, actions déclaratives,
prérequis ET, délais relatifs à l'acquisition, cibles physiques, fenêtres du personnel,
acquisition explicite et payloads sans supports/provenance privée. Scène, sang/verre,
examen médico-légal, analyse et stocks. Sang comparé seulement après prélèvement de
référence sur le corps ; un accès privé au verre ne devient pas un témoignage.
≥2 candidats par artefact **et paquet d'action**, aucune culpabilité inventée.

CLI `--step 6 [--walkthrough] [--json]`. Adaptateur au solver existant ; projection
physique seulement : corpus 500, sources atteintes, **aucun cas encore résolu**.
134 tests dédiés passent. Sources jeu règles 13 et APK v11 inchangés. Pas de
modification du rendu, sauvegarde, dépendance Android ou base utilisateur.
Voir [SCENARIO_OBSERVATIONS.md](SCENARIO_OBSERVATIONS.md) pour limites/next steps.

## Sources 0.13 — partenaire, triangles et déroulements (9 octobre 2026)

**APK v11 non reconstruit.** Sources en `RULES_VERSION=13` : nouveau lien
`LinkToVictim.PARTNER`, libellés, répliques et témoignages. Pas de rancune inférée
du seul fait d'être partenaire. La distribution seedée change ; replay ancien
refusé, aucun fichier utilisateur supprimé. Reprises testées en Loom isolé.

Prototype offline : noyau V3 (six amorces, dont rivalité sentimentale), relations
datées avec fin, triangles ordinaires optionnels indépendants du meurtrier,
liens à la victime dérivés. Exécution V4 : `tracking`, `agreed_meeting`, `venue` ;
dernier patron = empoisonnement fictif au bar/resto, verre servi, effet retardé,
aucune trace de sang, départ de l'auteur pouvant précéder la mort. Deux accès au
verre réellement coprésents et trajet d'un innocent, pas des candidats fictifs.

`scenario_situations.py`, `scenario_diversity.py`, nouveaux tests dédiés.
CLI `--situation`, `--method poisoned`, `--public-scene` (aperçu expurgé du verre).
Corpus 500 : suivi 160, rendez-vous 171, bar/resto 169 ; 180 signatures sans noms.
86 triangles concernent la victime et des innocents, pas le meurtrier.
**Variété des vérités, pas encore des résolutions** : pas de solver complet,
photos/témoignages/analyses/CCTV à projeter, générateur non branché au jeu.

Voir [SCENARIO_SITUATIONS.md](SCENARIO_SITUATIONS.md). Contrôles Godot 18:9/20:9 :
restaurant, serveur tactile et vraie interrogation du partenaire (graine 29,
personne 8), captures `current-partner-phone-v13-*` inspectées. Pas de changement
du design 3D, pas de nouvelle dépendance Android. Ne pas confondre ces captures
du lien intégré avec des screenshots d'un scénario V4 jouable.

Validation : **1 862 tests Python passent**, dont 199 nouveaux tests de triangles,
rencontres et empoisonnement ; corpus de 1 200 exécutions (200 graines × six
noyaux), conservation et reproductibilité. Partie CLI réelle graine 5 terminée,
37 actions, tour 11, 22 notes, reprise Loom exacte en base temporaire.
Compilation Python et `git diff --check` passent. Aucun commit/push de cette passe.

## Sources 0.12 — restaurant et provenance expérimentale (9 octobre 2026)

**APK non reconstruit : `builds/nexus-city-solo-debug-v11.apk` reste en règles 11.**
Les sources du jeu sont en `RULES_VERSION=12` : ajout de **Le Comptoir**, connecté
à l'hôpital, fréquentation, départ possible, serveur physique, échanges d'arrivée,
quartier et bâtiment bas ambre. Lounge générique réutilisé dans le monde global.
Le changement de carte/routines invalide le replay ancien ; aucun fichier de
sauvegarde utilisateur supprimé pendant cette passe. Reprises Loom testées
uniquement en bases temporaires isolées.

Le nouveau générateur reste **offline**, pas branché à `Game` / `CaseStory` :

- `scenario_kernel.py`, V2 : restaurant, cuisine, gestion du restaurant.
- `scenario_crime.py`, V3 : quatre modes d'acquisition (`owned`, `taken`,
  `borrowed`, `opportunistic`), trajets de préparation et accès effectifs ;
  prêteur présent pour un emprunt, prise opportuniste sur le suivi réel.
- `scenario_means.py` : propriétaires, stocks, transferts, conservation,
  objet conservé/laissé/caché, emprunt innocent optionnel avec aller-retour.
  Constats d'absence **dérivés** des sorties du rangement, pas indices inventés.
- `--public-inventory` : petite projection publique, lieu/heure contrôlés,
  aucun preneur/objet précis/guilt révélé, ≥2 suspects possibles par artefact
  complet. **Pas encore un graphe d'enquête résoluble ni un solver de convergence.**

Voir [SCENARIO_MEANS.md](SCENARIO_MEANS.md) pour les limites et commandes CLI.
`restaurant_smoke.gd` exécuté en 1080×540 et 1200×540 : préparation solo,
bâtiment, intérieur global, serveur et tap tactile réel. Captures
`restaurant-{world,room,server}-phone-v12-{18x9,20x9}.png` inspectées.
Rendu desktop, pas de mesure sur appareil Android. Nouvelle géométrie limitée
à un bâtiment existant réutilisé ; aucun nouvel asset bitmap ni dépendance serveur.

Validation : **1 608 tests Python passent**, dont 146 sur les moyens/provenances.
Corpus physique de 1 000 générations et 120 fixtures acquisition × méthode ×
devenir × noyau. Partie CLI réelle graine 5, conversations/échanges : affaire
terminée, 37 actions, tour 11, 22 notes ; reprise Loom exacte, base isolée.
`git diff --check` et compilation Python passent. Pas de commit/push de cette passe.

## Solo 0.11 — présences, échanges et audit (9 octobre 2026)

`builds/nexus-city-solo-debug-v11.apk`, même signature debug, `RULES_VERSION=11`.
Ancienne partie Android conservée à part, nouvelle préparation. Sources/ensemble
des candidats inchangés ; les actions gratuites `listen` sont maintenant rejouées.

- `presence.places` / `.districts` : effectifs et portraits/silhouettes, noms et
  visages seulement appris par ce détective. PNJ de service exclus des effectifs.
- `CaseStory.scenes_at` → projection moteur `arrival_scene` → cue `stage=scene`
  avec `beats` de locuteurs publics. Godot écoute automatiquement à l'entrée dans
  la **pièce**, pas au simple déplacement dans le quartier. CLI propose l'écoute.
  Une paire réellement liée (relation, voisins, collègues), aucun nom inventé,
  aucune accusation aléatoire. Note privée, sans PA ni fait certifié ajouté.
  `scenes_seen` par détective ; replay JSON/Loom garde la consommation et le journal.
- `investigation_solver.py` / `scenario_audit.py` : outils offline non embarqués.
  1 000 graines, projection narrative + alibi : vidéo obligatoire dans 100 % des
  cas ; recette 3 lectures + vidéo dans 95,64 % des déductions optimales pondérées
  par affaire, et 100 % des conditions de reconstitution actuelles. Déplacements,
  permissions et autres indices physiques exclus. Voir `SCENARIO_AUDIT.md`.
- 841 tests Python (20 solver + 49 présences/scènes), contrôles natifs 18:9 et
  20:9 avec screenshots `arrival-exchange-*`, `presence-*` ; low-FX 18:9.
  Affaire CLI graine 5 terminée avec conversations/échanges, 37 actions, tour 11,
  22 notes, reprise Loom exacte. Rendu desktop, pas de téléphone physique.

Modularité : le contrat JSON protège le rendu ; les trois axes et la règle de
confrontation restent spécifiques côté Python. Pas encore un générateur plug-in
entièrement interchangeable. Ne pas confondre chemin de pistes et précondition.

APK v11 vérifié : 10 modules Python / 27 assets identiques aux sources ; imports
depuis les ZIP sous Python 3.13, présence publique et scène gratuite exécutées.
Aucune permission Internet ; outils d'audit, serveur et Loom non embarqués.
SHA-256 `8840df85c95ec3b6ddf3f6043f14bc1d267b52e867d83e4c0ae02c704c2155cc`.

## Solo 0.10 — interactions physiques et lisibilité (9 octobre 2026)

`builds/nexus-city-solo-debug-v10.apk`, même signature debug. `RULES_VERSION=10` :
la rumeur vague ne révèle plus de noms ni de domiciles ; ancienne sauvegarde
Android conservée en `.invalid-*`, nouvelle préparation. Génération du graphe
et ensembles d'indices inchangés, toujours ≥2 candidats par observation.

- `view.staff` : barman, ouvreuse, croupier, infirmière, commissaire, technicienne,
  distincts de `present` / `notebook`. Halo rose, emplacement d'accueil distinct.
  Seulement les actions légales du moteur, vérification d'alibi avec sa vraie voix.
- `view.fixtures` : coffre, papiers/bureau, terminal, téléphone, morgue, poubelles,
  traces au sol. Halos cyan ; toucher exécute l'action ou ouvre ses choix.
  Suppression du menu flottant « Actions du lieu ».
- `view.doors` : appartements adjacents réels, présence au seuil et clés légales.
  « Voir les portes » ouvre les paliers du monde 3D, sans PA ; franchir une porte
  conserve le coût et la serrure réels. Pas d'entrée fictive dans Rue Verlaine.
- Carnet : neutre / « À investiguer » cyan en tête / écarté atténué en bas.
  Reclassement animé 0,32 s, états exclusifs, persistés par enquête/détective.
  Aucun changement de vue moteur, preuve, PA ou accusation.
- Dialogue : cinq choix visibles sans scroll en paysage téléphone. Répliques
  humaines sans consignes d'enquête ; pensée privée ponctuelle du détective,
  portrait cyan et italiques, distincte de la parole et conservée dans Notes.
- Pistes en langage courant ; aucun mobile privé dévoilé depuis le seul registre
  des clés. Pancarte du quartier explicitement repéré prioritaire et persistante.
- 0 PA : saturation du monde seule descend à zéro en 0,45 s, remonte au tour
  suivant ; UI intacte. Fonctionne aussi en `--low-fx` (bloom court-circuité).
- Sang déjà connu : pas de nouvelle analyse. Nouveau prélèvement à l'hôpital :
  analyse sur place. Après fouille discrète : raison explicite du blocage/police.

772 tests Python. Trois parties CLI avec conversations, terminées puis reprises
en bases Loom isolées (42 / 7 / 4). Tests Godot natifs : `presentation_smoke.gd`
en 18:9 / 20:9 / low-FX, `rpg_smoke.gd`, `story_notes_smoke.gd`, `lounge_smoke.gd`.
Captures `*-phone-v10*.png` : questions, rumeur/pensée, ouvreuse, paliers, carnet,
monochrome, quartier repéré. Rendu desktop, pas de mesure sur téléphone physique.

APK : 10 modules Python / 27 assets Godot comparés octet par octet ; moteur
exécuté depuis ses ZIP sous CPython 3.13 sur 0 / 3 / 4 / 7 / 42 / 93, JSON des
PNJ/objets/portes et graphe validés. Aucune permission Internet, Loom ou serveur.
SHA256 : `d66b1a51291770f6683c343992b450fd8dcb4bfceb606143b813e23a664af9de`.

Les sections ci-dessous décrivent les versions antérieures.

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
