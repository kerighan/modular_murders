# Playtest enquête — 8 octobre 2026

## Objets facultatifs v9 — 9 octobre 2026

Vraies parties CLI via `tests/playtest_cli.py`, menus publics, taxi + pied de
biche, QTE parfaits. Déduction = intersection des groupes réellement imprimés
dans les notes, sans consulter l'identifiant secret. Aucun objet récupéré dans
ces parcours, même lorsqu'une cache existe. Aucun intermédiaire à visiter.

| Graine | Branche | Actions | Tour final | Notes |
|---|---|---|---|---|
| 42 | USB cachée, non retrouvée avant conclusion | 21 | 6 | 12 |
| 7 | Bracelet hors d'atteinte | 23 | 8 | 13 |
| 4 | Vengeance sans objet disparu | 30 | 9 | 15 |

Transcriptions `/tmp/nexus-v9-cli42.log`, `/tmp/nexus-v9-cli7.log`,
`/tmp/nexus-v9-cli4.log`. Chaque processus fermé avant reprise Loom exclusive :
victoire, état résolu et notes exactes contrôlés. Aucun fichier utilisateur touché.
Pas un playtest aveugle ni un test de difficulté des QTE.
Rejoués sur les sources finales avec les mêmes compteurs :
`/tmp/nexus-v9-cli42-final.log`, `/tmp/nexus-v9-cli7-final.log`,
`/tmp/nexus-v9-cli4-release.log`.

723 tests Python : 1 000 générations conservent ≥2 candidats par indice,
paires ambiguës et intersection finale ; 40 scénarios résolus sans cache ;
fixtures anonymat, confidentialité, absence d'intermédiaire et faux alibi.
Distribution réelle sur 0–999 : 390 objets introuvables, 369 cachés, 241 absents.
Godot : Notes / Pistes / questions ciblées par taps natifs en 18:9 et 20:9 ;
fixtures avec cache retrouvée et sans objet pour relire les formulations mobiles.
Le coffre partagé reste un motif commun des vols / dossiers : cette itération
supprime le relais forcé, pas toute répétition narrative.
Packaging final : signature conservée, 10 modules Python / 27 assets Godot
comparés aux sources, six graines exécutées depuis les ZIP de l'APK sous Python
3.13 sans réseau / serveur / Loom. Pas de validation sur appareil physique.

## Itération graphe / pistes v8 — 9 octobre 2026

Trois affaires terminées par `tests/playtest_cli.py` dans le **vrai processus
CLI** : menus numérotés, QTE parfaits, taxi + pied de biche. L'automate suit les
pistes publiées et les adresses du carnet ; il déduit via l'intersection des
noms des documents affichés, pas via l'identifiant secret du meurtrier. Pas
de sang ni de dossier médical dans ces parcours. Ce n'est pas un test aveugle
utilisateur, ni une mesure de difficulté des QTE.

| Graine | Actions | Tour final | Notes |
|---|---|---|---|
| 42 | 23 | 6 | 13 |
| 7 | 25 | 8 | 17 |
| 3 | 27 | 9 | 16 |

Les deux derniers parcours précèdent le nettoyage des doublons de journal,
sans modification des règles de déduction. Fermeture du CLI puis réouverture
exclusive Loom : victoire et notes exactes contrôlées sur les trois affaires.
Transcriptions : `/tmp/nexus-v8-cli42-final.log`, `/tmp/nexus-v8-cli7.log`,
`/tmp/nexus-v8-cli3.log`. Bases temporaires isolées, aucune base utilisateur modifiée.
42 rejouée après protection des générations de sauvegarde : mêmes 23 actions,
6 tours et 13 notes ; `/tmp/nexus-v8-cli42-release.log`, reprise exacte contrôlée.

### Ce qui a changé suite aux essais

- Un mobile ou un objet ne réduit plus à un seul suspect, même indirectement
  via le lieu du document. Les copies compromettantes sont partagées entre
  tous les domiciles compatibles. La caméra montre un détail partagé, pas un visage.
