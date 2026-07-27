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

## Standards agents (scan Cloudflare Agent-Ready)

Quatre standards sont en place : Markdown négocié, WebMCP, index de compétences
et en-têtes Link. Reste un point, qui demande un accès au DNS Cloudflare.

### DNS-AID (Discoverability, 1 point)
Publier des enregistrements SVCB ou HTTPS sous `_index._agents.lesmeilleurshotelspa.fr`,
pointant vers un point d'entrée de découverte. À faire dans le tableau de bord
Cloudflare, zone DNS. Signer la zone en DNSSEC pour que les résolveurs valident.
Valeur réelle limitée tant que le site n'expose pas de point d'entrée agent :
c'est un gain de score plus qu'un gain d'usage.

### Volontairement non implémentés
Catalogue d'API (RFC 9727), OAuth/OIDC, ressource protégée OAuth, `auth.md` et
carte de serveur MCP. Le site n'a **ni API ni authentification** : publier ces
documents annoncerait aux agents des points d'entrée qui n'existent pas. Ils ne
deviendront pertinents que le jour où le média exposera un vrai service, par
exemple une API de consultation des classements.

## Édition internationale

La Sardaigne, publiée le 27 juillet 2026, est la première parution hors de France.
Trois points restent à trancher :

- Le colophon, la page d'accueil et `llms.txt` décrivent encore le média comme une
  **« Édition France »**. À revoir si d'autres destinations étrangères suivent.
- Les deux indices de l'article (**Indice Exclusivité** et **Score Authenticité sarde**,
  tous deux sur 10) ne figurent pas sur `/notre-methode/`. S'ils resservent ailleurs,
  les y documenter plutôt que de les redéfinir dans chaque article.
- Aucune des sept maisons n'a été visitée : l'article le dit, mais le site ne dispose
  d'aucune grille dédiée aux classements étrangers sur données publiques.

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

### Les sept tarifs sardes
Les prix de `/sardaigne/meilleurs-hotels-5-etoiles/` (de 172 à 600 €) viennent du
brief et sont publiés comme ordres de grandeur relevés en juillet 2026. Aucun n'a
été recoupé sur un moteur de réservation officiel.

### Les 3 adresses non visitées du palmarès
Le site annonce désormais « 47 des 50 adresses visitées anonymement, les 3
restantes évaluées sur données publiques ». Ajouter une phrase dans
`/notre-methode/` expliquant lesquelles et pourquoi.

---

## Entretien courant

### Après chaque publication
La routine est en trois temps, et la troisième n'est pas optionnelle :

```bash
npm run build                     # compteurs, Markdown, dates, sitemap, contrôles
git commit -am "…" && git push
npm run indexnow                  # après déploiement : Bing et Copilot
```

Le build rappelle lui-même la dernière étape en fin de sortie. Ne jamais éditer à
la main un compteur, une liste d'articles, une date de mise à jour ou le sitemap :
le prochain build les écrasera.

### Rythme de fraîcheur
Les tarifs relevés datent tous de juillet 2026. Prévoir une révision mensuelle :
re-relever les prix d'appel, commiter, le build re-date les pages automatiquement.

### Compteurs des cartes destinations
Les nombres d'adresses affichés sur les cartes de la page d'accueil
(« 30 adresses » pour Paris, etc.) sont saisis à la main dans `index.html`.
Ils sont exacts aujourd'hui ; à revoir à chaque nouvelle parution régionale.
