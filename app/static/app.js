"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const homeEl = $("#home");
const dropzone = $("#dropzone");
const fileInput = $("#fileInput");
const jobsEl = $("#jobs");
const reviewEl = $("#review");
const segmentsEl = $("#segments");
const player = $("#player");

let current = null;        // progetto aperto
let activeSeg = null;      // segmento in riproduzione
let stopAt = null;         // tempo a cui fermare la riproduzione (per span)
let allProjects = [];      // cache libreria
let APP_INFO = { audio_exts: [], video_exts: [], max_minutes: 60, version: "" };

// ============================================================================
// Info app (formati, versione, autore) — usata per validazione e pannelli
// ============================================================================
async function loadInfo() {
  try { APP_INFO = await (await fetch("/api/info")).json(); } catch { return; }
  const a = (APP_INFO.audio_exts || []).map((e) => e.toUpperCase());
  const v = (APP_INFO.video_exts || []).map((e) => e.toUpperCase());
  const fmt = `Audio: ${a.join(", ")}. Video: ${v.join(", ")} (viene usata solo la traccia audio).`;
  const dz = $("#dzFormats"); if (dz) dz.textContent = fmt;
  const hf = $("#helpFormats"); if (hf) hf.textContent = fmt;
  const av = $("#aboutVersion"); if (av) av.textContent = "versione " + (APP_INFO.version || "—");
  const rep = $("#aboutRepo"); if (rep && APP_INFO.repo) rep.href = APP_INFO.repo;
}

function allowedExts() {
  return [...(APP_INFO.audio_exts || []), ...(APP_INFO.video_exts || [])];
}
function extOf(name) {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i + 1).toLowerCase() : "";
}

// ============================================================================
// Pannelli laterali (Aiuto / Informazioni)
// ============================================================================
function openDrawer(id) {
  const d = $("#" + id);
  if (!d) return;
  d.classList.remove("hidden");
  d.setAttribute("aria-hidden", "false");
}
function closeDrawer(d) {
  d.classList.add("hidden");
  d.setAttribute("aria-hidden", "true");
}
$$("[data-open]").forEach((b) => b.addEventListener("click", () => openDrawer(b.dataset.open)));
$$(".drawer").forEach((d) => {
  d.querySelectorAll("[data-close]").forEach((c) => c.addEventListener("click", () => closeDrawer(d)));
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") $$(".drawer:not(.hidden)").forEach(closeDrawer);
});

// tinte tenui per interlocutore (assegnate per ordine di comparsa)
const SPEAKER_TINTS = [
  { bg: "oklch(0.93 0.045 274)", ink: "oklch(0.4 0.13 274)" },
  { bg: "oklch(0.93 0.05 150)",  ink: "oklch(0.4 0.12 150)" },
  { bg: "oklch(0.93 0.055 50)",  ink: "oklch(0.42 0.13 50)" },
  { bg: "oklch(0.93 0.05 340)",  ink: "oklch(0.42 0.13 340)" },
  { bg: "oklch(0.93 0.05 210)",  ink: "oklch(0.4 0.12 210)" },
];
function speakerTint(name) {
  const i = (current?.speakers || []).indexOf(name);
  return i >= 0 ? SPEAKER_TINTS[i % SPEAKER_TINTS.length] : null;
}

// ============================================================================
// Upload + drag & drop
// ============================================================================
function showDzError(msg) {
  const el = $("#dzError");
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(showDzError._t);
  showDzError._t = setTimeout(() => el.classList.add("hidden"), 6000);
}

async function handleFiles(files) {
  for (const file of [...files]) {
    const ext = extOf(file.name);
    const allowed = allowedExts();
    if (allowed.length && !allowed.includes(ext)) {
      showDzError(`“${file.name}” non è un formato supportato. Usa un file audio o video ` +
        `(${allowed.map((e) => e.toUpperCase()).join(", ")}).`);
      continue;
    }
    const ok = await confirmIfLong(file);
    if (ok) uploadOne(file);
  }
}

