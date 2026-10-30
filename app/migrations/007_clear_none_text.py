"""Until 2026-10-26 the edit form filled blank fields with the word "None",
so saving a recipe stored that text (shown as "Servings: None", and
searchable as a contributor). Blank them again and refresh search for any
recipe whose contributor changed."""
from app.models.recipes import _category_name, _sync_fts

FIELDS = ("contributor", "source", "servings", "prep_time", "cook_time")


def migrate(conn):
    affected = [
        r["id"] for r in conn.execute("SELECT id FROM recipes WHERE contributor = 'None'").fetchall()
    ]
    for field in FIELDS:
        conn.execute(f"UPDATE recipes SET {field} = NULL WHERE {field} = 'None'")

    for recipe_id in affected:
        recipe = conn.execute(
            "SELECT title, category_id, contributor FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        ingredients = conn.execute(
            "SELECT raw_text, kind FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,)
        ).fetchall()
        _sync_fts(
            conn, recipe_id, recipe["title"], _category_name(conn, recipe["category_id"]),
            recipe["contributor"], ingredients,
        )
