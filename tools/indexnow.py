#!/usr/bin/env python3
"""
IndexNow : prévient Bing, Yandex, Seznam et Naver qu'une page a changé.
Un seul ping suffit, le protocole est partagé entre ces moteurs. Google n'y
participe pas : pour lui, c'est la Search Console qui fait foi.

    python3 tools/indexnow.py --changed     # les pages modifiées au dernier commit
    python3 tools/indexnow.py --all         # toutes les URLs du sitemap
    python3 tools/indexnow.py --url https://www.lesmeilleurshotelspa.fr/articles.html
    python3 tools/indexnow.py --changed --dry-run

Prérequis : le fichier <clé>.txt doit être en ligne à la racine du domaine,
c'est ce qui prouve à Bing que nous possédons le site. Le script le vérifie
avant d'envoyer quoi que ce soit.
"""

import argparse, glob, json, os, re, subprocess, sys, urllib.error, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

HOST = "www.lesmeilleurshotelspa.fr"
BASE = f"https://{HOST}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

# Le point d'entrée partagé relaie déjà aux moteurs participants, mais on notifie
# Bing en direct : c'est son index qui alimente les citations de Microsoft Copilot,
# et un relais en panne passerait autrement inaperçu.
ENDPOINTS = [
    ("IndexNow (partagé)", "https://api.indexnow.org/indexnow"),
    ("Bing et Copilot", "https://www.bing.com/indexnow"),
]

# Un User-Agent explicite est indispensable : les pare-feu applicatifs (Cloudflare
# devant ce site, entre autres) renvoient 403 à l'agent par défaut de urllib.
UA = "Meilleurs-IndexNow/1.0 (+https://www.lesmeilleurshotelspa.fr/)"

MESSAGES = {
    200: "OK, URLs acceptées.",
    202: "Accepté, la clé est en cours de validation par le moteur.",
    400: "Requête invalide (format du JSON).",
    403: "Clé refusée : le fichier <clé>.txt n'est pas accessible à la racine du domaine.",
    422: "URLs refusées : elles n'appartiennent pas à l'hôte déclaré, ou la clé ne correspond pas.",
    429: "Trop de requêtes, réessayer plus tard.",
}


def find_key():
    files = [f for f in glob.glob("*.txt") if re.fullmatch(r"[0-9a-f]{8,128}\.txt", f)]
    if not files:
        sys.exit("Aucun fichier de clé IndexNow à la racine. En générer un :\n"
                 '  K=$(python3 -c "import secrets;print(secrets.token_hex(16))"); echo -n "$K" > "$K.txt"')
    key = os.path.splitext(files[0])[0]
    if open(files[0], encoding="utf-8").read().strip() != key:
        sys.exit(f"{files[0]} doit contenir exactement la clé, sans rien d'autre.")
    return key


def key_is_online(key):
    req = urllib.request.Request(f"{BASE}/{key}.txt", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200 and r.read().decode("utf-8-sig").strip() == key
    except Exception:
        return False


def sitemap_urls():
    return [u.find(NS + "loc").text for u in ET.parse("sitemap.xml").getroot().findall(NS + "url")]


def page_to_url(path):
    """Chemin de fichier -> URL canonique déclarée dans la page."""
    if not path.endswith(".html") or not os.path.exists(path):
        return None
    m = re.search(r'<link rel="canonical" href="([^"]+)"', open(path, encoding="utf-8").read())
    return m.group(1) if m else None


def changed_urls():
    """URLs des pages touchées par le dernier commit."""
    try:
        out = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                             capture_output=True, text=True, timeout=15).stdout
    except Exception:
        sys.exit("Impossible de lire l'historique git.")
    urls = {page_to_url(p) for p in out.split()}
    return sorted(u for u in urls if u)


def submit(urls, key, dry_run=False):
    if not urls:
        print("Aucune URL à soumettre : aucune page n'a changé au dernier commit.")
        print("Pour resoumettre tout le site : npm run indexnow:all")
        return 0
    payload = {"host": HOST, "key": key, "keyLocation": f"{BASE}/{key}.txt",
               "urlList": urls[:10000]}
    print(f"{len(payload['urlList'])} URL(s) à soumettre :")
    for u in payload["urlList"]:
        print("  ", u)
    if dry_run:
        print("\n--dry-run : rien n'a été envoyé.")
        return 0

    body = json.dumps(payload).encode()
    failed = 0
    print()
    for label, endpoint in ENDPOINTS:
        req = urllib.request.Request(
            endpoint, data=body,
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": UA},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            print(f"  {label:22} échec réseau : {e}")
            failed += 1
            continue
        ok = code in (200, 202)
        print(f"  {label:22} {code} {MESSAGES.get(code, 'code inattendu')}")
        failed += 0 if ok else 1
    return 1 if failed == len(ENDPOINTS) else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Soumission IndexNow (Bing, Yandex, Seznam, Naver)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--changed", action="store_true", help="pages modifiées au dernier commit")
    g.add_argument("--all", action="store_true", help="toutes les URLs du sitemap")
    g.add_argument("--url", action="append", help="une URL précise (répétable)")
    ap.add_argument("--dry-run", action="store_true", help="afficher sans envoyer")
    a = ap.parse_args()

    key = find_key()
    print(f"Clé IndexNow : {key}")

    if not a.dry_run and not key_is_online(key):
        sys.exit(f"\n{BASE}/{key}.txt n'est pas accessible en ligne.\n"
                 "Déployer le site avant de soumettre : sans ce fichier, Bing refuse la clé (403).")

    urls = sitemap_urls() if a.all else (a.url if a.url else changed_urls())
    sys.exit(submit(urls, key, a.dry_run))
