#!/usr/bin/env python3
"""Collecte automatisée. Bibliothèque standard uniquement.
 
Deux modes, volontairement séparés :
 
  --releves      Revisite les articles déjà enregistrés et ajoute un relevé
                 quand le titre a changé. Pure observation, sans jugement :
                 cette écriture est automatisable sans risque.
 
  --propositions Lit les flux des médias suivis et écrit des candidats dans
                 propositions/. Rien n'entre au corpus : rattacher un article
                 à un événement est une décision, elle revient à une personne.
 
Cette séparation est le garde-fou du projet. Une machine peut constater qu'un
titre a changé ; elle ne peut pas décider qu'un article parle d'un fait donné.
"""
 
from __future__ import annotations
 
import argparse
import json
import sys
import tomllib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
 
RACINE = Path(__file__).resolve().parent.parent
EVENEMENTS = RACINE / "donnees" / "evenements"
PROPOSITIONS = RACINE / "propositions"
 
AGENT = "Observatoire/1.0 (collecte de métadonnées ; contact dans le dépôt)"
DELAI = 20
 
 
class ExtracteurTitre(HTMLParser):
    """Récupère og:title, à défaut <title>. On ne lit rien d'autre de la page."""
 
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.og: str | None = None
        self.balise: str | None = None
        self._dans_titre = False
 
    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            if a.get("property") == "og:title" and a.get("content"):
                self.og = a["content"].strip()
        elif tag == "title":
            self._dans_titre = True
 
    def handle_endtag(self, tag):
        if tag == "title":
            self._dans_titre = False
 
    def handle_data(self, data):
        if self._dans_titre and not self.balise:
            self.balise = data.strip()
 
    @property
    def titre(self) -> str | None:
        return self.og or self.balise
 
 
def recuperer(url: str) -> str | None:
    requete = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            brut = reponse.read(400_000)
        return brut.decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"  inaccessible : {url} ({exc})", file=sys.stderr)
        return None
 
 
def titre_de(url: str) -> str | None:
    page = recuperer(url)
    if page is None:
        return None
    extracteur = ExtracteurTitre()
    extracteur.feed(page)
    return extracteur.titre
 
 
def bloc_releve(horodatage: str, titre: str) -> str:
    echappe = titre.replace("\\", "\\\\").replace('"', '\\"')
    return f'\n[[article.releve]]\nhorodatage = "{horodatage}"\ntitre = "{echappe}"\n'
 
 
def inserer_releve(chemin: Path, id_article: str, horodatage: str, titre: str) -> None:
    """Insère le relevé à la fin du bloc de l'article, sans toucher au reste.
 
    L'écriture est strictement additive : aucune ligne existante n'est modifiée,
    ce qui rend la différence lisible dans l'historique du dépôt."""
    lignes = chemin.read_text(encoding="utf-8").split("\n")
    debut = next(
        (i for i, l in enumerate(lignes)
         if l.strip() == "[[article]]"
         and any(f'id = "{id_article}"' in lignes[j] for j in range(i, min(i + 4, len(lignes))))),
        None,
    )
    if debut is None:
        print(f"  article {id_article} introuvable dans {chemin.name}", file=sys.stderr)
        return
 
    fin = len(lignes)
    for i in range(debut + 1, len(lignes)):
        if lignes[i].strip() == "[[article]]":
            fin = i
            break
 
    dernier = max(
        (i for i in range(debut, fin) if lignes[i].strip() == "[[article.releve]]"),
        default=debut,
    )
    insertion = dernier
    for i in range(dernier, fin):
        if lignes[i].strip() and not lignes[i].startswith("["):
            insertion = i
        elif i > dernier and lignes[i].startswith("["):
            break
 
    lignes.insert(insertion + 1, bloc_releve(horodatage, titre).strip("\n"))
    chemin.write_text("\n".join(lignes), encoding="utf-8")
 
 
def mode_releves() -> int:
    maintenant = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    changements = 0
 
    for chemin in sorted(EVENEMENTS.glob("*.toml")):
        with chemin.open("rb") as f:
            evenement = tomllib.load(f)
        for article in evenement.get("article", []):
            releves = article.get("releve", [])
            if not releves:
                continue
            actuel = releves[-1]["titre"]
            releve = titre_de(article["url"])
            if releve is None or releve == actuel:
                continue
            print(f"  {article['id']} — titre modifié")
            print(f"    avant : {actuel}")
            print(f"    après : {releve}")
            inserer_releve(chemin, article["id"], maintenant, releve)
            changements += 1
 
    print(f"{changements} révision(s) de titre enregistrée(s).")
    return 0
 
 
def mode_propositions(limite: int) -> int:
    registre = tomllib.loads((RACINE / "donnees" / "medias.toml").read_text(encoding="utf-8"))
    connues = {
        article["url"]
        for chemin in EVENEMENTS.glob("*.toml")
        for article in tomllib.loads(chemin.read_text(encoding="utf-8")).get("article", [])
    }
 
    # Ne proposer que le neuf : les adresses déjà écrites dans un fichier de
    # propositions ne reviennent pas. L'union des fichiers reste le journal
    # complet de tout ce qui a été vu.
    PROPOSITIONS.mkdir(exist_ok=True)
    for fichier in PROPOSITIONS.glob("*.json"):
        try:
            anciennes = json.loads(fichier.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        connues |= {
            c.get("url") for c in anciennes.get("candidats", []) if c.get("url")
        }
 
    candidats = []
 
    deja_vues = set()
    for media in registre["media"]:
        adresses = [media["flux"], *media.get("flux_complementaires", [])]
        for adresse in adresses:
            flux = recuperer(adresse)
            if flux is None:
                continue
            try:
                arbre = ET.fromstring(flux)
            except ET.ParseError as exc:
                print(f"  flux illisible pour {media['id']} ({adresse}) : {exc}",
                      file=sys.stderr)
                continue
 
            for item in arbre.iter("item"):
                lien = (item.findtext("link") or "").strip()
                titre = (item.findtext("title") or "").strip()
                if not lien or lien in connues or lien in deja_vues:
                    continue
                deja_vues.add(lien)
                candidats.append({
                    "media": media["id"],
                    "url": lien,
                    "titre_releve": titre,
                    "publication_flux": (item.findtext("pubDate") or "").strip(),
                    "evenement": None,  # à renseigner par une personne
                })
                if len(candidats) >= limite:
                    break
            if len(candidats) >= limite:
                break
        if len(candidats) >= limite:
            break
 
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fichier = PROPOSITIONS / f"{horodatage}.json"
    fichier.write_text(
        json.dumps({"genere": horodatage, "candidats": candidats},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{len(candidats)} candidat(s) écrit(s) dans {fichier.relative_to(RACINE)}.")
    print("Aucun n'entre au corpus tant qu'une personne ne l'a pas rattaché à un événement.")
    return 0
 
 
def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--releves", action="store_true",
                           help="revisiter les articles connus et relever les titres")
    analyseur.add_argument("--propositions", action="store_true",
                           help="lire les flux et écrire des candidats à rattacher")
    analyseur.add_argument("--limite", type=int, default=200)
    arguments = analyseur.parse_args()
 
    if arguments.releves:
        return mode_releves()
    if arguments.propositions:
        return mode_propositions(arguments.limite)
    analyseur.print_help()
    return 1
 
 
if __name__ == "__main__":
    sys.exit(main())
 