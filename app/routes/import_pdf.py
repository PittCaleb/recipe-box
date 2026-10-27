import json
import re
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for

from app import get_db
from app.import_jobs import start_import_job
from app.models.categories import add_category, list_categories
from app.models.recipes import save_recipe
from app.users import current_user

bp = Blueprint("import_pdf", __name__, url_prefix="/admin/import")


def _cfg():
    return current_app.config["RECIPES_CONFIG"]


def _safe_pdf_filename(original_name):
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", original_name.rsplit(".", 1)[0]).strip("-") or "upload"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}-{stem}.pdf"


@bp.route("/", methods=["GET"])
def new():
    if not _cfg().ANTHROPIC_API_KEY:
        flash("ANTHROPIC_API_KEY isn't set, so PDF import can't call Claude yet. Add it to your environment and restart the app.")
    return render_template("admin/import_upload.html")


@bp.route("/", methods=["POST"])
def create():
    cfg = _cfg()
    if not cfg.ANTHROPIC_API_KEY:
        flash("ANTHROPIC_API_KEY isn't set. Add it to your environment and restart the app before importing.")
        return redirect(url_for("import_pdf.new"))

    file = request.files.get("pdf")
    if not file or not file.filename:
        flash("Choose a PDF file first.")
        return redirect(url_for("import_pdf.new"))
    if not file.filename.lower().endswith(".pdf"):
        flash("That doesn't look like a PDF file.")
        return redirect(url_for("import_pdf.new"))

    cfg.PDF_DIR.mkdir(parents=True, exist_ok=True)
    cfg.ensure_data_dirs()

    pdf_filename = _safe_pdf_filename(file.filename)
    file.save(cfg.PDF_DIR / pdf_filename)

    default_contributor = request.form.get("default_contributor", "").strip() or None

    db = get_db()
    now = datetime.now().isoformat(timespec="seconds")
    cur = db.execute(
        """INSERT INTO import_batches
           (source_pdf, original_filename, status, default_contributor, created_at, updated_at)
           VALUES (?, ?, 'pending', ?, ?, ?)""",
        (pdf_filename, file.filename, default_contributor, now, now),
    )
    db.commit()
    batch_id = cur.lastrowid

    start_import_job(cfg, batch_id, pdf_filename, default_contributor)

    return redirect(url_for("import_pdf.progress", batch_id=batch_id))


@bp.route("/<int:batch_id>")
def progress(batch_id):
    db = get_db()
    batch = db.execute("SELECT * FROM import_batches WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        abort(404)

    if batch["status"] in ("ready", "error"):
        recipes = db.execute(
            "SELECT * FROM import_batch_recipes WHERE batch_id = ? ORDER BY source_page, id", (batch_id,)
        ).fetchall()
        staged = []
        for r in recipes:
            d = dict(r)
            d["ingredients"] = json.loads(r["ingredients_json"])
            d["notes"] = json.loads(r["notes_json"])
            staged.append(d)
        return render_template(
            "admin/import_review.html", batch=batch, recipes=staged, categories=list_categories(db)
        )

    return render_template("admin/import_progress.html", batch=batch)


@bp.route("/<int:batch_id>/status")
def status(batch_id):
    db = get_db()
    batch = db.execute("SELECT * FROM import_batches WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        abort(404)
    return jsonify(
        status=batch["status"], total_pages=batch["total_pages"],
        processed_pages=batch["processed_pages"], error_message=batch["error_message"],
    )


@bp.route("/<int:batch_id>/commit", methods=["POST"])
def commit(batch_id):
    db = get_db()
    batch = db.execute("SELECT * FROM import_batches WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        abort(404)

    recipes = db.execute(
        "SELECT * FROM import_batch_recipes WHERE batch_id = ? ORDER BY source_page, id", (batch_id,)
    ).fetchall()

    category_cache = {c["name"].lower(): c["id"] for c in list_categories(db)}
    imported = 0

    for r in recipes:
        if request.form.get(f"include_{r['id']}") != "1":
            continue

        category_name = request.form.get(f"category_{r['id']}", "").strip()
        category_id = None
        if category_name:
            category_id = category_cache.get(category_name.lower())
            if category_id is None:
                category_id = add_category(db, category_name)
                category_cache[category_name.lower()] = category_id

        fields = {
            "title": request.form.get(f"title_{r['id']}", r["title"]).strip() or r["title"],
            "category_id": category_id,
            "contributor": r["contributor"],
            "source": r["source"],
            "servings": r["servings"],
            "prep_time": r["prep_time"],
            "cook_time": r["cook_time"],
            "instructions_html": r["instructions_html"],
            "needs_review": r["needs_review"],
            "owner_id": current_user()["id"],
        }
        ingredients = json.loads(r["ingredients_json"])
        recipe_id = save_recipe(db, None, fields, ingredients)

        notes = json.loads(r["notes_json"])
        now = datetime.now().isoformat(timespec="seconds")
        for note_body in notes:
            db.execute(
                "INSERT INTO notes (recipe_id, body, created_at, author_id) VALUES (?, ?, ?, ?)",
                (recipe_id, note_body, now, current_user()["id"]),
            )

        if r["scan_filename"]:
            db.execute(
                "UPDATE recipes SET scan_filename = ?, source_pdf = ?, source_page = ? WHERE id = ?",
                (r["scan_filename"], batch["source_pdf"], r["source_page"], recipe_id),
            )

        db.execute("UPDATE import_batch_recipes SET imported_recipe_id = ? WHERE id = ?", (recipe_id, r["id"]))
        imported += 1

    db.execute("UPDATE import_batches SET status = 'done', updated_at = ? WHERE id = ?",
               (datetime.now().isoformat(timespec="seconds"), batch_id))
    db.commit()

    flash(f"Imported {imported} recipe{'s' if imported != 1 else ''}.")
    return redirect(url_for("admin.needs_review"))


@bp.route("/<int:batch_id>/discard", methods=["POST"])
def discard(batch_id):
    db = get_db()
    cfg = _cfg()
    batch = db.execute("SELECT * FROM import_batches WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        abort(404)

    scans = db.execute(
        "SELECT scan_filename FROM import_batch_recipes WHERE batch_id = ? AND scan_filename IS NOT NULL",
        (batch_id,),
    ).fetchall()
    for row in scans:
        path = cfg.SCANS_DIR / row["scan_filename"]
        if path.exists():
            path.unlink()

    db.execute("DELETE FROM import_batches WHERE id = ?", (batch_id,))
    db.commit()

    flash("Import discarded.")
    return redirect(url_for("import_pdf.new"))
