from datetime import date

import weasyprint
from flask import render_template


def gather_cookbook_data(conn, category_ids):
    categories = conn.execute(
        "SELECT * FROM categories WHERE id IN ({}) ORDER BY sort_order, name COLLATE NOCASE".format(
            ",".join("?" for _ in category_ids)
        ),
        category_ids,
    ).fetchall() if category_ids else []

    sections = []
    for cat in categories:
        recipes = conn.execute(
            "SELECT * FROM recipes WHERE category_id = ? ORDER BY title COLLATE NOCASE",
            (cat["id"],),
        ).fetchall()
        if not recipes:
            continue
        recipe_entries = []
        for r in recipes:
            ingredients = conn.execute(
                "SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY position", (r["id"],)
            ).fetchall()
            notes = conn.execute(
                "SELECT * FROM notes WHERE recipe_id = ? ORDER BY created_at, id", (r["id"],)
            ).fetchall()
            recipe_entries.append({"recipe": r, "ingredients": ingredients, "notes": notes})
        sections.append({"category": cat, "recipes": recipe_entries})

    return sections


def render_cookbook_pdf(conn, cfg, category_ids, cover_title, include_images, include_notes, output_path):
    sections = gather_cookbook_data(conn, category_ids)

    image_paths = {}
    if include_images:
        for section in sections:
            for entry in section["recipes"]:
                filename = entry["recipe"]["image_filename"]
                if filename:
                    path = cfg.IMAGES_DIR / filename
                    if path.exists():
                        image_paths[entry["recipe"]["id"]] = str(path)

    html = render_template(
        "print/cookbook.html",
        cover_title=cover_title,
        cover_date=date.today().strftime("%B %-d, %Y"),
        sections=sections,
        include_images=include_images,
        include_notes=include_notes,
        image_paths=image_paths,
    )
    weasyprint.HTML(string=html).write_pdf(str(output_path))
    return output_path