- Trois axes (objet / conflit / apparence au bon moment) : toute paire garde
  ≥2 candidats avec la population normale ; les trois convergent. Ce seuil
  vaut aussi par indice physique et par artefact qui regroupe plusieurs détails.
- Les personnes qui ne connaissent pas la victime ne désignent personne.
  Les témoignages sont peu fréquents et sourcés, pas une chaîne aléatoire d'accusations.
- Fouille unique, document complet à la première lecture, onglet Pistes pour
  reprendre une enquête. Question ciblée pendant l'interrogatoire = une question.
- Suppression de tous les faux liens / mensonges d'innocents et du mensonge
  unique qui aurait identifié immédiatement le meurtrier.

### Validation et limites

679 tests Python, dont audits de 1 000 générations et des petites populations.
Voir [les invariants](SCENARIO_GRAPH.md). Tests Godot `lounge_smoke.gd`,
`rpg_smoke.gd`, `story_notes_smoke.gd` en formats 18:9 et 20:9 : intérieur
global sans SubViewport, taps, carnet, questions et retour ville. Captures
`lounge-phone-v8*.png`, `story-leads-phone-v8*.png`, `story-notes-phone-v8*.png`.
APK 0.8 offline ; packaging vérifié séparément, pas de téléphone physique.
Sources embarquées comparées aux fichiers de travail : 10 modules Python et
27 assets Godot. Moteur de l'APK exécuté sous CPython 3.13 sur cinq graines,
sans serveur / Loom. Drag natif intérieur sans PA puis tap conversation validés.

Limites : encore trois familles narratives sur une structure commune ; les
routes facultatives guident mais ne remplacent pas les déductions. La résolution
physique classique reste possible, l'équilibrage global PA / accusation reste
à approfondir. Chambre générique, pas encore des décors distincts par lieu.
Les historiques v7 et antérieurs ci-dessous restent des archives, pas les règles v8.

## Itération narrative v7 — 9 octobre 2026

Deux affaires terminées dans les vrais menus CLI, en offline, QTE parfaits,
sans utiliser les indices sanguins ni les dossiers médicaux. Les choix suivent
les noms, documents et lieux affichés. Ce n'est toujours pas un test aveugle :
les générateurs et ces graines sont connus de l'auteur de l'itération.

| Graine | Famille | Fin | Actions | Documents | Notes après conclusion |
|---|---|---|---|---|---|
| 42 | Chantage / clé USB | Tour 11 | 45 | 7 | 20 |
| 7 | Vol / bracelet | Tour 9 | 38 | 6 | 20 |

Équipement des deux : taxi + pied de biche ; départ Rue Verlaine. Zéro trait
physique collecté dans ces parcours. Les traits classiques et leur route de
résolution restent disponibles, ils ne sont pas remplacés par une obligation
de terminer la narration. Pas d'accusation exploratoire utilisée.

### Ce qui est plus satisfaisant en jouant

- L'objet disparu mène à un reçu, puis à un intermédiaire. Présenter le reçu
  ouvre une visite consentie ; entrer reste une action volontaire, pas un saut
  forcé dans un intérieur. Le reçu mène à deux domiciles, pas à une seule fiche.
- Les deux personnes ont le même conflit réel et avaient manipulé l'objet.
  Dans 42, Marius soupçonne Chloé, innocente, alors que le transfert vient de
  Rose. Il faut départager la rumeur, la possession et la chronologie.
- Chez Chloé / Gaëlle : une attestation et une restitution ancienne. On va
  vérifier l'attestation à sa source au lieu de décréter instantanément l'alibi.
- Chez Rose / Farid : pression personnelle et ticket. La caméra est une
  vérification indépendante de l'utilisateur du ticket ; sans elle, pas de
  confrontation narrative finale. Pas de confession sur un mobile seul.
