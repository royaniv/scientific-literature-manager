import tkinter as tk
from tkinter import ttk

from literature_manager.ui_config import category_names, category_prefix_lines


CATEGORY_COLORS = {
    "Micelles": "#2563eb",
    "Chiral": "#7c3aed",
    "Soup": "#ea580c",
    "Astro": "#0369a1",
    "Light": "#b45309",
    "OrganBactr": "#15803d",
    "General": "#64748b",
}

APP_COLORS = {
    "bg": "#f6f9fb",
    "surface": "#ffffff",
    "line": "#d8e2ea",
    "text": "#1e293b",
    "muted": "#64748b",
    "header": "#15324a",
    "header_soft": "#244a63",
    "header_text": "#e6f2f7",
    "accent": "#2563eb",
    "accent_dark": "#1d4ed8",
    "success": "#15803d",
    "warning": "#b45309",
    "danger": "#dc2626",
}


def category_tag_name(category):
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(category or "General"))
    return f"category_{safe}"


def configure_app_theme(root):
    root.configure(bg=APP_COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=("Segoe UI", 10))
    style.configure("TFrame", background=APP_COLORS["bg"])
    style.configure("Toolbar.TFrame", background=APP_COLORS["header"])
    style.configure("TLabel", background=APP_COLORS["bg"], foreground=APP_COLORS["text"])
    style.configure(
        "Status.TLabel",
        background=APP_COLORS["surface"],
        foreground=APP_COLORS["muted"],
        padding=(12, 7),
    )
    style.configure(
        "TLabelframe",
        background=APP_COLORS["surface"],
        bordercolor=APP_COLORS["line"],
        lightcolor=APP_COLORS["line"],
        darkcolor=APP_COLORS["line"],
    )
    style.configure(
        "TLabelframe.Label",
        background=APP_COLORS["surface"],
        foreground=APP_COLORS["header"],
        font=("Segoe UI", 10, "bold"),
    )
    style.configure("TEntry", fieldbackground="#ffffff", bordercolor=APP_COLORS["line"])
    style.configure("TCombobox", fieldbackground="#ffffff", bordercolor=APP_COLORS["line"])
    style.configure("TSpinbox", fieldbackground="#ffffff", bordercolor=APP_COLORS["line"])
    style.configure(
        "Toolbar.TButton",
        background=APP_COLORS["header_soft"],
        foreground=APP_COLORS["header_text"],
        bordercolor=APP_COLORS["header_soft"],
        focusthickness=0,
        padding=(10, 6),
    )
    style.map(
        "Toolbar.TButton",
        background=[("active", "#2c5d78"), ("disabled", "#597386")],
        foreground=[("disabled", "#c5d3dd")],
    )
    style.configure(
        "Accent.TButton",
        background=APP_COLORS["accent"],
        foreground="#ffffff",
        bordercolor=APP_COLORS["accent"],
        focusthickness=0,
        padding=(10, 6),
    )
    style.map(
        "Accent.TButton",
        background=[("active", APP_COLORS["accent_dark"]), ("disabled", "#8da8df")],
        foreground=[("disabled", "#f8fbff")],
    )
    style.configure(
        "Success.TButton",
        background=APP_COLORS["success"],
        foreground="#ffffff",
        bordercolor=APP_COLORS["success"],
        focusthickness=0,
        padding=(10, 6),
    )
    style.map(
        "Success.TButton",
        background=[("active", "#166534"), ("disabled", "#89b89b")],
        foreground=[("disabled", "#f8fbff")],
    )
    style.configure(
        "Warning.TButton",
        background=APP_COLORS["warning"],
        foreground="#ffffff",
        bordercolor=APP_COLORS["warning"],
        focusthickness=0,
        padding=(10, 6),
    )
    style.configure(
        "Toolbar.TCheckbutton",
        background=APP_COLORS["header"],
        foreground=APP_COLORS["header_text"],
    )
    style.map(
        "Toolbar.TCheckbutton",
        background=[("active", APP_COLORS["header"])],
        foreground=[("disabled", "#b8c8d3")],
    )
    style.configure(
        "Results.Treeview",
        background=APP_COLORS["surface"],
        fieldbackground=APP_COLORS["surface"],
        foreground=APP_COLORS["text"],
        bordercolor=APP_COLORS["line"],
        rowheight=28,
    )
    style.configure(
        "Results.Treeview.Heading",
        background="#eef4f8",
        foreground=APP_COLORS["muted"],
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "Results.Treeview",
        background=[("selected", "#dbeafe")],
        foreground=[("selected", APP_COLORS["text"])],
    )


