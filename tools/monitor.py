#!/usr/bin/env python3
"""
Contrôle de santé du site en production.

    npm run monitor            # une passe sur toutes les URLs du sitemap
    npm run monitor -- --watch # sonde en continu, s'arrête au premier incident

À lancer quand un outil tiers signale une erreur : il dit en quelques secondes
si le problème est réel, et de quel côté il se situe.

Les codes 52x sont ceux de Cloudflare et désignent tous l'origine (Railway) :
  520 réponse invalide · 521 origine injoignable · 522 délai de connexion
  523 origine introuvable · 524 origine trop lente (plus de 100 s)
Un 52x isolé pendant un redéploiement est normal ; répété, il faut regarder
les journaux Railway.
"""

import argparse, concurrent.futures, sys, time
import urllib.error, urllib.request
import xml.etree.ElementTree as ET

BASE = "https://www.lesmeilleurshotelspa.fr"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
UA = "Meilleurs-Monitor/1.0 (+https://www.lesmeilleurshotelspa.fr/)"

CF = {
    520: "Cloudflare : réponse invalide de l'origine",
    521: "Cloudflare : origine injoignable (serveur arrêté ou pare-feu)",
    522: "Cloudflare : délai de connexion à l'origine dépassé",
    523: "Cloudflare : origine introuvable (DNS ou routage)",
    524: "Cloudflare : origine trop lente, pas de réponse en 100 s",
}


def get(url, timeout=110):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, time.time() - t0, None
    except urllib.error.HTTPError as e:
        return e.code, time.time() - t0, None
    except Exception as e:
        return None, time.time() - t0, str(e)


def sitemap_urls():
    code, _, err = None, None, None
    try:
        req = urllib.request.Request(f"{BASE}/sitemap.xml", headers={"User-Agent": UA})
        xml = urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        sys.exit(f"sitemap.xml injoignable : {e}")
    return [u.find(NS + "loc").text for u in ET.fromstring(xml).findall(NS + "url")]


def pass_once(urls, verbose=True):
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(lambda u: (u,) + get(u), urls))
    bad = [r for r in res if r[1] != 200]
    times = sorted(r[2] for r in res)
    if verbose:
        print(f"  {len(res) - len(bad)}/{len(res)} pages en 200 · "
              f"médiane {times[len(times) // 2]:.2f}s · max {times[-1]:.2f}s")
        for u, code, t, err in bad:
            label = CF.get(code, "") or (err or "")
            print(f"  ✗ {code or 'ERR'} {u}" + (f"\n      {label}" if label else ""))
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Contrôle de santé de lesmeilleurshotelspa.fr")
    ap.add_argument("--watch", action="store_true", help="sonder en continu jusqu'au premier incident")
    ap.add_argument("--interval", type=int, default=30, help="secondes entre deux passes (30 par défaut)")
    a = ap.parse_args()

    urls = sitemap_urls()

    # L'apex doit rediriger vers www : c'est l'URL que testent la plupart des
    # outils tiers, et une origine mal configurée n'y répond pas.
    code, t, err = get("https://lesmeilleurshotelspa.fr/", timeout=60)
    etat = "OK" if code in (200, 301, 308) else "PROBLÈME"
    print(f"Apex sans www : {code or err} ({t:.2f}s) {etat}")
    if code in CF:
        print(f"  {CF[code]}")

    if not a.watch:
        print(f"Sitemap : {len(urls)} URLs")
        sys.exit(1 if pass_once(urls) else 0)

    print(f"Sitemap : {len(urls)} URLs · sondage toutes les {a.interval}s, Ctrl+C pour arrêter")
    n = 0
    while True:
        n += 1
        print(f"[{time.strftime('%H:%M:%S')}] passe {n}")
        if pass_once(urls):
            sys.exit("Incident détecté, arrêt.")
        time.sleep(a.interval)