- Dans 7, Farid nie connaître la victime. Questionner Gaëlle à son sujet
  révèle le voisinage. Lui présenter cette contradiction lui fait reconnaître
  le lien, sans résoudre le crime. La confrontation sur le ticket recoupé
  produit ensuite le mobile et le parcours du bracelet.
- La conclusion raconte heure / mobile / transfert, plutôt que le seul nom.
  `n` montre tout ce chemin avec tours et sources ; fermer avec `q`, relancer
  `--resume 7`, lire `n`, puis accuser a été testé réellement.

### Corrections issues de ces essais et captures

1. Un document chez le rival innocentait trop vite : désormais une nouvelle
   action de vérification dans un autre lieu est nécessaire.
2. Un ticket seul pouvait identifier son utilisateur : vérification caméra
   exigée en plus de l'heure du crime et de la chaîne de possession.
3. Une confrontation prématurée ne doit pas épuiser le sujet définitivement :
   de nouvelles pièces permettent de revenir poser la question.
4. Visite autorisée : même en l'absence de l'hôte, pas besoin d'enfoncer sa porte.
5. Refus après intrusion : pas de petites questions, mais une preuve nouvelle
   reste confrontable afin de ne pas bloquer toute la branche narrative.
6. HUD « 0 preuves » après six découvertes : documents désormais comptés
   séparément, sans les transformer en critères physiques certifiés.
7. Capture mobile : documents mal cadrés et boutons du sous-menu trop étroits.
   Pied de page compacté, largeurs corrigées ; relecture 18:9 et 20:9.
8. Incident sur la base CLI temporaire en l'ouvrant depuis un second writer :
   verrou exclusif Loom ajouté et testé. La partie 7 a été rejouée entièrement
   dans sa propre base, puis fermée / rouverte avec succès. Pas d'incident de
   sauvegarde Android, dont le format atomique est indépendant de Loom.

Historique final 7 : `/tmp/nexus-story-cli7.slSX6v/playtest-7.loom`.
Historique final 42 : `/tmp/nexus-story-cli42.k2r3FB/playtest-42.loom`.
42 a été récupéré avec un lecteur Loom `flag="r"`, reconstitué et sauvegardé
dans une base séparée ; victoire, 45 actions et 20 notes revérifiées.

### Validation et limites

575 tests Python passent. Tests tactiles Godot `rpg_smoke.gd` et
`story_notes_smoke.gd` passent en 18:9 et 20:9 ; onglets, historique complet,
pointeur sans PA, sous-menu et vraie question ciblée. APK 0.7 signé, neuf
modules Python et treize scripts Godot comparés octet par octet aux sources.
Import / création d'affaires depuis les modules contenus dans l'APK également
testés sous CPython 3.13 (7, 42, 93), sans importer Loom ni le serveur.
Captures `story-notes-phone-v7*.png`, `story-people-questions-phone-v7*.png`,
`story-people-answer-phone-v7*.png`. Rendu desktop : pas une mesure de FPS ni
une validation sur téléphone physique.

Audit de **génération**, pas 1 000 parties supplémentaires : 544 vols,
185 chantages, 271 vengeances sur les graines 0–999. Le RNG narratif est séparé
du RNG historique : il n'altère pas les indices classiques.

Limites du premier jet : trois habillages cohérents partagent encore une même
grande structure de reçu / horaires / caméra ; les témoins de relations ont une
connaissance fixe du voisinage et de leur entourage. Les mensonges d'innocents
restent hors du système historique qui certifie les descriptions physiques.
La disparition concerne encore un objet secondaire, sans inventaire utilisable.
Les textes sont procéduraux, sans précalcul LLM. Le coût global des déplacements
et la possibilité classique de deviner une accusation restent à équilibrer.

---

## Audit initial v6 (conservé ci-dessous)

## Ce qui a réellement été joué

