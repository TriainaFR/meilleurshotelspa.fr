"""
Conversion des pages du site en Markdown, pour la négociation de contenu.

Un agent qui envoie `Accept: text/markdown` reçoit le texte de l'article, sans
la navigation, le chrome ni le JavaScript. Le convertisseur est écrit sur mesure
pour la structure de ce site plutôt que générique : il sait quoi jeter (bandeau,
menus, overlay de recherche, pied de page) et quoi préserver (tableaux de
classement, notes, bémols, sources).

Aucune dépendance externe.
"""

import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

# Éléments dont le contenu n'a aucun sens hors navigateur
DROP_TAGS = {"script", "style", "svg", "noscript", "button", "form",
             "input", "select", "textarea", "picture", "source"}

# Chrome du site : présent sur chaque page, sans valeur pour un agent
DROP_CLASSES = {"topstrip", "masthead", "overlay", "search-overlay", "float-img",
                "ticker", "ticker-inner", "foot-mast", "colophon", "mast-actions",
                "dest-ctrl", "crumb", "burger", "stamp", "reg"}
DROP_IDS = {"overlay", "search-overlay", "float-img", "ticker", "burger"}

BLOCKS = {"p", "div", "section", "article", "header", "footer", "ul", "ol", "li",
          "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "figure", "figcaption",
          "blockquote", "nav", "aside", "main", "span"}


class Converter(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.out = []          # blocs Markdown terminés
        self.buf = []          # texte du bloc courant
        self.depth_drop = 0    # profondeur dans un sous-arbre à jeter
        self.stack = []        # pile des balises ouvertes
        self.list_stack = []   # ("ul"|"ol", compteur)
        self.in_article = False
        self.article_depth = None
        self.saw_article = False
        self.table = None      # lignes du tableau courant
        self.row = None
        self.cell = None
        self.link = None
        self.pre_h = None

    # ------------------------------------------------------------------ utils
    def text(self):
        t = "".join(self.buf)
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r" *\n *", "\n", t)
        return t.strip()

    def flush(self, prefix=""):
        t = self.text()
        self.buf = []
        if t:
            self.out.append(prefix + t)

    def emit(self, s):
        self.buf.append(s)

    def dropped(self, attrs):
        d = dict(attrs)
        cls = set((d.get("class") or "").split())
        return bool(cls & DROP_CLASSES) or d.get("id") in DROP_IDS

    # ----------------------------------------------------------------- ouverture
    def handle_starttag(self, tag, attrs):
        if self.depth_drop:
            if tag not in ("br", "img", "meta", "link", "hr"):
                self.depth_drop += 1
            return
        if tag in DROP_TAGS or self.dropped(attrs):
            self.depth_drop = 1
            return

        d = dict(attrs)

        # On ne garde que le corps rédactionnel : <article> s'il existe.
        if tag == "article":
            self.saw_article = True
            self.in_article = True
            self.article_depth = len(self.stack)

        if tag in BLOCKS:
            self.stack.append(tag)

        if self.cell is not None and tag in ("td", "th"):
            pass

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.flush()
            self.pre_h = "#" * int(tag[1]) + " "
        elif tag == "p":
            self.flush()
        elif tag == "br":
            self.emit("\n")
        elif tag == "hr":
            self.flush()
            self.out.append("---")
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag in ("em", "i"):
            self.emit("*")
        elif tag == "a":
            href = d.get("href", "")
            if href and not href.startswith(("#", "javascript:")):
                self.link = urljoin(self.base, href)
                self.emit("[")
        elif tag == "span" and "lab" in (d.get("class") or "").split():
            # Libellé de section, collé au titre dans le HTML : on le sépare
            self.label_span = True
        elif tag in ("ul", "ol"):
            self.flush()
            self.list_stack.append([tag, 0])
        elif tag == "li":
            self.flush()
        elif tag == "table":
            self.flush()
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.buf = []
        elif tag == "figcaption":
            self.flush()
        elif tag == "blockquote":
            self.flush()
        elif tag == "img" and self.in_article:
            alt = (d.get("alt") or "").strip()
            src = d.get("src", "")
            if alt and src:
                self.flush()
                self.out.append(f"![{alt}]({urljoin(self.base, src)})")

    # ---------------------------------------------------------------- fermeture
    def handle_endtag(self, tag):
        if self.depth_drop:
            self.depth_drop -= 1
            return

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.flush(self.pre_h or "")
            self.pre_h = None
        elif tag == "p":
            self.flush()
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag in ("em", "i"):
            self.emit("*")
        elif tag == "a" and self.link:
            self.emit(f"]({self.link})")
            self.link = None
        elif tag in ("ul", "ol"):
            self.flush()
            if self.list_stack:
                self.list_stack.pop()
        elif tag == "li":
            t = self.text()
            self.buf = []
            if t and self.list_stack:
                kind, n = self.list_stack[-1]
                if kind == "ol":
                    self.list_stack[-1][1] = n + 1
                    self.out.append(f"{n + 1}. {t}")
                else:
                    self.out.append(f"- {t}")
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append(self.text())
            self.buf = []
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(c for c in self.row):
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.emit_table()
            self.table = None
        elif tag == "figcaption":
            self.flush("*")
            if self.out and self.out[-1].startswith("*") and not self.out[-1].endswith("*"):
                self.out[-1] += "*"
        elif tag == "blockquote":
            t = self.text()
            self.buf = []
            if t:
                self.out.append("\n".join("> " + l for l in t.split("\n")))
        elif tag == "article":
            self.flush()
            if self.article_depth is not None and len(self.stack) - 1 <= self.article_depth:
                self.in_article = False
        elif tag in ("div", "section", "header", "footer", "nav", "aside", "main"):
            self.flush()
        elif tag == "span" and getattr(self, "label_span", False):
            self.emit(" · ")
            self.label_span = False

        if tag in BLOCKS and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def emit_table(self):
        rows = [r for r in self.table if r]
        if not rows:
            return
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        esc = lambda c: c.replace("|", "\\|").replace("\n", " ")
        # Un tableau doit sortir en un seul bloc : les lignes ne peuvent pas être
        # séparées par des lignes vides, sinon le Markdown ne le reconnaît plus.
        lines = ["| " + " | ".join(esc(c) for c in rows[0]) + " |",
                 "|" + "|".join([" --- "] * width) + "|"]
        lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows[1:]]
        self.out.append("\n".join(lines))

    def handle_data(self, data):
        if self.depth_drop:
            return
        self.buf.append(data)

    # ------------------------------------------------------------------ sortie
    def result(self):
        self.flush()
        md = "\n\n".join(b for b in self.out if b.strip())
        md = re.sub(r"\n{3,}", "\n\n", md)
        md = re.sub(r"[ \t]+\n", "\n", md)
        return md.strip() + "\n"


