from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from app import get_db
from app.images import InvalidImage, delete_recipe_image, save_recipe_image
from app.ingredients.parser import parse_ingredient
from app.models.categories import list_categories
from app.models.recipes import delete_recipe, get_recipe, save_recipe, set_image_filename, update_note
from app.sanitize import sanitize_instructions

bp = Blueprint("edit", __name__, url_prefix="/recipes")


def _parse_ingredients(form):
    kinds = form.getlist("ingredient_kind")
    texts = form.getlist("ingredient_text")
    no_scales = form.getlist("ingredient_no_scale")
    is_splits = form.getlist("ingredient_is_split")
    quantities = form.getlist("ingredient_quantity")
    quantity_maxes = form.getlist("ingredient_quantity_max")
    units = form.getlist("ingredient_unit")
    items = form.getlist("ingredient_item")

    def _at(lst, i, default=""):
        return lst[i] if i < len(lst) else default

    ingredients = []
    for i in range(len(texts)):
        kind = _at(kinds, i, "item")
        text = _at(texts, i)
        no_scale = _at(no_scales, i)
        is_split = _at(is_splits, i)
        quantity = _at(quantities, i)
        quantity_max = _at(quantity_maxes, i)
        unit = _at(units, i)
        item = _at(items, i)
        text = text.strip()
        if not text:
            continue
        ingredients.append({
            "kind": kind if kind in ("item", "heading") else "item",
            "raw_text": text,
            "no_scale": 1 if no_scale == "1" else 0,
            "is_split": 1 if is_split == "1" and quantity else 0,
            "quantity": float(quantity) if is_split == "1" and quantity else None,
            "quantity_max": float(quantity_max) if is_split == "1" and quantity_max else None,
            "unit": unit or None if is_split == "1" else None,
            "item": item or None if is_split == "1" else None,
        })
    return ingredients


@bp.route("/parse-ingredient")
def parse_ingredient_api():
    text = request.args.get("text", "")
    return jsonify(parse_ingredient(text))


def _parse_fields(form):
    category_id = form.get("category_id", "").strip()
    rating = form.get("rating", "").strip()
    last_made = form.get("last_made", "").strip()
    return {
        "title": form.get("title", "").strip(),
        "category_id": int(category_id) if category_id else None,
        "contributor": form.get("contributor", "").strip() or None,
        "source": form.get("source", "").strip() or None,
        "servings": form.get("servings", "").strip() or None,
        "prep_time": form.get("prep_time", "").strip() or None,
        "cook_time": form.get("cook_time", "").strip() or None,
        "instructions_html": sanitize_instructions(form.get("instructions_html", "")),
        "needs_review": 1 if form.get("needs_review") == "1" else 0,
        "favorite": 1 if form.get("favorite") == "1" else 0,
        "rating": int(rating) if rating else None,
        "last_made": last_made or None,
    }


@bp.route("/new", methods=["GET"])
def new():
    db = get_db()
    categories = list_categories(db)
    return render_template("edit.html", recipe=None, ingredients=[], notes=[], categories=categories)


@bp.route("/<int:recipe_id>/edit", methods=["GET"])
def edit(recipe_id):
    db = get_db()
    data = get_recipe(db, recipe_id)
    if data is None:
        abort(404)
    categories = list_categories(db)
    return render_template(
        "edit.html", recipe=data["recipe"], ingredients=data["ingredients"],
        notes=data["notes"], categories=categories,
    )


@bp.route("/new", methods=["POST"])
def create():
    db = get_db()
    fields = _parse_fields(request.form)
    if not fields["title"]:
        flash("Title is required.")
        categories = list_categories(db)
        return render_template("edit.html", recipe=None, ingredients=[], notes=[], categories=categories), 400

    ingredients = _parse_ingredients(request.form)
    recipe_id = save_recipe(db, None, fields, ingredients)

    image_file = request.files.get("image")
    if image_file and image_file.filename:
        cfg = _cfg()
        try:
            filename = save_recipe_image(image_file, cfg.IMAGES_DIR, recipe_id)
            set_image_filename(db, recipe_id, filename)
        except InvalidImage as exc:
            flash(str(exc))

    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>", methods=["POST"])
def update(recipe_id):
    db = get_db()
    data = get_recipe(db, recipe_id)
    if data is None:
        abort(404)

    fields = _parse_fields(request.form)
    if not fields["title"]:
        flash("Title is required.")
        categories = list_categories(db)
        return render_template(
            "edit.html", recipe=data["recipe"], ingredients=data["ingredients"],
            notes=data["notes"], categories=categories,
        ), 400

    ingredients = _parse_ingredients(request.form)
    save_recipe(db, recipe_id, fields, ingredients)

    for note in data["notes"]:
        key = f"note_body_{note['id']}"
        if key in request.form:
            update_note(db, recipe_id, note["id"], request.form[key])

    cfg = _cfg()
    if request.form.get("remove_image") == "1" and data["recipe"]["image_filename"]:
        delete_recipe_image(cfg.IMAGES_DIR, data["recipe"]["image_filename"])
        set_image_filename(db, recipe_id, None)

    image_file = request.files.get("image")
    if image_file and image_file.filename:
        if data["recipe"]["image_filename"]:
            delete_recipe_image(cfg.IMAGES_DIR, data["recipe"]["image_filename"])
        try:
            filename = save_recipe_image(image_file, cfg.IMAGES_DIR, recipe_id)
            set_image_filename(db, recipe_id, filename)
        except InvalidImage as exc:
            flash(str(exc))

    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/image", methods=["POST"])
def upload_image(recipe_id):
    db = get_db()
    data = get_recipe(db, recipe_id)
    if data is None:
        abort(404)
    cfg = _cfg()

    image_file = request.files.get("image")
    if image_file and image_file.filename:
        if data["recipe"]["image_filename"]:
            delete_recipe_image(cfg.IMAGES_DIR, data["recipe"]["image_filename"])
        try:
            filename = save_recipe_image(image_file, cfg.IMAGES_DIR, recipe_id)
            set_image_filename(db, recipe_id, filename)
        except InvalidImage as exc:
            flash(str(exc))

    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/image/delete", methods=["POST"])
def remove_image(recipe_id):
    db = get_db()
    data = get_recipe(db, recipe_id)
    if data is None:
        abort(404)
    cfg = _cfg()
    if data["recipe"]["image_filename"]:
        delete_recipe_image(cfg.IMAGES_DIR, data["recipe"]["image_filename"])
        set_image_filename(db, recipe_id, None)
    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/delete", methods=["POST"])
def delete(recipe_id):
    db = get_db()
    row = delete_recipe(db, recipe_id)
    if row is None:
        abort(404)
    cfg = _cfg()
    if row["image_filename"]:
        delete_recipe_image(cfg.IMAGES_DIR, row["image_filename"])
    if row["scan_filename"]:
        scan_path = cfg.SCANS_DIR / row["scan_filename"]
        if scan_path.exists():
            scan_path.unlink()
    return redirect(url_for("browse.index"))


def _cfg():
    from flask import current_app
    return current_app.config["RECIPES_CONFIG"]
