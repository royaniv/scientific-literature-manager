import argparse
import io
import os
import shutil
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, send_file, url_for

from literature_manager.core import (
    apply_planned_records,
    category_output_dir,
    collect_pdfs,
    plan_pdf_paths,
    sanitize_filename,
    unique_path,
)
from literature_manager.settings import load_config
from literature_manager.ui_config import (
    category_prefix_lines,
    default_sort_rules as default_sort_rule_pairs,
    merge_sort_rules_with_base,
    parse_category_prefixes,
    positive_int,
    split_keyword_text,
)


WEB_TEMP_WORKSPACE = Path(
    os.environ.get(
        "SLM_WEB_WORKSPACE",
        Path(tempfile.gettempdir()) / "scientific_literature_manager_web",
    ),
)
MAX_JOB_AGE_SECONDS = 24 * 60 * 60
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
JOBS = {}


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    @app.before_request
    def before_request():
        cleanup_jobs()

    @app.route("/", methods=["GET"])
    def index():
        config = load_config(None)
        return render_template(
            "index.html",
            config=config,
            category_prefixes=category_prefix_lines(config),
            sort_rules=default_sort_rules(config),
            error=request.args.get("error", ""),
        )

    @app.route("/preview", methods=["POST"])
    def preview():
        if request.form.get("input_mode") == "local":
            return create_local_preview_job()

        uploaded_files = request.files.getlist("pdf_files")
        uploaded_files = [file for file in uploaded_files if file and file.filename]

        if not uploaded_files:
            return redirect(url_for("index", error="Choose at least one PDF file."))

        job_id = uuid.uuid4().hex
        job_dir = WEB_TEMP_WORKSPACE / job_id
        upload_dir = job_dir / "uploads"
        output_dir = job_dir / "output"
        upload_dir.mkdir(parents=True, exist_ok=True)

        pdf_paths = []
        for uploaded_file in uploaded_files:
            filename = sanitize_filename(uploaded_file.filename)
            if not filename.lower().endswith(".pdf"):
                continue

            destination = unique_path(upload_dir / filename)
            uploaded_file.save(destination)
            pdf_paths.append(destination)

        if not pdf_paths:
            remove_job_dir(job_dir)
            return redirect(url_for("index", error="Only PDF files can be processed."))

        try:
            config = config_from_form(request.form)
            separate_folders, rename_files = task_settings_from_form(request.form)
            records = plan_pdf_paths(
                pdf_paths,
                output_dir,
                config,
                separate_category_folders=separate_folders,
                rename_files=rename_files,
            )
        except Exception as error:
            remove_job_dir(job_dir)
            return redirect(url_for("index", error=str(error)))

        JOBS[job_id] = {
            "created": time.time(),
            "job_dir": job_dir,
            "mode": "upload",
            "output_dir": output_dir,
            "records": records,
            "categories": list(config.get("categories", {}).keys()),
            "separate_category_folders": separate_folders,
            "rename_files": rename_files,
        }
        return render_preview(job_id)

    @app.route("/local-preview", methods=["POST"])
    def local_preview():
        return create_local_preview_job()

    def create_local_preview_job():
        input_dir = Path(request.form.get("input_folder", "")).expanduser()
        if not input_dir.exists() or not input_dir.is_dir():
            return redirect(url_for("index", error=f"Input folder does not exist: {input_dir}"))

        input_dir = input_dir.resolve()
        output_text = request.form.get("output_folder", "").strip()
        output_dir = (
            Path(output_text).expanduser().resolve()
            if output_text
            else input_dir / "organized_papers"
        )
        recursive = "recursive" in request.form
        copy = "keep_originals" in request.form
        pdf_paths = [
            path
            for path in collect_pdfs(input_dir, recursive)
            if not is_relative_to_path(path, output_dir)
        ]

        if not pdf_paths:
            return redirect(url_for("index", error=f"No PDF files found in: {input_dir}"))

        try:
            config = config_from_form(request.form)
            separate_folders, rename_files = task_settings_from_form(request.form)
            records = plan_pdf_paths(
                pdf_paths,
                output_dir,
                config,
                separate_category_folders=separate_folders,
                rename_files=rename_files,
            )
        except Exception as error:
            return redirect(url_for("index", error=str(error)))

        job_id = uuid.uuid4().hex
        JOBS[job_id] = {
            "created": time.time(),
            "job_dir": None,
            "mode": "local",
            "output_dir": output_dir,
            "records": records,
            "categories": list(config.get("categories", {}).keys()),
            "copy": copy,
            "separate_category_folders": separate_folders,
            "rename_files": rename_files,
        }
        return render_preview(job_id)

    @app.route("/preview/<job_id>", methods=["GET"])
    def render_preview(job_id, error=""):
        job = JOBS.get(job_id)
        if job is None:
            abort(404)

        set_preview_output_paths(job)
        return render_template(
            "preview.html",
            job_id=job_id,
            records=job["records"],
            categories=job.get("categories", load_config(None).get("categories", {}).keys()),
            error=error,
            mode=job["mode"],
            rename_files=job.get("rename_files", True),
            output_heading=preview_output_heading(job),
            review_message=preview_review_message(job),
            submit_label=preview_submit_label(job),
        )

    @app.route("/apply/<job_id>", methods=["POST"])
    def apply_job(job_id):
        job = JOBS.get(job_id)
        if job is None:
            abort(404)

        records = job["records"]
        output_dir = job["output_dir"]

        try:
            update_records_from_form(
                records,
                output_dir,
                request.form,
                separate_category_folders=job.get("separate_category_folders", False),
                rename_files=job.get("rename_files", True),
            )
            if job["mode"] == "upload":
                remove_job_dir(output_dir)
                apply_planned_records(records, copy=True)
                archive = zip_output_dir(output_dir)
            else:
                apply_planned_records(records, copy=job.get("copy", True))
        except Exception as error:
            return render_preview(job_id, error=str(error))

        if job["mode"] == "upload":
            archive.seek(0)
            return send_file(
                archive,
                mimetype="application/zip",
                as_attachment=True,
                download_name="organized_papers.zip",
            )

        action = "copied" if job.get("copy", True) else "moved"
        return render_template(
            "complete.html",
            records=records,
            message=f"{len(records)} PDF file(s) {action} to the output folder.",
        )

    return app


