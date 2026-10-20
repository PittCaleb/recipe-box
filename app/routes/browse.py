from flask import Blueprint, render_template, request

from app import get_db
from app.models.recipes import list_categories, search_recipes

bp = Blueprint("browse", __name__)


def _search_params():
    return {
        "q": request.args.get("q", "").strip(),
        "category_id": request.args.get("category", type=int),
        "sort": request.args.get("sort", "name"),
        "needs_review": request.args.get("needs_review") == "1",
        "favorites": request.args.get("favorites") == "1",
    }


@bp.route("/")
def index():
    db = get_db()
    params = _search_params()
    recipes = search_recipes(db, **params)
    categories = list_categories(db)
    return render_template("index.html", recipes=recipes, categories=categories, params=params)


@bp.route("/api/search")
def api_search():
    db = get_db()
    params = _search_params()
    recipes = search_recipes(db, **params)
    return render_template("partials/_recipe_cards.html", recipes=recipes)
