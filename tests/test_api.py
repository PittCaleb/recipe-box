from app.routes.api import instruction_steps
from tests.conftest import seed_ingredient, seed_personal, seed_recipe, sync_fts


def _make_recipe(db, **kw):
    rid = seed_recipe(db, **kw)
    sync_fts(db, rid, kw.get("title", "Test Recipe"))
    return rid


def _category(db, name, sort_order=0):
    cur = db.execute("INSERT INTO categories (name, sort_order) VALUES (?, ?)", (name, sort_order))
    db.commit()
    return cur.lastrowid


def _titles(resp):
    return [r["title"] for r in resp.get_json()["recipes"]]


# --- Recipe list ---

def test_lists_every_recipe_by_name(client, db):
    _make_recipe(db, title="Banana Bread")
    _make_recipe(db, title="Apple Pie")
    resp = client.get("/api/v1/recipes")
    assert resp.status_code == 200
    assert resp.is_json
    assert _titles(resp) == ["Apple Pie", "Banana Bread"]
    assert resp.get_json()["total"] == 2


def test_list_entry_has_what_a_card_needs(client, db):
    cat = _category(db, "Breads")
    rid = _make_recipe(
        db, title="Banana Bread", category_id=cat, contributor="Grandma", servings="1 loaf",
        prep_time="15 min", cook_time="1 hr", image_filename="bread.jpg",
        favorite=1, rating=4, last_made="2026-10-01",
    )
    entry = client.get("/api/v1/recipes").get_json()["recipes"][0]
    assert entry == {
        "id": rid,
        "title": "Banana Bread",
        "category": {"id": cat, "name": "Breads"},
        "contributor": "Grandma",
        "servings": "1 loaf",
        "prep_time": "15 min",
        "cook_time": "1 hr",
        "image_url": "http://localhost/media/images/bread.jpg",
        "image_is_placeholder": False,
        "favorite": True,
        "rating": 4,
        "last_made": "2026-10-01",
        "web_url": f"http://localhost/recipes/{rid}",
    }


def test_recipe_without_picture_or_category(client, db):
    _make_recipe(db, title="Plain")
    entry = client.get("/api/v1/recipes").get_json()["recipes"][0]
    assert entry["image_url"] is None
    assert entry["category"] is None
    assert entry["favorite"] is False
    assert entry["rating"] is None


def test_links_include_the_proxy_prefix(client, db):
    rid = _make_recipe(db, title="Banana Bread", image_filename="bread.jpg")
    resp = client.get("/api/v1/recipes", headers={"X-Forwarded-Prefix": "/recipes", "X-Forwarded-Proto": "https"})
    entry = resp.get_json()["recipes"][0]
    assert entry["image_url"] == "https://localhost/recipes/media/images/bread.jpg"
    assert entry["web_url"] == f"https://localhost/recipes/recipes/{rid}"


def test_search(client, db):
    _make_recipe(db, title="Chocolate Cake")
    _make_recipe(db, title="Banana Bread")
    assert _titles(client.get("/api/v1/recipes?q=choc")) == ["Chocolate Cake"]


def test_search_matches_ingredients(client, db):
    rid = seed_recipe(db, title="Mystery Dish")
    seed_ingredient(db, rid, 0, "2 cups flour")
    sync_fts(db, rid, "Mystery Dish", ingredients_text="2 cups flour")
    assert _titles(client.get("/api/v1/recipes?q=flour")) == ["Mystery Dish"]


def test_search_is_ranked_unless_sorted(client, db):
    # A title match outranks an ingredient match, even when the name sorts later.
    rid = seed_recipe(db, title="Apple Pie")
    sync_fts(db, rid, "Apple Pie", ingredients_text="2 cups lemon zest")
    _make_recipe(db, title="Lemon Bars")
    assert _titles(client.get("/api/v1/recipes?q=lemon")) == ["Lemon Bars", "Apple Pie"]
    assert _titles(client.get("/api/v1/recipes?q=lemon&sort=name")) == ["Apple Pie", "Lemon Bars"]


def test_category_filter(client, db):
    cat = _category(db, "Desserts")
    _make_recipe(db, title="In Category", category_id=cat)
    _make_recipe(db, title="No Category")
    assert _titles(client.get(f"/api/v1/recipes?category={cat}")) == ["In Category"]


def test_favorites_filter(client, db):
    _make_recipe(db, title="Fav", favorite=1)
    _make_recipe(db, title="Not Fav")
    assert _titles(client.get("/api/v1/recipes?favorites=1")) == ["Fav"]


def test_sort_recently_made(client, db):
    _make_recipe(db, title="Old", last_made="2026-01-01")
    _make_recipe(db, title="Never")
    _make_recipe(db, title="New", last_made="2026-10-01")
    assert _titles(client.get("/api/v1/recipes?sort=recent_made")) == ["New", "Old", "Never"]


