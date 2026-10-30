"""A read-only JSON API for other apps (the Google TV app). It uses the same
queries as the pages, so both always agree. Who's asking is decided by
load_user like any other request: from home, that's user 1."""

from html.parser import HTMLParser

from flask import Blueprint, abort, jsonify, request, url_for

from app import get_db
from app.models.recipes import SORT_OPTIONS, get_recipe, search_recipes
from app.users import current_user

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.errorhandler(404)
def not_found(exc):
    return jsonify(error="not found"), 404


@bp.route("/categories")
def categories():
    rows = get_db().execute(
        """SELECT c.id, c.name, COUNT(r.id) AS recipe_count
           FROM categories c LEFT JOIN recipes r ON r.category_id = c.id
           GROUP BY c.id ORDER BY c.sort_order, c.name COLLATE NOCASE"""
    ).fetchall()
    return jsonify(categories=[dict(r) for r in rows])


@bp.route("/recipes")
def recipes():
    """All recipes, or those matching ?q=, ?category=<id> and ?favorites=1.
    ?sort= is name (the default), category, recent_made or recent_added. A
    search is ranked best match first unless a sort is given."""
    db = get_db()
    sort = request.args.get("sort")
    if sort is not None and sort not in SORT_OPTIONS:
        abort(400)
    rows = search_recipes(
        db,
        q=request.args.get("q", "").strip(),
        category_id=request.args.get("category", type=int),
        favorites=request.args.get("favorites") == "1",
        sort=sort or "name",
        rank_by_relevance=sort is None,
        user_id=current_user()["id"],
    )
    total = db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    return jsonify(total=total, recipes=[_summary(r) for r in rows])


@bp.route("/recipes/<int:recipe_id>")
def recipe(recipe_id):
    data = get_recipe(get_db(), recipe_id, current_user()["id"])
    if data is None:
        abort(404)
    r = data["recipe"]
    return jsonify({
        **_summary(r),
        "source": r["source"],
        "owner": r["owner_name"],
        "ingredients": [{"kind": i["kind"], "text": i["raw_text"]} for i in data["ingredients"]],
        "steps": instruction_steps(r["instructions_html"]),
        "instructions_html": r["instructions_html"],
        "notes": [
            {"id": n["id"], "body": n["body"], "author": n["author_name"], "created_at": n["created_at"]}
            for n in data["notes"]
        ],
    })


def _summary(r):
    image = r["image_filename"]
    return {
        "id": r["id"],
        "title": r["title"],
        "category": {"id": r["category_id"], "name": r["category_name"]} if r["category_id"] else None,
        "contributor": r["contributor"],
        "servings": r["servings"],
        "prep_time": r["prep_time"],
        "cook_time": r["cook_time"],
        "image_url": url_for("media.image", filename=image, _external=True) if image else None,
        "image_is_placeholder": bool(r["image_is_placeholder"]),
        "favorite": bool(r["favorite"]),
        "rating": r["rating"],
        "last_made": r["last_made"],
        "slug": r["slug"],
        "web_url": url_for("recipe.view", slug=r["slug"], _external=True),
    }


class _StepParser(HTMLParser):
    """Each list item is a step, and so is each paragraph outside a list
    item. <br> line breaks inside one stay as newlines; other whitespace,
    including newlines in the HTML source, collapses to single spaces."""

    def __init__(self):
        super().__init__()
        self.steps = []
        self.current = []
        self.li_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self._finish()
            self.li_depth += 1
        elif tag == "br":
            self.current.append("\n")

    def handle_endtag(self, tag):
        if tag == "li":
            self.li_depth = max(0, self.li_depth - 1)
            self._finish()
        elif tag == "p":
            if self.li_depth:
                self.current.append(" ")
            else:
                self._finish()

    def handle_data(self, data):
        self.current.append(data.replace("\n", " "))

    def _finish(self):
        lines = (" ".join(line.split()) for line in "".join(self.current).split("\n"))
        text = "\n".join(line for line in lines if line)
        if text:
            self.steps.append(text)
        self.current = []


def instruction_steps(html):
    parser = _StepParser()
    parser.feed(html or "")
    parser.close()
    parser._finish()
    return parser.steps
