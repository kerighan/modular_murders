# Triangles et déroulements — noyau V3, exécution V4

Prototype offline, **pas encore le générateur des parties Godot/APK**.
Le lien « partenaire amoureux » est, lui, ajouté au jeu existant (règles 13).
Suite : [étape 6 de découverte](SCENARIO_OBSERVATIONS.md), premières analyses
et acquisitions à prérequis ; pas encore de témoignages ni de convergence.

## Un triangle n'est pas un mobile

`Relationship` possède désormais un début et une fin optionnelle. Le lien à la
victime est dérivé des relations : partenaire actuel, ex, ami, collègue,
connaissance, ou inconnu (`link_to_victim`). Une personne peut avoir plusieurs
liens vrais, par exemple collègue et partenaire. Aucun lien ne dérive du rôle
« meurtrier » ; une romance ne crée pas automatiquement de conflit.

`romantic_triangles(world)` détecte les configurations ancien/nouveau couple
sur ces relations. Il ne leur attribue ni jalousie, ni violence, ni intention.
Le builder ajoute optionnellement un triangle ordinaire. Dans les affaires de
révélation professionnelle, il peut concerner la victime et **deux innocents**,
sans participation sentimentale du meurtrier. Dans les autres noyaux, un
triangle ordinaire peut exister entre trois personnages secondaires.

Nouveau noyau construit : `remove_obstacle × romance × romantic_rival`.

1. A et C ont formé un couple, réellement terminé.
2. C et B forment ensuite un couple actuel.
3. C annonce cette relation à A, puis refuse de reprendre leur ancien couple.
4. A connaît personnellement B et attribue à B cet échec sentimental.
5. A décide d'éliminer B pour tenter de renouer avec C.

`RomanticRivalry` référence les deux relations, les trois acteurs et les
événements d'annonce/refus. Le validateur contrôle les participants, l'ordre,
la connaissance et la réaction. L'effet attendu est une **croyance de A**, pas
une réconciliation garantie. Ce noyau n'est pas une liaison clandestine :
les deux couples ne se chevauchent pas. Les autres triangles (liaison secrète,
jalousie fondée sur une erreur, vengeance contre le partenaire) restent à écrire.

## Trois déroulements réellement distincts

`SituationKind` est séparé du mobile, de la méthode et de la provenance.

| Situation | Déplacement / rencontre | Conséquences |
|---|---|---|
| `tracking` | La victime quitte son travail pour son propre objectif. L'auteur observe la sortie, puis éventuellement suit. | Crime extérieur ; corps, sang, lésion, éventuel objet abandonné. |
| `agreed_meeting` | La victime part de chez elle pour un rendez-vous extérieur accepté avec une personne réellement connue, au sujet de leur différend. | Discussion avant l'attaque ; pas de surveillance du travail ni de faux rendez-vous manqué. |
| `venue` | La victime part de chez elle pour boire un verre au bar ou dîner au restaurant. L'auteur est sur place, sans recevoir son plan privé. | Boisson servie puis altérée, effet retardé fictif, corps/verre, **aucun sang ni lésion de coup**. |

Un rendez-vous contient un accord, un lieu, une heure et une présence attendue,
vérifiée contre le vrai trajet de l'auteur. Le lien social ne fait pas office
d'accord implicite. Les crimes extérieurs restent extérieurs ; l'empoisonnement
est la nouvelle exception intérieure demandée, au bar/restaurant.

L'empoisonnement utilise exclusivement un **produit entièrement fictif** :
aucune substance réelle, quantité ou procédure. Les délais sont des conventions
de scénario, pas une simulation médicale. L'auteur repart après l'altération,
potentiellement avant la mort. Le texte CLI conserve cet ordre chronologique.

`DrinkExposure` représente le verre, son destinataire, le serveur présent, les
instants de service/altération/effet et les accès possibles. Deux personnages
au moins ont un accès compatible : dans le patron actuel, l'auteur et un
innocent dont le trajet depuis chez lui et la présence sont explicites.
`VenuePresence` vérifie cette présence ; un prêt ordinaire antérieur ne doit
pas chevaucher le déplacement. Ce n'est pas une simulation complète des journées,
du service, des lignes de vue ou des occasions discrètes de toucher le verre.

