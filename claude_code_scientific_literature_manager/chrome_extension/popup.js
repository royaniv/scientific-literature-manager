// popup.js — Paper Organizer Chrome Extension
// Naming logic mirrors paper_organizer/core.py

const CATEGORIES = {
  Micelles:   ["micelle","micelles","micellar","amphiphile","vesicle","composome","gard"],
  Chiral:     ["chiral","chirality","enantiomer","homochirality"],
  Soup:       ["origin of life","prebiotic","primordial soup","autocatalysis"],
  Astro:      ["astrobiology","biosignature","enceladus","europa","icy moon","mars"],
  Light:      ["light","photochemical","photochemistry","photolysis","ultraviolet"],
  OrganBactr: ["bacteria","bacterial","microbe","microbial","microorganism"],
  General:    [],
};

const DEFAULTS = { subfolder: "organized_papers", prefix: "CB", nextNumber: 1, digits: 3, saveAs: false };

const $ = id => document.getElementById(id);
const el = {
  pdfUrl: $("pdfUrl"), title: $("title"), author: $("author"),
  journal: $("journal"), year: $("year"), category: $("category"),
  catBadge: $("catBadge"), prefix: $("prefix"), nextNumber: $("nextNumber"),
  digits: $("digits"), subfolder: $("subfolder"), saveAs: $("saveAs"),
  filenamePreview: $("filenamePreview"), downloadBtn: $("downloadBtn"), status: $("status"),
};

// ── Naming helpers (mirrors core.py) ────────────────────────────────────────

const LOWER = new Set(["a","an","and","at","by","for","from","in","of","on","or","the","to","with"]);
const JSTOP = new Set(["a","and","for","in","international","journal","of","on","the"]);

