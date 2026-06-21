const CATEGORIES = {
  Micelles: {
    prefix: "M",
    keywords: [
      "micelle",
      "micelles",
      "micellar",
      "amphiphile",
      "amphiphiles",
      "vesicle",
      "vesicles",
      "composome",
      "composomes",
      "gard"
    ]
  },
  Chiral: {
    prefix: "C",
    keywords: ["chiral", "chirality", "enantiomer", "enantiomers", "homochirality"]
  },
  Soup: {
    prefix: "S",
    keywords: [
      "origin of life",
      "prebiotic",
      "primordial soup",
      "autocatalysis",
      "replication"
    ]
  },
  Astro: {
    prefix: "A",
    keywords: [
      "astrobiology",
      "biosignature",
      "enceladus",
      "europa",
      "icy moon",
      "mars",
      "ocean world"
    ]
  },
  Light: {
    prefix: "L",
    keywords: [
      "light",
      "photochemical",
      "photochemistry",
      "photolysis",
      "photosynthesis",
      "irradiation",
      "ultraviolet"
    ]
  },
  OrganBactr: {
    prefix: "O",
    keywords: [
      "bacteria",
      "bacterial",
      "microbe",
      "microbes",
      "microbial",
      "microorganism",
      "microorganisms",
      "organotroph",
      "organotrophs"
    ]
  },
  General: {
    prefix: "",
    keywords: []
  }
};

const DEFAULT_SETTINGS = {
  downloadSubfolder: "organized_papers",
  prefix: "CB",
  nextNumber: 1,
  digits: 3,
  useCategoryPrefix: false,
  saveAs: false
};

const fields = {
  pdfUrl: document.getElementById("pdfUrl"),
  title: document.getElementById("title"),
  author: document.getElementById("author"),
  journal: document.getElementById("journal"),
  year: document.getElementById("year"),
  prefix: document.getElementById("prefix"),
  nextNumber: document.getElementById("nextNumber"),
  digits: document.getElementById("digits"),
  category: document.getElementById("category"),
  useCategoryPrefix: document.getElementById("useCategoryPrefix"),
  downloadSubfolder: document.getElementById("downloadSubfolder"),
  saveAs: document.getElementById("saveAs"),
  filename: document.getElementById("filename"),
  downloadButton: document.getElementById("downloadButton"),
  status: document.getElementById("status")
};

