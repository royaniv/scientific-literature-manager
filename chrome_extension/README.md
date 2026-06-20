# Chrome Extension Prototype

This is a separate browser-extension prototype for downloading an article PDF with a literature-manager filename.

## What It Can Do

- Detect basic article metadata from the current page.
- Find a likely PDF URL from common citation metadata or PDF links.
- Build a filename like:

```text
CB001 LastAuthor, Short Paper Title, Biol Chem 24.pdf
```

- Save into a subfolder inside Chrome's Downloads folder, such as:

```text
Downloads/organized_papers/
```

- Optionally show Chrome's `Save As` dialog.

## Browser Limitation

Chrome extensions cannot silently save files to any arbitrary folder on the user's computer.

They can:

- suggest a filename,
- save under the browser's Downloads folder,
- create subfolders inside Downloads,
- or show a Save As dialog.

To silently save into a completely arbitrary folder, the extension would need a separate native helper application installed on the user's computer.

## Install For Local Testing

1. Open Chrome.
2. Go to:

```text
chrome://extensions
```

3. Turn on `Developer mode`.
4. Click `Load unpacked`.
5. Select this folder:

```text
chrome_extension
```

6. Pin the extension.
7. Open an article or PDF page and click the extension button.

## Monetization Notes

Possible monetization paths:

- Chrome Web Store paid extension or one-time license.
- Freemium extension: limited downloads/month free, paid unlimited plan.
- Researcher subscription: saved naming templates, DOI lookup, Zotero/BibTeX export, duplicate detection.
- Institutional license for labs or departments.
- Companion desktop app upsell for direct arbitrary-folder saving.

The strongest paid version would likely combine the Chrome extension with a small local companion app, because that unlocks direct folder saving and better PDF metadata extraction.
