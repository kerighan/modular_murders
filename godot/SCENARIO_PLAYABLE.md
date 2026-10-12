# Nouveau générateur : CLI et solo Godot 3D

9 octobre 2026. Entrée indépendante de `Game`, sans serveur, LLM ni base.

Mise à jour v18 (11 octobre) : sept suspects, vrais PNJ de service pour corroborer
les soirées, fils localisables et frise publique dans l'onglet Horaires. CLI :
`horaires` / `chronologie`, intervalle médical distinct des passages CCTV et
rendez-vous seulement prévus. Rapport à la morgue demandé une seule fois, délai
au plus quatre fins de tour en 3D, rappel gratuit. Aucun changement aux trois
méthodes physiques ; amélioration des sources et de la lisibilité. Détails et
limites actuelles : [playtest v18](PLAYTEST_V18.md). Les sections v16/v17 ci-dessous
restent historiques ; moteur actuel `causal-3d-v3`, nouvelle enquête requise.

```bash
python scenario_sampler.py --play --seed 7 --skills fingerprints,search
# Entrée équivalente :
python scenario_play.py --seed 7 --skills fingerprints,search

python scenario_playtest.py --seed 0 --count 20
python scenario_playtest.py --seed 0 --transcript
python scenario_playtest.py --seed 0 --count 20 --guided
```

## Chaîne de construction

1. Grammaire causale → noyau concret (six racines exécutables existantes).
2. Objectif de la victime → moyens existants → rencontre, trajets, acte et devenir de l'objet.
3. Remplissage social indépendant : faits de famille, amis, voisins, collègues,
   couples/ex, absence de lien, habitudes, petits griefs ordinaires.
4. Manifestations sourcées : échanges réellement envoyés/lus, albums domestiques,
   agenda privé, témoins avec présence/attention, caméras, contacts et corroborations.
5. Sélection d'une famille d'accès et rejet des cas sans convergence. Aucune
   modification de l'auteur, de la méthode, des apparences ou du trajet pour réparer
   un cas insoluble. Les descriptions uniques ne sont pas rendues ambiguës par
   ajout de faux candidats.
6. Acquisition par le joueur au lieu/à l'heure, carnet, recoupement puis accusation.

Modules : `scenario_life.py`, `scenario_evidence.py`, `scenario_play.py` et
`scenario_playtest.py`. `WitnessBuilder.build(..., focus_assault=1|2)` autorise
l'ajout a posteriori de témoins d'un acte réellement exécuté. Le comportement
par défaut de l'étape 7 et son RNG restent inchangés.

## Raccordement au monde 3D

`causal_game.py` adapte **PlaySession**, sans recopier les règles de découverte.
Godot solo desktop et Android utilisent maintenant cette entrée. Le serveur
WebSocket multijoueur et l'ancienne CLI restent sur `Game` ; pour les sélectionner,
utiliser `--server-url=ws://127.0.0.1:8000/ws/42/Ada` ou `--solo --legacy-engine`.
Sur desktop, le lancement normal ne nécessite plus de serveur.

La carte conserve les quatre rues du scénario, les lieux professionnels, les
vraies attaches des domiciles et des témoins. Laboratoire = commissariat ; morgue
= seconde entrée de l'hôpital, comme dans la CLI. Le coût de trajet
vaut `max(1, ceil(minutes / 6))` PA ; entrer dans un appartement nécessite d'avoir
rejoint sa rue. Le couloir ne montre que les portes ; sonner fait apparaître
l'habitant au seuil et ouvre les questions, sans réponse automatique. Un domicile
occupé ne peut pas être visité ; vide, il faut Crochetage (un slot, 1 PA) sauf
chez la victime. Six PA par tour, jamais de passage automatique : terminer rend
les PA et avance l'horloge de quinze minutes. Chaque découverte, relevé ou analyse
coûte un PA. Réouvrir une conversation connue et ses questions contextuelles ne
consomment pas de PA ; Mobile/Témoin/Alibi coûtent un PA à la première question
pour tous les suspects, même sans nouveau témoignage, puis sont gratuits. Les
trois questions d'enquête et les détails personnels repliés sont identiques pour
tous ; les derniers échanges écrits sont réservés aux appartements. Un rendez-vous
appris dans l'agenda devient questionnable auprès de tous les suspects.
Les conversations
en cours se terminent explicitement, y compris à zéro PA.

