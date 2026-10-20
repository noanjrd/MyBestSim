# MyBestSim : Rapport statistique du catalogue eSIM

## Objectif
Lire tous les CSV de `donnees-test-mybestsim/` (un fichier par fournisseur) et générer
un rapport visuel HTML : `rapport/index.html` (avec son CSS séparé). Langue de l'interface : français.

## Commandes
- Générer le rapport : `python generer_rapport.py` (sortie : `rapport/index.html`)
- Le script n'a aucun argument : les CSV sont toujours lus dans `donnees-test-mybestsim/`
  et le rapport est toujours écrit dans `rapport/`. Il doit fonctionner si de nouveaux CSV y sont
  ajoutés (glob `*.csv`, jamais de liste en dur).

## Stack
- Python 3 + bibliothèque standard (csv, statistics, json) ; pas de pandas sauf nécessité.
- Rapport = `rapport/index.html` + `rapport/style.css` + `rapport/script.js`. Le CSS et le JS
  ne sont JAMAIS inline : leurs sources vivent dans `templates/` (`style.css`, `script.js`)
  et sont copiées à côté de `index.html` à chaque génération (ne pas éditer les copies).
- Pas de diagrammes/graphiques dans le rapport (demande de l'utilisateur) : KPI + tableaux seulement.
  Seule exception réseau : la police Poppins (Google Fonts), facultative : sans connexion la page
  reste lisible avec une police de secours. Doit s'ouvrir par double-clic.
- Le HTML généré est indenté (4 espaces par niveau, une balise de bloc par ligne).

## Publication
- Le site est publié sur GitHub Pages (https://noanjrd.github.io/MyBestSim/) par le workflow
  `.github/workflows/pages.yml` (à la racine du dépôt), qui lance `dashboard/generer_rapport.py` à chaque push
  sur `main`. Le tableau de bord est publié à la racine du site et l'article de blog (dossier `article/`, à la
  racine du dépôt) dans `/article/` (https://noanjrd.github.io/MyBestSim/article/).
- `rapport/` est dans `.gitignore` (généré). Les CSV de `donnees-test-mybestsim/` doivent rester versionnés.

## Données (schéma CSV)
Colonnes utilisées : `sku, provider, product_name, country_name, data_gb, validity_days,
price, currency`. Les autres colonnes des CSV (`country_code`, `data_display`, `network`,
`top_up`) sont ignorées : ne pas les relire ni les calculer tant qu'elles ne sont pas affichées.
- Lire en `utf-8-sig`. Séparateur `,`. Prix avec point décimal. Devise : EUR.
- `data_gb` vide = forfait illimité. Ne JAMAIS le compter comme 0 Go : l'exclure de la moyenne
  de data et l'afficher à part (nombre / %).
- `validity_days` : 7/15/30.
- Fournisseur = colonne `provider` (pas le nom de fichier).
- Valider à la lecture : colonnes attendues, prix numérique > 0, SKU unique, devise unique.
  Signaler (sans planter) les lignes invalides dans une section « Qualité des données ».

## Statistiques à produire
Requises :
1. Nombre total de cartes eSIM (produits).
2. Nombre de produits à plus de 100 € (strictement > 100).
3. Fourchette de prix globale (min / max, avec le produit concerné).
4. Moyenne de data (Go) par carte (hors illimités), et préciser le nombre de cartes prises en compte.
5. Prix moyen global.
6. Répartition par fournisseur (carte « Répartition par fournisseur » : graphique en barres du nombre de cartes, plus la colonne « Cartes » du tableau détaillé).

Complémentaires (pertinentes) :
- Prix médian ; prix moyen et médian par fournisseur ; fournisseur le moins/plus cher.
- Prix moyen par Go (hors illimités) : meilleur rapport qualité/prix, par fournisseur.
- Part d'illimités, par fournisseur.
- Top 10 produits les moins chers et les plus chers (tableaux), filtrables par fournisseur et/ou
  par pays, par volume de data (1/3/5/10/20/50 Go ou Illimité) et/ou par durée du forfait (7/15/30 jours)
  via quatre listes déroulantes
  combinables (« Tous » par défaut + bouton Réinitialiser). Les illimités ont `data = null`. Le filtrage se
  fait dans le navigateur (`script.js`) à partir de `rapport/donnees.js`, généré avec tous les produits.
- Rien n'est calculé s'il n'est pas affiché : pas de code, de donnée ni de fonctionnalité inutilisé.

## Conventions de présentation
- Prix : format français « 12,34 € ». Nombres : séparateur espace/virgule FR.
- Chaque chiffre clé = une carte KPI en haut ; détails en dessous (tableaux triables).
- Le CSS reprend le design de la page https://mybestsim.com/en/comparison-best-esim-card-france/ :
  fond blanc (pas de mode sombre), police Poppins, texte bleu nuit #0f172a, cartes à fine bordure
  #e5e7eb (rayon 16px) avec bandeau gris #f8fafc, encadré gris à liseré rouge #e2001a, étiquettes de
  tableau en majuscules, pastille verte, accents bleu #007bff. Responsive : aucun débordement horizontal.
- Le logo MyBestSim est dans `assets/logo.webp` (déposé par l'utilisateur) ; `assets/` est copié dans
  `rapport/assets/` à chaque génération et affiché en tête de page s'il existe.
- Le code HTML (et CSS) doit être beau et espacé : indentation cohérente, une balise par ligne
  pour les blocs, lignes vides entre sections ; interface aérée (marges, paddings et
  espacements généreux). Le HTML généré doit rester lisible si on ouvre le fichier source.
- Toujours indiquer le périmètre (nb de lignes) derrière une moyenne.

## Règles de travail
- Ne jamais modifier les CSV source ; le dossier est en lecture seule.
- Tout calcul vit dans un module (`stats.py`), séparé du rendu HTML.
- Pas de tests automatisés dans le projet (supprimés à la demande de l'utilisateur).
- Après changement, régénérer le rapport et vérifier que total = somme des fournisseurs (5 056 actuellement).
- Commentaires obligatoires : chaque module et chaque fonction a un docstring ; commenter
  le « pourquoi » des blocs non évidents (cas illimités, validations, formules de stats).
  Tout code ajouté ou modifié doit être commenté, en français.
- Code lisible et facile à comprendre : noms explicites (pas d'abréviations cryptiques),
  fonctions courtes à responsabilité unique, pas de one-liners trop denses ni d'astuces
  obscures ; préférer la version simple et claire à la version « maligne ».
- Pas de dépendances réseau à l'exécution du script (hors police Poppins du rapport, facultative) ;
  ne pas committer `rapport/` sauf demande.
