"""
gui.py  —  Paper Organizer desktop GUI.

Layout:

  ┌───────────────────────────────────────────────────────────────┐
  │ [dark header]                                                 │
  │  Source  [_________________________________] [Browse]         │
  │  Output  [_________________________________] [Browse]         │
  │  ☐ Subfolders  ☐ Keep originals  ☐ Recursive   [⚙ Settings] │
  ├───────────────────────────────────────────────────────────────┤
  │  [ALL 24]  [● Micelles 5]  [● Chiral 3]  [● Astro 1]  ...   │
  ├───────────────────────────────────────────────────────────────┤
  │                                                               │
  │   Source file          →    New name           Cat    ★  St  │
  │   download.pdf              CB001 Lancet...    Mic    ★  Prv │
  │   paper.pdf                 CB002 Segre...     Soup      Prv │
  │                                                               │
  ├───────────────────────────────────────────────────────────────┤
  │  [Clear]  [Edit]     ████████░░  8/24   [Preview]  [Apply]   │
  └───────────────────────────────────────────────────────────────┘

Key design decisions:
  - No left panel of any kind.  The table spans the full window width.
  - Category filter is a HORIZONTAL row of colored pills above the table.
    Each pill shows the count and turns solid when active.
  - Every category has its own persistent colour so papers are
    colour-coded at a glance without reading the text.
  - Settings (prefix, digits, template) live in a separate popup
    opened with the gear button — the main window stays uncluttered.
  - Action buttons are at the bottom in a footer bar.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from paper_organizer.core import (
    DEFAULT_CATEGORIES, PDF_OK, NET_OK,
    Paper, State,
    apply_plan, collect_pdfs, plan_papers,
)

# ── Category colour palette ───────────────────────────────────────────────────
# Each category has a unique colour used for the pill and the table row.

CAT_COLORS: dict[str, str] = {
    "All":        "#475569",
    "Micelles":   "#2563eb",
    "Chiral":     "#7c3aed",
    "Soup":       "#ea580c",
    "Astro":      "#0369a1",
    "Light":      "#b45309",
    "OrganBactr": "#15803d",
    "General":    "#64748b",
}
HIGH_COLOR  = "#dc2626"
DONE_COLOR  = "#15803d"
FAIL_COLOR  = "#94a3b8"

C_DARK   = "#1b2d4f"   # header background
C_PILLS  = "#f1f5f9"   # pill bar background
C_BG     = "#ffffff"   # table background

_COLS    = ("source", "arrow", "new_name", "category", "priority", "status")
_HEADS   = ("Source file", "", "New name", "Category", "★", "Status")
_WIDTHS  = (195, 22, 285, 88, 24, 90)
_STRETCH = (True, False, True, False, False, False)


# ═════════════════════════════════════════════════════════════════════════════
class PaperOrganizerApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("Paper Organizer")
        self.geometry("980x660")
        self.minsize(780, 500)
        self.configure(bg=C_DARK)

        self._papers:      list[Paper]      = []
        self._item_paper:  dict[str, Paper] = {}
        self._filter:      str              = "All"
        self._categories:  dict[str, list[str]] = dict(DEFAULT_CATEGORIES)

        self._src_var   = tk.StringVar()
        self._out_var   = tk.StringVar()
        self._sub_var   = tk.BooleanVar(value=False)
        self._copy_var  = tk.BooleanVar(value=True)
        self._rec_var   = tk.BooleanVar(value=True)
        self._status    = tk.StringVar(value="Choose a source folder, then click Preview.")
        self._progress  = tk.DoubleVar(value=0.0)

        self._pill_btns: dict[str, tk.Button] = {}

        # naming config (changed only via Settings dialog)
        self._prefix  = "CB"
        self._digits  = 3
        self._start   = 1
        self._template = "{id} {author}, {title}, {journal} {year_short}.pdf"

        self._build()
        self._check_packages()

    # ── Build layout ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)   # table row expands

        self._build_header(row=0)
        self._build_pills(row=1)
        self._build_table(row=2)
        self._build_footer(row=3)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self, row: int) -> None:
        hdr = tk.Frame(self, bg=C_DARK, padx=18, pady=12)
        hdr.grid(row=row, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)
        hdr.columnconfigure(4, weight=1)

        lbl  = dict(bg=C_DARK, fg="#8faac8", font=("Segoe UI", 9))
        ent  = dict(relief="flat", bg="#243d64", fg="white",
                    insertbackground="white", font=("Segoe UI", 10))
        brws = dict(relief="flat", bg="#2a4a7a", fg="white",
                    activebackground="#3a5e96", cursor="hand2",
                    font=("Segoe UI", 9), padx=10)

        tk.Label(hdr, text="Source", **lbl).grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Entry(hdr, textvariable=self._src_var, **ent).grid(row=0, column=1, columnspan=2, sticky="ew", ipady=5)
        tk.Button(hdr, text="Browse…", command=self._pick_source, **brws).grid(row=0, column=3, padx=(6, 20), ipady=3)

        tk.Label(hdr, text="Output", **lbl).grid(row=0, column=4, sticky="w", padx=(0, 8))
        tk.Entry(hdr, textvariable=self._out_var, **ent).grid(row=0, column=5, sticky="ew", ipady=5)
        tk.Button(hdr, text="Browse…", command=self._pick_output, **brws).grid(row=0, column=6, padx=(6, 0), ipady=3)

        opts = tk.Frame(hdr, bg=C_DARK)
        opts.grid(row=1, column=0, columnspan=7, sticky="w", pady=(10, 0))

        def _chk(txt, var):
            tk.Checkbutton(opts, text=txt, variable=var,
                           bg=C_DARK, fg="#a8c4e0", selectcolor=C_DARK,
                           activebackground=C_DARK, activeforeground="white",
                           font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=(0, 18))

        _chk("Sort into category folders", self._sub_var)
        _chk("Keep originals (copy)",      self._copy_var)
        _chk("Include subfolders",         self._rec_var)

        tk.Button(opts, text="⚙  Settings", command=self._open_settings,
                  relief="flat", bg="#243d64", fg="#7dd3fc",
                  activebackground="#2a4a7a", cursor="hand2",
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side="right")

    # ── Category pill bar ─────────────────────────────────────────────────────

    def _build_pills(self, row: int) -> None:
        bar = tk.Frame(self, bg=C_PILLS, padx=14, pady=8)
        bar.grid(row=row, column=0, sticky="ew")
        self._pill_bar = bar
        self._redraw_pills()

    def _redraw_pills(self) -> None:
        for w in self._pill_bar.winfo_children():
            w.destroy()
        self._pill_btns.clear()

        counts = {"All": len(self._papers)}
        for cat in DEFAULT_CATEGORIES:
            counts[cat] = sum(1 for p in self._papers if p.category == cat)

        names = ["All"] + list(DEFAULT_CATEGORIES.keys())
        for name in names:
            n   = counts.get(name, 0)
            col = CAT_COLORS.get(name, "#64748b")
            active = (name == self._filter)

            if active:
                bg, fg, relief = col, "white", "flat"
            else:
                bg, fg, relief = C_PILLS, col, "flat"

            label = f"  {name}  {n}  " if n else f"  {name}  "
            btn = tk.Button(
                self._pill_bar, text=label,
                bg=bg, fg=fg, relief=relief,
                font=("Segoe UI", 9, "bold"),
                activebackground=col, activeforeground="white",
                cursor="hand2", bd=1,
                highlightthickness=1,
                highlightbackground=col if not active else col,
                command=lambda n=name: self._set_filter(n),
            )
            btn.pack(side="left", padx=(0, 6))
            self._pill_btns[name] = btn

    # ── Table ─────────────────────────────────────────────────────────────────

    def _build_table(self, row: int) -> None:
        frame = tk.Frame(self, bg=C_BG)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("P.Treeview",
                        rowheight=26, font=("Segoe UI", 10),
                        background=C_BG, fieldbackground=C_BG)
        style.configure("P.Treeview.Heading",
                        font=("Segoe UI", 9, "bold"),
                        background="#f1f5f9")

        self._tree = ttk.Treeview(frame, columns=_COLS,
                                  show="headings", selectmode="browse",
                                  style="P.Treeview")
        for col, head, width, stretch in zip(_COLS, _HEADS, _WIDTHS, _STRETCH):
            self._tree.heading(col, text=head)
            self._tree.column(col, width=width, stretch=stretch, anchor="w")

        # one tag per category colour + special states
        for cat, colour in CAT_COLORS.items():
            self._tree.tag_configure(f"cat_{cat}", foreground=colour)
        self._tree.tag_configure("high", foreground=HIGH_COLOR)
        self._tree.tag_configure("done", foreground=DONE_COLOR)
        self._tree.tag_configure("fail", foreground=FAIL_COLOR)

        vs = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=self._tree.yview)
        hs = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")

        self._tree.bind("<<TreeviewSelect>>", lambda _: self._on_select())
        self._tree.bind("<Double-1>", self._edit_selected)

        self._placeholder = tk.Label(
            frame,
            text="Choose a source folder above, then click  Preview.",
            font=("Segoe UI", 13), fg="#94a3b8", bg=C_BG)
        self._placeholder.place(relx=0.5, rely=0.45, anchor="center")

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self, row: int) -> None:
        foot = tk.Frame(self, bg="#e2e8f0", padx=14, pady=8)
        foot.grid(row=row, column=0, sticky="ew")
        foot.columnconfigure(3, weight=1)

        self._btn_edit = tk.Button(foot, text="Edit selected",
                                   command=self._edit_selected, state=tk.DISABLED,
                                   relief="flat", bg="#e2e8f0", fg="#475569",
                                   cursor="hand2", font=("Segoe UI", 9))
        self._btn_edit.grid(row=0, column=0, padx=(0, 8))

        tk.Button(foot, text="Clear", command=self._clear,
                  relief="flat", bg="#e2e8f0", fg="#475569",
                  cursor="hand2", font=("Segoe UI", 9)).grid(row=0, column=1, padx=(0, 14))

        ttk.Progressbar(foot, variable=self._progress,
                        maximum=100, length=150).grid(row=0, column=2, padx=(0, 10))

        tk.Label(foot, textvariable=self._status,
                 bg="#e2e8f0", fg="#64748b",
                 font=("Segoe UI", 9), anchor="w").grid(row=0, column=3, sticky="ew")

        self._btn_preview = tk.Button(
            foot, text="Preview", command=self._on_preview,
            relief="flat", bg="#2563eb", fg="white",
            activebackground="#1d4ed8", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=18, pady=5)
        self._btn_preview.grid(row=0, column=4, padx=(0, 6))

        self._btn_apply = tk.Button(
            foot, text="Apply", command=self._on_apply,
            relief="flat", bg="#15803d", fg="white",
            activebackground="#166534", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=18, pady=5)
        self._btn_apply.grid(row=0, column=5)

    # ── Folder pickers ─────────────────────────────────────────────────────────

    def _pick_source(self) -> None:
        d = filedialog.askdirectory(title="Source folder")
        if d:
            self._src_var.set(str(Path(d).resolve()))
            if not self._out_var.get().strip():
                self._out_var.set(str(Path(d).resolve() / "organized_papers"))

    def _pick_output(self) -> None:
        d = filedialog.askdirectory(title="Output folder")
        if d:
            self._out_var.set(str(Path(d).resolve()))

    # ── Category filter ────────────────────────────────────────────────────────

    def _set_filter(self, name: str) -> None:
        self._filter = name
        self._redraw_pills()
        self._repopulate_table()

    def _repopulate_table(self) -> None:
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._item_paper.clear()

        papers = self._papers
        if self._filter != "All":
            papers = [p for p in papers if p.category == self._filter]

        for p in papers:
            self._insert_row(p)

        if self._papers:
            self._placeholder.place_forget()
        else:
            self._placeholder.place(relx=0.5, rely=0.45, anchor="center")

        self._on_select()

    def _insert_row(self, paper: Paper) -> str:
        if paper.state == State.DONE:
            tag = "done"
        elif paper.state == State.FAILED:
            tag = "fail"
        elif paper.is_high_priority:
            tag = "high"
        else:
            tag = f"cat_{paper.category}"

        iid = self._tree.insert("", tk.END, values=(
            paper.source.name,
            "→",
            paper.new_name or "—",
            paper.category,
            "★" if paper.is_high_priority else "",
            paper.status_label,
        ), tags=(tag,))
        self._item_paper[iid] = paper
        return iid

    # ── Actions ────────────────────────────────────────────────────────────────

    def _on_preview(self) -> None:
        src = self._src_var.get().strip()
        if not src or not Path(src).is_dir():
            messagebox.showinfo("No folder", "Choose a source folder first.")
            return
        self._run(execute=False)

    def _on_apply(self) -> None:
        planned = [p for p in self._papers if p.state == State.PLANNED]
        if planned:
            self._do_apply(planned)
        else:
            self._on_preview()

    def _run(self, execute: bool) -> None:
        src  = Path(self._src_var.get().strip())
        outs = self._out_var.get().strip()
        out  = Path(outs) if outs else src / "organized_papers"
        self._clear()
        self._set_busy(True)
        self._status.set("Collecting PDFs…")

        def _bg() -> None:
            pdfs = collect_pdfs([src], recursive=self._rec_var.get())
            if not pdfs:
                self.after(0, lambda: (self._set_busy(False),
                    self._status.set("No PDF files found.")))
                return

            def _prog(i, total, name):
                self.after(0, self._progress.set, (i / max(total, 1)) * 100)
                self.after(0, self._status.set,
                           f"{i}/{total}  {name}" if name else "Planning complete.")

            papers = plan_papers(
                pdfs, out,
                prefix=self._prefix, digits=self._digits, start=self._start,
                template=self._template, categories=self._categories,
                sort_into_folders=self._sub_var.get(),
                on_progress=_prog,
            )
            if execute:
                apply_plan(papers, copy=self._copy_var.get())
            self.after(0, self._show_results, papers, not execute)

        threading.Thread(target=_bg, daemon=True).start()

    def _do_apply(self, planned: list[Paper]) -> None:
        self._set_busy(True)
        self._status.set(f"Applying {len(planned)} files…")

        def _bg() -> None:
            apply_plan(planned, copy=self._copy_var.get())
            self.after(0, self._show_results, self._papers, False)

        threading.Thread(target=_bg, daemon=True).start()

    def _show_results(self, papers: list[Paper], is_preview: bool) -> None:
        self._papers = papers
        self._redraw_pills()
        self._repopulate_table()
        self._progress.set(0 if is_preview else 100)
        self._set_busy(False)

        done    = sum(1 for p in papers if p.state == State.DONE)
        failed  = sum(1 for p in papers if p.state == State.FAILED)
        planned = sum(1 for p in papers if p.state == State.PLANNED)

        if is_preview:
            self._status.set(f"{planned} files planned — click Apply to execute.")
        else:
            self._status.set(f"Done: {done} succeeded, {failed} failed.")

    def _clear(self) -> None:
        self._papers.clear()
        self._item_paper.clear()
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._placeholder.place(relx=0.5, rely=0.45, anchor="center")
        self._filter = "All"
        self._redraw_pills()
        self._progress.set(0)
        self._status.set("Ready.")
        self._on_select()

    # ── Edit selected ──────────────────────────────────────────────────────────

    def _on_select(self) -> None:
        p = self._selected_paper()
        self._btn_edit.configure(
            state=tk.NORMAL if (p and p.state == State.PLANNED) else tk.DISABLED)

    def _selected_paper(self) -> Paper | None:
        sel = self._tree.selection() or [self._tree.focus()]
        return self._item_paper.get(sel[0]) if (sel and sel[0]) else None

    def _edit_selected(self, _event=None) -> None:
        p = self._selected_paper()
        if p and p.state == State.PLANNED:
            _EditDialog(self, p)

    def refresh_row(self, paper: Paper) -> None:
        self._redraw_pills()
        self._repopulate_table()

    # ── Settings ───────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        _SettingsDialog(self)

    # ── Busy / packages ────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool) -> None:
        st = tk.DISABLED if busy else tk.NORMAL
        self._btn_preview.configure(state=st)
        self._btn_apply.configure(state=st)

    def _check_packages(self) -> None:
        missing = (["pypdf"] if not PDF_OK else []) + (["requests"] if not NET_OK else [])
        if missing:
            self._status.set("⚠  Missing: " + ", ".join(missing) +
                             " — run:  pip install " + " ".join(missing))


# ═════════════════════════════════════════════════════════════════════════════
# Settings dialog
# ═════════════════════════════════════════════════════════════════════════════

class _SettingsDialog(tk.Toplevel):
    def __init__(self, parent: PaperOrganizerApp) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self._app = parent

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        self._build_naming(nb)
        self._build_categories(nb)

        row = ttk.Frame(self)
        row.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(row, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        ttk.Button(row, text="Save",   command=self._save).pack(side="right")
        self.wait_window()

    def _build_naming(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="  Naming  ")
        f.columnconfigure(1, weight=1)

        self._pfx = tk.StringVar(value=self._app._prefix)
        self._dig = tk.StringVar(value=str(self._app._digits))
        self._sta = tk.StringVar(value=str(self._app._start))
        self._tpl = tk.StringVar(value=self._app._template)

        for i, (lbl, var) in enumerate([("Prefix", self._pfx),
                                         ("Digits", self._dig),
                                         ("Start",  self._sta)]):
            ttk.Label(f, text=lbl).grid(row=i, column=0, sticky="w", padx=(0,10), pady=5)
            ttk.Entry(f, textvariable=var, width=12).grid(row=i, column=1, sticky="w")

        ttk.Label(f, text="Template").grid(row=3, column=0, sticky="w", padx=(0,10), pady=(10,5))
        ttk.Entry(f, textvariable=self._tpl, width=46).grid(row=3, column=1, sticky="ew", pady=(10,5))
        ttk.Label(f, text="Placeholders: {id} {author} {title} {journal} {journal_full} {year} {year_short} {category}",
                  foreground="#64748b", font=("Segoe UI", 8),
                  wraplength=340).grid(row=4, column=0, columnspan=2, sticky="w")

    def _build_categories(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="  Categories  ")
        f.columnconfigure(1, weight=1)
        f.rowconfigure(0, weight=1)

        self._cat_kw: dict[str, str] = {
            cat: "; ".join(kws) for cat, kws in self._app._categories.items()
        }
        cat_names = list(self._app._categories.keys())

        lb = tk.Listbox(f, selectmode=tk.SINGLE, height=8, width=14, exportselection=False)
        for c in cat_names:
            lb.insert(tk.END, c)
        lb.select_set(0)
        lb.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._lb = lb

        kw_f = ttk.LabelFrame(f, text="Keywords (semicolon-separated)", padding=6)
        kw_f.grid(row=0, column=1, sticky="nsew")
        kw_f.columnconfigure(0, weight=1)
        kw_f.rowconfigure(0, weight=1)
        self._kw_text = tk.Text(kw_f, height=8, width=32, wrap=tk.WORD)
        self._kw_text.pack(fill="both", expand=True)
        self._kw_text.insert("1.0", self._cat_kw.get(cat_names[0], "") if cat_names else "")
        lb.bind("<<ListboxSelect>>", self._switch_cat)

    def _switch_cat(self, _event=None) -> None:
        sel = self._lb.curselection()
        if not sel:
            return
        cat_names = list(self._app._categories.keys())
        old = cat_names[sel[0]]
        self._cat_kw[old] = self._kw_text.get("1.0", tk.END).strip()
        self._kw_text.delete("1.0", tk.END)
        self._kw_text.insert("1.0", self._cat_kw.get(old, ""))

    def _save(self) -> None:
        sel = self._lb.curselection()
        if sel:
            old = list(self._app._categories.keys())[sel[0]]
            self._cat_kw[old] = self._kw_text.get("1.0", tk.END).strip()

        self._app._prefix   = self._pfx.get().strip() or "CB"
        self._app._template = self._tpl.get().strip() or "{id} {author}, {title}, {journal} {year_short}.pdf"
        try:
            self._app._digits = max(1, int(self._dig.get()))
            self._app._start  = max(1, int(self._sta.get()))
        except ValueError:
            pass
        for cat, txt in self._cat_kw.items():
            self._app._categories[cat] = [k.strip() for k in txt.split(";") if k.strip()]

        self._app._status.set("Settings saved — run Preview again to apply.")
        self.destroy()


# ═════════════════════════════════════════════════════════════════════════════
# Edit-row dialog
# ═════════════════════════════════════════════════════════════════════════════

class _EditDialog(tk.Toplevel):
    def __init__(self, parent: PaperOrganizerApp, paper: Paper) -> None:
        super().__init__(parent)
        self.title("Edit row")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self._parent = parent
        self._paper  = paper

        dest           = paper.destination
        self._base_dir = dest.parent if dest else Path(".")
        self._sep      = parent._sub_var.get()

        self._cat_var  = tk.StringVar(value=paper.category)
        self._name_var = tk.StringVar(value=dest.name if dest else "")
        self._full_var = tk.StringVar()

        f = ttk.Frame(self, padding=16)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        for i, (lbl, var, ro, kind) in enumerate([
            ("Source",      tk.StringVar(value=paper.source.name), True,  "entry"),
            ("Category",    self._cat_var,                         False, "combo"),
            ("Filename",    self._name_var,                        False, "entry"),
            ("Full output", self._full_var,                        True,  "entry"),
        ]):
            ttk.Label(f, text=lbl).grid(row=i, column=0, sticky="w", padx=(0,12), pady=6)
            if kind == "combo":
                w = ttk.Combobox(f, textvariable=var, width=46,
                                 values=list(DEFAULT_CATEGORIES.keys()))
            else:
                w = ttk.Entry(f, textvariable=var, width=48)
            if ro:
                w.configure(state="readonly")
            w.grid(row=i, column=1, sticky="ew", pady=6)

        btn = ttk.Frame(f)
        btn.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btn, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btn, text="Save",   command=self._save).grid(row=0, column=1)

        self._cat_var.trace_add("write",  self._refresh)
        self._name_var.trace_add("write", self._refresh)
        self._refresh()
        self.wait_window()

    def _dest(self) -> Path:
        cat  = self._cat_var.get().strip() or "General"
        name = self._name_var.get().strip()
        if name and not name.lower().endswith(".pdf"):
            name += ".pdf"
        base = (self._base_dir.parent / cat) if self._sep else self._base_dir
        return base / (name or "unnamed.pdf")

    def _refresh(self, *_) -> None:
        self._full_var.set(str(self._dest()))

    def _save(self) -> None:
        new_dest = self._dest()
        key = str(new_dest.resolve()).lower()
        for other in self._parent._papers:
            if other is self._paper or other.destination is None:
                continue
            if str(other.destination.resolve()).lower() == key:
                messagebox.showerror("Conflict",
                    "Another row already targets that path.", parent=self)
                return
        self._paper.category    = self._cat_var.get().strip() or "General"
        self._paper.new_name    = new_dest.name
        self._paper.destination = new_dest
        self._parent.refresh_row(self._paper)
        self._parent._status.set(f"Updated: {self._paper.source.name}")
        self.destroy()


def run() -> None:
    PaperOrganizerApp().mainloop()
