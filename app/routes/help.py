from flask import Blueprint, render_template

from app.shopping import SHORTCUT_NAME

bp = Blueprint("help", __name__)


@bp.route("/about")
def about():
    return render_template("help/about.html")


@bp.route("/help/shopping-list")
def shopping_list():
    return render_template("help/shopping_list.html", shortcut_name=SHORTCUT_NAME)
