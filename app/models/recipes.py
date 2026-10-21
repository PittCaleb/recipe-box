import re
from datetime import date


def list_categories(conn):
    return conn.execute(
        "SELECT id, name, sort_order FROM categories ORDER BY sort_order, name COLLATE NOCASE"
    ).fetchall()


def _fts_match_query(q):
    tokens = re.findall(r"\w+", q)
    if not tokens:
        return None
    return " ".join(f'"{t}"*' for t in tokens)


SORT_OPTIONS = {
    "name": "r.title COLLATE NOCASE ASC",
    "recent_made": "r.last_made IS NULL, r.last_made DESC",
    "recent_added": "r.created_at DESC",
    "category": "c.id IS NULL, c.sort_order, c.name COLLATE NOCASE, r.title COLLATE NOCASE ASC",
}


def search_recipes(conn, q="", category_id=None, sort="name", needs_review=False, favorites=False,
                   rank_by_relevance=True):
    sort_sql = SORT_OPTIONS.get(sort, SORT_OPTIONS["name"])
    where = []
    params = []

    match = _fts_match_query(q) if q else None
    if match:
        base = """
            SELECT r.*, c.name AS category_name
            FROM recipes_fts f
            JOIN recipes r ON r.id = f.rowid
            LEFT JOIN categories c ON c.id = r.category_id
            WHERE recipes_fts MATCH ?
        """
        params.append(match)
    else:
        base = """
            SELECT r.*, c.name AS category_name
            FROM recipes r
            LEFT JOIN categories c ON c.id = r.category_id
            WHERE 1=1
        """

    if category_id:
        where.append("r.category_id = ?")
        params.append(category_id)
    if needs_review:
        where.append("r.needs_review = 1")
    if favorites:
        where.append("r.favorite = 1")

    sql = base
    if where:
        sql += " AND " + " AND ".join(where)

    if match and rank_by_relevance:
        sql += f" ORDER BY bm25(recipes_fts, 10.0, 3.0, 3.0, 1.0), {sort_sql}"
    else:
        sql += f" ORDER BY {sort_sql}"

    return conn.execute(sql, params).fetchall()


def group_recipes(rows, group_by):
    """Splits already-sorted rows into (label, [rows]) sections. `group_by`
    is "alpha" (rows must already be name-sorted) or "category" (rows must
    already be category-then-name sorted); any other value returns a single
    unlabeled section."""
    if group_by not in ("alpha", "category"):
        return [(None, rows)] if rows else []

    sections = []
    current_label = None
    current_rows = []

    for row in rows:
        if group_by == "alpha":
            first = (row["title"] or "").strip()[:1].upper()
            label = first if first.isalpha() else "#"
        else:
            label = row["category_name"] or "Uncategorized"

        if label != current_label:
            if current_rows:
                sections.append((current_label, current_rows))
            current_label = label
            current_rows = []
        current_rows.append(row)

    if current_rows:
        sections.append((current_label, current_rows))

    return sections


def get_recipe(conn, recipe_id):
    row = conn.execute(
        """SELECT r.*, c.name AS category_name
           FROM recipes r LEFT JOIN categories c ON c.id = r.category_id
           WHERE r.id = ?""",
        (recipe_id,),
    ).fetchone()
    if row is None:
        return None
    ingredients = conn.execute(
        "SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,)
    ).fetchall()
    notes = conn.execute(
        "SELECT * FROM notes WHERE recipe_id = ? ORDER BY created_at DESC, id DESC", (recipe_id,)
    ).fetchall()
    return {
        "recipe": row,
        "ingredients": ingredients,
        "notes": notes,
        "scalable": is_scalable(ingredients),
    }


def is_scalable(ingredients):
    items = [i for i in ingredients if i["kind"] == "item"]
    if not items:
        return False
    any_split = False
    for i in items:
        if i["no_scale"]:
            continue
        if i["is_split"] and i["quantity"] is not None:
            any_split = True
            continue
        return False
    return any_split


def toggle_favorite(conn, recipe_id):
    with conn:
        conn.execute(
            "UPDATE recipes SET favorite = CASE favorite WHEN 1 THEN 0 ELSE 1 END, updated_at = ? WHERE id = ?",
            (_now(), recipe_id),
        )


def mark_made_today(conn, recipe_id):
    today = date.today().isoformat()
    with conn:
        conn.execute(
            "UPDATE recipes SET last_made = ?, updated_at = ? WHERE id = ?",
            (today, _now(), recipe_id),
        )
    return today


