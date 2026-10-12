# Passation : client Godot

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
