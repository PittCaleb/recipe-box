from app.export.txt_backup import build_backup_text, html_to_text, parse_backup_text
from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def test_export_route_downloads_txt_file(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Exportable")
    sync_fts(db, rid, "Exportable")
    resp = client.post("/admin/export")
    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    assert b"RECIPE: Exportable" in resp.data
    saved = list(cfg.EXPORTS_DIR.glob("recipes-backup-*.txt"))
    assert len(saved) == 1


def test_html_to_text_paragraphs():
    html = "<p>First.</p><p>Second.</p>"
    assert html_to_text(html) == "First.\n\nSecond."


def test_html_to_text_lists_and_emphasis():
    html = "<p>Mix <strong>well</strong> and <em>fold</em> gently.</p><ul><li>Flour</li><li>Sugar</li></ul>"
    text = html_to_text(html)
    assert "**well**" in text
    assert "*fold*" in text
    assert "- Flour" in text
    assert "- Sugar" in text


def test_html_to_text_ordered_list_numbering():
    html = "<ol><li>First step</li><li>Second step</li><li>Third step</li></ol>"
    text = html_to_text(html)
    assert "1. First step" in text
    assert "2. Second step" in text
    assert "3. Third step" in text


def test_html_to_text_br_within_paragraph():
    html = "<p>Line one.<br>Line two.</p>"
    assert html_to_text(html) == "Line one.\nLine two."


def test_backup_header_has_app_name_timestamp_and_count(db):
    seed_recipe(db, title="Only Recipe")
    text = build_backup_text(db)
    header = text.split("\n\n", 1)[0]
    assert "Recipes" in header
    assert "1 recipes" in header


def test_backup_every_field_present_even_when_empty(db):
    rid = seed_recipe(db, title="Bare Bones")
    text = build_backup_text(db)
    for field in [
        "RECIPE:", "ID:", "CATEGORY:", "CONTRIBUTOR:", "SOURCE:", "SERVINGS:",
        "PREP TIME:", "COOK TIME:", "OWNER:", "PERSONAL:",
        "NEEDS REVIEW:", "IMAGE FILE:", "SCAN FILE:", "ORIGIN:", "CREATED:", "UPDATED:",
    ]:
        assert field in text


def test_backup_sorted_by_category_then_title(db):
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Breads', 0)")
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Desserts', 1)")
    db.commit()
    bread_id = db.execute("SELECT id FROM categories WHERE name='Breads'").fetchone()["id"]
    dessert_id = db.execute("SELECT id FROM categories WHERE name='Desserts'").fetchone()["id"]

    seed_recipe(db, title="Zucchini Bread", category_id=bread_id)
    seed_recipe(db, title="Apple Bread", category_id=bread_id)
    seed_recipe(db, title="Cake", category_id=dessert_id)

    text = build_backup_text(db)
    apple_pos = text.index("RECIPE: Apple Bread")
    zucchini_pos = text.index("RECIPE: Zucchini Bread")
    cake_pos = text.index("RECIPE: Cake")
    assert apple_pos < zucchini_pos < cake_pos


# --- Full round-trip test (required by SPEC.md section 7) ---

def _build_full_recipe(db):
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Desserts – Cakes', 0)")
    db.commit()
    cat_id = db.execute("SELECT id FROM categories WHERE name='Desserts – Cakes'").fetchone()["id"]

    rid = seed_recipe(
        db, title="Grandma's Pound Cake", category_id=cat_id, contributor="Pat Cohen",
        source="Family recipe box", servings="12", cook_time="1 hr 15 min", rating=5,
        favorite=1, last_made="2026-09-14", needs_review=0,
        image_filename="recipe-42-20260914.jpg", scan_filename="recipes2-p007-a.jpg",
        source_pdf="recipes2.pdf", source_page=7,
        instructions_html="<p>Cream butter and sugar.</p><p>Add eggs <strong>one at a time</strong>.</p>",
    )
    seed_ingredient(db, rid, 0, "For the glaze:", kind="heading")
    seed_ingredient(db, rid, 1, "2 cups flour, sifted", is_split=1, quantity=2, unit="cup", item="flour, sifted")
    seed_ingredient(db, rid, 2, "salt to taste", no_scale=1)
    seed_ingredient(db, rid, 3, "3 eggs")
    db.execute(
        "INSERT INTO notes (recipe_id, body, created_at) VALUES (?, 'Used less sugar, still great.', '2026-09-14T18:22:00')",
        (rid,),
    )
    db.commit()
    return rid


def test_round_trip_matches_database(db):
    rid = _build_full_recipe(db)
    text = build_backup_text(db)
    header, recipes = parse_backup_text(text)

    assert "1 recipes" in header
    assert len(recipes) == 1
    parsed = recipes[0]
    f = parsed["fields"]

    row = db.execute("SELECT * FROM recipes WHERE id=?", (rid,)).fetchone()
    cat = db.execute("SELECT name FROM categories WHERE id=?", (row["category_id"],)).fetchone()

    assert f["RECIPE"] == row["title"]
    assert f["ID"] == str(row["id"])
    assert f["CATEGORY"] == cat["name"]
    assert f["CONTRIBUTOR"] == row["contributor"]
    assert f["SOURCE"] == row["source"]
    assert f["SERVINGS"] == row["servings"]
    assert f["PREP TIME"] == (row["prep_time"] or "")
    assert f["COOK TIME"] == row["cook_time"]
    assert f["OWNER"] == "caleb@hail2pitt.org"
    assert f["PERSONAL"] == "caleb@hail2pitt.org (favorite, 5 stars, made 2026-09-14)"
    assert f["NEEDS REVIEW"] == "no"
    assert f["IMAGE FILE"] == row["image_filename"]
    assert f["SCAN FILE"] == row["scan_filename"]
    assert f["ORIGIN"] == f"{row['source_pdf']} page {row['source_page']}"
    assert f["CREATED"] == row["created_at"]
    assert f["UPDATED"] == row["updated_at"]

    db_ingredients = db.execute(
        "SELECT * FROM ingredients WHERE recipe_id=? ORDER BY position", (rid,)
    ).fetchall()
    assert len(parsed["ingredients"]) == len(db_ingredients)

    assert parsed["ingredients"][0]["kind"] == "heading"
    assert parsed["ingredients"][0]["raw_text"] == "For the glaze:"

    split_ing = parsed["ingredients"][1]
    assert split_ing["raw_text"] == "2 cups flour, sifted"
    assert split_ing["split"]["qty"] == "2"
    assert split_ing["split"]["unit"] == "cup"
    assert split_ing["split"]["item"] == "flour, sifted"

    no_scale_ing = parsed["ingredients"][2]
    assert no_scale_ing["raw_text"] == "salt to taste"
    assert no_scale_ing.get("no_scale") is True

    unsplit_ing = parsed["ingredients"][3]
    assert unsplit_ing["raw_text"] == "3 eggs"
    assert "split" not in unsplit_ing
    assert not unsplit_ing.get("no_scale")

    assert "Cream butter and sugar." in parsed["instructions_text"]
    assert "**one at a time**" in parsed["instructions_text"]

    assert len(parsed["notes"]) == 1
    assert parsed["notes"][0]["date"] == "2026-09-14 18:22"
    assert parsed["notes"][0]["body"] == "Used less sugar, still great."


def test_round_trip_multiple_recipes_and_blank_fields(db):
    seed_recipe(db, title="Minimal Recipe")
    _build_full_recipe(db)
    text = build_backup_text(db)
    header, recipes = parse_backup_text(text)
    assert "2 recipes" in header
    assert len(recipes) == 2

    minimal = next(r for r in recipes if r["fields"]["RECIPE"] == "Minimal Recipe")
    assert minimal["fields"]["CATEGORY"] == ""
    assert minimal["fields"]["CONTRIBUTOR"] == ""
    assert minimal["fields"]["PERSONAL"] == ""
    assert minimal["ingredients"] == []
    assert minimal["notes"] == []
