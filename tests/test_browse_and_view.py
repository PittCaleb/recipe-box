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


# --- Display style and grouping ---

def _seed_two_categories(db):
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Breads', 0)")
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Desserts', 1)")
    db.commit()
    breads = db.execute("SELECT id FROM categories WHERE name='Breads'").fetchone()["id"]
    desserts = db.execute("SELECT id FROM categories WHERE name='Desserts'").fetchone()["id"]
    _make_recipe(db, title="Zucchini Bread", category_id=breads)
    _make_recipe(db, title="Apple Cake", category_id=desserts)
    _make_recipe(db, title="Banana Bread", category_id=breads)
    _make_recipe(db, title="Loose Recipe")


def _headings(html, cls):
    import re
    return re.findall(rf'<h2 class="{cls}">([^<]+)</h2>', html.decode())


def test_default_view_is_cards_grouped_by_letter(client, db):
    _seed_two_categories(db)
    resp = client.get("/api/search")
    assert b"recipe-card-title" in resp.data
    assert b"recipe-text-list" not in resp.data
    assert _headings(resp.data, "card-section-heading") == ["A", "B", "L", "Z"]


def test_text_view_grouped_by_letter(client, db):
    _seed_two_categories(db)
    resp = client.get("/api/search?display=text&group=alpha")
    assert b"recipe-text-list" in resp.data
    assert b"recipe-card-title" not in resp.data
    assert _headings(resp.data, "text-list-heading") == ["A", "B", "L", "Z"]


def test_group_by_category_orders_sections_and_titles(client, db):
    _seed_two_categories(db)
    resp = client.get("/api/search?display=text&group=category")
    assert _headings(resp.data, "text-list-heading") == ["Breads", "Desserts", "Uncategorized"]
    html = resp.data.decode()
    assert html.index("Banana Bread") < html.index("Zucchini Bread") < html.index("Apple Cake")


def test_search_keeps_display_style_and_category_headings(client, db):
    _seed_two_categories(db)
    resp = client.get("/api/search?q=bread&display=text&group=category")
    assert b"recipe-text-list" in resp.data
    assert _headings(resp.data, "text-list-heading") == ["Breads"]
    assert b"Apple Cake" not in resp.data
    html = resp.data.decode()
    assert html.index("Banana Bread") < html.index("Zucchini Bread")


def test_search_keeps_letter_headings(client, db):
    _seed_two_categories(db)
    resp = client.get("/api/search?q=bread")
    assert _headings(resp.data, "card-section-heading") == ["B", "Z"]


def test_index_count_is_in_controls_bar(client, db):
    _seed_two_categories(db)
    resp = client.get("/?q=bread")
    assert b'id="results-count" aria-live="polite">Showing 2 of 4 recipes<' in resp.data


def test_recency_sort_disables_grouping(client, db):
    _seed_two_categories(db)
    resp = client.get("/api/search?sort=recent_added&group=alpha")
    assert _headings(resp.data, "card-section-heading") == []
    assert resp.data.count(b"recipe-card-title") == 4


def test_invalid_display_and_group_fall_back_to_defaults(client, db):
    _seed_two_categories(db)
    resp = client.get("/api/search?display=bogus&group=bogus")
    assert b"recipe-card-title" in resp.data
    assert _headings(resp.data, "card-section-heading") == ["A", "B", "L", "Z"]


def test_index_page_renders_view_toggles(client, db):
    _make_recipe(db, title="Anything")
    resp = client.get("/?display=text&group=category")
    assert b'data-pill-group="display"' in resp.data
    assert b'id="display-input" value="text"' in resp.data
    assert b'id="group-input" value="category"' in resp.data
    assert b"recipe-text-list" in resp.data


def test_category_grouping_follows_admin_sort_order(client, db):
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Zebra Dishes', 0)")
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Apple Dishes', 1)")
    db.commit()
    z = db.execute("SELECT id FROM categories WHERE name='Zebra Dishes'").fetchone()["id"]
    a = db.execute("SELECT id FROM categories WHERE name='Apple Dishes'").fetchone()["id"]
    _make_recipe(db, title="One", category_id=a)
    _make_recipe(db, title="Two", category_id=z)
    resp = client.get("/api/search?group=category")
    assert _headings(resp.data, "card-section-heading") == ["Zebra Dishes", "Apple Dishes"]


def test_results_count_reflects_filter(client, db):
    _seed_two_categories(db)
    assert b"Showing 4 of 4 recipes" in client.get("/").data
    assert b"Showing 2 of 4 recipes" in client.get("/api/search?q=bread").data
    assert b"Showing 0 of 4 recipes" in client.get("/api/search?q=nonexistentxyz").data


def test_non_letter_titles_group_under_hash(client, db):
    _make_recipe(db, title="7-Layer Dip")
    _make_recipe(db, title="Apple Pie")
    resp = client.get("/api/search")
    assert _headings(resp.data, "card-section-heading") == ["#", "A"]


def test_user_menu_links_present(client, db):
    resp = client.get("/")
    for path in (b"/recipes/new", b"/admin/import/", b"/admin/cookbook", b"/admin/categories",
                 b"/admin/needs-review", b"/admin/export"):
        assert path in resp.data


def test_needs_split_filter(client, db):
    unsplit = _make_recipe(db, title="Old Card")
    seed_ingredient(db, unsplit, 0, "1 1/2 c. sugar")
    done = _make_recipe(db, title="All Split")
    seed_ingredient(db, done, 0, "2 cups flour", is_split=1, quantity=2, unit="cup", item="flour")
    seed_ingredient(db, done, 1, "salt to taste", no_scale=1)
    seed_ingredient(db, done, 2, "For the glaze", kind="heading")
    _make_recipe(db, title="No Ingredients")

    resp = client.get("/api/search?needs_split=1")
    assert b"Old Card" in resp.data
    assert b"All Split" not in resp.data
    assert b"No Ingredients" not in resp.data
    assert b"Showing 1 of 3 recipes" in resp.data

    assert b"Old Card" in client.get("/api/search?needs_split=1&q=old").data
    assert b"Old Card" not in client.get("/api/search?needs_split=1&q=split").data
    assert b'name="needs_split"' in client.get("/").data


def test_needs_split_filter_empty_when_everything_is_split(client, db):
    rid = _make_recipe(db, title="Tidy")
    seed_ingredient(db, rid, 0, "2 cups flour", is_split=1, quantity=2, unit="cup", item="flour")
    assert b"Showing 0 of 1 recipes" in client.get("/api/search?needs_split=1").data
