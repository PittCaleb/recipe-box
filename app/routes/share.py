from flask import Blueprint, abort, current_app, request, send_file

from app import get_db
from app.models.recipes import get_recipe
from app.rendering.image import render_recipe_png
from app.rendering.pdf import render_recipe_pdf
from app.users import current_user

bp = Blueprint("share", __name__, url_prefix="/recipes")


def _cfg():
    return current_app.config["RECIPES_CONFIG"]


def _get_or_404(db, recipe_id):
    data = get_recipe(db, recipe_id, current_user()["id"])
    if data is None:
        abort(404)
    return data


def _image_path(data):
    cfg = _cfg()
    filename = data["recipe"]["image_filename"]
    if not filename:
        return None
    path = cfg.IMAGES_DIR / filename
    return path if path.exists() else None


def _build_pdf(data, recipe_id):
    cfg = _cfg()
    cfg.ensure_data_dirs()
    out_path = cfg.TMP_DIR / f"recipe-{recipe_id}.pdf"
    render_recipe_pdf(
        data["recipe"], data["ingredients"], data["notes"], _image_path(data), out_path
    )
    return out_path


def _build_png(data, recipe_id):
    pdf_path = _build_pdf(data, recipe_id)
    out_path = _cfg().TMP_DIR / f"recipe-{recipe_id}.png"
    render_recipe_png(pdf_path, out_path)
    return out_path


def _safe_filename(title, ext):
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()
    slug = slug.replace(" ", "-") or "recipe"
    return f"{slug}.{ext}"


@bp.route("/<int:recipe_id>/pdf")
def download_pdf(recipe_id):
    db = get_db()
    data = _get_or_404(db, recipe_id)
    pdf_path = _build_pdf(data, recipe_id)
    return send_file(
        pdf_path, mimetype="application/pdf", as_attachment=True,
        download_name=_safe_filename(data["recipe"]["title"], "pdf"),
    )


@bp.route("/<int:recipe_id>/image")
def download_image(recipe_id):
    """The recipe as one PNG. ?download=1 saves it as a file; without it the
    image is served inline, which is what the Copy button fetches."""
    db = get_db()
    data = _get_or_404(db, recipe_id)
    png_path = _build_png(data, recipe_id)
    return send_file(
        png_path, mimetype="image/png",
        as_attachment=request.args.get("download") == "1",
        download_name=_safe_filename(data["recipe"]["title"], "png"),
        max_age=0,
    )