def build_main_layout(app):
    configure_app_theme(app.root)
    app.root.columnconfigure(0, weight=1)
    app.root.rowconfigure(1, weight=1)

    toolbar = ttk.Frame(app.root, padding=(12, 12, 12, 8), style="Toolbar.TFrame")
    toolbar.grid(row=0, column=0, sticky="ew")
    toolbar.columnconfigure(8, weight=1)

    app.add_pdf_button = ttk.Button(
        toolbar,
        text="Add PDF files",
        command=app.add_pdf_files,
        style="Toolbar.TButton",
    )
    app.add_pdf_button.grid(row=0, column=0, padx=(0, 8))

    app.add_folder_button = ttk.Button(
        toolbar,
        text="Add folder",
        command=app.add_folder,
        style="Toolbar.TButton",
    )
    app.add_folder_button.grid(row=0, column=1, padx=(0, 8))

    app.remove_button = ttk.Button(
        toolbar,
        text="Remove selected",
        command=app.remove_selected,
        style="Toolbar.TButton",
    )
    app.remove_button.grid(row=0, column=2, padx=(0, 8))

    app.clear_button = ttk.Button(
        toolbar,
        text="Clear all",
        command=app.clear_paths,
        style="Toolbar.TButton",
    )
    app.clear_button.grid(row=0, column=3, padx=(0, 16))

    ttk.Checkbutton(
        toolbar,
        text="Include subfolders",
        variable=app.recursive,
        style="Toolbar.TCheckbutton",
    ).grid(
        row=0,
        column=4,
        padx=(0, 12),
    )
    ttk.Checkbutton(
        toolbar,
        text="Keep originals",
        variable=app.copy_files,
        style="Toolbar.TCheckbutton",
    ).grid(
        row=0,
        column=5,
        padx=(0, 12),
    )

    app.preview_button = ttk.Button(
        toolbar,
        text="Preview changes",
        command=app.preview_files,
        style="Accent.TButton",
    )
    app.preview_button.grid(row=0, column=6, padx=(0, 8))

    app.process_button = ttk.Button(
        toolbar,
        text="Apply changes",
        command=app.process_files,
        style="Success.TButton",
    )
    app.process_button.grid(row=0, column=7, padx=(0, 8))

    app.install_button = ttk.Button(
        toolbar,
        text="Install missing packages",
        command=app.install_missing_packages,
        style="Warning.TButton",
    )
    app.install_button.grid(row=0, column=9)

    main_area = ttk.PanedWindow(app.root, orient=tk.HORIZONTAL)
    main_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)

    left = ttk.Frame(main_area, padding=8)
    right = ttk.Frame(main_area, padding=8)
    main_area.add(left, weight=1)
    main_area.add(right, weight=2)

    build_left_panel(app, left)
    build_results_panel(app, right)

    status = ttk.Label(
        app.root,
        textvariable=app.status_text,
        anchor="w",
        style="Status.TLabel",
    )
    status.grid(row=2, column=0, sticky="ew")


