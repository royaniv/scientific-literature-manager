// Initialise storage defaults on first install.
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get({
    subfolder: "organized_papers",
    prefix: "CB",
    nextNumber: 1,
    digits: 3,
    perCategory: false,
    saveAs: false
  }, (existing) => chrome.storage.local.set(existing));
});
