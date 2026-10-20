"""Load data/import/seed.json into the SQLite database.

Refuses to run if `recipes` already has rows, unless --force is given
(which wipes and reloads). This protects edits made after import.

Usage: python -m importer.load_seed [--force]
"""
import argparse
import json
from datetime import datetime

from app.db import get_connection, run_migrations
from config import config


def load(force=False):
    run_migrations(config.DB_PATH)
    conn = get_connection(config.DB_PATH)

    existing = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    if existing and not force:
        raise SystemExit(
            f"recipes table already has {existing} rows. Pass --force to wipe and reload."
        )

    seed = json.loads((config.IMPORT_DIR / "seed.json").read_text())
    recipes = seed["recipes"]

    now = datetime.now().isoformat(timespec="seconds")

    with conn:
        if force:
            conn.execute("DELETE FROM notes")
            conn.execute("DELETE FROM ingredients")
            conn.execute("DELETE FROM recipes")
            conn.execute("DELETE FROM recipes_fts")

        # categories: insert distinct proposed_category values, preserving first-seen order
        cat_names = []
        for r in recipes:
            name = r["proposed_category"]
            if name not in cat_names:
                cat_names.append(name)
        cat_ids = {}
        for i, name in enumerate(cat_names):
            cur = conn.execute(
                "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
                (name, i),
            )
            cat_ids[name] = cur.lastrowid

        per_pdf_counts = {}
        needs_review_list = []

        for r in recipes:
            category_id = cat_ids[r["proposed_category"]]
            notes_text = list(r.get("notes") or [])
            review_note = r.get("review_note") or ""
            if review_note:
                notes_text.append(f"Import review note: {review_note}")

            cur = conn.execute(
                """INSERT INTO recipes
                   (title, category_id, contributor, source, servings, prep_time, cook_time,
                    instructions_html, scan_filename, source_pdf, source_page,
                    needs_review, favorite, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (
                    r["title"], category_id, r["contributor"] or None, r["source"] or None,
                    r["servings"] or None, r["prep_time"] or None, r["cook_time"] or None,
                    r["instructions_html"], r["scan_filename"], r["source_pdf"], r["source_page"],
                    r["needs_review"], now, now,
                ),
            )
            recipe_id = cur.lastrowid

            for pos, ing in enumerate(r["ingredients"]):
                conn.execute(
                    """INSERT INTO ingredients (recipe_id, position, kind, raw_text, no_scale)
                       VALUES (?, ?, ?, ?, ?)""",
                    (recipe_id, pos, ing["kind"], ing["raw_text"], 1 if ing.get("no_scale") else 0),
                )

            for note_body in notes_text:
                conn.execute(
                    "INSERT INTO notes (recipe_id, body, created_at) VALUES (?, ?, ?)",
                    (recipe_id, note_body, now),
                )

            ingredients_text = " ".join(i["raw_text"] for i in r["ingredients"])
            conn.execute(
                """INSERT INTO recipes_fts (rowid, title, category_name, contributor, ingredients_text)
                   VALUES (?, ?, ?, ?, ?)""",
                (recipe_id, r["title"], r["proposed_category"], r["contributor"] or "", ingredients_text),
            )

            per_pdf_counts[r["source_pdf"]] = per_pdf_counts.get(r["source_pdf"], 0) + 1
            if r["needs_review"]:
                needs_review_list.append((r["title"], r["source_pdf"], r["source_page"]))

    conn.close()

    print(f"Loaded {len(recipes)} recipes into {config.DB_PATH}")
    for pdf, count in per_pdf_counts.items():
        print(f"  {pdf}: {count}")
    print(f"\nNeeds review: {len(needs_review_list)}")
    for title, pdf, page in needs_review_list:
        print(f"  - {title} ({pdf} p{page})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    load(force=args.force)


if __name__ == "__main__":
    main()