const sanitize = t => String(t||"").replace(/[\\/*?:"<>|]/g,"").replace(/\s+/g," ").trim().replace(/[. ]+$/g,"");
const titleCase = t => sanitize(t).toLowerCase().split(/\s+/).filter(Boolean)
  .map((w,i) => (i>0 && LOWER.has(w)) ? w : w[0].toUpperCase()+w.slice(1)).join(" ") || "Unknown Title";
const shorten = (t,n=8) => sanitize(t).split(/\s+/).filter(Boolean).slice(0,n).join(" ");
const abbreviate = j => {
  const words = sanitize(j).replace(/[^\w\s]/g," ").split(/\s+/)
    .map(w=>w.replace(/[^A-Za-z0-9]/g,""))
    .filter(w => w.length>=3 && !JSTOP.has(w.toLowerCase()));
  if(!words.length) return "Unknown";
  return words.slice(0,4).map(w => /^[A-Z]+$/.test(w)&&w.length<=4 ? w : w.slice(0,1).toUpperCase()+w.slice(1,4).toLowerCase()).join(" ");
};
const kwMatch = (kw,hay) => {
  const parts = kw.trim().toLowerCase().split(/\s+/).map(p=>p.replace(/[.*+?^${}()|[\]\\]/g,"\\$&"));
  return new RegExp(`(^|[^a-z0-9])${parts.join("[\\s-]+")}([^a-z0-9]|$)`,"i").test(hay);
};

function detectCategory(meta) {
  const hay = [meta.title, meta.journal, meta.author, meta.pageText].join(" ").toLowerCase();
  for (const [cat, kws] of Object.entries(CATEGORIES)) {
    if (cat === "General") continue;
    if (kws.some(kw => kwMatch(kw, hay))) return cat;
  }
  return "General";
}

function buildFilename() {
  const pfx  = el.prefix.value.trim() || "CB";
  const num  = Math.max(1, parseInt(el.nextNumber.value||"1",10));
  const digs = Math.max(1, parseInt(el.digits.value||"3",10));
  const id   = `${pfx}${String(num).padStart(digs,"0")}`;
  const yr   = String(el.year.value||"0000");
  const yrS  = yr.length>=2 ? yr.slice(-2) : "00";
  return sanitize(
    `${id} ${sanitize(el.author.value)||"Unknown"}, ${titleCase(shorten(el.title.value))}, ${abbreviate(el.journal.value)} ${yrS}.pdf`
  );
}

function refreshUI() {
  const name = buildFilename();
  el.filenamePreview.textContent = name || "—";
}

// ── Page scraping ────────────────────────────────────────────────────────────

function collectPageMeta() {
  const m = (...sels) => { for (const s of sels) { const e=document.querySelector(s); const v=e?.content||e?.href||""; if(v.trim()) return v.trim(); } return ""; };
  const authors = [...document.querySelectorAll('meta[name="citation_author"]')].map(e=>e.content).filter(Boolean);
  let pdf = m('meta[name="citation_pdf_url"]','meta[name="bepress_citation_pdf_url"]','link[type="application/pdf"]')
    || [...document.querySelectorAll("a[href]")].map(a=>a.href).find(h=>/\.pdf($|[?#])/i.test(h)) || "";
  try { pdf = pdf ? new URL(pdf,location.href).href : ""; } catch(_) {}
  return {
    title: m('meta[name="citation_title"]','meta[property="og:title"]','meta[name="dc.title"]') || document.title,
    journal: m('meta[name="citation_journal_title"]','meta[name="prism.publicationName"]'),
    year: (m('meta[name="citation_publication_date"]','meta[name="citation_online_date"]','meta[name="dc.date"]').match(/\d{4}/)||[""])[0],
    author: authors.length ? authors[authors.length-1] : "",
    pdfUrl: pdf,
    pageText: (document.body?.innerText||"").slice(0,10000),
  };
}

// ── Init ─────────────────────────────────────────────────────────────────────

function populateCategories() {
  for (const cat of Object.keys(CATEGORIES)) {
    const o = document.createElement("option");
    o.value = cat; o.textContent = cat;
    el.category.appendChild(o);
  }
}

async function loadSettings() {
  const s = await chrome.storage.local.get(DEFAULTS);
  el.prefix.value     = s.prefix;
  el.nextNumber.value = s.nextNumber;
  el.digits.value     = s.digits;
  el.subfolder.value  = s.subfolder;
  el.saveAs.checked   = s.saveAs;
}

async function saveSettings() {
  await chrome.storage.local.set({
    subfolder: el.subfolder.value,
    prefix: el.prefix.value,
    nextNumber: Math.max(1, parseInt(el.nextNumber.value||"1",10)),
    digits: Math.max(1, parseInt(el.digits.value||"3",10)),
    saveAs: el.saveAs.checked,
  });
}

async function loadPageMeta() {
  const tabs = await chrome.tabs.query({active:true,currentWindow:true});
  const tab  = tabs[0];
  let meta = {title:tab?.title||"",journal:"",year:"",author:"",pdfUrl:tab?.url||"",pageText:""};
  try {
    const [r] = await chrome.scripting.executeScript({target:{tabId:tab.id},func:collectPageMeta});
    Object.assign(meta, r?.result||{});
  } catch(_) {}
  if (!meta.pdfUrl || /\.pdf($|[?#])/i.test(tab.url)) meta.pdfUrl = tab.url;

  el.pdfUrl.value  = meta.pdfUrl;
  el.title.value   = meta.title;
  el.journal.value = meta.journal;
  el.year.value    = meta.year;
  el.author.value  = meta.author || "Unknown";

  const detected = detectCategory(meta);
  el.category.value = detected;
  el.catBadge.textContent = detected;
  refreshUI();
}

async function download() {
  const url = el.pdfUrl.value.trim();
  if (!url) { el.status.textContent = "No PDF URL found — paste one manually."; return; }
  const sub  = sanitize(el.subfolder.value).replace(/^\/+|\/+$/g,"");
  const name = sanitize(el.filenamePreview.textContent) || buildFilename();
  const path = sub ? `${sub}/${name}` : name;

  el.downloadBtn.disabled  = true;
  el.status.textContent    = "Starting download…";
  await saveSettings();

  chrome.downloads.download({url, filename:path, saveAs:el.saveAs.checked, conflictAction:"uniquify"}, async id => {
    el.downloadBtn.disabled = false;
    if (chrome.runtime.lastError) { el.status.textContent = chrome.runtime.lastError.message; return; }
    const next = Math.max(1, parseInt(el.nextNumber.value||"1",10)) + 1;
    el.nextNumber.value = next;
    await chrome.storage.local.set({nextNumber: next});
    refreshUI();
    el.status.textContent = `Saved as: ${name}`;
  });
}

async function init() {
  populateCategories();
  await loadSettings();
  await loadPageMeta();
  for (const e of [el.title,el.author,el.journal,el.year,el.prefix,el.nextNumber,el.digits,el.category]) {
    e.addEventListener("input",  refreshUI);
    e.addEventListener("change", refreshUI);
  }
  el.category.addEventListener("change", () => { el.catBadge.textContent = el.category.value; });
  el.downloadBtn.addEventListener("click", download);
}

init();
