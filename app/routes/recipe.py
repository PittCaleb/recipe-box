from flask import Blueprint, abort, redirect, render_template, request, url_for

from app import get_db
from app.ingredients.scaling import DEFAULT_MULTIPLIER, MULTIPLIER_LABELS, MULTIPLIER_STOPS, scale_ingredient_line
from app.models.recipes import add_note, delete_note, get_recipe, mark_made_today, set_rating, toggle_favorite
from app.shopping import SHORTCUT_NAME, shopping_entry, shopping_list
from app.users import can_delete_note, current_user, require

bp = Blueprint("recipe", __name__, url_prefix="/recipes")


def _get_or_404(db, recipe_id):
    data = get_recipe(db, recipe_id, current_user()["id"])
    if data is None:
        abort(404)
    return data


@bp.route("/<int:recipe_id>")
def view(recipe_id):
    db = get_db()
    data = _get_or_404(db, recipe_id)

    ingredients = data["ingredients"]
    scaled_variants = None
    if data["scalable"]:
        scaled_variants = [
            [scale_ingredient_line(ing, m) for ing in ingredients]
            for m in MULTIPLIER_STOPS
        ]

    # One set of shopping entries per slider stop, so the list matches the
    # amounts on screen; unscalable recipes only ever show the default.
    stops = MULTIPLIER_STOPS if data["scalable"] else [DEFAULT_MULTIPLIER]
    shopping = {
        "shortcut": SHORTCUT_NAME,
        "stops": [
            {
                "items": [shopping_entry(ing, m) for ing in ingredients],
                "all": shopping_list(ingredients, m),
            }
            for m in stops
        ],
    }
    default_entries = shopping["stops"][stops.index(DEFAULT_MULTIPLIER)]["items"]

    return render_template(
        "recipe_view.html", **data,
        scaled_variants=scaled_variants,
        multiplier_labels=MULTIPLIER_LABELS,
        default_index=MULTIPLIER_STOPS.index(DEFAULT_MULTIPLIER),
        shopping=shopping,
        shoppable=[entry is not None for entry in default_entries],
    )


@bp.route("/<int:recipe_id>/favorite", methods=["POST"])
def favorite(recipe_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    toggle_favorite(db, current_user()["id"], recipe_id)
    return redirect(request.referrer or url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/made", methods=["POST"])
def made(recipe_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    mark_made_today(db, current_user()["id"], recipe_id)
    return redirect(request.referrer or url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/rating", methods=["POST"])
def rating(recipe_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    stars = request.form.get("rating", type=int)
    if stars not in range(1, 6):
        abort(400)
    set_rating(db, current_user()["id"], recipe_id, stars)
    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/notes", methods=["POST"])
def add_note_route(recipe_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    body = request.form.get("body", "")
    add_note(db, recipe_id, body, current_user()["id"])
    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/notes/<int:note_id>/delete", methods=["POST"])
def delete_note_route(recipe_id, note_id):
    db = get_db()
    data = _get_or_404(db, recipe_id)
    note = next((n for n in data["notes"] if n["id"] == note_id), None)
    if note is None:
        abort(404)
    require(can_delete_note(note))
    delete_note(db, recipe_id, note_id)
    return redirect(url_for("recipe.view", recipe_id=recipe_id))
