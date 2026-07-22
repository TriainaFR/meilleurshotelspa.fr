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

Hébergement : OVH et Railway. Servir la racine du dépôt en statique, avec
`404.html` en page d'erreur et une redirection de l'apex vers `www`.
