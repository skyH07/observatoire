# Observatoire du traitement de l'information

Un registre de faits attestés par des sources hors presse, auquel se rattache la
couverture médiatique, afin de rendre mesurables les choix de sélection et de
cadrage — y compris les silences.

Le dépôt fait foi. Le site n'en est qu'un rendu, reconstruit à chaque
modification.

## Démarrer

```bash
python3 scripts/valider.py      # vérifie le contrat de données
python3 scripts/construire.py   # écrit le site dans site/
python3 -m http.server -d site  # consulte sur http://localhost:8000
```

Python 3.11 ou plus récent. Aucune dépendance à installer.

## Organisation

```
schema/vocabulaire.toml    le vocabulaire contrôlé, versionné comme donnée
donnees/medias.toml        le périmètre de suivi, déclaré avant collecte
donnees/evenements/*.toml  un fichier par fait : le fait, ses sources, sa couverture
preenregistrements/        les hypothèses déposées avant analyse
scripts/valider.py         le contrat, exécuté à chaque proposition
scripts/construire.py      la génération du site et des exports
scripts/ingerer.py         la collecte : relevés de titres, propositions
METHODE.md                 le manuel de codage et les limites assumées
CONTRIBUER.md              les règles de relecture
```

## Six décisions à ne pas défaire

Ce sont les choix qui font tenir le projet dans la durée. Chacun coûte un peu de
confort immédiat et évite une impasse à trois ans.

**Un fichier par événement, en texte lisible.** Tout ce qui concerne un fait
tient dans un seul fichier : le fait, ses sources, ses articles, leurs relevés,
leur codage. Une proposition de modification se relit d'un coup d'œil. Une base
binaire ne se relit pas, ne se compare pas, et rend la relecture collective
impossible.

**Aucune dépendance externe.** Le validateur et le générateur n'utilisent que la
bibliothèque standard. Un projet documentaire doit pouvoir être relancé dans dix
ans sans archéologie de paquets.

**Le texte intégral n'est jamais recopié.** Titres relevés, métadonnées,
variables calculées, liens d'archive. Rien d'autre. Aucune mesure du projet n'a
besoin du corps des articles, et sa reproduction ne serait pas licite. Le
validateur rejette toute donnée qui en contiendrait.

**Le périmètre des médias est déclaré avant collecte.** Un média ne peut être
compté comme silencieux que s'il était déjà suivi à la date du fait. Sans cette
règle, on peut fabriquer n'importe quel taux d'omission après coup.

**Une source primaire hors presse est obligatoire.** Un événement connu par la
seule presse ne permet pas de mesurer une omission : on ne connaîtrait que les
faits déjà couverts. C'est la contrainte la plus coûteuse à respecter et la
seule qui rend l'exercice valide.

**L'écriture est additive.** Une correction crée une version, elle n'en écrase
pas une. La seule écriture automatique autorisée est le relevé d'un titre qui a
changé : constater est mécanisable, rattacher et coder ne le sont pas.

## Limites assumées

Ce projet mesure des choix éditoriaux observables dans les textes publiés. Il ne
mesure pas l'intention d'une rédaction, ni la vérité d'un fait, ni l'origine des
personnes impliquées — variable absente des sources utilisables et que nous ne
cherchons pas à reconstituer. La question posée est donc « quels médias
mentionnent quoi, dans quels cas », et non « telle catégorie est-elle plus
couverte ». Voir `METHODE.md`.

Un écart de couverture entre deux événements non appariés sur la gravité, le
nombre de victimes, le lieu et le moment ne veut rien dire. Le site affiche
systématiquement les effectifs et refuse de présenter un taux comme un résultat
en dessous de vingt événements.

## État

Le jeu de données livré est une démonstration : faits, médias et titres sont
fictifs. Ils servent à montrer la structure, pas à décrire la presse réelle.

## Avant la mise en ligne

- Vérifier la base légale du traitement. Une base reliant des personnes à des
  infractions relève de l'article 10 du RGPD ; le corpus est conçu pour rester
  anonyme et agrégé, il faut s'assurer qu'il le reste.
- Confirmer les conditions d'accès aux flux et aux dépêches utilisés.
- Héberger les polices localement plutôt que de les charger depuis un tiers.
- Déposer les versions majeures sur une archive délivrant un identifiant pérenne,
  pour disposer d'une copie que le projet lui-même ne peut plus modifier.
