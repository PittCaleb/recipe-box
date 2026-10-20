from datetime import datetime

from flask import Blueprint, current_app, redirect, render_template, request, send_file, url_for

from app import get_db
from app.export.txt_backup import build_backup_text
from app.models.categories import add_category, delete_category, list_categories, move_category, rename_category
from app.models.recipes import search_recipes
from app.rendering.cookbook import render_cookbook_pdf

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
def index():
    return render_template("admin/index.html")


@bp.route("/categories", methods=["GET"])
def categories():
    db = get_db()
    return render_template("admin/categories.html", categories=list_categories(db))


@bp.route("/categories/add", methods=["POST"])
def categories_add():
    db = get_db()
    add_category(db, request.form.get("name", ""))
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:category_id>/rename", methods=["POST"])
def categories_rename(category_id):
    db = get_db()
    rename_category(db, category_id, request.form.get("name", ""))
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:category_id>/move", methods=["POST"])
def categories_move(category_id):
    db = get_db()
    direction = request.form.get("direction", "")
    move_category(db, category_id, direction)
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:category_id>/delete", methods=["POST"])
def categories_delete(category_id):
    db = get_db()
    delete_category(db, category_id)
    return redirect(url_for("admin.categories"))


@bp.route("/needs-review")
def needs_review():
    db = get_db()
    recipes = search_recipes(db, needs_review=True, sort="name")
    return render_template("admin/needs_review.html", recipes=recipes)


@bp.route("/export", methods=["GET", "POST"])
def export():
    if request.method != "POST":
        return render_template("admin/export.html")

    db = get_db()
    cfg = current_app.config["RECIPES_CONFIG"]
    cfg.ensure_data_dirs()

    text = build_backup_text(db)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"recipes-backup-{timestamp}.txt"
    out_path = cfg.EXPORTS_DIR / filename
    out_path.write_text(text, encoding="utf-8")

    return send_file(out_path, mimetype="text/plain", as_attachment=True, download_name=filename)


@bp.route("/cookbook", methods=["GET"])
def cookbook():
    db = get_db()
    cfg = current_app.config["RECIPES_CONFIG"]
    return render_template(
        "admin/cookbook.html", categories=list_categories(db), default_title=cfg.COOKBOOK_TITLE
    )


@bp.route("/cookbook/build", methods=["POST"])
def cookbook_build():
    db = get_db()
    cfg = current_app.config["RECIPES_CONFIG"]
    cfg.ensure_data_dirs()

    category_ids = [int(c) for c in request.form.getlist("category_id")]
    cover_title = request.form.get("cover_title", "").strip() or cfg.COOKBOOK_TITLE
    include_images = request.form.get("include_images") == "1"
    include_notes = request.form.get("include_notes") == "1"

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"cookbook-{timestamp}.pdf"
    out_path = cfg.EXPORTS_DIR / filename

    render_cookbook_pdf(db, cfg, category_ids, cover_title, include_images, include_notes, out_path)

    return send_file(out_path, mimetype="application/pdf", as_attachment=True, download_name=filename)
