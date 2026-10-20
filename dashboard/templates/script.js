// Tri des tableaux au clic sur un en-tête de colonne.
// Source éditable : copiée dans rapport/script.js à chaque génération.

// Flèche affichée à côté d'un nom de colonne qui n'est pas (encore) triée.
const FLECHE_NEUTRE = "↕";

// Transforme le texte d'une cellule (« 12,34 € », « 14,3 % »...) en nombre.
// Si la cellule n'est pas numérique, on renvoie le texte tel quel (tri alphabétique).
function valeurDeCellule(ligne, indexColonne) {
    const texte = ligne.cells[indexColonne].textContent;
    const textePropre = texte
        .replace(/[\s  €%Go]/g, "")  // espaces, unités
        .replace(",", ".");                    // virgule décimale française
    const nombre = parseFloat(textePropre);

    if (textePropre === "" || isNaN(nombre)) {
        return texte;
    }
    return nombre;
}

// Trie les lignes du tableau selon une colonne ; un second clic inverse le sens.
function trierTableau(tableau, entete, indexColonne) {
    const corps = tableau.tBodies[0];
    const lignes = Array.from(corps.rows);

    const ordreCroissant = entete.dataset.croissant !== "1";
    entete.dataset.croissant = ordreCroissant ? "1" : "0";

    // Une seule colonne est triée à la fois : on remet les autres flèches à neutre.
    tableau.querySelectorAll("th .fleche").forEach((fleche) => {
        fleche.textContent = FLECHE_NEUTRE;
        fleche.classList.remove("fleche-active");
    });
    const flecheActive = entete.querySelector(".fleche");
    flecheActive.textContent = ordreCroissant ? "▲" : "▼";
    flecheActive.classList.add("fleche-active");

    lignes.sort((ligneA, ligneB) => {
        const a = valeurDeCellule(ligneA, indexColonne);
        const b = valeurDeCellule(ligneB, indexColonne);

        let comparaison = 0;
        if (indexColonne === 0) {
            const  nameA = ligneA.cells[0].textContent
            const  nameB = ligneB.cells[0].textContent
            comparaison = nameA.localeCompare(nameB, "fr")
        }
        else {
            if (a > b) comparaison = 1;
            if (a < b) comparaison = -1;
        }

        return ordreCroissant ? comparaison : -comparaison;
    });

    // Réinsérer les lignes dans le nouvel ordre.
    lignes.forEach((ligne) => corps.appendChild(ligne));
}

// ----------------------------------------------------------------------
// Top 10 filtrables par fournisseur et/ou par pays
// (la liste complète des produits vient de donnees.js : PRODUITS)
// ----------------------------------------------------------------------
const TAILLE_TOP = 10;

