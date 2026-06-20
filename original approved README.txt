README
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