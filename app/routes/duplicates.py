from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app import get_db
from app.duplicates import (
    clean_title, dismiss_group, find_duplicate_groups, ingredient_line_key, lines_match, merge_recipes,
)
from app.images import delete_recipe_image

bp = Blueprint("duplicates", __name__, url_prefix="/admin/duplicates")


def _cfg():
    return current_app.config["RECIPES_CONFIG"]


def _parse_ids(raw):
    ids = []
    for part in (raw or "").split(","):
        if part.strip().isdigit():
            ids.append(int(part))
    return list(dict.fromkeys(ids))


def _ids_param(ids):
    return ",".join(str(i) for i in ids)


def _group_names(db, groups):
    titles = {r["id"]: r["title"] for r in db.execute("SELECT id, title FROM recipes")}
    return [clean_title(titles[g[0]]).lower() for g in groups]


def _redirect_to_next(after_name):
    """Goes to the first group that sorts after the one just handled, so
    groups the owner skipped earlier don't come straight back."""
    db = get_db()
    groups = find_duplicate_groups(db)
    if not groups:
        flash("No more likely duplicates.")
        return redirect(url_for("duplicates.index"))
    names = _group_names(db, groups)
    after = (after_name or "").lower()
    target = next((g for g, n in zip(groups, names) if n > after), groups[0])
    return redirect(url_for("duplicates.compare", ids=_ids_param(target)))


def _default_keeper(recipes):
    # Prefer the copy whose title has no import disambiguator, then the one
    # with a photo, then the one with the most ingredient lines.
    def score(r):
        return (
            "(" not in r["title"],
            bool(r["image_filename"]),
            len(r["ingredients"]),
        )
    return max(recipes, key=score)["id"]


@bp.route("/")
def index():
    db = get_db()
    groups = find_duplicate_groups(db)
    titles = {r["id"]: r["title"] for r in db.execute("SELECT id, title FROM recipes")}
    rows = [
        {"ids": _ids_param(g), "titles": [titles[i] for i in g], "name": clean_title(titles[g[0]])}
        for g in groups
    ]
    return render_template("admin/duplicates.html", groups=rows)


@bp.route("/compare")
def compare():
    db = get_db()
    ids = _parse_ids(request.args.get("ids"))
    if len(ids) < 2:
        abort(404)

    recipes = []
    for rid in ids:
        row = db.execute(
            "SELECT r.*, c.name AS category_name FROM recipes r "
            "LEFT JOIN categories c ON c.id = r.category_id WHERE r.id = ?",
            (rid,),
        ).fetchone()
        if row is None:
            abort(404)
        recipe = dict(row)
        recipe["ingredients"] = db.execute(
            "SELECT kind, raw_text FROM ingredients WHERE recipe_id = ? ORDER BY position", (rid,)
        ).fetchall()
        recipe["notes"] = db.execute(
            "SELECT body, created_at FROM notes WHERE recipe_id = ? ORDER BY created_at, id", (rid,)
        ).fetchall()
        recipe["clean_title"] = clean_title(recipe["title"])
        recipes.append(recipe)

    # Mark ingredient lines with no equivalent in some other copy, so real
    # differences (quantity, unit, or a different ingredient) jump out while
    # "1 C." vs "1 cup" style differences don't.
    line_keys = [
        [ingredient_line_key(i["raw_text"]) for i in r["ingredients"] if i["kind"] == "item"]
        for r in recipes
    ]
    for idx, recipe in enumerate(recipes):
        others = [keys for j, keys in enumerate(line_keys) if j != idx]
        rows = []
        for i in recipe["ingredients"]:
            differs = False
            if i["kind"] == "item":
                key = ingredient_line_key(i["raw_text"])
                differs = any(not any(lines_match(key, k) for k in keys) for keys in others)
            rows.append({"kind": i["kind"], "text": i["raw_text"], "differs": differs})
        recipe["ingredient_rows"] = rows

    groups = find_duplicate_groups(db)
    group_name = clean_title(recipes[0]["title"])
    next_ids = None
    if groups:
        names = _group_names(db, groups)
        later = [g for g, n in zip(groups, names) if n > group_name.lower() and g != sorted(ids)]
        candidate = later[0] if later else groups[0]
        if candidate != sorted(ids):
            next_ids = _ids_param(candidate)

    return render_template(
        "admin/duplicates_compare.html",
        recipes=recipes,
        keep_id=_default_keeper(recipes),
        ids=_ids_param(ids),
        group_name=group_name,
        remaining=len(groups),
        next_ids=next_ids,
    )


@bp.route("/merge", methods=["POST"])
def merge():
    db = get_db()
    keep_id = request.form.get("keep_id", type=int)
    merge_ids = [int(m) for m in request.form.getlist("merge_ids") if m.isdigit()]
    merge_ids = [m for m in merge_ids if m != keep_id]
    if not keep_id or not merge_ids:
        flash("Pick a recipe to keep and at least one other copy to merge into it.")
        return redirect(url_for("duplicates.compare", ids=request.form.get("ids", "")))

    try:
        orphaned = merge_recipes(db, keep_id, merge_ids, new_title=request.form.get("title"))
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("duplicates.index"))

    cfg = _cfg()
    for kind, name in orphaned:
        if kind == "image":
            delete_recipe_image(cfg.IMAGES_DIR, name)
        else:
            path = cfg.SCANS_DIR / name
            if path.exists():
                path.unlink()

    title = db.execute("SELECT title FROM recipes WHERE id = ?", (keep_id,)).fetchone()["title"]
    copies = "copy" if len(merge_ids) == 1 else "copies"
    flash(f"Merged {len(merge_ids)} {copies} into “{title}”.")
    return _redirect_to_next(request.form.get("group_name"))


@bp.route("/dismiss", methods=["POST"])
def dismiss():
    ids = _parse_ids(request.form.get("ids"))
    if len(ids) >= 2:
        dismiss_group(get_db(), ids)
        flash("Marked as not duplicates — they won't be suggested together again.")
    return _redirect_to_next(request.form.get("group_name"))
