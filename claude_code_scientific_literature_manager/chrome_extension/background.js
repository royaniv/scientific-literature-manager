chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(
    {
      downloadSubfolder: "organized_papers",
      prefix: "CB",
      nextNumber: 1,
      digits: 3,
      useCategoryPrefix: false,
      saveAs: false
    },
    (settings) => chrome.storage.local.set(settings)
  );
});
