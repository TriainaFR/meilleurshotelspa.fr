# Ce qu'il reste à faire

État au 22 juillet 2026. Les points de l'audit SEO / GEO / E-E-A-T déjà traités
ne figurent plus ici : voir l'historique git.

---

## À faire avant la mise en ligne

### Mettre le site en production
Le dépôt est prêt à être servi tel quel. Deux configurations sont fournies :

- **OVH (Apache)** : `.htaccess` à la racine. Il force HTTPS, force `www`,
  supprime les URLs en double (`/dossier/index.html` → `/dossier/`), déclare
  `404.html`, active la compression, le cache long sur les images et les
  en-têtes de sécurité.
- **Railway (Caddy)** : `Caddyfile` + `nixpacks.toml` + `railway.json`. Même
  comportement. Seul l'apex est redirigé vers `www`, pour que le domaine
  technique `.up.railway.app` reste joignable par les healthchecks.

Côté DNS, faire pointer `www` vers l'hébergeur retenu et laisser l'apex
`lesmeilleurshotelspa.fr` redirigé (la config s'en charge côté serveur).

**Après la mise en ligne**, dans l'ordre :
1. Vérifier que `https://www.lesmeilleurshotelspa.fr/robots.txt` et `/sitemap.xml`
   répondent en 200, et qu'une URL inexistante renvoie bien un **code 404** (pas 200).
2. Déclarer le site dans **Google Search Console** et **Bing Webmaster Tools**,
   y soumettre le sitemap.
3. Contrôler les redirections : apex → www, http → https, `/index.html` → `/`.

---

## Contenu et crédibilité

### Photos des deux auteurs
Les fiches `/redaction/lucas-lecoq/` et `/redaction/swann-bertaud/` n'ont aucun
portrait. C'est le signal E-E-A-T manquant le plus rentable : il ne manque que
les fichiers. Les déposer dans `images/` (`auteur-lucas-lecoq.jpg`,
`auteur-swann-bertaud.jpg`, format carré ≥ 800 px), les ajouter dans la carte
auteur et dans la propriété `image` des `Person` en JSON-LD.

### Réseaux sociaux de la marque
Aucun `sameAs` d'entreprise n'est déclaré sur l'`Organization` : seuls les
profils LinkedIn personnels des deux auteurs le sont. Dès qu'un compte média
existe (LinkedIn Triaina, Instagram, X), l'ajouter aux blocs `NewsMediaOrganization`.

### Newsletter
Aucun mécanisme de rétention. Un formulaire « alerte palmarès » suffirait,
sur le modèle du formulaire de contact déjà branché sur EmailJS.

---

## Données à recouper

### Deux prix identiques non vérifiés
Les Étangs de Corot et Le Barn affichent tous deux **290 €** dans
`destinations/hotel-spa-privatif-ile-de-france/`. C'est plausible mais les deux
agents chargés de la vérification ont été interrompus : à recouper sur les
moteurs de réservation officiels.

### Bandeau « Eau du bassin : 28,4 °C »
Présent sur les 28 pages, rattaché à aucun bassin identifiable. Soit l'assumer
comme un clin d'œil de chrome, soit le rattacher à un établissement réel et le
sourcer.

### Les 3 adresses non visitées du palmarès
Le site annonce désormais « 47 des 50 adresses visitées anonymement, les 3
restantes évaluées sur données publiques ». Ajouter une phrase dans
`/notre-methode/` expliquant lesquelles et pourquoi.

---

## Entretien courant

### Après chaque publication
Lancer le build, qui recalcule tout ce qui dérive du catalogue :

```bash
uv run --with pillow python tools/build.py
```

Ne jamais éditer à la main un compteur, une liste d'articles, une date de mise à
jour ou le sitemap : le prochain build les écrasera.

### Rythme de fraîcheur
Les tarifs relevés datent tous de juillet 2026. Prévoir une révision mensuelle :
re-relever les prix d'appel, commiter, le build re-date les pages automatiquement.

### Compteurs des cartes destinations
Les nombres d'adresses affichés sur les cartes de la page d'accueil
(« 30 adresses » pour Paris, etc.) sont saisis à la main dans `index.html`.
Ils sont exacts aujourd'hui ; à revoir à chaque nouvelle parution régionale.
