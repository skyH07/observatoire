# Contribuer

## Le principe qui prime sur tous les autres

Aucune écriture directe sur la branche `principale`. Tout passe par une
proposition de modification, relue et consignée. Un projet qui reproche aux
rédactions leurs corrections silencieuses ne peut pas s'en autoriser une seule.

## Trois niveaux de relecture

| Type de modification | Relecteurs requis |
|---|---|
| Correction de forme, lien mort, faute | 1 |
| Ajout d'un événement, d'un article, d'un relevé | 1 |
| Codage d'un article | 2 codeurs distincts, déclarés dans le fichier |
| Modification du manuel de méthode ou du vocabulaire | 2, dont un n'ayant pas rédigé la proposition |
| Ajout ou retrait d'un média du périmètre | 2, et la modification ne vaut que pour l'avenir |

Le codage à deux personnes n'est pas une formalité : c'est ce qui distingue une
mesure d'une opinion. Le validateur refuse tout article codé par une seule.

## Ajouter un événement

1. Vérifier qu'une source primaire hors presse existe. Sans elle, l'événement
   n'entre pas : une absence de couverture ne serait pas interprétable.
2. Créer `donnees/evenements/EVT-AAAA-NNNN.toml` en partant d'un fichier
   existant.
3. Rédiger un résumé factuel, sans qualificatif, sans nom de personne, sous
   300 caractères.
4. Lancer `python3 scripts/valider.py`.

## Ajouter un article

Un article se rattache à un événement existant, dans le fichier de cet
événement. Il faut systématiquement une copie archivée : sans elle, la mesure
n'est pas reproductible et la proposition est refusée.

## Corriger

On ne réécrit pas un enregistrement erroné. On ajoute la correction, on la
motive, et on laisse l'historique visible. Pour un titre mal relevé, ajouter un
relevé ; pour un codage contesté, ouvrir une discussion avant de proposer.

## Composition de l'équipe de codage

L'équipe de codage doit rester diverse politiquement, et cette diversité doit
être vérifiable dans la durée. Un désaccord de codage se tranche par la règle
écrite, jamais par vote. Si la règle ne tranche pas, c'est la règle qu'il faut
reformuler, dans une proposition séparée, avant de coder l'article.

## Ce qui est refusé sans discussion

- Le texte intégral d'un article, sous quelque forme que ce soit.
- Le nom d'une personne physique impliquée dans un fait.
- Un codage sans second codeur.
- Un article sans copie archivée.
- Une analyse publiée sans pré-enregistrement, présentée comme un résultat.
