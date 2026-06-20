# Scientific Literature Manager

Scientific Literature Manager is a Python project for organizing downloaded scientific PDF papers. It was built as a final project for the Weizmann Institute Basic Programming Skills (Python) course, based on a real workflow problem: Google Scholar alerts and journal websites often produce files with unclear names such as `download.pdf`, `fulltext.pdf`, or `paper.pdf`, etc.

The main goal is to scan PDF files, extract whatever useful metadata is available, suggest readable filenames, classify papers into research categories, and copy or move them into organized folders.

## Project Scope

The core course project is the desktop and command-line literature organizer:

- choose PDF files or a folder of PDFs
- preview planned filenames before changing files
- rename papers using a consistent naming format
- classify papers by editable keyword categories
- copy or move papers into an output folder
- keep the file-handling and classification logic separate from the user interface

The local web app and Chrome extension are optional additions. They explore how the same idea could be used from a browser, but they are not the main required part of the course project.

## Why This Is Useful

I receive many scientific papers from Google Scholar alerts related to origin-of-life research, astrobiology, and citation alerts from the research group. When the number of papers grows, manually renaming and sorting them becomes repetitive and inconsistent.

This project helps automate that workflow while keeping the rules configurable enough for other researchers to adapt the program to 
their own topics.

## What The Program Does

For each PDF, the program can:

1. Read PDF metadata and text.
2. Find identifiers such as DOI numbers when possible.
3. Retrieve publication information when possible.
4. Create a readable filename.
5. Classify the paper into a category using keywords.
6. Copy or move the paper into an organized output folder.
7. Show a preview before applying the changes.

The program can be used through a desktop GUI, a command-line interface, or the optional local web app.

The classification system is rule-based: it checks paper text and metadata for keywords that belong to each category. For example, papers containing words such as `micelle`, `vesicle`, or `GARD` may be classified into the `Micelles` category.

The current version does not use machine learning.

## Main Interfaces

### Desktop App

The desktop app is the main interface for the project.

Start it by double-clicking:

```text
START_HERE_RUN_APP.bat
```

Or run it from the terminal:

```powershell
.\.venv\Scripts\python.exe .\sci_lit_man.py
```

The desktop app lets the user add PDF files, add a folder, choose an output folder, preview changes, edit suggested filenames, and then apply the changes.

### Command Line

The command-line interface is useful for testing and repeatable runs.

Preview changes without moving files:

```powershell
.\.venv\Scripts\python.exe -m literature_manager.rename_papers --cli "C:\path\to\pdfs" --dry-run
```

Process a folder:

```powershell
.\.venv\Scripts\python.exe -m literature_manager.rename_papers --cli "C:\path\to\pdfs"
```

Copy files instead of moving them:

```powershell
.\.venv\Scripts\python.exe -m literature_manager.rename_papers --cli "C:\path\to\pdfs" --copy
```

Scan subfolders too:

```powershell
.\.venv\Scripts\python.exe -m literature_manager.rename_papers --cli "C:\path\to\pdfs" --recursive
```

### Local Web App

The local web app uses the same general idea as the desktop app, but runs in a browser through Flask.

Start it by double-clicking:

```text
START_HERE_WEB_APP.bat
```

Then open:

```text
http://127.0.0.1:5000
```

The web app has two modes:

- upload PDFs and download an organized ZIP file
- process a local folder on the same computer running the Flask app

Browsers cannot freely rename arbitrary files on a user's computer. The local-folder mode works only because the Flask server is running on the same computer as the files.

### Chrome Extension Prototype

The `chrome_extension/` folder contains an experimental prototype. It explores the idea of detecting article metadata from the current browser page and suggesting a literature-manager filename.

This is not the main course project. It is included as an extra experimental app.

To test it:

1. Open Chrome.
2. Go to `chrome://extensions`.
3. Turn on `Developer mode`.
4. Click `Load unpacked`.
5. Select the `chrome_extension` folder.
6. Open an article or PDF page and click the extension button.

Chrome can save automatically only inside the Downloads folder or a subfolder of Downloads. Saving directly into any arbitrary folder would require a native companion app.

## Naming System

The default filename format is:

```text
XX### LastAuthor, Paper Title, Journal Abbreviation YY.pdf
```

Example input filenames:

```text
download.pdf
paper1.pdf
fulltext.pdf
```

Example output filenames:

```text
CB001 Lancet, The Lipid World, JRSI 18.pdf
CB002 Yaniv, Biomarkers on the Icy Jovian Moons, Life 26.pdf
CB003 Segre, Graded Autocatalysis Replication Domain, PNAS 00.pdf
```

The naming options can be changed in the app:

- `Prefix` controls the letters before the number, such as `CB` or `OL`.
- `Start` controls the first number.
- `Digits` controls number padding, so 3 gives `001` and 4 gives `0001`.
- `Mode` controls whether all papers share one sequence or each category gets its own sequence.

## Classification System

The program classifies papers using editable keyword categories.

Default categories include:

- Micelles
- Chiral
- Soup
- Astro
- Light
- OrganBactr
- General

Example keywords:

```text
Micelles: micelle, amphiphile, vesicle, composome, GARD
Astro: astrobiology, Europa, Enceladus, biosignature, ocean world
```

Categories are checked in order. If a paper matches more than one category, the first matching category is used.

## Output

The program creates an organized output folder, usually:

```text
organized_papers/
```

Depending on the selected task, the program can:

- rename PDFs into one output folder
- sort PDFs into category folders while keeping the original names
- sort PDFs into category folders and rename them

By default, the GUI copies files so the original PDFs are not changed. The user can turn this off if they want to move the original files instead.

## Code Layout

- `sci_lit_man.py`: main desktop launcher
- `literature_manager/rename_papers.py`: command-line interface
- `literature_manager/gui.py`: desktop app behavior
- `literature_manager/gui_layout.py`: desktop window layout
- `literature_manager/gui_dialogs.py`: desktop edit dialogs
- `literature_manager/web_app.py`: optional Flask web app
- `literature_manager/templates/`: web app HTML pages
- `literature_manager/static/`: web app CSS
- `literature_manager/core/`: shared processing logic
- `literature_manager/settings.py`: default categories and settings
- `chrome_extension/`: optional browser-extension prototype

## Installation

Create a virtual environment from the project folder:

```powershell
& "C:\Users\royy\AppData\Local\Programs\Python\Python314\python.exe" -m venv .venv
```

Install the dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The required packages are listed in `requirements.txt`:

- `pypdf`
- `requests`
- `tkinterdnd2`
- `Flask`
- `pytest`

`pypdf` reads PDF text and metadata. `requests` is used for online metadata lookup. `tkinterdnd2` adds drag-and-drop support to the desktop GUI. `Flask` is used only for the optional local web app. `pytest` is used for the automated tests.

## Running Tests

Run:

```powershell
pytest
```

or:

```powershell
python -m pytest
```

## Custom Configuration

The program can load a JSON configuration file for custom categories, keywords, priority rules, or filename settings.

Example:

```json
{
  "identifier_prefix": "OL",
  "start_number": 1,
  "identifier_digits": 3,
  "numbering_mode": "category",
  "category_identifiers": {
    "OriginOfLife": {"prefix": "OL"},
    "Astrobiology": {"prefix": "AS", "start_number": 50}
  },
  "title_words": 10,
  "categories": {
    "OriginOfLife": ["origin of life", "prebiotic", "autocatalysis"],
    "Astrobiology": ["astrobiology", "biosignature", "europa"],
    "General": []
  },
  "priority_rules": {
    "authors": ["Lancet"],
    "journals": ["Nature", "Science"],
    "keywords": ["GARD", "composome"]
  }
}
```

Run with a custom config:

```powershell
.\.venv\Scripts\python.exe -m literature_manager.rename_papers --cli "C:\path\to\pdfs" --config my_config.json --dry-run
```

## Use Of AI

AI tools were used as programming assistance during development. The final project was reviewed, adjusted, and tested in this repository.

## Future Features

Possible future extensions include:

- duplicate paper detection
- DOI validation
- BibTeX export
- Zotero integration
- EndNote support
- paper summaries
- smarter keyword suggestions
- user accounts
- cloud synchronization
- public web deployment
- standalone Windows `.exe` packaging

## Course Information

This project is being developed as part of the Weizmann Institute Basic Programming Skills (Python) course 2026.

Course repository:

```text
https://github.com/Code-Maven/wis-python-course-2026-03
```