def build_left_panel(app, left):
    left.columnconfigure(0, weight=1)
    left.rowconfigure(0, weight=1)

    canvas = tk.Canvas(left, highlightthickness=0)
    scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=canvas.yview)
    content = ttk.Frame(canvas)
    content_id = canvas.create_window((0, 0), window=content, anchor="nw")

    def update_scroll_region(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def fit_content_width(event):
        canvas.itemconfigure(content_id, width=event.width)

    def scroll_with_wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def bind_scroll(_event):
        canvas.bind_all("<MouseWheel>", scroll_with_wheel)

    def unbind_scroll(_event):
        canvas.unbind_all("<MouseWheel>")

    content.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", fit_content_width)
    canvas.bind("<Enter>", bind_scroll)
    canvas.bind("<Leave>", unbind_scroll)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    build_left_panel_contents(app, content)


def build_left_panel_contents(app, left):
    left.columnconfigure(0, weight=1)
    left.rowconfigure(2, weight=1)

    ttk.Label(left, text="Input files and folders").grid(row=0, column=0, sticky="w")

    app.drop_area = tk.Label(
        left,
        text=app.drop_area_text(),
        relief=tk.GROOVE,
        bd=2,
        height=3,
        anchor="center",
        background="#e9f5f8",
        foreground=APP_COLORS["header"],
        font=("Segoe UI", 10, "bold"),
    )
    app.drop_area.grid(row=1, column=0, sticky="ew", pady=(6, 0))
    app.register_drop_target(app.drop_area)

    app.path_list = tk.Listbox(
        left,
        activestyle="none",
        height=5,
        selectmode=tk.EXTENDED,
    )
    app.path_list.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
    app.path_list.bind("<Delete>", lambda event: app.remove_selected())
    app.register_drop_target(app.path_list)

    output_frame = ttk.Frame(left)
    output_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    output_frame.columnconfigure(0, weight=1)

    ttk.Entry(output_frame, textvariable=app.output_folder).grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(0, 8),
    )
    ttk.Button(
        output_frame,
        text="Choose output",
        command=app.choose_output_folder,
    ).grid(row=0, column=1)

    task_frame = ttk.LabelFrame(left, text="Task", padding=8)
    task_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
    task_frame.columnconfigure(0, weight=1)
    app.task_controls = [
        ttk.Radiobutton(
            task_frame,
            text="Rename only",
            value="Rename only",
            variable=app.task_mode,
        ),
        ttk.Radiobutton(
            task_frame,
            text="Sort into category folders only",
            value="Sort into category folders only",
            variable=app.task_mode,
        ),
        ttk.Radiobutton(
            task_frame,
            text="Sort into category folders + rename",
            value="Sort into category folders + rename",
            variable=app.task_mode,
        ),
    ]
    app.task_controls[0].grid(row=0, column=0, sticky="w")
    app.task_controls[1].grid(row=1, column=0, sticky="w", pady=(4, 0))
    app.task_controls[2].grid(row=2, column=0, sticky="w", pady=(4, 0))

    category_frame = ttk.LabelFrame(task_frame, text="Built-in category keywords", padding=6)
    category_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    category_frame.columnconfigure(0, weight=1)

    ttk.Combobox(
        category_frame,
        textvariable=app.category_choice,
        values=category_names(app.base_config),
        state="readonly",
    ).grid(row=0, column=0, sticky="ew")
    app.category_keyword_text = tk.Text(category_frame, height=4, width=32)
    app.category_keyword_text.grid(row=1, column=0, sticky="ew", pady=(4, 0))
    app.category_keyword_text.insert(
        "1.0",
        app.category_keyword_values.get(app.category_choice.get(), ""),
    )
    app.category_keyword_text.bind("<KeyRelease>", app.category_keywords_changed)
    app.category_choice.trace_add("write", app.load_selected_category_keywords)

    ttk.Label(
        category_frame,
        text="Micelles, Chiral, Soup, Astro, Light, OrganBactr, and General are available here.",
        wraplength=280,
    ).grid(row=2, column=0, sticky="w", pady=(4, 0))

    ttk.Label(task_frame, text="Sort-only keyword folders").grid(
        row=4,
        column=0,
        sticky="w",
        pady=(10, 0),
    )
    app.sort_keyword_texts = []
    for index, folder_name in enumerate(app.sort_folder_names):
        group = ttk.LabelFrame(task_frame, text=f"{index + 1}) Folder rule", padding=6)
        group.grid(row=5 + index, column=0, sticky="ew", pady=(4, 0))
        group.columnconfigure(0, weight=1)

        ttk.Entry(group, textvariable=folder_name).grid(
            row=0,
            column=0,
            sticky="ew",
        )
        keywords = tk.Text(group, height=3, width=32)
        keywords.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        keywords.insert("1.0", app.sort_keyword_defaults[index])
        keywords.bind("<KeyRelease>", lambda event: app.invalidate_preview())
        app.sort_keyword_texts.append(keywords)

    build_naming_panel(app, left)