## Ambiguïté et politique de tirage

Les domaines physiques sont filtrés avant le RNG : méthode compatible,
provenance réelle, accord de rendez-vous, déplacements, prêteur présent,
délais et mort avant une divulgation déjà prévue. Une requête incompatible
échoue sans déplacer les faits ou changer discrètement l'objectif.

Tirage : **situation → objectif → raison → plan → méthode → acquisition →
variante physique**. Les situations réalisables sont équiprobables avant les
variantes : vingt objets ou trajets de suivi ne doivent pas écraser les autres
déroulements. Avec un filtre, le domaine restant peut évidemment être plus étroit.
Le patron `venue` utilise uniquement l'empoisonnement pour le moment.

`venue_observations(crime, place=..., discovered_at=...)` fournit un premier
artefact public limité : le verre resté sur la table, accessible au bon lieu
après l'événement. Il ne diagnostique pas l'empoisonnement et ne dévoile ni
l'auteur, ni l'heure d'altération, ni les horaires de départ. L'artefact complet
reste compatible avec **au moins deux personnes réellement présentes**.
`--public-scene` est séparé du récit privé et de `--public-inventory`.

Les présences ne constituent pas encore des témoignages : être là ne prouve
pas avoir vu le geste. Les photos de couples, conversations, analyses du verre,
témoins et vidéos doivent ensuite être matérialisés depuis leurs vraies sources.
Pas encore de solver certifiant la convergence de l'enquête complète.

## Mesure de la répétition

```bash
python scenario_diversity.py --count 500 --seed 0
```

Corpus actuel : 160 suivis, 171 rendez-vous, 169 scènes de bar/restaurant.
180 signatures structurelles (mobile, situation, objectif, méthode, acquisition,
devenir), **sans compter les noms**. Signature la plus fréquente : 2,4 % ;
situation la plus fréquente : 34,2 %. 248 affaires contiennent un triangle sans
le meurtrier, dont 86 autour de la victime.

Ce sont des mesures de **variété de construction**, pas 500 recettes de
résolution différentes ni une note de plaisir de jeu. Il reste seulement six
amorces construites et trois grandes familles de déroulement. La diversité des
chemins de preuves doit encore être auditée par un solver du nouveau générateur.

## Essayer

```bash
python scenario_sampler.py --step 4 --motive remove_obstacle --context romance --stake romantic_rival --requirements
python scenario_sampler.py --step 5 --seed 42 --motive remove_obstacle --situation agreed_meeting
python scenario_sampler.py --step 5 --seed 42 --motive remove_obstacle --method poisoned
python scenario_sampler.py --step 5 --seed 42 --motive remove_obstacle --method poisoned --public-scene
python scenario_sampler.py --step 5 --situation tracking
python -m pytest -q tests/test_scenario_situations.py
```

Noyau `kernel_version=3`, exécution `crime_version=4`, RNG `physical-v4` :
anciens snapshots seedés non conservés. Les stages 2/3 du sampler restent inchangés.

## Jeu existant et captures

`LinkToVictim.PARTNER` possède son poids de tirage, ses libellés, répliques et
formulations de témoignage. Il n'ajoute pas de rancune par défaut. Le moteur
actuel conserve son ancien graphe de résolution ; il ne possède pas encore les
couples détaillés et triangles du nouveau noyau. Le nouveau lien ne doit pas
être présenté comme une intégration du générateur V4.

Règles sources 13, **APK v11 inchangé**. Les anciennes parties ne sont pas
rejouées sous les nouvelles distributions ; aucun fichier utilisateur supprimé.
Captures `current-partner-phone-v13-{18x9,20x9}.png` prises en solo natif,
graine 29, suspect 8 au restaurant, vraie interrogation/question sur le lien.
Rendu desktop en dimensions téléphone, pas une validation sur appareil Android.

Validation : 1 862 tests Python passent, dont 199 dédiés aux nouvelles situations,
relations/triangles et effets de l'empoisonnement ; 1 200 exécutions physiques
reproductibles, mutateurs négatifs et contrôle des artefacts publics. Partie CLI
du jeu existant terminée puis reprise exacte dans une base Loom temporaire.
