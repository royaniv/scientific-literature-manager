"""Desktop GUI using ttk.Notebook (tabbed layout).

The original had a complex split-pane layout with multiple Tkinter files.
Here everything fits in one file using three tabs:
  Files    — choose source folder and output folder
  Options  — config settings
  Results  — table of planned / applied papers
"""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from slm.config import Config
from slm.organize import apply, collect, plan
from slm.paper import Paper, PaperState


class _ResultsTable(ttk.Frame):
    COLUMNS = ("filename", "category", "priority", "new_name", "state")
    HEADINGS = ("Source file", "Category", "Priority", "New name", "State")

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self._tree = ttk.Treeview(self, columns=self.COLUMNS, show="headings",
                                  selectmode="browse")
        for col, heading in zip(self.COLUMNS, self.HEADINGS):
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=160, anchor="w", stretch=True)
        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._tree.tag_configure("high", foreground="#c0392b")
        self._tree.tag_configure("fail", foreground="#7f8c8d")

    def populate(self, papers: list[Paper]) -> None:
        self._tree.delete(*self._tree.get_children())
        for p in papers:
            tag = "high" if p.is_high_priority else ("fail" if p.state == PaperState.FAILED else "")
            self._tree.insert("", "end", values=(
                p.source.name,
                p.category,
                p.priority,
                p.new_name or "—",
                p.state_label,
            ), tags=(tag,))


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Scientific Literature Manager")
        self.geometry("900x620")
        self.resizable(True, True)

        self._config = Config()
        self._papers: list[Paper] = []

        self._src_var = tk.StringVar()
        self._out_var = tk.StringVar()
        self._sort_var = tk.BooleanVar(value=False)
        self._move_var = tk.BooleanVar(value=False)
        self._rename_var = tk.BooleanVar(value=True)
        self._recursive_var = tk.BooleanVar(value=False)
        self._status_var = tk.StringVar(value="Ready.")
        self._progress_var = tk.DoubleVar(value=0.0)

        self._build_ui()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self._tab_files = ttk.Frame(notebook, padding=12)
        self._tab_options = ttk.Frame(notebook, padding=12)
        self._tab_results = ttk.Frame(notebook, padding=12)

        notebook.add(self._tab_files, text="  Files  ")
        notebook.add(self._tab_options, text="  Options  ")
        notebook.add(self._tab_results, text="  Results  ")

        self._notebook = notebook
        self._build_files_tab()
        self._build_options_tab()
        self._build_results_tab()
        self._build_status_bar()

    def _folder_row(self, parent: tk.Widget, label: str, var: tk.StringVar,
                    row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var, width=60).grid(row=row, column=1,
                                                            padx=6, sticky="ew")
        ttk.Button(parent, text="Browse…",
                   command=lambda v=var: v.set(
                       filedialog.askdirectory(title=f"Select {label}")
                       or v.get()
                   )).grid(row=row, column=2)

    def _build_files_tab(self) -> None:
        f = self._tab_files
        f.columnconfigure(1, weight=1)
        self._folder_row(f, "Source folder:", self._src_var, 0)
        self._folder_row(f, "Output folder:", self._out_var, 1)

        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=14, sticky="w")
        ttk.Button(btn_frame, text="Preview", command=self._on_preview).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Apply", command=self._on_apply).pack(side="left", padx=4)

        self._progress = ttk.Progressbar(f, variable=self._progress_var,
                                          maximum=100, length=500)
        self._progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=6)

    def _build_options_tab(self) -> None:
        f = self._tab_options
        f.columnconfigure(1, weight=1)
        opts = [
            ("Recursive (include subfolders)", self._recursive_var),
            ("Sort into category subfolders",  self._sort_var),
            ("Move files (default: copy)",     self._move_var),
            ("Rename files",                   self._rename_var),
        ]
        for i, (label, var) in enumerate(opts):
            ttk.Checkbutton(f, text=label, variable=var).grid(
                row=i, column=0, sticky="w", pady=3)

    def _build_results_tab(self) -> None:
        f = self._tab_results
        f.columnconfigure(0, weight=1)
        f.rowconfigure(0, weight=1)
        self._results_table = _ResultsTable(f)
        self._results_table.grid(row=0, column=0, sticky="nsew")

    def _build_status_bar(self) -> None:
        bar = ttk.Frame(self, relief="sunken", padding=(6, 2))
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self._status_var, anchor="w").pack(fill="x")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)
        self.update_idletasks()

    def _set_progress(self, i: int, total: int) -> None:
        val = (i / max(total, 1)) * 100
        self._progress_var.set(val)
        self.update_idletasks()

    def _source_dir(self) -> Path | None:
        src = self._src_var.get().strip()
        if not src:
            messagebox.showerror("No source", "Please select a source folder.")
            return None
        return Path(src)

    def _output_dir(self, src: Path) -> Path:
        out = self._out_var.get().strip()
        return Path(out) if out else src

    def _run_in_thread(self, fn):
        self.config(cursor="watch")
        t = threading.Thread(target=fn, daemon=True)
        t.start()

    def _on_preview(self) -> None:
        src = self._source_dir()
        if src is None:
            return
        self._run_in_thread(lambda: self._do_plan(src, execute=False))

    def _on_apply(self) -> None:
        src = self._source_dir()
        if src is None:
            return
        self._run_in_thread(lambda: self._do_plan(src, execute=True))

    def _do_plan(self, src: Path, execute: bool) -> None:
        try:
            self._set_status("Collecting files…")
            pdfs = collect([src], recursive=self._recursive_var.get())
            if not pdfs:
                self.after(0, lambda: messagebox.showinfo("Nothing found",
                                                          "No PDFs found in the selected folder."))
                return

            out = self._output_dir(src)

            def _progress(i: int, total: int, name: str) -> None:
                self.after(0, lambda: self._set_status(
                    f"Planning {i}/{total}: {name}" if name else "Planning complete."
                ))
                self.after(0, lambda: self._set_progress(i, total))

            self._set_status(f"Planning {len(pdfs)} files…")
            papers = plan(pdfs, out, self._config,
                          sort_into_folders=self._sort_var.get(),
                          rename=self._rename_var.get(),
                          on_progress=_progress)

            if execute:
                self._set_status("Applying…")
                papers = apply(papers, copy=not self._move_var.get())
                done = sum(1 for p in papers if p.state == PaperState.DONE)
                failed = sum(1 for p in papers if p.state == PaperState.FAILED)
                msg = f"Done: {done} succeeded, {failed} failed."
            else:
                msg = f"Preview: {len(papers)} files planned."

            self._papers = papers
            self.after(0, lambda: self._results_table.populate(self._papers))
            self.after(0, lambda: self._set_status(msg))
            self.after(0, lambda: self._notebook.select(2))
        finally:
            self.after(0, lambda: self.config(cursor=""))


def run() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run()
