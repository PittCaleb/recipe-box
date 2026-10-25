from flask import Blueprint, render_template

from app.shopping import SHORTCUT_NAME

bp = Blueprint("help", __name__, url_prefix="/help")


@bp.route("/shopping-list")
def shopping_list():
    return render_template("help/shopping_list.html", shortcut_name=SHORTCUT_NAME)
