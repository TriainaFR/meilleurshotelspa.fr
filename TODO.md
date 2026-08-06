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
1. ~~Vérifier `robots.txt`, `/sitemap.xml` et le code 404~~ : fait le 28/07/2026,
   les trois répondent correctement (404 réel sur une URL inexistante).
2. Déclarer le site dans **Google Search Console** et **Bing Webmaster Tools**,
   y soumettre le sitemap. Search Console est en place depuis le 25/07/2026.
3. ~~Contrôler les redirections~~ : fait, `/index.html` renvoie bien 301 vers `/`.

### Suivi Search Console
Au 28/07/2026, trois rapports sont ouverts. Deux ne demandent aucune action :

- **« Autre page avec balise canonique correcte »** sur `articles.html?cat=Ouverture` :
  la canonique faisait son travail, mais ces URLs de filtre consommaient du budget
  de crawl pour rien. Le 28/07/2026, les 38 liens internes en `?cat=` et `?q=` sont
  passés en fragment (`#cat=Spas`), que les crawlers ignorent. L'ancienne forme
  reste lue par le JavaScript pour les liens déjà partagés. Le rapport s'éteindra
  de lui-même une fois les URLs oubliées.
- **« Explorée, actuellement non indexée »** sur la thalasso bretonne et les hôtels
  de luxe parisiens : les deux pages avaient été publiées sans aucun lien éditorial
  entrant. Corrigé le 28/07/2026, et le build refuse désormais toute page orpheline.
  Reste à **demander l'indexation** des deux URLs dans l'inspecteur Search Console,
  puis à cliquer « Valider la correction » sur le rapport « Page avec redirection ».

---

## Standards agents (scan Cloudflare Agent-Ready)

Score au 28/07/2026 : **57, niveau 4 « Agent-Integrated »**. Six standards sont en
place : Markdown négocié, WebMCP (4 outils), index de compétences, en-têtes Link,
règles de bots et Content Signals dans `robots.txt`, et depuis le 28/07/2026 une
**API de consultation** décrite par OpenAPI et publiée dans un catalogue RFC 9727.

Reste un point qui demande un accès au DNS Cloudflare.

### DNS-AID, à faire dans Cloudflare (Discoverability, 1 point)
Le site expose désormais un vrai point d'entrée machine, l'enregistrement DNS a donc
un sens. Dans le tableau de bord Cloudflare, zone `lesmeilleurshotelspa.fr`, onglet
DNS, créer un enregistrement **HTTPS** (type 65) :

```
Nom     : _index._agents
Priorité: 1
Cible   : www.lesmeilleurshotelspa.fr
Params  : alpn="h2,http/1.1" port=443
```

Puis activer **DNSSEC** (onglet DNS, section DNSSEC, « Enable DNSSEC ») pour que les
résolveurs renvoient une réponse authentifiée : la spec DNS-AID le demande. Le
registrar doit ensuite recevoir l'enregistrement DS que Cloudflare affiche.

### Volontairement non implémentés
**OAuth/OIDC, ressource protégée OAuth, `auth.md` et carte de serveur MCP.** Le site
n'a **ni compte ni authentification**, et son WebMCP s'exécute dans la page, sans
serveur MCP distant : publier ces documents annoncerait aux agents des points
d'entrée qui n'existent pas, et le premier agent qui essaierait tomberait sur un 404.
Ils ne deviendront pertinents que si le média expose un service authentifié, ou un
serveur MCP hébergé. Un Worker Cloudflare exposant les classements en outils MCP
ferait gagner le point « MCP Server Card », mais c'est un projet à part entière.

**Web Bot Auth** (`/.well-known/http-message-signatures-directory`) ne nous concerne
pas : ce répertoire de clés se publie quand on **opère** un robot qui signe ses
requêtes, pas quand on édite un site. Le scan le signale sans le compter.

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

### Un 404 mis en cache un an par Cloudflare
**Bug d'infrastructure rencontré le 30/07/2026.** Le `Caddyfile` pose
`Cache-Control: public, max-age=31536000, immutable` sur tout chemin en `.jpg`,
`.webp`, `.png`, `.woff2`, **en fonction du chemin demandé, pas du code de
réponse**. Une requête sur une image qui n'est pas encore déployée reçoit donc
un **404 assorti d'un cache d'un an**, que Cloudflare sert ensuite en `HIT` :
l'image devient inatteignable à cette URL même une fois le fichier en ligne.

