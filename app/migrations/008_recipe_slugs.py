"""Readable recipe addresses (/brownies instead of /recipes/84). Existing
recipes get slugs oldest first, so the original keeps the plain name and
later copies get -2, -3, ..."""
from app.slugs import assign_slug


def migrate(conn):
    conn.execute("ALTER TABLE recipes ADD COLUMN slug TEXT")
    conn.execute("CREATE UNIQUE INDEX idx_recipes_slug ON recipes(slug)")
    conn.execute(
        """CREATE TABLE recipe_slugs (
               slug TEXT PRIMARY KEY,
               recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE
           )"""
    )
    conn.execute("CREATE INDEX idx_recipe_slugs_recipe ON recipe_slugs(recipe_id)")
    for recipe_id, title in conn.execute("SELECT id, title FROM recipes ORDER BY id").fetchall():
        assign_slug(conn, recipe_id, title)