def test_unknown_sort_is_rejected(client, db):
    assert client.get("/api/v1/recipes?sort=bogus").status_code == 400


def test_favorites_and_ratings_are_the_askers_own(member, db):
    rid = _make_recipe(db, title="Banana Bread", favorite=1, rating=5)  # user 1's
    member.get("/api/v1/recipes")  # creates the member's user row
    member_id = db.execute("SELECT id FROM users WHERE email = 'pat@example.com'").fetchone()["id"]
    seed_personal(db, rid, user_id=member_id, rating=2)
    entry = member.get("/api/v1/recipes").get_json()["recipes"][0]
    assert entry["favorite"] is False
    assert entry["rating"] == 2
    assert _titles(member.get("/api/v1/recipes?favorites=1")) == []


def test_admin_worklist_filters_are_ignored(client, db):
    _make_recipe(db, title="Checked")
    _make_recipe(db, title="Unchecked", needs_review=1)
    assert _titles(client.get("/api/v1/recipes?needs_review=1")) == ["Checked", "Unchecked"]


# --- One recipe ---

def test_recipe_detail(client, db):
    rid = _make_recipe(
        db, title="Pancakes", source="Grandma's card",
        instructions_html="<ol><li>Mix.</li><li>Fry.</li></ol>",
    )
    seed_ingredient(db, rid, 0, "Batter", kind="heading")
    seed_ingredient(db, rid, 1, "1 cup flour")
    db.execute(
        "INSERT INTO notes (recipe_id, body, author_id, created_at) VALUES (?, 'Double it', 1, '2026-10-01T09:00:00')",
        (rid,),
    )
    db.commit()

    data = client.get(f"/api/v1/recipes/{rid}").get_json()
    assert data["title"] == "Pancakes"
    assert data["source"] == "Grandma's card"
    assert data["ingredients"] == [{"kind": "heading", "text": "Batter"}, {"kind": "item", "text": "1 cup flour"}]
    assert data["steps"] == ["Mix.", "Fry."]
    assert data["instructions_html"] == "<ol><li>Mix.</li><li>Fry.</li></ol>"
    assert [n["body"] for n in data["notes"]] == ["Double it"]
    assert data["notes"][0]["created_at"] == "2026-10-01T09:00:00"
    assert data["web_url"].endswith(f"/recipes/{rid}")


def test_missing_recipe_is_a_json_404(client, db):
    resp = client.get("/api/v1/recipes/999")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "not found"}


# --- Categories ---

def test_categories_in_order_with_counts(client, db):
    breads = _category(db, "Breads", sort_order=2)
    soups = _category(db, "Soups", sort_order=1)
    _category(db, "Empty", sort_order=3)
    _make_recipe(db, title="Rye", category_id=breads)
    _make_recipe(db, title="Sourdough", category_id=breads)
    _make_recipe(db, title="Minestrone", category_id=soups)
    cats = client.get("/api/v1/categories").get_json()["categories"]
    mine = [c for c in cats if c["name"] in ("Breads", "Soups", "Empty")]
    assert [(c["name"], c["recipe_count"]) for c in mine] == [("Soups", 1), ("Breads", 2), ("Empty", 0)]


# --- Who can ask ---

def test_strangers_are_turned_away(app, db):
    stranger = app.test_client()
    stranger.environ_base["HTTP_X_FORWARDED_HOST"] = "recipes.example.com"
    assert stranger.get("/api/v1/recipes").status_code == 403


def test_signed_in_member_can_read(member, db):
    _make_recipe(db, title="Apple Pie")
    assert _titles(member.get("/api/v1/recipes")) == ["Apple Pie"]


# --- Splitting instructions into steps ---

def test_steps_from_a_list():
    assert instruction_steps("<ol><li>Mix  the\n flour.</li><li>Bake.</li></ol>") == ["Mix the flour.", "Bake."]


def test_steps_from_paragraphs_skip_blank_ones():
    html = "<p>Make the brine.</p><p><br></p><p>Brine the turkey.</p>"
    assert instruction_steps(html) == ["Make the brine.", "Brine the turkey."]


def test_line_breaks_stay_inside_a_step():
    assert instruction_steps("<p>Line one<br>Line two</p>") == ["Line one\nLine two"]


def test_paragraphs_inside_a_list_item_are_one_step():
    html = "<ol><li><p>First part.</p><p>Second part.</p></li><li>Next.</li></ol>"
    assert instruction_steps(html) == ["First part. Second part.", "Next."]


def test_mixed_paragraphs_and_lists():
    html = "<p>Before you start:</p><ol><li><em>Gently</em> stir.</li></ol><p>Serve.</p>"
    assert instruction_steps(html) == ["Before you start:", "Gently stir.", "Serve."]


def test_entities_and_empty_html():
    assert instruction_steps("<p>Heat to 350&deg; &amp; bake</p>") == ["Heat to 350° & bake"]
    assert instruction_steps("") == []
    assert instruction_steps(None) == []
