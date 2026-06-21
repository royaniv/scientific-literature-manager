"""
gui.py — Desktop GUI with a dark sidebar and full-width results table.

Layout (completely different from the split-pane original):

  ┌────────────────────────────────────────────────────────────────┐
  │  [dark header]  Source folder  [_______________]  [Browse]     │
  │                 Output folder  [_______________]  [Browse]     │
  ├─────────────┬──────────────────────────────────────────────────┤
  │  SIDEBAR    │  RESULTS TABLE (fills the rest of the window)    │
  │  (dark)     │                                                  │
  │  All   24   │  Source file     New name          Cat    ★  St │
  │  ─────────  │  download.pdf →  CB001 Lancet...  Mic   ★  Prev│
  │  Micelles 5 │  paper1.pdf   →  CB002 Segre...   Soup     Prev│
  │  Chiral   3 │  fulltext.pdf →  CB003 Yaniv...   Astro    Prev│
  │  Soup     2 │                                                  │
  │  Astro    1 │                                                  │
  │  General 13 │                                                  │
  │  ─────────  │                                                  │
  │  Prefix CB  │                                                  │
  │  Digits  3  │                                                  │
  │  ☐ Subfoldr │                                                  │
  │  ☐ Recursive│                                                  │
  │  ☐ Copy     │                                                  │
  ├─────────────┴──────────────────────────────────────────────────┤
  │  [Preview]  [Apply]  ████████░░  12/24  Planning files...      │
  └────────────────────────────────────────────────────────────────┘

What makes this different:
  - Category sidebar that acts as a live filter (click Micelles → see only those rows)
  - Settings live in the sidebar, not a separate left panel
  - The results table is the dominant element; nothing competes with it
  - Action buttons are at the bottom, not the top
  - Dark header + dark sidebar for a modern two-tone look
"""
from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from paper_organizer.core import (
    DEFAULT_CATEGORIES, PDF_OK, NET_OK,
    Paper, State,
    apply_plan, collect_pdfs, plan_papers,
)

# ── Colour palette ────────────────────────────────────────────────────────────

C_BG       = "#f1f4f8"   # main background (light)
C_SIDEBAR  = "#1b2d4f"   # sidebar background (dark navy)
C_HEADER   = "#16243e"   # header strip (darker navy)
C_SIDE_TXT = "#8faac8"   # sidebar label text
C_SIDE_SEL = "#2a4a7a"   # selected category highlight
C_SIDE_HOV = "#243d64"   # hovered category highlight
C_ACCENT   = "#2563eb"   # blue accent (Preview button)
C_GREEN    = "#16a34a"   # Apply button
C_HIGH     = "#dc2626"   # high-priority row text
C_DONE     = "#15803d"   # done row text
C_FAIL     = "#94a3b8"   # failed row text
C_PLANNED  = "#1d4ed8"   # planned row text

_TABLE_COLS   = ("source", "arrow", "new_name", "category", "priority", "status")
_TABLE_HEADS  = ("Source file", "",  "New name", "Category", "★", "Status")
_TABLE_WIDTHS = (190,           22,   280,        88,          22,  90)
_TABLE_STRETCH= (True,          False, True,       False,       False, False)


class PaperOrganizerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Paper Organizer")
        self.geometry("1000x680")
        self.minsize(800, 520)
        self.configure(bg=C_BG)

        # --- state ---
        self._all_papers:     list[Paper]      = []
        self._item_to_paper:  dict[str, Paper] = {}
        self._active_filter:  str              = "All"
        self._categories:     dict[str, list[str]] = dict(DEFAULT_CATEGORIES)
        self._is_busy:        bool             = False

        # --- tk variables ---
        self._src_var      = tk.StringVar()
        self._out_var      = tk.StringVar()
        self._prefix_var   = tk.StringVar(value="CB")
        self._digits_var   = tk.StringVar(value="3")
        self._start_var    = tk.StringVar(value="1")
        self._recursive_var = tk.BooleanVar(value=True)
        self._sort_var     = tk.BooleanVar(value=False)
        self._copy_var     = tk.BooleanVar(value=True)
        self._status_var   = tk.StringVar(value="Choose a source folder, then click Preview.")
        self._progress_var = tk.DoubleVar(value=0.0)

        # --- sidebar filter button references ---
        self._filter_btns: dict[str, tk.Button] = {}

        self._build_ui()
        self._update_sidebar_counts()
        self._check_packages()

    # ═════════════════════════════════════════════════════════════════════════
    # Layout
    # ═════════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_header(row=0)
        self._build_middle(row=1)
        self._build_footer(row=2)

    # ── Header ───────────────────────────────────────────────────────────────

    def _build_header(self, row: int) -> None:
        hdr = tk.Frame(self, bg=C_HEADER, padx=16, pady=10)
        hdr.grid(row=row, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)
        hdr.columnconfigure(3, weight=1)

        label_cfg  = dict(bg=C_HEADER, fg=C_SIDE_TXT, font=("Segoe UI", 9))
        entry_cfg  = dict(relief="flat", bg="#243d64", fg="white",
                          insertbackground="white", font=("Segoe UI", 10), bd=0)
        browse_cfg = dict(relief="flat", bg="#2a4a7a", fg="white",
                          activebackground="#3a5e96", cursor="hand2",
                          font=("Segoe UI", 9), padx=8)

        tk.Label(hdr, text="Source folder", **label_cfg).grid(row=0, column=0, sticky="w", padx=(0,8))
        tk.Entry(hdr, textvariable=self._src_var, **entry_cfg).grid(row=0, column=1, sticky="ew", ipady=5)
        tk.Button(hdr, text="Browse…", command=self._pick_source, **browse_cfg).grid(row=0, column=2, padx=(6,20), ipady=3)

        tk.Label(hdr, text="Output folder", **label_cfg).grid(row=0, column=3, sticky="w", padx=(0,8))
        tk.Entry(hdr, textvariable=self._out_var, **entry_cfg).grid(row=0, column=4, sticky="ew", ipady=5)
        tk.Button(hdr, text="Browse…", command=self._pick_output, **browse_cfg).grid(row=0, column=5, padx=(6,0), ipady=3)

    # ── Middle (sidebar + table) ──────────────────────────────────────────────

    def _build_middle(self, row: int) -> None:
        mid = tk.Frame(self, bg=C_BG)
        mid.grid(row=row, column=0, sticky="nsew")
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(0, weight=1)

        self._build_sidebar(mid)
        self._build_table(mid)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sb = tk.Frame(parent, bg=C_SIDEBAR, width=168)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.columnconfigure(0, weight=1)

        # ── Category filters ──
        tk.Label(sb, text="CATEGORIES", bg=C_SIDEBAR, fg=C_SIDE_TXT,
                 font=("Segoe UI", 8, "bold"), anchor="w",
                 padx=14, pady=(14,2)).pack(fill="x")

        filter_names = ["All"] + list(DEFAULT_CATEGORIES.keys())
        for name in filter_names:
            btn = tk.Button(
                sb, text=name,
                bg=C_SIDE_SEL if name == "All" else C_SIDEBAR,
                fg="white" if name == "All" else C_SIDE_TXT,
                font=("Segoe UI", 10), anchor="w",
                relief="flat", bd=0, padx=14, pady=5,
                activebackground=C_SIDE_HOV, activeforeground="white",
                cursor="hand2",
                command=lambda n=name: self._set_filter(n),
            )
            btn.pack(fill="x")
            self._filter_btns[name] = btn

        # ── Divider ──
        tk.Frame(sb, bg="#2a3f5f", height=1).pack(fill="x", padx=10, pady=(12,12))

        # ── Settings ──
        tk.Label(sb, text="SETTINGS", bg=C_SIDEBAR, fg=C_SIDE_TXT,
                 font=("Segoe UI", 8, "bold"), anchor="w",
                 padx=14, pady=2).pack(fill="x")

        cfg_f = tk.Frame(sb, bg=C_SIDEBAR, padx=14)
        cfg_f.pack(fill="x", pady=4)

        def _row(label: str, var: tk.StringVar, width: int = 6) -> None:
            tk.Label(cfg_f, text=label, bg=C_SIDEBAR, fg=C_SIDE_TXT,
                     font=("Segoe UI", 9), anchor="w").pack(fill="x")
            tk.Entry(cfg_f, textvariable=var, width=width,
                     font=("Segoe UI", 10), relief="flat",
                     bg="#243d64", fg="white",
                     insertbackground="white").pack(fill="x", pady=(0, 6), ipady=3)

        _row("Prefix", self._prefix_var)
        _row("Digits", self._digits_var)
        _row("Start at", self._start_var)

        # ── Checkboxes ──
        def _chk(label: str, var: tk.BooleanVar) -> None:
            tk.Checkbutton(
                sb, text=label, variable=var,
                bg=C_SIDEBAR, fg=C_SIDE_TXT, selectcolor=C_SIDEBAR,
                activebackground=C_SIDEBAR, activeforeground="white",
                font=("Segoe UI", 9), anchor="w",
            ).pack(fill="x", padx=14, pady=2)

        _chk("Sort into category folders", self._sort_var)
        _chk("Include subfolders",         self._recursive_var)
        _chk("Keep originals (copy)",      self._copy_var)

        # ── Spacer + edit button at bottom ──
        tk.Frame(sb, bg=C_SIDEBAR).pack(fill="both", expand=True)
        tk.Frame(sb, bg="#2a3f5f", height=1).pack(fill="x", padx=10, pady=8)

        self._edit_btn = tk.Button(
            sb, text="Edit selected row",
            bg=C_SIDEBAR, fg=C_SIDE_TXT,
            relief="flat", font=("Segoe UI", 9),
            cursor="hand2", state=tk.DISABLED,
            command=self._edit_selected,
        )
        self._edit_btn.pack(fill="x", padx=14, pady=(0, 10))

    # ── Table ────────────────────────────────────────────────────────────────

    def _build_table(self, parent: tk.Frame) -> None:
        tbl_frame = tk.Frame(parent, bg=C_BG)
        tbl_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        tbl_frame.columnconfigure(0, weight=1)
        tbl_frame.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Papers.Treeview",
                        rowheight=26, font=("Segoe UI", 10),
                        background="white", fieldbackground="white")
        style.configure("Papers.Treeview.Heading",
                        font=("Segoe UI", 9, "bold"))

        self._tree = ttk.Treeview(
            tbl_frame, columns=_TABLE_COLS,
            show="headings", selectmode="browse",
            style="Papers.Treeview",
        )
        for col, head, width, stretch in zip(
                _TABLE_COLS, _TABLE_HEADS, _TABLE_WIDTHS, _TABLE_STRETCH):
            self._tree.heading(col, text=head)
            self._tree.column(col, width=width, stretch=stretch, anchor="w")

        self._tree.tag_configure("high",    foreground=C_HIGH)
        self._tree.tag_configure("fail",    foreground=C_FAIL)
        self._tree.tag_configure("done",    foreground=C_DONE)
        self._tree.tag_configure("planned", foreground=C_PLANNED)

        self._tree.bind("<<TreeviewSelect>>", lambda _: self._on_select())
        self._tree.bind("<Double-1>",          self._edit_selected)

        vs = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL,   command=self._tree.yview)
        hs = ttk.Scrollbar(tbl_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")

        # Empty state placeholder
        self._placeholder = tk.Label(
            tbl_frame,
            text="Choose a source folder above,\nthen click Preview.",
            font=("Segoe UI", 13), fg="#94a3b8", bg="white",
        )
        self._placeholder.place(relx=0.5, rely=0.45, anchor="center")

    # ── Footer ───────────────────────────────────────────────────────────────

    def _build_footer(self, row: int) -> None:
        foot = tk.Frame(self, bg="#e2e8f0", padx=14, pady=8)
        foot.grid(row=row, column=0, sticky="ew")
        foot.columnconfigure(2, weight=1)

        self._progress_bar = ttk.Progressbar(
            foot, variable=self._progress_var, maximum=100, length=160)
        self._progress_bar.grid(row=0, column=0, padx=(0,10))

        self._badge_lbl = tk.Label(
            foot, text="", bg="#e2e8f0", fg="#475569",
            font=("Segoe UI", 9))
        self._badge_lbl.grid(row=0, column=1, padx=(0,10))

        tk.Label(foot, textvariable=self._status_var,
                 bg="#e2e8f0", fg="#64748b",
                 font=("Segoe UI", 9), anchor="w").grid(row=0, column=2, sticky="ew")

        tk.Button(foot, text="Clear", command=self._clear,
                  relief="flat", bg="#e2e8f0", fg="#475569",
                  cursor="hand2", font=("Segoe UI", 9)).grid(row=0, column=3, padx=(0,10))

        self._btn_preview = tk.Button(
            foot, text="Preview", command=self._on_preview,
            relief="flat", bg=C_ACCENT, fg="white",
            activebackground="#1d4ed8", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=18, pady=5)
        self._btn_preview.grid(row=0, column=4, padx=(0,6))

        self._btn_apply = tk.Button(
            foot, text="Apply", command=self._on_apply,
            relief="flat", bg=C_GREEN, fg="white",
            activebackground="#166534", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=18, pady=5)
        self._btn_apply.grid(row=0, column=5)

    # ═════════════════════════════════════════════════════════════════════════
    # Folder picking
    # ═════════════════════════════════════════════════════════════════════════

    def _pick_source(self) -> None:
        d = filedialog.askdirectory(title="Choose source folder")
        if d:
            self._src_var.set(str(Path(d).resolve()))
            if not self._out_var.get().strip():
                self._out_var.set(str(Path(d).resolve() / "organized_papers"))

    def _pick_output(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self._out_var.set(str(Path(d).resolve()))

    # ═════════════════════════════════════════════════════════════════════════
    # Category filter
    # ═════════════════════════════════════════════════════════════════════════

    def _set_filter(self, name: str) -> None:
        # Update button appearance
        for btn_name, btn in self._filter_btns.items():
            if btn_name == name:
                btn.configure(bg=C_SIDE_SEL, fg="white")
            else:
                btn.configure(bg=C_SIDEBAR, fg=C_SIDE_TXT)
        self._active_filter = name
        self._repopulate_table()

    def _update_sidebar_counts(self) -> None:
        counts: dict[str, int] = {"All": len(self._all_papers)}
        for cat in DEFAULT_CATEGORIES:
            counts[cat] = sum(1 for p in self._all_papers if p.category == cat)

        for name, btn in self._filter_btns.items():
            n   = counts.get(name, 0)
            lbl = f"{name}   {n}" if n else name
            btn.configure(text=lbl)

    def _repopulate_table(self) -> None:
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._item_to_paper.clear()

        papers = self._all_papers
        if self._active_filter != "All":
            papers = [p for p in papers if p.category == self._active_filter]

        for paper in papers:
            self._insert_row(paper)

        if self._all_papers:
            self._placeholder.place_forget()
        else:
            self._placeholder.place(relx=0.5, rely=0.45, anchor="center")

        self._on_select()

    def _insert_row(self, paper: Paper) -> str:
        tag = ("high"    if paper.is_high_priority and paper.state != State.DONE
               else "fail"    if paper.state == State.FAILED
               else "done"    if paper.state == State.DONE
               else "planned")
        iid = self._tree.insert("", tk.END, values=(
            paper.source.name,
            "→",
            paper.new_name or "—",
            paper.category,
            "★" if paper.is_high_priority else "",
            paper.status_label,
        ), tags=(tag,))
        self._item_to_paper[iid] = paper
        return iid

    # ═════════════════════════════════════════════════════════════════════════
    # Actions
    # ═════════════════════════════════════════════════════════════════════════

    def _on_preview(self) -> None:
        src = self._src_var.get().strip()
        if not src or not Path(src).is_dir():
            messagebox.showinfo("No source folder",
                                "Choose a source folder before running Preview.")
            return
        self._run(execute=False)

    def _on_apply(self) -> None:
        planned = [p for p in self._all_papers if p.state == State.PLANNED]
        if planned:
            self._do_apply(planned)
        else:
            src = self._src_var.get().strip()
            if not src or not Path(src).is_dir():
                messagebox.showinfo("No source folder", "Choose a source folder first.")
                return
            self._run(execute=True)

    def _run(self, execute: bool) -> None:
        src   = Path(self._src_var.get().strip())
        out_s = self._out_var.get().strip()
        out   = Path(out_s) if out_s else src / "organized_papers"

        try:
            prefix = self._prefix_var.get().strip() or "CB"
            digits = max(1, int(self._digits_var.get() or "3"))
            start  = max(1, int(self._start_var.get()  or "1"))
        except ValueError:
            messagebox.showerror("Bad settings", "Digits and Start must be whole numbers.")
            return

        self._clear()
        self._set_busy(True)
        self._status_var.set("Collecting PDFs…")

        def _bg() -> None:
            pdfs = collect_pdfs([src], recursive=self._recursive_var.get())
            if not pdfs:
                self.after(0, lambda: (
                    self._set_busy(False),
                    self._status_var.set("No PDF files found in the selected folder."),
                ))
                return

            total = len(pdfs)

            def _progress(i: int, _total: int, name: str) -> None:
                pct = (i / max(_total, 1)) * 100
                self.after(0, self._progress_var.set, pct)
                self.after(0, self._status_var.set,
                           f"{i}/{_total}  {name}" if name else "Done planning.")

            papers = plan_papers(
                pdfs, out,
                prefix=prefix, digits=digits, start=start,
                categories=self._categories,
                sort_into_folders=self._sort_var.get(),
                on_progress=_progress,
            )
            if execute:
                apply_plan(papers, copy=self._copy_var.get())

            self.after(0, self._show_results, papers, not execute)

        threading.Thread(target=_bg, daemon=True).start()

    def _do_apply(self, planned: list[Paper]) -> None:
        self._set_busy(True)
        self._status_var.set(f"Applying {len(planned)} files…")

        def _bg() -> None:
            apply_plan(planned, copy=self._copy_var.get())
            self.after(0, self._show_results, self._all_papers, False)

        threading.Thread(target=_bg, daemon=True).start()

    def _show_results(self, papers: list[Paper], is_preview: bool) -> None:
        self._all_papers = papers
        self._update_sidebar_counts()
        self._repopulate_table()
        self._progress_var.set(100)
        self._set_busy(False)

        done    = sum(1 for p in papers if p.state == State.DONE)
        failed  = sum(1 for p in papers if p.state == State.FAILED)
        planned = sum(1 for p in papers if p.state == State.PLANNED)
        high    = sum(1 for p in papers if p.is_high_priority)

        parts = []
        if planned: parts.append(f"{planned} planned")
        if done:    parts.append(f"{done} done")
        if failed:  parts.append(f"{failed} failed")
        if high:    parts.append(f"{high} high-priority")
        self._badge_lbl.configure(text="  ·  ".join(parts))

        if is_preview:
            self._status_var.set("Preview ready — click Apply to execute.")
            self._progress_var.set(0)
        else:
            self._status_var.set(f"Complete: {done} succeeded, {failed} failed.")

    def _clear(self) -> None:
        self._all_papers.clear()
        self._item_to_paper.clear()
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._placeholder.place(relx=0.5, rely=0.45, anchor="center")
        self._badge_lbl.configure(text="")
        self._progress_var.set(0)
        self._status_var.set("Ready.")
        self._update_sidebar_counts()
        self._on_select()

    # ═════════════════════════════════════════════════════════════════════════
    # Edit selected row
    # ═════════════════════════════════════════════════════════════════════════

    def _on_select(self) -> None:
        paper = self._selected_paper()
        can   = paper is not None and paper.state == State.PLANNED
        self._edit_btn.configure(state=tk.NORMAL if can else tk.DISABLED)

    def _selected_paper(self) -> Paper | None:
        sel = self._tree.selection() or [self._tree.focus()]
        return self._item_to_paper.get(sel[0]) if (sel and sel[0]) else None

    def _edit_selected(self, _event=None) -> None:
        paper = self._selected_paper()
        if paper and paper.state == State.PLANNED:
            _EditDialog(self, paper)

    def refresh_paper_row(self, paper: Paper) -> None:
        """Called by _EditDialog after saving changes."""
        self._repopulate_table()
        self._update_sidebar_counts()

    # ═════════════════════════════════════════════════════════════════════════
    # Busy / package check
    # ═════════════════════════════════════════════════════════════════════════

    def _set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        st = tk.DISABLED if busy else tk.NORMAL
        self._btn_preview.configure(state=st)
        self._btn_apply.configure(state=st)

    def _check_packages(self) -> None:
        missing = []
        if not PDF_OK: missing.append("pypdf")
        if not NET_OK: missing.append("requests")
        if missing:
            self._status_var.set(
                "⚠  Missing packages: " + ", ".join(missing) +
                ".  Run:  pip install " + " ".join(missing))


# ═════════════════════════════════════════════════════════════════════════════
# Edit dialog
# ═════════════════════════════════════════════════════════════════════════════

class _EditDialog(tk.Toplevel):
    """Let the user correct the category and filename for one planned paper."""

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
        self._sep      = parent._sort_var.get()

        self._cat_var  = tk.StringVar(value=paper.category)
        self._name_var = tk.StringVar(value=dest.name if dest else "")
        self._full_var = tk.StringVar()

        self._build()
        self._cat_var.trace_add("write",  self._refresh)
        self._name_var.trace_add("write", self._refresh)
        self._refresh()
        self.wait_window()

    def _build(self) -> None:
        f = ttk.Frame(self, padding=16)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        rows = [
            ("Source",     tk.StringVar(value=self._paper.source.name), True,  "entry"),
            ("Category",   self._cat_var,                               False, "combo"),
            ("Filename",   self._name_var,                              False, "entry"),
            ("Full output",self._full_var,                              True,  "entry"),
        ]
        for i, (lbl, var, readonly, kind) in enumerate(rows):
            ttk.Label(f, text=lbl).grid(row=i, column=0, sticky="w", padx=(0,12), pady=6)
            if kind == "combo":
                w = ttk.Combobox(f, textvariable=var, width=46,
                                 values=list(DEFAULT_CATEGORIES.keys()))
            else:
                w = ttk.Entry(f, textvariable=var, width=48)
            if readonly:
                w.configure(state="readonly")
            w.grid(row=i, column=1, sticky="ew", pady=6)

        btn_row = ttk.Frame(f)
        btn_row.grid(row=len(rows), column=0, columnspan=2, sticky="e", pady=(12,0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=(0,8))
        ttk.Button(btn_row, text="Save",   command=self._save).grid(row=0, column=1)

    def _planned_dest(self) -> Path:
        cat  = self._cat_var.get().strip() or "General"
        name = self._name_var.get().strip()
        if name and not name.lower().endswith(".pdf"):
            name += ".pdf"
        base = (self._base_dir.parent / cat) if self._sep else self._base_dir
        return base / (name or "unnamed.pdf")

    def _refresh(self, *_) -> None:
        self._full_var.set(str(self._planned_dest()))

    def _save(self) -> None:
        new_dest = self._planned_dest()
        key = str(new_dest.resolve()).lower()
        for other in self._parent._all_papers:
            if other is self._paper or other.destination is None:
                continue
            if str(other.destination.resolve()).lower() == key:
                messagebox.showerror("Conflict",
                    "Another row already targets that output path.", parent=self)
                return
        self._paper.category    = self._cat_var.get().strip() or "General"
        self._paper.new_name    = new_dest.name
        self._paper.destination = new_dest
        self._parent.refresh_paper_row(self._paper)
        self._parent._status_var.set(f"Updated: {self._paper.source.name}")
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    PaperOrganizerApp().mainloop()
