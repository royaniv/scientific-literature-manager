chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get({
    subfolder: "organized_papers",
    prefix: "CB",
    nextNumber: 1,
    digits: 3,
    saveAs: false
  }, s => chrome.storage.local.set(s));
});
