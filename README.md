# Scientific Literature Manager

**Main program file:** `MAIN_sci_lit_man.py`

The easiest way to run the project is to double-click:

```text
START_HERE_RUN_APP.bat
```

Scientific Literature Manager is a Python project for organizing downloaded scientific PDF papers. It was built as a final project for the Weizmann Institute Basic Programming Skills (Python) course.

The program helps with papers that are downloaded with unclear names such as `download.pdf`, `fulltext.pdf`, or `paper.pdf`. It can scan PDF files, read available metadata, suggest clearer filenames, classify papers by keywords, and copy or move them into an organized output folder.

## What The Project Does

For each PDF, the program can:

1. Read PDF metadata and text.
2. Find identifiers such as DOI numbers when possible.
3. Retrieve publication information when possible.
4. Create a readable filename.
5. Classify the paper into a category using keywords.
6. Copy or move the paper into an organized folder.
7. Show a preview before applying changes.

The classification system is rule-based. It does not use machine learning.

## Main Parts Of The Project

### Main Desktop App

These are the files for the main program:

- `MAIN_sci_lit_man.py`: the main Python file that starts the desktop app
- `START_HERE_RUN_APP.bat`: the file to double-click on Windows
- `literature_manager/gui.py`: desktop app behavior
- `literature_manager/gui_layout.py`: desktop window layout
- `literature_manager/gui_dialogs.py`: edit dialogs used by the desktop app

The desktop app is the main course project.

### Core Logic

The `literature_manager/core/` folder contains the shared logic that does the actual work. It is separate from the GUI so it can be tested more easily.

- `classifier.py`: classifies papers into categories by keywords
- `files.py`: finds PDFs, plans output paths, copies or moves files
- `metadata.py`: extracts text, finds DOI values, and looks up metadata
- `models.py`: defines the paper metadata object
- `naming.py`: creates paper identifiers and filenames
- `text.py`: cleans text and filenames

### Settings And Helpers

- `literature_manager/settings.py`: default categories, keywords, and filename settings
- `literature_manager/ui_config.py`: small helper functions shared by the desktop and web interfaces
- `literature_manager/rename_papers.py`: simple terminal version that asks the user questions with `input()`

### Optional Web App

The optional Flask web app is now separate from the main `literature_manager` package:

- `web_app/app.py`: starts the Flask web app
- `web_app/templates/`: HTML pages
- `web_app/static/`: CSS file
- `START_HERE_WEB_APP.bat`: starts the web app on Windows

To run it, double-click:

```text
START_HERE_WEB_APP.bat
```

Then open:

```text
http://127.0.0.1:5000
```

### Optional Chrome Extension

The `chrome_extension/` folder contains an experimental browser-extension prototype. It is not the main course project.

### Tests

The `tests/` folder contains automated tests for the shared Python logic:

- classification
- filename creation
- PDF file collection
- planned file operations
- settings loading
- shared interface helpers

These tests mainly check the core logic used by the desktop app and web app. They do not directly test the visual GUI window or the Chrome extension.

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

## Categories

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

## Installation

Create a virtual environment from the project folder:

```powershell
& "C:\Users\royy\AppData\Local\Programs\Python\Python314\python.exe" -m venv .venv
```

Install the dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The required packages are:

- `pypdf`
- `requests`
- `tkinterdnd2`
- `Flask`
- `pytest`

## Running The Desktop App

Double-click:

```text
START_HERE_RUN_APP.bat
```

Or run:

```powershell
.\.venv\Scripts\python.exe .\MAIN_sci_lit_man.py
```

## Simple Terminal Version

The terminal version is optional. It uses simple `input()` questions instead of a graphical window.

Run:

```powershell
.\.venv\Scripts\python.exe -m literature_manager.rename_papers
```

The script asks for the input folder, output folder, and whether to preview, copy, or include subfolders.

## Running Tests

Run:

```powershell
python -m pytest
```

Current tests check the shared core logic, not the Chrome extension.

## Course Information

This project is being developed as part of the Weizmann Institute Basic Programming Skills (Python) course 2026.

Course repository:

```text
https://github.com/Code-Maven/wis-python-course-2026-03
```
