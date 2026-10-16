# Nexus City — APK solo hors ligne

Version **0.54-causal** : `../builds/nexus-city-solo-debug-v54.apk`, moteur `causal-3d-v13`
(sauvegardes conservées). Français relu : élisions et prépositions des lieux.

Version 0.53 : moteur `causal-3d-v13` (sauvegardes conservées). On peut toujours sonner à une porte habitée, même sans point d'action.

Version 0.52 : moteur `causal-3d-v13` (sauvegardes conservées). Rater la jauge de persuasion ferme la conversation ; l'aiguille
tourne encore un peu plus vite ; finir le tour dans un appartement vous remet dans la rue.

Version 0.51 : moteur `causal-3d-v13` (sauvegardes conservées). La gardienne de l'immeuble répond dès le premier tour.

Version 0.50 : moteur `causal-3d-v13` (sauvegardes conservées). Le coupable qui avait rendez-vous avec la victime ne l'admet plus.

Version 0.49 : moteur `causal-3d-v13` (sauvegardes v48 archivées, nouvelle affaire). Le personnel ne disculpe plus que trois
suspects au plus par affaire ; les autres ont une visite partielle ou rien.

Version 0.48 : moteur `causal-3d-v12` (sauvegardes conservées). Sortir d'un appartement crocheté remet dans la rue comme avant ; les
suspects ne disent plus que le barman les a vus.

Version 0.47 : moteur `causal-3d-v12` (sauvegardes conservées). L'aiguille de la jauge tourne un peu plus vite.

Version 0.46 : moteur `causal-3d-v12` (sauvegardes v45 archivées, nouvelle affaire). Une affaire sur cinq est l'œuvre d'un inconnu :
aucun lien avec la victime, et s'il l'a étudiée, la caméra de sa rue sur les jours précédents,
la gardienne de l'immeuble et la sonnette de l'entrée en gardent la trace.

Version 0.45 : moteur `causal-3d-v11` (sauvegardes conservées). Le légiste explique « objet contondant ».

Version 0.44 : moteur `causal-3d-v11` (sauvegardes conservées). L'onglet Éléments s'ouvre sur le résumé de l'affaire (victime,
lieu, heure du crime, signalement recueilli, preuves, suspects, pistes) ; l'approche d'un
suspect montre sa description et « Lui parler (1 PA) » sur le même écran.

Version 0.43 : moteur `causal-3d-v11` (sauvegardes v42 archivées, nouvelle affaire). Un logement partagé porte le nom de tous ses
habitants, et vivre avec la victime n'est plus un indice : des innocents partagent aussi leur
logement.

Version 0.42 : moteur `causal-3d-v10`. Un suspect ne nomme que les gens qu'il connaît ; un inconnu est
décrit par un ou deux traits à recouper avec les portraits du carnet.

Version 0.41 : Le commissariat a sa propre salle néon-noir : comptoir d'accueil
sous l'écusson, cellule rouge, bureaux aux écrans allumés, tableau d'enquête.

Version 0.40 : La question « Témoin » raconte un souvenir, une ou deux personnes
avec ce qu'elles faisaient, au lieu d'une liste de noms.

Version 0.39 : Corrige l'approche d'un suspect (le bouton « Lui parler (1 PA) »
manquait, la liste de questions restait vide) ; la première notification d'un tour attend la
fin du titre « TOUR n ».

Version 0.38 : Au début de chaque tour, de petites notifications en haut de
l'écran annoncent ce qui vient de devenir possible : rapport du légiste prêt, résultats du
laboratoire, témoin de retour, employé rappelé arrivé sur place.

Version 0.37 : moteur `causal-3d-v10` (les sauvegardes v36 sont archivées, nouvelle affaire). Au Néon Bleu et au Comptoir, « Faire
appeler un employé… » : le patron rappelle un suspect dont vous avez établi qu'il travaille là
(sa réponse « Métier », sa fiche police ou « Qui travaille ici ? ») ; au tour suivant il est sur
place et son domicile est vide (1 PA).

Version **0.36-causal** : `../builds/nexus-city-solo-debug-v36.apk`. Toucher un suspect ouvre
d'abord sa description par le détective, puis « Lui parler (1 PA) » ou « Quitter » ; ses
réponses passées sont dans un déroulant en bas de sa fiche.
Portes d'appartements espacées (cinq sur le fond, les autres sur le mur de
gauche) ; toucher une porte la fait coulisser et apparaître la personne avant
le dialogue. Questions préfixées de façon cohérente (Lien, Alibi, Témoin,
Mobile, Métier, Entourage, Agenda), plus de « (gratuit) », compteur
« Questions 1/3 · PA » visible, un ⚡ sur les actions qui déclenchent une
jauge (et ces questions restent proposées à 0 PA). Dans les dialogues, la
victime en rouge, les suspects nommés en or, les preuves en main en cyan.
« Invérifiable » pour un récit que personne ne peut confirmer. Commissariat
moins haut, banlieue aux parcelles irrégulières (plus petites, décalées,
parfois un terrain vague). Même moteur, même signature, enquêtes conservées.


