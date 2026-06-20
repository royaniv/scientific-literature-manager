# =========================================================
# FIXED VERSION (NO FREEZE, SAME CORRECT OUTPUT)
# =========================================================

import os
import re
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import fitz

LOWER_WORDS = {"of","and","or","in","on","at","to","for","with","by","from","the","a","an"}


# -------- HELPERS --------
def sanitize_filename(text):
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def title_case_smart(title):
    words = title.lower().split()
    return ' '.join([w.capitalize() if i == 0 or w not in LOWER_WORDS else w for i, w in enumerate(words)])

def shorten_title(title):
    return ' '.join(title.split()[:8])

def abbreviate_journal(journal):
    return ' '.join([re.sub(r'[^A-Za-z]', '', w)[:4] for w in journal.split() if w]) or "Unknown"


# -------- EXTRACTION --------
def extract_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for i in range(min(3, len(doc))):
            text += doc[i].get_text()
        doc.close()
        return text
    except:
        return ""


def find_doi(text):
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.I)
    return match.group(0) if match else None


def query_crossref(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()["message"]

        title = data.get("title", ["UnknownTitle"])[0]
        journal = data.get("container-title", ["UnknownJournal"])[0]
        year = str(data.get("issued", {}).get("date-parts", [[0]])[0][0])

        authors = data.get("author", [])
        last_author = authors[-1]["family"] if authors else "Unknown"

        return title, journal, year, last_author
    except:
        return None


def fallback_parse(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    candidates = lines[:10]
    title = max(candidates, key=len) if candidates else "UnknownTitle"

    author = "Unknown"
    for line in lines[:10]:
        if ',' in line:
            author = line.split(',')[-1].strip()
            break

    year_match = re.search(r"(19|20)\d{2}", text)
    year = year_match.group(0) if year_match else "0000"

    journal = "UnknownJournal"

    return title, journal, year, author


# -------- BUILD --------
def build_filename(title, journal, year, author, prefix, number):
    title = sanitize_filename(title)
    title = shorten_title(title)
    title = title_case_smart(title)

    journal = abbreviate_journal(journal)
    author = sanitize_filename(author)
    year = year[-2:] if len(year) >= 2 else "00"

    base = f"{author}, {title}, {journal} {year}"

    if prefix or number:
        base = f"{prefix or ''}{number or ''} {base}".strip()

    return base + ".pdf"


# -------- GUI --------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Renamer")
        self.root.geometry("1100x650")

        style = ttk.Style()
        style.theme_use('clam')

        self.files = []
        self.rows = []
        self.cache = {}   # 🔥 important

        ttk.Label(root, text="Drag PDFs or folders here", font=("Segoe UI", 14)).pack(pady=10)

        container = ttk.Frame(root)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.frame = ttk.Frame(canvas)

        self.frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Button(root, text="Apply Rename", command=self.apply).pack(pady=10)

        root.drop_target_register(DND_FILES)
        root.dnd_bind("<<Drop>>", self.drop)


    def drop(self, event):
        paths = self.root.tk.splitlist(event.data)

        self.files = []
        self.cache = {}

        for p in paths:
            if os.path.isdir(p):
                for root_dir, _, files in os.walk(p):
                    for f in files:
                        if f.lower().endswith(".pdf"):
                            full = os.path.join(root_dir, f)
                            self.files.append(full)
            elif p.lower().endswith(".pdf"):
                self.files.append(p)

        # 🔥 PARSE ONCE (no freeze later)
        for f in self.files:
            text = extract_text(f)
            doi = find_doi(text)

            if doi:
                meta = query_crossref(doi)
            else:
                meta = None

            if not meta:
                meta = fallback_parse(text)

            self.cache[f] = meta

        self.render()


    def render(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        self.rows = []

        for f in self.files:
            row = ttk.Frame(self.frame)
            row.pack(fill="x", pady=4, padx=5)

            prefix_entry = ttk.Entry(row, width=8)
            prefix_entry.pack(side="left", padx=5)

            number_entry = ttk.Entry(row, width=8)
            number_entry.pack(side="left", padx=5)

            ttk.Label(row, text=os.path.basename(f), width=35).pack(side="left", padx=10)

            preview = ttk.Label(row, text="", width=70)
            preview.pack(side="left", padx=10)

            self.rows.append((f, prefix_entry, number_entry, preview))

            prefix_entry.bind("<KeyRelease>", lambda e, r=row: self.update_row(r))
            number_entry.bind("<KeyRelease>", lambda e, r=row: self.update_row(r))


    def update_row(self, row):
        for f, p, n, preview in self.rows:
            if p.master == row:

                prefix = p.get().strip()
                number = n.get().strip()

                title, journal, year, author = self.cache[f]  # 🔥 fast

                preview.config(text=build_filename(title, journal, year, author, prefix, number))


    def apply(self):
        for f, p, n, _ in self.rows:

            prefix = p.get().strip()
            number = n.get().strip()

            title, journal, year, author = self.cache[f]

            new_name = build_filename(title, journal, year, author, prefix, number)
            new_path = os.path.join(os.path.dirname(f), new_name)

            try:
                if f != new_path:
                    os.replace(f, new_path)
            except Exception as e:
                print("Rename failed:", e)

        messagebox.showinfo("Done", "Renaming complete")


# -------- RUN --------
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = App(root)
    root.mainloop()