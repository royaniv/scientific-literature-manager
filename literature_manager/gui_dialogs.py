import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from literature_manager.core import category_output_dir, sanitize_filename


def show_edit_record_dialog(app, item, record):
    destination = Path(record.destination_path)
    separate_category_folders = app.preview_separate_category_folders
    rename_files = app.preview_rename_files
    if app.preview_output_dir:
        output_dir = app.preview_output_dir
    elif separate_category_folders:
        output_dir = destination.parent.parent
    else:
        output_dir = destination.parent

    dialog = tk.Toplevel(app.root)
    dialog.title("Edit output")
    dialog.transient(app.root)
    dialog.grab_set()
    dialog.columnconfigure(1, weight=1)

    category_text = tk.StringVar(value=record.category)
    filename_text = tk.StringVar(value=destination.name)
    full_output_text = tk.StringVar()

    def planned_destination():
        category = sanitize_filename(category_text.get()) or "General"
        filename = sanitize_filename(filename_text.get())
        if filename and not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        destination_dir = output_dir
        if separate_category_folders:
            destination_dir = category_output_dir(output_dir, category)
        return destination_dir / filename if filename else destination_dir

    def refresh_full_output(*args):
        full_output_text.set(str(planned_destination()))

    def save_changes():
        category = sanitize_filename(category_text.get()) or "General"
        if rename_files:
            filename = sanitize_filename(filename_text.get())
        else:
            filename = destination.name

        if not filename:
            messagebox.showerror("Missing filename", "Enter a filename.", parent=dialog)
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        destination_path = planned_destination()
        destination_key = str(destination_path.resolve()).lower()
        for other_record in app.preview_records:
            if other_record is record or other_record.destination_path is None:
                continue
            other_key = str(Path(other_record.destination_path).resolve()).lower()
            if other_key == destination_key:
                messagebox.showerror(
                    "Duplicate output",
                    "Another preview row already uses that output path.",
                    parent=dialog,
                )
                return

        record.category = category
        record.new_filename = filename
        record.destination_path = destination_path
        app.refresh_result_row(item, record)
        app.status_text.set(f"Updated output for {record.source_path.name}.")
        dialog.destroy()

    build_edit_record_form(
        app=app,
        dialog=dialog,
        record=record,
        category_text=category_text,
        filename_text=filename_text,
        full_output_text=full_output_text,
        rename_files=rename_files,
        save_changes=save_changes,
    )

    category_text.trace_add("write", refresh_full_output)
    filename_text.trace_add("write", refresh_full_output)
    refresh_full_output()
    dialog.wait_window()


def build_edit_record_form(
    app,
    dialog,
    record,
    category_text,
    filename_text,
    full_output_text,
    rename_files,
    save_changes,
):
    ttk.Label(dialog, text="Source").grid(
        row=0,
        column=0,
        sticky="w",
        padx=12,
        pady=(12, 4),
    )
    source_entry = ttk.Entry(dialog)
    source_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 4))
    source_entry.insert(0, record.source_path.name)
    source_entry.configure(state="readonly")

    ttk.Label(dialog, text="Category").grid(
        row=1,
        column=0,
        sticky="w",
        padx=12,
        pady=4,
    )
    category_entry = ttk.Combobox(
        dialog,
        textvariable=category_text,
        values=list(getattr(app, "preview_categories", app.base_config.get("categories", {}))),
    )
    category_entry.grid(
        row=1,
        column=1,
        sticky="ew",
        padx=(0, 12),
        pady=4,
    )

    ttk.Label(dialog, text="Filename").grid(
        row=2,
        column=0,
        sticky="w",
        padx=12,
        pady=4,
    )
    filename_entry = ttk.Entry(dialog, textvariable=filename_text)
    filename_entry.grid(
        row=2,
        column=1,
        sticky="ew",
        padx=(0, 12),
        pady=4,
    )
    if not rename_files:
        filename_entry.configure(state="readonly")

    ttk.Label(dialog, text="Full output").grid(
        row=3,
        column=0,
        sticky="w",
        padx=12,
        pady=4,
    )
    full_output_entry = ttk.Entry(dialog, textvariable=full_output_text)
    full_output_entry.grid(
        row=3,
        column=1,
        sticky="ew",
        padx=(0, 12),
        pady=4,
    )
    full_output_entry.configure(state="readonly")

    buttons = ttk.Frame(dialog)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", padx=12, pady=12)
    ttk.Button(buttons, text="Cancel", command=dialog.destroy).grid(
        row=0,
        column=0,
        padx=(0, 8),
    )
    ttk.Button(buttons, text="Save", command=save_changes).grid(row=0, column=1)
