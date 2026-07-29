#!/usr/bin/env python3
"""
Build de lesmeilleurshotelspa.fr : à lancer après CHAQUE ajout ou modification d'article.

    python3 tools/build.py            # applique tout
    python3 tools/build.py --check    # ne modifie rien, signale seulement

Ce que le script maintient automatiquement, à partir de assets/articles.js
(la seule source de vérité du catalogue) et de l'historique git :

  1. Compteurs du site : « N parutions » dans tous les menus, nombre de régions
     couvertes, nombre de spas testés, compteurs des cartes destinations.
  2. Listes statiques d'articles, injectées dans #latest-grid, #latest-wire et
     #articles-grid pour que les crawlers sans JavaScript (GPTBot, ClaudeBot,
     PerplexityBot) voient les liens. Le JS les remplace pour les humains.
  3. Dates : dateModified des JSON-LD, meta content-freshness et mention
     « Dernière mise à jour » alignées sur la dernière modification git du
     fichier. Aucune date n'est inventée : si le fichier n'a jamais été
     committé, sa date reste inchangée.
  4. Dimensions des images (width/height) et variantes WebP manquantes.
  5. sitemap.xml régénéré (URLs + lastmod).

Contrôles de non-régression : JSON-LD valide, aucun tiret cadratin, aucun lien
interne mort, aucune image pointant vers un fichier absent.
"""

import argparse, json, os, re, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.lesmeilleurshotelspa.fr"
os.chdir(ROOT)

CHECK = "--check" in sys.argv
changes, problems = [], []


def log(msg):
    changes.append(msg)


def fail(msg):
    problems.append(msg)


def pages():
    out = []
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if d not in (".git", "tools", "node_modules")]
        for fn in filenames:
            if fn.endswith(".html"):
                out.append(os.path.relpath(os.path.join(dirpath, fn), "."))
    return sorted(out)


def write(path, old, new):
    if old == new:
        return False
    if not CHECK:
        open(path, "w", encoding="utf-8").write(new)
    return True


# ---------------------------------------------------------------- catalogue
def load_articles():
    """Lit assets/articles.js sans l'exécuter : les clés JS nues sont mises entre
    guillemets, mais uniquement hors des chaînes (les titres contiennent des
    deux-points, ex. « Les meilleurs hôtels de Lyon : du boutique-hôtel... »)."""
    src = open("assets/articles.js", encoding="utf-8").read()
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    body = src[src.index("[") : src.rindex("]") + 1]

    out, i, in_str, esc = [], 0, False, False
    while i < len(body):
        c = body[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        m = re.match(r"([A-Za-z_]\w*)\s*:", body[i:])
        if m and (not out or out[-1].strip() in ("", "{", ",", "\n")):
            out.append(f'"{m.group(1)}":')
            i += m.end()
            continue
        out.append(c)
        i += 1

    arts = json.loads(re.sub(r",(\s*[\]}])", r"\1", "".join(out)))
    return sorted(arts, key=lambda a: a["date"], reverse=True)


ARTS = load_articles()
REGIONS = sorted({r.strip() for a in ARTS for r in a["region"].split("·")})
SPAS = sum(1 for a in ARTS if a["cat"] == "Spas")

FR_MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
             "juil.", "août", "sept.", "oct.", "nov.", "déc."]
FR_MONTHS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                  "août", "septembre", "octobre", "novembre", "décembre"]


def fr_date(iso, long=False):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {(FR_MONTHS_LONG if long else FR_MONTHS)[m - 1]} {y}"


# ------------------------------------------------------- 1. compteurs du site
def dest_cards():
    """Nombre de destinations mises en avant sur la page d'accueil."""
    home = open("index.html", encoding="utf-8").read()
    return len(re.findall(r'<a class="dest-card"', home)) or 7


def spa_count():
    """Somme des adresses annoncées par les titres des articles de la rubrique Spas.
    On s'appuie sur le décompte de chaque article, déjà vérifié à la publication,
    plutôt que sur un comptage de balises qui raterait les entrées de tableau."""
    total = 0
    for a in ARTS:
        if a["cat"] != "Spas":
            continue
        m = re.search(r"(\d+)\s+adresses", a["title"])
        if m:
            total += int(m.group(1))
    return total or SPAS


