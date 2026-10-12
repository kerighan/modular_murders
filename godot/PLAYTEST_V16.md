# Playtest v16 — dérouler un fil, sans tout épuiser

10 octobre 2026. APK `builds/nexus-city-solo-debug-v16.apk`.

## Constats depuis les transcriptions

L'ancien parcours automatique gagnait, mais interrogeait presque tout le monde
sur presque tout et consultait des registres vides sans piste préalable. Une
réussite exhaustive ne garantit ni lisibilité ni plaisir. Les récits personnels
répétés et l'absence de retour clair sur les exclusions accentuaient ce problème.

La stratégie guidée utilise les mêmes faits publics : constat/examen, agenda,
témoins, profils, récits personnels et tiers nommés. Elle évite de vider chaque
sujet d'un suspect déjà incompatible et choisit les heures CCTV à partir du
rapport connu. Elle ne lit jamais le meurtrier ni les masques de candidats privés.
Le calcul public d'incompatibilité reste une aide de test plus rigoureuse que
la mémoire d'un vrai joueur ; ce n'est pas une étude utilisateur.

```bash
python scenario_playtest.py --seed 0 --count 20 --guided
python scenario_playtest.py --seed 7 --guided --transcript
python scenario_play.py --seed 7
# Après avoir rencontré la personne, au même endroit :
# question Tess mobile
# question Tess alibi
# pistes / recouper
```

Sur les seeds 0–19, même version : 20/20 enquêtes achevées dans les deux modes.
Exploration exhaustive : 28,65 actions en moyenne. Guidée : 19,55 (10–33), en
incluant ses questions contextuelles. Certaines affaires restent moins efficaces
en mode guidé (ex. 6/11) : ce n'est pas un succès universel sur le rythme.

## Deux fils relus

Seed 7 : un témoin décrit une personne de taille moyenne ; l'agenda mentionne un
rendez-vous avec Farid. Sa réponse est demandable. Tess évoque une dette réelle,
puis Camille ; le témoignage de Camille couvre la période médicale et permet
d'infirmer cette hypothèse. Un autre alibi et les profils finissent le croisement.
Le fil de la dette n'est pas un cul-de-sac et ne désigne pas le tueur à lui seul.

Seed 19 : un rendez-vous non honoré et un passant à midi existent, mais le second
n'est pas un témoin de l'agression du soir. Une description de cheveux bruns
réduit les possibilités seulement après identification des personnes ; le
témoignage indépendant ferme ensuite une autre possibilité. Le récit d'attente
ne commence plus par « je n'ai rien à vous raconter ».

Les repas/sorties du jour d'enquête ne réécrivent **jamais** la veille du crime.
Les emplois du temps nouveaux restent indépendants du rôle criminel.

## Garanties vérifiées

- >=2 compatibles par indice et paquet d'action, puis convergence par croisement.
- Aucun innocent ne ment ; relation/lecture/présentation datées et bornées.
- Pas d'information sur les positions des inconnus dans leurs fiches.
- Alibi corroboré incompatible avec aucun trajet/rendez-vous existant.
- Chaque crochet innocent proposé par le sampler possède une voie d'infirmation.
- Déclarations, relations, passages innocents et empreintes partielles ne sont pas
  des exclusions de culpabilité.
- Marquages du carnet toujours manuels ; pas de déplacement au milieu du dialogue.
- Reprise exacte et parties réalisables sans compétence obligatoire.

1 682 tests ciblés (641 + 680 + 361), dont 40 parties via le protocole 3D sur
20 seeds avec deux équipements différents. Parcours natifs accès/services/vie,
captures 18:9 et 20:9 inspectées. Exécution des modules staged CPython 3.13 sur
0/1/7/19, puis comparaison de 16 modules et 8 assets avec l'APK signé.

## Limites assumées

Le rythme n'est pas encore une diversité causale illimitée : six racines
exécutables, reconstitution complète du mobile non certifiée. Les alibis de
conversation domestique restent fréquents ; une future bibliothèque d'activités
de la veille doit pouvoir les varier sans collision physique.

Les témoins de la veille ont un créneau d'entretien le lendemain jusqu'à 22 h,
pas encore un emploi du temps reconductible. Le CLI pur ne simule pas les portes
ni les routines de jour : ces règles sont testées dans l'adaptateur et Godot.
Pas de test sur un vrai téléphone. Les anciennes fonctions non portées sont
répertoriées dans `REGRESSION_AUDIT.md`, pas présentées comme restaurées.

Captures utiles : `art/captures/life-open-thread-v16-18x9.png`,
`life-refuted-thread-v16-18x9.png`, `life-positions-notebook-v16-18x9.png`,
`life-public-lunch-v16-18x9.png` et variantes 20x9.
