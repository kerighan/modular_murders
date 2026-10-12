# Migration du solo causal — inventaire fonctionnel (v16)

V18 : sept suspects, corroborations par le vrai barman/serveur (plus de tiers
nommés), au moins deux alibis publics accessibles ; silhouettes citées avec
positions actuelles/prochaines. Période médicale rappelable gratuitement,
frise des horaires acquis, glow de vérification et piste du verre prélevé.
La table v16 ci-dessous demeure historique ; détails actuels : `PLAYTEST_V18.md`.

Le solo causal remplace le générateur, pas l'intention de jeu. L'ancien moteur
reste accessible avec `--legacy-engine`.

v17 : statuts explicites Personnel/Témoin et onglet Contacts séparé. Nom cité =
fiche en silhouette sans signalement ; annotations isolées par instance d'enquête,
pas seulement seed. Pas de nouveau témoin généré, sauvegardes v16 conservées.

| Fonction ancienne | Solo causal v16 |
| --- | --- |
| Conversations lien / mobile / témoin / alibi | Trois questions d'enquête, détails personnels repliés, rendez-vous questionnable après agenda |
| Alibis et vérification auprès d'un tiers | Récits sourcés, tiers nommés dans des lieux publics, pistes ; exclusion après comparaison temporelle |
| Fils et élimination lisible | Fils nommés ouverts / à recouper / infirmés ; motifs d'incompatibilité dans les fiches, marquages manuels conservés |
| Où trouver un personnage | Fiche identifiée : position actuelle et prochain tour ; travail, déjeuner, dîner/verre, trajets réels |
| Serveur/barman même sans indice de stock | Présents pendant la journée d'enquête ; registre sourcé sur de vraies visites |
| Commissaire et casiers/fiches | Accueil physique, fiches repliées avec identité, signalement, domicile et métier ; pas de condamnation inventée |
| Critères physiques « qui est-ce » | Cheveux + taille + manteau, cohérence portraits/avatars, >=2 candidats par description projetée |
| Caméras | Régie, quatre fenêtres ; passages innocents réels, une présence n'est pas une agression |
| Appartement/sonnerie/effraction | Couloir et seuil ; pas d'entrée si occupé, Crochetage pour les logements vides |
| Groupes sanguins / dossier hospitalier individuel | Pas encore portés comme critères d'identité ; prélèvements du crime et analyses existent |
| Yeux, sexe et latéralité comme critères | Pas encore portés au nouveau graphe |
| Taxi, hacking, contacts police/hôpital, faveurs et autorisations | Pas encore portés |
| Échanges spontanés entre suspects | Ancien moteur seulement ; nouveau : routines de jour et conversations individuelles |
| Serveur multi / Loom | Ancien moteur conservé ; nouveau solo hors ligne sans base |

Références : `tests/test_causal_game.py`, `tests/test_scenario_play.py`,
`tests/test_scenario_witnesses.py`, captures tactiles `causal_access_smoke.gd` et
`causal_services_smoke.gd`. Le playtester explore des sources publiques ; sa
réussite ne mesure pas le fun.