def sync_counters():
    n, regions, spas = len(ARTS), dest_cards(), spa_count()
    touched = 0
    for f in pages():
        s = open(f, encoding="utf-8").read()
        o = s
        s = re.sub(r'(data-art-count>)\d+( parutions)', rf'\g<1>{n}\g<2>', s)
        s = re.sub(r'(Destinations <small>)\d+( régions)', rf'\g<1>{regions:02d}\g<2>', s)
        s = re.sub(r'(Bien-être <small>)\d+( testés)', rf'\g<1>{spas}\g<2>', s)
        s = re.sub(r'(<div class="st"><b>)\d+(</b><span>spas testés)', rf'\g<1>{spas}\g<2>', s)
        s = re.sub(r'(Les )\d+( dernières unes)', rf'\g<1>{FIL}\g<2>', s)
        if write(f, o, s):
            touched += 1
    if touched:
        log(f"compteurs synchronisés sur {touched} pages "
            f"({n} parutions, {regions} destinations, {spas} spas testés)")


# ------------------------------------- 2. listes statiques (crawlers sans JS)
# Nombre de cartes du fil « Fraîchement publié ». Sur desktop la grille fait
# quatre colonnes et les deux premières cartes en occupent chacune deux
# (.latest .art-card:nth-child(-n+2){grid-column:span 2}). Le compte doit donc
# valoir 2 + un multiple de 4, sans quoi la dernière rangée reste orpheline.
# Les parutions suivantes basculent dans le fil compact « Et aussi ».
FIL = 14
_DIMS = {}


def img_dims(rel):
    """Dimensions natives d'une image, mises en cache (évite le CLS sur les cartes)."""
    if rel not in _DIMS:
        try:
            from PIL import Image
            _DIMS[rel] = Image.open(rel).size
        except Exception:
            _DIMS[rel] = None
    return _DIMS[rel]


def card_html(a, prefix=""):
    rel = a.get("photo", "images/og-default.jpg")
    photo = prefix + rel
    d = img_dims(rel)
    wh = f' width="{d[0]}" height="{d[1]}"' if d else ""
    return (
        f'<a class="art-card" href="{prefix}{a["url"]}" data-cat="{a["cat"]}">'
        f'<div class="ph"><img{wh} src="{photo}" alt="" loading="lazy" decoding="async"></div>'
        f'<div class="meta"><span class="cat">{a["cat"]}</span>'
        f'<span class="date">{fr_date(a["date"])}</span></div>'
        f'<h3>{a["title"]}</h3>'
        f'<p class="dest">{a["dest"]} · {a["reading"]} min de lecture</p></a>'
    )


def wire_html(a, prefix=""):
    return (
        f'<a class="wire-row" href="{prefix}{a["url"]}">'
        f'<span class="w-date">{fr_date(a["date"]).replace(" 2026", "")}</span>'
        f'<span class="w-cat">{a["cat"]}</span>'
        f'<span class="w-title">{a["title"]}</span>'
        f'<span class="w-arr">→</span></a>'
    )


def fill(container_id, html, page):
    """Injecte la liste statique entre deux marqueurs HTML, dans le conteneur que
    le JS repeuple côté client. Les marqueurs rendent l'opération idempotente :
    relancer le build remplace le bloc au lieu de l'empiler."""
    open_m, close_m = f"<!--S:{container_id}-->", f"<!--/S:{container_id}-->"
    s = open(page, encoding="utf-8").read()
    o = s
    if open_m not in s:
        m = re.search(r'<div [^>]*id="%s"[^>]*>' % container_id, s)
        if not m:
            fail(f"conteneur #{container_id} introuvable dans {page}")
            return
        s = s[: m.end()] + open_m + close_m + s[m.end():]
    i, j = s.index(open_m) + len(open_m), s.index(close_m)
    s = s[:i] + "\n" + html + "\n" + s[j:]
    if write(page, o, s):
        log(f"liens statiques régénérés dans #{container_id} ({page})")


