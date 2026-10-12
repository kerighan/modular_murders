# Étape 6 — découverte V1 (prototype offline)

`scenario_observations.py` projette l'exécution physique V4 **sans modifier sa
vérité ni son RNG**. Ce n'est pas encore le générateur du jeu Godot/APK.
Suite disponible : [étape 7, témoins](SCENARIO_WITNESSES.md). Les chiffres et
limites ci-dessous décrivent l'étape 6 seule, maintenue telle quelle.

## Contrat de découverte

- `Artifact` : texte, type, sources causales et support privé de compatibilité.
- `DiscoveryAction` : opération, lieu, personne/objet cible, observations requises
  (ET), observations produites, disponibilité, délai et fenêtres de présence.
- `DiscoveryState` : informations acquises avec leur date, actions consommées.
- `DiscoveryPlan.perform` : contrôle des prérequis, lieu, date, délai et présence ;
  acquisition explicite, pas de révélation lors d'une simple lecture d'UI.

Les payloads publics ne contiennent **ni supports, ni provenance privée, ni
identifiant d'objet utilisé, ni rôle meurtrier**. Le catalogue expose le contenu
futur à un développeur, pas le journal courant du joueur. Le walkthrough commence
par convention le lendemain à 08 h 00 : ses dates d'acquisition ne sont pas des
estimations médico-légales de l'heure du crime.

Chaque artefact ET chaque paquet livré en une action conserve ≥2 personnes
compatibles. Deux paragraphes ambigus ne doivent pas former un singleton dans
un même clic. L'intersection entre plusieurs actions reste possible plus tard.
Le validateur refuse les sources absentes et les cycles de prérequis.

## Ce qui est réellement projeté

1. Corps découvert en examinant la scène, sans révéler la méthode privée.
2. Sang au sol ou verre : prélèvement/conservation après examen de la scène.
3. Demande d'examen du corps, puis consultation médico-légale après un délai.
4. Sang : comparaison uniquement après obtention du prélèvement de référence
   sur le corps. Pas de groupe sanguin inventé ni de sang de meurtrier ajouté.
5. Verre : analyse après conservation ; contamination entièrement fictive,
   sans auteur ni correspondance magique avec un flacon précis.
6. Objet abandonné : type visible, sans affirmer qu'il est l'arme du crime ni
   dévoiler son propriétaire. L'objet caché n'est pas magiquement découvert.
7. Stocks : constat dérivé du registre existant, auprès du personnel réellement
   présent. Un prêt innocent reste un prêt, pas une accusation.

Un accès au verre dans la vérité privée n'est **pas un témoignage**. Sans une
source qui a effectivement observé les personnes, la projection ne nomme
personne et ne réduit pas les candidats à la liste des présents privés.
Les constats corporels décrivent la victime/la méthode, pas les suspects : leurs
supports restent toute la population. Les supports d'inventaire sont des accès
possibles, pas des présences réelles. Aucun masque artificiel fabriqué pour faire
converger un solver.

La morgue et le laboratoire sont des services déclarés dans ce prototype,
avec opérations/cibles physiques, **pas des lieux ajoutés à la carte du jeu**.
Le transport institutionnel du corps et les analyses sont des conventions
d'auteur. Les délais 30/60 minutes sont des conventions de gameplay fictives,
pas une modélisation médicale. Déplacements/PA, autorisations, persistance et
personnages visibles dans les nouveaux services restent à intégrer.

## Essayer / vérifier

```bash
python scenario_sampler.py --step 6 --seed 42 --motive remove_obstacle --method poisoned --walkthrough
python scenario_sampler.py --step 6 --seed 17 --situation agreed_meeting --walkthrough
python scenario_sampler.py --step 6 --seed 23 --goal report_incident --json
python -m pytest -q tests/test_scenario_observations.py
```

Sans `--walkthrough`, catalogue des sources/prérequis. Avec : acquisition
chronologique automatique de toutes les sources disponibles, **sans simulation
de déplacements ou PA**, puis nombre de personnes compatibles. Aucun diagnostic
« résolu » pour satisfaire un objectif de diversité.

L'adaptateur `solver_actions()` expose les actions au `InvestigationSolver`
existant ; `graph()` fournit son algèbre de supports. L'audit logique ignore les
fenêtres horaires/coûts de déplacement. Le runtime de découverte vérifie les
horaires ; cet adaptateur n'est donc pas un certificat complet de jouabilité.

Contrôles : **134 tests dédiés** ; corpus 500 graines, 160 suivis, 171 rendez-vous,
169 scènes de bar/resto ; toutes les sources projetées atteintes. **500/500 restent
non résolus, avec cinq suspects compatibles**. C'est attendu : les indices qui
reconstituent les actions des personnes n'existent pas encore dans cette couche.

## Retour empirique et prochaines étapes

Les exemples privés lus rendent plus claire l'intention de la victime : retourner
chez soi, venir discuter ou aller signaler une faute à la police. En revanche,
« discuter du différend » reste générique ; certains prêts ordinaires éloignés
du crime font du bruit plutôt qu'une piste. Pas encore un playtest d'enquête V4
résoluble ni une preuve de plaisir joueur.

Prochaines couches, dans cet ordre :

1. **Observateurs et connaissances** : présences réelles, événements vus/entendus,
   participants connaissant une conversation ; témoignage borné par ces faits.
   Le serveur peut avoir vu un service sans avoir vu l'altération du verre.
2. **Manifestations contextuelles** : séparation, rémunération détournée, nouvelle
   relation ; objets/documents/messages réellement produits et détenus. Une photo
   de couple ne prouve pas une intention criminelle ; innocents également vivants.
3. **Projection ambiguë et convergente** : indices complets ≥2 candidats, puis
   intersection de sources indépendantes, reconstitution méthode/chronologie.
   Rejeter les cas insolubles ou à raccourci plutôt qu'inventer une fausse preuve.
4. **Audit de résolution** : certificats minimaux, actions incontournables,
   recettes sans permutations, retrait d'une famille d'actions. Pas de CCTV
   universelle : elle ne concerne que la rue réellement empruntée.
5. **Parties CLI à l'aveugle**, puis adaptateur au contrat JSON existant du jeu.
   Les mesures structurelles ne remplacent pas cette étape de ressenti joueur.
