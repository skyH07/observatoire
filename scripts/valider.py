#!/usr/bin/env python3
"""Vérifie que les données respectent le contrat décrit dans schema/.

Ce script est le garde-fou du projet. Il tourne à chaque proposition de
modification et refuse toute donnée non conforme. Il n'utilise que la
bibliothèque standard : aucune dépendance à installer, aucune à maintenir.

Usage :  python3 scripts/valider.py
Sortie :  0 si tout est conforme, 1 sinon.
"""

from __future__ import annotations

import re
import sys
import tomllib
from datetime import date, datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_EVENEMENTS = RACINE / "donnees" / "evenements"

MOTIF_EVENEMENT = re.compile(r"^EVT-\d{4}-\d{4}$")
MOTIF_ARTICLE = re.compile(r"^ART-\d{4}$")

CHAMPS_FAIT = ("date", "type", "departement", "milieu", "victimes", "resume")
CHAMPS_ARTICLE = ("id", "media", "url", "archive", "publication")

LONGUEUR_RESUME_MAX = 300
CODEURS_MINIMUM = 2


class Journal:
    """Collecte les erreurs pour tout signaler d'un coup."""

    def __init__(self) -> None:
        self.erreurs: list[str] = []
        self.avertissements: list[str] = []

    def erreur(self, ou: str, message: str) -> None:
        self.erreurs.append(f"{ou} : {message}")

    def avertir(self, ou: str, message: str) -> None:
        self.avertissements.append(f"{ou} : {message}")


def lire_toml(chemin: Path) -> dict:
    with chemin.open("rb") as f:
        return tomllib.load(f)


def analyser_date(valeur) -> date | None:
    if isinstance(valeur, date) and not isinstance(valeur, datetime):
        return valeur
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, str):
        try:
            return date.fromisoformat(valeur)
        except ValueError:
            return None
    return None