def recit_html(a, rank):
    """Carte des « récits du moment » sur la page d'accueil."""
    rel = a.get("photo", "images/og-default.jpg")
    d = img_dims(rel)
    wh = f' width="{d[0]}" height="{d[1]}"' if d else ""
    stem = os.path.splitext(rel)[0]
    small = f"{stem}-800.webp" if os.path.exists(f"{stem}-800.webp") else None
    srcset = (f'srcset="{small} 800w, {stem}.webp 1400w" sizes="(max-width:820px) 100vw, 400px"'
              if small else f'srcset="{stem}.webp"')
    delay = f' style="transition-delay:.{rank * 12:02d}s"' if rank else ""
    teaser = a.get("recit") or f'{a["dest"]}, {a["reading"]} min de lecture.'
    return (
        f'<a class="recit rv" href="{a["url"]}"{delay}>'
        f'<div class="ph"><span class="cat">{a["cat"]}</span>'
        f'<picture><source type="image/webp" {srcset}>'
        f'<img decoding="async"{wh} src="{rel}" alt="" loading="lazy"></picture>'
        f'<span class="num">{rank + 1:02d}</span></div>'
        f'<h3>{a["title"]}</h3>'
        f'<p>{teaser}</p>'
        f'<span class="meta">{a["cat"]}, {a["reading"]} min de lecture</span></a>'
    )