Poubelles dans les rues (après fouille, seul le sélecteur disparaît) ; ordinateurs, albums,
agenda et objets dans les logements ; personnel et témoins ont leurs propres
avatars/halos, séparés des suspects. Chaque PNJ propose ses questions avant de
répondre, même si seul un statut est disponible. Les archives des caméras sont
accessibles uniquement à la Régie vidéo : quartier puis quatre choix directs
(avant 18 h / 18–20 h / 20–22 h / 22 h–minuit), sans révéler le créneau utile.
Une consultation coûte un PA et cinq minutes, relecture gratuite. Le paquet
conserve au moins deux candidats compatibles ; si nécessaire, une autre
consultation du même créneau fournit la suite. Empreintes sur les objets déjà
examinés, uniquement avec la compétence ; comparaison/analyses au carnet. Les
couleurs des manteaux et tailles des avatars suivent les vrais signalements.
Corps voxel au sol ; gouttes de sang seulement lorsqu'elles existent dans la
vérité physique, pas pour les poisons. Attente médicale annoncée sur place et dans
les pistes en nombre de tours maximum (15 minutes par fin de tour ; trajets et
actions peuvent raccourcir ce délai). Consulter le statut n'avance pas le temps ;
aucun meuble « attendre » n'est créé. Les connaissances sont acquises **par les mêmes actions que la CLI**,
pas par export du catalogue auteur. Notes, personnes, adresses et pistes alimentent
le carnet existant, avec marquages manuels toujours purement visuels.

Sauvegarde JSON par replay, discriminant de moteur/version : `causal-solo.json`
desktop et `nexus-causal-solo.json` Android. Les anciennes sauvegardes ne sont pas
écrasées. Moteur v16 `causal-3d-v2` : nouvelle enquête après v15, ancien fichier
conservé en `.invalid-*`. `scenario_access.py` ajoute au solo 3D une routine
domicile/travail indépendante de la culpabilité, mise à jour uniquement en fin
de tour. La CLI pure reste statique à domicile et ne gère pas encore les portes.
L'aspect lounge reste générique pour les pièces, avec un couloir distinct.
Compteurs quartier/lieu : uniquement les suspects, sans personnel ni témoins annexes.

V16 finalisée : routines continues avec déjeuner, dîners/verres facultatifs et vrais
temps de marche. Activités/positions figées pendant les actions et conversations,
mises à jour uniquement à la fin du tour. La fiche identifiée donne la position
actuelle et celle d'une prochaine fin de tour immédiate (+15 minutes) ; les autres
actions peuvent changer cette prévision. Les poses/accessoires des repas sont
des décors ordinaires, pas des objets d'enquête supplémentaires.

Les fils nommés proviennent seulement des documents/lien/réponses déjà appris.
Un alibi recueilli reste « à recouper » jusqu'aux résultats nécessaires ; un fil
infirmé explique pourquoi. Les fiches montrent également les incompatibilités de
signalement d'ASSAUT. Les marquages visuels restent au choix du détective.
Le sampler exige une voie d'infirmation pour chaque crochet narratif innocent,
sans déplacer ni falsifier les acteurs : alibi compatible avec tout le déroulé,
ou critères d'agression incompatibles. Voir `PLAYTEST_V16.md` pour les résultats
et les limites, notamment la reconstitution causale encore non certifiée.

## Social : faits ≠ connaissance ≠ culpabilité

Chaque personnage possède un profil et un ou plusieurs liens réels avec la
victime, ou aucun. Fratries transitives, pas de romance au sein d'une fratrie ;
couples/ex existants conservés ; collègues au même établissement ; voisins avec
logements distincts donnant sur **la même rue/quartier**. Les triangles ordinaires
du noyau restent possibles sans implication du meurtrier.

Des amis/frères/sœurs ont parfois été présentés au partenaire de la victime
(65 % par possibilité, RNG distinct). L'événement de présentation est daté après
les deux relations, ses participants le connaissent réciproquement et peuvent
évoquer ce couple précis, sans hériter de ses messages ou conflits privés.

