#!/usr/bin/env python3
"""Construit le site statique à partir des fichiers de donnees/.

Aucune dépendance externe : bibliothèque standard uniquement. Le site produit
est entièrement statique, donc hébergeable n'importe où et archivable tel quel.

Usage :  python3 scripts/construire.py
Sortie : site/
"""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import statistics
import sys
import tomllib
from datetime import date, datetime, time, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "site"

TITRE_SITE = "Observatoire du traitement de l'information"
EFFECTIF_PRUDENCE = 20  # en dessous, aucun taux n'est affiché sans avertissement

e = html.escape


# --- Lecture ---------------------------------------------------------------

def lire_toml(chemin: Path) -> dict:
    with chemin.open("rb") as f:
        return tomllib.load(f)


def en_date(valeur) -> date:
    return date.fromisoformat(str(valeur))


def en_horodatage(valeur) -> datetime:
    brut = str(valeur).replace("Z", "+00:00")
    marque = datetime.fromisoformat(brut)
    if marque.tzinfo is None:
        marque = marque.replace(tzinfo=timezone.utc)
    return marque.astimezone(timezone.utc)


def charger() -> tuple[dict, dict, list[dict]]:
    vocab = lire_toml(RACINE / "schema" / "vocabulaire.toml")
    medias = {m["id"]: m for m in lire_toml(RACINE / "donnees" / "medias.toml")["media"]}
    evenements = [
        lire_toml(p)
        for p in sorted((RACINE / "donnees" / "evenements").glob("*.toml"))
    ]
    evenements.sort(key=lambda ev: ev["fait"]["date"], reverse=True)
    return vocab, medias, evenements


# --- Mesures ---------------------------------------------------------------

def medias_eligibles(medias: dict, jour: date) -> list[dict]:
    """Un média ne peut être compté comme silencieux que s'il était déjà suivi."""
    return [m for m in medias.values() if en_date(m["suivi_depuis"]) <= jour]


def mesurer_evenement(evenement: dict, medias: dict) -> dict:
    jour = en_date(evenement["fait"]["date"])
    origine = datetime.combine(jour, time.min, tzinfo=timezone.utc)
    articles = evenement.get("article", [])
    eligibles = medias_eligibles(medias, jour)
    couvrants = {a["media"] for a in articles}

    delais = [
        (en_horodatage(a["publication"]) - origine).total_seconds() / 3600
        for a in articles
    ]
    revisions = sum(max(0, len(a.get("releve", [])) - 1) for a in articles)

    return {
        "origine": origine,
        "articles": len(articles),
        "eligibles": len(eligibles),
        "couvrants": len(couvrants),
        "silencieux": [m for m in eligibles if m["id"] not in couvrants],
        "delai_premier": min(delais) if delais else None,
        "revisions": revisions,
    }


def mesurer_media(media: dict, evenements: list[dict], vocab: dict) -> dict:
    depuis = en_date(media["suivi_depuis"])
    eligibles = [ev for ev in evenements if en_date(ev["fait"]["date"]) >= depuis]

    couverts, delais, longueurs, codes, cadres = 0, [], [], [], {}
    for evenement in eligibles:
        siens = [a for a in evenement.get("article", []) if a["media"] == media["id"]]
        if not siens:
            continue
        couverts += 1
        origine = datetime.combine(
            en_date(evenement["fait"]["date"]), time.min, tzinfo=timezone.utc
        )
        for article in siens:
            delais.append(
                (en_horodatage(article["publication"]) - origine).total_seconds() / 3600
            )
            if "signes" in article:
                longueurs.append(article["signes"])
            codage = article.get("codage")
            if codage:
                codes.append(codage)
                cadres[codage["cadre"]] = cadres.get(codage["cadre"], 0) + 1

    frequences = {}
    if codes:
        for variable in vocab["codage"]["booleens"]:
            presents = sum(1 for c in codes if c.get(variable))
            frequences[variable] = (presents, len(codes))

    return {
        "eligibles": len(eligibles),
        "couverts": couverts,
        "taux": couverts / len(eligibles) if eligibles else None,
        "delai_median": statistics.median(delais) if delais else None,
        "longueur_moyenne": statistics.mean(longueurs) if longueurs else None,
        "codes": len(codes),
        "frequences": frequences,
        "cadres": cadres,
    }


