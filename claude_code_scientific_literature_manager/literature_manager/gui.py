import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from literature_manager.core import (
    PDF_READER_AVAILABLE,
    REQUESTS_AVAILABLE,
    apply_planned_records,
    collect_pdfs_from_paths,
    process_pdf_paths,
)
from literature_manager.gui_dialogs import show_edit_record_dialog
from literature_manager.gui_layout import build_main_layout
from literature_manager.settings import load_config
from literature_manager.ui_config import (
    category_names,
    category_prefix_lines,
    default_sort_rules,
    merge_sort_rules_with_base,
    parse_category_prefixes,
    positive_int,
    split_keyword_text,
)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None


class LiteratureManagerApp:
    def __init__(self, root, initial_paths=None):
        self.root = root
        self.root.title("Scientific Literature Manager")
        self.root.geometry("1120x720")
        self.root.minsize(900, 600)

        self.base_config = load_config(None)
        self.selected_paths = []
        self.preview_records = []
        self.preview_output_dir = None
        self.preview_separate_category_folders = False
        self.preview_rename_files = True
        self.result_records = {}
        self.output_folder = tk.StringVar()
        self.copy_files = tk.BooleanVar(value=True)
        self.recursive = tk.BooleanVar(value=True)
        self.task_mode = tk.StringVar(value="Rename only")
        rules = default_sort_rules(self.base_config)
        self.sort_folder_names = [
            tk.StringVar(value=folder_name)
            for folder_name, _keywords in rules
        ]
        self.sort_keyword_texts = []
        self.sort_keyword_defaults = [
            "; ".join(keywords)
            for _folder_name, keywords in rules
        ]
        self.category_keyword_values = {
            category: "; ".join(keywords)
            for category, keywords in self.base_config.get("categories", {}).items()
        }
        self.category_choice = tk.StringVar(value=category_names(self.base_config)[0])
        self.current_category_name = self.category_choice.get()
        self.loading_category_keywords = False
        self.prefix_text = tk.StringVar(
            value=str(self.base_config.get("identifier_prefix", "CB")),
        )
        self.start_number = tk.StringVar(
            value=str(self.base_config.get("start_number", 1)),
        )
        self.identifier_digits = tk.StringVar(
            value=str(self.base_config.get("identifier_digits", 3)),
        )
        mode = self.base_config.get("numbering_mode", "global")
        self.numbering_mode = tk.StringVar(
            value="Separate by category" if mode == "category" else "One sequence",
        )
        self.status_text = tk.StringVar()
        self.preview_categories = list(self.base_config.get("categories", {}).keys())

        self.build_layout()
        self.watch_preview_inputs()
        self.refresh_dependency_status()
        if initial_paths:
            self.add_paths(initial_paths)

    def build_layout(self):
        build_main_layout(self)

    def watch_preview_inputs(self):
        variables = [
            self.output_folder,
            self.recursive,
            self.task_mode,
            self.prefix_text,
            self.start_number,
            self.identifier_digits,
            self.numbering_mode,
            *self.sort_folder_names,
        ]
        for variable in variables:
            variable.trace_add("write", lambda *args: self.invalidate_preview())

    def invalidate_preview(self):
        if self.preview_records:
            self.clear_results()
            self.status_text.set("Preview cleared. Preview changes again when ready.")

    def register_drop_target(self, widget):
        if TkinterDnD is None:
            return
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", self.handle_drop)

    def handle_drop(self, event):
        dropped_paths = [Path(path) for path in self.root.tk.splitlist(event.data)]
        self.add_paths(dropped_paths)

    def drop_area_text(self):
        if TkinterDnD is None:
            return "Drop PDFs here after installing tkinterdnd2\nor use Add PDF files"
        return "Drop PDFs or folders here"

    def add_pdf_files(self):
        filenames = filedialog.askopenfilenames(
            title="Choose PDF files",
            filetypes=[("PDF files", "*.pdf *.PDF"), ("All files", "*.*")],
        )
        self.add_paths(Path(filename) for filename in filenames)

    def add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder of PDFs")
        if folder:
            self.add_paths([Path(folder)])

    def add_paths(self, paths):
        existing = {path.resolve() for path in self.selected_paths if path.exists()}
        added = 0

        for path in paths:
            path = Path(path).expanduser()
            if not path.exists():
                continue

            resolved = path.resolve()
            if resolved in existing:
                continue

            existing.add(resolved)
            self.selected_paths.append(resolved)
            self.path_list.insert(tk.END, str(resolved))
            added += 1

        if added:
            self.set_default_output_folder()
            self.clear_results()
            self.status_text.set(f"Added {added} item(s).")

    def remove_selected(self):
        selected_indexes = list(self.path_list.curselection())
        for index in reversed(selected_indexes):
            self.path_list.delete(index)
            del self.selected_paths[index]

        if selected_indexes:
            self.clear_results()
            self.status_text.set(f"Removed {len(selected_indexes)} item(s).")

    def clear_paths(self):
        self.selected_paths.clear()
        self.path_list.delete(0, tk.END)
        self.clear_results()
        self.status_text.set("Cleared input list.")

    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Choose output folder")
        if folder:
            self.output_folder.set(str(Path(folder).resolve()))

    def set_default_output_folder(self):
        if self.output_folder.get().strip() or not self.selected_paths:
            return

        first_path = self.selected_paths[0]
        parent = first_path if first_path.is_dir() else first_path.parent
        self.output_folder.set(str(parent / "organized_papers"))

    def selected_pdf_paths(self):
        return collect_pdfs_from_paths(self.selected_paths, recursive=self.recursive.get())

    def resolved_output_folder(self):
        output = self.output_folder.get().strip()
        if output:
            return Path(output).expanduser().resolve()

        self.set_default_output_folder()
        return Path(self.output_folder.get()).expanduser().resolve()

    def save_current_category_keywords(self):
        if not hasattr(self, "category_keyword_text") or self.loading_category_keywords:
            return

        category = self.current_category_name
        if category:
            self.category_keyword_values[category] = self.category_keyword_text.get(
                "1.0",
                tk.END,
            ).strip()

    def load_selected_category_keywords(self, *_args):
        if not hasattr(self, "category_keyword_text"):
            return

        self.save_current_category_keywords()
        category = self.category_choice.get() or "General"
        self.current_category_name = category
        self.loading_category_keywords = True
        self.category_keyword_text.delete("1.0", tk.END)
        self.category_keyword_text.insert(
            "1.0",
            self.category_keyword_values.get(category, ""),
        )
        self.loading_category_keywords = False

    def category_keywords_changed(self, _event=None):
        if self.loading_category_keywords:
            return

        self.save_current_category_keywords()
        self.invalidate_preview()

    def parse_category_keyword_values(self):
        self.save_current_category_keywords()
        categories = {}

        for category, value in self.category_keyword_values.items():
            if category.lower() == "general":
                categories[category] = []
            else:
                categories[category] = split_keyword_text(value)

        categories.setdefault("General", [])
        return categories

    def parse_category_prefixes(self):
        text = self.category_prefixes.get("1.0", tk.END)
        start_number = positive_int(self.start_number.get(), 1)
        return parse_category_prefixes(text, start_number)

    def parse_sort_keyword_rules(self, base_categories):
        rules = []
        for index, text_box in enumerate(self.sort_keyword_texts):
            category = self.sort_folder_names[index].get().strip()
            if not category:
                continue

            value = text_box.get("1.0", tk.END)
            rules.append((category, split_keyword_text(value)))

        return merge_sort_rules_with_base(rules, base_categories)

    def config_from_gui(self):
        config = load_config(None)
        config["identifier_prefix"] = self.prefix_text.get().strip() or "CB"
        config["start_number"] = positive_int(self.start_number.get(), 1)
        config["identifier_digits"] = positive_int(
            self.identifier_digits.get(),
            3,
        )
        config["numbering_mode"] = (
            "category"
            if self.numbering_mode.get() == "Separate by category"
            else "global"
        )
        config["category_identifiers"] = self.parse_category_prefixes()
        config["categories"] = self.parse_category_keyword_values()
        if self.task_mode.get() == "Sort into category folders only":
            config["categories"] = self.parse_sort_keyword_rules(config["categories"])
        return config

    def separate_category_folders(self):
        return self.task_mode.get() in {
            "Sort into category folders only",
            "Sort into category folders + rename",
        }

    def rename_files(self):
        return self.task_mode.get() != "Sort into category folders only"

    def preview_files(self):
        self.run_processing(dry_run=True)

    def process_files(self):
        if self.preview_records:
            self.apply_reviewed_records()
            return

        self.run_processing(dry_run=False)

    def run_processing(self, dry_run):
        if not self.selected_paths:
            messagebox.showinfo("No input", "Choose PDF files or a folder first.")
            return

        pdf_paths = self.selected_pdf_paths()
        if not pdf_paths:
            messagebox.showinfo("No PDFs", "No PDF files were found in the selected input.")
            return

        output_dir = self.resolved_output_folder()
        config = self.config_from_gui()
        copy = self.copy_files.get()
        separate_category_folders = self.separate_category_folders()
        rename_files = self.rename_files()

        self.set_busy(True)
        self.clear_results()
        if dry_run:
            self.preview_output_dir = output_dir
            self.preview_separate_category_folders = separate_category_folders
            self.preview_rename_files = rename_files
            self.preview_categories = list(config.get("categories", {}).keys())

        if separate_category_folders and rename_files:
            action = "Previewing category folders and filenames" if dry_run else "Sorting and renaming"
        elif separate_category_folders:
            action = "Previewing category folders" if dry_run else "Sorting"
        else:
            action = "Previewing filenames" if dry_run else "Renaming"
        self.status_text.set(f"{action} {len(pdf_paths)} PDF file(s)...")

        thread = threading.Thread(
            target=self.process_in_background,
            args=(
                pdf_paths,
                output_dir,
                config,
                dry_run,
                copy,
                separate_category_folders,
                rename_files,
            ),
            daemon=True,
        )
        thread.start()

    def process_in_background(
        self,
        pdf_paths,
        output_dir,
        config,
        dry_run,
        copy,
        separate_category_folders,
        rename_files,
    ):
        try:
            records = process_pdf_paths(
                pdf_paths=pdf_paths,
                output_dir=output_dir,
                config=config,
                dry_run=dry_run,
                copy=copy,
                separate_category_folders=separate_category_folders,
                rename_files=rename_files,
            )
        except Exception as error:
            self.root.after(0, self.show_processing_error, error)
            return

        self.root.after(0, self.show_records, records, dry_run)

    def apply_reviewed_records(self):
        self.set_busy(True)
        self.status_text.set(f"Applying {len(self.preview_records)} reviewed PDF file(s)...")
        thread = threading.Thread(
            target=self.apply_records_in_background,
            args=(list(self.preview_records), self.copy_files.get()),
            daemon=True,
        )
        thread.start()

    def apply_records_in_background(self, records, copy):
        try:
            records = apply_planned_records(records, copy=copy)
        except Exception as error:
            self.root.after(0, self.show_processing_error, error)
            return

        self.root.after(0, self.show_records, records, False)

    def show_processing_error(self, error):
        self.set_busy(False)
        self.status_text.set("Processing failed.")
        messagebox.showerror("Processing failed", str(error))

    def show_records(self, records, dry_run):
        self.clear_results(clear_preview=not dry_run)
        if dry_run:
            self.preview_records = records

        for record in records:
            item = self.results.insert("", tk.END, values=self.result_values(record))
            self.result_records[item] = record

        self.set_busy(False)
        action = "Previewed" if dry_run else "Processed"
        self.status_text.set(f"{action} {len(records)} PDF file(s).")
        self.refresh_edit_button()

    def result_values(self, record):
        destination = record.destination_path or ""
        return (
            record.source_path.name,
            record.category,
            ", ".join(record.matched_keywords),
            record.new_filename,
            str(destination),
            self.result_text(record.action),
        )

    def refresh_result_row(self, item, record):
        self.results.item(item, values=self.result_values(record))

    def selected_result_item(self):
        selection = self.results.selection()
        if selection:
            return selection[0]
        focused = self.results.focus()
        return focused or None

    def selected_preview_record(self):
        item = self.selected_result_item()
        if not item:
            return None, None

        record = self.result_records.get(item)
        if record is None or record.action != "preview":
            return item, None

        return item, record

    def refresh_edit_button(self):
        if not hasattr(self, "edit_button"):
            return

        _item, record = self.selected_preview_record()
        state = tk.NORMAL if record is not None else tk.DISABLED
        self.edit_button.configure(state=state)

    def edit_selected_record(self, event=None):
        item, record = self.selected_preview_record()
        if record is None:
            return

        show_edit_record_dialog(self, item, record)

    def result_text(self, action):
        labels = {
            "preview": (
                "Will sort + rename"
                if self.preview_separate_category_folders and self.preview_rename_files
                else (
                    "Will sort"
                    if self.preview_separate_category_folders
                    else "Will rename"
                )
            ),
            "copied": "Copied",
            "moved": "Moved",
        }
        return labels.get(action, action)

    def clear_results(self, clear_preview=True):
        for item in self.results.get_children():
            self.results.delete(item)
        self.result_records.clear()
        if clear_preview:
            self.preview_records = []
            self.preview_output_dir = None
            self.preview_separate_category_folders = False
            self.preview_rename_files = True
            self.preview_categories = list(self.base_config.get("categories", {}).keys())
        self.refresh_edit_button()

    def set_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        for button in [
            self.add_pdf_button,
            self.add_folder_button,
            self.remove_button,
            self.clear_button,
            self.preview_button,
            self.process_button,
            *getattr(self, "task_controls", []),
        ]:
            button.configure(state=state)

        install_state = tk.DISABLED if busy or not self.missing_packages() else tk.NORMAL
        self.install_button.configure(state=install_state)
        if busy:
            self.edit_button.configure(state=tk.DISABLED)
        else:
            self.refresh_edit_button()

    def missing_packages(self):
        packages = []
        if not PDF_READER_AVAILABLE:
            packages.append("pypdf")
        if not REQUESTS_AVAILABLE:
            packages.append("requests")
        if TkinterDnD is None:
            packages.append("tkinterdnd2")
        return packages

    def refresh_dependency_status(self):
        missing = self.missing_packages()
        if missing:
            self.install_button.configure(state=tk.NORMAL)
            self.status_text.set("Missing package(s): " + ", ".join(missing))
        else:
            self.install_button.configure(state=tk.DISABLED)
            self.status_text.set("Ready.")

    def install_missing_packages(self):
        packages = self.missing_packages()
        if not packages:
            self.refresh_dependency_status()
            return

        confirm = messagebox.askyesno(
            "Install packages",
            "Install missing packages with pip?\n\n" + "\n".join(packages),
        )
        if not confirm:
            return

        self.set_busy(True)
        self.status_text.set("Installing package(s)...")
        thread = threading.Thread(
            target=self.install_in_background,
            args=(packages,),
            daemon=True,
        )
        thread.start()

    def install_in_background(self, packages):
        command = [sys.executable, "-m", "pip", "install", *packages]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.root.after(0, self.show_install_result, result)

    def show_install_result(self, result):
        self.set_busy(False)
        if result.returncode == 0:
            self.status_text.set("Packages installed. Restart the program to use them.")
            messagebox.showinfo(
                "Packages installed",
                "Packages installed. Restart the program to use them.",
            )
        else:
            self.status_text.set("Package installation failed.")
            details = result.stderr.strip() or result.stdout.strip() or "Unknown pip error."
            messagebox.showerror("Package installation failed", details)


def create_root():
    if TkinterDnD is not None:
        try:
            return TkinterDnD.Tk()
        except Exception:
            pass
    return tk.Tk()


def run_gui(initial_paths=None):
    root = create_root()
    app = LiteratureManagerApp(root, initial_paths=initial_paths)
    root.mainloop()
    return app