C'est arrivé à `images/ld-shangrila.jpg`, l'image `og:image` de l'avis
Shangri-La The Shard, contournée en renommant le fichier `ld-shard-vue.jpg`.

Deux choses à faire :

1. **Corriger le `Caddyfile`** pour que les réponses d'erreur ne portent jamais
   le cache long. Piste, à valider avec un binaire Caddy avant de pousser :
   ```
   handle_errors {
       header -Cache-Control
       header Cache-Control "no-store"
       rewrite * /404.html
       file_server
   }
   ```
   Non testé : il n'y a pas de Caddy sur le poste, et une erreur de syntaxe dans
   ce fichier casse tout le site.
2. **Purger** `https://www.lesmeilleurshotelspa.fr/images/ld-shangrila.jpg` dans
   Cloudflare (Caching → Purge single file), pour libérer l'URL empoisonnée.

Règle de travail en attendant : **ne jamais requêter l'URL d'un nouvel asset
avant que le déploiement soit en ligne.** Vérifier d'abord la page HTML, dont
le cache est en `max-age=0`, et seulement ensuite les images.

### Quatre adresses lyonnaises sans score Destination
La parution du 30/07/2026, `/hotel-romantique-lyon/`, fait entrer quatre maisons
au catalogue sans score LMHS sur 10 : **Villa Maïa**, **MiHotel La Tour Rose**,
**Hôtel de l'Abbaye** et **Boscolo Lyon**. Elles n'ont pas passé la grille
Destination, dont le critère thématique lyonnais est l'ancrage gastronomique
(25 %), et trois d'entre elles n'ont pas de table lyonnaise intégrée. Deux suites
possibles, à trancher :

1. les faire passer la grille complète et **les intégrer au palmarès de Lyon**,
   qui compte aujourd'hui sept adresses intra-muros. La Villa Maïa est la plus
   criante : un 5 étoiles Leading Hotels of the World absent du palmarès de sa
   propre ville ;
2. ou assumer durablement la mention « non noté », qui est déjà explicitée dans
   la méthode de la page.

Manquent aussi leurs **fourchettes haute saison** : seul le tarif d'entrée a été
relevé (450 €, 132 €, 195 €, 325 €). Et le **Collège Hôtel n'a pas de photo**,
c'est la seule des huit fiches sans image.

---

## Données à recouper

### Château du Portereau : aller dormir sur place
L'avis du 06/08/2026, `/avis/chateau-du-portereau-vertou/`, est documentaire et
l'annonce : **aucun séjour de contrôle**. Deux choses à obtenir pour le lever.
D'abord une nuit sur place, qui permettrait de passer de la fiche LMHS sur 10 au
Protocole LMHS sur 20. Ensuite **la grille tarifaire des chambres**, que
l'établissement ne publie nulle part, et qui est ce qui pèse aujourd'hui sur
l'axe rapport prix-expérience.

Rappel avant tout échange avec l'hôtel : la page corrige trois chiffres que
l'établissement lui-même publie autrement que la presse (3 hectares et non 5,
fontaine de 6 mètres et non 7, Orangerie de 200 m²). C'est un argument à leur
faveur, pas contre eux.

### Deux spas parisiens publiés sans note
La parution du 05/08/2026, `/spas/meilleur-spa-avec-hammam-paris/`, publie le
**Mandarin Oriental Paris** (251 rue Saint-Honoré, à ne pas confondre avec le
Mandarin Oriental Lutetia du comparatif des palaces) et **Aux Bains Montorgueil**
sans aucune note, faute de visite. Les visiter, relever la température de leur
salle chaude au thermomètre, et remplacer les deux « non noté » par des scores
Protocole LMHS sur 20. Le Mandarin Oriental est le plus urgent : 900 m², l'un
des plus vastes spas d'hôtel de Paris, et son périmètre d'accès aux non-résidents
n'est pas publié, il faudra le demander à l'établissement.

### Le hammam de la Grande Mosquée et les annuaires
Le site officiel écrit que le hammam est **exclusivement réservé aux femmes**.
Top-halal, Plein Soleil Paris et la plupart des annuaires publient encore des
créneaux hommes le mardi de 14 h à 21 h et le dimanche de 10 h à 21 h. Nos deux
pages retiennent la source de l'établissement. À reconfirmer par téléphone lors
de la prochaine passe : si les créneaux hommes existent dans les faits sans
figurer en ligne, c'est une information qu'aucun guide français ne donne
correctement, et elle vaut d'être publiée.

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
