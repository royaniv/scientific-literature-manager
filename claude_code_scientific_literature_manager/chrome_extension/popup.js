// SLM Chrome Extension — popup.js
// Mirrors the naming logic in slm/rename.py so filenames match
// what the desktop app would produce.

const CATEGORIES = {
  Micelles:   { prefix: "M", keywords: ["micelle","micelles","micellar","amphiphile","vesicle","vesicles","composome","gard"] },
  Chiral:     { prefix: "C", keywords: ["chiral","chirality","enantiomer","homochirality"] },
  Soup:       { prefix: "S", keywords: ["origin of life","prebiotic","primordial soup","autocatalysis","replication"] },
  Astro:      { prefix: "A", keywords: ["astrobiology","biosignature","enceladus","europa","icy moon","mars","ocean world"] },
  Light:      { prefix: "L", keywords: ["light","photochemical","photochemistry","photolysis","photosynthesis","irradiation","ultraviolet"] },
  OrganBactr: { prefix: "O", keywords: ["bacteria","bacterial","microbe","microbial","microorganism","organotroph"] },
  General:    { prefix: "",  keywords: [] },
};

const DEFAULTS = {
  subfolder: "organized_papers",
  prefix: "CB",
  nextNumber: 1,
  digits: 3,
  perCategory: false,
  saveAs: false,
};

const $ = (id) => document.getElementById(id);

const el = {
  pdfUrl:          $("pdfUrl"),
  title:           $("title"),
  author:          $("author"),
  journal:         $("journal"),
  year:            $("year"),
  category:        $("category"),
  prefix:          $("prefix"),
  nextNumber:      $("nextNumber"),
  digits:          $("digits"),
  perCategory:     $("perCategory"),
  subfolder:       $("subfolder"),
  saveAs:          $("saveAs"),
  filenamePreview: $("filenamePreview"),
  downloadBtn:     $("downloadBtn"),
  status:          $("status"),
};

// ── Naming helpers (mirrors slm/rename.py) ─────────────────────────────────

const LOWER_WORDS = new Set(["a","an","and","at","by","for","from","in","of","on","or","the","to","with"]);
const JOURNAL_STOP = new Set(["a","and","for","in","international","journal","of","on","the"]);