def analyser_horodatage(valeur) -> datetime | None:
    if isinstance(valeur, datetime):
        return valeur
    if isinstance(valeur, str):
        try:
            return datetime.fromisoformat(valeur.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def chercher_cles_interdites(noeud, interdits: set[str], chemin: str = "") -> list[str]:
    """Empêche la réapparition du texte intégral, qui ferait basculer le
    projet dans la contrefaçon et n'est utile à aucune mesure."""
    trouvees: list[str] = []
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            ici = f"{chemin}.{cle}" if chemin else cle
            if cle.lower() in interdits:
                trouvees.append(ici)
            trouvees += chercher_cles_interdites(valeur, interdits, ici)
    elif isinstance(noeud, list):
        for i, element in enumerate(noeud):
            trouvees += chercher_cles_interdites(element, interdits, f"{chemin}[{i}]")
    return trouvees


def valider_article(article, ou, vocab, medias, ids_articles, journal) -> None:
    identifiant = article.get("id", "?")
    ou = f"{ou} / {identifiant}"

    for champ in CHAMPS_ARTICLE:
        if champ not in article:
            journal.erreur(ou, f"champ obligatoire manquant : {champ}")

    if not MOTIF_ARTICLE.match(str(identifiant)):
        journal.erreur(ou, "identifiant attendu au format ART-0000")
    elif identifiant in ids_articles:
        journal.erreur(ou, f"identifiant déjà utilisé dans {ids_articles[identifiant]}")
    else:
        ids_articles[identifiant] = ou

    media = article.get("media")
    if media not in medias:
        journal.erreur(ou, f"média « {media} » absent de donnees/medias.toml")

    if not article.get("archive"):
        journal.erreur(ou, "lien d'archive obligatoire : sans copie figée, la mesure "
                           "n'est pas reproductible")

    publication = analyser_horodatage(article.get("publication"))
    if publication is None:
        journal.erreur(ou, "horodatage de publication illisible")
    elif media in medias:
        depuis = analyser_date(medias[media].get("suivi_depuis"))
        if depuis and publication.date() < depuis:
            journal.erreur(ou, "publication antérieure au début du suivi de ce média")

    releves = article.get("releve", [])
    if not releves:
        journal.erreur(ou, "au moins un relevé de titre est obligatoire")
    precedent = None
    for i, releve in enumerate(releves):
        if not releve.get("titre"):
            journal.erreur(ou, f"relevé {i + 1} sans titre")
        horodatage = analyser_horodatage(releve.get("horodatage"))
        if horodatage is None:
            journal.erreur(ou, f"relevé {i + 1} : horodatage illisible")
        elif precedent and horodatage < precedent:
            journal.erreur(ou, f"relevé {i + 1} antérieur au précédent : les relevés "
                               "s'ajoutent, ils ne se réordonnent pas")
        else:
            precedent = horodatage

    codage = article.get("codage")
    if codage is None:
        journal.avertir(ou, "aucun codage : l'article ne sera pas comptabilisé dans les mesures")
        return

    if codage.get("cadre") not in vocab["codage"]["cadre"]:
        journal.erreur(ou, f"cadre « {codage.get('cadre')} » hors vocabulaire")

    for booleen in vocab["codage"]["booleens"]:
        if booleen not in codage:
            journal.erreur(ou, f"variable de codage manquante : {booleen}")
        elif not isinstance(codage[booleen], bool):
            journal.erreur(ou, f"{booleen} doit valoir true ou false")

    codeurs = codage.get("codeurs", [])
    if len(set(codeurs)) < CODEURS_MINIMUM:
        journal.erreur(ou, f"{CODEURS_MINIMUM} codeurs distincts minimum, "
                           f"{len(set(codeurs))} déclaré(s)")
    if not isinstance(codage.get("accord"), bool):
        journal.erreur(ou, "champ `accord` obligatoire (true ou false)")
    elif codage["accord"] is False and not codage.get("note_desaccord"):
        journal.erreur(ou, "un désaccord doit être motivé dans `note_desaccord`")


def valider_evenement(chemin, vocab, medias, ids_evenements, ids_articles, journal) -> None:
    ou = chemin.name
    try:
        donnees = lire_toml(chemin)
    except tomllib.TOMLDecodeError as exc:
        journal.erreur(ou, f"TOML illisible : {exc}")
        return

    interdites = chercher_cles_interdites(donnees, set(vocab["interdits"]["cles"]))
    for cle in interdites:
        journal.erreur(ou, f"clé interdite « {cle} » : on ne stocke pas le texte intégral")

    if donnees.get("contrat") != 1:
        journal.erreur(ou, "version de contrat inconnue ou absente")

    identifiant = donnees.get("id", "")
    if not MOTIF_EVENEMENT.match(str(identifiant)):
        journal.erreur(ou, "identifiant attendu au format EVT-0000-0000")
    if identifiant != chemin.stem:
        journal.erreur(ou, "l'identifiant doit être identique au nom du fichier")
    if identifiant in ids_evenements:
        journal.erreur(ou, "identifiant déjà utilisé")
    ids_evenements.add(identifiant)

    fait = donnees.get("fait", {})
    for champ in CHAMPS_FAIT:
        if champ not in fait:
            journal.erreur(ou, f"champ obligatoire manquant : fait.{champ}")

    if fait.get("type") not in vocab["fait"]["type"]:
        journal.erreur(ou, f"type de fait « {fait.get('type')} » hors vocabulaire")
    if fait.get("milieu") not in vocab["fait"]["milieu"]:
        journal.erreur(ou, f"milieu « {fait.get('milieu')} » hors vocabulaire")
    if analyser_date(fait.get("date")) is None:
        journal.erreur(ou, "date du fait illisible")
    if len(str(fait.get("resume", ""))) > LONGUEUR_RESUME_MAX:
        journal.erreur(ou, f"résumé de plus de {LONGUEUR_RESUME_MAX} caractères")

    sources = fait.get("source_primaire", [])
    if not sources:
        journal.erreur(ou, "au moins une source primaire hors presse est obligatoire : "
                           "un événement connu par la seule presse ne peut pas servir "
                           "à mesurer une omission")
    for source in sources:
        if source.get("type") not in vocab["source_primaire"]["type"]:
            journal.erreur(ou, f"source « {source.get('type')} » hors vocabulaire")
        if not source.get("reference"):
            journal.erreur(ou, "source primaire sans référence vérifiable")

    for article in donnees.get("article", []):
        valider_article(article, ou, vocab, medias, ids_articles, journal)


def main() -> int:
    journal = Journal()
    vocab = lire_toml(RACINE / "schema" / "vocabulaire.toml")
    registre = lire_toml(RACINE / "donnees" / "medias.toml")
    medias = {m["id"]: m for m in registre.get("media", [])}

    fichiers = sorted(DOSSIER_EVENEMENTS.glob("*.toml"))
    if not fichiers:
        print("Aucun événement à valider.", file=sys.stderr)
        return 1

    ids_evenements: set[str] = set()
    ids_articles: dict[str, str] = {}
    for chemin in fichiers:
        valider_evenement(chemin, vocab, medias, ids_evenements, ids_articles, journal)

    for message in journal.avertissements:
        print(f"  avertissement  {message}")
    for message in journal.erreurs:
        print(f"  ERREUR         {message}", file=sys.stderr)

    total = f"{len(fichiers)} événement(s), {len(ids_articles)} article(s)"
    if journal.erreurs:
        print(f"\nÉchec : {len(journal.erreurs)} erreur(s) sur {total}.", file=sys.stderr)
        return 1
    print(f"\nConforme : {total}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
