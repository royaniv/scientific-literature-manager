# Scientific Literature Manager

The original README.md text can be found at the end of the current README.md in case a comparison is needed. there were many changes and additions in this final README.md

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

### Optional Command-Line Mode

The program can also run from the terminal. This is useful for testing the file-renaming logic without opening the desktop app.

For example, this previews the planned changes without moving or renaming files:

```powershell
.\.venv\Scripts\python.exe -m literature_manager.rename_papers --cli "C:\path\to\pdfs" --dry-run
```

Remove `--dry-run` to apply the changes. Add `--copy` to copy files instead of moving them, or `--recursive` to include PDFs inside subfolders.

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

# Original README 

Scientific Literature Manager
Project Overview
I receive a large number of scientific papers through Google Scholar alerts. These alerts are based on keywords related to my research interests, including origin-of-life research, astrobiology, and such. I also receive citation alerts related to publications by Prof. Doron Lancet.

When new papers appear, I download the PDF files and save them locally and rename them when deemed important and place them in dedicated folders after reading them. These files are often saved initially with uninformative names such as:

download.pdf

fulltext.pdf

paper.pdf

As the number of papers grows, it becomes increasingly difficult to organize them consistently, locate specific articles, and determine which papers are most relevant.

The goal of this project is to create a configurable literature-management system that automatically renames, classifies, organizes, and prioritizes scientific papers.

The project is intended to automate part of my literature-management workflow while remaining flexible enough for researchers working in completely different fields.

I would like to attempt to create a GUI and possibly web application that will allow myself and other users who receive such alerts to create a way to rename, save, and categorize relevant papers to our research.

What Does This Project Do?
The application scans a folder containing scientific PDF files.

For each PDF it will:

Extract metadata from the PDF file.
Search for identifiers such as DOI numbers.
Retrieve publication information when possible.
Rename the PDF using a configurable naming convention.
Classify the paper into a category.
Move the paper into the appropriate folder.
Save a record of all changes performed.
Generate a summary of newly processed papers.
The application will allow users to customize:

Folder names.
Categories.
Classification keywords.
Naming conventions.
Prioritization rules.
Naming System
The default naming convention will be according to my needs but should be changeable:

XX### LastAuthor, Paper Title, Journal Abbreviation YY.pdf

where:

XX### is a unique identifier assigned by the program.
LastAuthor is the surname of the senior (last) author.
Paper Title is the article title.
Journal Abbreviation is the journal abbreviation.
YY is the last two digits of the publication year.
Example:

Before:

download.pdf

paper1.pdf

fulltext.pdf

After:

CB001 Lancet, The Lipid World, JRSI 18.pdf

CB002 Yaniv, Biomarkers on the Icy Jovian Moons, Life 26.pdf

CB003 Segre, Graded Autocatalysis Replication Domain, PNAS 00.pdf

The naming convention will be user-configurable so that different researchers can use formats that fit their own workflow.

Input
The program expects a folder containing PDF files.

The PDFs may originate from:

Google Scholar keyword alerts.
Google Scholar citation alerts.
Journal websites.
Email attachments containing scientific papers.
Existing personal collections of scientific literature.
Future versions may also support importing information directly from saved email files.

Output
The application will generate:

Renamed PDF files.
Organized folder structures.
Processing logs.
Optional CSV files containing extracted metadata.
Paper summaries and prioritization reports.
Example folder structure:

Micelles/

Chiral/

Soup/

Astro/

General/

The folder structure will be configurable by the user.

Classification System
The application will classify papers based on user-defined categories and keywords.

Default categories may include:

Micelles
Chiral
Soup
Astro
General
Each category will contain user-editable keywords.

Example:

Micelles

micelle
amphiphile
vesicle
composome
GARD
Astro

astrobiology
Europa
Enceladus
biosignature
ocean world
Users will be able to create, edit, and remove categories through the application settings.

This allows the software to be used by researchers from completely different scientific disciplines.

Prioritization
The application will optionally prioritize papers based on configurable rules.

Examples:

Specific authors.
Specific journals.
Citation alerts.
Keywords.
User-defined topics.
This feature is intended to help users identify which papers may deserve immediate attention.

Why Is This Useful?
Google Scholar alerts can generate a large number of papers over time.

Manually:

Renaming files.
Creating folders.
Organizing papers.
Identifying relevant papers.
is repetitive and time-consuming.

This project automates those tasks and provides a consistent organizational system while remaining customizable for different users and research areas.

Planned Technologies
Python
PDF metadata extraction
File management and renaming
Automated testing
Standalone desktop GUI
Local web application
Future public web deployment
Planned User Interfaces
Desktop GUI
The primary interface will be a standalone desktop application.

Users will be able to:

Select folders.
Process papers.
Review metadata.
Preview filenames.
Edit categories.
Edit keyword lists.
Configure naming conventions.
Approve or reject changes.
Local Web Application
A local web application will also be developed if time permits.

The web interface will run on the user's own computer and will provide the same functionality through a browser.

Future Online Deployment
The architecture will be designed so that the application can eventually be deployed online, allowing multiple users to maintain their own categories, keywords, naming conventions, and paper collections.

Expected Dependencies
pypdf
requests
pytest
PySide6
Flask (or another Python web framework if web app is developed)
Additional dependencies may be added as the project evolves.

Installation
Open a terminal and run:

pip install -r requirements.txt

Running the Project
Desktop application:

python literature_manager_gui.py

Local web application:

python app.py

and then open the local address displayed by the application in a browser.

Running Tests
pytest

Future Features
Possible future extensions include:

Duplicate paper detection.
DOI validation.
BibTeX export.
Zotero integration.
Endnote placement.
AI-assisted paper summaries.
AI-assisted keyword suggestions.
User accounts.
Cloud synchronization.
Public web deployment.
Shared literature collections.
Course Information
This project is being developed as part of the Weizmann Institute Basic programming skills (Python) course 2026.

Course repository:

https://github.com/Code-Maven/wis-python-course-2026-03
