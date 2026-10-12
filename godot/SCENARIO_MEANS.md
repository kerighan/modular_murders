# Provenance des moyens — exécution V3

V4 conserve ces mécanismes et ajoute les [triangles, rendez-vous et empoisonnements fictifs](SCENARIO_SITUATIONS.md).
Les nombres de stocks et de méthodes ci-dessous décrivent V3 ; V4 ajoute des
flacons fictifs préexistants, des présences au bar/resto et un aperçu du verre.
Noyau actuel V3, exécution V4, sources du jeu règles 13 ; APK toujours v11.

[scenario_means.py](../scenario_means.py) porte les objets, accès, mouvements,
états et constats d'inventaire. [scenario_crime.py](../scenario_crime.py) fournit
les trajets physiques et les valide. Le nouveau générateur reste indépendant
du moteur d'enquête actuel : ces constats ne sont pas encore des actions du jeu.

## Du monde vers l'indice

1. Créer les objets avant le crime : usage ordinaire, propriétaire, stock
   d'origine, point de prise, disponibilité et personnes ayant accès.
2. Calculer les prises réalisables sans modifier le plan de la victime.
3. Tirer objectif → raison → plan → méthode → mode d'acquisition → variante.
4. Exécuter la prise et le déplacement de l'objet ; conserver son propriétaire.
5. Dériver son état final et le stock manquant, pas tirer une absence au hasard.
6. Projeter un constat limité, seulement au lieu concerné après l'inventaire.

| Acquisition | Contrainte physique |
|---|---|
| `owned` | Objet préexistant au domicile de l'auteur, apporté avant sa sortie. |
| `taken` | Détour réel par le bar/restaurant avant de rejoindre la sortie du travail. |
| `borrowed` | Même détour, avec accord d'un prêteur réellement présent. |
| `opportunistic` | Objet accessible sur le trajet effectivement suivi, pris après avoir aperçu la victime et avant l'attaque. |

Le restaurant **Le Comptoir** et le bar disposent chacun de trois couteaux et
de deux marteaux, à usage normal de service/entretien. Certains sont au comptoir,
d'autres au point extérieur de service/entretien sur leur rue. Cela ne donne pas
magiquement accès à une cuisine privée. Dans ce premier patron les six personnes
ont accès aux objets de ces espaces communs ; ce sont des possibilités d'accès,
pas des visites constatées. Des accès différenciés pourront remplacer ce domaine.

Une acquisition opportuniste n'est pas encore un meurtre impulsif : l'intention
de tuer préexiste dans les cinq noyaux pris en charge, seul le moyen est opportun.

## Devenir et vie ordinaire

Trois devenirs : conservé par l'auteur, laissé sur la scène, ou caché sur un nœud
réel de sa fuite. Un objet caché n'est **pas** automatiquement découvert ; aucune
trace ne lui attribue publiquement un déposant. L'identité exacte reste privée.

Un innocent peut également emprunter un autre objet pour un usage domestique,
avec un vrai aller-retour à midi et l'accord du personnel. Événement optionnel
(35 % si faisable), jamais un intermédiaire permanent. Il finit chez cet innocent,
avant toute visite du soir. Aucun mensonge n'est nécessaire. La raison domestique
reste générique à ce stade ; repas/travaux détaillés restent à développer.

`ToolTransfer` conserve les mouvements datés. `ToolState` distingue propriétaire,
porteur, emplacement, rangement d'origine et dissimulation. Un objet déposé sur
la même rue n'est pas, pour autant, retourné au rangement du restaurant.
Les constats comptent uniquement les sorties du stock, y compris les prêts.
Le prototype ne simule pas encore de retours de prêts ou de service continu.

## Vue publique limitée

`inventory_observations(crime, place=..., discovered_at=...)` ne renvoie rien
avant l'inventaire du lendemain à 08 h, ni pour un autre lieu. Exemple :

> À l'inventaire, il manque 1 couteau. Je n'ai pas de prêt noté pour ça.

Un prêt autorisé donne plutôt « On en a prêté un. » Un manque inexpliqué
supplémentaire est distingué. Le constat ne révèle ni emprunteur, ni objet exact,
ni transfert, ni usage criminel. Il est marqué `lead_not_proof`. Le même type de
constat peut provenir d'un prêt innocent sans arme du crime issue du lieu.

L'artefact complet (compte + contexte de prêt) conserve **au moins deux suspects
compatibles** : accès possibles au stock, victime exclue. Pas deux cibles par
phrase artificiellement séparée. Le prototype n'identifie aucun bénéficiaire
de prêt dans cette projection ; une future réplique nominative devra elle aussi
passer le contrôle d'ambiguïté de son artefact complet.

Ce contrôle local n'est **pas** un solver global : aucune convergence d'enquête
complète n'est encore garantie. Pas de CCTV, empreintes, témoins du crime ou
projection du rendez-vous manqué. L'étape suivante est de matérialiser les
observations sur les vrais trajets, puis vérifier ambiguïté et convergence.

## Essayer

```bash
# Vérité privée : couteau pris au restaurant avant la rencontre.
python scenario_sampler.py --step 5 --seed 7 --acquisition taken --weapon-origin restaurant --method edged --no-mundane

# Même génération, uniquement le constat expurgé, en JSON.
python scenario_sampler.py --step 5 --seed 7 --acquisition taken --weapon-origin restaurant --method edged --no-mundane --public-inventory

# Moyen opportuniste : restaurant réellement sur le trajet suivi.
python scenario_sampler.py --step 5 --seed 0 --acquisition opportunistic --weapon-origin restaurant --no-mundane

python scenario_sampler.py --step 5 --catalogue
python -m pytest -q tests/test_scenario_means.py tests/test_scenario_crime.py
```

Imposer une provenance incompatible échoue : pas de relance cachée du monde,
pas de déplacement du restaurant pour faire réussir la requête. `--no-mundane`
supprime seulement les emprunts ordinaires, pas les modes d'acquisition criminels.
JSON privé `crime_version=3`, noyau `kernel_version=2` : le restaurant et ses
métiers ont changé les domaines seedés. Même graine ancienne ≠ ancien scénario.

## Jeu et rendu existants

Le Comptoir est aussi ajouté au jeu actuel : quartier connecté, fréquentation
ordinaire, départ possible, serveur distinct des suspects, bâtiment bas à accent
ambre et enseigne. Il réutilise le lounge global, pas une modale ni un nouvel
intérieur spécialisé. **Seul ce lieu est intégré au jeu**, pas le sampler V3.

Sources du jeu `RULES_VERSION=12` : les anciennes parties ne sont pas rejouées
contre une carte/routine modifiée. Aucun fichier utilisateur supprimé pendant
le développement ; validations de reprise en bases Loom temporaires isolées.
L'APK v11 existant n'a pas été reconstruit.

`tests/restaurant_smoke.gd` vérifie la préparation solo réelle, le bâtiment,
l'intérieur dans le même monde 3D et le tap tactile sur le serveur. Captures
`art/captures/restaurant-*-phone-v12-{18x9,20x9}.png` ; rendu natif desktop en
1080×540 et 1200×540, pas une mesure de performance sur téléphone physique.

Validation de cette passe : 1 608 tests Python réussis, dont 146 sur les moyens ;
1 000 générations physiques, fixtures exhaustives sur les cinq noyaux et les
quatre modes d'acquisition. Partie CLI existante terminée et reprise exacte en
Loom, sans remplacer son ancien générateur par le prototype.
