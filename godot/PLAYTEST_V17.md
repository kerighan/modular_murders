# V17 — contacts distincts des suspects

Périmètre : clarification d'identité et placement physique ; pas de nouveau
générateur, pas d'ajout de témoins annexes. Les témoins déjà nécessaires aux alibis
restent dans l'affaire avec un statut explicite. Les services peuvent renseigner
le détective, comme auparavant, depuis leurs propres observations/registres.

## Vérifications Python

`python -m pytest tests/test_causal_game.py tests/test_scenario_play.py tests/test_solo.py tests/test_presentation.py -q`

645 tests passent. Régressions nouvelles : citation de nom sans traits/adresse,
non-lecture des sources privées, correspondance de noms entiers, Camille contact
Témoin distinct des cinq suspects, barman Personnel, replay, UUID stable à la
reprise et différent au restart, migration additive de sauvegarde v16.

Le cas exact rapporté « Lina déjà écartée » n'est pas reproduit. Correction
préventive fondée sur deux risques réels : carnet indexé seulement par seed et
priorités non vidées au reset. Les anciens marquages restent dans le fichier,
mais ne sont plus réutilisés avec une autre distribution.

## Parcours natif et captures

`tests/causal_contacts_smoke.gd`, seed 7, options `--phone-ui`, rendu Compatibility.
Formats 1080×540 et 1200×540, simulation tactile desktop, pas d'appareil Android.

- Inspection, commissaire, fiche de Tess, conversation et citation de Farid.
- Farid nommé, silhouette, aucun trait/domicile ajouté.
- Soirée de Tess, piste Camille, toucher du vrai PNJ : statut Témoin.
- Corroboration reçue, carnet Contacts séparé des suspects.
- Tours manuels jusqu'à un client au bar, barman derrière le comptoir, suspect
  dans la zone clients, dialogue Personnel.
- Écarter/Favoriser deux suspects, nouvelle enquête, préparation : aucun marquage
  précédent et nouvelle clé du carnet.

Captures `art/captures/contacts-{name-only,witness-dialogue,notebook,bar-lanes,staff-dialogue}-v17-{18x9,20x9}.png`.
Le comptoir a été abaissé après examen pour ne pas cacher le visage du personnel.

## Livraison

APK v17 : moteur `causal-3d-v2` inchangé, sauvegarde v16 reprise sans nouvelle
enquête imposée. Signature debug identique, mise à jour sans désinstallation.
Le changement ne porte ni les anciennes mécaniques absentes, ni le multijoueur.
CPython 3.13 staged : seeds 0/1/7/19, personnel/contacts et replay exact validés.
16 modules Python et 8 assets Godot embarqués comparés octet à octet aux sources.
ARM64, versionCode 17, 44 125 890 octets (42,08 MiB).
SHA-256 : `2080a681ade507bc9b9ca10009eacfdc37e4122796fc54185fd2badd92f11796`.
