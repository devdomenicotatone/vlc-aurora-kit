/* Aurora - logica dell'interfaccia web di VLC (API Lua HTTP di VLC 3.x: requests/status.json, playlist.json, browse.json) */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const el = {
    conn: $("conn"), connText: $("connText"), host: $("host"), vlcVersion: $("vlcVersion"),
    art: $("art"), artImg: $("artImg"), title: $("title"), subtitle: $("subtitle"), stateBadge: $("stateBadge"), rateBadge: $("rateBadge"),
    seek: $("seek"), tCur: $("tCur"), tTot: $("tTot"),
    bShuffle: $("bShuffle"), bPrev: $("bPrev"), bPlay: $("bPlay"), bNext: $("bNext"), bRepeat: $("bRepeat"),
    bStop: $("bStop"), bMute: $("bMute"), vol: $("vol"), volPct: $("volPct"), bSlower: $("bSlower"), bRate: $("bRate"), bFaster: $("bFaster"), bFull: $("bFull"),
    openForm: $("openForm"), openUrl: $("openUrl"), bEnqueue: $("bEnqueue"),
    plList: $("plList"), plCount: $("plCount"), plEmpty: $("plEmpty"), bClear: $("bClear"),
    crumbs: $("crumbs"), brList: $("brList"),
    eqOn: $("eqOn"), eqOnLabel: $("eqOnLabel"), eqPreset: $("eqPreset"), eqBands: $("eqBands"),
    toast: $("toast"), bHelp: $("bHelp"),
    bPhone: $("bPhone"), phoneDlg: $("phoneDlg"), bPhoneClose: $("bPhoneClose"), phoneQr: $("phoneQr"), phoneUrl: $("phoneUrl"),
    bPhoneCopy: $("bPhoneCopy"), phoneAlt: $("phoneAlt"), phonePw: $("phonePw"), bPhonePw: $("bPhonePw"), phoneNote: $("phoneNote"),
  };
  const MEDIA_EXT = /\.(mp4|m4v|mkv|avi|mov|wmv|webm|flv|mpg|mpeg|ts|m2ts|mts|vob|3gp|ogv|iso|mp3|flac|m4a|aac|ogg|oga|opus|wav|wma|aiff|ape|mka|m3u|m3u8|pls|xspf|srt|ass)$/i;
  const RATES = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3];

  let status = null;
  let seeking = false;         // l'utente sta trascinando la barra
  let volDragging = false;
  let lastVolume = 256;
  let currentPlid = null;
  let eqDragging = null;       // indice banda in trascinamento
  let plSignature = "";
  let browseUri = "file:///";
  let failures = 0;
  // URL assoluti dall'origine: se la pagina e' stata aperta con credenziali nell'indirizzo, i percorsi relativi
  // verrebbero rifiutati da fetch(); l'origine non le contiene mai.
  const BASE = location.origin + location.pathname.replace(/[^/]*$/, "");
  const api = (p) => BASE + p;

  // ------------------------------------------------------------ utilita'
  const fmt = (s) => {
    s = Math.max(0, Math.floor(Number(s) || 0));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
    return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(x).padStart(2, "0");
  };
  const esc = (t) => String(t == null ? "" : t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const setRange = (input, value) => { input.value = value; const p = (input.max > input.min) ? ((value - input.min) / (input.max - input.min)) * 100 : 0; input.style.setProperty("--p", p + "%"); };
  let toastTimer = 0;
  const toast = (msg, ms = 2600) => { el.toast.textContent = msg; el.toast.classList.remove("hidden"); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.toast.classList.add("hidden"), ms); };

  async function getJSON(url) {
    const r = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }
  // comando all'API: ritorna il nuovo stato
  async function cmd(name, params = {}) {
    const q = new URLSearchParams({ command: name, ...params });
    try {
      const st = await getJSON(api("requests/status.json?" + q.toString()));
      applyStatus(st);
      return st;
    } catch (e) {
      toast("Comando non riuscito: " + e.message);
      throw e;
    }
  }

  // ------------------------------------------------------------ stato
  function setConn(ok) {
    el.conn.classList.toggle("ok", ok);
    el.conn.classList.toggle("ko", !ok);
    el.connText.textContent = ok ? "collegato" : "VLC non raggiungibile";
  }

  function metaOf(st) {
    const m = (st.information && st.information.category && st.information.category.meta) || {};
    return m;
  }

  function applyStatus(st) {
    status = st;
    const playing = st.state === "playing", paused = st.state === "paused", stopped = !playing && !paused;
    const meta = metaOf(st);
    const name = meta.title || meta.filename || (stopped ? "Nessun elemento in riproduzione" : "Elemento senza nome");
    el.title.textContent = name;
    const parts = [];
    if (meta.artist) parts.push(meta.artist);
    if (meta.album) parts.push(meta.album);
    if (meta.now_playing) parts.push(meta.now_playing);
    el.subtitle.textContent = parts.length ? parts.join(" · ") : (stopped ? "Scegli dalla playlist, sfoglia il PC o incolla un indirizzo" : (meta.filename && meta.title ? meta.filename : ""));
    el.stateBadge.textContent = playing ? "In riproduzione" : paused ? "In pausa" : "Fermo";
    el.stateBadge.className = "badge " + (playing ? "playing" : paused ? "paused" : "");
    el.bPlay.classList.toggle("playing", playing);
    el.bPlay.title = playing ? "Pausa" : "Riproduci";
    // tempo e posizione
    const len = Number(st.length) || 0, t = Number(st.time) || 0;
    if (!seeking) {
      el.seek.disabled = stopped || len <= 0;
      setRange(el.seek, len > 0 ? Math.round((t / len) * 1000) : 0);
      el.tCur.textContent = fmt(t);
    }
    el.tTot.textContent = len > 0 ? fmt(len) : (playing || paused ? "live" : "0:00");
    // volume (0..512 = 0..200%; 256 = 100%)
    const v = Number(st.volume) || 0;
    if (!volDragging) { setRange(el.vol, Math.min(320, v)); }
    el.volPct.textContent = Math.round(v / 2.56) + "%";
    el.bMute.classList.toggle("on", v === 0);
    if (v > 0) lastVolume = v;
    // velocita'
    const rate = Number(st.rate) || 1;
    el.bRate.textContent = rate.toFixed(2) + "×";
    el.bRate.classList.toggle("changed", Math.abs(rate - 1) > 0.01);
    el.rateBadge.classList.toggle("hidden", Math.abs(rate - 1) < 0.01 || stopped);
    el.rateBadge.textContent = rate.toFixed(2) + "×";
    // casuale / ripetizione (loop = tutta la playlist, repeat = un solo elemento)
    el.bShuffle.classList.toggle("on", !!st.random);
    const rep = st.repeat ? "one" : st.loop ? "all" : "off";
    el.bRepeat.classList.toggle("on", rep !== "off");
    el.bRepeat.classList.toggle("one", rep === "one");
    el.bRepeat.title = "Ripetizione: " + (rep === "one" ? "un solo elemento" : rep === "all" ? "tutta la playlist" : "spenta");
    el.bFull.classList.toggle("on", !!st.fullscreen);
    el.vlcVersion.textContent = "VLC " + (st.version || "");
    // copertina
    const plid = st.currentplid;
    if (plid !== currentPlid) {
      currentPlid = plid;
      if (plid && plid > 0 && !stopped) {
        el.artImg.src = api("art?item=" + encodeURIComponent(plid) + "&_=" + Date.now());
      } else {
        el.art.classList.remove("has-art"); el.artImg.removeAttribute("src");
      }
    }
    if (stopped) el.art.classList.remove("has-art");
    applyEqualizer(st.equalizer);
  }
  el.artImg.addEventListener("load", () => el.art.classList.add("has-art"));
  el.artImg.addEventListener("error", () => el.art.classList.remove("has-art"));

  // ------------------------------------------------------------ playlist
  function flatten(node, out) {
    if (!node) return out;
    if (node.type === "leaf") out.push(node);
    (node.children || []).forEach((c) => flatten(c, out));
    return out;
  }
  function renderPlaylist(root) {
    const main = (root.children || [])[0] || root;          // primo nodo: la scaletta
    const items = flatten(main, []);
    const sig = items.map((i) => i.id + ":" + (i.current || "") + ":" + i.name).join("|");
    if (sig === plSignature) return;
    plSignature = sig;
    el.plCount.textContent = items.length ? (items.length === 1 ? "1 elemento" : items.length + " elementi") : "Playlist vuota";
    el.plEmpty.classList.toggle("hidden", items.length > 0);
    el.plList.innerHTML = items.map((i) => {
      const cur = i.current ? " current" : "";
      const dur = Number(i.duration) > 0 ? fmt(i.duration) : "";
      const isAudio = /\.(mp3|flac|m4a|aac|ogg|oga|opus|wav|wma|aiff|ape)$/i.test(i.uri || "");
      return `<li class="item${cur}" data-id="${esc(i.id)}" title="${esc(i.uri || "")}">
        <span class="ico"><svg><use href="#${i.current ? "i-play" : isAudio ? "i-note" : "i-film"}"/></svg></span>
        <span class="name">${esc(i.name)}</span><span class="dur">${dur}</span>
        <button class="act danger" data-del="${esc(i.id)}" title="Rimuovi"><svg><use href="#i-trash"/></svg></button></li>`;
    }).join("");
    const cur = el.plList.querySelector(".current");
    if (cur) cur.scrollIntoView({ block: "nearest" });
  }
  async function refreshPlaylist() {
    try { renderPlaylist(await getJSON(api("requests/playlist.json"))); } catch (e) { /* silenzioso: lo stato segnala gia' il problema */ }
  }
  el.plList.addEventListener("click", async (ev) => {
    const del = ev.target.closest("[data-del]");
    if (del) { ev.stopPropagation(); await cmd("pl_delete", { id: del.dataset.del }); plSignature = ""; refreshPlaylist(); return; }
    const li = ev.target.closest(".item");
    if (li) { await cmd("pl_play", { id: li.dataset.id }); plSignature = ""; setTimeout(refreshPlaylist, 400); }
  });
  el.bClear.addEventListener("click", async () => { if (confirm("Svuotare la playlist?")) { await cmd("pl_empty"); plSignature = ""; refreshPlaylist(); } });

  // ------------------------------------------------------------ sfoglia
  function crumbsOf(uri) {
    const parts = [];
    let p = uri.replace(/^file:\/\/\//, "");
    try { p = decodeURIComponent(p); } catch (e) { /* lascia com'e' */ }
    const segs = p.split("/").filter(Boolean);
    let acc = "file:///";
    parts.push({ name: "PC", uri: acc });
    segs.forEach((s) => { acc += encodeURIComponent(s).replace(/%3A/g, ":") + "/"; parts.push({ name: s, uri: acc }); });
    return parts;
  }
  async function browse(uri) {
    browseUri = uri;
    el.crumbs.innerHTML = crumbsOf(uri).map((c, i, a) => (i === a.length - 1
      ? `<span class="here">${esc(c.name)}</span>`
      : `<button data-uri="${esc(c.uri)}">${esc(c.name)}</button><span class="sepc">›</span>`)).join("");
    el.brList.innerHTML = `<p class="empty">Caricamento…</p>`;
    let data;
    try { data = await getJSON(api("requests/browse.json?uri=" + encodeURIComponent(uri))); }
    catch (e) { el.brList.innerHTML = `<p class="empty">Impossibile leggere la cartella.</p>`; return; }
    const els = (data.element || []).filter((e) => e.type === "dir" ? e.name !== "." : MEDIA_EXT.test(e.name));
    els.sort((a, b) => (a.type === b.type ? a.name.localeCompare(b.name, "it", { numeric: true, sensitivity: "base" }) : a.type === "dir" ? -1 : 1));
    if (!els.length) { el.brList.innerHTML = `<p class="empty">Nessun file multimediale qui.</p>`; return; }
    el.brList.innerHTML = els.map((e) => {
      const up = e.name === "..";
      const isDir = e.type === "dir";
      const audio = !isDir && /\.(mp3|flac|m4a|aac|ogg|oga|opus|wav|wma|aiff|ape)$/i.test(e.name);
      return `<li class="item${isDir ? " dir" : ""}" data-uri="${esc(e.uri)}" data-type="${isDir ? "dir" : "file"}" title="${esc(e.path || "")}">
        <span class="ico"><svg><use href="#${up ? "i-up" : isDir ? "i-folder" : audio ? "i-note" : "i-film"}"/></svg></span>
        <span class="name">${esc(up ? "Cartella superiore" : e.name.replace(/[\\/]$/, ""))}</span>
        ${isDir ? "" : `<button class="act" data-enqueue="${esc(e.uri)}" title="Aggiungi alla playlist"><svg><use href="#i-plus"/></svg></button>`}
      </li>`;
    }).join("");
  }
  el.crumbs.addEventListener("click", (ev) => { const b = ev.target.closest("button[data-uri]"); if (b) browse(b.dataset.uri); });
  el.brList.addEventListener("click", async (ev) => {
    const enq = ev.target.closest("[data-enqueue]");
    if (enq) { ev.stopPropagation(); await cmd("in_enqueue", { input: enq.dataset.enqueue }); toast("Aggiunto alla playlist"); plSignature = ""; refreshPlaylist(); return; }
    const li = ev.target.closest(".item");
    if (!li) return;
    if (li.dataset.type === "dir") browse(li.dataset.uri);
    else { await cmd("in_play", { input: li.dataset.uri }); toast("Riproduzione avviata"); plSignature = ""; setTimeout(refreshPlaylist, 500); }
  });

  // ------------------------------------------------------------ equalizzatore
  const EQ_LABELS = ["Pre", "60", "170", "310", "600", "1k", "3k", "6k", "12k", "14k", "16k"];
  function buildEq() {
    el.eqBands.innerHTML = EQ_LABELS.map((l, i) => `<div class="band${i === 0 ? " pre" : ""}">
      <span class="val" id="eqv${i}">0.0</span>
      <input type="range" min="-20" max="20" step="0.1" value="0" data-band="${i - 1}" aria-label="${l}">
      <span class="lbl">${l}</span></div>`).join("");
    el.eqBands.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("input", () => { eqDragging = inp; $("eqv" + (Number(inp.dataset.band) + 1)).textContent = Number(inp.value).toFixed(1); });
      inp.addEventListener("change", async () => {
        const b = Number(inp.dataset.band);
        if (b < 0) await cmd("preamp", { val: inp.value }); else await cmd("equalizer", { band: b, val: inp.value });
        eqDragging = null;
      });
    });
  }
  function applyEqualizer(eq) {
    const enabled = eq && !Array.isArray(eq) && eq.bands;
    el.eqOn.checked = !!enabled;
    el.eqOnLabel.textContent = enabled ? "Attivo" : "Spento";
    el.eqBands.querySelectorAll("input").forEach((inp) => { inp.disabled = !enabled; });
    if (!enabled) return;
    // preimpostazioni
    if (eq.presets && el.eqPreset.options.length <= 1) {
      Object.keys(eq.presets).forEach((k) => {
        const id = (k.match(/\d+/) || [""])[0];
        const o = document.createElement("option"); o.value = id; o.textContent = eq.presets[k]; el.eqPreset.appendChild(o);
      });
    }
    const set = (i, v) => {
      const inp = el.eqBands.querySelector(`input[data-band="${i}"]`);
      if (!inp || inp === eqDragging) return;
      inp.value = Number(v).toFixed(1); $("eqv" + (i + 1)).textContent = Number(v).toFixed(1);
    };
    set(-1, eq.preamp);
    Object.keys(eq.bands || {}).forEach((k) => { const id = Number((k.match(/\d+/) || [0])[0]); set(id, eq.bands[k]); });
  }
  el.eqOn.addEventListener("change", () => cmd("enableeq", { val: el.eqOn.checked ? 1 : 0 }));
  el.eqPreset.addEventListener("change", async () => { if (el.eqPreset.value !== "") { await cmd("setpreset", { val: el.eqPreset.value }); el.eqPreset.value = ""; } });

  // ------------------------------------------------------------ comandi
  el.bPlay.addEventListener("click", () => {
    if (!status) return;
    if (status.state === "stopped") cmd("pl_play"); else cmd("pl_pause");
  });
  el.bStop.addEventListener("click", () => cmd("pl_stop"));
  el.bPrev.addEventListener("click", () => cmd("pl_previous"));
  el.bNext.addEventListener("click", () => cmd("pl_next"));
  el.bShuffle.addEventListener("click", () => cmd("pl_random"));
  el.bRepeat.addEventListener("click", () => {
    if (!status) return;
    if (status.repeat) cmd("pl_repeat");          // un elemento -> spento
    else if (status.loop) cmd("pl_repeat");       // playlist -> un elemento (l'API spegne loop da sola)
    else cmd("pl_loop");                          // spento -> playlist
  });
  el.bFull.addEventListener("click", () => cmd("fullscreen"));
  el.bMute.addEventListener("click", () => {
    const v = status ? Number(status.volume) : 0;
    cmd("volume", { val: v > 0 ? 0 : (lastVolume || 256) });
  });
  el.vol.addEventListener("input", () => { volDragging = true; setRange(el.vol, el.vol.value); el.volPct.textContent = Math.round(el.vol.value / 2.56) + "%"; });
  el.vol.addEventListener("change", async () => { await cmd("volume", { val: el.vol.value }); volDragging = false; });
  el.seek.addEventListener("input", () => { seeking = true; setRange(el.seek, el.seek.value); if (status) el.tCur.textContent = fmt((el.seek.value / 1000) * (Number(status.length) || 0)); });
  el.seek.addEventListener("change", async () => {
    if (status && Number(status.length) > 0) await cmd("seek", { val: Math.round((el.seek.value / 1000) * Number(status.length)) });
    seeking = false;
  });
  const stepRate = (dir) => {
    const r = status ? Number(status.rate) || 1 : 1;
    let i = RATES.findIndex((x) => Math.abs(x - r) < 0.02);
    if (i < 0) i = RATES.findIndex((x) => x > r) - (dir < 0 ? 1 : 0);
    i = Math.max(0, Math.min(RATES.length - 1, i + dir));
    cmd("rate", { val: RATES[i] });
  };
  el.bSlower.addEventListener("click", () => stepRate(-1));
  el.bFaster.addEventListener("click", () => stepRate(1));
  el.bRate.addEventListener("click", () => cmd("rate", { val: 1 }));
  el.openForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const u = el.openUrl.value.trim(); if (!u) return;
    await cmd("in_play", { input: u }); el.openUrl.value = ""; toast("Riproduzione avviata"); plSignature = ""; setTimeout(refreshPlaylist, 600);
  });
  el.bEnqueue.addEventListener("click", async () => {
    const u = el.openUrl.value.trim(); if (!u) return;
    await cmd("in_enqueue", { input: u }); el.openUrl.value = ""; toast("Aggiunto alla playlist"); plSignature = ""; refreshPlaylist();
  });
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
    document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("active", p.id === "pane-" + t.dataset.tab));
    if (t.dataset.tab === "browse" && !el.brList.children.length) browse(browseUri);
    try { localStorage.setItem("aurora.tab", t.dataset.tab); } catch (e) { /* ignora */ }
  }));
  el.bHelp.addEventListener("click", (ev) => { ev.preventDefault(); toast("Spazio: riproduci/pausa · ← →: ±10 s · ↑ ↓: volume · M: muto · F: schermo intero", 6000); });

  // ------------------------------------------------------------ collega il telefono
  // Il telefono deve aprire la pagina con l'indirizzo del PC nella rete locale. Se questa pagina e' gia' stata aperta
  // cosi', l'indirizzo e' quello della barra; da localhost lo dice VLC (aurora/telefono.json, grazie al plugin del kit).
  const NOTA_RETE = "Se il telefono non si collega: in Windows la rete del PC deve essere impostata come «Privata».";
  const isLocal = /^(localhost|127\.\d+\.\d+\.\d+|\[::1\])$/.test(location.hostname);
  let phone = { hosts: [], host: "", password: "", note: "" };
  const phoneLink = (host) => location.protocol + "//" + host + (location.port ? ":" + location.port : "") + "/";
  function renderPhone() {
    const url = phone.host ? phoneLink(phone.host) : "";
    el.phoneUrl.textContent = url || "indirizzo non disponibile";
    el.bPhoneCopy.classList.toggle("hidden", !url);
    let qr = "";
    try { if (url) qr = AuroraQR.svg(url); } catch (e) { /* indirizzo troppo lungo: resta il testo */ }
    el.phoneQr.innerHTML = qr;
    el.phoneQr.classList.toggle("hidden", !qr);
    el.phoneAlt.classList.toggle("hidden", phone.hosts.length < 2);
    el.phoneAlt.innerHTML = phone.hosts.length < 2 ? "" : "<span>Altri indirizzi del PC:</span>" +
      phone.hosts.map((h) => `<button class="link${h === phone.host ? " on" : ""}" data-host="${esc(h)}">${esc(h)}</button>`).join("");
    el.phonePw.textContent = "••••••••";
    el.bPhonePw.textContent = "Mostra";
    el.bPhonePw.classList.toggle("hidden", !phone.password);
    el.phoneNote.textContent = phone.note;
  }
  async function openPhone() {
    if (!el.phoneDlg.open) { if (el.phoneDlg.showModal) el.phoneDlg.showModal(); else el.phoneDlg.setAttribute("open", ""); }
    let dati = { indirizzi: [], pc: "", password: "" };
    try { dati = await getJSON(api("aurora/telefono.json")); } catch (e) { /* versione del kit senza questo file: si usa quel che si sa */ }
    const hosts = isLocal ? [] : [location.hostname];
    (dati.indirizzi || []).forEach((h) => { if (!hosts.includes(h)) hosts.push(h); });
    let note = NOTA_RETE;
    if (!hosts.length && dati.pc) {
      hosts.push(dati.pc);
      note = "Indirizzo di rete non rilevato: il codice usa il nome del PC. Se il telefono non lo trova, scrivi al suo posto l'indirizzo IPv4 del PC (Impostazioni di Windows → Rete e Internet).";
    } else if (!hosts.length) {
      note = "Indirizzo di rete non rilevato. Sul telefono apri http://<indirizzo IPv4 del PC>" + (location.port ? ":" + location.port : "") + " (lo trovi in Impostazioni di Windows → Rete e Internet).";
    }
    phone = { hosts, host: hosts[0] || "", password: dati.password || "", note };
    renderPhone();
  }
  el.bPhone.addEventListener("click", openPhone);
  el.bPhoneClose.addEventListener("click", () => el.phoneDlg.close());
  el.phoneDlg.addEventListener("click", (ev) => { if (ev.target === el.phoneDlg) el.phoneDlg.close(); });   // clic fuori dal riquadro
  el.phoneAlt.addEventListener("click", (ev) => { const b = ev.target.closest("[data-host]"); if (b) { phone.host = b.dataset.host; renderPhone(); } });
  el.bPhonePw.addEventListener("click", () => {
    const nascosta = el.bPhonePw.textContent === "Mostra";
    el.phonePw.textContent = nascosta ? phone.password : "••••••••";
    el.bPhonePw.textContent = nascosta ? "Nascondi" : "Mostra";
  });
  el.bPhoneCopy.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(el.phoneUrl.textContent); toast("Indirizzo copiato"); }
    catch (e) { const r = document.createRange(); r.selectNodeContents(el.phoneUrl); const s = getSelection(); s.removeAllRanges(); s.addRange(r); toast("Indirizzo selezionato: copialo con Ctrl+C"); }
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.target.matches("input, select, textarea") || el.phoneDlg.open) return;
    const t = Number(status && status.time) || 0;
    switch (ev.key) {
      case " ": ev.preventDefault(); el.bPlay.click(); break;
      case "ArrowRight": ev.preventDefault(); cmd("seek", { val: t + 10 }); break;
      case "ArrowLeft": ev.preventDefault(); cmd("seek", { val: Math.max(0, t - 10) }); break;
      case "ArrowUp": ev.preventDefault(); cmd("volume", { val: Math.min(512, (Number(status && status.volume) || 0) + 13) }); break;
      case "ArrowDown": ev.preventDefault(); cmd("volume", { val: Math.max(0, (Number(status && status.volume) || 0) - 13) }); break;
      case "m": case "M": el.bMute.click(); break;
      case "f": case "F": el.bFull.click(); break;
      default: break;
    }
  });

  // ------------------------------------------------------------ ciclo di aggiornamento
  async function tick() {
    try {
      const st = await getJSON(api("requests/status.json"));
      applyStatus(st);
      if (failures > 0 || !el.conn.classList.contains("ok")) setConn(true);
      failures = 0;
    } catch (e) {
      failures++;
      if (failures >= 2) setConn(false);
    }
    setTimeout(tick, status && status.state === "playing" ? 1000 : 2000);
  }
  async function tickPlaylist() {
    if (document.visibilityState === "visible") await refreshPlaylist();
    setTimeout(tickPlaylist, 4000);
  }

  el.host.textContent = location.hostname || "VLC";
  buildEq();
  setRange(el.vol, 256);
  setRange(el.seek, 0);
  try {
    const t = localStorage.getItem("aurora.tab");
    if (t && document.querySelector(`.tab[data-tab="${t}"]`)) document.querySelector(`.tab[data-tab="${t}"]`).click();
  } catch (e) { /* ignora */ }
  if (location.hash === "#telefono") openPhone();
  tick();
  tickPlaylist();
})();