// Prova a leggere la durata nel browser: se supera il massimo consigliato, avvisa col tempo
// stimato. Se il browser non sa leggere il formato, non blocca (procede in silenzio).
function confirmIfLong(file) {
  return new Promise((resolve) => {
    const maxMin = APP_INFO.max_minutes || 60;
    const isVideo = (APP_INFO.video_exts || []).includes(extOf(file.name));
    const media = document.createElement(isVideo ? "video" : "audio");
    const url = URL.createObjectURL(file);
    let done = false;
    const finish = (proceed) => {
      if (done) return; done = true;
      URL.revokeObjectURL(url); media.remove();
      resolve(proceed);
    };
    media.preload = "metadata";
    media.onloadedmetadata = () => {
      const min = media.duration / 60;
      if (isFinite(min) && min > maxMin) {
        const wait = Math.round(min * 2); // stima prudente ~2x la durata
        finish(confirm(
          `“${file.name}” dura circa ${Math.round(min)} minuti.\n\n` +
          `La trascrizione potrebbe richiedere ~${wait} minuti su questo computer. ` +
          `Per file molto lunghi conviene dividerli.\n\nVuoi procedere comunque?`));
      } else { finish(true); }
    };
    media.onerror = () => finish(true); // formato non leggibile dal browser: procedi
    media.src = url;
  });
}
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault(); dropzone.classList.remove("drag");
  handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener("change", () => { handleFiles(fileInput.files); fileInput.value = ""; });

async function uploadOne(file) {
  const fd = new FormData();
  fd.append("file", file);
  const row = makeJobRow(file.name);
  const res = await fetch("/api/upload", { method: "POST", body: fd });
  const { id } = await res.json();
  pollProgress(id, row);
}

function makeJobRow(name) {
  const el = document.createElement("div");
  el.className = "job";
  el.innerHTML = `<span class="name"></span>
    <div class="bar"><i></i></div>
    <span class="state">in attesa…</span>`;
  el.querySelector(".name").textContent = name;
  jobsEl.prepend(el);
  return el;
}

async function pollProgress(id, row) {
  const bar = row.querySelector("i");
  const state = row.querySelector(".state");
  const tick = async () => {
    const p = await (await fetch(`/api/progress/${id}`)).json();
    if (p.status === "processing") {
      const pct = p.total ? Math.round((p.done / p.total) * 100) : 5;
      bar.style.width = pct + "%";
      state.textContent = p.total ? `${p.done}/${p.total} segmenti` : "preparazione…";
      setTimeout(tick, 700);
    } else if (p.status === "done") {
      bar.style.width = "100%";
      state.textContent = "completato — apri";
      state.classList.add("done");
      row.classList.add("clickable");
      row.onclick = () => openProject(id);
      loadLibrary();
    } else if (p.status === "error") {
      state.textContent = "errore: " + (p.error || "sconosciuto");
      state.classList.add("error");
    } else {
      setTimeout(tick, 800);
    }
  };
  tick();
}

// ============================================================================
// Libreria progetti (home)
// ============================================================================
const STATUS_LABEL = {
  done: "completato", processing: "in corso",
  error: "errore", interrupted: "interrotto", unknown: "—",
};

async function loadLibrary() {
  try {
    allProjects = await (await fetch("/api/projects")).json();
  } catch { allProjects = []; }
  renderLibrary();
}

function fmtDur(s) {
  if (!s) return "";
  const m = Math.floor(s / 60), sec = Math.round(s % 60);
  return m ? `${m} min ${sec}s` : `${sec}s`;
}
function fmtDate(mtime) {
  try { return new Date(mtime * 1000).toLocaleDateString("it-IT",
    { day: "numeric", month: "short", year: "numeric" }); } catch { return ""; }
}

