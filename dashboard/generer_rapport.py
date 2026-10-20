"""Génère rapport/index.html (+ style.css et script.js) à partir des CSV du catalogue eSIM.

Ce module ne fait que le rendu HTML ; tous les calculs sont dans stats.py.
Le HTML produit est indenté : chaque balise de bloc est sur sa propre ligne.

Usage : python generer_rapport.py
(les CSV sont lus dans donnees-test-mybestsim/, le rapport est écrit dans rapport/)
"""
import json
import os
import shutil
import sys
from html import escape
from textwrap import indent

# stats.py est dans le même dossier que ce script : import direct, quel que soit le dossier de lancement.
from stats import calculer, charger, produits_pour_export

RACINE = os.path.dirname(os.path.abspath(__file__))

DOSSIER_DONNEES = os.path.join(RACINE, "donnees-test-mybestsim")
FICHIER_SORTIE = os.path.join(RACINE, "rapport", "index.html")
DOSSIER_MODELES = os.path.join(RACINE, "templates")
# Fichiers statiques copiés à côté de index.html à chaque génération.
FICHIERS_STATIQUES = ["style.css", "script.js"]
# Images du rapport (logo...) : le dossier assets/ est copié tel quel à côté de index.html.
DOSSIER_ASSETS = os.path.join(RACINE, "assets")
NOM_LOGO = "logo.webp"

UN_NIVEAU = "    "  # 4 espaces par niveau d'indentation


# ----------------------------------------------------------------------
# Formatage des nombres et des prix (à la française)
# ----------------------------------------------------------------------
def formater_nombre(valeur, decimales=0):
    """Formate un nombre à la française : espace fine insécable, virgule décimale."""
    # On passe par le format anglais (1,234.5) puis on permute les séparateurs.
    texte = f"{valeur:,.{decimales}f}"
    return texte.replace(",", " ").replace(".", ",")


def formater_prix(valeur):
    """Formate un prix : « 12,34 € » (espace insécable pour éviter un retour à la ligne)."""
    return f"{formater_nombre(valeur, 2)} €"


def formater_data(data):
    """Volume de data : « 5 Go », ou « Illimité » quand data vaut None."""
    if data is None:
        return "Illimité"
    return f"{formater_nombre(data, 0 if data == int(data) else 1)} Go"


def formater_pourcentage(valeur, decimales=1):
    """Formate un pourcentage : « 12,9 % »."""
    return f"{formater_nombre(valeur, decimales)} %"


# ----------------------------------------------------------------------
# Briques HTML (chaque fonction renvoie un bloc déjà indenté)
# ----------------------------------------------------------------------
def indenter(bloc_html, niveaux=1):
    """Décale tout un bloc HTML vers la droite pour l'insérer dans une balise parente."""
    return indent(bloc_html, UN_NIVEAU * niveaux)


def carte(titre, contenu_html, classe_supplementaire=""):
    """Encadré avec un titre, qui contient le HTML fourni."""
    classes = f"carte {classe_supplementaire}".strip()
    return "\n".join([
        f'<section class="{classes}">',
        f'    <h2>{escape(titre)}</h2>',
        indenter(contenu_html),
        '</section>',
    ])


def carte_kpi(titre, valeur, detail=""):
    """Carte d'indicateur clé : libellé, grande valeur, détail optionnel."""
    # escape() partout : les valeurs viennent des CSV, on évite toute injection HTML.
    lignes = [
        '<div class="carte">',
        f'    <div class="kpi-titre">{escape(titre)}</div>',
        f'    <div class="kpi-valeur">{escape(valeur)}</div>',
    ]
    if detail:
        lignes.append(f'    <div class="kpi-detail">{escape(detail)}</div>')
    lignes.append('</div>')
    return "\n".join(lignes)


def graphique_barres(elements, cle_libelle="label", cle_valeur="count", titre=""):
    """Graphique en barres horizontales en HTML/CSS (aucune dépendance externe)."""
    # Largeur relative à la plus grande valeur ; `or 1` évite une division par zéro.
    valeur_max = max((element[cle_valeur] or 0) for element in elements) or 1

    lignes_barres = []
    for element in elements:
        valeur = element[cle_valeur] or 0
        largeur_pourcent = valeur / valeur_max * 100
        lignes_barres.append("\n".join([
            '<div class="ligne-barre">',
            f'    <span class="barre-libelle">{escape(str(element[cle_libelle]))}</span>',
            '    <span class="barre-fond">',
            f'        <span class="barre" style="width: {largeur_pourcent:.1f}%"></span>',
            '    </span>',
            f'    <span class="barre-valeur">{escape(formater_nombre(valeur))}</span>',
            '</div>',
        ]))

    # role="img" + aria-label : le graphique reste compréhensible pour un lecteur d'écran.
    return "\n".join([
        f'<div role="img" aria-label="{escape(titre)}">',
        indenter("\n".join(lignes_barres)),
        '</div>',
    ])


