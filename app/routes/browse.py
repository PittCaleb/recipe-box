from flask import Blueprint, render_template, request

from app import get_db
from app.models.recipes import group_recipes, list_categories, search_recipes

bp = Blueprint("browse", __name__)

VALID_DISPLAYS = {"card", "text"}
VALID_GROUPS = {"alpha", "category"}


def _search_params():
    display = request.args.get("display", "card")
    group = request.args.get("group", "alpha")
    return {
        "q": request.args.get("q", "").strip(),
        "category_id": request.args.get("category", type=int),
        "sort": request.args.get("sort", "name"),
        "needs_review": request.args.get("needs_review") == "1",
        "favorites": request.args.get("favorites") == "1",
        "needs_split": request.args.get("needs_split") == "1",
        "display": display if display in VALID_DISPLAYS else "card",
        "group": group if group in VALID_GROUPS else "alpha",
    }


def _fetch_sections(db, params):
    search_kwargs = {
        k: params[k] for k in ("q", "category_id", "sort", "needs_review", "favorites", "needs_split")
    }

    # Grouping needs rows already in section order, so it replaces relevance
    # ranking for searches; recency sorts have no meaningful sections.
    grouping_active = params["sort"] == "name"
    if grouping_active:
        search_kwargs["rank_by_relevance"] = False
        if params["group"] == "category":
            search_kwargs["sort"] = "category"

    recipes = search_recipes(db, **search_kwargs)
    group_by = params["group"] if grouping_active else None
    return group_recipes(recipes, group_by)


def _results_context(db, params):
    sections = _fetch_sections(db, params)
    shown = sum(len(rows) for _, rows in sections)
    total = db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    return {
        "sections": sections,
        "params": params,
        "count_text": f"Showing {shown} of {total} recipes",
    }


@bp.route("/")
def index():
    db = get_db()
    params = _search_params()
    return render_template(
        "index.html", categories=list_categories(db), **_results_context(db, params)
    )


@bp.route("/api/search")
def api_search():
    db = get_db()
    params = _search_params()
    return render_template("partials/_recipe_results.html", **_results_context(db, params))
