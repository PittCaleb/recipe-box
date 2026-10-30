"""Finds likely-duplicate recipes and merges a group of them into one."""
import re
from itertools import combinations

from app.models.recipes import _category_name, _now, _sync_fts
from app.slugs import assign_slug

TITLE_STOPWORDS = {
    "a", "an", "and", "the", "of", "with", "recipe", "recipes", "my", "s",
    "version", "copy", "card", "typed", "detailed", "duplicate",
}
INGREDIENT_STOPWORDS = {
    "a", "an", "and", "or", "the", "of", "to", "for", "in", "into", "with",
    "cup", "cups", "c", "tablespoon", "tablespoons", "tbsp", "tbs", "t",
    "teaspoon", "teaspoons", "tsp", "pound", "pounds", "lb", "lbs", "oz",
    "ounce", "ounces", "pint", "quart", "pkg", "package", "can", "stick",
    "sticks", "large", "small", "medium", "chopped", "sliced", "diced",
    "melted", "softened", "beaten", "sifted", "fresh", "about", "plus",
    "divided", "optional", "taste", "each", "pinch", "dash",
}

# Tuned against the Phase 1 import, whose review notes name every known
# duplicate. Ingredients alone are never enough: unrelated baked goods
# (cornbread vs. pizzelles) share flour/sugar/eggs and score up to ~0.73.
TITLE_MATCH = 0.6
TITLE_AND_INGREDIENTS = (0.3, 0.5)
MIN_INGREDIENT_WORDS = 4

IMPORT_NOTE_PREFIX = "Import review note:"


def _stem(word):
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _words(text, stopwords):
    return {
        _stem(w) for w in re.findall(r"[a-z]+", (text or "").lower())
        if w not in stopwords and len(w) > 1
    }


def title_words(title):
    # Parentheticals are almost always import disambiguators like
    # "(recipes2 version)" rather than part of the dish name.
    return _words(re.sub(r"\([^)]*\)", " ", title or ""), TITLE_STOPWORDS)


def clean_title(title):
    return re.sub(r"\s*\([^)]*\)\s*", " ", title or "").strip() or (title or "")


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _similarity(t1, i1, t2, i2):
    title_sim = _jaccard(t1, t2)
    enough = len(i1) >= MIN_INGREDIENT_WORDS and len(i2) >= MIN_INGREDIENT_WORDS
    ing_sim = _jaccard(i1, i2) if enough else 0.0
    if title_sim >= TITLE_MATCH:
        return True, title_sim, ing_sim
    if title_sim >= TITLE_AND_INGREDIENTS[0] and ing_sim >= TITLE_AND_INGREDIENTS[1]:
        return True, title_sim, ing_sim
    return False, title_sim, ing_sim


UNIT_ALIASES = {
    "cup": "cup", "cups": "cup", "c": "cup",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp", "tsps": "tsp",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "tbs": "tbsp", "tbl": "tbsp",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "stick": "stick", "sticks": "stick",
    "pint": "pint", "pints": "pint", "quart": "quart", "quarts": "quart",
    "pkg": "pkg", "package": "pkg", "packages": "pkg",
}
LINE_FILLER = INGREDIENT_STOPWORDS | {"single", "only", "extract", "pure", "all", "purpose"}
FRACTIONS = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3", "⅛": "1/8"}


def ingredient_line_key(text):
    """(quantity, unit, words) for loose comparison of two ingredient lines
    written in different styles: "1 C. sifted flour" ~ "1 cup flour"."""
    text = re.sub(r"\([^)]*\)", " ", text or "")
    for sym, frac in FRACTIONS.items():
        text = text.replace(sym, f" {frac} ")
    tokens = re.findall(r"\d+/\d+|\d+(?:\.\d+)?|[A-Za-z]+", text)

    qty = []
    while tokens and re.match(r"\d", tokens[0]):
        qty.append(tokens.pop(0))
    unit = ""
    if tokens:
        first = tokens[0]
        # Recipe-card shorthand: lowercase "t" is a teaspoon, capital "T" a tablespoon.
        if first == "t":
            unit = "tsp"
        elif first == "T":
            unit = "tbsp"
        else:
            unit = UNIT_ALIASES.get(first.lower(), "")
        if unit:
            tokens.pop(0)
    words = {_stem(t.lower()) for t in tokens if t.lower() not in LINE_FILLER and len(t) > 1}
    return " ".join(qty), unit, words


def lines_match(a, b):
    qa, ua, wa = a
    qb, ub, wb = b
    if qa != qb or ua != ub:
        return False
    if not wa and not wb:
        return True
    return _jaccard(wa, wb) >= 0.5


def _dismissed_pairs(conn):
    return {
        (r["recipe_a"], r["recipe_b"])
        for r in conn.execute("SELECT recipe_a, recipe_b FROM duplicate_dismissals")
    }


def find_duplicate_groups(conn):
    """Returns a list of groups, each a list of recipe ids (sorted), of
    recipes that look like copies of each other. Pairs the owner marked as
    "not duplicates" are never linked."""
    recipes = conn.execute("SELECT id, title FROM recipes ORDER BY id").fetchall()
    ingredient_text = {}
    for row in conn.execute(
        "SELECT recipe_id, group_concat(raw_text, ' ') AS txt FROM ingredients "
        "WHERE kind = 'item' GROUP BY recipe_id"
    ):
        ingredient_text[row["recipe_id"]] = row["txt"]

    info = {
        r["id"]: (title_words(r["title"]), _words(ingredient_text.get(r["id"]), INGREDIENT_STOPWORDS))
        for r in recipes
    }
    dismissed = _dismissed_pairs(conn)

    parent = {rid: rid for rid in info}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in combinations(sorted(info), 2):
        if (a, b) in dismissed:
            continue
        match, _, _ = _similarity(*info[a], *info[b])
        if match:
            parent[find(a)] = find(b)

    groups = {}
    for rid in info:
        groups.setdefault(find(rid), []).append(rid)
    result = [sorted(g) for g in groups.values() if len(g) > 1]
    titles = {r["id"]: r["title"] for r in recipes}
    result.sort(key=lambda g: clean_title(titles[g[0]]).lower())
    return result