def tableau(entetes, lignes, triable=True, classes_supplementaires="", id_corps=""):
    """Tableau HTML. Les cellules de `lignes` doivent déjà être échappées par l'appelant.

    `id_corps` donne un identifiant au <tbody> pour que script.js puisse le remplir.
    """
    classes = f'{"triable " if triable else ""}{classes_supplementaires}'.strip()
    classe = f' class="{classes}"' if classes else ""
    attribut_id = f' id="{id_corps}"' if id_corps else ""

    html_entetes = "\n".join(f"<th>{escape(entete)}</th>" for entete in entetes)

    html_lignes = []
    for cellules in lignes:
        html_cellules = "\n".join(f"<td>{cellule}</td>" for cellule in cellules)
        html_lignes.append("\n".join([
            "<tr>",
            indenter(html_cellules),
            "</tr>",
        ]))

    return "\n".join([
        '<div class="tableau-defilant">',
        f'    <table{classe}>',
        '        <thead>',
        '            <tr>',
        indenter(html_entetes, 4),
        '            </tr>',
        '        </thead>',
        f'        <tbody{attribut_id}>',
        indenter("\n".join(html_lignes), 3),
        '        </tbody>',
        '    </table>',
        '</div>',
    ])


def tableau_classement(produits, id_corps):
    """Tableau Produit / Fournisseur / Pays / Prix pour un top 10 (non triable : déjà classé).

    Ce contenu est le point de départ (tous fournisseurs, tous pays) ;
    script.js le remplace quand l'utilisateur choisit un filtre.
    """
    lignes = [
        [escape(produit["name"]), escape(produit["provider"]),
         escape(produit["country"]), formater_data(produit["data"]),
         f'{produit["days"]} jours', formater_prix(produit["price"])]
        for produit in produits
    ]
    return tableau(["Produit", "Fournisseur", "Pays / zone", "Data", "Durée", "Prix"], lignes,
                   triable=False, classes_supplementaires="tableau-classement", id_corps=id_corps)


# ----------------------------------------------------------------------
# Sections de la page
# ----------------------------------------------------------------------
def section_kpis(stats):
    """Les cartes d'indicateurs : les 6 chiffres demandés d'abord, puis les compléments."""
    part_chers = stats["over_100"] / stats["total"] * 100
    cartes = [
        carte_kpi("Cartes eSIM (produits)", formater_nombre(stats["total"]),
                  f'{stats["providers_count"]} fournisseurs'),
        carte_kpi("Produits à plus de 100 €", formater_nombre(stats["over_100"]),
                  f'{formater_pourcentage(part_chers)} du catalogue'),
        carte_kpi("Fourchette de prix",
                  f'{formater_prix(stats["price_min"])} – {formater_prix(stats["price_max"])}',
                  f'min : {stats["cheapest"]["provider"]} · max : {stats["priciest"]["provider"]}'),
        # On précise toujours le périmètre derrière une moyenne (règle du CLAUDE.md).
        carte_kpi("Data moyenne par carte", f'{formater_nombre(stats["avg_data"], 1)} Go',
                  f'sur {formater_nombre(stats["avg_data_n"])} cartes '
                  f'(hors {formater_nombre(stats["unlimited"])} illimitées)'),
        carte_kpi("Prix moyen global", formater_prix(stats["avg_price"]),
                  f'médiane {formater_prix(stats["median_price"])}'),
        carte_kpi("Forfaits illimités", formater_nombre(stats["unlimited"]),
                  f'{formater_pourcentage(stats["unlimited_pct"])} du catalogue'),
        carte_kpi("Prix moyen par Go", formater_prix(stats["price_per_gb"]), "hors illimités"),
        carte_kpi("Pays / zones couverts", formater_nombre(stats["countries_count"]),
                  f'{formater_pourcentage(stats["regional_pct"])} de produits régionaux'),
    ]
    return "\n".join([
        '<section class="grille-kpi">',
        indenter("\n".join(cartes)),
        '</section>',
    ])


