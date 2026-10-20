from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def _make_recipe(db, **kw):
    rid = seed_recipe(db, **kw)
    sync_fts(
        db, rid, kw.get("title", "Test Recipe"),
        contributor=kw.get("contributor") or "",
        ingredients_text="",
    )
    return rid


def test_index_lists_recipes(client, db):
    _make_recipe(db, title="Apple Pie")
    _make_recipe(db, title="Banana Bread")
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Apple Pie" in resp.data
    assert b"Banana Bread" in resp.data


def test_search_matches_title_prefix(client, db):
    _make_recipe(db, title="Chocolate Cake")
    _make_recipe(db, title="Banana Bread")
    resp = client.get("/api/search?q=choc")
    assert b"Chocolate Cake" in resp.data
    assert b"Banana Bread" not in resp.data


def test_search_matches_ingredient_text(client, db):
    rid = seed_recipe(db, title="Mystery Dish")
    seed_ingredient(db, rid, 0, "2 cups flour")
    sync_fts(db, rid, "Mystery Dish", ingredients_text="2 cups flour")
    resp = client.get("/api/search?q=flour")
    assert b"Mystery Dish" in resp.data


def test_favorites_filter(client, db):
    _make_recipe(db, title="Fav One", favorite=1)
    _make_recipe(db, title="Not Fav")
    resp = client.get("/api/search?favorites=1")
    assert b"Fav One" in resp.data
    assert b"Not Fav" not in resp.data


def test_needs_review_filter(client, db):
    _make_recipe(db, title="Flagged", needs_review=1)
    _make_recipe(db, title="Clean")
    resp = client.get("/api/search?needs_review=1")
    assert b"Flagged" in resp.data
    assert b"Clean" not in resp.data


def test_recipe_view_shows_core_fields(client, db):
    rid = seed_recipe(
        db, title="Rice Pilaf", contributor="Pat Lee", servings="6 servings",
        instructions_html="<p>Brown the rice.</p>",
    )
    seed_ingredient(db, rid, 0, "1 cup rice")
    sync_fts(db, rid, "Rice Pilaf")
    resp = client.get(f"/recipes/{rid}")
    assert resp.status_code == 200
    assert b"Rice Pilaf" in resp.data
    assert b"Pat Lee" in resp.data
    assert b"1 cup rice" in resp.data
    assert b"Brown the rice." in resp.data


def test_recipe_view_hides_empty_fields(client, db):
    rid = seed_recipe(db, title="Bare Recipe", contributor=None, source=None, servings=None)
    sync_fts(db, rid, "Bare Recipe")
    resp = client.get(f"/recipes/{rid}")
    assert b"Source:" not in resp.data
    assert b"Servings:" not in resp.data


def test_recipe_view_404_for_missing(client, db):
    resp = client.get("/recipes/9999")
    assert resp.status_code == 404


def test_favorite_toggle(client, db):
    rid = _make_recipe(db, title="Toggle Me")
    resp = client.post(f"/recipes/{rid}/favorite", follow_redirects=True)
    assert resp.status_code == 200
    row = db.execute("SELECT favorite FROM recipes WHERE id=?", (rid,)).fetchone()
    assert row["favorite"] == 1
    client.post(f"/recipes/{rid}/favorite")
    row = db.execute("SELECT favorite FROM recipes WHERE id=?", (rid,)).fetchone()
    assert row["favorite"] == 0


def test_mark_made_sets_today(client, db):
    import datetime
    rid = _make_recipe(db, title="Make Me")
    client.post(f"/recipes/{rid}/made")
    row = db.execute("SELECT last_made FROM recipes WHERE id=?", (rid,)).fetchone()
    assert row["last_made"] == datetime.date.today().isoformat()


def test_add_and_delete_note(client, db):
    rid = _make_recipe(db, title="Notable")
    client.post(f"/recipes/{rid}/notes", data={"body": "Used less sugar"})
    notes = db.execute("SELECT * FROM notes WHERE recipe_id=?", (rid,)).fetchall()
    assert len(notes) == 1
    assert notes[0]["body"] == "Used less sugar"

    note_id = notes[0]["id"]
    client.post(f"/recipes/{rid}/notes/{note_id}/delete")
    notes = db.execute("SELECT * FROM notes WHERE recipe_id=?", (rid,)).fetchall()
    assert len(notes) == 0


def test_add_note_ignores_blank_body(client, db):
    rid = _make_recipe(db, title="No Blank Notes")
    client.post(f"/recipes/{rid}/notes", data={"body": "   "})
    notes = db.execute("SELECT * FROM notes WHERE recipe_id=?", (rid,)).fetchall()
    assert len(notes) == 0


def test_category_filter(client, db):
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Desserts', 0)")
    db.commit()
    cat_id = db.execute("SELECT id FROM categories WHERE name='Desserts'").fetchone()["id"]
    _make_recipe(db, title="In Category", category_id=cat_id)
    _make_recipe(db, title="No Category")
    resp = client.get(f"/api/search?category={cat_id}")
    assert b"In Category" in resp.data
    assert b"No Category" not in resp.data