function renderLibrary() {
  const q = ($("#librarySearch").value || "").toLowerCase();
  const list = $("#library");
  list.innerHTML = "";
  const items = allProjects.filter((p) => (p.name || "").toLowerCase().includes(q));
  $("#libraryEmpty").classList.toggle("hidden", allProjects.length > 0);

  items.forEach((p) => {
    const row = document.createElement("div");
    row.className = "lib-row";
    const openable = p.status === "done" || (p.status === "interrupted" && p.n_segments > 0);

    const main = document.createElement("button");
    main.className = "lib-open";
    main.disabled = !openable;
    main.innerHTML = `<span class="lib-name"></span>
      <span class="lib-meta">
        <span class="badge badge-${p.status}">${STATUS_LABEL[p.status] || p.status}</span>
        <span>${[fmtDur(p.duration), p.n_segments ? p.n_segments + " segmenti" : "", fmtDate(p.created)]
          .filter(Boolean).join(" · ")}</span>
      </span>`;
    main.querySelector(".lib-name").textContent = p.name || "(senza nome)";
    if (openable) main.onclick = () => openProject(p.id);

    const actions = document.createElement("div");
    actions.className = "lib-actions";
    const renameBtn = iconBtn("Rinomina",
      `<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>`,
      () => renameProject(p));
    const delBtn = iconBtn("Elimina",
      `<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>`,
      () => deleteProject(p), true);
    actions.append(renameBtn, delBtn);

    row.append(main, actions);
    list.appendChild(row);
  });
}

function iconBtn(title, paths, onClick, danger = false) {
  const b = document.createElement("button");
  b.className = "icon-btn" + (danger ? " danger" : "");
  b.title = title;
  b.setAttribute("aria-label", title);
  b.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${paths}</svg>`;
  b.onclick = (e) => { e.stopPropagation(); onClick(); };
  return b;
}

async function renameProject(p) {
  const name = prompt("Nuovo nome della trascrizione:", p.name || "");
  if (name === null) return;
  const v = name.trim();
  if (!v || v === p.name) return;
  await fetch(`/api/project/${p.id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: v }),
  });
  loadLibrary();
}

async function deleteProject(p) {
  if (!confirm(`Eliminare definitivamente "${p.name}"?\nL'audio e la trascrizione verranno rimossi dal computer.`))
    return;
  await fetch(`/api/project/${p.id}`, { method: "DELETE" });
  loadLibrary();
}

$("#librarySearch").addEventListener("input", renderLibrary);

// ============================================================================
// Revisione
// ============================================================================
async function openProject(id) {
  current = await (await fetch(`/api/project/${id}`)).json();
  $("#projName").textContent = current.name;
  player.src = `/api/audio/${id}`;
  refreshExportLinks();
  renderSegments();
  renderLegend();
  homeEl.classList.add("hidden");
  reviewEl.classList.remove("hidden");
  window.scrollTo(0, 0);
}

async function reloadProject() {
  if (!current) return;
  const t = player.currentTime;
  current = await (await fetch(`/api/project/${current.id}`)).json();
  renderSegments();
  renderLegend();
  player.currentTime = t || 0;
}

function refreshExportLinks() {
  $("#dlTxt").href = exportUrl(current.id, "txt");
  $("#dlDocx").href = exportUrl(current.id, "docx");
}
function exportUrl(id, ext) {
  const ts = $("#tsChk").checked ? "?timestamps=true" : "";
  return `/api/export/${id}.${ext}${ts}`;
}
$("#tsChk").addEventListener("change", () => { if (current) refreshExportLinks(); });

$("#backBtn").addEventListener("click", () => {
  reviewEl.classList.add("hidden");
  homeEl.classList.remove("hidden");
  player.pause();
  current = null;
  loadLibrary();
});