Version **0.35-causal** : `../builds/nexus-city-solo-debug-v35.apk`.
Quartiers avec une identité : couleur de base, accent, skyline et habillage
propres (mâts et parabole aux Ondes, enseignes et guirlandes au Palace,
auvent et terrasse au Comptoir, haies et croix à Saint-Vital, canal avec
garde-fou au Canal, balcons à Verlaine, mâts et bornes au Central), halo de
couleur par quartier (lumière douce + flaques de néon teintées), liseré de
trottoir à la couleur du quartier, un coin de chaque parcelle planté, et
les cellules vides varient (jardin, parking, bassin). Même moteur, même
signature, enquêtes conservées.


Version **0.34-causal** : `../builds/nexus-city-solo-debug-v34.apk`.
Parler à un suspect coûte 1 PA et donne trois questions neuves (compteur
« 1/3 » dans la boîte ; relectures gratuites) ; au-delà, une jauge de
persuasion réussie offre la question suivante, sinon 1 PA ; « Contact
humain » saute la jauge. Le relevé d'empreintes est ouvert à tous avec une
jauge, sauté par la compétence. La question « Témoin » dit maintenant qui le
suspect a aperçu, où et à quelle heure (trois réponses sur quatre sont
informatives, contre une sur vingt-cinq). Le serveur nomme l'emprunteur d'un
objet prêté ; l'objet se retrouve chez lui, étiqueté « (du Néon Bleu) », on
l'emporte au labo : pas de sang, fausse piste refermée. Les PNJ gardent
leurs coûts actuels. Même moteur, même signature, nouvelles affaires.


Version **0.33-causal** : `../builds/nexus-city-solo-debug-v33.apk`.
Onglet « Réseau » du carnet : qui connaît qui autour de la victime, d'après
les témoignages, la question « métier » et les albums ; les personnes
écartées s'estompent ; toucher un nom ouvre sa fiche. Le personnel d'un
établissement peut dire qui y travaille (« Qui travaille ici ? »), et quand
un outil manque, celui qui l'a pris y travaille plus souvent qu'avant (une
piste, pas une preuve). Même moteur, même signature, nouvelles affaires.


Version **0.32-causal** : `../builds/nexus-city-solo-debug-v32.apk`.
Un seul témoin de l'acte sur la scène du crime ; un second témoin éventuel a
vu autre chose (un départ, un passage). Même moteur, même signature,
nouvelles affaires.


