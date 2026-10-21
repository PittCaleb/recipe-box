from flask import Blueprint, abort, redirect, render_template, request, url_for

from app import get_db
from app.ingredients.scaling import DEFAULT_MULTIPLIER, MULTIPLIER_LABELS, MULTIPLIER_STOPS, scale_ingredient_line
from app.models.recipes import add_note, delete_note, get_recipe, mark_made_today, toggle_favorite

bp = Blueprint("recipe", __name__, url_prefix="/recipes")


def _get_or_404(db, recipe_id):
    data = get_recipe(db, recipe_id)
    if data is None:
        abort(404)
    return data


@bp.route("/<int:recipe_id>")
def view(recipe_id):
    db = get_db()
    data = _get_or_404(db, recipe_id)

    scaled_variants = None
    if data["scalable"]:
        scaled_variants = [
            [scale_ingredient_line(ing, m) for ing in data["ingredients"]]
            for m in MULTIPLIER_STOPS
        ]

    return render_template(
        "recipe_view.html", **data,
        scaled_variants=scaled_variants,
        multiplier_labels=MULTIPLIER_LABELS,
        default_index=MULTIPLIER_STOPS.index(DEFAULT_MULTIPLIER),
    )


@bp.route("/<int:recipe_id>/favorite", methods=["POST"])
def favorite(recipe_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    toggle_favorite(db, recipe_id)
    return redirect(request.referrer or url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/made", methods=["POST"])
def made(recipe_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    mark_made_today(db, recipe_id)
    return redirect(request.referrer or url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/notes", methods=["POST"])
def add_note_route(recipe_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    body = request.form.get("body", "")
    add_note(db, recipe_id, body)
    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/notes/<int:note_id>/delete", methods=["POST"])
def delete_note_route(recipe_id, note_id):
    db = get_db()
    _get_or_404(db, recipe_id)
    delete_note(db, recipe_id, note_id)
    return redirect(url_for("recipe.view", recipe_id=recipe_id))
