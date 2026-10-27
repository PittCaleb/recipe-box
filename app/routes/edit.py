from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app import get_db
from app.images import InvalidImage, delete_recipe_image, save_recipe_image
from app.ingredients.parser import parse_amount
from app.ingredients.scaling import format_amount
from app.ingredients.units import UNIT_LABELS
from app.models.categories import list_categories
from app.models.recipes import (
    delete_recipe, get_recipe, save_recipe, set_image_filename, split_guess, update_note,
)
from app.sanitize import sanitize_instructions
from app.users import can_delete_note, can_delete_recipe, can_edit_recipe, current_user, is_admin, require

bp = Blueprint("edit", __name__, url_prefix="/recipes")


UNIT_CHOICES = [
    "tsp", "tbsp", "cup", "fl_oz", "pt", "qt", "gal", "oz", "lb",
    "ml", "l", "g", "kg", "stick", "can", "package", "clove", "pinch", "dash",
]


def _form_rows_from_ingredients(ingredients):
    """Editor rows for saved ingredients. Lines that were never split are
    pre-filled with the parser's best guess and flagged so they get a look
    before saving -- saving turns them into split rows."""
    rows = []
    for ing in ingredients:
        if ing["kind"] == "heading":
            rows.append({"kind": "heading", "heading": ing["raw_text"]})
            continue
        if ing["is_split"] and ing["quantity"] is not None:
            q, q_max, unit, item, guess_from = (
                ing["quantity"], ing["quantity_max"], ing["unit"], ing["item"], None,
            )
        else:
            parsed = split_guess(ing["raw_text"])
            if parsed:
                q, q_max, unit, item = (parsed["quantity"], parsed["quantity_max"],
                                        parsed["unit"], parsed["item"])
            else:
                q, q_max, unit, item = None, None, None, ing["raw_text"]
            guess_from = ing["raw_text"] if q is not None else None
        rows.append({
            "kind": "item",
            "quantity": format_amount(q) if q is not None else "",
            "quantity_max": format_amount(q_max) if q_max else "",
            "unit": unit or "",
            "item": item or "",
            "no_scale": bool(ing["no_scale"]) and q is not None,
            "guess_from": guess_from,
        })
    return rows


def _form_rows_from_request(form):
    def at(name, i):
        values = form.getlist(name)
        return values[i].strip() if i < len(values) else ""

    rows = []
    for i, kind in enumerate(form.getlist("ingredient_kind")):
        if kind == "heading":
            rows.append({"kind": "heading", "heading": at("ingredient_heading", i)})
        else:
            rows.append({
                "kind": "item",
                "quantity": at("ingredient_quantity", i),
                "quantity_max": at("ingredient_quantity_max", i),
                "unit": at("ingredient_unit", i),
                "item": at("ingredient_item", i),
                "no_scale": at("ingredient_no_scale", i) == "1",
                "guess_from": None,
            })
    return rows


def _ingredients_from_rows(rows):
    """Validated ingredient dicts for save_recipe, plus error messages. Every
    item row is split: an amount (and optional unit/range) plus an
    ingredient. A row with no amount ("salt to taste") is saved as just its
    name and never scaled."""
    ingredients, errors = [], []
    for n, row in enumerate(rows, start=1):
        if row["kind"] == "heading":
            if row["heading"]:
                ingredients.append({"kind": "heading", "raw_text": row["heading"]})
            continue

        q_text, max_text, item = row["quantity"], row["quantity_max"], row["item"]
        if not (q_text or max_text or item):
            continue
        q = parse_amount(q_text)
        q_max = parse_amount(max_text)
        unit = row["unit"] if row["unit"] in UNIT_LABELS else None
        label = f"Ingredient {n}" + (f" ({item})" if item else "")

        if q_text and q is None:
            errors.append(f"{label}: “{q_text}” isn't an amount. Use numbers like 2, 1 1/2, or ¾ — or leave it blank if there's no amount.")
            continue
        if max_text and q_max is None:
            errors.append(f"{label}: “{max_text}” isn't an amount.")
            continue
        if q_max is not None and (q is None or q_max <= q):
            errors.append(f"{label}: the “to” amount must be larger than the first amount.")
            continue
        if not item:
            errors.append(f"Ingredient {n}: add what the ingredient is.")
            continue

        if q is None:
            ingredients.append({
                "kind": "item", "raw_text": item, "is_split": 0, "no_scale": 1,
                "quantity": None, "quantity_max": None, "unit": None, "item": None,
            })
        else:
            ingredients.append({
                "kind": "item", "is_split": 1, "no_scale": 1 if row["no_scale"] else 0,
                "quantity": q, "quantity_max": q_max, "unit": unit, "item": item,
            })
    return ingredients, errors


