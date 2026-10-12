# V20 — carnet de lecture et premier bar distinct

Cette passe ne modifie pas Python ni le scénario. APK ARM64 `0.20-causal`,
versionCode 20, même signature et moteur `causal-3d-v3` que v18/v19.

## Lecture testée

- 1080×540 (18:9) et 1200×540 (20:9), renderer OpenGL Compatibility desktop.
- Parcours réel seed 7 : constat → fiche police → nom cité → récit de soirée →
  serveur qui corrobore → rapport médical → CCTV/frise → autres fiches police.
- Noms cités en silhouette sans signalement privé ; sept profils ensuite acquis
  par les vraies actions de consultation, pas injectés dans la vue.
- Touches natives sur portraits, onglets, suivi/écartement et titres de documents.
- Drag sur une carte à droite : seul le rail de suspects défile. Drag dans une
  preuve à gauche : seule la lecture défile. Aucun clic parasite, PA ou temps.
- Tri animé et atténuation personnels conservés ; nouvelle enquête efface les
  annotations. Menu de nouvelle enquête ouvert depuis la préparation réelle,
  puis confirmation testée (signal pour la fenêtre native desktop).
- Le bar utilise ses clients réellement présents, le barman derrière le comptoir
  et les questions au toucher. Restaurant revenu au décor générique après sortie.
- Pas de SubViewport, deux meshes de décor fusionnés, trois lumières sans ombres.

Les scripts `notebook_layout_smoke.gd` et `barroom_smoke.gd` doivent utiliser une
sauvegarde neuve. Exemple depuis la racine (remplacer les chemins temporaires
pour chaque lancement) :

```bash
xvfb-run -a -s '-screen 0 1080x540x24' godot \
  --path godot --rendering-driver opengl3 --resolution 1080x540 \
  --script res://tests/notebook_layout_smoke.gd -- \
  --phone-ui --seed=7 --solo-save=/tmp/notebook-review.json \
  --notes-path=/tmp/notebook-review.cfg --capture-suffix=review-18x9
```

Remplacer le script par `res://tests/barroom_smoke.gd` pour la pièce. Le parcours
ancien `causal_contacts_smoke.gd` cible les témoins nommés de v17 : il n'est pas
le test de référence de v20 (ces contacts ont déjà été supprimés en v18).

## Captures contrôlées

Dans `art/captures/`, suffixes `v20-18x9` et `v20-20x9` :

- `guidance-notebook-reading-*` : témoignage déplié, autre récit en aperçu.
- `guidance-notebook-dossier-*` : fiche centrée sur récit/source indépendante.
- `guidance-notebook-populated-*` : 24 notes et sept profils réellement acquis.
- `guidance-notebook-{followed,excluded,notes,contacts,leads}-*` : annotations
  et autres vues avec la colonne de suspects toujours présente.
- `guidance-timeline-*` : frise acquise après le rapport.
- `guidance-barroom-*` : premier décor dédié au Néon Bleu.

## Paquet et limites

APK construit/signature vérifiée. Sources Godot et 24 modules Python du paquet
comparés byte à byte au dépôt, bibliothèques Godot/Python 3.13 embarquées,
aucun Loom, secret ou script de test embarqué. Deux snapshots de tests v18/v19
restaurés identiquement sous le CPython 3.13 staged ; ancienne UI legacy rendue
sans erreur. Test de sélection solo par plugin, sans connexion WebSocket, passé.
Les parcours legacy `rpg_smoke.gd` et `touch_momentum_smoke.gd` passent aussi :
annotations sauvegardées/reprises, adresses connues uniquement et repérage sans
PA, drag/inertie/pinch, options des frontières et fin de tour manuelle.

SHA256 : `f148860207045dccb995dcbb72b8b8273eaf5685863fce1999e99b88b6ba6914`.

Le billard est décoratif. Pour en faire un souvenir du barman, il faudra créer
et vérifier une activité observée cohérente avec la présence réelle : jamais
inventer une heure ou un alibi à partir du décor. Pas de test sur téléphone
physique, ni de benchmark Android. Pas de nouvelle campagne CLI de diversité :
aucun changement de génération ou de règles dans cette passe.