def section_detail_fournisseurs(fournisseurs):
    """Tableau détaillé par fournisseur, avec une courte note explicative au-dessus."""
    synthese = (
        "Cliquez sur un en-tête pour trier. Le prix moyen par Go et la data moyenne "
        "excluent les illimités."
    )

    def ou_tiret(valeur, formateur):
        """Affiche un tiret quand la valeur est absente (ex. fournisseur 100 % illimité)."""
        return formateur(valeur) if valeur is not None else "-"

    lignes = []
    for f in fournisseurs:
        lignes.append([
            escape(f["name"]),
            formater_nombre(f["count"]),
            formater_pourcentage(f["pct"]),
            formater_prix(f["avg_price"]),
            formater_prix(f["median_price"]),
            ou_tiret(f["avg_data"], lambda v: f"{formater_nombre(v, 1)} Go"),
            ou_tiret(f["price_per_gb"], formater_prix),
            formater_pourcentage(f["unlimited_pct"], 0),
            formater_nombre(f["over_100"]),
        ])

    entetes = ["Fournisseur", "Cartes", "Part", "Prix moyen", "Prix médian",
               "Data moy.", "€/Go", "Illimités", "> 100 €"]
    contenu = f'<p class="discret">{synthese}</p>\n{tableau(entetes, lignes)}'
    return carte("Détail par fournisseur", contenu)


def section_classements(stats):
    """Barre de filtres (fournisseur / pays) puis les 10 moins chers et les 10 plus chers."""
    # Les listes déroulantes sont remplies par script.js à partir de donnees.js.
    filtres = "\n".join([
        '<div class="filtres">',
        '    <label>',
        '        <span class="etiquette">Fournisseur</span>',
        '        <select id="filtre-fournisseur">',
        '            <option value="">Tous les fournisseurs</option>',
        '        </select>',
        '    </label>',
        '    <label>',
        '        <span class="etiquette">Pays / zone</span>',
        '        <select id="filtre-pays">',
        '            <option value="">Tous les pays</option>',
        '        </select>',
        '    </label>',
        '    <label>',
        '        <span class="etiquette">Data</span>',
        '        <select id="filtre-data">',
        '            <option value="">Toutes les data</option>',
        '        </select>',
        '    </label>',
        '    <label>',
        '        <span class="etiquette">Durée du forfait</span>',
        '        <select id="filtre-duree">',
        '            <option value="">Toutes les durées</option>',
        '        </select>',
        '    </label>',
        '    <button type="button" id="filtre-reinitialiser">Réinitialiser</button>',
        '    <p class="discret" id="filtre-resume"></p>',
        '</div>',
    ])
    # Les deux classements sont des blocs simples (sans encadré) : ils vivent dans la même
    # carte que les filtres, pour que l'on comprenne que les listes pilotent les tableaux.
    classements = [
        bloc_classement("10 produits les moins chers",
                        tableau_classement(stats["top_cheap"], "top-moins-chers")),
        bloc_classement("10 produits les plus chers",
                        tableau_classement(stats["top_expensive"], "top-plus-chers")),
    ]
    grille = "\n".join([
        '<div class="grille-deux">',
        indenter("\n".join(classements)),
        '</div>',
    ])
    return carte("Top 10 des produits", f"{filtres}\n\n{grille}")


def bloc_classement(titre, tableau_html):
    """Un classement : petit titre + tableau, sans encadré propre."""
    return "\n".join([
        '<div>',
        f'    <h3>{escape(titre)}</h3>',
        indenter(tableau_html),
        '</div>',
    ])


def section_qualite(problemes):
    """Alerte si des lignes ont été ignorées, sinon simple note de confirmation."""
    if not problemes:
        return ('<p class="discret">Qualité des données : aucune anomalie détectée '
                '(colonnes, prix, SKU, devise).</p>')

    # Limité à 50 lignes pour que la page reste lisible.
    elements = "\n".join(f"<li>{escape(probleme)}</li>" for probleme in problemes[:50])
    contenu = "\n".join([
        f'<p>{len(problemes)} problème(s) détecté(s) (lignes ignorées) :</p>',
        '<ul>',
        indenter(elements),
        '</ul>',
    ])
    return carte("Qualité des données", contenu, "carte-alerte")