// rinomina progetto dal titolo
$("#projName").addEventListener("click", async () => {
  const name = prompt("Nuovo nome della trascrizione:", current.name || "");
  if (name === null) return;
  const v = name.trim();
  if (!v || v === current.name) return;
  await fetch(`/api/project/${current.id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: v }),
  });
  current.name = v;
  $("#projName").textContent = v;
});

function fmt(t) {
  const m = Math.floor(t / 60), s = Math.floor(t % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function renderSegments() {
  segmentsEl.innerHTML = "";
  current.segments.forEach((seg) => {
    const el = document.createElement("div");
    el.className = "seg";
    el.dataset.id = seg.id;

    const head = document.createElement("div");
    head.className = "seg-head";
    const time = document.createElement("span");
    time.className = "time";
    time.textContent = `${fmt(seg.start)} – ${fmt(seg.end)}`;
    const chip = makeSpeakerChip(seg);
    const saved = document.createElement("span");
    saved.className = "saved";
    saved.textContent = "salvato";
    head.append(time, chip, saved);

    // LETTERALE (primario, editabile, parole cliccabili)
    const lit = document.createElement("div");
    lit.className = "literal";
    lit.contentEditable = "true";
    lit.spellcheck = false;
    renderWords(lit, seg);
    lit.addEventListener("focus", () => { lit.textContent = seg.literal; });
    lit.addEventListener("blur", () => saveLiteral(seg, lit, head));

    // LEGGIBILE (secondario, sola lettura)
    const read = document.createElement("div");
    read.className = "readable";
    read.textContent = seg.readable || "—";

    el.append(head, lit, read);
    el.addEventListener("click", (e) => {
      if (e.target.closest(".spk-chip") || e.target.closest(".spk-input")) return;
      if (e.target.classList.contains("word")) return;
      if (e.target === lit) return;
      playSpan(seg.start, seg.end, el);
    });
    segmentsEl.appendChild(el);
  });
}

function makeSpeakerChip(seg) {
  const chip = document.createElement("button");
  chip.className = "spk-chip";
  const name = seg.speaker || "";
  chip.textContent = name || "+ interlocutore";
  if (!name) chip.classList.add("empty");
  const tint = speakerTint(name);
  if (tint) { chip.style.background = tint.bg; chip.style.color = tint.ink; }
  chip.onclick = (e) => { e.stopPropagation(); editSpeaker(seg, chip); };
  return chip;
}

function editSpeaker(seg, chip) {
  ensureSpeakerDatalist();
  const input = document.createElement("input");
  input.className = "spk-input";
  input.value = seg.speaker || "";
  input.placeholder = "Interlocutore";
  input.setAttribute("list", "speakerOptions");
  chip.replaceWith(input);
  input.focus();
  input.select();

  let committed = false;
  const commit = async () => {
    if (committed) return; committed = true;
    const val = input.value.trim();
    if (val !== (seg.speaker || "")) {
      seg.speaker = val;
      const r = await fetch(`/api/project/${current.id}/segment/${seg.id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speaker: val }),
      });
      const d = await r.json();
      current.speakers = d.speakers || current.speakers;
    }
    renderSegments();
    renderLegend();
  };
  input.addEventListener("blur", commit, { once: true });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); input.blur(); }
    if (e.key === "Escape") { input.value = seg.speaker || ""; input.blur(); }
  });
}

function ensureSpeakerDatalist() {
  let dl = $("#speakerOptions");
  if (!dl) { dl = document.createElement("datalist"); dl.id = "speakerOptions"; document.body.appendChild(dl); }
  dl.innerHTML = "";
  (current.speakers || []).forEach((s) => {
    const o = document.createElement("option"); o.value = s; dl.appendChild(o);
  });
}

function renderLegend() {
  const box = $("#speakerLegend");
  box.innerHTML = "";
  const speakers = current.speakers || [];
  box.classList.toggle("hidden", speakers.length === 0);
  speakers.forEach((name) => {
    const tint = speakerTint(name);
    const chip = document.createElement("button");
    chip.className = "legend-chip";
    chip.title = "Clicca per rinominare ovunque";
    chip.textContent = name;
    if (tint) { chip.style.background = tint.bg; chip.style.color = tint.ink; }
    chip.onclick = () => renameSpeakerEverywhere(name);
    box.appendChild(chip);
  });
}

async function renameSpeakerEverywhere(old) {
  const name = prompt(`Rinominare "${old}" in tutta la trascrizione:`, old);
  if (name === null) return;
  const v = name.trim();
  if (!v || v === old) return;
  await fetch(`/api/project/${current.id}/speaker/rename`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old, new: v }),
  });
  reloadProject();
}

function renderWords(container, seg) {
  container.innerHTML = "";
  if (seg.words && seg.words.length) {
    seg.words.forEach((w) => {
      const span = document.createElement("span");
      span.className = "word";
      span.textContent = w.w + " ";
      span.addEventListener("click", (e) => {
        e.stopPropagation();
        playSpan(w.start, w.end + 0.15, container.closest(".seg"));
      });
      container.appendChild(span);
    });
  } else {
    container.textContent = seg.literal || "";
  }
}

