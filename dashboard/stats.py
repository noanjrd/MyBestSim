"""Chargement et calcul des statistiques du catalogue eSIM (sans rendu).

Ce module ne produit aucun HTML : il lit les CSV, valide les lignes puis calcule
les indicateurs (KPI) sous forme de dictionnaires, afin de rester séparés du rendu HTML.
"""
import csv
import glob
import os
import statistics
from collections import Counter, defaultdict

# Colonnes des CSV réellement utilisées par le rapport (les autres colonnes sont ignorées).
COLONNES = ["sku", "provider", "product_name", "country_name",
            "data_gb", "validity_days", "price", "currency"]
# Noms de "pays" qui sont en réalité des zones régionales. On se base sur le NOM
# et non sur le code : le code « SA » désigne l'Arabie saoudite, pas l'Amérique du Sud.
REGIONS_NOMS = {"Europe", "Asie", "Monde", "Afrique", "Amérique", "Océanie",
                "Moyen-Orient", "Amérique du Nord", "Amérique du Sud",
                "Amérique latine", "Global"}
# Seuil du KPI « produits chers » : strictement supérieur à ce prix (en €).
SEUIL_PRIX = 100.0


def charger(dossier):
    """Lit tous les *.csv du dossier.

    Retourne (lignes valides, problèmes). Une ligne invalide est ignorée et
    signalée dans la liste des problèmes, sans interrompre le chargement.
    """
    lignes, problemes, skus = [], [], set()
    # glob + tri : tout nouveau CSV déposé dans le dossier est pris en compte,
    # et l'ordre de lecture reste déterministe.
    fichiers = sorted(glob.glob(os.path.join(dossier, "*.csv")))
    for chemin in fichiers:
        nom = os.path.basename(chemin)
        # utf-8-sig : tolère un éventuel BOM ; les accents français restent corrects.
        with open(chemin, encoding="utf-8-sig", newline="") as f:
            lecteur = csv.DictReader(f)
            manquantes = [c for c in COLONNES if c not in (lecteur.fieldnames or [])]
            if manquantes:
                # Fichier inutilisable : on le signale et on passe au suivant.
                problemes.append(f"{nom} : colonnes manquantes {manquantes}")
                continue
            # start=2 : la ligne 1 est l'en-tête, donc le numéro affiché
            # correspond à la ligne réelle dans le fichier.
            for n, r in enumerate(lecteur, start=2):
                # Validation du prix : numérique et strictement positif.
                try:
                    prix = float(r["price"])
                    if prix <= 0:
                        raise ValueError("prix <= 0")
                except (ValueError, TypeError):
                    problemes.append(f"{nom} l.{n} : prix invalide ({r['price']!r})")
                    continue
                # Le SKU doit être unique sur l'ensemble des fichiers.
                if r["sku"] in skus:
                    problemes.append(f"{nom} l.{n} : SKU en double ({r['sku']})")
                    continue
                skus.add(r["sku"])
                # data_gb vide = forfait illimité : on stocke None (et NON 0),
                # sinon la moyenne de data serait faussée.
                brut = (r["data_gb"] or "").strip()
                try:
                    data = float(brut) if brut else None
                except ValueError:
                    problemes.append(f"{nom} l.{n} : data_gb invalide ({brut!r})")
                    continue
                lignes.append({
                    "provider": r["provider"],
                    "name": r["product_name"], "country": r["country_name"],
                    "data": data, "illimite": data is None,
                    "days": int(r["validity_days"]), "price": prix,
                    "currency": r["currency"],
                })
    # Mélanger des devises fausserait toutes les moyennes : on le signale.
    devises = {l["currency"] for l in lignes}
    if len(devises) > 1:
        problemes.append(f"Plusieurs devises présentes : {sorted(devises)}")
    return lignes, problemes


def _moy(vals):
    """Moyenne arithmétique, ou None si la liste est vide (évite une division par 0)."""
    return statistics.fmean(vals) if vals else None


def _produit(l):
    """Résumé minimal d'un produit (nom, fournisseur, pays, data, durée, prix) pour l'affichage."""
    # data vaut None pour un forfait illimité (devient null dans donnees.js).
    return {"name": l["name"], "provider": l["provider"],
            "country": l["country"], "data": l["data"], "days": l["days"],
            "price": l["price"]}


def produits_pour_export(lignes):
    """Liste compacte de tous les produits, utilisée par le navigateur pour filtrer les top 10."""
    return [_produit(l) for l in lignes]


def calculer(lignes):
    """Calcule tous les KPI à partir des lignes chargées."""
    total = len(lignes)
    if not total:
        return {"total": 0}
    prix = [l["price"] for l in lignes]
    # Les illimités n'ont pas de volume : ils sont exclus de tout calcul sur la data.
    avec_data = [l for l in lignes if not l["illimite"]]
    data = [l["data"] for l in avec_data]
    moins_cher = min(lignes, key=lambda l: l["price"])
    plus_cher = max(lignes, key=lambda l: l["price"])

    # --- Statistiques par fournisseur (colonne `provider`, pas le nom de fichier) ---
    # defaultdict : une clé qui n'existe pas encore est créée toute seule avec une liste vide.
    par_four = defaultdict(list)
    for l in lignes:
        par_four[l["provider"]].append(l)
    fournisseurs = []
    for nom, ls in par_four.items():
        pf = [l["price"] for l in ls]
        dg = [l for l in ls if not l["illimite"]]
        # Prix par Go : uniquement pour les forfaits à volume défini (> 0).
        ppg = [l["price"] / l["data"] for l in dg if l["data"] > 0]
        fournisseurs.append({
            "name": nom, "count": len(ls), "pct": len(ls) / total * 100,
            "avg_price": _moy(pf), "median_price": statistics.median(pf),
            "unlimited_pct": sum(l["illimite"] for l in ls) / len(ls) * 100,
            "avg_data": _moy([l["data"] for l in dg]),
            "price_per_gb": _moy(ppg),
            "over_100": sum(l["price"] > SEUIL_PRIX for l in ls),
        })
    # Plus gros catalogue d'abord ; le nom départage les égalités.
    fournisseurs.sort(key=lambda f: (-f["count"], f["name"]))

    # --- Géographie ---
    zones = Counter(l["country"] for l in lignes)
    regionaux = sum(1 for l in lignes if l["country"] in REGIONS_NOMS)
    # Prix moyen par Go global, toujours hors illimités.
    ppg_global = [l["price"] / l["data"] for l in avec_data if l["data"] > 0]

    return {
        "total": total,
        "providers_count": len(fournisseurs),
        # Strictement supérieur à 100 € (un produit à 100,00 € n'est pas compté).
        "over_100": sum(p > SEUIL_PRIX for p in prix),
        "price_min": moins_cher["price"], "price_max": plus_cher["price"],
        "cheapest": _produit(moins_cher), "priciest": _produit(plus_cher),
        "avg_price": _moy(prix), "median_price": statistics.median(prix),
        # avg_data_n : nombre de cartes réellement prises en compte dans la moyenne.
        "avg_data": _moy(data), "avg_data_n": len(data),
        "unlimited": total - len(avec_data),
        "unlimited_pct": (total - len(avec_data)) / total * 100,
        "price_per_gb": _moy(ppg_global),
        "providers": fournisseurs,
        "countries_count": len(zones),
        "regional_pct": regionaux / total * 100,
        # Top 10 des moins chers / plus chers.
        "top_cheap": [_produit(l) for l in sorted(lignes, key=lambda l: l["price"])[:10]],
        "top_expensive": [_produit(l) for l in sorted(lignes, key=lambda l: -l["price"])[:10]],
    }