function sanitize(text) {
  return String(text || "")
    .replace(/[\\/*?:"<>|]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "");
}

function shortenTitle(title, maxWords = 8) {
  const words = sanitize(title).split(/\s+/).filter(Boolean);
  return words.slice(0, maxWords).join(" ") || "Unknown Title";
}

function titleCaseSmart(text) {
  const lowerWords = new Set(["a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"]);
  const words = sanitize(text).toLowerCase().split(/\s+/).filter(Boolean);
  return words
    .map((word, index) => {
      if (index > 0 && lowerWords.has(word)) {
        return word;
      }
      return word.slice(0, 1).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

function abbreviateJournal(journal) {
  const stopWords = new Set(["a", "and", "for", "in", "international", "journal", "of", "on", "the"]);
  const words = sanitize(journal)
    .replace(/[^\w\s]/g, " ")
    .split(/\s+/)
    .map((word) => word.replace(/[^A-Za-z0-9]/g, ""))
    .filter((word) => word.length >= 3 && !stopWords.has(word.toLowerCase()));

  if (!words.length) {
    return "Unknown";
  }

  return words
    .slice(0, 4)
    .map((word) => {
      if (/^[A-Z]+$/.test(word) && word.length <= 4) {
        return word;
      }
      return word.slice(0, 4).slice(0, 1).toUpperCase() + word.slice(1, 4).toLowerCase();
    })
    .join(" ");
}

function keywordMatches(keyword, haystack) {
  const pattern = keyword
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("[\\s-]+");
  return new RegExp(`(^|[^a-z0-9])${pattern}([^a-z0-9]|$)`, "i").test(haystack);
}

function detectCategory(metadata) {
  const haystack = [metadata.title, metadata.journal, metadata.author, metadata.pageText]
    .join(" ")
    .toLowerCase();

  for (const [category, config] of Object.entries(CATEGORIES)) {
    if (category === "General") {
      continue;
    }
    if (config.keywords.some((keyword) => keywordMatches(keyword, haystack))) {
      return category;
    }
  }
  return "General";
}

function buildFilename() {
  const category = fields.category.value || "General";
  const categoryPrefix = CATEGORIES[category]?.prefix ?? "";
  const prefix = fields.useCategoryPrefix.checked ? categoryPrefix : fields.prefix.value.trim();
  const number = Math.max(1, Number.parseInt(fields.nextNumber.value || "1", 10));
  const digits = Math.max(1, Number.parseInt(fields.digits.value || "3", 10));
  const identifier = `${prefix}${String(number).padStart(digits, "0")}`;
  const title = titleCaseSmart(shortenTitle(fields.title.value));
  const author = sanitize(fields.author.value) || "Unknown";
  const journal = abbreviateJournal(fields.journal.value);
  const year = String(fields.year.value || "0000");
  const yearShort = year.length >= 2 ? year.slice(-2) : "00";
  return sanitize(`${identifier} ${author}, ${title}, ${journal} ${yearShort}.pdf`);
}

function fullDownloadPath(filename) {
  const subfolder = sanitize(fields.downloadSubfolder.value).replace(/^\/+|\/+$/g, "");
  if (!subfolder) {
    return filename;
  }
  return `${subfolder}/${filename}`;
}

function refreshFilename() {
  fields.filename.value = buildFilename();
}

async function activeTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

function collectPageMetadata() {
  function meta(...selectors) {
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      const value = element?.content || element?.href || "";
      if (value.trim()) {
        return value.trim();
      }
    }
    return "";
  }

  const pdfLink =
    meta(
      'meta[name="citation_pdf_url"]',
      'meta[name="bepress_citation_pdf_url"]',
      'link[type="application/pdf"]'
    ) ||
    Array.from(document.querySelectorAll("a[href]"))
      .map((link) => link.href)
      .find((href) => /\.pdf($|[?#])/i.test(href)) ||
    "";

  const authors = Array.from(document.querySelectorAll('meta[name="citation_author"]'))
    .map((element) => element.content)
    .filter(Boolean);

  let resolvedPdfUrl = pdfLink;
  try {
    resolvedPdfUrl = pdfLink ? new URL(pdfLink, window.location.href).href : "";
  } catch (_error) {
    resolvedPdfUrl = pdfLink;
  }

  return {
    title:
      meta('meta[name="citation_title"]', 'meta[property="og:title"]', 'meta[name="dc.title"]') ||
      document.title,
    journal: meta('meta[name="citation_journal_title"]', 'meta[name="prism.publicationName"]'),
    year:
      meta('meta[name="citation_publication_date"]', 'meta[name="citation_online_date"]', 'meta[name="dc.date"]')
        .match(/\d{4}/)?.[0] || "",
    author: authors.length ? authors[authors.length - 1] : "",
    pdfUrl: resolvedPdfUrl,
    pageText: document.body?.innerText?.slice(0, 12000) || ""
  };
}

async function loadMetadata() {
  const tab = await activeTab();
  let metadata = {
    title: tab?.title || "",
    journal: "",
    year: "",
    author: "",
    pdfUrl: tab?.url || "",
    pageText: ""
  };

  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: collectPageMetadata
    });
    metadata = { ...metadata, ...(result?.result || {}) };
  } catch (_error) {
    // Chrome blocks script injection on some internal/PDF pages. Use tab data then.
  }

  if (!metadata.pdfUrl || /\.pdf($|[?#])/i.test(tab.url)) {
    metadata.pdfUrl = tab.url;
  }

  fields.pdfUrl.value = metadata.pdfUrl || "";
  fields.title.value = metadata.title || "";
  fields.journal.value = metadata.journal || "";
  fields.year.value = metadata.year || "";
  fields.author.value = metadata.author || "Unknown";
  fields.category.value = detectCategory(metadata);
  refreshFilename();
}

function populateCategories() {
  fields.category.innerHTML = "";
  for (const category of Object.keys(CATEGORIES)) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    fields.category.appendChild(option);
  }
}

async function loadSettings() {
  const settings = await chrome.storage.local.get(DEFAULT_SETTINGS);
  fields.downloadSubfolder.value = settings.downloadSubfolder;
  fields.prefix.value = settings.prefix;
  fields.nextNumber.value = settings.nextNumber;
  fields.digits.value = settings.digits;
  fields.useCategoryPrefix.checked = settings.useCategoryPrefix;
  fields.saveAs.checked = settings.saveAs;
}

async function saveSettings() {
  await chrome.storage.local.set({
    downloadSubfolder: fields.downloadSubfolder.value,
    prefix: fields.prefix.value,
    nextNumber: Math.max(1, Number.parseInt(fields.nextNumber.value || "1", 10)),
    digits: Math.max(1, Number.parseInt(fields.digits.value || "3", 10)),
    useCategoryPrefix: fields.useCategoryPrefix.checked,
    saveAs: fields.saveAs.checked
  });
}

async function downloadCurrentPdf() {
  const url = fields.pdfUrl.value.trim();
  if (!url) {
    fields.status.textContent = "No PDF URL found. Paste one manually.";
    return;
  }

  const filename = sanitize(fields.filename.value) || buildFilename();
  const downloadPath = fullDownloadPath(filename);
  fields.downloadButton.disabled = true;
  fields.status.textContent = "Starting download...";

  await saveSettings();
  chrome.downloads.download(
    {
      url,
      filename: downloadPath,
      saveAs: fields.saveAs.checked,
      conflictAction: "uniquify"
    },
    async (downloadId) => {
      fields.downloadButton.disabled = false;
      if (chrome.runtime.lastError) {
        fields.status.textContent = chrome.runtime.lastError.message;
        return;
      }
      const nextNumber = Math.max(1, Number.parseInt(fields.nextNumber.value || "1", 10)) + 1;
      fields.nextNumber.value = nextNumber;
      await chrome.storage.local.set({ nextNumber });
      refreshFilename();
      fields.status.textContent = `Download started: ${downloadId}`;
    }
  );
}

async function init() {
  populateCategories();
  await loadSettings();
  await loadMetadata();

  for (const element of [
    fields.title,
    fields.author,
    fields.journal,
    fields.year,
    fields.prefix,
    fields.nextNumber,
    fields.digits,
    fields.category,
    fields.useCategoryPrefix,
    fields.downloadSubfolder
  ]) {
    element.addEventListener("input", refreshFilename);
    element.addEventListener("change", refreshFilename);
  }

  fields.saveAs.addEventListener("change", saveSettings);
  fields.downloadButton.addEventListener("click", downloadCurrentPdf);
}

init();