Version **0.31-causal** : `../builds/nexus-city-solo-debug-v31.apk`.
Jauge tournante : tout le monde peut crocheter une porte ; sans la
compétence, une aiguille tourne et il faut toucher l'écran quand elle passe
dans la zone verte (un tour pour lire, deux tours avant l'échec automatique).
Dans la zone : la porte s'ouvre ; à côté : le crochet ripe, 1 PA perdu, on
peut réessayer. La compétence Crochetage saute la jauge. Le score est
enregistré avec le coup (la reprise d'une partie ne rejoue pas la jauge).
Même moteur `causal-3d-v9`, même signature, nouvelles affaires.


Version **0.30-causal** : `../builds/nexus-city-solo-debug-v30.apk`.
Signalement moins frontal : sur la scène, un seul témoin décrit un trait,
les autres ne donnent que l'heure et une silhouette ; la caméra du quartier
montre toujours un trait différent de celui des témoins, le détour par la
Régie vidéo rapporte donc quelque chose. Même moteur `causal-3d-v9` et même
signature que la v29 (nouvelles affaires tout de même : les seeds changent).


Version **0.29-causal** : `../builds/nexus-city-solo-debug-v29.apk`.
Tissu social : les collègues d'un même lieu de travail se connaissent toujours
(« On travaille ensemble »), les gens d'une même rue le plus souvent, et le
cercle direct de la victime est moins systématiquement amical (amis, fratrie
et connaissances plus rares ; collègues et voisins nommés comme tels). La
question « métier » cite les collègues, ce qui donne des noms à chercher au
commissariat. Alibis partiels : certaines personnes, parfois le coupable, ont
vraiment été vues dans un établissement mais pas sur toute la période du
crime ; le personnel le confirme sans mettre hors de cause, et le rapport du
légiste redevient nécessaire pour lire un alibi. Récit de soirée
chronologique (« Jusqu'à 19 h et demie, j'étais chez moi… Ensuite, j'étais au
Comptoir… »). Pancartes de quartier hors de portée affichées en transparence
au lieu de disparaître. Empoisonnement : être vu dans la salle ne disculpe
pas ; le personnel ne met hors de cause qu'un client qu'il n'a vraiment jamais
quitté des yeux (pas systématique), les alibis de service et les registres ne
sont jamais dans la salle du crime, et les témoins décrivent l'empoisonneur
comme un agresseur, et il y a toujours au moins un témoin du geste. Crocheter une porte fait entrer directement dans
l'appartement (une seule action). Rencontrer quelqu'un ne donne plus que son
apparence ; son récit de soirée attend la question « Alibi ». Une ex et le partenaire actuel de la
victime se connaissent le plus souvent, avec une humeur tirée au sort
(venimeuse, bienveillante ou neutre) quand on demande à l'un l'avis sur
l'autre ; les ruptures amères du récit (réconciliation refusée) donnent des
réponses piquantes dans les deux sens. La question « quotidien » est remplacée par « Qui fréquentait la
victime ? », qui cite les proches connus du suspect. Moteur `causal-3d-v9` : les sauvegardes v28
repartent sur une nouvelle enquête. Même signature.


Version **0.28-causal** : `../builds/nexus-city-solo-debug-v28.apk`.
Phares corrigés : feux blanc chaud et feux arrière rouges seulement sur les
voitures en circulation, voitures garées éteintes, plus de faisceau au sol.
Même moteur `causal-3d-v7` et même signature : les enquêtes v27 sont conservées.


Version **0.27-causal** : `../builds/nexus-city-solo-debug-v27.apk`.
Horloge au tour par tour : les actions et les trajets ne consomment plus de
temps, l'heure n'avance que de 30 minutes à « Terminer le tour », et c'est à
ce moment-là seulement qu'une enquête hors délai est classée. L'en-tête et
l'onglet Fils comptent en tours ; un dossier rejeté coûte trois tours. Moteur
`causal-3d-v7` : les sauvegardes v26 repartent sur une nouvelle enquête. Même
signature.


Version **0.26-causal** : `../builds/nexus-city-solo-debug-v26.apk`.
Vie de rue : neuf voitures roulent lentement dans les voies libres de la grille
(circulation à droite, phares au sol), les voitures garées serrent le trottoir,
et le train du viaduc passe toutes les trente secondes environ en alternant le
sens. Même moteur `causal-3d-v6` et même signature : les enquêtes v25 sont
conservées.


Version **0.25-causal** : `../builds/nexus-city-solo-debug-v25.apk`.
Moteur `causal-3d-v6` : profils d'affaire tirés par seed (le fil le plus court
change d'une enquête à l'autre), un placard à fouiller dans chaque logement,
empreintes comparables (la tasse de l'habitant est relevée en fouillant avec la
compétence empreintes ; un motif absent de l'objet du crime écarte la personne),
serveurs limités à deux clients cités spontanément. Sauvegardes v24 et
antérieures : nouvelle enquête. Même signature.


Version **0.24-causal** : `../builds/nexus-city-solo-debug-v24.apk`.
Mode libre : difficulté choisie à la préparation (échéance large, serrée, très
serrée), compte à rebours dans l'en-tête, onglet « Fils » du carnet (trois fils
d'enquête avec l'étape suivante en clair), accusation au Commissariat de toute
personne nommée après confirmation (un dossier rejeté coûte 1 h 30 et met la
personne hors de cause), carte de fin (affaire résolue ou classée) puis nouvelle
enquête. Moteur `causal-3d-v5` : les sauvegardes v23 et antérieures repartent
sur une nouvelle enquête. Même signature. Pas de téléphone physique ; détails
dans `../HANDOFF.md`.


Version **0.23-causal** : `../builds/nexus-city-solo-debug-v23.apk`.
Néon Bleu : corps et indices dans une allée dégagée, clients/contacts séparés,
table déplacée, cibles tactiles distinctes et libellés courts. Objets fixes après
interaction, transfert du corps inchangé. Compatible v18–v22, même signature.
Tests natifs et captures desktop 18:9/20:9, avec stress visuel de salle peuplée.
Pas de téléphone physique ; détails dans `../HANDOFF.md`.


Version **0.22-causal** : `../builds/nexus-city-solo-debug-v22.apk`.
Relation avec la victime en premier, alibi/observations/tensions directement
accessibles. Relance PNJ « quelque chose à ajouter » supprimée. Toutes les
premières questions informatives à 1 PA ; relecture gratuite, même à zéro PA.
Questions payantes grisées, dernier texte lisible puis retour à la ville sans
fin de tour automatique. Menus secondaires gratuits. Sauvegardes v18–v21
conservées : les coûts historiques ne sont pas recalculés rétroactivement.
Tests natifs et captures desktop 18:9/20:9, pas de téléphone physique.
Voir `../HANDOFF.md` pour le protocole des choix et la reprise des sauvegardes.

Version **0.21-causal** : `../builds/nexus-city-solo-debug-v21.apk`.
Objets et positions persistants après interaction : seulement les halos/actions
évoluent. Examiner le corps ne le transforme plus ; transfert à la morgue
annoncé dans un choix explicite, puis corps visible sur la table d'examen.
Même état si demandé au légiste. Retour sur les lieux et lecture du rapport
ne déplacent/recréent pas les objets. Compatible v18–v20, signature inchangée.
Régressions Python et comparaisons des meshes après touchers natifs, captures
18:9/20:9 inspectées ; pas de téléphone physique. Voir `../HANDOFF.md`.

Version **0.20-causal** : `../builds/nexus-city-solo-debug-v20.apk`.
Carnet aéré : lecture/éléments à gauche, suspects à droite, onglets compacts,
documents et détails secondaires dépliables, deux scrolls tactiles indépendants.
Annotations personnelles et journal complet conservés. Nouvelle enquête et
frontières accessibles par « ••• ». Premier intérieur distinct du bar avec
billard décoratif, barman derrière le comptoir, néons/briques/banquettes voxel.
Compatible v18/v19, même moteur/signature ; pas de nouvelle enquête imposée.
Parcours natifs desktop et captures 18:9/20:9, replays sous Python 3.13 staged.
Pas de test sur appareil Android physique. Détails : `../HANDOFF.md`.

Version **0.19-causal** : `../builds/nexus-city-solo-debug-v19.apk`.
Compatible avec les enquêtes v18, même moteur/signature. Barman/serveur : souvenirs
par repères humains (heures/quarts d'heure), pas 19:55–21:05 récité à la minute.
La frise et les pistes reprennent les bornes réellement dites, à l'intérieur de
la présence vraie. Poison : souvenir de la séquence verre → malaise, pas d'heure
précise ajoutée au carnet. Vérité du crime inchangée, 20/20 parcours CLI réussis.
603 tests ciblés passent. Captures `../art/captures/guidance-*-v19-{18x9,20x9}.png`,
pas de téléphone physique.

Version **0.18-causal** : `../builds/nexus-city-solo-debug-v18.apk`.
**Nouvelle enquête après v17** (`causal-3d-v3`), sauvegarde précédente conservée
à part, même signature debug. Sept suspects, seeds générées 0–1000. Noms cités :
positions actuelle/prochaine disponibles, portrait toujours en silhouette jusqu'à
apprentissage du profil. Plus de corroborateurs nommés : le barman/serveur
confirme les présences réellement observées. Pistes localisables vers la source
exacte, glow vert après vérification, marquages personnels toujours manuels.
Onglet Horaires : frise des seules données acquises, période du crime en corail,
récits ambre / corroborations vertes / CCTV cyan. Examen demandé à la morgue ou
sur la scène, délai au plus quatre fins de tour ; rappel du résultat gratuit.
La période vient en premier dans la réponse du légiste. Piste du verre prélevé
vers le laboratoire. Pancarte/entrée corail pour la scène du crime.
Captures desktop 18:9/20:9, pas de téléphone physique. Voir `../PLAYTEST_V18.md`.

Version **0.17-causal** : `../builds/nexus-city-solo-debug-v17.apk`.
Sauvegarde v16 conservée, même moteur `causal-3d-v2` et signature debug.
Camille/Alex/etc. existants portent explicitement le statut « Témoin » ; services
« Personnel ». Aucun témoin annexe supplémentaire généré. Carnet séparé en
Suspects / Contacts / Pistes / Notes ; contacts sans boutons d'accusation ni
d'écartement. Le nom d'un suspect cité dans un texte effectivement reçu ouvre
sa fiche en silhouette, sans traits, domicile ou positions : profil appris par
rencontre ou fiche police seulement. Barman/restaurateur derrière le comptoir,
suspects clients dans la salle ; comptoir abaissé pour garder les visages visibles.
Les annotations manuelles sont isolées par instance d'enquête (UUID persisté),
pas seulement par seed, et les deux types de marquage sont effacés au redémarrage.
645 tests ciblés ; parcours tactiles desktop 18:9/20:9 et captures examinées.
Pas de test sur téléphone physique. Voir `../PLAYTEST_V17.md`.

Version **0.16-causal** : `../builds/nexus-city-solo-debug-v16.apk`.
**Nouvelle enquête après v15** (moteur `causal-3d-v2`) ; sauvegarde précédente
conservée à part. Installer sans désinstaller, signature debug inchangée.
Suspects : questions dès le toucher, aucun lien révélé automatiquement. Domiciles :
couloir de portes, sonnerie et conversation au seuil ; entrée impossible si habité,
Crochetage requis si vide (hors domicile de la victime). Routines domicile/travail
commises à la fin du tour. Entrées publiques cyan, couloirs violets, morgue comme
seconde entrée de l'hôpital ; arrivée au Palace corrigée. Présences comptées :
suspects uniquement, personnel/témoins toujours physiquement interactifs.
Amis/proches peuvent avoir été présentés au partenaire, sans omniscience.
Souvenirs personnels pour tous ; visites avec témoin nommé = piste au carnet.
Les témoins sont dans des lieux publics, déclaration ≠ alibi confirmé. La période
médicale et, pour le poison, l'analyse restent nécessaires au recoupement.
Questions Mobile/Témoin/Alibi, autres détails repliés ; échanges écrits dans les
appartements. Rendez-vous questionnable après lecture de l'agenda. Serveurs
physiques, registre de clients ; commissaire et fiches/casiers avec signalement.
Cheveux restaurés dans critères et portraits ; passages innocents réels sur les
mauvaises heures CCTV, pas d'exclusion par une simple présence. Témoins plus
fréquents, pistes de contact, Seed au HUD. `../REGRESSION_AUDIT.md` distingue les
mécanismes retrouvés de ceux à porter (taxi/hacking, dossiers individuels, etc.).
Captures/tests tactiles desktop en 18:9 et 20:9 ; pas de téléphone physique.

Finalisation v16 : déjeuner/dîner/verre avec poses/accessoires légers, lieux actuels
et prochain tour dans les fiches identifiées. Fils nommés, recoupements explicites,
hypothèses infirmables par des sources réellement accessibles ; tri/écartement
toujours manuels. Pas de fausse clôture d'alibi avant le rapport médical.
1 682 tests ciblés, 20 CLI guidées achevées et parcours tactiles natifs ; replay du
paquet sous CPython 3.13 (0/1/7/19), sources du paquet comparées au dépôt.
APK ARM64 42,21 MiB, certificat debug conservé. Voir `../PLAYTEST_V16.md`.

Version **0.15-causal** : `../builds/nexus-city-solo-debug-v15.apk`.
Correction des fermetures bloquées sur « En attente ». PNJ : menu de questions
avant toute réponse, statut explicite sans PA ni avance de temps. Pas d'objet
« attendre » fictif : compte rendu annoncé en tours au plus, horloge inchangée
par consultation du statut. Cinq questions identiques et mêmes coûts chez tous
les suspects. Poubelles fouillées conservées, halo retiré. Archives CCTV seulement
à la régie : quartier puis quatre créneaux directs, relecture gratuite.
Reprise des historiques v14 (anciennes caméras/attentes) conservée.

Version **0.14-causal** : `../builds/nexus-city-solo-debug-v14.apk`.
Le nouveau générateur causal est maintenant branché au monde 3D : suspects et
témoins physiques, poubelles/caméras par rue et heure, objets domestiques, agenda,
correspondance, albums, analyses et empreintes optionnelles dans les deux slots.
6 PA, tours manuels, temps et délais réels du prototype ; carnet/notes/adresses et
pistes conservés. Sauvegarde séparée `nexus-causal-solo.json` : une nouvelle enquête
sans toucher l'ancienne. Les PNJ restent à domicile pour cette première intégration.
Moteur sans serveur, Loom, LLM ni accès réseau. Tous les modules du générateur sont
embarqués explicitement. Signature debug existante conservée, compatible avec une
mise à jour v11 sans désinstallation. Tests desktop natifs 18:9/20:9, parcours
poison/labo/morgue, packaging CPython 3.13 ; pas de test sur téléphone physique.
Ancien serveur multijoueur non migré. Voir ../SCENARIO_PLAYABLE.md pour les limites.

Version **0.11** : `../builds/nexus-city-solo-debug-v11.apk`, même signature debug.
Présences par quartier et lieu (portraits connus / silhouettes inconnues),
échanges spontanés entre habitants réellement liés à l'entrée dans une pièce.
Deux locuteurs, écoute gratuite, journal privé ; une seule fois, y compris après
reprise. Version de règles 11 : ancienne sauvegarde conservée à part, nouvelle
préparation. 841 tests Python, CLI avec échanges et reprises, taps natifs 18:9 /
20:9 desktop. L'auditeur de graphes est un outil de développement, non embarqué.

Version **0.10** (précédente) : `../builds/nexus-city-solo-debug-v10.apk`.
PNJ de service distincts des suspects (halos roses), vrais objets d'interaction
et paliers avec les portes des appartements du graphe. Plus d'actions flottantes
dans un quartier vide. Cinq questions sans scroll, dialogues sans conseils,
pensées du détective en cyan/italiques, pistes en langage courant. Carnet :
« À investiguer » en tête, écartés en bas, animation et choix visuels réversibles.
Le monde passe seul en N&B à 0 PA ; l'UI reste colorée. « Repérer » conserve la
pancarte demandée. Sang déjà connu = aucune deuxième analyse ; morgue = labo
sur place. 772 tests Python, trois affaires CLI terminées et sauvegardées.
Captures et taps natifs desktop en 18:9 / 20:9 ; pas de téléphone physique.
**Nouvelle enquête après v9**, car les rumeurs ne donnent plus une liste de noms.
L'ancien fichier est conservé en `.invalid-*`. Réinstaller sans désinstaller,
avec la même signature ; aucune permission Internet, aucun serveur ou Loom requis.

Version **0.9** : `../builds/nexus-city-solo-debug-v9.apk`.
Plus d'intermédiaire ni de reçu obligatoire. Le vol / dossier compromettant
peut laisser un objet introuvable ou dans une cache anonyme ; la vengeance
n'ajoute plus de montre artificiellement volée. Retrouver l'objet est facultatif,
jamais une condition pour résoudre l'affaire. Les clés partagées / invitations,
le mobile et les images restent des sources à recouper, ≥2 candidats par indice.
Carnet : statut de l'objet appris, pas de cache dévoilée avant découverte.
Accusation erronée : plus de faux « alibi en béton » inventé par le retour système.
723 tests Python, 3 affaires terminées en CLI et reprises depuis des bases isolées.
Nouvelle enquête nécessaire après v8 ; sauvegarde ancienne conservée en `.invalid-*`.
Réinstaller sans désinstaller : même signature. Les versions ci-dessous sont
historiques. Vérifications desktop / packaging, pas de téléphone physique.

Version **0.8** : `../builds/nexus-city-solo-debug-v8.apk`.
Intérieur lounge générique dans le monde 3D global, caméra téléportée (pas
une modale), détective cyan et suspects dorés, conversation en un toucher.
Carnet Personnes / Pistes / Notes, fouille unique, grands choix repliés.
Chaque indice incriminant conserve au moins deux candidats ; objet, conflit
et chronologie / apparence se recoupent. Pas de mensonges d'innocents ni de
rumeurs inventées par les inconnus de la victime. Crime aléatoire toujours dehors.
679 tests Python ; captures et gestes natifs desktop en 1080×540 / 1200×540.

**Nouvelle enquête nécessaire après v7** : la génération a changé. Une ancienne
sauvegarde équipée est conservée en `.invalid-*`, puis l'application revient
à la préparation ; on ne mélange pas les anciens indices au nouveau monde.
Même clé de signature, réinstallation sans désinstallation. Les paragraphes
v7 et précédents ci-dessous sont historiques.

Version 0.7 : `../builds/nexus-city-solo-debug-v7.apk`. Premier générateur
narratif offline : objets disparus, mobiles partagés, fausses pistes, documents,
chronologie et confrontation après recoupement. Les innocents ont aussi une
vie et des secrets. Un mobile ou un mensonge ne suffit pas à conclure.
Sélectionner quelqu'un puis « Parler de quelqu'un… » pour questionner sur ses
voisins/proches ; présenter ensuite les contradictions découvertes.
Onglet Notes du carnet : tout l'historique, avec sources et pistes repérables
sans PA, conservé à la reprise. Première nouvelle affaire Android aléatoire.
Nouvelle enquête conseillée pour essayer la couche narrative depuis le début.
Validation v7 : 575 tests Python ; dialogues, carnet, Notes et questions sur
les proches testés par taps natifs en 18:9 / 20:9. Captures
`../art/captures/story-notes-phone-v7*.png` et
`../art/captures/story-people-answer-phone-v7*.png`. Les modules Python de
l'APK ont aussi été exécutés sous CPython 3.13. Ce sont des vérifications
desktop / packaging, pas une validation sur appareil Android physique.

Version 0.6 : `../builds/nexus-city-solo-debug-v6.apk`. Dans le carnet, le
« Domicile » des personnes identifiées indique quartier et appartement.
Toucher l'adresse repère le quartier sur la carte sans déplacer le détective
ni dépenser de PA ; rejoindre le quartier et ouvrir sa liste d'entrées pour
aller fouiller. Aucun domicile affiché pour les inconnus ou révélé à un autre
détective qui ne connaît pas encore cette personne. Mise à jour sans
désinstallation, sauvegarde et notes personnelles conservées.

Version 0.5 : `../builds/nexus-city-solo-debug-v5.apk`. À distance, un descriptif
par quartier avec ses lieux et le coût en PA ; les pancartes d'entrée et marques
au sol n'apparaissent que dans le quartier courant. « Quartiers » ouvre aussi
la liste des trajets autorisés quand les descriptifs sont hors écran ou masqués.

Carnet : toucher « Écarter » pour rendre une fiche translucide, « Réactiver »
pour la restaurer. C'est votre note personnelle, pas une déduction automatique
du jeu ; aucun PA ni effet sur les règles. Les notes sont gardées par enquête
et détective dans un fichier Godot privé, distinct de la sauvegarde moteur.

Version 0.4 : `../builds/nexus-city-solo-debug-v4.apk`. Dialogues RPG par
personnage, réponses progressives et petite notification « Carnet mis à jour ».
Carnet à portraits, silhouettes inconnues et fiches hiérarchisées. Arrivée dans
le quartier à l'extérieur ; toucher « Entrer » pour ouvrir le bâtiment.

À 0 PA, la dernière réponse reste lisible, puis un fondu ramène à la ville.
Appuyer soi-même sur « Terminer le tour » : les habitants avancent seulement
pendant « La ville continue », avant le titre du nouveau tour. Plus d'arrivées
au milieu d'un interrogatoire. Les sauvegardes v1 des APK précédents sont
reprises automatiquement avec leurs anciennes règles, puis continuent en v2
avec tours manuels. Pas besoin de désinstaller ou de recommencer.

L'APK généré est `../builds/nexus-city-solo-debug.apk` : build de test signé,
Android 7.0/API 24 minimum, ARM64, OpenGL ES 3. Aucun serveur externe, aucune
permission Internet ni clé API. Les dialogues sont les répliques hors ligne du
moteur, pas des appels IA. Pas de multijoueur dans cet APK.

Version 0.2 : corrige la détection Android (`OS.has_feature("android")`, et non
`"Android"`). La présence du plugin embarqué force aussi le mode solo, sans
argument CLI. Le client ne doit jamais essayer le WebSocket dans cet APK.
Copie ARM64 versionnée : `../builds/nexus-city-solo-debug-v2.apk`.

Version 0.3 : glissement tactile avec inertie sur la carte et les menus, même en
partant d'un bouton ; un nouveau toucher arrête le mouvement sans clic parasite.
Les lieux hors de portée n'ont plus de texte ; aucun long trait ne relie les
pancartes aux entrées. Essai de frontières au sol, dorées pour la zone actuelle,
cyan pour ses voisins accessibles à 1 PA. Désactivation dans Carnet →
« Frontières · essai ». Copie : `../builds/nexus-city-solo-debug-v3.apk`.
Les notifications de carte sont masquées pendant le carnet ou les listes de
destinations, pour ne pas recouvrir leurs commandes.

Installer en ouvrant l'APK sur le téléphone et en autorisant cette source
d'installation si Android le demande. Ne pas désinstaller pour mettre à jour :
réinstaller un APK signé avec la même clé conserve la partie.

## Partie et sauvegarde

- Premier lancement : choisir deux équipements et un lieu, puis « Commencer ».
- Sauvegarde automatique après préparation et chaque action terminée.
- Reprise automatique au lancement, y compris les conversations en cours.
- QTE : bouton tactile au-dessus de l'intérieur ; Espace fonctionne sur desktop.
- Nouvelle enquête : Carnet → Nouvelle enquête · solo → confirmer. Remplace la
  sauvegarde par une nouvelle graine, sans modifier le serveur multijoueur.
- Android conserve `nexus-solo.json` dans le stockage privé de l'application.
  Une action/QTE interrompue avant sa fin n'est pas sauvegardée : reprise au
  dernier point validé. Une sauvegarde illisible est conservée en `.invalid-*`.
- `SAVE_VERSION` distingue les formats de fichier ; `RULES_VERSION` dans
  `game.py` protège les changements incompatibles du générateur de scénario.

## Architecture

L'application Android héberge Godot 4.7.2 via sa bibliothèque Maven et Python
3.13 via Chaquopy 17. `NexusSolo.java` expose une passerelle JSON non bloquante
au client. `solo_runtime.py` possède le moteur sur un worker, une file d'actions,
une file de scores QTE et une file de messages. Aucun port TCP n'est ouvert.

Le build recopie seulement les dix modules nécessaires depuis la racine ; il
n'y a pas de duplication manuelle des règles. Seule dépendance Python embarquée :
`networkx==3.4.2`. `server.py`, `store.py`, loom, FastAPI, aiquery et les captures
ne sont pas embarqués. Les assets Godot actuels sont tous procéduraux ; le build
copie leurs sources. Ajouter une vraie étape d'export/import si des textures,
polices ou modèles importés sont ajoutés plus tard.

## Recompiler

Prérequis : JDK 17, Gradle 8.14.3, Python 3.13, SDK Android 35 avec
`platforms;android-35` et `build-tools;35.0.0`. Le build télécharge ses dépendances
Maven/Python ; **la compilation** nécessite Internet, pas le jeu installé.

```bash
bash godot/build_android_solo.sh
```

Le script utilise le SDK local `.sdk/` par défaut, ou `ANDROID_HOME` s'il est
défini. `NEXUS_GRADLE` peut indiquer l'exécutable Gradle et `NEXUS_PYTHON` le
Python 3.13. Il détecte aussi le Python isolé `.tools/python/cpython-3.13-*/`
et le Gradle 8.14.3 déjà présent dans le cache utilisateur. Les nouveaux caches
Gradle restent dans `.gradle-home/` ; aucune configuration globale Godot changée.

Exemple d'installation du Python isolé :

```bash
UV_PYTHON_INSTALL_DIR="$PWD/godot/android-solo/.tools/python" \
UV_CACHE_DIR="$PWD/godot/android-solo/.tools/uv-cache" uv python install 3.13
```

Pour un émulateur x86_64, inclure cette ABI explicitement (APK plus gros) :

```bash
bash godot/build_android_solo.sh -PnexusAbis=arm64-v8a,x86_64
```

La signature est une clé debug Android, pas une clé de publication Play Store.
Conserver cette clé pour les mises à jour de test ; la sauvegarde disparaît lors
d'une désinstallation. Ce n'est pas une release de production.

## Tests et captures

V4 : `pytest -q tests` — 516 cas, dont la stabilité des habitants pendant le
dialogue et la migration des sauvegardes automatiques → manuelles. Test GUI
`res://tests/rpg_smoke.gd` : déplacement, entrée volontaire, sélection, QTE,
trois questions à 0 PA, dernière réponse, retour ville, fin manuelle, phase des
habitants, titre de tour, silhouettes du carnet et scroll tactile sur les fiches.
Captures `rpg-answer-phone.png`, `rpg-city-phase-phone.png`,
`rpg-notebook-phone.png` et variantes `-20x9.png`.

```bash
pytest -q tests/test_solo.py tests/test_navigation.py tests/test_game.py tests/test_server.py
godot --path godot -- --solo
xvfb-run -a -s '-screen 0 2400x1080x24' godot --path godot --resolution 2400x1080 -- \
  --solo --solo-save=/tmp/nexus-fresh-review.json --phone-ui --city --shot \
  --shot-path=/tmp/nexus-solo-phone.png
```

Desktop `--solo` utilise un processus Python local par pipes (aucun serveur).
`--python=/chemin/python` et `--solo-save=/chemin/test.json` permettent d'isoler
les tests de la partie utilisateur. Sans `--solo`, le client desktop conserve
le protocole WebSocket existant. Android utilise toujours la passerelle locale.

Captures : `../art/captures/zones-near-phone.png`, `zones-overview-phone.png`,
`zones-off-phone.png` (comparaison), `zones-20x9.png`, ainsi que les captures
précédentes `solo-phone.png` et `solo-setup-phone.png`. Rendus desktop avec
format/UI téléphone, pas captures Android validées.

La v3 passe les tests Python et les tests GUI de préparation, déplacements et
événements natifs `InputEventScreenTouch` / `InputEventScreenDrag` : scroll en
partant d'un équipement, inertie, sélection par tap, drag depuis une pancarte,
arrêt sans clic, pincement, toggle des frontières, conformité au graphe et bouton
tactile « Terminer le tour ». 84 tests Python passent. Exemple isolé :

```bash
xvfb-run -a -s '-screen 0 1440x720x24' godot --path godot --resolution 1440x720 \
  --rendering-driver opengl3 --script res://tests/touch_momentum_smoke.gd -- \
  --solo --phone-ui --solo-save=/tmp/nexus-touch-fresh.json
```

Un émulateur Android API 30 sans KVM a été essayé, mais son rendu logiciel
SwiftShader et ses blocages système ne permettent pas une validation fiable.
Le tactile matériel et les performances de la v3 restent à valider sur téléphone.

Références : [Godot Android embedding](https://docs.godotengine.org/en/stable/tutorials/platform/android/embedding_in_android_projects.html),
[Chaquopy Android](https://chaquo.com/chaquopy/doc/current/android.html).