def dismiss_group(conn, recipe_ids):
    with conn:
        for a, b in combinations(sorted(set(recipe_ids)), 2):
            conn.execute(
                "INSERT OR IGNORE INTO duplicate_dismissals (recipe_a, recipe_b, created_at) "
                "VALUES (?, ?, ?)",
                (a, b, _now()),
            )


def merge_recipes(conn, keep_id, merge_ids, new_title=None):
    """Folds each recipe in `merge_ids` into `keep_id`, then deletes them.

    Carried over to the kept recipe: notes (except the importer's own
    review notes, which only described the duplication being resolved),
    each person's favorite, most recent last-made date, and higher rating,
    and the photo if the kept recipe has none. Each removed copy also leaves a note
    saying where it came from, so the provenance isn't lost.

    Returns the image/scan filenames of the deleted rows that are no longer
    referenced, for the caller to remove from disk."""
    merge_ids = [m for m in dict.fromkeys(merge_ids) if m != keep_id]
    keep = conn.execute("SELECT * FROM recipes WHERE id = ?", (keep_id,)).fetchone()
    if keep is None:
        raise ValueError(f"recipe {keep_id} not found")
    others = [
        conn.execute("SELECT * FROM recipes WHERE id = ?", (m,)).fetchone() for m in merge_ids
    ]
    if any(o is None for o in others):
        raise ValueError("one of the recipes to merge no longer exists")

    image, placeholder = keep["image_filename"], keep["image_is_placeholder"]
    orphaned_files = []
    now = _now()

    with conn:
        for o in others:
            conn.execute(
                """INSERT INTO user_recipes (user_id, recipe_id, favorite, rating, last_made)
                   SELECT user_id, ?, favorite, rating, last_made FROM user_recipes WHERE recipe_id = ?
                   ON CONFLICT (user_id, recipe_id) DO UPDATE SET
                     favorite = max(favorite, excluded.favorite),
                     rating = NULLIF(max(COALESCE(rating, 0), COALESCE(excluded.rating, 0)), 0),
                     last_made = NULLIF(max(COALESCE(last_made, ''), COALESCE(excluded.last_made, '')), '')""",
                (keep_id, o["id"]),
            )
            # A real photo wins over a drawn placeholder.
            if o["image_filename"] and (not image or (placeholder and not o["image_is_placeholder"])):
                if image:
                    orphaned_files.append(("image", image))
                image, placeholder = o["image_filename"], o["image_is_placeholder"]
            elif o["image_filename"]:
                orphaned_files.append(("image", o["image_filename"]))
            if o["scan_filename"]:
                orphaned_files.append(("scan", o["scan_filename"]))

            conn.execute(
                "UPDATE notes SET recipe_id = ? WHERE recipe_id = ? AND body NOT LIKE ?",
                (keep_id, o["id"], IMPORT_NOTE_PREFIX + "%"),
            )
            origin = ""
            if o["source_pdf"]:
                origin = f" ({o['source_pdf']} page {o['source_page']})"
            contributor = f", credited to {o['contributor']}" if o["contributor"] else ""
            conn.execute(
                "INSERT INTO notes (recipe_id, body, created_at, author_id) VALUES (?, ?, ?, ?)",
                (keep_id, f"Merged in a duplicate copy: \"{o['title']}\"{origin}{contributor}.", now,
                 keep["owner_id"]),
            )
            # Links to the removed copy now lead to the kept one.
            conn.execute("UPDATE recipe_slugs SET recipe_id = ? WHERE recipe_id = ?", (keep_id, o["id"]))
            conn.execute("DELETE FROM recipes_fts WHERE rowid = ?", (o["id"],))
            conn.execute("DELETE FROM recipes WHERE id = ?", (o["id"],))

        title = (new_title or "").strip() or keep["title"]
        conn.execute(
            "UPDATE recipes SET title = ?, image_filename = ?, image_is_placeholder = ?, updated_at = ? WHERE id = ?",
            (title, image, placeholder, now, keep_id),
        )
        if title != keep["title"]:
            assign_slug(conn, keep_id, title)

        # The importer's "duplicate of X" notes on the keeper are resolved now.
        conn.execute(
            "DELETE FROM notes WHERE recipe_id = ? AND body LIKE ? AND lower(body) LIKE '%duplicate%'",
            (keep_id, IMPORT_NOTE_PREFIX + "%"),
        )
        remaining_import_notes = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE recipe_id = ? AND body LIKE ?",
            (keep_id, IMPORT_NOTE_PREFIX + "%"),
        ).fetchone()[0]
        if remaining_import_notes == 0:
            conn.execute("UPDATE recipes SET needs_review = 0 WHERE id = ?", (keep_id,))

        ingredients = conn.execute(
            "SELECT raw_text, kind FROM ingredients WHERE recipe_id = ? ORDER BY position",
            (keep_id,),
        ).fetchall()
        _sync_fts(
            conn, keep_id, title, _category_name(conn, keep["category_id"]),
            keep["contributor"], ingredients,
        )

    still_used = set()
    for kind, name in orphaned_files:
        col = "image_filename" if kind == "image" else "scan_filename"
        if conn.execute(f"SELECT 1 FROM recipes WHERE {col} = ?", (name,)).fetchone():
            still_used.add((kind, name))
    return [f for f in orphaned_files if f not in still_used]