`scenario_evening.py` construit un petit épisode personnel pour chaque suspect,
avant tous les déplacements/présences contraints, avec le temps de trajet vérifié.
« Vos souvenirs d'hier soir » le restitue, puis les visites, sorties ou emprunts
effectivement construits. C'est un récit, jamais un filtre d'identité ni un alibi
auto-certifié. Les visites avec Alex/Camille/… ouvrent une piste vers le témoin
nommé, rencontré aujourd'hui dans un lieu public (pas enfermé chez le suspect).
La corroboration peut être recueillie immédiatement ; son effet d'exclusion attend
le rapport médical, et l'analyse du verre dans les cas d'exposition au poison.

Une relation n'accorde pas la connaissance des événements vécus par autrui.
Les messages ont un contenu borné, un expéditeur, un destinataire, une date et une
lecture explicite. Pas de pensée privée projetée, ni de transfert d'un message
non lu ou enrichi de faits inconnus. Le téléphone porté par la victime n'apparaît
pas magiquement à domicile : les archives sont une correspondance conservée sur
un terminal, et l'agenda est une manifestation privée distincte du plan partagé.

`demander Oscar Marius` consulte les liens/échanges réellement connus d'Oscar,
pas tout le réseau. Les innocents ne mentent pas. Les réponses n'ordonnent pas au
détective de vérifier tel horaire.

Les albums, liens et griefs sont du **contexte**, pas des filtres de culpabilité.
Cheveux + taille + manteau sont les critères physiques actuels, cohérents dans les
portraits et les descriptions ; aucune description projetée n'isole un suspect.
Registres de clients = visites réelles en présence du personnel de garde ; aucun
alibi complet déduit d'une entrée au bar. Fiches du commissariat = identité et
signalement, pas de culpabilité. Les témoins sont plus fréquents (un ou deux) et
disponibles jusqu'à 22 h. Les caméras contiennent aussi les vrais passages de
personnages innocents lors de leurs emprunts : sans agression visible, aucun filtre
d'identité n'est appris. Voir `REGRESSION_AUDIT.md` pour les fonctions à porter.
Des plaintes pour musique nocturne peuvent provenir de deux voisins réellement
dans le même quartier. C'est actuellement un conflit ordinaire, **pas encore une
racine de meurtre pour bruit**.

## Objets et sources physiques

- Une caméra locale par quartier, parfois hors service ; consultation **quartier
  + heure de la veille**. Les images décrivent uniquement des actes aux lieux et
  instants effectivement exécutés. Un créneau vide ne prouve pas une absence.
- Une poubelle fouillable dans chacun des quatre quartiers. Un objet caché dans
  une poubelle y a vraiment été déposé pendant la fuite. Les autres sont vides
  d'éléments utiles. Un objet caché en intérieur reste dans un placard : il n'est
  pas déplacé pour fabriquer une bonne piste vidéo.
- Un dépôt filmé mène à un objet récupérable, mais n'identifie pas automatiquement
  son auteur ni le meurtrier. Un simple départ ou ajout au verre reste contextuel.
- Des contacts typés découlent de manipulations réelles : prise/emprunt d'objet et
  tasse personnelle utilisée antérieurement. Une compétence `fingerprints` est
  nécessaire ; **deux slots**, donc elle remplace `search` ou `rapport`.
- Empreintes **partielles et fictives**, comparaison entre objets relevés ; motifs
  utilisables compatibles avec au moins deux personnes. Pas de vrai système
  biométrique. Un motif partagé n'est pas une correspondance complète et un
  contact n'est pas daté. Aucun filtre automatique de culpabilité par empreinte.
- Les objets récupérés sont transportables ; les objets domestiques demandent
  un relevé sur place. `analyse N` au laboratoire compare sang/résidus avec les
  prélèvements déjà acquis, sans confondre contact ou produit commun et meurtre.
- Une présence innocentante est une véritable visite continue corroborée par un
  autre personnage, couvrant l'estimation du moment de l'acte. Un visiteur du bar
  n'est jamais téléporté ailleurs pour fabriquer son alibi : la corroboration
  porte alors sur une observation continue de son absence de contact avec le verre.

