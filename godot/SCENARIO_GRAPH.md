# Contrat du générateur d'enquête · v9

## Objets facultatifs, aucun intermédiaire imposé

Le bracelet matérialise un vol pour payer une dette ; la clé USB contient une
copie d'un dossier compromettant. La vengeance n'ajoute plus une montre volée
sans raison : aucun objet disparu dans cette famille. Dans les deux autres,
le responsable emporte / détruit l'objet hors d'atteinte, ou le cache dans un lieu
public. Pas de reçu au nom d'un innocent, de dépositaire ou de remise automatique.

`object_fate` / `cache_place` restent privés. Une découverte de cache ne donne
aucun nom ni trace attribuable : support = population entière. Le détective
ne connaît pas la cache avant de l'avoir fouillée ou d'obtenir la confession.
Si elle est trouvée en premier, l'objet et son propriétaire ne sont pas liés
automatiquement : marquage à comparer avec les papiers du domicile de la victime.
Retrouver l'objet n'est jamais requis pour la confrontation finale. Le carnet
distingue disparition, récupération, non-récupérable après conclusion, et absence
de disparition signalée ; pas d'omniscience de la piste avant découverte.

L'axe d'occasion vient d'un registre de clés partagées pour le coffre où était
rangé l'objet, ou des destinataires d'un rendez-vous pour la vengeance. Avoir
une clé / recevoir une invitation n'implique pas une connaissance personnelle
de la victime. Les trois sources finales sont **occasion + mobile + silhouette**,
avec le constat horaire nécessaire. Pas de récupération ni de relais obligatoire.
Cette version reste un premier modèle : les affaires avec objet utilisent encore
un coffre partagé, pas une bibliothèque complète de circonstances de vol.

La v8 décrite historiquement dans les autres documents employait une chaîne
d'intermédiaire / reçu / transfert, supprimée en v9. Les principes mathématiques
ci-dessous restent inchangés.

Un indice incriminant est une observation compatible avec un ensemble de
personnes **sur la base de cette observation seule**. Pour chaque indice `i`,
son support `S_i` contient au moins deux personnes, jamais forcément deux
exactement. Après plusieurs indices, les candidats sont l'intersection des
supports. Cette intersection peut naturellement finir par ne contenir qu'une
personne : c'est la déduction, pas un indice singleton.

Les informations d'identité et d'orientation (« ce reçu est chez Marius »)
peuvent nommer une personne. Elles ne certifient ni sa présence au meurtre ni
sa culpabilité. Un conflit réel concernant des innocents est une piste à
vérifier, pas une propriété nécessaire du meurtrier.

## Trois axes narratifs indépendants

`scenario_graph.py` sépare observations immuables, supports, chemins de
recoupement et connaissance privée du détective. `narrative.py` construit un
petit monde causal, puis ses documents et témoignages :

- mobile / pression réellement partagée ;
- occasion : accès partagé ou connaissance du rendez-vous ;
- silhouette pendant la fenêtre du crime, accessoire partagé, visage masqué.

Un noyau de quatre personnes `{K, A, B, C}` donne les supports
`{K,A,B}`, `{K,A,C}`, `{K,B,C}`. Chaque paire laisse encore deux candidats ;
les trois axes convergent vers `K`. Les autres habitants peuvent appartenir
à zéro, un ou deux groupes, jamais aux trois. Les tailles varient donc au-delà
de trois. Aucun témoin n'affirme que tous les porteurs d'un accessoire étaient
sur place : la vidéo est **compatible** avec eux, elle ne les identifie pas.
À trois habitants, la profondeur minimale est deux : l'exigence des paires
encore ambiguës sur trois axes n'est pas mathématiquement possible.

L'objet manquant et sa récupération éventuelle n'identifient personne : ils ne
comptent pas comme de nouvelles preuves indépendantes. Le constat horaire
situe le crime, sans identifier quelqu'un. Un alibi original vérifié peut
écarter un innocent, mais un conflit ou une attestation non vérifiée ne le fait
pas. La confession conclut une reconstitution déjà croisée ; elle n'est jamais
une source isolante disponible au départ.

## Indices physiques et raccourcis évités

`Case` refuse les traits révélés propres à une seule personne, et retire les
populations dont les traits partagés ne peuvent pas converger. La sélection
reste une combinaison minimale (la plus longue disponible). Les armes,
téléphones, enregistrements et témoignages portent parfois plusieurs traits :
leur **combinaison par objet / source** doit elle aussi garder au moins deux
candidats. Tous les traits retenus restent accessibles par une source physique.
Les papiers de relation ne sont pas déposés uniquement au domicile du coupable.

Pas de mensonge factuel généré chez un innocent. Pas non plus de « seul
menteur forcément coupable », raccourci incompatible avec ce contrat.
L'ancien mécanisme de confrontation d'une déclaration importée reste lisible,
mais les nouvelles affaires génèrent des réponses vraies ou partielles.
Quelqu'un qui ne connaissait pas la victime ne peut pas donner de renseignements
sur ses conflits, même si les questions sont posées dans un autre ordre.

Les témoignages dirigent rarement vers un problème partagé, jamais vers un
nom arbitraire. Une piste vague sur le travail n'existe que si un vrai différend
concerne au moins deux vrais collègues et un lieu présent dans le graphe.
Les autres papiers personnels ne lancent pas de fausses flèches gratuites.

## Trajectoires facultatives

`view.leads` donne au carnet Pistes : raison connue, prochaine vérification,
lieux accessibles et état « source recueillie ». Aucun dévoilement de fait
non découvert, déplacement automatique, coût caché ou classement automatique
des suspects. Le détective peut suivre ces pistes ou fouiller ailleurs.
Les notes et les listes de pistes restent privées par détective.

## Validation et limites

`tests/test_scenario_graph.py` audite 1 000 générations : cardinalités,
intersections par paire, convergence finale, artefacts multi-traits, vérité
des liens, connaissances des inconnus, collègues, lieux et graphe connecté.
Les petites populations sont testées séparément. La scène varie entre trois
parcelles extérieures ; le graphe et la grille visible sont reconstruits ensemble.

`godot/tests/playtest_cli.py` pilote réellement `cli.py` en terminal,
QTE parfaits, sauvegarde Loom isolée. Il choisit ses destinations à partir du
carnet public, calcule le candidat depuis les trois groupes lus dans les notes,
puis vérifie la reprise après fermeture du processus. Trois parcours v9 :
42 objet caché non récupéré, 7 objet hors d'atteinte, 4 aucun objet disparu.
Il ne consulte ni
l'identité secrète du meurtrier ni les supports privés du générateur.

Ce premier générateur reste une famille de petits motifs causaux, pas encore
une bibliothèque narrative extensive. Les traits physiques peuvent fournir
une autre combinaison convergente que la trame en trois axes. Les professions
utilisent les lieux existants : pas encore de campus distinct. Le modèle est
deterministe et offline, sans texte LLM requis. `RULES_VERSION=9` interdit de
rejouer une génération v8 avec ces règles : Loom refuse sans modifier le record,
Android préserve le fichier ancien en `.invalid-*` puis revient à la préparation.
Le format de sauvegarde et la version du générateur sont distincts.
