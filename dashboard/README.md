# MyBestSim : Rapport statistique du catalogue eSIM

Ce programme lit les fichiers CSV du catalogue eSIM (un fichier par fournisseur) et génère
un **rapport web** présentant les chiffres clés, un détail par fournisseur et des classements
filtrables.

## Ce que montre le rapport

- **Chiffres clés :** nombre total de cartes eSIM, produits à plus de 100 €, fourchette de prix
  (min / max), data moyenne par carte (hors illimités), prix moyen et médian, forfaits illimités,
  prix moyen par Go, nombre de pays / zones couverts.
- **Répartition par fournisseur :** graphique en barres du nombre de cartes de chaque fournisseur.
- **Détail par fournisseur :** tableau triable (clic sur un en-tête) avec le nombre de cartes,
  la part, le prix moyen et médian, la data moyenne, le prix par Go, la part d'illimités et le
  nombre de produits à plus de 100 €.
- **Top 10 des produits :** les 10 moins chers et les 10 plus chers, filtrables par
  **fournisseur**, **pays / zone**, **volume de data** et **durée du forfait** (critères combinables).
- **Qualité des données :** signale les lignes ignorées (prix invalide, SKU en double…).

> Les forfaits **illimités** (colonne `data_gb` vide) ne sont jamais comptés comme 0 Go : ils sont
> exclus des moyennes de data et du prix par Go, et comptés à part.

## Prérequis

- Python 3 (testé avec 3.13), aucune bibliothèque externe pour générer le rapport.

## Utilisation

Générer le rapport (depuis la racine du projet) :

```bash
python generer_rapport.py
```

Le rapport est écrit dans `rapport/index.html` : ouvrez-le par double-clic dans un navigateur,
aucun serveur n'est nécessaire.

Les fichiers CSV doivent se trouver dans le dossier `donnees-test-mybestsim/`.


## Format des CSV

Chaque fichier doit avoir au minimum ces colonnes (UTF-8, séparateur virgule, prix avec point
décimal). Les autres colonnes éventuelles sont ignorées.

```
sku, provider, product_name, country_name, data_gb, validity_days, price, currency
```

Le fournisseur est lu dans la colonne `provider` (et non dans le nom du fichier). Un fichier avec
des colonnes manquantes est signalé dans la section « Qualité des données ».

## Structure du projet

| Chemin | Rôle |
|---|---|
| `generer_rapport.py` | Génère la page HTML (rendu uniquement) |
| `stats.py` | Lecture des CSV, validation et calcul des statistiques |
| `templates/style.css` | Source du CSS (copié dans `rapport/` à chaque génération) |
| `templates/script.js` | Source du JavaScript : tri des tableaux et filtres du top 10 |
| `assets/logo.webp` | Logo affiché en haut du rapport |
| `donnees-test-mybestsim/` | CSV de test (18 fournisseurs, 5 056 produits) |
| `rapport/` | Sortie générée : `index.html`, `style.css`, `script.js`, `donnees.js`, `assets/` |
| `.github/workflows/pages.yml` | Publication automatique du rapport sur GitHub Pages |
| `CLAUDE.md` | Conventions du projet pour Claude Code |