def meta(src, name=None, prop=None):
    pat = (rf'<meta name="{name}" content="([^"]*)"' if name
           else rf'<meta property="{prop}" content="([^"]*)"')
    m = re.search(pat, src)
    return html.unescape(m.group(1)) if m else None


def convert(path, src, base_url):
    """Retourne le Markdown d'une page, en-tête de contexte compris."""
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', src)
    canonical = canonical.group(1) if canonical else base_url
    title = re.search(r"<title>(.*?)</title>", src, re.S)
    title = html.unescape(title.group(1).strip()) if title else path
    desc = meta(src, name="description")
    summary = meta(src, name="ai-content-summary")
    author = meta(src, name="author")
    updated = meta(src, name="content-freshness")

    # Le corps : <article> quand il existe, sinon le <body> nettoyé
    body = re.search(r"<body[^>]*>(.*)</body>", src, re.S)
    body = body.group(1) if body else src

    c = Converter(canonical)
    c.feed(body)
    md = c.result()

    head = [f"# {title}", ""]
    if desc:
        head += [f"> {desc}", ""]
    ctx = [f"URL canonique : {canonical}"]
    if author:
        ctx.append(f"Auteur : {author}")
    if updated:
        ctx.append(f"Dernière mise à jour : {updated}")
    ctx.append("Source : Meilleurs. (lesmeilleurshotelspa.fr), média indépendant édité par Triaina SAS")
    head += [" · ".join(ctx), ""]
    if summary:
        head += ["## En résumé pour un agent", "", summary, ""]
    head += ["---", ""]

    # Le H1 du corps ferait doublon avec le titre de l'en-tête, qui devient le H1
    # du document Markdown. On le retire où qu'il se trouve.
    md = re.sub(r"^# .*\n?\n?", "", md, count=1, flags=re.M)
    return "\n".join(head) + md
