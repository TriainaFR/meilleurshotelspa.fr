# Meilleurs. — lesmeilleurshotelspa.fr

Site du média **Meilleurs.**, consacré aux hôtels, spas et destinations d'exception.
Édité par **Triaina SAS** (Paris, RCS Paris 999 402 654).

Site statique : HTML, CSS et JavaScript vanilla, aucune dépendance de build côté client.

## Structure

```
index.html              page d'accueil (fil, palmarès, destinations, spas, récits)
articles.html           sommaire filtrable des parutions
contact.html            formulaire (EmailJS)
404.html                page d'erreur
<slug>/index.html       un dossier par article
palmares/ spas/ destinations/   rubriques
notre-methode/          le Protocole LMHS (méthodologie de notation)
redaction/              la rédaction + une page par auteur
mentions-legales/ confidentialite/
assets/
  articles.js           SOURCE DE VÉRITÉ du catalogue d'articles
  app.js                comportements partagés (fil, recherche, filtres, formulaire)
  style.css             design system complet
images/                 photos d'établissements (JPEG + variantes WebP 800w et pleine largeur)
tools/build.py          build : compteurs, liens statiques, dates, sitemap, contrôles
robots.txt llms.txt sitemap.xml
```

## Build

À lancer **après chaque ajout ou modification d'article** :

```bash
uv run --with pillow python tools/build.py
```

Le script dérive automatiquement de `assets/articles.js` et de l'historique git :

- les compteurs affichés (parutions, destinations, spas testés) ;
- les listes d'articles statiques injectées entre les marqueurs `<!--S:...-->`,
  qui rendent le catalogue visible des crawlers IA n'exécutant pas JavaScript ;
- les dates (`dateModified`, `content-freshness`, « Dernière mise à jour ») ;
- les attributs `width`/`height` et les variantes WebP manquantes ;
- `sitemap.xml`.

Il échoue si un JSON-LD est invalide, s'il reste un tiret cadratin, une image
absente ou un lien interne mort. `--check` exécute les contrôles sans rien écrire.

## IndexNow

Le site est déclaré auprès d'**IndexNow**, le protocole partagé par Bing, Yandex,
Seznam et Naver : un ping et la page est recrawlée en quelques minutes au lieu de
quelques jours. Google n'y participe pas, c'est la Search Console qui fait foi
pour lui.

La clé est le fichier `<clé>.txt` à la racine, qui doit contenir exactement la
clé et rester accessible en ligne : c'est la preuve de propriété du domaine.
`tools/build.py` vérifie cette cohérence à chaque build.

```bash
npm run indexnow        # pages modifiées au dernier commit (usage courant)
npm run indexnow:all    # toutes les URLs du sitemap (après une refonte)
npm run indexnow:dry    # afficher ce qui serait envoyé, sans envoyer
```

La soumission part vers **deux points d'entrée** : celui partagé
(`api.indexnow.org`, qui relaie aux moteurs participants) et **celui de Bing en
direct**, dont l'index alimente les citations de Microsoft Copilot. Un relais en
panne passerait autrement inaperçu.

À lancer **après le déploiement**, pas avant : tant que le fichier de clé n'est
pas en ligne, Bing refuse la soumission avec un 403. Le script le vérifie et
s'arrête plutôt que d'envoyer dans le vide.

## Scripts npm

`package.json` ne sert qu'à ces raccourcis : le site n'a **aucune dépendance
Node**, rien n'est compilé.

| Commande | Effet |
|---|---|
| `npm run build` | Le build complet (compteurs, Markdown, dates, sitemap, contrôles) |
| `npm run check` | Les contrôles seuls, sans rien écrire |
| `npm run indexnow` | Soumet les pages modifiées au dernier commit |
| `npm run indexnow:all` | Soumet les 27 URLs du sitemap |
| `npm run publish:site` | Build, commit et push en une commande |

Le `nixpacks.toml` déclare `providers = []` précisément pour que Railway ignore
ce `package.json` : sans ça, Nixpacks basculerait en build Node et chercherait
un `npm run build` côté serveur, qui n'a pas lieu d'être.

## Règles éditoriales appliquées dans le code

- Domaine canonique : `https://www.lesmeilleurshotelspa.fr`.
- **Tiret cadratin interdit** (virgule, deux-points ou point-virgule à la place).
- Photos : uniquement de vraies photos des établissements nommés, issues des sites
  officiels ou des dossiers de presse. Les banques d'images ne servent que de repli.
- Toute donnée chiffrée publiée (prix, superficie, chambres, étoiles) est vérifiée
  sur source externe, consignée dans le bloc `FAITS VÉRIFIÉS` en fin de fichier.
- Notation : voir `/notre-methode/`. Une note sur 20 et une note sur 10 relèvent
  d'instruments différents et ne se convertissent pas l'une dans l'autre.

## Déploiement

Domaine canonique : **https://www.lesmeilleurshotelspa.fr**

Deux configurations sont fournies, à choisir selon l'hébergeur :

| Hébergeur | Fichiers | Ce qu'ils font |
|---|---|---|
| **OVH** (Apache) | `.htaccess` | HTTPS forcé via `X-Forwarded-Proto`, apex → `www`, `/dossier/index.html` → `/dossier/`, `ErrorDocument 404`, compression, cache long sur les images, en-têtes de sécurité |
| **Railway** (Caddy) | `Caddyfile`, `nixpacks.toml`, `railway.json` | Même comportement. Seul l'apex est redirigé vers `www` : le domaine `.up.railway.app` reste joignable, sinon les healthchecks reçoivent une 301 |

Le build Railway copie le site dans `/srv` et en exclut `tools/`, les fichiers de
configuration et la documentation, puis valide le `Caddyfile` avant de démarrer.

### Après la première mise en ligne

1. Vérifier que `/robots.txt` et `/sitemap.xml` répondent en 200, et qu'une URL
   inexistante renvoie un **code 404** et non un 200.
2. Déclarer le site dans Google Search Console et Bing Webmaster Tools, y
   soumettre le sitemap.
3. Contrôler les trois redirections : apex → www, http → https, `/index.html` → `/`.

Le reste des chantiers ouverts est listé dans [TODO.md](TODO.md).
