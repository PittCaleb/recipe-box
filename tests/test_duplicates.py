import pytest

from app import create_app
from app.duplicates import find_duplicate_groups, ingredient_line_key, lines_match, merge_recipes
from tests.conftest import seed_ingredient, seed_recipe, sync_fts

BAKING = ["2 cups flour", "1 cup sugar", "2 eggs", "1 tsp baking powder", "1/2 cup butter", "1 tsp vanilla"]


def _recipe(db, title, ingredients=(), **kw):
    rid = seed_recipe(db, title=title, **kw)
    for pos, text in enumerate(ingredients):
        seed_ingredient(db, rid, pos, text)
    sync_fts(db, rid, title, ingredients_text=" ".join(ingredients))
    return rid


def _note(db, rid, body, created_at="2026-01-01T00:00:00"):
    db.execute("INSERT INTO notes (recipe_id, body, created_at) VALUES (?, ?, ?)", (rid, body, created_at))
    db.commit()


def _notes(db, rid):
    return [r["body"] for r in db.execute("SELECT body FROM notes WHERE recipe_id=? ORDER BY id", (rid,))]


# --- Detection ---

def test_same_title_ignoring_parenthetical_is_grouped(db):
    a = _recipe(db, "Brownies")
    b = _recipe(db, "Brownies (recipes2 version)")
    _recipe(db, "Chicken Soup")
    assert find_duplicate_groups(db) == [[a, b]]


def test_reordered_and_plural_titles_are_grouped(db):
    a = _recipe(db, "Vanilla Pizzelles")
    b = _recipe(db, "Pizzelles, Vanilla (recipes2 version)")
    c = _recipe(db, "Venetians")
    d = _recipe(db, "Venetian")
    assert find_duplicate_groups(db) == [[a, b], [c, d]]


def test_different_titles_need_similar_ingredients(db):
    rice = ["1 cup rice", "1/2 cup slivered almonds", "2 cups chicken broth", "1 onion chopped", "2 tbsp butter"]
    a = _recipe(db, "Rice Pilaf", rice)
    b = _recipe(db, "Nut Rice", rice[:4] + ["1 tsp savory"])
    _recipe(db, "Fried Rice", ["2 cups cooked rice", "2 eggs", "soy sauce", "scallions", "peas"])
    assert find_duplicate_groups(db) == [[a, b]]


def test_shared_baking_staples_alone_are_not_duplicates(db):
    _recipe(db, "Cornbread", BAKING + ["1 cup cornmeal"])
    _recipe(db, "Pizzelles", BAKING + ["anise extract"])
    assert find_duplicate_groups(db) == []


def test_three_copies_form_one_group(db):
    ids = [_recipe(db, t) for t in ("Thumbprint Cookies", "Thumbprint Cookies (Pat Cohen card)",
                                     "Thumbprint Cookies (recipes2 version)")]
    assert find_duplicate_groups(db) == [ids]


def test_dismissed_group_is_not_suggested_again(client, db):
    a = _recipe(db, "Blintzes (J Crozier version)")
    b = _recipe(db, "Blintzes (Bette Galcik version)")
    assert find_duplicate_groups(db) == [[a, b]]
    resp = client.post("/admin/duplicates/dismiss", data={"ids": f"{a},{b}", "group_name": "Blintzes"})
    assert resp.status_code == 302
    assert find_duplicate_groups(db) == []
    assert db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 2


# --- Ingredient line comparison ---

@pytest.mark.parametrize("a, b", [
    ("1 cup ice water", "1 C ice water"),
    ("1 teaspoon salt", "1 tsp. salt"),
    ("1 tablespoon cornstarch", "1 Tbs. cornstarch"),
    ("1 pound Crisco", "1 lb. Crisco"),
    ("2 single eggs; yolks only", "2 egg yolks"),
    ("2 oz baking chocolate (3/8 cup cocoa, 2 T butter)", "2 oz baking chocolate"),
    ("1/2 cup flour", "1/2 C sifted flour"),
    ("2 cup flour; sifted", "2 C sifted all purpose flour"),
    ("1 teaspoon vanilla extract", "1 t vanilla"),
    ("½ cup sugar", "1/2 c sugar"),
])
def test_equivalent_lines_match(a, b):
    assert lines_match(ingredient_line_key(a), ingredient_line_key(b))


