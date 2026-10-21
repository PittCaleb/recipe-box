import io

from PIL import Image

from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def _png_bytes(size=(50, 50)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=(200, 50, 50)).save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_new_recipe_form_renders(client):
    resp = client.get("/recipes/new")
    assert resp.status_code == 200
    assert b"New recipe" in resp.data


def test_create_recipe_minimal(client, db):
    resp = client.post(
        "/recipes/new",
        data={
            "title": "Brand New Dish",
            "category_id": "",
            "ingredient_kind": ["item"],
            "ingredient_text": ["1 cup flour"],
            "ingredient_no_scale": ["0"],
            "instructions_html": "<p>Mix it.</p>",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302
    row = db.execute("SELECT * FROM recipes WHERE title='Brand New Dish'").fetchone()
    assert row is not None
    assert row["instructions_html"] == "<p>Mix it.</p>"
    ing = db.execute("SELECT * FROM ingredients WHERE recipe_id=?", (row["id"],)).fetchall()
    assert len(ing) == 1
    assert ing[0]["raw_text"] == "1 cup flour"


def test_create_recipe_requires_title(client, db):
    resp = client.post("/recipes/new", data={"title": "   "})
    assert resp.status_code == 400
    assert db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 0


def test_create_recipe_sanitizes_instructions(client, db):
    client.post(
        "/recipes/new",
        data={
            "title": "Sanitize Me",
            "instructions_html": '<p onclick="alert(1)">Hi</p><script>bad()</script><img src=x>',
        },
    )
    row = db.execute("SELECT * FROM recipes WHERE title='Sanitize Me'").fetchone()
    assert "<script>" not in row["instructions_html"]
    assert "onclick" not in row["instructions_html"]
    assert "<img" not in row["instructions_html"]
    assert "<p>Hi</p>" in row["instructions_html"]


def test_edit_form_prefills_existing_recipe(client, db):
    rid = seed_recipe(db, title="Existing Dish", contributor="Pat")
    seed_ingredient(db, rid, 0, "2 eggs")
    sync_fts(db, rid, "Existing Dish")
    resp = client.get(f"/recipes/{rid}/edit")
    assert resp.status_code == 200
    assert b"Existing Dish" in resp.data
    assert b"2 eggs" in resp.data


def test_update_recipe_replaces_ingredients(client, db):
    rid = seed_recipe(db, title="Updatable")
    seed_ingredient(db, rid, 0, "old ingredient")
    sync_fts(db, rid, "Updatable")

    client.post(
        f"/recipes/{rid}",
        data={
            "title": "Updated Title",
            "ingredient_kind": ["heading", "item"],
            "ingredient_text": ["For the topping", "3 cups sugar"],
            "ingredient_no_scale": ["0", "0"],
            "instructions_html": "<p>New steps.</p>",
        },
    )
    row = db.execute("SELECT * FROM recipes WHERE id=?", (rid,)).fetchone()
    assert row["title"] == "Updated Title"
    ing = db.execute("SELECT * FROM ingredients WHERE recipe_id=? ORDER BY position", (rid,)).fetchall()
    assert [i["raw_text"] for i in ing] == ["For the topping", "3 cups sugar"]
    assert ing[0]["kind"] == "heading"


def test_update_recipe_search_index_follows_title_change(client, db):
    rid = seed_recipe(db, title="Original Name")
    sync_fts(db, rid, "Original Name")
    client.post(f"/recipes/{rid}", data={"title": "Renamed Dish", "instructions_html": "<p>x</p>"})
    resp = client.get("/api/search?q=Renamed")
    assert b"Renamed Dish" in resp.data
    resp2 = client.get("/api/search?q=Original")
    assert b"Renamed Dish" not in resp2.data


def test_recipe_view_shows_delete_button_when_authenticated(client, db):
    rid = seed_recipe(db, title="Deletable From View")
    sync_fts(db, rid, "Deletable From View")
    resp = client.get(f"/recipes/{rid}")
    assert f'/recipes/{rid}/delete'.encode() in resp.data
    assert b'aria-label="Delete recipe"' in resp.data


def test_delete_recipe_removes_row_and_cascades(client, db):
    rid = seed_recipe(db, title="Doomed")
    seed_ingredient(db, rid, 0, "something")
    sync_fts(db, rid, "Doomed")
    db.execute("INSERT INTO notes (recipe_id, body, created_at) VALUES (?, 'n', '2026-01-01')", (rid,))
    db.commit()

    resp = client.post(f"/recipes/{rid}/delete")
    assert resp.status_code == 302
    assert db.execute("SELECT COUNT(*) FROM recipes WHERE id=?", (rid,)).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM ingredients WHERE recipe_id=?", (rid,)).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM notes WHERE recipe_id=?", (rid,)).fetchone()[0] == 0
    assert client.get("/api/search?q=Doomed").data.count(b"recipe-card-title") == 0


def test_delete_recipe_removes_image_files(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="HasImage", image_filename="recipe-99-x.jpg")
    sync_fts(db, rid, "HasImage")
    (cfg.IMAGES_DIR / "recipe-99-x.jpg").write_bytes(b"fake")
    (cfg.IMAGES_DIR / "recipe-99-x-thumb.jpg").write_bytes(b"fake")

    client.post(f"/recipes/{rid}/delete")
    assert not (cfg.IMAGES_DIR / "recipe-99-x.jpg").exists()
    assert not (cfg.IMAGES_DIR / "recipe-99-x-thumb.jpg").exists()


def test_image_upload_creates_full_and_thumbnail(client, db, cfg):
    rid = seed_recipe(db, title="Needs Photo")
    sync_fts(db, rid, "Needs Photo")

    resp = client.post(
        f"/recipes/{rid}/image",
        data={"image": (_png_bytes(), "photo.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302
    row = db.execute("SELECT image_filename FROM recipes WHERE id=?", (rid,)).fetchone()
    assert row["image_filename"] is not None
    assert (cfg.IMAGES_DIR / row["image_filename"]).exists()
    from app.images import thumb_filename
    assert (cfg.IMAGES_DIR / thumb_filename(row["image_filename"])).exists()


def test_image_upload_resizes_large_image(client, db, cfg):
    rid = seed_recipe(db, title="Big Photo")
    sync_fts(db, rid, "Big Photo")
    resp = client.post(
        f"/recipes/{rid}/image",
        data={"image": (_png_bytes(size=(3000, 2000)), "big.png")},
        content_type="multipart/form-data",
    )
    row = db.execute("SELECT image_filename FROM recipes WHERE id=?", (rid,)).fetchone()
    with Image.open(cfg.IMAGES_DIR / row["image_filename"]) as im:
        assert max(im.size) <= 1600


def test_remove_image(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Remove Photo", image_filename="recipe-5-y.jpg")
    sync_fts(db, rid, "Remove Photo")
    (cfg.IMAGES_DIR / "recipe-5-y.jpg").write_bytes(b"fake")
    (cfg.IMAGES_DIR / "recipe-5-y-thumb.jpg").write_bytes(b"fake")

    client.post(f"/recipes/{rid}/image/delete")
    row = db.execute("SELECT image_filename FROM recipes WHERE id=?", (rid,)).fetchone()
    assert row["image_filename"] is None
    assert not (cfg.IMAGES_DIR / "recipe-5-y.jpg").exists()


# --- Categories admin ---

def test_add_rename_delete_category(client, db):
    client.post("/admin/categories/add", data={"name": "Soups"})
    cat = db.execute("SELECT * FROM categories WHERE name='Soups'").fetchone()
    assert cat is not None

    client.post(f"/admin/categories/{cat['id']}/rename", data={"name": "Soups & Stews"})
    renamed = db.execute("SELECT name FROM categories WHERE id=?", (cat["id"],)).fetchone()
    assert renamed["name"] == "Soups & Stews"

    rid = seed_recipe(db, title="Bisque", category_id=cat["id"])
    sync_fts(db, rid, "Bisque")
    client.post(f"/admin/categories/{cat['id']}/delete")
    assert db.execute("SELECT COUNT(*) FROM categories WHERE id=?", (cat["id"],)).fetchone()[0] == 0
    row = db.execute("SELECT category_id FROM recipes WHERE id=?", (rid,)).fetchone()
    assert row["category_id"] is None


def test_category_reorder(client, db):
    client.post("/admin/categories/add", data={"name": "A"})
    client.post("/admin/categories/add", data={"name": "B"})
    a = db.execute("SELECT * FROM categories WHERE name='A'").fetchone()
    b = db.execute("SELECT * FROM categories WHERE name='B'").fetchone()
    assert a["sort_order"] < b["sort_order"]

    client.post(f"/admin/categories/{b['id']}/move", data={"direction": "up"})
    a2 = db.execute("SELECT * FROM categories WHERE name='A'").fetchone()
    b2 = db.execute("SELECT * FROM categories WHERE name='B'").fetchone()
    assert b2["sort_order"] < a2["sort_order"]


def test_needs_review_queue_lists_flagged_only(client, db):
    seed_recipe(db, title="Flagged One", needs_review=1)
    r2 = seed_recipe(db, title="Clean One", needs_review=0)
    sync_fts(db, r2, "Clean One")
    resp = client.get("/admin/needs-review")
    assert b"Flagged One" in resp.data
    assert b"Clean One" not in resp.data


def test_notes_edited_via_edit_form(client, db):
    rid = seed_recipe(db, title="With Note")
    sync_fts(db, rid, "With Note")
    cur = db.execute(
        "INSERT INTO notes (recipe_id, body, created_at) VALUES (?, 'old body', '2026-01-01')", (rid,)
    )
    db.commit()
    note_id = cur.lastrowid

    client.post(
        f"/recipes/{rid}",
        data={"title": "With Note", "instructions_html": "<p>x</p>", f"note_body_{note_id}": "new body"},
    )
    row = db.execute("SELECT body FROM notes WHERE id=?", (note_id,)).fetchone()
    assert row["body"] == "new body"
