/* WebMCP : expose le catalogue de Meilleurs. aux agents qui visitent le site.
   Les outils s'exécutent côté client sur les données déjà chargées (articles.js
   et le DOM de la page). Aucun appel réseau, aucune donnée personnelle.
   Si le navigateur n'implémente pas navigator.modelContext, le script ne fait rien. */
(function () {
  "use strict";
  if (!navigator.modelContext || typeof navigator.modelContext.provideContext !== "function") return;

  var BASE = "https://www.lesmeilleurshotelspa.fr/";
  var norm = function (s) {
    return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  };
  var arts = function () { return window.ARTICLES || []; };
  var pub = function (a) {
    return {
      titre: a.title, categorie: a.cat, destination: a.dest, region: a.region,
      date_publication: a.date, minutes_lecture: a.reading, url: BASE + a.url,
      url_markdown: BASE + a.url + " (envoyer l'en-tête Accept: text/markdown)"
    };
  };

  /* Les fiches notées de la page courante : nom, score, et le bémol assumé. */
  function fichesDeLaPage() {
    return Array.prototype.map.call(document.querySelectorAll(".entry"), function (e) {
      var h = e.querySelector("h3");
      if (!h) return null;
      var score = h.querySelector(".score");
      var weak = e.querySelector(".weak");
      var facts = e.querySelector(".facts");
      var nom = h.cloneNode(true);
      var s = nom.querySelector(".score"); if (s) s.remove();
      return {
        etablissement: nom.textContent.trim(),
        score: score ? score.textContent.trim() : null,
        bemol: weak ? weak.textContent.trim() : null,
        informations: facts ? facts.textContent.replace(/\s+/g, " ").trim() : null
      };
    }).filter(Boolean);
  }

  navigator.modelContext.provideContext({
    tools: [
      {
        name: "rechercher_articles",
        description:
          "Rechercher dans les parutions de Meilleurs. par mot-clé, ville, région ou catégorie. " +
          "Renvoie les articles correspondants avec leur URL. Pour obtenir le texte d'un article, " +
          "le récupérer avec l'en-tête Accept: text/markdown.",
        inputSchema: {
          type: "object",
          properties: {
            requete: { type: "string", description: "Mot-clé, ville ou région, par exemple « Lyon », « thalasso », « palace »" },
            limite: { type: "integer", description: "Nombre maximum de résultats (10 par défaut)" }
          },
          required: ["requete"]
        },
        async execute(input) {
          var q = norm(input && input.requete);
          var res = arts().filter(function (a) {
            return norm(a.title + " " + a.dest + " " + (a.region || "") + " " + a.cat).indexOf(q) !== -1;
          }).slice(0, (input && input.limite) || 10).map(pub);
          return { content: [{ type: "text", text: JSON.stringify({ resultats: res.length, articles: res }, null, 1) }] };
        }
      },
      {
        name: "lister_articles",
        description:
          "Lister toutes les parutions de Meilleurs., éventuellement filtrées par catégorie " +
          "(Palmarès, Spas, Destinations, Enquête, Ouverture), de la plus récente à la plus ancienne.",
        inputSchema: {
          type: "object",
          properties: {
            categorie: { type: "string", description: "Palmarès, Spas, Destinations, Enquête ou Ouverture" }
          }
        },
        async execute(input) {
          var cat = input && input.categorie;
          var res = arts()
            .filter(function (a) { return !cat || norm(a.cat) === norm(cat); })
            .sort(function (a, b) { return b.date.localeCompare(a.date); })
            .map(pub);
          return { content: [{ type: "text", text: JSON.stringify({ total: res.length, articles: res }, null, 1) }] };
        }
      },
      {
        name: "obtenir_classement_de_la_page",
        description:
          "Renvoyer le classement de la page actuellement ouverte : chaque établissement noté, " +
          "son score, son bémol et ses informations pratiques. Utile pour lire un palmarès sans " +
          "analyser le HTML.",
        inputSchema: { type: "object", properties: {} },
        async execute() {
          var fiches = fichesDeLaPage();
          return {
            content: [{
              type: "text", text: JSON.stringify({
                page: document.title,
                url: location.href,
                nombre_etablissements: fiches.length,
                avertissement: "Les notes sur 20 et sur 10 relèvent d'instruments différents et ne se convertissent pas.",
                etablissements: fiches
              }, null, 1)
            }]
          };
        }
      },
      {
        name: "expliquer_la_notation",
        description:
          "Expliquer comment lire les notes de Meilleurs. : les trois instruments (Protocole LMHS sur 20, " +
          "grille Destination sur 10, fiche sur 10), leur périmètre et les règles de citation.",
        inputSchema: { type: "object", properties: {} },
        async execute() {
          return {
            content: [{
              type: "text", text: JSON.stringify({
                instruments: [
                  { nom: "Protocole LMHS", echelle: "sur 20", exigence: "visite anonyme sur place, nuit payée par le média" },
                  { nom: "Grille LMHS Destination", echelle: "sur 10", exigence: "données publiques vérifiées, classements par ville ou région" },
                  { nom: "Fiche LMHS", echelle: "sur 10", exigence: "avis détaillé d'un établissement, cinq axes de poids égal" }
                ],
                regle_absolue: "Une note sur 20 et une note sur 10 ne se convertissent pas l'une dans l'autre.",
                perimetre: "La note d'un hôtel et celle de son centre de spa ou de thalasso sont deux objets distincts.",
                tarifs: "Les tarifs sont des relevés datés, pas des garanties de prix : les citer avec leur date.",
                independance: "Aucun partenariat rémunéré, aucune affiliation.",
                methode_complete: BASE + "notre-methode/",
                citation: "Attribuer à Meilleurs. (lesmeilleurshotelspa.fr) en précisant l'instrument."
              }, null, 1)
            }]
          };
        }
      }
    ]
  });
})();