Deux parties complètes dans le vrai menu de `cli.main`, choix d'actions manuels,
réponses offline identiques à celles de l'APK. Les QTE ont été fixés à 1 pour
évaluer l'enquête sans mesurer la vitesse de saisie à travers le terminal distant.
Ce n'est donc pas un test de difficulté des QTE ni un chronométrage mobile.
La carte ASCII a été masquée sur la deuxième partie pour alléger les sorties.

| Graine | Équipement | Départ | Résultat | Actions enregistrées |
|---|---|---|---|---|
| 42 | Pied de biche + kit médico-légal | Palace | Résolue, tour 11 | 53, dont 18 questions et 2 fouilles |
| 93 | Hacking + taxi | Rue Verlaine | Résolue, tour 12 | 71, dont 27 questions et 7 fouilles |

Les deux parties ont été accusées après avoir réduit les candidats à un seul,
sans accusation exploratoire. Les générateurs et les indices de ces graines
avaient été inspectés pour l'audit : ce n'est pas un playtest utilisateur aveugle.
Les décisions de navigation/interrogatoire ont suivi les informations affichées.
Historiques Loom de cette session :
`/tmp/nexus-cli-playtest.pkN886/playtest-42.loom` et `playtest-93.loom`.
Le skill Loom a servi à isoler et fermer proprement les bases, puis à relire les
historiques pour vérifier les compteurs. Aucune règle modifiée par cet audit.

## Moments concrets

Attention : spoilers de ces deux graines ci-dessous.

- **42 : un vrai crochet de déduction.** Arme = main gauche. Rose, blonde et
  gauchère, affirme avoir vu une arme tenue à droite. Je veux lui présenter
  l'arme, demander d'où elle regardait, puis confronter son récit. Impossible :
  les trois questions ont été consommées ; elle ne peut plus être interrogée.
  Son dossier médical confirme B. La fin consiste ensuite à rencontrer/identifier
  les personnes restantes, plutôt qu'à exploiter ce mensonge.
- **42 : collecte assez explosive, suite plus administrative.** Une seule fouille
  de l'arme donne cheveux blonds + sang B + main gauche ; le cheveu avait déjà
  donné les cheveux blonds. Les trois critères physiques sont obtenus au tour 4,
  résolution au tour 11. La récompense d'une grosse découverte est bonne ; le
  reste ne développe pas une nouvelle question d'enquête.
- **93 : absence de sang, même recette.** Une lettre donne « ex », l'inscription
  sur la scène redonne « ex », l'arme donne « droitier ». Sept fouilles produisent
  deux critères nouveaux : quatre fouilles chez la victime (trois codes + lettre),
  une scène, une ruelle et un appartement vide. Les codes sont une petite chaîne
  potentielle intéressante, mais inutilisés ici, et le kit de hacking en réduit
  l'intérêt. Le carnet se remplit surtout en posant alibi/lien à chaque personne.
- **Les corroborations sociales sont à garder.** Un témoin écarté par une preuve
  physique peut fiabiliser ses paroles et les personnes qu'il cite. Les noms
  débloquent de vraies pistes et maintenant leurs domiciles. C'est plus prometteur
  que de simplement ajouter des couleurs d'yeux ou des variantes de sang.
- **Les deux conclusions sont une seule phrase :** « X craque. Affaire classée,
  bravo. » Pas de reconstruction du crime ni de retour sur ce qu'on a démontré.

## Variété mesurée, et non sensation seule

Audit distinct du jeu manuel : `Game(seed=s)` pour `s` dans `range(1000)`,
12 suspects, réglages actuels. Lecture de la génération, pas 1 000 parties jouées.

- Sang dans **386/1 000 affaires (38,6 %)**. Dans ces affaires : **288** proposent
  trois indices sanguins et **98** en proposent deux. `place_evidence()` place
  tous les indices compatibles, pas un seul indice varié par critère.
- Médiane **3 critères distincts** ; moyenne **2,855**, contre **6,279 indices
  physiques placés**. Redondance utile pour éviter une impasse, mais les lieux
  différents donnent souvent exactement la même information.