async function saveLiteral(seg, lit, head) {
  const txt = lit.textContent.trim();
  if (txt === seg.literal) { renderWords(lit, seg); return; }
  seg.literal = txt;
  await fetch(`/api/project/${current.id}/segment/${seg.id}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ literal: txt }),
  });
  seg.words = null; // i timestamp non valgono piu' dopo modifica manuale
  renderWords(lit, seg);
  const saved = head.querySelector(".saved");
  saved.classList.add("show");
  setTimeout(() => saved.classList.remove("show"), 1200);
}

// ============================================================================
// Diarizzazione automatica
// ============================================================================
$("#diarBtn").addEventListener("click", runDiarize);

async function runDiarize() {
  if (!current) return;
  const btn = $("#diarBtn"), label = $("#diarLabel");
  btn.disabled = true;
  label.textContent = "Analisi in corso…";
  await fetch(`/api/project/${current.id}/diarize`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n_speakers: 2 }),
  });
  const tick = async () => {
    const p = await (await fetch(`/api/progress/${current.id}`)).json();
    if (p.phase === "diarize" && p.status === "processing") {
      const pct = p.total ? Math.round((p.done / p.total) * 100) : 0;
      label.textContent = `Analisi… ${pct}%`;
      setTimeout(tick, 600);
    } else if (p.status === "done") {
      label.textContent = "Identifica interlocutori";
      btn.disabled = false;
      await reloadProject();
    } else if (p.status === "error") {
      label.textContent = "Errore nell'analisi";
      btn.disabled = false;
    } else {
      setTimeout(tick, 700);
    }
  };
  tick();
}

// ============================================================================
// Riproduzione per span
// ============================================================================
function playSpan(start, end, segEl) {
  $$(".seg.active").forEach((e) => e.classList.remove("active"));
  if (segEl) { segEl.classList.add("active"); activeSeg = segEl; }
  stopAt = end;
  player.currentTime = start;
  player.play();
}
player.addEventListener("timeupdate", () => {
  if (stopAt !== null && player.currentTime >= stopAt) { player.pause(); stopAt = null; }
});

// ============================================================================
// Scorciatoie da tastiera
// ============================================================================
document.addEventListener("keydown", (e) => {
  if (reviewEl.classList.contains("hidden")) return;
  const editing = document.activeElement && (document.activeElement.isContentEditable ||
                  document.activeElement.tagName === "INPUT");
  if (editing) return;
  if (e.code === "Space") {
    e.preventDefault();
    player.paused ? player.play() : player.pause();
  } else if (e.key.toLowerCase() === "r" && activeSeg) {
    const seg = current.segments[+activeSeg.dataset.id];
    if (seg) playSpan(seg.start, seg.end, activeSeg);
  }
});

// ============================================================================
// Primo avvio: download modelli (una tantum)
// ============================================================================
async function checkSetup() {
  let s;
  try { s = await (await fetch("/api/setup/status")).json(); }
  catch { return true; }  // in caso di dubbio, non bloccare
  if (s.ready) return true;
  showSetup();
  return false;
}

function showSetup() {
  $("#setup").classList.remove("hidden");
  const btn = $("#setupBtn"), prog = $("#setupProgress");
  btn.onclick = async () => {
    btn.disabled = true;
    await fetch("/api/setup/download", { method: "POST" });
    const tick = async () => {
      const s = await (await fetch("/api/setup/status")).json();
      if (s.error) { prog.textContent = "Errore: " + s.error; btn.disabled = false; return; }
      prog.textContent = s.phase || "Scaricamento…";
      if (s.ready && !s.running) {
        $("#setup").classList.add("hidden");
        loadLibrary();
        return;
      }
      setTimeout(tick, 800);
    };
    tick();
  };
}

// ============================================================================
// Primo avvio: disclaimer legale (una tantum)
// ============================================================================
function requireLegal() {
  return new Promise((resolve) => {
    if (APP_INFO.accepted) { resolve(true); return; }
    const ov = $("#legal"), chk = $("#legalChk"), btn = $("#legalBtn");
    ov.classList.remove("hidden");
    chk.onchange = () => { btn.disabled = !chk.checked; };
    btn.onclick = async () => {
      btn.disabled = true;
      try { await fetch("/api/legal/accept", { method: "POST" }); } catch {}
      ov.classList.add("hidden");
      resolve(true);
    };
  });
}

// avvio
(async () => {
  await loadInfo();
  await requireLegal();
  if (await checkSetup()) loadLibrary();
})();