def add_note(conn, recipe_id, body):
    body = body.strip()
    if not body:
        return None
    now = _now()
    with conn:
        cur = conn.execute(
            "INSERT INTO notes (recipe_id, body, created_at) VALUES (?, ?, ?)",
            (recipe_id, body, now),
        )
        conn.execute("UPDATE recipes SET updated_at = ? WHERE id = ?", (now, recipe_id))
    return cur.lastrowid


def delete_note(conn, recipe_id, note_id):
    with conn:
        conn.execute("DELETE FROM notes WHERE id = ? AND recipe_id = ?", (note_id, recipe_id))


def update_note(conn, recipe_id, note_id, body):
    body = body.strip()
    if not body:
        return
    with conn:
        conn.execute(
            "UPDATE notes SET body = ? WHERE id = ? AND recipe_id = ?", (body, note_id, recipe_id)
        )


def _sync_fts(conn, recipe_id, title, category_name, contributor, ingredients):
    ingredients_text = " ".join(i["raw_text"] for i in ingredients if i["kind"] == "item")
    conn.execute("DELETE FROM recipes_fts WHERE rowid = ?", (recipe_id,))
    conn.execute(
        "INSERT INTO recipes_fts (rowid, title, category_name, contributor, ingredients_text) "
        "VALUES (?, ?, ?, ?, ?)",
        (recipe_id, title, category_name or "", contributor or "", ingredients_text),
    )


def _category_name(conn, category_id):
    if not category_id:
        return ""
    row = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    return row["name"] if row else ""


def save_recipe(conn, recipe_id, fields, ingredients):
    """Create (recipe_id is None) or update a recipe plus its full ingredient list,
    in one transaction. `ingredients` is a list of dicts with keys matching the
    ingredients table (kind, raw_text, no_scale, is_split, quantity, quantity_max,
    unit, item)."""
    now = _now()
    category_name = _category_name(conn, fields.get("category_id"))

    with conn:
        if recipe_id is None:
            cur = conn.execute(
                """INSERT INTO recipes
                   (title, category_id, contributor, source, servings, prep_time, cook_time,
                    instructions_html, needs_review, favorite, rating, last_made,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fields["title"], fields.get("category_id"), fields.get("contributor"),
                    fields.get("source"), fields.get("servings"), fields.get("prep_time"),
                    fields.get("cook_time"), fields["instructions_html"],
                    fields.get("needs_review", 0), fields.get("favorite", 0),
                    fields.get("rating"), fields.get("last_made"), now, now,
                ),
            )
            recipe_id = cur.lastrowid
        else:
            conn.execute(
                """UPDATE recipes SET
                   title=?, category_id=?, contributor=?, source=?, servings=?, prep_time=?,
                   cook_time=?, instructions_html=?, needs_review=?, favorite=?, rating=?,
                   last_made=?, updated_at=?
                   WHERE id=?""",
                (
                    fields["title"], fields.get("category_id"), fields.get("contributor"),
                    fields.get("source"), fields.get("servings"), fields.get("prep_time"),
                    fields.get("cook_time"), fields["instructions_html"],
                    fields.get("needs_review", 0), fields.get("favorite", 0),
                    fields.get("rating"), fields.get("last_made"), now, recipe_id,
                ),
            )
            conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))

        for pos, ing in enumerate(ingredients):
            conn.execute(
                """INSERT INTO ingredients
                   (recipe_id, position, kind, raw_text, is_split, quantity, quantity_max,
                    unit, item, no_scale)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    recipe_id, pos, ing["kind"], ing["raw_text"],
                    ing.get("is_split", 0), ing.get("quantity"), ing.get("quantity_max"),
                    ing.get("unit"), ing.get("item"), ing.get("no_scale", 0),
                ),
            )

        fresh_ingredients = conn.execute(
            "SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,)
        ).fetchall()
        _sync_fts(conn, recipe_id, fields["title"], category_name, fields.get("contributor"), fresh_ingredients)

    return recipe_id


def delete_recipe(conn, recipe_id):
    """Deletes the recipe row (cascades ingredients/notes) and returns the
    image/scan filenames so the caller can remove those files too."""
    row = conn.execute(
        "SELECT image_filename, scan_filename FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    with conn:
        conn.execute("DELETE FROM recipes_fts WHERE rowid = ?", (recipe_id,))
        conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    return row


def set_image_filename(conn, recipe_id, filename):
    with conn:
        conn.execute(
            "UPDATE recipes SET image_filename = ?, updated_at = ? WHERE id = ?",
            (filename, _now(), recipe_id),
        )


def _now():
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")
