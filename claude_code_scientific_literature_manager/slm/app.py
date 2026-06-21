"""Desktop GUI — horizontal split-pane layout.

Left panel (scrollable): file list, output folder, task mode,
    category keyword editor, naming config.
Right panel: rich results table (source / category / keywords /
    new name / destination / state) with Edit Selected support.

Design differences from the original:
- Single file instead of gui.py + gui_layout.py + gui_dialogs.py.
- Works with typed Config and Paper objects rather than raw dicts.
- PaperState enum values displayed as state labels.
- Progress is updated via the on_progress callback rather than
  being tracked inside the processing functions themselves.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from slm.classify import assign_category, assign_priority
from slm.config import Config, NamingConfig
from slm.extract import PYPDF_OK, REQUESTS_OK
from slm.organize import apply, collect, plan
from slm.paper import Paper, PaperState
from slm.rename import build_name, next_id

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_OK = True
except Exception:
    DND_FILES = None
    TkinterDnD = None
    _DND_OK = False

_RESULT_COLS = ("source", "category", "keywords", "new_name", "destination", "state")
_RESULT_HEADS = ("Source", "Category", "Keywords", "New name", "Destination", "State")
_RESULT_WIDTHS = (170, 90, 150, 230, 340, 110)
_RESULT_STRETCH = (True, False, True, True, True, False)


class App:
    def __init__(self, root: tk.Tk, initial_paths: list[Path] | None = None) -> None:
        self.root = root
        self.root.title("Scientific Literature Manager")
        self.root.geometry("1150x740")
        self.root.minsize(900, 600)

        self._config = Config()
        self._selected_paths: list[Path] = []
        self._papers: list[Paper] = []
        self._item_to_paper: dict[str, Paper] = {}
        self._planned = False

        self._output_var = tk.StringVar()
        self._recursive_var = tk.BooleanVar(value=True)
        self._copy_var = tk.BooleanVar(value=True)
        self._task_var = tk.StringVar(value="rename")
        self._prefix_var = tk.StringVar(value=self._config.naming.prefix)
        self._start_var = tk.StringVar(value=str(self._config.naming.start))
        self._digits_var = tk.StringVar(value=str(self._config.naming.digits))
        self._mode_var = tk.StringVar(value="One sequence")
        self._status_var = tk.StringVar(value="Ready.")

        self._category_kw_values: dict[str, str] = {
            cat: "; ".join(kws)
            for cat, kws in self._config.categories.items()
        }
        self._cat_choice_var = tk.StringVar(
            value=next(iter(self._config.categories), "General")
        )
        self._loading_cat = False

        self._build_ui()
        self._watch_inputs()
        self._refresh_status()

        if initial_paths:
            self._add_paths(initial_paths)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_toolbar()

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)

        left_frame = ttk.Frame(paned, padding=6)
        right_frame = ttk.Frame(paned, padding=6)
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=2)

        self._build_left_panel(left_frame)
        self._build_right_panel(right_frame)

        ttk.Label(self.root, textvariable=self._status_var, anchor="w",
                  padding=(12, 4)).grid(row=2, column=0, sticky="ew")

    def _build_toolbar(self) -> None:
        tb = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        tb.grid(row=0, column=0, sticky="ew")
        tb.columnconfigure(7, weight=1)

        self._btn_add_files = ttk.Button(tb, text="Add PDFs", command=self._add_pdf_files)
        self._btn_add_files.grid(row=0, column=0, padx=(0, 6))

        self._btn_add_folder = ttk.Button(tb, text="Add folder", command=self._add_folder)
        self._btn_add_folder.grid(row=0, column=1, padx=(0, 6))

        self._btn_remove = ttk.Button(tb, text="Remove", command=self._remove_selected)
        self._btn_remove.grid(row=0, column=2, padx=(0, 6))

        self._btn_clear = ttk.Button(tb, text="Clear all", command=self._clear_paths)
        self._btn_clear.grid(row=0, column=3, padx=(0, 14))

        ttk.Checkbutton(tb, text="Include subfolders",
                        variable=self._recursive_var).grid(row=0, column=4, padx=(0, 10))
        ttk.Checkbutton(tb, text="Keep originals",
                        variable=self._copy_var).grid(row=0, column=5, padx=(0, 14))

        self._btn_preview = ttk.Button(tb, text="Preview", command=self._on_preview)
        self._btn_preview.grid(row=0, column=6, padx=(0, 6))

        self._btn_apply = ttk.Button(tb, text="Apply", command=self._on_apply)
        self._btn_apply.grid(row=0, column=7, padx=(0, 20))

        self._btn_install = ttk.Button(tb, text="Install missing packages",
                                       command=self._install_packages)
        self._btn_install.grid(row=0, column=8, sticky="e")

        self._action_buttons = [
            self._btn_add_files, self._btn_add_folder, self._btn_remove,
            self._btn_clear, self._btn_preview, self._btn_apply,
        ]

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        content = ttk.Frame(canvas)
        cid = canvas.create_window((0, 0), window=content, anchor="nw")

        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(cid, width=e.width))
        canvas.bind("<Enter>", lambda e: canvas.bind_all(
            "<MouseWheel>", lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._build_left_contents(content)

    def _build_left_contents(self, left: ttk.Frame) -> None:
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Input files and folders").grid(row=0, column=0, sticky="w")

        drop_text = "Drop PDFs or folders here" if _DND_OK else "Use Add PDFs / Add folder below"
        self._drop_area = tk.Label(left, text=drop_text, relief=tk.GROOVE, bd=2,
                                   height=3, anchor="center",
                                   background="#f5f7fa", foreground="#555")
        self._drop_area.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        if _DND_OK:
            self._drop_area.drop_target_register(DND_FILES)
            self._drop_area.dnd_bind("<<Drop>>", self._handle_drop)

        self._path_list = tk.Listbox(left, activestyle="none", height=6,
                                     selectmode=tk.EXTENDED)
        self._path_list.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self._path_list.bind("<Delete>", lambda e: self._remove_selected())
        if _DND_OK:
            self._path_list.drop_target_register(DND_FILES)
            self._path_list.dnd_bind("<<Drop>>", self._handle_drop)

        out_row = ttk.Frame(left)
        out_row.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        out_row.columnconfigure(0, weight=1)
        ttk.Entry(out_row, textvariable=self._output_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(out_row, text="Output folder…",
                   command=self._choose_output).grid(row=0, column=1)

        task_f = ttk.LabelFrame(left, text="Task", padding=8)
        task_f.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        task_f.columnconfigure(0, weight=1)
        for txt, val in [
            ("Rename only", "rename"),
            ("Sort into category folders only", "sort"),
            ("Sort into category folders + rename", "sort_rename"),
        ]:
            ttk.Radiobutton(task_f, text=txt, value=val,
                            variable=self._task_var).pack(anchor="w", pady=2)

        cat_f = ttk.LabelFrame(left, text="Category keywords", padding=6)
        cat_f.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        cat_f.columnconfigure(0, weight=1)
        cat_names = list(self._config.categories.keys())
        ttk.Combobox(cat_f, textvariable=self._cat_choice_var,
                     values=cat_names, state="readonly").grid(
            row=0, column=0, sticky="ew")
        self._cat_kw_text = tk.Text(cat_f, height=4, width=30)
        self._cat_kw_text.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self._cat_kw_text.insert("1.0", self._category_kw_values.get(
            self._cat_choice_var.get(), ""))
        self._cat_kw_text.bind("<KeyRelease>", self._on_cat_kw_changed)
        self._cat_choice_var.trace_add("write", self._load_cat_keywords)

        self._build_naming_panel(left)

    def _build_naming_panel(self, left: ttk.Frame) -> None:
        nf = ttk.LabelFrame(left, text="Naming", padding=8)
        nf.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        nf.columnconfigure(3, weight=1)

        for col, label, var, kw in [
            (0, "Prefix", self._prefix_var, {"width": 8}),
            (1, "Start",  self._start_var,  {"width": 8, "from_": 1, "to": 999999}),
            (2, "Digits", self._digits_var, {"width": 6, "from_": 1, "to": 8}),
        ]:
            ttk.Label(nf, text=label).grid(row=0, column=col, sticky="w")
            if "from_" in kw:
                ttk.Spinbox(nf, textvariable=var, **kw).grid(
                    row=1, column=col, sticky="ew", padx=(0, 8))
            else:
                ttk.Entry(nf, textvariable=var, **kw).grid(
                    row=1, column=col, sticky="ew", padx=(0, 8))

        ttk.Label(nf, text="Mode").grid(row=0, column=3, sticky="w")
        ttk.Combobox(nf, textvariable=self._mode_var,
                     values=["One sequence", "Separate by category"],
                     state="readonly", width=20).grid(row=1, column=3, sticky="ew")

        ttk.Label(nf, text="Category prefixes (name = prefix, one per line)").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self._prefix_text = tk.Text(nf, height=5, width=28)
        self._prefix_text.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(4, 0))
        lines = "\n".join(f"{cat} = {pfx}" for cat, pfx in
                          self._config.naming.category_prefixes.items() if pfx)
        self._prefix_text.insert("1.0", lines)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        hdr = ttk.Frame(parent)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        ttk.Label(hdr, text="Results").grid(row=0, column=0, sticky="w")
        self._btn_edit = ttk.Button(hdr, text="Edit selected",
                                    command=self._edit_selected, state=tk.DISABLED)
        self._btn_edit.grid(row=0, column=1, sticky="e")

        self._results = ttk.Treeview(parent, columns=_RESULT_COLS, show="headings")
        for col, head, width, stretch in zip(
                _RESULT_COLS, _RESULT_HEADS, _RESULT_WIDTHS, _RESULT_STRETCH):
            self._results.heading(col, text=head)
            self._results.column(col, width=width, stretch=stretch)
        self._results.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self._results.bind("<<TreeviewSelect>>", lambda e: self._refresh_edit_btn())
        self._results.bind("<Double-1>", self._edit_selected)
        self._results.tag_configure("high", foreground="#c0392b")
        self._results.tag_configure("fail", foreground="#7f8c8d")

        vs = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self._results.yview)
        hs = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self._results.xview)
        self._results.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.grid(row=1, column=1, sticky="ns", pady=(6, 0))
        hs.grid(row=2, column=0, sticky="ew")

    def _watch_inputs(self) -> None:
        for var in (self._output_var, self._recursive_var, self._task_var,
                    self._prefix_var, self._start_var, self._digits_var, self._mode_var):
            var.trace_add("write", lambda *_: self._invalidate_preview())

    def _invalidate_preview(self) -> None:
        if self._planned:
            self._clear_results()
            self._status_var.set("Settings changed — preview again when ready.")

    def _handle_drop(self, event) -> None:
        self._add_paths([Path(p) for p in self.root.tk.splitlist(event.data)])

    def _add_pdf_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Choose PDF files",
            filetypes=[("PDF files", "*.pdf *.PDF"), ("All files", "*.*")])
        self._add_paths([Path(p) for p in paths])

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose folder")
        if folder:
            self._add_paths([Path(folder)])

    def _add_paths(self, paths) -> None:
        existing = {p.resolve() for p in self._selected_paths if p.exists()}
        added = 0
        for raw in paths:
            p = Path(raw).expanduser()
            if not p.exists():
                continue
            r = p.resolve()
            if r in existing:
                continue
            existing.add(r)
            self._selected_paths.append(r)
            self._path_list.insert(tk.END, str(r))
            added += 1
        if added:
            self._set_default_output()
            self._clear_results()
            self._status_var.set(f"Added {added} item(s).")

    def _remove_selected(self) -> None:
        for i in reversed(self._path_list.curselection()):
            self._path_list.delete(i)
            del self._selected_paths[i]
        self._clear_results()

    def _clear_paths(self) -> None:
        self._selected_paths.clear()
        self._path_list.delete(0, tk.END)
        self._clear_results()
        self._status_var.set("Cleared.")

    def _choose_output(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self._output_var.set(str(Path(d).resolve()))

    def _set_default_output(self) -> None:
        if self._output_var.get().strip() or not self._selected_paths:
            return
        first = self._selected_paths[0]
        parent = first if first.is_dir() else first.parent
        self._output_var.set(str(parent / "organized_papers"))

    def _on_cat_kw_changed(self, _event=None) -> None:
        if not self._loading_cat:
            cat = self._cat_choice_var.get()
            self._category_kw_values[cat] = self._cat_kw_text.get("1.0", tk.END).strip()
            self._invalidate_preview()

    def _load_cat_keywords(self, *_) -> None:
        cat = self._cat_choice_var.get()
        self._loading_cat = True
        self._cat_kw_text.delete("1.0", tk.END)
        self._cat_kw_text.insert("1.0", self._category_kw_values.get(cat, ""))
        self._loading_cat = False

    def _build_config(self) -> Config:
        cfg = Config()
        cfg.naming.prefix = self._prefix_var.get().strip() or "CB"
        cfg.naming.per_category = self._mode_var.get() == "Separate by category"
        try:
            cfg.naming.start = max(1, int(self._start_var.get()))
        except ValueError:
            pass
        try:
            cfg.naming.digits = max(1, int(self._digits_var.get()))
        except ValueError:
            pass
        for cat, kws_text in self._category_kw_values.items():
            cfg.categories[cat] = [k.strip() for k in kws_text.split(";") if k.strip()]
        return cfg

    def _on_preview(self) -> None:
        self._run(execute=False)

    def _on_apply(self) -> None:
        if self._planned:
            self._run_apply()
        else:
            self._run(execute=True)

    def _run(self, execute: bool) -> None:
        if not self._selected_paths:
            messagebox.showinfo("No input", "Add PDF files or a folder first.")
            return
        pdfs = collect(self._selected_paths, recursive=self._recursive_var.get())
        if not pdfs:
            messagebox.showinfo("No PDFs", "No PDF files found.")
            return
        out_str = self._output_var.get().strip()
        if not out_str:
            self._set_default_output()
            out_str = self._output_var.get().strip()
        output_dir = Path(out_str)
        config = self._build_config()
        sort = self._task_var.get() in ("sort", "sort_rename")
        rename = self._task_var.get() in ("rename", "sort_rename")
        copy = self._copy_var.get()
        self._set_busy(True)
        self._clear_results()
        action = "Previewing" if not execute else "Processing"
        self._status_var.set(f"{action} {len(pdfs)} file(s)…")
        threading.Thread(
            target=self._background_run,
            args=(pdfs, output_dir, config, sort, rename, copy, execute),
            daemon=True,
        ).start()

    def _background_run(self, pdfs, output_dir, config, sort, rename, copy, execute):
        def progress(i, total, name):
            msg = f"Planning {i}/{total}: {name}" if name else "Planning done."
            self.root.after(0, self._status_var.set, msg)

        try:
            papers = plan(pdfs, output_dir, config,
                          sort_into_folders=sort, rename=rename, on_progress=progress)
            if execute:
                papers = apply(papers, copy=copy)
        except Exception as exc:
            self.root.after(0, self._show_error, str(exc))
            return
        self.root.after(0, self._show_results, papers, not execute)

    def _run_apply(self) -> None:
        planned = [p for p in self._papers if p.state == PaperState.PLANNED]
        if not planned:
            messagebox.showinfo("Nothing to apply", "Run Preview first.")
            return
        copy = self._copy_var.get()
        self._set_busy(True)
        self._status_var.set(f"Applying {len(planned)} file(s)…")
        threading.Thread(
            target=lambda: self.root.after(
                0, self._show_results, apply(planned, copy=copy), False),
            daemon=True,
        ).start()

    def _show_results(self, papers: list[Paper], is_preview: bool) -> None:
        self._clear_results(keep_plan=is_preview)
        if is_preview:
            self._papers = papers
            self._planned = True
        for paper in papers:
            tag = "high" if paper.is_high_priority else (
                "fail" if paper.state == PaperState.FAILED else "")
            iid = self._results.insert("", tk.END, values=(
                paper.source.name,
                paper.category,
                ", ".join(paper.keywords),
                paper.new_name or "—",
                str(paper.destination) if paper.destination else "—",
                paper.state_label,
            ), tags=(tag,))
            self._item_to_paper[iid] = paper
        self._set_busy(False)
        done = sum(1 for p in papers if p.state == PaperState.DONE)
        failed = sum(1 for p in papers if p.state == PaperState.FAILED)
        planned = sum(1 for p in papers if p.state == PaperState.PLANNED)
        if is_preview:
            self._status_var.set(f"Preview: {planned} planned. Click Apply to execute.")
        else:
            self._status_var.set(f"Done: {done} succeeded, {failed} failed.")
        self._refresh_edit_btn()

    def _clear_results(self, keep_plan: bool = False) -> None:
        for iid in self._results.get_children():
            self._results.delete(iid)
        self._item_to_paper.clear()
        if not keep_plan:
            self._papers.clear()
            self._planned = False
        self._refresh_edit_btn()

    def _show_error(self, msg: str) -> None:
        self._set_busy(False)
        self._status_var.set("Error.")
        messagebox.showerror("Error", msg)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        for btn in self._action_buttons:
            btn.configure(state=state)
        missing = self._missing_packages()
        self._btn_install.configure(
            state=tk.DISABLED if (busy or not missing) else tk.NORMAL)
        if busy:
            self._btn_edit.configure(state=tk.DISABLED)
        else:
            self._refresh_edit_btn()

    def _refresh_edit_btn(self) -> None:
        sel = self._results.selection() or [self._results.focus()]
        paper = self._item_to_paper.get(sel[0]) if sel and sel[0] else None
        can_edit = paper is not None and paper.state == PaperState.PLANNED
        self._btn_edit.configure(state=tk.NORMAL if can_edit else tk.DISABLED)

    def _edit_selected(self, _event=None) -> None:
        sel = self._results.selection() or [self._results.focus()]
        if not sel or not sel[0]:
            return
        paper = self._item_to_paper.get(sel[0])
        if paper is None or paper.state != PaperState.PLANNED:
            return
        _EditDialog(self, paper, sel[0])

    def _refresh_row(self, iid: str, paper: Paper) -> None:
        self._results.item(iid, values=(
            paper.source.name,
            paper.category,
            ", ".join(paper.keywords),
            paper.new_name or "—",
            str(paper.destination) if paper.destination else "—",
            paper.state_label,
        ))

    def _missing_packages(self) -> list[str]:
        pkgs = []
        if not PYPDF_OK:
            pkgs.append("pypdf")
        if not REQUESTS_OK:
            pkgs.append("requests")
        if not _DND_OK:
            pkgs.append("tkinterdnd2")
        return pkgs

    def _refresh_status(self) -> None:
        missing = self._missing_packages()
        if missing:
            self._btn_install.configure(state=tk.NORMAL)
            self._status_var.set("Missing: " + ", ".join(missing))
        else:
            self._btn_install.configure(state=tk.DISABLED)
            self._status_var.set("Ready.")

    def _install_packages(self) -> None:
        pkgs = self._missing_packages()
        if not pkgs:
            return
        if not messagebox.askyesno("Install", "Install via pip?\n\n" + "\n".join(pkgs)):
            return
        self._set_busy(True)
        self._status_var.set("Installing…")
        def _do():
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", *pkgs],
                capture_output=True, text=True)
            self.root.after(0, self._install_done, result)
        threading.Thread(target=_do, daemon=True).start()

    def _install_done(self, result) -> None:
        self._set_busy(False)
        if result.returncode == 0:
            messagebox.showinfo("Done", "Installed. Restart to use.")
            self._status_var.set("Installed. Restart the app.")
        else:
            messagebox.showerror("Failed", result.stderr.strip() or "pip error")
            self._status_var.set("Install failed.")


class _EditDialog:
    def __init__(self, app: App, paper: Paper, iid: str) -> None:
        self._app = app
        self._paper = paper
        self._iid = iid

        dlg = tk.Toplevel(app.root)
        dlg.title("Edit output")
        dlg.transient(app.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.columnconfigure(1, weight=1)
        self._dlg = dlg

        dest = paper.destination
        self._out_dir = dest.parent if dest else Path(".")
        self._sep = self._app._task_var.get() in ("sort", "sort_rename")

        self._cat_var = tk.StringVar(value=paper.category)
        self._name_var = tk.StringVar(value=dest.name if dest else "")
        self._full_var = tk.StringVar()

        self._cat_var.trace_add("write", self._refresh_full)
        self._name_var.trace_add("write", self._refresh_full)

        self._build(dlg)
        self._refresh_full()
        dlg.wait_window()

    def _build(self, dlg: tk.Toplevel) -> None:
        pad = {"padx": 12, "pady": 4}

        ttk.Label(dlg, text="Source").grid(row=0, column=0, sticky="w", **pad)
        e = ttk.Entry(dlg, width=50)
        e.grid(row=0, column=1, sticky="ew", **pad)
        e.insert(0, self._paper.source.name)
        e.configure(state="readonly")

        ttk.Label(dlg, text="Category").grid(row=1, column=0, sticky="w", **pad)
        ttk.Combobox(dlg, textvariable=self._cat_var,
                     values=list(self._app._config.categories.keys())).grid(
            row=1, column=1, sticky="ew", **pad)

        ttk.Label(dlg, text="Filename").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(dlg, textvariable=self._name_var, width=50).grid(
            row=2, column=1, sticky="ew", **pad)

        ttk.Label(dlg, text="Full output").grid(row=3, column=0, sticky="w", **pad)
        full_e = ttk.Entry(dlg, textvariable=self._full_var, width=50)
        full_e.grid(row=3, column=1, sticky="ew", **pad)
        full_e.configure(state="readonly")

        btn_row = ttk.Frame(dlg)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="e", padx=12, pady=12)
        ttk.Button(btn_row, text="Cancel", command=self._dlg.destroy).grid(
            row=0, column=0, padx=(0, 8))
        ttk.Button(btn_row, text="Save", command=self._save).grid(row=0, column=1)

    def _planned_dest(self) -> Path:
        cat = self._cat_var.get().strip() or "General"
        name = self._name_var.get().strip()
        if name and not name.lower().endswith(".pdf"):
            name += ".pdf"
        base = (self._out_dir.parent / cat) if self._sep else self._out_dir
        return base / (name or "unnamed.pdf")

    def _refresh_full(self, *_) -> None:
        self._full_var.set(str(self._planned_dest()))

    def _save(self) -> None:
        dest = self._planned_dest()
        dest_key = str(dest.resolve()).lower()
        for other in self._app._papers:
            if other is self._paper or other.destination is None:
                continue
            if str(other.destination.resolve()).lower() == dest_key:
                messagebox.showerror("Conflict",
                    "Another row already uses that output path.", parent=self._dlg)
                return
        self._paper.category = self._cat_var.get().strip() or "General"
        self._paper.new_name = dest.name
        self._paper.destination = dest
        self._app._refresh_row(self._iid, self._paper)
        self._app._status_var.set(f"Updated {self._paper.source.name}.")
        self._dlg.destroy()


def run() -> None:
    root = TkinterDnD.Tk() if _DND_OK else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run()
