# Nexus City — APK solo hors ligne

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