@pytest.mark.parametrize("a, b", [
    ("1/3 teaspoon salt", "1/4 t salt"),
    ("1 t baking soda", "1 T baking soda"),
    ("1 stick margarine", "1/4 lb. margarine"),
    ("1 cup sugar", "1 cup flour"),
])
def test_different_lines_do_not_match(a, b):
    assert not lines_match(ingredient_line_key(a), ingredient_line_key(b))


# --- Merge ---

def test_merge_carries_over_history_and_notes(db):
    keep = _recipe(db, "Ladylocks", ["1 pound Crisco"], favorite=0, rating=3, last_made="2025-01-01")
    other = _recipe(db, "Ladylocks (recipes2 version)", ["1/4 pound Crisco"], favorite=1, rating=5,
                    last_made="2026-03-01", image_filename="photo.jpg", contributor="Pat Cohen",
                    source_pdf="recipes2.pdf", source_page=18)
    _note(db, other, "From original card: makes double")
    _note(db, other, "Import review note: Duplicate of \"Ladylocks\" - pick one.")

    merge_recipes(db, keep, [other], new_title="Ladylocks")

    assert db.execute("SELECT COUNT(*) FROM recipes WHERE id=?", (other,)).fetchone()[0] == 0
    row = db.execute("SELECT * FROM recipes WHERE id=?", (keep,)).fetchone()
    assert row["favorite"] == 1
    assert row["rating"] == 5
    assert row["last_made"] == "2026-03-01"
    assert row["image_filename"] == "photo.jpg"
    notes = _notes(db, keep)
    assert "From original card: makes double" in notes
    assert not any("pick one" in n for n in notes)
    assert any("Ladylocks (recipes2 version)" in n and "recipes2.pdf page 18" in n and "Pat Cohen" in n
               for n in notes)


def test_merge_keeps_better_values_already_on_keeper(db):
    keep = _recipe(db, "Spatzle", favorite=1, rating=5, last_made="2026-05-01", image_filename="mine.jpg")
    other = _recipe(db, "Spatzle (recipes2 version)", rating=2, last_made="2024-01-01", image_filename="theirs.jpg")
    orphaned = merge_recipes(db, keep, [other])
    row = db.execute("SELECT * FROM recipes WHERE id=?", (keep,)).fetchone()
    assert (row["favorite"], row["rating"], row["last_made"], row["image_filename"]) == (1, 5, "2026-05-01", "mine.jpg")
    assert ("image", "theirs.jpg") in orphaned


def test_merge_renames_and_updates_search(client, db):
    keep = _recipe(db, "Chicken Soup (Pat Cohen typed)", ["peppercorns"])
    other = _recipe(db, "Chicken Soup")
    merge_recipes(db, keep, [other], new_title="Grandma Chicken Soup")
    assert db.execute("SELECT title FROM recipes WHERE id=?", (keep,)).fetchone()["title"] == "Grandma Chicken Soup"
    resp = client.get("/api/search?q=grandma")
    assert b"Grandma Chicken Soup" in resp.data
    assert b"Showing 1 of 1 recipes" in resp.data


def test_merge_clears_needs_review_only_when_duplicate_was_the_only_issue(db):
    simple = _recipe(db, "Brownies", needs_review=1)
    _note(db, simple, "Import review note: Duplicate of \"Brownies (recipes2 version)\" - pick one.")
    simple_other = _recipe(db, "Brownies (recipes2 version)", needs_review=1)

    tricky = _recipe(db, "Venetians", needs_review=1)
    _note(db, tricky, "Import review note: Salt has a handwritten correction, 1/3 to 1/4.")
    _note(db, tricky, "Import review note: Duplicate copy exists in recipes2.pdf.")
    tricky_other = _recipe(db, "Venetian (recipes2 version)", needs_review=1)

    merge_recipes(db, simple, [simple_other])
    merge_recipes(db, tricky, [tricky_other])

    assert db.execute("SELECT needs_review FROM recipes WHERE id=?", (simple,)).fetchone()[0] == 0
    assert db.execute("SELECT needs_review FROM recipes WHERE id=?", (tricky,)).fetchone()[0] == 1
    tricky_notes = _notes(db, tricky)
    assert any("Salt has a handwritten correction" in n for n in tricky_notes)
    assert not any("Duplicate copy exists" in n for n in tricky_notes)