def construire_corps(stats, problemes, dossier_donnees):
    """Assemble le contenu de <main> à partir des stats (résultat de calculer)."""
    if not stats["total"]:
        return "<p>Aucune donnée.</p>"

    nom_dossier = os.path.basename(dossier_donnees.rstrip("/\\"))
    # Le logo n'est affiché que s'il a été déposé dans assets/ (sinon l'en-tête reste valide).
    lignes_logo = []
    if os.path.exists(os.path.join(DOSSIER_ASSETS, NOM_LOGO)):
        lignes_logo = [f'    <img class="logo" src="assets/{NOM_LOGO}" alt="MyBestSim">']

    en_tete = "\n".join([
        '<header>',
        *lignes_logo,
        '    <h1>MyBestSim - Catalogue <em>eSIM</em></h1>',
        '    <p class="encadre">',
        f'        {formater_nombre(stats["total"])} produits comparés auprès de '
        f'{stats["providers_count"]} fournisseurs.',
        '    </p>',
        f'    <span class="pastille-verte">Source : {escape(nom_dossier)}/</span>',
        '</header>',
    ])

    # Les sections sont séparées par une ligne vide pour aérer le code source.
    sections = [
        en_tete,
        section_kpis(stats),
        carte("Répartition par fournisseur",
              graphique_barres(stats["providers"], "name", "count",
                               titre="Nombre de cartes par fournisseur")),
        section_detail_fournisseurs(stats["providers"]),
        section_classements(stats),
        section_qualite(problemes),
    ]
    return "\n\n".join(sections)


def construire_page(corps_html):
    """Page HTML complète : le CSS et le JS sont dans des fichiers séparés."""
    return "\n".join([
        '<!doctype html>',
        '<html lang="fr">',
        '',
        '<head>',
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        '    <title>MyBestSim Rapport</title>',
        # Police Poppins (celle du site) : si elle ne se charge pas, la page reste lisible.
        '    <link rel="preconnect" href="https://fonts.googleapis.com">',
        '    <link rel="stylesheet" '
        'href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,500;0,600;0,700;1,700&display=swap">',
        '    <link rel="stylesheet" href="style.css">',
        '</head>',
        '',
        '<body>',
        '    <main>',
        indenter(corps_html, 2),
        '    </main>',
        '',
        '    <script src="donnees.js"></script>',
        '    <script src="script.js"></script>',
        '</body>',
        '',
        '</html>',
        '',
    ])


def main():
    """Point d'entrée : charge les CSV, calcule les stats, écrit la page et ses fichiers."""
    # Les chemins sont fixes : CSV dans donnees-test-mybestsim/, sortie dans rapport/index.html.
    dossier_donnees = DOSSIER_DONNEES
    fichier_sortie = FICHIER_SORTIE

    lignes, problemes = charger(dossier_donnees)
    if not lignes:
        sys.exit(f"Aucune donnée valide dans {dossier_donnees}")

    corps = construire_corps(calculer(lignes), problemes, dossier_donnees)
    page = construire_page(corps)

    dossier_sortie = os.path.dirname(os.path.abspath(fichier_sortie))
    os.makedirs(dossier_sortie, exist_ok=True)
    with open(fichier_sortie, "w", encoding="utf-8") as fichier:
        fichier.write(page)

    # donnees.js : tous les produits, pour que le navigateur recalcule les top 10 filtrés.
    # Un produit par ligne (et non tout sur une seule ligne) pour garder le fichier lisible.
    lignes_produits = [
        "    " + json.dumps(produit, ensure_ascii=False)
        for produit in produits_pour_export(lignes)
    ]
    contenu_donnees = "const PRODUITS = [\n" + ",\n".join(lignes_produits) + "\n];\n"
    with open(os.path.join(dossier_sortie, "donnees.js"), "w", encoding="utf-8") as fichier:
        fichier.write(contenu_donnees)

    # Le CSS et le JS vivent dans templates/ : on les copie à côté de index.html.
    for nom in FICHIERS_STATIQUES:
        shutil.copyfile(os.path.join(DOSSIER_MODELES, nom), os.path.join(dossier_sortie, nom))

    # Copie du dossier assets/ (logo...) s'il existe.
    if os.path.isdir(DOSSIER_ASSETS):
        shutil.copytree(DOSSIER_ASSETS, os.path.join(dossier_sortie, "assets"), dirs_exist_ok=True)

    print(f"{len(lignes)} produits, {len(problemes)} problème(s) -> {fichier_sortie}")


if __name__ == "__main__":
    main()