function clean(text) {
  return String(text || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function sanitize(text) {
  return clean(text).replace(/[\\/*?:"<>|]/g, "").replace(/[. ]+$/g, "").trim();
}

function titleCase(text) {
  const words = sanitize(text).toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return "Unknown Title";
  return words.map((w, i) => (i > 0 && LOWER_WORDS.has(w)) ? w : w[0].toUpperCase() + w.slice(1)).join(" ");
}

function shorten(text, maxWords = 8) {
  const words = clean(text).split(/\s+/).filter(Boolean);
  return words.slice(0, maxWords).join(" ") || "Unknown Title";
}

function abbreviate(journal) {
  const words = sanitize(journal)
    .replace(/[^\w\s]/g, " ")
    .split(/\s+/)
    .map(w => w.replace(/[^A-Za-z0-9]/g, ""))
    .filter(w => w.length >= 3 && !JOURNAL_STOP.has(w.toLowerCase()));
  if (!words.length) return "Unknown";
  return words.slice(0, 4).map(w =>
    (/^[A-Z]+$/.test(w) && w.length <= 4) ? w : w.slice(0,1).toUpperCase() + w.slice(1,4).toLowerCase()
  ).join(" ");
}

function kwMatches(kw, haystack) {
  const parts = kw.trim().toLowerCase().split(/\s+/).map(p => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  return new RegExp(`(^|[^a-z0-9])${parts.join("[\\s-]+")}([^a-z0-9]|$)`, "i").test(haystack);
}

function detectCategory(meta) {
  const hay = [meta.title, meta.journal, meta.author, meta.pageText].join(" ").toLowerCase();
  for (const [cat, cfg] of Object.entries(CATEGORIES)) {
    if (cat === "General") continue;
    if (cfg.keywords.some(kw => kwMatches(kw, hay))) return cat;
  }
  return "General";
}

function buildFilename() {
  const cat    = el.category.value || "General";
  const catPfx = CATEGORIES[cat]?.prefix ?? "";
  const pfx    = el.perCategory.checked ? catPfx : el.prefix.value.trim();
  const num    = Math.max(1, parseInt(el.nextNumber.value || "1", 10));
  const digs   = Math.max(1, parseInt(el.digits.value || "3", 10));
  const id     = `${pfx}${String(num).padStart(digs, "0")}`;
  const title  = titleCase(shorten(el.title.value));
  const author = sanitize(el.author.value) || "Unknown";
  const jnl    = abbreviate(el.journal.value);
  const yr     = String(el.year.value || "0000");
  const yrShrt = yr.length >= 2 ? yr.slice(-2) : "00";
  return sanitize(`${id} ${author}, ${title}, ${jnl} ${yrShrt}.pdf`);
}

function refreshFilename() {
  el.filenamePreview.value = buildFilename();
}

function downloadPath(filename) {
  const sub = sanitize(el.subfolder.value).replace(/^\/+|\/+$/g, "");
  return sub ? `${sub}/${filename}` : filename;
}

// ── Page scraping ──────────────────────────────────────────────────────────

function collectPageMeta() {
  function metaAttr(...selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      const v = el?.content || el?.href || "";
      if (v.trim()) return v.trim();
    }
    return "";
  }

  const authors = [...document.querySelectorAll('meta[name="citation_author"]')]
    .map(e => e.content).filter(Boolean);

  let pdfLink =
    metaAttr('meta[name="citation_pdf_url"]', 'meta[name="bepress_citation_pdf_url"]', 'link[type="application/pdf"]') ||
    [...document.querySelectorAll("a[href]")].map(a => a.href).find(h => /\.pdf($|[?#])/i.test(h)) || "";

  try { pdfLink = pdfLink ? new URL(pdfLink, location.href).href : ""; } catch (_) {}

  return {
    title:   metaAttr('meta[name="citation_title"]','meta[property="og:title"]','meta[name="dc.title"]') || document.title,
    journal: metaAttr('meta[name="citation_journal_title"]','meta[name="prism.publicationName"]'),
    year:    (metaAttr('meta[name="citation_publication_date"]','meta[name="citation_online_date"]','meta[name="dc.date"]').match(/\d{4}/) || [""])[0],
    author:  authors.length ? authors[authors.length - 1] : "",
    pdfUrl:  pdfLink,
    pageText: (document.body?.innerText || "").slice(0, 10000),
  };
}

// ── Init ───────────────────────────────────────────────────────────────────

function populateCategories() {
  el.category.innerHTML = "";
  for (const cat of Object.keys(CATEGORIES)) {
    const opt = document.createElement("option");
    opt.value = cat;
    opt.textContent = cat;
    el.category.appendChild(opt);
  }
}

async function loadSettings() {
  const s = await chrome.storage.local.get(DEFAULTS);
  el.prefix.value      = s.prefix;
  el.nextNumber.value  = s.nextNumber;
  el.digits.value      = s.digits;
  el.perCategory.checked = s.perCategory;
  el.subfolder.value   = s.subfolder;
  el.saveAs.checked    = s.saveAs;
}

async function saveSettings() {
  await chrome.storage.local.set({
    subfolder:  el.subfolder.value,
    prefix:     el.prefix.value,
    nextNumber: Math.max(1, parseInt(el.nextNumber.value || "1", 10)),
    digits:     Math.max(1, parseInt(el.digits.value || "3", 10)),
    perCategory: el.perCategory.checked,
    saveAs:     el.saveAs.checked,
  });
}

async function loadPageMeta() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tab  = tabs[0];
  let meta = { title: tab?.title || "", journal: "", year: "", author: "", pdfUrl: tab?.url || "", pageText: "" };

  try {
    const [r] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: collectPageMeta });
    Object.assign(meta, r?.result || {});
  } catch (_) { /* blocked on restricted pages */ }

  if (!meta.pdfUrl || /\.pdf($|[?#])/i.test(tab.url)) meta.pdfUrl = tab.url;

  el.pdfUrl.value  = meta.pdfUrl;
  el.title.value   = meta.title;
  el.journal.value = meta.journal;
  el.year.value    = meta.year;
  el.author.value  = meta.author || "Unknown";
  el.category.value = detectCategory(meta);
  refreshFilename();
}

async function download() {
  const url = el.pdfUrl.value.trim();
  if (!url) { el.status.textContent = "No PDF URL — paste one manually."; return; }

  const filename = sanitize(el.filenamePreview.value) || buildFilename();
  el.downloadBtn.disabled = true;
  el.status.textContent   = "Starting download…";

  await saveSettings();
  chrome.downloads.download(
    { url, filename: downloadPath(filename), saveAs: el.saveAs.checked, conflictAction: "uniquify" },
    async (id) => {
      el.downloadBtn.disabled = false;
      if (chrome.runtime.lastError) {
        el.status.textContent = chrome.runtime.lastError.message;
        return;
      }
      const next = Math.max(1, parseInt(el.nextNumber.value || "1", 10)) + 1;
      el.nextNumber.value = next;
      await chrome.storage.local.set({ nextNumber: next });
      refreshFilename();
      el.status.textContent = `Download started (id ${id}).`;
    }
  );
}

async function init() {
  populateCategories();
  await loadSettings();
  await loadPageMeta();

  for (const e of [el.title, el.author, el.journal, el.year, el.prefix,
                   el.nextNumber, el.digits, el.category, el.perCategory, el.subfolder]) {
    e.addEventListener("input", refreshFilename);
    e.addEventListener("change", refreshFilename);
  }
  el.saveAs.addEventListener("change", saveSettings);
  el.downloadBtn.addEventListener("click", download);
}

init();