def test_merge_three_way_with_one_left_out(db):
    a = _recipe(db, "Chocolate Mousse")
    b = _recipe(db, "Chocolate Mousse (typed version)")
    c = _recipe(db, "Chocolate Mousse (recipes2 version)")
    merge_recipes(db, a, [b])
    remaining = {r["id"] for r in db.execute("SELECT id FROM recipes")}
    assert remaining == {a, c}
    assert find_duplicate_groups(db) == [[a, c]]


def test_merge_rejects_missing_recipe(db):
    a = _recipe(db, "Spatzle")
    with pytest.raises(ValueError):
        merge_recipes(db, a, [9999])


# --- Routes ---

def test_index_lists_groups(client, db):
    _recipe(db, "Brownies")
    _recipe(db, "Brownies (recipes2 version)")
    resp = client.get("/admin/duplicates/")
    assert resp.status_code == 200
    assert b"Brownies (recipes2 version)" in resp.data
    assert b"1 group of recipes" in resp.data


def test_compare_highlights_only_real_differences_and_defaults_keeper(client, db):
    plain = _recipe(db, "Ladylocks", ["1 pound Crisco", "1/3 teaspoon salt"])
    copy = _recipe(db, "Ladylocks (recipes2 version)", ["1 lb. Crisco", "1/4 t salt"])
    resp = client.get(f"/admin/duplicates/compare?ids={copy},{plain}")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert html.count('class="differs"') == 2
    assert '<li class="differs">1/3 teaspoon salt</li>' in html
    assert f'value="{plain}" checked' in html
    assert 'id="merged-title" name="title" value="Ladylocks"' in html


def test_compare_404s_on_bad_ids(client, db):
    a = _recipe(db, "Only One")
    assert client.get(f"/admin/duplicates/compare?ids={a}").status_code == 404
    assert client.get(f"/admin/duplicates/compare?ids={a},9999").status_code == 404


def test_merge_route_deletes_orphaned_scan_and_moves_on(client, db, cfg):
    cfg.ensure_data_dirs()
    (cfg.SCANS_DIR / "p007.jpg").write_bytes(b"scan")
    (cfg.SCANS_DIR / "p048.jpg").write_bytes(b"scan")
    keep = _recipe(db, "Brownies", scan_filename="p007.jpg")
    other = _recipe(db, "Brownies (recipes2 version)", scan_filename="p048.jpg")
    nxt_a = _recipe(db, "Spatzle")
    nxt_b = _recipe(db, "Spatzle (recipes2 version)")

    resp = client.post("/admin/duplicates/merge", data={
        "ids": f"{keep},{other}", "keep_id": keep, "merge_ids": [keep, other],
        "title": "Brownies", "group_name": "Brownies",
    })
    assert resp.status_code == 302
    assert f"ids={nxt_a},{nxt_b}" in resp.headers["Location"].replace("%2C", ",")
    assert (cfg.SCANS_DIR / "p007.jpg").exists()
    assert not (cfg.SCANS_DIR / "p048.jpg").exists()


def test_merge_route_requires_something_to_merge(client, db):
    a = _recipe(db, "Brownies")
    b = _recipe(db, "Brownies (recipes2 version)")
    resp = client.post("/admin/duplicates/merge", data={"ids": f"{a},{b}", "keep_id": a, "merge_ids": [a]})
    assert resp.status_code == 302
    assert db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 2


def test_duplicates_require_login_when_password_set(cfg, db):
    cfg.APP_PASSWORD = "sesame"
    client = create_app(cfg).test_client()
    resp = client.get("/admin/duplicates/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