- **94 combinaisons de critères** : il y a déjà du hasard, mais presque toujours
  la même forme de problème, un filtrage d'identités sur sept attributs.
- Un indice chez le meurtrier dans **330 affaires** ; **aucun indice d'enquête
  chez un innocent** dans cet échantillon, confirmé par `place_evidence()` qui
  n'y place rien. Dans **670 affaires**, aucune résidence de suspect ne contient
  d'indice. Les fouilles peuvent identifier un propriétaire à l'arrivée, mais
  rarement donner une piste après le « Rien d'intéressant ici ».
- **Première installation APK : graine 42 fixe** (`main.gd` : `SEED`, transmis à
  `SoloTransport.start`). Elle contient le sang. Changer les objets/la position
  ne change pas l'affaire. « Nouvelle enquête » utilise déjà `SystemRandom` :
  c'est la première création qu'il faudrait varier hors tests/démo explicites.

Limite des tests actuels : le bot de `tests/test_game.py` consulte les lieux
réels des indices et des témoins pour choisir ses cibles. Il vérifie une forme
de résolubilité, pas la lisibilité des pistes offertes à un vrai joueur.

## Diagnostic de game design

Le noyau est un bon « Qui est-ce ? » exploratoire, mais encore peu une
reconstruction de meurtre. L'alibi est un lieu, pas une chronologie. Le mobile
est essentiellement une catégorie de relation. Une découverte ajoute un
attribut ; elle ouvre rarement une action contextuelle ou une branche nouvelle.

Les quatre questions sont fixes et une personne qui a accepté de parler n'est
plus interrogeable ensuite. Les innocents disent toujours vrai ; le meurtrier
seul peut inventer une description. Introduire des mensonges d'innocents serait
intéressant, **mais exige de revoir la fiabilisation automatique des témoignages** :
ce n'est pas un simple changement de texte.

En solo, pas d'échéance globale. Une accusation erronée coûte deux tours et
innocente automatiquement la personne : sans score/pression extérieure, cela
peut devenir une stratégie d'essais. Ce risque vient des règles ; ce playtest
n'a pas pratiqué les accusations à l'aveugle.

## Ordre recommandé pour une prochaine itération

1. **Faire jouer une contradiction.** Réinterroger après un indice nouveau,
   choisir « Présenter : l'arme / le ticket / le message », obtenir une réponse
   spécifique et une piste vérifiable. Un mensonge ne doit pas constituer à lui
   seul une preuve de meurtre. Commencer par une petite affaire cohérente, avant
   de généraliser le générateur ; éviter un bouton qui résout automatiquement.
2. **Varier les raisonnements.** Trois familles d'affaires : chronologie et
   trajets ; objet/provenance et trace ; relations/messages et mobile. Exemples :
   ticket horaire + caméra rendent un alibi impossible ; fibre d'un manteau +
   témoin situent une personne ; objet de la victime retrouvé + récit contradictoire
   relient une résidence au crime. Ne pas remplacer le sang par dix attributs
   qui reproduisent exactement le même filtrage.
3. **Donner une utilité narrative aux fouilles.** Chez un innocent : reçu,
   rendez-vous, lettre, témoignage indirect, qui innocente ou conduit ailleurs.
   Distribuer moins de copies du même critère tout en garantissant plusieurs
   chemins légaux vers les preuves nécessaires et les cas d'alibis indispensables.
4. **Payer le raisonnement en fin de partie.** Petite confrontation puis
   reconstitution « quand / comment / pourquoi » à partir des preuves établies.
   Le joueur explique son accusation, il ne choisit pas seulement un portrait.
   Évaluer seulement ensuite une pression douce / note d'enquête ; ne pas
   compenser le manque de profondeur par davantage de PA perdus ou de QTE.

Correctif très court à considérer séparément : première enquête aléatoire avec
graine explicite conservée pour les tests reproductibles. Les adresses et
l'APK v6 livrés en parallèle ne changent aucune de ces règles d'enquête.