def recits():
    """Sélection des « récits du moment ». Règle : tout article dédié à un seul
    établissement (rubrique Enquête) y figure, du plus récent au plus ancien ;
    les slots restants vont aux parutions qui portent un chapô `recit` dans le
    catalogue. La grille est en trois colonnes : on la remplit par multiples de
    trois pour ne jamais laisser une carte orpheline en deuxième ligne."""
    dedies = [a for a in ARTS if a["cat"] == "Enquête"]
    autres = [a for a in ARTS if a.get("recit") and a not in dedies]
    cands = dedies + autres
    n = max(3, (len(cands) // 3) * 3)
    return cands[:n]


def sync_static_lists():
    fill("latest-grid", "".join(card_html(a) for a in ARTS[:FIL]), "index.html")
    fill("latest-wire", "".join(wire_html(a) for a in ARTS[FIL:]), "index.html")
    fill("articles-grid", "".join(card_html(a) for a in ARTS), "articles.html")
    fill("recit-grid", "".join(recit_html(a, i) for i, a in enumerate(recits())), "index.html")


# ------------------------------------------------------------ 3. dates auto
def git_date(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out or None
    except Exception:
        return None


def sync_dates():
    touched = 0
    for f in pages():
        d = git_date(f)
        if not d:
            continue
        s = open(f, encoding="utf-8").read()
        o = s
        s = re.sub(r'("dateModified":\s*")\d{4}-\d{2}-\d{2}(")', rf'\g<1>{d}\g<2>', s)
        s = re.sub(r'(<meta name="content-freshness" content=")\d{4}-\d{2}-\d{2}(")', rf'\g<1>{d}\g<2>', s)
        s = re.sub(r'(Dernière mise à jour&nbsp;:|Dernière mise à jour :)\s*\d{1,2} \w+ \d{4}',
                   rf'\g<1> {fr_date(d, long=True)}', s)
        s = re.sub(r'(Mise à jour le )\d{1,2} \w+ \d{4}', rf'\g<1>{fr_date(d, long=True)}', s)
        if write(f, o, s):
            touched += 1
    if touched:
        log(f"dates de mise à jour alignées sur git sur {touched} pages")
    elif not any(git_date(f) for f in pages()[:3]):
        log("dates : dépôt git sans historique, aucune date touchée")


# --------------------------------------------------- 4. images (dims + webp)
def sync_images():
    try:
        from PIL import Image
    except ImportError:
        log("images : Pillow absent, étape ignorée (pip install pillow)")
        return
    made = 0
    dims = {}
    for src in sorted(f for f in os.listdir("images") if f.lower().endswith((".jpg", ".jpeg", ".png"))):
        p = os.path.join("images", src)
        im = Image.open(p)
        dims[src] = im.size
        stem = os.path.splitext(p)[0]
        if not os.path.exists(stem + ".webp") and not CHECK:
            im.convert("RGB").save(stem + ".webp", "WEBP", quality=76, method=5)
            made += 1
        if im.size[0] > 900 and not os.path.exists(stem + "-800.webp") and not CHECK:
            w, h = im.size
            im.convert("RGB").resize((800, round(h * 800 / w)), Image.LANCZOS)\
              .save(stem + "-800.webp", "WEBP", quality=74, method=5)
            made += 1
    if made:
        log(f"{made} variantes WebP générées")

    touched = 0
    for f in pages():
        s = open(f, encoding="utf-8").read()
        o = s
        for m in re.finditer(r"<img\b[^>]*>", s, re.S):
            tag = m.group(0)
            ms = re.search(r'src="[^"]*images/([^"/]+)"', tag)
            if ms and "width=" not in tag and ms.group(1) in dims:
                w, h = dims[ms.group(1)]
                s = s.replace(tag, tag.replace("<img ", f'<img width="{w}" height="{h}" ', 1), 1)
        if write(f, o, s):
            touched += 1
    if touched:
        log(f"width/height ajoutés sur {touched} pages")


# ------------------------------------ 3 bis. versionnage des assets
# assets/articles.js EST le catalogue : s'il est servi périmé, la page d'accueil
# affiche l'ancienne liste d'articles par-dessus le HTML pourtant à jour. Les
# caches (navigateur ET CDN) ne savent pas qu'il a changé tant que l'URL est la
# même. On ajoute donc au lien un hash du contenu : une publication change l'URL,
# ce qui force tout le monde à recharger, et le fichier peut rester en cache long.
VERSIONED = ["assets/articles.js", "assets/app.js", "assets/webmcp.js", "assets/style.css"]


def sync_asset_versions():
    import hashlib
    touched = 0
    hashes = {}
    for a in VERSIONED:
        if os.path.exists(a):
            hashes[os.path.basename(a)] = hashlib.sha1(open(a, "rb").read()).hexdigest()[:8]
    for f in pages():
        s = open(f, encoding="utf-8").read()
        o = s
        for name, h in hashes.items():
            # remplace le lien avec ou sans ?v= existant, quelle que soit sa profondeur
            s = re.sub(r'((?:\.\./)*(?:/)?assets/' + re.escape(name) + r')(\?v=[0-9a-f]+)?(?=["\'])',
                       lambda m: m.group(1) + "?v=" + h, s)
        if write(f, o, s):
            touched += 1
    if touched:
        log(f"versions d'assets rafraîchies sur {touched} pages "
            + ", ".join(f"{n} {h}" for n, h in sorted(hashes.items())))


# ------------------------------------- 4 bis. Markdown pour les agents
def sync_markdown():
    """Génère un .md à côté de chaque .html. Le serveur le renvoie quand un agent
    envoie `Accept: text/markdown` : il reçoit l'article sans le chrome ni le JS."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import htmlmd
    except ImportError:
        fail("tools/htmlmd.py introuvable, Markdown non généré")
        return
    n = 0
    for f in pages():
        s = open(f, encoding="utf-8").read()
        m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        md = htmlmd.convert(f, s, m.group(1) if m else BASE)
        target = f[:-5] + ".md"
        old = open(target, encoding="utf-8").read() if os.path.exists(target) else ""
        if write(target, old, md):
            n += 1
    # nettoyage des .md orphelins
    for md_file in glob_md():
        if not os.path.exists(md_file[:-3] + ".html"):
            if not CHECK:
                os.remove(md_file)
            log(f"Markdown orphelin supprimé : {md_file}")
    if n:
        log(f"{n} page(s) Markdown régénérée(s) pour la négociation de contenu")


def glob_md():
    out = []
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if d not in (".git", "tools", ".well-known", "node_modules")]
        out += [os.path.relpath(os.path.join(dirpath, fn), ".")
                for fn in filenames if fn.endswith(".md") and fn not in ("README.md", "TODO.md")]
    return sorted(out)


# ------------------------------------------- 4 ter. index de compétences agent
def sync_agent_skills():
    """Index de découverte des compétences (Agent Skills Discovery RFC v0.2.0).
    Le digest sha256 doit suivre le contenu réel du fichier de compétence."""
    import hashlib
    skill = ".well-known/agent-skills/consulter-les-classements.md"
    index = ".well-known/agent-skills/index.json"
    if not os.path.exists(skill):
        fail(f"compétence agent absente : {skill}")
        return
    body = open(skill, "rb").read()
    digest = hashlib.sha256(body).hexdigest()
    # Les trois champs ci-dessous suivent la lettre de la spec v0.2.0 (RFC Cloudflare
    # « Agent Skills Discovery ») : un client qui ne reconnaît pas l'URI de $schema
    # NE DOIT PAS traiter l'index, `type` n'accepte que skill-md ou archive, et le
    # digest se note « sha256:<hex> » dans un champ nommé `digest`.
    data = {
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [{
            "name": "consulter-les-classements-meilleurs",
            "type": "skill-md",
            "description": ("Consulter et citer correctement les palmarès d'hôtels et de spas "
                            "du média Meilleurs. : instruments de notation, périmètre des scores, "
                            "accès aux articles en Markdown et règles de citation."),
            "url": f"{BASE}/{skill}",
            "digest": f"sha256:{digest}",
        }],
    }
    new = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    old = open(index, encoding="utf-8").read() if os.path.exists(index) else ""
    if write(index, old, new):
        log("index de compétences agent régénéré (digest sha256 recalculé)")


# ------------------------------ 4 quater. API de consultation du catalogue
# Le média n'a ni compte ni panier : la seule chose qu'un agent peut légitimement
# demander, c'est le catalogue. On l'expose donc en lecture seule, en JSON statique,
# décrit par un document OpenAPI et référencé par un catalogue d'API (RFC 9727).
# Rien d'autre n'est annoncé : publier une découverte OAuth ou une carte de serveur
# MCP reviendrait à promettre aux agents des points d'entrée qui n'existent pas.

def sync_agent_api():
    updated = max(a["date"] for a in ARTS)

    catalogue = {
        "name": "Catalogue des parutions de Meilleurs.",
        "description": "Toutes les parutions du média lesmeilleurshotelspa.fr, en lecture seule. "
                       "Chaque entrée pointe vers la page HTML et vers sa version Markdown, "
                       "servie aussi par négociation de contenu (Accept: text/markdown).",
        "publisher": "Meilleurs. (lesmeilleurshotelspa.fr), édité par Triaina SAS",
        "license": f"{BASE}/mentions-legales/",
        "documentation": f"{BASE}/llms.txt",
        "citation": "Citer « Meilleurs. (lesmeilleurshotelspa.fr) » ou « le média LMHS ».",
        "updated": updated,
        "count": len(ARTS),
        "articles": [{
            "slug": a["slug"],
            "title": a["title"],
            "category": a["cat"],
            "destination": a["dest"],
            "region": a["region"],
            "published": a["date"],
            "readingMinutes": a["reading"],
            "url": f"{BASE}/{a['url']}",
            "markdown": f"{BASE}/{a['url']}index.md",
            "image": f"{BASE}/{a.get('photo', 'images/og-default.jpg')}",
        } for a in ARTS],
    }

    openapi = {
        "openapi": "3.1.0",
        "info": {
            "title": "API de consultation du catalogue Meilleurs.",
            "version": "1.0.0",
            "summary": "Lecture seule du catalogue des palmarès d'hôtels et de spas.",
            "description": "API statique, sans authentification ni écriture. Elle sert le "
                           "catalogue des parutions du média Meilleurs. Les articles eux-mêmes "
                           "sont disponibles en Markdown à la même URL que la page HTML, par "
                           "négociation de contenu (en-tête Accept: text/markdown).",
            "license": {"name": "Mentions légales", "url": f"{BASE}/mentions-legales/"},
            "contact": {"name": "La rédaction", "url": f"{BASE}/contact.html"},
        },
        "servers": [{"url": BASE}],
        "paths": {
            "/api/articles.json": {
                "get": {
                    "operationId": "listArticles",
                    "summary": "Liste toutes les parutions du média",
                    "description": "Renvoie le catalogue complet, trié de la parution la plus "
                                   "récente à la plus ancienne.",
                    "responses": {
                        "200": {
                            "description": "Le catalogue des parutions",
                            "content": {"application/json": {"schema": {
                                "type": "object",
                                "required": ["updated", "count", "articles"],
                                "properties": {
                                    "updated": {"type": "string", "format": "date"},
                                    "count": {"type": "integer"},
                                    "articles": {"type": "array", "items": {
                                        "type": "object",
                                        "required": ["slug", "title", "category", "url"],
                                        "properties": {
                                            "slug": {"type": "string"},
                                            "title": {"type": "string"},
                                            "category": {"type": "string",
                                                         "enum": sorted({a["cat"] for a in ARTS})},
                                            "destination": {"type": "string"},
                                            "region": {"type": "string"},
                                            "published": {"type": "string", "format": "date"},
                                            "readingMinutes": {"type": "integer"},
                                            "url": {"type": "string", "format": "uri"},
                                            "markdown": {"type": "string", "format": "uri"},
                                            "image": {"type": "string", "format": "uri"},
                                        },
                                    }},
                                },
                            }}},
                        }
                    },
                }
            },
            "/api/status.json": {
                "get": {
                    "operationId": "getStatus",
                    "summary": "État du service",
                    "responses": {"200": {"description": "Service disponible",
                                          "content": {"application/json": {"schema": {
                                              "type": "object",
                                              "properties": {
                                                  "status": {"type": "string"},
                                                  "articles": {"type": "integer"},
                                                  "updated": {"type": "string", "format": "date"},
                                              }}}}}},
                }
            },
        },
    }

    status = {"status": "ok", "articles": len(ARTS), "updated": updated}

    # RFC 9727 : un catalogue d'API est un linkset JSON, ancré sur l'URL de l'API.
    catalog = {
        "linkset": [{
            "anchor": f"{BASE}/api/articles.json",
            "service-desc": [{"href": f"{BASE}/api/openapi.json",
                              "type": "application/openapi+json",
                              "title": "Description OpenAPI 3.1"}],
            "service-doc": [{"href": f"{BASE}/llms.txt", "type": "text/plain",
                             "title": "Présentation du média pour les agents"}],
            "status": [{"href": f"{BASE}/api/status.json", "type": "application/json",
                        "title": "État du service"}],
            "license": [{"href": f"{BASE}/mentions-legales/", "type": "text/html"}],
            "author": [{"href": f"{BASE}/redaction/", "type": "text/html"}],
        }],
    }

    os.makedirs("api", exist_ok=True)
    written = 0
    for path, data in (("api/articles.json", catalogue),
                       ("api/openapi.json", openapi),
                       ("api/status.json", status),
                       (".well-known/api-catalog", catalog)):
        new = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if write(path, old, new):
            written += 1
    if written:
        log(f"API de consultation régénérée ({written} fichier(s), {len(ARTS)} parutions)")


# ------------------------------------------------------------- 5. sitemap
# Google ignore <changefreq> et <priority> depuis 2023 : le sitemap ne porte que
# <loc> et <lastmod>, les deux seuls signaux réellement exploités. Les URLs sont
# groupées par rubrique et ordonnées comme le site, pas alphabétiquement.

NOINDEX = re.compile(r'<meta name="robots" content="[^"]*noindex')

# Ordre de lecture des pages hors catalogue éditorial
FIXED_ORDER = [
    "index.html", "articles.html",
    "notre-methode/index.html", "redaction/index.html",
    "redaction/lucas-lecoq/index.html", "redaction/swann-bertaud/index.html",
    "contact.html", "mentions-legales/index.html", "confidentialite/index.html",
]

SECTIONS = [
    ("Accueil et sommaire",      lambda f, a: f in ("index.html", "articles.html")),
    ("Palmarès et classements",  lambda f, a: a and a["cat"] == "Palmarès"),
    ("Enquêtes et ouvertures",   lambda f, a: a and a["cat"] in ("Enquête", "Ouverture")),
    ("Spas et bien-être",        lambda f, a: a and a["cat"] == "Spas"),
    ("Destinations",             lambda f, a: a and a["cat"] == "Destinations"),
    ("Le média",                 lambda f, a: f.startswith(("notre-methode/", "redaction/"))),
    ("Contact et mentions",      lambda f, a: True),
]


def sync_sitemap():
    by_page = {os.path.join(a["url"], "index.html").replace("\\", "/"): a for a in ARTS}
    entries, seen, skipped = [], set(), 0

    remaining = []
    for f in pages():
        if f == "404.html":
            continue
        s = open(f, encoding="utf-8").read()
        if NOINDEX.search(s):
            skipped += 1
            continue
        m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        if not m:
            fail(f"canonical manquant, page absente du sitemap : {f}")
            continue
        loc = m.group(1)
        if not loc.startswith(BASE + "/"):
            fail(f"canonical hors domaine canonique : {f} -> {loc}")
            continue
        if loc in seen:
            fail(f"URL en double dans le sitemap : {loc}")
            continue
        seen.add(loc)
        remaining.append((f, loc, by_page.get(f)))

    blocks = []
    for title, match in SECTIONS:
        group = [x for x in remaining if match(x[0], x[2])]
        if not group:
            continue
        remaining = [x for x in remaining if x not in group]
        # Règle de tri : page pilier en tête de rubrique, puis parutions de la plus
        # récente à la plus ancienne (titre en départage). Les pages hors catalogue
        # suivent l'ordre de lecture défini dans FIXED_ORDER.
        group.sort(key=lambda x: (x[2]["title"] if x[2] else x[1]))
        group.sort(key=lambda x: x[2]["date"] if x[2] else "", reverse=True)
        group.sort(key=lambda x: FIXED_ORDER.index(x[0]) if x[0] in FIXED_ORDER else 99)
        group.sort(key=lambda x: 0 if x[0].startswith("palmares/") else 1)
        lines = [f"  <!-- {title} -->"]
        for f, loc, a in group:
            d = git_date(f) or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            lines.append(f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{d}</lastmod>\n  </url>")
            entries.append(loc)
        blocks.append("\n".join(lines))

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n\n".join(blocks) + "\n</urlset>\n")

    # validation stricte avant écriture
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        n = len(root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"))
        if n != len(entries):
            fail(f"sitemap : {n} balises url pour {len(entries)} URLs attendues")
    except Exception as e:
        fail(f"sitemap XML invalide : {e}")
        return

    old = open("sitemap.xml", encoding="utf-8").read() if os.path.exists("sitemap.xml") else ""
    if write("sitemap.xml", old, xml):
        log(f"sitemap.xml régénéré ({len(entries)} URLs indexables"
            + (f", {skipped} page(s) en noindex exclue(s)" if skipped else "") + ")")


# ------------------------------------------------------------- 6. contrôles
def check_indexnow():
    """La clé IndexNow doit être un fichier <clé>.txt à la racine, contenant
    exactement la clé. Un fichier renommé ou modifié fait refuser toutes les
    soumissions par Bing (403), sans autre signal que l'absence d'indexation."""
    keys = [f for f in os.listdir(".") if re.fullmatch(r"[0-9a-f]{8,128}\.txt", f)]
    if not keys:
        fail("clé IndexNow absente : voir tools/indexnow.py")
        return
    if len(keys) > 1:
        fail(f"plusieurs clés IndexNow à la racine ({', '.join(keys)}), n'en garder qu'une")
    k = keys[0]
    if open(k, encoding="utf-8").read().strip() != os.path.splitext(k)[0]:
        fail(f"{k} doit contenir exactement la clé, sans rien d'autre")


def check_no_redirect_links():
    """Aucun lien interne ne doit pointer vers une URL que le serveur redirige.
    Le cas rencontré le 28/07/2026 : 342 liens vers index.html, que .htaccess et
    le Caddyfile renvoient en 301 vers le dossier. Search Console classait la page
    d'accueil en « Page avec redirection », et chaque passage de Googlebot payait
    un saut inutile. La règle du site : une page = une URL, celle de la canonique."""
    for f in pages():
        s = open(f, encoding="utf-8").read()
        for href in set(re.findall(r'href="([^"]*index\.html[^"]*)"', s)):
            fail(f"lien vers une URL redirigée (301) : {f} -> {href}, "
                 f"écrire {href.replace('index.html', '') or './'}")


def check_no_query_links():
    """Le site ne publie aucun lien interne vers une URL à paramètre. Une URL en
    ?cat= ou ?q= est une page distincte pour un crawler : il la parcourt, la
    déduplique, et ce budget-là n'est pas passé sur les vrais articles. Les
    filtres et la recherche passent par un fragment (#cat=Spas), que les
    crawlers ignorent. Seul le versionnage des assets (?v=hash) est toléré :
    il force le rafraîchissement des caches et ne crée pas de page."""
    for f in pages():
        s = open(f, encoding="utf-8").read()
        for href in set(re.findall(r'href="([^"]+)"', s)):
            if href.startswith(("http", "mailto", "tel", "data:")) or "?" not in href:
                continue
            if re.match(r'^[./]*assets/[^?]+\?v=[0-9a-f]+$', href):
                continue
            fail(f"lien vers une URL à paramètre : {f} -> {href}, "
                 f"utiliser un fragment (#{href.split('?', 1)[1]})")


def check_canonical_path():
    """La canonique doit désigner exactement l'URL servie : domaine avec www,
    barre oblique finale sur les pages en dossier, pas de index.html. Une
    canonique vers une URL redirigée annule le bénéfice de la balise."""
    for f in pages():
        if f == "404.html":
            continue
        s = open(f, encoding="utf-8").read()
        m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        if not m:
            continue
        expected = BASE + "/" + (os.path.dirname(f) + "/" if f.endswith("/index.html") else f)
        expected = expected.replace("/index.html", "/")
        if m.group(1) != expected:
            fail(f"canonique inexacte : {f} -> {m.group(1)}, attendu {expected}")


def check_no_orphans():
    """Un article que seules les listes automatiques (accueil et page articles)
    citent n'a aucun signal éditorial interne. Google le classe alors « Explorée,
    actuellement non indexée », ce qui est arrivé le 25/07/2026 à la thalasso
    bretonne et aux hôtels de luxe parisiens. Chaque parution doit recevoir au
    moins un lien contextuel depuis un autre article."""
    auto = {"index.html", "articles.html"}
    for a in ARTS:
        target = a["url"]
        inbound = 0
        for f in pages():
            if f in auto or f == os.path.join(target, "index.html"):
                continue
            s = open(f, encoding="utf-8").read()
            s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
            if re.search(r'href="[^"]*%s"' % re.escape(target), s):
                inbound += 1
        if inbound == 0:
            fail(f"article orphelin, aucun lien éditorial entrant : {target} "
                 f"(ajouter un lien depuis un article proche avant de publier)")


def checks():
    check_indexnow()
    check_no_redirect_links()
    check_no_query_links()
    check_canonical_path()
    check_no_orphans()
    for f in pages():
        s = open(f, encoding="utf-8").read()
        for i, b in enumerate(re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)):
            try:
                json.loads(b)
            except Exception as e:
                fail(f"JSON-LD invalide : {f} bloc {i} ({e})")
        if "—" in s:
            fail(f"tiret cadratin interdit : {f}")
        if re.search(r"[Rr]édactrice", re.sub(r"<!--.*?-->", "", s, flags=re.S)):
            fail(f"signature au féminin : {f}")
        d = os.path.dirname(f) or "."

        def resolve(ref):
            """Un chemin commençant par / est relatif à la racine du site,
            les autres au dossier de la page."""
            return os.path.join(".", ref.lstrip("/")) if ref.startswith("/") else os.path.join(d, ref)

        for src in re.findall(r'src="([^"]*images/[^"]+)"', s) + re.findall(r'srcset="([^"]+)"', s):
            for cand in src.split(","):
                path = cand.strip().split(" ")[0]
                if path.startswith("http") or not path:
                    continue
                if not os.path.exists(resolve(path)):
                    fail(f"image absente : {f} -> {path}")
        for href in re.findall(r'href="([^"#?]+)"', s):
            if href.startswith(("http", "mailto", "tel", "data:")):
                continue
            p = resolve(href)
            if not os.path.exists(p) and not os.path.exists(os.path.join(p, "index.html")):
                fail(f"lien mort : {f} -> {href}")


# ----------------------------------------------------------------- exécution
if __name__ == "__main__":
    sync_counters()
    sync_static_lists()
    sync_images()
    sync_dates()
    sync_asset_versions()
    sync_markdown()
    sync_agent_skills()
    sync_agent_api()
    sync_sitemap()
    checks()

    print(f"\n  Build {'(vérification seule)' if CHECK else ''} : "
          f"{len(ARTS)} articles, {len(pages())} pages\n")
    for c in changes:
        print("  ✓", c)
    if problems:
        print()
        for p in problems:
            print("  ✗", p)
        sys.exit(1)
    print("\n  Aucun problème détecté.")

    # Rappel de l'étape que l'on oublie : un contenu publié sans notification met
    # des jours à être découvert, avec elle quelques minutes.
    if changes and not CHECK:
        print("\n  Prochaine étape : commiter, pousser, déployer,")
        print("  puis  npm run indexnow  pour notifier Bing et Copilot.")
    print()
