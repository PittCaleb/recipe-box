from flask import Blueprint, abort, current_app, jsonify, request, send_file

from app import get_db
from app.models.recipes import get_recipe
from app.rendering.jpg import render_recipe_jpg
from app.rendering.pdf import render_recipe_pdf
from app.sharing import get_backend
from app.sharing.validate import validate_email, validate_imessage_target

bp = Blueprint("share", __name__, url_prefix="/recipes")


def _cfg():
    return current_app.config["RECIPES_CONFIG"]


def _get_or_404(db, recipe_id):
    data = get_recipe(db, recipe_id)
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


def _build_jpg(data, recipe_id):
    pdf_path = _build_pdf(data, recipe_id)
    cfg = _cfg()
    out_path = cfg.TMP_DIR / f"recipe-{recipe_id}.jpg"
    render_recipe_jpg(pdf_path, out_path)
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


@bp.route("/<int:recipe_id>/email", methods=["POST"])
def email(recipe_id):
    db = get_db()
    data = _get_or_404(db, recipe_id)
    cfg = _cfg()
    backend = get_backend(cfg)

    if not backend.supports_email():
        return jsonify(success=False, message="Email isn't available on this server."), 400

    to = validate_email(request.form.get("to"))
    if not to:
        return jsonify(success=False, message="Enter a valid email address."), 400
    message = request.form.get("message", "").strip()

    pdf_path = _build_pdf(data, recipe_id)
    title = data["recipe"]["title"]
    result = backend.send_email(to, f"Recipe: {title}", message, pdf_path)
    return jsonify(success=result.success, message=result.message)


@bp.route("/<int:recipe_id>/text", methods=["POST"])
def text(recipe_id):
    db = get_db()
    data = _get_or_404(db, recipe_id)
    cfg = _cfg()
    backend = get_backend(cfg)

    if not backend.supports_imessage():
        return jsonify(success=False, message="Text isn't available on this server."), 400

    to = validate_imessage_target(request.form.get("to"))
    if not to:
        return jsonify(success=False, message="Enter a valid phone number or iMessage email."), 400
    message = request.form.get("message", "").strip()

    jpg_path = _build_jpg(data, recipe_id)
    result = backend.send_imessage(to, message, jpg_path)
    return jsonify(success=result.success, message=result.message)
