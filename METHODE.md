Méthode

Ce document est le contrat intellectuel du projet. Il se modifie par proposition de modification, jamais en silence, et toute version antérieure reste consultable dans l'historique du dépôt.

Ce que ce projet mesure

Des choix éditoriaux observables dans un corpus de textes publiés : quels faits sont repris, par qui, en combien de temps, sur quelle longueur, avec quel cadrage déclaré, et avec quelles révisions après publication.

Ce que ce projet ne mesure pas

Il ne mesure pas l'intention d'une rédaction. Il ne mesure pas la vérité d'un fait. Il ne mesure pas l'origine réelle des personnes impliquées, qui n'est disponible dans aucune source utilisable et que nous ne cherchons pas à reconstituer.

La conséquence est directe et volontaire : nous ne posons pas la question « telle catégorie de personnes est-elle plus couverte ». Nous posons la question « quels médias mentionnent l'origine, la nationalité, la religion, le milieu social ou l'état de santé, dans quels cas ». La première n'est pas mesurable sans inférer la variable explicative à partir de l'objet mesuré. La seconde se lit directement dans le texte publié.

Constitution du corpus
Un événement n'entre au corpus que s'il est attesté par une source primaire qui n'est pas un article de presse : dépêche d'agence, audience, décision de justice, communiqué officiel, publication statistique.
La dépêche de référence définit la fenêtre de couverture possible. Sans elle, une absence de reprise n'est pas interprétable.
Le périmètre des médias suivis est déclaré dans donnees/medias.toml avant collecte. Un média ajouté ne compte que pour les événements postérieurs à sa date d'entrée.
Les articles sont rattachés à l'événement, jamais l'inverse.
Périmètre territorial des médias

Un média national est réputé pouvoir couvrir tout événement du corpus. Un média local ou régional déclare dans le registre la liste des départements qu'il couvre, dans le champ departements.

Un média territorial n'est compté comme éligible — donc susceptible d'être silencieux — que pour les événements survenus dans ses départements déclarés. Compter un titre régional comme « n'ayant pas couvert » un fait hors de sa zone ne mesurerait pas une omission, mais une évidence de diffusion.

S'il couvre malgré tout un événement hors de son territoire, l'article est enregistré et affiché, mais n'entre pas dans le taux de reprise : la mesure reste à périmètre constant.

Le territoire déclaré se modifie par proposition et ne vaut que pour l'avenir, comme la date d'entrée au suivi. Les flux complémentaires (flux_complementaires) ne sont que de la tuyauterie de détection : l'unité de mesure reste le média, jamais le flux.

Appariement

Comparer des volumes de couverture bruts ne produit rien d'interprétable : la reprise dépend d'abord de la gravité, du nombre de victimes, du lieu, de l'existence d'images, et de la concurrence de l'actualité ce jour-là.

Toute comparaison entre événements doit donc être appariée sur les variables enregistrées dans la fiche du fait : type, nombre de victimes, milieu, implication d'un mineur. Un écart observé entre deux événements non appariés n'est pas publié comme un résultat.

Codage

Chaque article est codé indépendamment par deux personnes au minimum. Les codes sont enregistrés dans le fichier de l'événement, avec la liste des codeurs et un indicateur d'accord.

En cas de désaccord, la valeur est tranchée par application de la règle écrite, et le désaccord reste consigné dans note_desaccord. Il n'est jamais effacé : un taux de désaccord élevé sur une variable est une information sur la variable, pas un défaut à masquer.

Règles de codage
On code ce qui est écrit, pas ce qui est suggéré.
mentionne_origine : vrai si l'article indique une origine géographique ou ethnique d'une personne impliquée, y compris par périphrase explicite.
mentionne_nationalite : vrai si une nationalité est indiquée. Distinct du point 2 et codé séparément.
mentionne_sante_mentale : vrai si l'article évoque un trouble, un suivi psychiatrique ou une hospitalisation. Une mention de « suivi médical » sans précision est codée vrai, avec désaccord consigné si les codeurs divergent.
mentionne_milieu_social : vrai si l'article évoque la situation socio-économique, le logement, l'emploi ou la prise en charge sociale.
centre_sur_victime : vrai si la victime est nommée, décrite ou citée avant la personne mise en cause.
cadre : le cadre dominant, un seul, déterminé par le titre et le premier paragraphe. En cas d'ambiguïté réelle, le cadre le moins interprétatif l'emporte.
Fiabilité

Un accord inter-codeurs est calculé par variable dès que le corpus atteint cinquante articles codés. En dessous d'un accord de 0,7, la variable est suspendue : elle reste collectée mais n'est plus publiée tant que la règle n'a pas été reformulée.

Pré-enregistrement

Toute hypothèse est déposée dans preenregistrements/ avant l'analyse, avec sa date, les variables concernées, la stratégie d'appariement et le critère qui la ferait rejeter. Une analyse conduite hors pré-enregistrement est publiable, mais étiquetée comme exploratoire et ne peut pas être présentée comme un résultat.

Les hypothèses rejetées sont publiées avec la même visibilité que les autres.

Révisions de titre

Les titres sont relevés à chaque passage de collecte. Un titre modifié n'écrase pas le précédent : il s'ajoute. C'est la mesure la plus objective du corpus, puisqu'elle ne demande aucun codage.

Ce qui n'est pas conservé

Le texte intégral des articles n'est pas recopié. Sont conservés les titres relevés, l'adresse d'origine, l'adresse d'archive, les métadonnées et les variables calculées. Le validateur rejette toute donnée contenant un corps d'article.

Aucune personne physique impliquée dans un fait n'est nommée dans le corpus. Les résumés sont factuels et anonymes. Les analyses sont publiées de façon agrégée, par média, jamais par affaire individuelle mise en accusation.

Correction

Une erreur signalée donne lieu à un nouvel enregistrement, jamais à une réécriture. La page corrigée porte la mention de la correction et la date.

Le projet reproche aux rédactions leurs modifications silencieuses. Il perd toute autorité le jour où il s'en autorise une.