# --- Bande de couverture ---------------------------------------------------

def bande(evenement: dict, medias: dict, mesures: dict) -> str:
    """Une ligne par média suivi. Les médias qui n'ont rien publié gardent
    leur ligne : c'est le seul moyen de voir une omission."""
    jour = en_date(evenement["fait"]["date"])
    eligibles = sorted(medias_eligibles(medias, jour), key=lambda m: m["nom"])
    origine = mesures["origine"]

    marques = [
        en_horodatage(r["horodatage"])
        for a in evenement.get("article", [])
        for r in a.get("releve", [])
    ]
    fin_h = max([(m - origine).total_seconds() / 3600 for m in marques] + [47.0])
    jours = int(fin_h // 24) + 1
    portee = jours * 24

    x0, x1 = 170, 700
    def px(heures: float) -> float:
        return x0 + (heures / portee) * (x1 - x0)

    haut, pas = 34, 24
    hauteur = haut + len(eligibles) * pas + 14
    out = [
        f'<svg class="bande" viewBox="0 0 720 {hauteur}" role="img" '
        f'aria-label="Couverture par média, {mesures["couvrants"]} sur '
        f'{mesures["eligibles"]} médias suivis">'
    ]

    for j in range(jours + 1):
        x = px(j * 24)
        out.append(f'<line class="repere" x1="{x:.1f}" y1="26" x2="{x:.1f}" y2="{hauteur - 14}"/>')
        out.append(f'<text x="{x:.1f}" y="18" text-anchor="middle">J+{j}</text>')

    for i, media in enumerate(eligibles):
        y = haut + i * pas + 6
        siens = [a for a in evenement.get("article", []) if a["media"] == media["id"]]
        classe = "ligne-pleine" if siens else "ligne-vide"
        out.append(
            f'<line class="{classe}" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>'
        )
        etiquette = "" if siens else ' class="absent"'
        out.append(
            f'<text x="152" y="{y + 3.5}" text-anchor="end"{etiquette}>'
            f"{e(media['nom'])}</text>"
        )
        for article in siens:
            releves = article.get("releve", [])
            for k, releve in enumerate(releves):
                heures = (en_horodatage(releve["horodatage"]) - origine).total_seconds() / 3600
                x = px(heures)
                if k == 0:
                    out.append(f'<circle class="parution" cx="{x:.1f}" cy="{y}" r="3.5"/>')
                else:
                    out.append(
                        f'<line class="revision" x1="{x:.1f}" y1="{y - 5}" '
                        f'x2="{x:.1f}" y2="{y + 5}"/>'
                    )

    out.append("</svg>")
    return "\n".join(out)


# --- Gabarits --------------------------------------------------------------

def page(titre: str, corps: str, profondeur: int = 0) -> str:
    r = "../" * profondeur
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titre)} — {e(TITRE_SITE)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Public+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400&display=swap">
<link rel="stylesheet" href="{r}style.css">
</head>
<body>
<header class="bandeau"><div class="bandeau-interne">
<a class="marque" href="{r}index.html">{e(TITRE_SITE)}</a>
<nav class="navigation">
<a href="{r}index.html">Corpus</a>
<a href="{r}medias/index.html">Médias</a>
<a href="{r}methode.html">Méthode</a>
<a href="{r}donnees/index.html">Données</a>
</nav>
</div></header>
<div class="enveloppe">
{corps}
<footer class="pied">
<p>Chaque enregistrement est ajouté, jamais écrasé : les corrections créent une
nouvelle version et laissent la précédente visible dans l'historique du dépôt.</p>
<p class="ref">Construit le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC</p>
</footer>
</div>
</body>
</html>
"""


def avertissement_effectif(n: int) -> str:
    if n >= EFFECTIF_PRUDENCE:
        return ""
    return (
        f'<p class="garde-fou">Effectif de {n} événement(s) : trop faible pour '
        f"qu'un écart entre médias soit interprétable. Les chiffres ci-dessous "
        f"décrivent le corpus, ils ne mesurent rien.</p>"
    )


# --- Pages -----------------------------------------------------------------

def page_accueil(evenements: list[dict], medias: dict) -> str:
    total_articles = sum(len(ev.get("article", [])) for ev in evenements)
    total_revisions = sum(
        max(0, len(a.get("releve", [])) - 1)
        for ev in evenements
        for a in ev.get("article", [])
    )

    lignes = []
    for evenement in evenements:
        m = mesurer_evenement(evenement, medias)
        identifiant = evenement["id"]
        delai = f"{m['delai_premier']:.0f} h" if m["delai_premier"] is not None else "aucune reprise"
        lignes.append(
            f"""<li>
<a href="evenements/{identifiant}.html">{e(evenement['fait']['resume'])}</a>
<p class="meta"><span class="ref">{identifiant}</span> · {e(evenement['fait']['date'])} ·
{m['couvrants']}/{m['eligibles']} médias · première reprise à {delai} ·
{m['revisions']} révision(s) de titre</p>
</li>"""
        )

    return f"""<h1>Ce qui a eu lieu, et ce qui en a été publié</h1>
<p class="chapeau">Chaque fait est enregistré à partir d'une source qui ne vient pas
de la presse. La couverture s'y rattache ensuite. Un média suivi qui ne publie rien
garde sa ligne : l'absence se lit aussi bien que la présence.</p>

<div class="avis">Jeu de démonstration. Les faits, les médias et les titres sont
fictifs et servent uniquement à montrer la structure. Aucun chiffre de cette page
ne décrit la presse réelle.</div>

<h2>Corpus</h2>
<table>
<tr><th>Événements</th><th>Articles rattachés</th><th>Médias suivis</th><th>Révisions de titre relevées</th></tr>
<tr><td class="nombre">{len(evenements)}</td><td class="nombre">{total_articles}</td>
<td class="nombre">{len(medias)}</td><td class="nombre">{total_revisions}</td></tr>
</table>
{avertissement_effectif(len(evenements))}

<h2>Événements</h2>
<ul class="liste-evenements">{''.join(lignes)}</ul>
"""


def page_evenement(evenement: dict, medias: dict) -> str:
    fait = evenement["fait"]
    m = mesurer_evenement(evenement, medias)

    sources = "".join(
        f"""<div class="source-primaire">
<span class="ref">{e(s['reference'])}</span> · {e(s['type'])} · {e(str(s.get('date', '')))}
<br>{e(s.get('note', ''))}</div>"""
        for s in fait.get("source_primaire", [])
    )

    silencieux = (
        "<p class=\"meta\">Aucune reprise relevée chez : "
        + ", ".join(e(x["nom"]) for x in m["silencieux"])
        + ".</p>"
        if m["silencieux"]
        else ""
    )

    blocs = []
    for article in sorted(evenement.get("article", []), key=lambda a: a["publication"]):
        releves = article.get("releve", [])
        titres = []
        for i, releve in enumerate(reversed(releves)):
            rang = len(releves) - i
            if rang == len(releves):
                titres.append(f'<p class="titre-releve">{e(releve["titre"])}</p>')
            else:
                titres.append(
                    f'<p class="mention-revision">titre remplacé le '
                    f'{e(str(releve["horodatage"])[:16].replace("T", " à "))}</p>'
                    f'<p class="titre-remplace">{e(releve["titre"])}</p>'
                )

        codage = article.get("codage")
        etiquettes = ""
        desaccord = ""
        if codage:
            items = [f'<span class="etiquette etiquette-cadre">cadre : {e(codage["cadre"])}</span>']
            for cle, valeur in codage.items():
                if isinstance(valeur, bool) and valeur:
                    items.append(
                        f'<span class="etiquette etiquette-active">{e(cle.replace("_", " "))}</span>'
                    )
            items.append(
                f'<span class="etiquette">codeurs : {e(", ".join(codage.get("codeurs", [])))}</span>'
            )
            etiquettes = f'<div class="etiquettes">{"".join(items)}</div>'
            if codage.get("accord") is False:
                desaccord = f'<p class="desaccord">{e(codage.get("note_desaccord", ""))}</p>'

        nom = medias.get(article["media"], {}).get("nom", article["media"])
        signes = f" · {article['signes']} signes" if "signes" in article else ""
        une = " · en une" if article.get("position_une") else ""
        blocs.append(
            f"""<article class="article">
<div class="article-entete">
<span class="article-media">{e(nom)}</span>
<span class="ref">{e(article['id'])} · {e(str(article['publication'])[:16].replace('T', ' à '))}{e(signes)}{e(une)}</span>
</div>
{''.join(titres)}
{etiquettes}
{desaccord}
<p class="meta"><a href="{e(article['url'])}">page d'origine</a> ·
<a href="{e(article['archive'])}">copie archivée</a></p>
</article>"""
        )

    return f"""<div class="plan-evenement">
<aside class="fiche">
<h2>Le fait</h2>
<dl>
<dt>Registre</dt><dd>{e(evenement['id'])}</dd>
<dt>Date</dt><dd>{e(fait['date'])}</dd>
<dt>Type</dt><dd>{e(fait['type'])}</dd>
<dt>Département</dt><dd>{e(str(fait['departement']))}</dd>
<dt>Milieu</dt><dd>{e(fait['milieu'])}</dd>
<dt>Victimes</dt><dd>{e(str(fait['victimes']))}</dd>
</dl>
<p class="resume">{e(fait['resume'])}</p>
<h2>Sources primaires</h2>
{sources}
</aside>

<main>
<h1>Couverture</h1>
<p class="chapeau">{m['couvrants']} média(s) sur {m['eligibles']} suivis ont publié.
{m['revisions']} révision(s) de titre relevée(s).</p>
{bande(evenement, medias, m)}
{silencieux}
<h2>Articles</h2>
{''.join(blocs) or '<p class="meta">Aucun article relevé.</p>'}
</main>
</div>
"""


def page_medias(medias: dict, evenements: list[dict], vocab: dict) -> str:
    lignes = []
    for media in sorted(medias.values(), key=lambda m: m["nom"]):
        s = mesurer_media(media, evenements, vocab)
        taux = f"{s['taux']:.0%}" if s["taux"] is not None else "—"
        delai = f"{s['delai_median']:.0f} h" if s["delai_median"] is not None else "—"
        longueur = f"{s['longueur_moyenne']:.0f}" if s["longueur_moyenne"] else "—"
        lignes.append(
            f"""<tr>
<td><a href="{media['id']}.html">{e(media['nom'])}</a><br>
<span class="ref">{e(media['famille'])}</span></td>
<td class="nombre">{s['couverts']}/{s['eligibles']}</td>
<td class="nombre">{taux}</td>
<td class="nombre">{delai}</td>
<td class="nombre">{longueur}</td>
</tr>"""
        )

    return f"""<h1>Médias suivis</h1>
<p class="chapeau">Le taux de reprise rapporte les événements couverts aux
événements du corpus déjà suivis à leur date. Il ne dit rien de la qualité du
traitement, seulement de la sélection.</p>
{avertissement_effectif(len(evenements))}
<table>
<tr><th>Média</th><th class="nombre">Couverts</th><th class="nombre">Taux de reprise</th>
<th class="nombre">Délai médian</th><th class="nombre">Signes (moy.)</th></tr>
{''.join(lignes)}
</table>
"""


def page_media(media: dict, evenements: list[dict], vocab: dict) -> str:
    s = mesurer_media(media, evenements, vocab)

    if s["codes"]:
        lignes = "".join(
            f'<tr><td>{e(variable.replace("_", " "))}</td>'
            f'<td class="nombre">{n}/{total}</td></tr>'
            for variable, (n, total) in s["frequences"].items()
        )
        frequences = f"""<h2>Marqueurs de cadrage</h2>
<p class="effectif">Sur {s['codes']} article(s) codé(s).</p>
<table><tr><th>Variable</th><th class="nombre">Présence</th></tr>{lignes}</table>"""
    else:
        frequences = '<p class="meta">Aucun article codé pour ce média.</p>'

    cadres = "".join(
        f'<tr><td>{e(cadre)}</td><td class="nombre">{n}</td></tr>'
        for cadre, n in sorted(s["cadres"].items(), key=lambda x: -x[1])
    )

    taux = f"{s['taux']:.0%}" if s["taux"] is not None else "—"
    return f"""<h1>{e(media['nom'])}</h1>
<p class="chapeau"><span class="ref">{e(media['id'])} · {e(media['famille'])} ·
suivi depuis le {e(media['suivi_depuis'])}</span></p>
{avertissement_effectif(s['eligibles'])}
<h2>Sélection</h2>
<table>
<tr><th class="nombre">Événements suivis</th><th class="nombre">Couverts</th><th class="nombre">Taux</th></tr>
<tr><td class="nombre">{s['eligibles']}</td><td class="nombre">{s['couverts']}</td>
<td class="nombre">{taux}</td></tr>
</table>
{frequences}
<h2>Cadres retenus</h2>
<table><tr><th>Cadre</th><th class="nombre">Articles</th></tr>{cadres or '<tr><td>—</td><td class="nombre">0</td></tr>'}</table>
"""


def page_donnees(evenements: list[dict]) -> str:
    return f"""<h1>Données</h1>
<p class="chapeau">Le dépôt fait foi. Ces exports en sont dérivés à chaque
construction et n'ont pas vocation à être modifiés à la main.</p>
<h2>Exports</h2>
<ul class="prose">
<li><a href="corpus.json">corpus.json</a> — l'intégralité des enregistrements</li>
<li><a href="articles.csv">articles.csv</a> — un article par ligne, codage aplati</li>
</ul>
<h2>Ce qui n'est pas stocké</h2>
<p class="prose">Le texte intégral des articles n'est jamais recopié : seuls les
titres relevés, les métadonnées et les variables calculées le sont. Le validateur
refuse toute donnée qui contiendrait un corps d'article. Les mesures n'en ont
pas besoin, et la reproduction n'en serait pas licite.</p>
<p class="effectif">{len(evenements)} événement(s) dans cette version.</p>
"""


# --- Rendu léger du texte de méthode ---------------------------------------

def markdown_minimal(source: str) -> str:
    """Assez de Markdown pour un manuel de méthode, pas plus."""
    sortie, liste = [], None
    for brut in source.split("\n"):
        ligne = brut.rstrip()
        if not ligne:
            if liste:
                sortie.append(f"</{liste}>")
                liste = None
            continue
        ligne = e(ligne)
        ligne = re.sub(r"`([^`]+)`", r"<code>\1</code>", ligne)
        if ligne.startswith("### "):
            sortie.append(f"<h3>{ligne[4:]}</h3>")
        elif ligne.startswith("## "):
            sortie.append(f"<h2>{ligne[3:]}</h2>")
        elif ligne.startswith("# "):
            sortie.append(f"<h1>{ligne[2:]}</h1>")
        elif ligne.startswith("&gt; "):
            sortie.append(f"<blockquote>{ligne[5:]}</blockquote>")
        elif ligne.startswith("- "):
            if liste != "ul":
                sortie.append("<ul>")
                liste = "ul"
            sortie.append(f"<li>{ligne[2:]}</li>")
        elif re.match(r"^\d+\. ", ligne):
            if liste != "ol":
                sortie.append("<ol>")
                liste = "ol"
            sortie.append(f"<li>{ligne.split('. ', 1)[1]}</li>")
        else:
            sortie.append(f"<p>{ligne}</p>")
    if liste:
        sortie.append(f"</{liste}>")
    return f'<div class="prose">{"".join(sortie)}</div>'


# --- Exports ---------------------------------------------------------------

def exporter(evenements: list[dict], vocab: dict, dossier: Path) -> None:
    (dossier / "corpus.json").write_text(
        json.dumps(
            {"contrat": 1, "genere": datetime.now(timezone.utc).isoformat(),
             "evenements": evenements},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    colonnes = [
        "evenement", "date_fait", "type_fait", "departement", "milieu",
        "article", "media", "publication", "signes", "position_une",
        "titre_initial", "titre_actuel", "revisions", "cadre", "codeurs", "accord",
    ] + vocab["codage"]["booleens"]

    with (dossier / "articles.csv").open("w", newline="", encoding="utf-8") as f:
        plume = csv.DictWriter(f, fieldnames=colonnes)
        plume.writeheader()
        for evenement in evenements:
            for article in evenement.get("article", []):
                releves = article.get("releve", [])
                codage = article.get("codage", {})
                ligne = {
                    "evenement": evenement["id"],
                    "date_fait": evenement["fait"]["date"],
                    "type_fait": evenement["fait"]["type"],
                    "departement": evenement["fait"]["departement"],
                    "milieu": evenement["fait"]["milieu"],
                    "article": article["id"],
                    "media": article["media"],
                    "publication": article["publication"],
                    "signes": article.get("signes", ""),
                    "position_une": article.get("position_une", ""),
                    "titre_initial": releves[0]["titre"] if releves else "",
                    "titre_actuel": releves[-1]["titre"] if releves else "",
                    "revisions": max(0, len(releves) - 1),
                    "cadre": codage.get("cadre", ""),
                    "codeurs": " ".join(codage.get("codeurs", [])),
                    "accord": codage.get("accord", ""),
                }
                for variable in vocab["codage"]["booleens"]:
                    ligne[variable] = codage.get(variable, "")
                plume.writerow(ligne)


# --- Construction ----------------------------------------------------------

def main() -> int:
    vocab, medias, evenements = charger()

    if SORTIE.exists():
        shutil.rmtree(SORTIE)
    for sous in ("evenements", "medias", "donnees"):
        (SORTIE / sous).mkdir(parents=True)

    shutil.copy(RACINE / "gabarits" / "style.css", SORTIE / "style.css")

    (SORTIE / "index.html").write_text(
        page("Corpus", page_accueil(evenements, medias)), encoding="utf-8"
    )

    for evenement in evenements:
        (SORTIE / "evenements" / f"{evenement['id']}.html").write_text(
            page(evenement["id"], page_evenement(evenement, medias), 1), encoding="utf-8"
        )

    (SORTIE / "medias" / "index.html").write_text(
        page("Médias", page_medias(medias, evenements, vocab), 1), encoding="utf-8"
    )
    for media in medias.values():
        (SORTIE / "medias" / f"{media['id']}.html").write_text(
            page(media["nom"], page_media(media, evenements, vocab), 1), encoding="utf-8"
        )

    methode = (RACINE / "METHODE.md").read_text(encoding="utf-8")
    (SORTIE / "methode.html").write_text(
        page("Méthode", markdown_minimal(methode)), encoding="utf-8"
    )

    (SORTIE / "donnees" / "index.html").write_text(
        page("Données", page_donnees(evenements), 1), encoding="utf-8"
    )
    exporter(evenements, vocab, SORTIE / "donnees")

    pages = len(list(SORTIE.rglob("*.html")))
    print(f"Site construit : {pages} pages, {len(evenements)} événement(s) → {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