Les estimations médico-légales et produits sont des conventions fictionnelles de
jeu, pas des modèles médicaux/forensiques. Pour le poison, l'estimation couvre
l'administration antérieure au décès, pas seulement l'heure du malaise.

## Jouer

`voir` affiche les actions numérotées, `faire N` les effectue ; `lieux` montre les
habitants et les interlocuteurs disponibles ; `aller ID` marche réellement sur le
graphe. `camera 19` consulte 19 h–20 h dans le quartier courant. `objets`,
`empreinte N`, `analyse N`, `demander NOM AUTRE_NOM`, `carnet`, `pistes` et
`recouper` complètent l'enquête. Les délais médicaux sont annoncés ; `attendre N`
avance l'horloge. `suivre`/`ecarter` sont des repères visuels seulement.

Le recoupement joueur compare uniquement les descriptions acquises aux profils
**rencontrés**. Un profil inconnu n'est jamais éliminé en consultant secrètement
sa couleur de manteau. Chaque indice et chaque paquet reçu par une seule action
reste compatible avec au moins deux suspects ; les actions distinctes peuvent
converger ensuite. L'accusation demande une identité recoupée, le rapport médical
et le dernier projet de la victime. Elle ne certifie pas encore un mobile complet.

Les deux autres compétences ont un effet : `search` réduit le temps de fouille,
`rapport` celui des conversations. Aucune compétence n'est obligatoire pour finir.

## Tests empiriques et limites

Deux parties manuelles terminées sans consulter la vérité : agression contondante
reconstituée par rendez-vous, caméra puis corroboration ; empoisonnement exploré
par verre, flacon, empreinte, voisinage, rivalité sentimentale et corroborations.
La seconde expose encore la faiblesse des résolutions par accumulation d'alibis.

Sur 100 graines demandées, l'exploration automatisée aveugle a terminé 100 affaires.
Elle lit seulement les actions disponibles et les faits acquis, respecte les
trajets/délais/fenêtres, et n'utilise ni coupable, ni supports privés, ni solution
du solver. **Ce n'est pas une mesure de plaisir**, ni une stratégie humaine optimale.

L'ablation d'identité sur ces 100 cas retenus donne :

| Famille | Indispensable | Suffisante seule |
| --- | ---: | ---: |
| Témoignages directs | 29 | 32 |
| Caméras | 16 | 0 |
| Corroborations de présence | 36 | 42 |

La première passe nécessitait les corroborations dans 99 cas sur 100 ; la politique
de sélection diversifie désormais témoignages croisés, témoin/caméra et exploration
ouverte. Le rejet **biaise volontairement** les résultats : 61 armes blanches,
29 objets contondants, 10 poisons dans cet échantillon, pas une distribution promise.

Validation finale : **1 664 tests ciblés passent**, dont **348 dédiés** à cette
nouvelle couche (100 mondes sociaux/physiques, paquets d'indices, connaissances,
caméras/créneaux, dépôts, compétences, empreintes, analyses, profils inconnus,
routes d'accès et parties aveugles). Compilation et `git diff --check` passent.
La relance finale des 100 parties termine les 100 affaires en 1 742 actions
acquises au total ; ces chiffres restent ceux d'un explorateur exhaustif.

Limites : six racines causales seulement ; identité/méthode/dernier projet, pas
certificat de reconstruction complète du mobile ; poison moins diversifié ;
peu d'attributs de signalement ; empreintes encore des pistes de contact. La CLI
est en mémoire, sans sauvegarde, PA multijoueur ni animation. Les intérieurs sont
accessibles pour ce banc d'essai, pas un système d'autorisation policière final.
Les PNJ du nouveau générateur sont intégrés au **solo 3D**, pas à l'ancien `Game`
multijoueur. La CLI reste en mémoire ; le solo 3D dispose de PA et de sauvegardes
propres. Les bases et anciennes sauvegardes ne sont pas converties.

Suite utile : chaîne causale du verre et points de contrôle indépendants pour le
poison, méthodes plus variées, racine bruit/voisinage, reconstitution explicite du
mobile, puis routines sociales et enrichissement des manifestations dans le 3D.
