from flask import Blueprint, current_app, send_from_directory

bp = Blueprint("media", __name__, url_prefix="/media")


@bp.route("/scans/<path:filename>")
def scan(filename):
    cfg = current_app.config["RECIPES_CONFIG"]
    return send_from_directory(cfg.SCANS_DIR, filename)


@bp.route("/images/<path:filename>")
def image(filename):
    cfg = current_app.config["RECIPES_CONFIG"]
    return send_from_directory(cfg.IMAGES_DIR, filename)