def build_naming_panel(app, left):
    naming_frame = ttk.LabelFrame(left, text="Naming", padding=8)
    naming_frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))
    naming_frame.columnconfigure(3, weight=1)

    ttk.Label(naming_frame, text="Prefix").grid(row=0, column=0, sticky="w")
    ttk.Entry(naming_frame, textvariable=app.prefix_text, width=8).grid(
        row=1,
        column=0,
        sticky="ew",
        padx=(0, 8),
    )

    ttk.Label(naming_frame, text="Start").grid(row=0, column=1, sticky="w")
    ttk.Spinbox(
        naming_frame,
        from_=1,
        to=999999,
        textvariable=app.start_number,
        width=8,
    ).grid(row=1, column=1, sticky="ew", padx=(0, 8))

    ttk.Label(naming_frame, text="Digits").grid(row=0, column=2, sticky="w")
    ttk.Spinbox(
        naming_frame,
        from_=1,
        to=8,
        textvariable=app.identifier_digits,
        width=6,
    ).grid(row=1, column=2, sticky="ew", padx=(0, 8))

    ttk.Label(naming_frame, text="Mode").grid(row=0, column=3, sticky="w")
    ttk.Combobox(
        naming_frame,
        textvariable=app.numbering_mode,
        values=["One sequence", "Separate by category"],
        state="readonly",
        width=20,
    ).grid(row=1, column=3, sticky="ew")

    ttk.Label(naming_frame, text="Category prefixes").grid(
        row=2,
        column=0,
        columnspan=4,
        sticky="w",
        pady=(8, 0),
    )
    app.category_prefixes = tk.Text(naming_frame, height=5, width=28)
    app.category_prefixes.grid(
        row=3,
        column=0,
        columnspan=4,
        sticky="ew",
        pady=(4, 0),
    )
    app.category_prefixes.insert("1.0", category_prefix_lines(app.base_config))
    app.category_prefixes.bind(
        "<KeyRelease>",
        lambda event: app.invalidate_preview(),
    )


def build_results_panel(app, right):
    right.columnconfigure(0, weight=1)
    right.rowconfigure(1, weight=1)

    results_header = ttk.Frame(right)
    results_header.grid(row=0, column=0, columnspan=2, sticky="ew")
    results_header.columnconfigure(0, weight=1)

    ttk.Label(results_header, text="Results").grid(row=0, column=0, sticky="w")
    app.edit_button = ttk.Button(
        results_header,
        text="Edit selected",
        command=app.edit_selected_record,
        state=tk.DISABLED,
    )
    app.edit_button.grid(row=0, column=1, sticky="e")

    columns = ("source", "category", "keywords", "filename", "destination", "action")
    app.results = ttk.Treeview(
        right,
        columns=columns,
        show="headings",
        style="Results.Treeview",
    )
    app.results.heading("source", text="Source")
    app.results.heading("category", text="Category")
    app.results.heading("keywords", text="Matched keywords")
    app.results.heading("filename", text="Filename")
    app.results.heading("destination", text="Full output")
    app.results.heading("action", text="Result")
    app.results.column("source", width=170, stretch=True)
    app.results.column("category", width=90, stretch=False)
    app.results.column("keywords", width=150, stretch=True)
    app.results.column("filename", width=240, stretch=True)
    app.results.column("destination", width=360, stretch=True)
    app.results.column("action", width=110, stretch=False)
    app.results.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
    app.results.bind("<<TreeviewSelect>>", lambda event: app.refresh_edit_button())
    app.results.bind("<Double-1>", app.edit_selected_record)
    for category, color in CATEGORY_COLORS.items():
        app.results.tag_configure(category_tag_name(category), foreground=color)
    app.results.tag_configure("priority_high", foreground=APP_COLORS["danger"])
    app.results.tag_configure("action_copied", foreground=APP_COLORS["success"])
    app.results.tag_configure("action_moved", foreground=APP_COLORS["success"])

    scrollbar = ttk.Scrollbar(right, orient=tk.VERTICAL, command=app.results.yview)
    xscrollbar = ttk.Scrollbar(right, orient=tk.HORIZONTAL, command=app.results.xview)
    app.results.configure(
        yscrollcommand=scrollbar.set,
        xscrollcommand=xscrollbar.set,
    )
    scrollbar.grid(row=1, column=1, sticky="ns", pady=(6, 0))
    xscrollbar.grid(row=2, column=0, sticky="ew")