def _editable_notes(notes):
    """Notes the editor may change: their own, or any for an admin."""
    return [n for n in notes if can_delete_note(n)]


def _get_editable_or_404(db, recipe_id):
    data = get_recipe(db, recipe_id, current_user()["id"])
    if data is None:
        abort(404)
    require(can_edit_recipe(data["recipe"]))
    return data


def _render_form(recipe, rows, notes, values=None, status=200):
    """`values` fills the fields; when a save fails it's what was submitted,
    so nothing typed is lost. `recipe` is only the saved recipe, if any (for
    its id, photo, and scan)."""
    if values is None:
        values = dict(recipe) if recipe else {}
    return render_template(
        "edit.html", recipe=recipe, rows=rows, notes=notes, values=values,
        categories=list_categories(get_db()), unit_choices=UNIT_CHOICES,
        unit_labels=UNIT_LABELS,
    ), status


def _notes_with_submitted_edits(notes, form):
    return [
        {**dict(n), "body": form.get(f"note_body_{n['id']}", n["body"])}
        for n in notes
    ]


def _parse_fields(form, needs_review=0):
    """`needs_review` is kept as given unless an admin is saving: only admins
    see that checkbox."""
    category_id = form.get("category_id", "").strip()
    return {
        "title": form.get("title", "").strip(),
        "category_id": int(category_id) if category_id else None,
        "contributor": form.get("contributor", "").strip() or None,
        "source": form.get("source", "").strip() or None,
        "servings": form.get("servings", "").strip() or None,
        "prep_time": form.get("prep_time", "").strip() or None,
        "cook_time": form.get("cook_time", "").strip() or None,
        "instructions_html": sanitize_instructions(form.get("instructions_html", "")),
        "needs_review": (1 if form.get("needs_review") == "1" else 0) if is_admin() else needs_review,
    }


@bp.route("/new", methods=["GET"])
def new():
    blank = {"kind": "item", "quantity": "", "quantity_max": "", "unit": "", "item": "",
             "no_scale": False, "guess_from": None}
    return _render_form(None, [dict(blank) for _ in range(3)], [])


@bp.route("/<int:recipe_id>/edit", methods=["GET"])
def edit(recipe_id):
    data = _get_editable_or_404(get_db(), recipe_id)
    return _render_form(
        data["recipe"], _form_rows_from_ingredients(data["ingredients"]), _editable_notes(data["notes"]),
    )


def _validate(form, needs_review=0):
    """Parsed fields + ingredients, or a list of problems to show."""
    fields = _parse_fields(form, needs_review)
    rows = _form_rows_from_request(form)
    ingredients, errors = _ingredients_from_rows(rows)
    if not fields["title"]:
        errors.insert(0, "Title is required.")
    return fields, rows, ingredients, errors


@bp.route("/new", methods=["POST"])
def create():
    db = get_db()
    fields, rows, ingredients, errors = _validate(request.form)
    if errors:
        for e in errors:
            flash(e)
        return _render_form(None, rows, [], values=fields, status=400)

    recipe_id = save_recipe(db, None, {**fields, "owner_id": current_user()["id"]}, ingredients)

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
    data = _get_editable_or_404(db, recipe_id)
    notes = _editable_notes(data["notes"])

    fields, rows, ingredients, errors = _validate(request.form, data["recipe"]["needs_review"])
    if errors:
        for e in errors:
            flash(e)
        return _render_form(
            data["recipe"], rows, _notes_with_submitted_edits(notes, request.form),
            values=fields, status=400,
        )

    save_recipe(db, recipe_id, fields, ingredients)

    for note in notes:
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
    """Anyone may add or replace a photo."""
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
    data = _get_editable_or_404(db, recipe_id)
    cfg = _cfg()
    if data["recipe"]["image_filename"]:
        delete_recipe_image(cfg.IMAGES_DIR, data["recipe"]["image_filename"])
        set_image_filename(db, recipe_id, None)
    return redirect(url_for("recipe.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/delete", methods=["POST"])
def delete(recipe_id):
    require(can_delete_recipe())
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
