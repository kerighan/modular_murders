# Playtest v18 — 11 octobre 2026

## Changements visibles

Sept suspects ; deux alibis publics accessibles au minimum. Le barman et le
serveur sont les vrais corroborateurs, pas des personnages Alex/Camille nommés.
Les pistes acquises précisent le lieu et la question, avec un état ambre/vert et
un glow de vérification. Un récit corroboré n'est pas encore un alibi confirmé :
comparaison à la période médicale, et analyse du verre pour le non-contact dans
une affaire de poison. Marquages « Écarter / À investiguer » toujours manuels.

Les noms cités ont leurs positions actuelle/prochaine dans le carnet, sans
physique ni domicile privé révélés. Nouvelles seeds générées 0–1000 inclus.
Scène du crime corail ; lieux publics cyan, logements violets. Personnel
derrière comptoir, marqueur d'interaction devant. Questions de vérification repliées.

À la morgue, demande d'examen après constat, au plus quatre fins de tour et
rappel gratuit de la même période. Réponse affichant l'heure en premier.
Onglet Horaires / commande CLI `horaires` : données acquises uniquement, périodes
corroborées, déclarations, rendez-vous prévus, CCTV consultées et souvenirs
approximatifs ; aucun minutage privé du crime ou nom caché issu d'une caméra.
La piste du verre prélevé mène à la technicienne et se clôt après analyse.

## Parcours CLI

`python scenario_playtest.py --seed 0 --count 20 --guided`

20/20 résolutions. Actions par seed :

```
0:20  1:13  2:28  3:20  4:14  5:43  6:43  7:23  8:20  9:35
10:19 11:21 12:14 13:20 14:14 15:26 16:18 17:13 18:16 19:40
```

23 actions en moyenne ; 7 armes blanches, 11 contondants, 2 poisons. Pas une
garantie d'équilibrage des méthodes. Le parcours utilise labels/semantiques acquis,
pas l'identité privée du coupable ni les masques de compatibilité du graphe.
Transcripts examinés pour 5, 6 et 19 ; interface CLI interactive vérifiée sur 7.

## Validation

905 tests ciblés passent en deux lots (601 adaptateur/playable, 304 moyens et
observations), plus revalidation ciblée du poison après retouche des textes.
Les rapports/dialogues joueur ne répètent plus « substance fictive » ; poison
non nommé, aucune recette chimique ni détail réel d'administration ajouté.

Suites : `tests/test_causal_game.py`, `tests/test_scenario_play.py`, dont
corroboration avant rapport, rappel gratuit sans temps/PA, alibis/prérequis,
documents/casiers, replay, descriptions ambiguës et trajectoires cohérentes.
Nouvelles régressions : sept suspects, seeds aux bornes 0/1000, pas de contact
inventé avec le verre pour un alibi ailleurs, horaires réellement prononcés dans
la corroboration, piste d'analyse acquise puis clôturée, articles français.
Fixture rendez-vous mise à jour : seed 2 est un rendez-vous manqué, pas une
rencontre effectuée. Le test conserve l'uniformité des questions pour tous.

Godot : `tests/causal_guidance_smoke.gd` en 18:9 et 20:9, taps réels, rôle de
service, menu replié, source verte, résultat médical et frise, reset annotations.
Captures examinées : `art/captures/guidance-*-v18-clean-18x9.png` et
`guidance-*-v18-final-20x9.png`. `tests/causal_poison_smoke.gd` couvre le verre,
le statut gratuit, le labo, la morgue et la chronologie d'administration.
Tests desktop avec rendu logiciel ; pas de téléphone physique disponible.

## APK

`builds/nexus-city-solo-debug-v18.apk`, versionCode 18, 0.18-causal, ARM64,
moteur `causal-3d-v3`, nouvelle enquête après v17. Ancienne sauvegarde conservée
à part. Signature debug inchangée :
`ec60e1074b13fa254d7ae148255bd853da2005b7ba3c7223bb70449981361295`.

SHA256 : `4f77fa7149da03ef319a15f91603181899a37810021bd3a00a1bc8a9afcceb55`.
16 modules Python et 9 assets Godot comparés byte pour byte aux sources, dont
`timeline_strip.gd`. CPython 3.13 du build : seeds 0/5/7/19, vues/replays exacts,
sept suspects et aucune chronologie dévoilée avant acquisition.

## Limites à ne pas masquer

La CLI guidée est un test de résolution/accessibilité, pas une mesure du fun.
Les deux poisons prennent 43 actions : beaucoup de recueil puis confirmation.
La seed 19, sans description d'agression apprise, repose surtout sur l'élimination
par alibis (40 actions). Les formulations ont été variées sans modifier les faits,
mais la recette « interroger puis corroborer » peut encore dominer certains cas.
La CCTV atteste un passage, pas une présence continue dans le bar : pas de
nouvel alibi fictif fabriqué à partir d'une image isolée.

Incident disque plein : source restaurée depuis le stage, byte-comparée avant
modification. ~612 Mio de copies intermédiaires Android régénérables supprimées,
aucun APK historique ni sauvegarde effacé. Build final effectué en mémoire
(`/dev/shm`) ; environ 50 Mio libres sur disque, à traiter avant le prochain
build normal. Les modules/stages temporaires ne sont pas requis pour jouer.
