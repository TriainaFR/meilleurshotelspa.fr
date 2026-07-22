/* Meilleurs. comportements partagés (landing + articles) */
(function(){
  "use strict";
  const $ = (s, c) => (c || document).querySelector(s);
  const $$ = (s, c) => Array.from((c || document).querySelectorAll(s));

  /* ---------- helpers ---------- */
  const MONTHS = ["janv.","févr.","mars","avr.","mai","juin","juil.","août","sept.","oct.","nov.","déc."];
  function frDate(iso){
    const [y,m,d] = iso.split("-").map(Number);
    return d + " " + MONTHS[m-1] + " " + y;
  }
  function norm(s){
    return (s||"").normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase();
  }
  function imgUrl(a, w){
    return "https://images.unsplash.com/photo-" + a.img + "?q=75&w=" + (w||600) + "&auto=format&fit=crop";
  }
  /* préfixe racine déduit du <link> CSS : "" à la racine, "../../" dans /palmares/<slug>/ */
  const ROOT = (function(){
    const l = document.querySelector('link[rel="stylesheet"][href*="assets/style.css"]');
    return l ? l.getAttribute("href").replace(/assets\/style\.css.*$/, "") : "";
  })();
  function href(a){ return a.url ? ROOT + a.url : "#"; }
  function cardHTML(a){
    return '<a class="art-card" href="' + href(a) + '" data-cat="' + a.cat + '">' +
      '<div class="ph"><img src="' + (a.photo ? ROOT + a.photo : imgUrl(a,600)) + '" alt="" loading="lazy" ' +
      'onerror="this.onerror=null;this.src=\'https://picsum.photos/seed/' + a.seed + '/600/400\'"></div>' +
      '<div class="meta"><span class="cat">' + a.cat + '</span><span class="date">' + frDate(a.date) + '</span></div>' +
      '<h3>' + a.title + '</h3>' +
      '<p class="dest">' + a.dest + ' · ' + a.reading + ' min de lecture</p>' +
    '</a>';
  }
  const byDateDesc = (a,b) => b.date.localeCompare(a.date);

  /* ---------- date du jour (topstrip) ---------- */
  const today = $("#today");
  if(today){
    const s = new Date().toLocaleDateString("fr-FR", {weekday:"long", day:"numeric", month:"long"});
    today.textContent = s.charAt(0).toUpperCase() + s.slice(1);
  }

  /* ---------- menu overlay ---------- */
  const ov = $("#overlay"), burger = $("#burger");
  if(ov && burger){
    const toggle = (open) => {
      ov.classList.toggle("open", open);
      ov.setAttribute("aria-hidden", String(!open));
      burger.setAttribute("aria-expanded", String(open));
      document.body.style.overflow = open ? "hidden" : "";
    };
    burger.addEventListener("click", () => toggle(true));
    $("#close-overlay").addEventListener("click", () => toggle(false));
    $$("a", ov).forEach(a => a.addEventListener("click", () => toggle(false)));
    window.__closeMenu = () => toggle(false);
  }

  /* ---------- reveals ---------- */
  const io = new IntersectionObserver((es) => {
    es.forEach(e => { if(e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target); } });
  }, {threshold:.12});
  $$(".rv").forEach(el => io.observe(el));

  /* ---------- ticker (landing) ---------- */
  const ticker = $("#ticker");
  if(ticker){ ticker.innerHTML += ticker.innerHTML; }

  /* ---------- palmarès : image flottante (landing) ---------- */
  const list = $("#rank-list"), float = $("#float-img");
  if(list && float){
    const img = $("img", float);
    let x=0,y=0,tx=0,ty=0,raf=null;
    const lerp = (a,b,n) => a + (b-a)*n;
    function loop(){
      x = lerp(x,tx,.12); y = lerp(y,ty,.12);
      float.style.left = (x+24)+"px"; float.style.top = (y-140)+"px";
      raf = requestAnimationFrame(loop);
    }
    list.addEventListener("mousemove", (e) => { tx=e.clientX; ty=e.clientY; if(!raf) loop(); });
    $$(".rank-row", list).forEach(row => {
      row.addEventListener("mouseenter", () => {
        img.onerror = () => { img.onerror=null; img.src=row.dataset.fallback; };
        img.src = row.dataset.img;
        float.classList.add("on");
      });
    });
    list.addEventListener("mouseleave", () => {
      float.classList.remove("on");
      if(raf){ cancelAnimationFrame(raf); raf=null; }
    });
  }

  /* ---------- destinations : drag + flèches (landing) ---------- */
  const sc = $("#dest-scroll");
  if(sc){
    const card = $(".dest-card", sc);
    const step = () => (card ? card.getBoundingClientRect().width + 24 : 320);
    $("#dnext").addEventListener("click", () => sc.scrollBy({left:step(), behavior:"smooth"}));
    $("#dprev").addEventListener("click", () => sc.scrollBy({left:-step(), behavior:"smooth"}));
    let down=false, startX=0, startL=0, moved=false;
    sc.addEventListener("pointerdown", (e) => { down=true; moved=false; startX=e.clientX; startL=sc.scrollLeft; sc.classList.add("grabbing"); });
    window.addEventListener("pointermove", (e) => {
      if(!down) return;
      const dx = e.clientX - startX;
      if(Math.abs(dx) > 4) moved = true;
      sc.scrollLeft = startL - dx;
    });
    window.addEventListener("pointerup", () => { down=false; sc.classList.remove("grabbing"); });
    sc.addEventListener("click", (e) => { if(moved){ e.preventDefault(); } }, true);
  }

  /* ---------- compteurs de parutions (menus) ---------- */
  if(window.ARTICLES){
    $$("[data-art-count]").forEach(el => { el.textContent = ARTICLES.length + " parutions"; });
  }

  /* ---------- le fil : 12 unes + dépêches (landing) ---------- */
  const latest = $("#latest-grid");
  if(latest && window.ARTICLES){
    const sorted = ARTICLES.slice().sort(byDateDesc);
    latest.innerHTML = sorted.slice(0,12).map(cardHTML).join("");
    const wire = $("#latest-wire");
    if(wire){
      wire.innerHTML = sorted.slice(12).map(a =>
        '<a class="wire-row" href="' + href(a) + '">' +
          '<span class="w-date">' + frDate(a.date).replace(" 2026","") + '</span>' +
          '<span class="w-cat">' + a.cat + '</span>' +
          '<span class="w-title">' + a.title + '</span>' +
          '<span class="w-arr">→</span>' +
        '</a>'
      ).join("");
    }
  }

  /* ---------- page articles : filtres + recherche locale ---------- */
  const grid = $("#articles-grid");
  if(grid && window.ARTICLES){
    const chipsWrap = $("#chips"), input = $("#filter-input"), count = $("#art-count"), empty = $("#empty-state");
    const cats = ["Tous"].concat(Array.from(new Set(ARTICLES.map(a => a.cat))));
    let state = {cat:"Tous", q:""};
    /* filtres profonds : articles.html?cat=Spas / ?q=Corse (depuis la landing) */
    const params = new URLSearchParams(location.search);
    const pCat = params.get("cat"), pQ = params.get("q");
    if(pCat){
      const m = cats.find(c => norm(c) === norm(pCat));
      if(m) state.cat = m;
    }
    if(pQ){ state.q = pQ; input.value = pQ; }
    chipsWrap.innerHTML = cats.map(c =>
      '<button class="chip' + (c===state.cat ? " on" : "") + '" data-cat="' + c + '">' + c + '</button>'
    ).join("");
    function apply(){
      const q = norm(state.q);
      const res = ARTICLES.slice().sort(byDateDesc).filter(a =>
        (state.cat === "Tous" || a.cat === state.cat) &&
        (!q || norm(a.title + " " + a.dest + " " + (a.region || "") + " " + a.cat).includes(q))
      );
      grid.innerHTML = res.map(cardHTML).join("");
      grid.style.display = res.length ? "" : "none";
      empty.style.display = res.length ? "none" : "";
      count.textContent = res.length + (res.length > 1 ? " articles" : " article") +
        (state.cat !== "Tous" ? " · " + state.cat : "") +
        " · mis à jour quotidiennement";
    }
    chipsWrap.addEventListener("click", (e) => {
      const b = e.target.closest(".chip");
      if(!b) return;
      state.cat = b.dataset.cat;
      $$(".chip", chipsWrap).forEach(c => c.classList.toggle("on", c === b));
      apply();
    });
    input.addEventListener("input", () => { state.q = input.value; apply(); });
    apply();
  }

  /* ---------- page contact : formulaire EmailJS ---------- */
  const cform = $("#contact-form");
  if(cform){
    const EMAILJS = {pub:"E7cFvIw50eYZ8er2v", service:"service_urokw1i", template:"template_4n5km5l"};
    const status = $("#form-status"), btn = $("#form-send"), lbl = $(".lbl", btn);
    const success = $("#form-success"), again = $("#form-again");
    if(window.emailjs){ emailjs.init({publicKey: EMAILJS.pub}); }
    function setStatus(msg, err){
      status.textContent = msg;
      status.classList.toggle("err", !!err);
    }
    function showSuccess(){
      cform.hidden = true;
      success.hidden = false;
      success.scrollIntoView({block:"center", behavior:"smooth"});
    }
    again.addEventListener("click", () => {
      cform.reset();
      btn.disabled = false; lbl.textContent = "Envoyer";
      setStatus("Champs requis : nom, e-mail valide et message.", false);
      success.hidden = true;
      cform.hidden = false;
    });
    cform.addEventListener("submit", (e) => {
      e.preventDefault();
      const f = cform.elements;
      if(f.website.value){ showSuccess(); return; } /* honeypot : on fait semblant */
      const name = f.name.value.trim(), email = f.email.value.trim(), message = f.message.value.trim();
      if(!name || !message || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){
        setStatus("Il manque un nom, un e-mail valide ou un message.", true);
        return;
      }
      if(!window.emailjs){
        setStatus("Service d'envoi indisponible, réessayez dans un instant.", true);
        return;
      }
      btn.disabled = true; lbl.textContent = "Envoi…";
      setStatus("Le message prend l'ascenseur de service…", false);
      /* les variables couvrent les conventions de template EmailJS les plus courantes */
      emailjs.send(EMAILJS.service, EMAILJS.template, {
        name: name, from_name: name,
        email: email, from_email: email, reply_to: email,
        subject: f.subject.value, title: f.subject.value,
        message: message
      }).then(showSuccess).catch((err) => {
        btn.disabled = false; lbl.textContent = "Envoyer";
        setStatus("L'envoi a échoué (" + ((err && (err.text || err.status)) || "erreur réseau") + "). Réessayez dans un instant.", true);
      });
    });
  }

  /* ---------- recherche : overlay global ---------- */
  if(window.ARTICLES){
    const so = document.createElement("div");
    so.className = "search-overlay";
    so.id = "search-overlay";
    so.setAttribute("aria-hidden", "true");
    so.innerHTML =
      '<button class="close" id="close-search">Fermer ✕</button>' +
      '<div class="search-box">' +
        '<span class="tag">Rechercher dans Meilleurs.</span>' +
        '<input class="search-input" id="search-input" type="search" autocomplete="off" spellcheck="false" ' +
          'placeholder="Une destination, un hôtel, un rituel…" aria-label="Rechercher un article">' +
        '<div class="s-results" id="s-results"></div>' +
        '<p class="s-hint">Échap pour fermer · essayez «&nbsp;spa&nbsp;», «&nbsp;Paris&nbsp;», «&nbsp;palmarès&nbsp;»</p>' +
      '</div>';
    document.body.appendChild(so);
    const sInput = $("#search-input", so), sRes = $("#s-results", so);

    function renderSearch(q){
      const n = norm(q);
      if(!n){
        sRes.innerHTML = ARTICLES.slice().sort(byDateDesc).slice(0,5).map(rowHTML).join("") +
          '<p class="s-hint" style="margin-top:14px">Dernières parutions, tapez pour affiner.</p>';
        return;
      }
      const res = ARTICLES.slice().sort(byDateDesc).filter(a =>
        norm(a.title + " " + a.dest + " " + (a.region || "") + " " + a.cat).includes(n)
      ).slice(0,8);
      sRes.innerHTML = res.length
        ? res.map(rowHTML).join("")
        : '<p class="s-empty">Rien pour «&nbsp;' + q.replace(/</g,"&lt;") + '&nbsp;»… mais la rédaction prend note.</p>';
    }
    function rowHTML(a){
      return '<a class="s-row" href="' + href(a) + '">' +
        '<span class="s-cat">' + a.cat + '</span>' +
        '<span class="s-title">' + a.title + '</span>' +
        '<span class="s-meta">' + a.dest + ' · ' + frDate(a.date) + '</span>' +
      '</a>';
    }
    function openSearch(){
      if(window.__closeMenu) window.__closeMenu();
      so.classList.add("open");
      so.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      renderSearch(sInput.value);
      setTimeout(() => sInput.focus(), 350);
    }
    function closeSearch(){
      so.classList.remove("open");
      so.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    }
    $$("[data-search-open]").forEach(el => el.addEventListener("click", (e) => { e.preventDefault(); openSearch(); }));
    $("#close-search", so).addEventListener("click", closeSearch);
    sInput.addEventListener("input", () => renderSearch(sInput.value));
    document.addEventListener("keydown", (e) => {
      if(e.key === "Escape" && so.classList.contains("open")) closeSearch();
      if((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k"){ e.preventDefault(); openSearch(); }
      if(e.key === "/" && !/^(input|textarea)$/i.test(document.activeElement.tagName)){ e.preventDefault(); openSearch(); }
    });
  }
})();