def preview_output_heading(job):
    if job["mode"] == "upload":
        return "ZIP path"
    return "Full output path"


def preview_review_message(job):
    if job.get("rename_files", True) and job.get("separate_category_folders", False):
        task_text = "categories and filenames"
    elif job.get("separate_category_folders", False):
        task_text = "categories"
    else:
        task_text = "filenames"

    if job["mode"] == "upload":
        return f"Review {task_text} before creating the ZIP."
    return f"Review {task_text} before applying changes to the local folder."


def preview_submit_label(job):
    if job["mode"] == "upload":
        if job.get("separate_category_folders", False) and not job.get("rename_files", True):
            return "Create sorted ZIP"
        return "Create organized ZIP"
    if job.get("copy", True):
        if job.get("separate_category_folders", False) and not job.get("rename_files", True):
            return "Copy files to category folders"
        return "Copy files to output folder"
    if job.get("separate_category_folders", False) and not job.get("rename_files", True):
        return "Move files to category folders"
    return "Move files to output folder"


def task_settings_from_form(form):
    task_mode = form.get("task_mode", "rename")
    if task_mode == "sort":
        return True, False
    if task_mode == "sort_rename":
        return True, True
    return False, True


def default_sort_rules(config):
    rules = default_sort_rule_pairs(config)
    return [
        {
            "index": index,
            "folder": folder,
            "keywords": "; ".join(keywords),
        }
        for index, (folder, keywords) in enumerate(rules[:3])
    ]


def parse_sort_keyword_rules(form):
    config = load_config(None)
    rules = []
    for index in range(3):
        category = form.get(f"sort_folder_{index}", "").strip()
        if not category:
            continue

        value = form.get(f"sort_keywords_{index}", "")
        rules.append((category, split_keyword_text(value)))

    return merge_sort_rules_with_base(rules, config.get("categories", {}))

def set_preview_output_paths(job):
    output_dir = job["output_dir"]
    for record in job["records"]:
        if job["mode"] == "upload":
            record.preview_output = str(record.destination_path.relative_to(output_dir))
        else:
            record.preview_output = str(record.destination_path)


def config_from_form(form):
    config = load_config(None)
    start_number = positive_int(form.get("start_number"), 1)

    config["identifier_prefix"] = form.get("prefix", "").strip() or "CB"
    config["start_number"] = start_number
    config["identifier_digits"] = positive_int(form.get("identifier_digits"), 3)
    config["numbering_mode"] = (
        "category" if form.get("numbering_mode") == "category" else "global"
    )
    config["category_identifiers"] = parse_category_prefixes(
        form.get("category_prefixes", ""),
        start_number,
    )
    if form.get("task_mode") == "sort":
        config["categories"] = parse_sort_keyword_rules(form)
    return config


def is_relative_to_path(path, possible_parent):
    try:
        path.resolve().relative_to(possible_parent.resolve())
    except ValueError:
        return False
    return True


def update_records_from_form(
    records,
    output_dir,
    form,
    separate_category_folders=False,
    rename_files=True,
):
    for index, record in enumerate(records):
        category = sanitize_filename(form.get(f"category_{index}", record.category))
        category = category or "General"
        if rename_files:
            filename = sanitize_filename(form.get(f"filename_{index}", ""))
        else:
            filename = Path(record.destination_path).name

        if not filename:
            raise ValueError(f"Missing filename for {record.source_path.name}")
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        record.category = category
        record.new_filename = filename
        destination_dir = output_dir
        if separate_category_folders:
            destination_dir = category_output_dir(output_dir, category)
        record.destination_path = destination_dir / filename


def zip_output_dir(output_dir):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                zip_file.write(path, path.relative_to(output_dir))
    return archive


def cleanup_jobs():
    WEB_TEMP_WORKSPACE.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for job_id, job in list(JOBS.items()):
        if now - job["created"] > MAX_JOB_AGE_SECONDS:
            JOBS.pop(job_id, None)
            if job.get("job_dir") is not None:
                remove_job_dir(job["job_dir"])


def remove_job_dir(path):
    path = Path(path)
    try:
        resolved_workspace = WEB_TEMP_WORKSPACE.resolve()
        resolved_path = path.resolve()
    except FileNotFoundError:
        return

    if resolved_path == resolved_workspace or resolved_workspace not in resolved_path.parents:
        return

    shutil.rmtree(resolved_path, ignore_errors=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the web app.")
    parser.add_argument("--host", default=os.environ.get("SLM_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", os.environ.get("SLM_PORT", "5000"))),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Create the Flask app and exit without starting the server.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    app = create_app()
    if args.check:
        print("Web app check passed.")
        return

    app.run(host=args.host, port=args.port, debug=False)


app = create_app()


if __name__ == "__main__":
    main()