// Formate un prix comme le rapport : « 12,34 € » (espace insécable avant €).
function formaterPrix(prix) {
    const nombre = prix.toLocaleString("fr-FR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    return nombre + " €";
}

// Ajoute une option par valeur dans une liste déroulante.
function remplirListe(liste, valeurs) {
    valeurs.forEach((valeur) => {
        const option = document.createElement("option");
        option.value = valeur;
        option.textContent = valeur;
        liste.appendChild(option);
    });
}

// Valeurs distinctes d'un champ des produits, triées par ordre alphabétique.
function valeursDistinctes(champ) {
    const valeurs = new Set(PRODUITS.map((produit) => produit[champ]));
    return Array.from(valeurs).sort((a, b) => a.localeCompare(b, "fr"));
}

// Valeur de la liste « Data » pour les forfaits illimités (data = null dans PRODUITS).
const VALEUR_ILLIMITE = "illimite";

// Texte affiché pour le volume de data d'un produit : « 5 Go » ou « Illimité ».
function formaterData(data) {
    return data === null ? "Illimité" : data + " Go";
}

// Remplit la liste « Data » : volumes présents triés du plus petit au plus grand,
// puis « Illimité » en dernier (s'il existe des forfaits illimités).
function remplirListeData(liste) {
    const volumes = PRODUITS
        .map((produit) => produit.data)
        .filter((data) => data !== null);
    const volumesTries = Array.from(new Set(volumes)).sort((a, b) => a - b);

    volumesTries.forEach((volume) => {
        const option = document.createElement("option");
        option.value = String(volume);
        option.textContent = volume + " Go";
        liste.appendChild(option);
    });

    if (PRODUITS.some((produit) => produit.data === null)) {
        const option = document.createElement("option");
        option.value = VALEUR_ILLIMITE;
        option.textContent = "Illimité";
        liste.appendChild(option);
    }
}

// Un produit correspond-il à la liste « Data » ? (vide = tous)
function correspondData(produit, choix) {
    if (choix === "") return true;
    if (choix === VALEUR_ILLIMITE) return produit.data === null;
    return produit.data === Number(choix);
}

// Remplit la liste « Durée » : durées présentes (en jours), de la plus courte à la plus longue.
function remplirListeDuree(liste) {
    const durees = Array.from(new Set(PRODUITS.map((produit) => produit.days)))
        .sort((a, b) => a - b);

    durees.forEach((jours) => {
        const option = document.createElement("option");
        option.value = String(jours);
        option.textContent = jours + " jours";
        liste.appendChild(option);
    });
}

// Remplace le contenu d'un tableau de classement par les produits donnés.
function afficherClassement(idCorps, produits) {
    const corps = document.getElementById(idCorps);
    corps.innerHTML = "";

    produits.forEach((produit) => {
        const ligne = document.createElement("tr");
        const cellules = [
            produit.name,
            produit.provider,
            produit.country,
            formaterData(produit.data),
            produit.days + " jours",
            formaterPrix(produit.price),
        ];
        cellules.forEach((texte) => {
            const cellule = document.createElement("td");
            cellule.textContent = texte;  // textContent : pas d'injection HTML possible
            ligne.appendChild(cellule);
        });
        corps.appendChild(ligne);
    });
}

function initialiserTopFiltrable() {
    const listeFournisseur = document.getElementById("filtre-fournisseur");
    const listePays = document.getElementById("filtre-pays");
    const listeData = document.getElementById("filtre-data");
    const listeDuree = document.getElementById("filtre-duree");
    const boutonReinitialiser = document.getElementById("filtre-reinitialiser");
    const resume = document.getElementById("filtre-resume");

    // Page sans filtres ou sans données : on laisse le tableau tel que généré.
    if (!listeFournisseur || !listePays || !listeData || !listeDuree ||
        typeof PRODUITS === "undefined") {
        return;
    }

    remplirListe(listeFournisseur, valeursDistinctes("provider"));
    remplirListe(listePays, valeursDistinctes("country"));
    remplirListeData(listeData);
    remplirListeDuree(listeDuree);

    function mettreAJour() {
        const fournisseur = listeFournisseur.value;
        const pays = listePays.value;
        const data = listeData.value;
        const duree = listeDuree.value;

        // Une liste vide = « tous » ; sinon le produit doit correspondre aux 4 critères.
        const produits = PRODUITS.filter((produit) =>
            (fournisseur === "" || produit.provider === fournisseur) &&
            (pays === "" || produit.country === pays) &&
            correspondData(produit, data) &&
            (duree === "" || produit.days === Number(duree))
        );

        const moinsChers = [...produits].sort((a, b) => a.price - b.price);
        const plusChers = [...produits].sort((a, b) => b.price - a.price);

        afficherClassement("top-moins-chers", moinsChers.slice(0, TAILLE_TOP));
        afficherClassement("top-plus-chers", plusChers.slice(0, TAILLE_TOP));

        resume.textContent = produits.length + " produit(s) correspondent à la sélection.";
    }

    listeFournisseur.addEventListener("change", mettreAJour);
    listePays.addEventListener("change", mettreAJour);
    listeData.addEventListener("change", mettreAJour);
    listeDuree.addEventListener("change", mettreAJour);
    boutonReinitialiser.addEventListener("click", () => {
        listeFournisseur.value = "";
        listePays.value = "";
        listeData.value = "";
        listeDuree.value = "";
        mettreAJour();
    });

    mettreAJour();
}

initialiserTopFiltrable();


// ----------------------------------------------------------------------
// Tri des tableaux au clic sur un en-tête
// ----------------------------------------------------------------------
document.querySelectorAll("table.triable").forEach((tableau) => {
    tableau.querySelectorAll("th").forEach((entete, indexColonne) => {
        // Ajoute la flèche à côté du nom de la colonne.
        const fleche = document.createElement("span");
        fleche.className = "fleche";
        fleche.textContent = FLECHE_NEUTRE;
        entete.appendChild(fleche);

        entete.addEventListener("click", () => {
            trierTableau(tableau, entete, indexColonne);
        });
    });
});
