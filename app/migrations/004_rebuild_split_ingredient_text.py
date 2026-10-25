"""Split fields became the only source of truth for a split ingredient's
text. Rebuild raw_text for existing split rows (some had been edited so the
split no longer matched the original typed line) and refresh search."""
from app.ingredients.scaling import format_ingredient_line
from app.models.recipes import _category_name, _sync_fts


def migrate(conn):
    conn.execute("UPDATE ingredients SET unit = NULL WHERE unit = ''")

    rows = conn.execute(
        "SELECT id, recipe_id, quantity, quantity_max, unit, item FROM ingredients "
        "WHERE kind = 'item' AND is_split = 1 AND quantity IS NOT NULL"
    ).fetchall()
    touched = set()
    for r in rows:
        text = format_ingredient_line(r["quantity"], r["quantity_max"], r["unit"], r["item"])
        conn.execute("UPDATE ingredients SET raw_text = ? WHERE id = ?", (text, r["id"]))
        touched.add(r["recipe_id"])

    for recipe_id in touched:
        recipe = conn.execute(
            "SELECT title, category_id, contributor FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        if recipe is None:
            continue
        ingredients = conn.execute(
            "SELECT raw_text, kind FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,)
        ).fetchall()
        _sync_fts(
            conn, recipe_id, recipe["title"], _category_name(conn, recipe["category_id"]),
            recipe["contributor"], ingredients,
        )
