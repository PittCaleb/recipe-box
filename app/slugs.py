"""Readable recipe addresses: "Grandma's Chili" lives at /grandmas-chili.

Every slug a recipe has ever had stays in recipe_slugs, so a link shared
before a rename still finds the recipe, and no other recipe can take it over.
recipes.slug is the current one."""
import re
import unicodedata

# Top-level paths the app uses or might one day, so no recipe can claim them.
RESERVED = {
    "about", "account", "add", "admin", "api", "categories", "category", "cookbook", "delete", "edit",
    "export", "favicon", "favorites", "help", "home", "import", "index", "ingredients", "list", "login",
    "logout", "media", "new", "print", "profile", "random", "recipe", "recipes", "robots", "search",
    "settings", "share", "shopping", "shopping-list", "static", "tags", "user", "users",
}
MAX_LENGTH = 80


def slugify(title):
    """'Grandma's Chili (Spicy!)' -> 'grandmas-chili-spicy'. Accents are
    dropped, '&' reads as 'and', and a title with nothing usable left
    becomes 'recipe'."""
    text = unicodedata.normalize("NFKD", title or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"['’]", "", text)
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(slug) > MAX_LENGTH:
        slug = slug[:MAX_LENGTH].rsplit("-", 1)[0]
    return slug or "recipe"


def assign_slug(conn, recipe_id, title):
    """Gives the recipe the first free slug for `title` ('brownies',
    'brownies-2', ...) and returns it. A slug this recipe had before counts
    as free, so renaming back reclaims it. Doesn't commit."""
    base = slugify(title)
    n = 1
    while True:
        slug = base if n == 1 else f"{base}-{n}"
        if slug not in RESERVED:
            owner = conn.execute("SELECT recipe_id FROM recipe_slugs WHERE slug = ?", (slug,)).fetchone()
            if owner is None or owner[0] == recipe_id:
                break
        n += 1
    conn.execute("INSERT OR IGNORE INTO recipe_slugs (slug, recipe_id) VALUES (?, ?)", (slug, recipe_id))
    conn.execute("UPDATE recipes SET slug = ? WHERE id = ?", (slug, recipe_id))
    return slug


def find_slug(conn, slug):
    """(recipe id, current slug) for any slug the recipe has had, or None."""
    row = conn.execute(
        "SELECT r.id, r.slug FROM recipe_slugs s JOIN recipes r ON r.id = s.recipe_id WHERE s.slug = ?",
        (slug.lower(),),
    ).fetchone()
    return (row[0], row[1]) if row else None


def current_slug(conn, recipe_id):
    row = conn.execute("SELECT slug FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    return row[0] if row else None
