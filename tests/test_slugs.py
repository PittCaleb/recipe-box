"""Readable recipe addresses: /brownies instead of /recipes/84."""
import pytest

from app.db import _migration_files, _run_python_migration, get_connection, run_migrations
from app.duplicates import merge_recipes
from app.slugs import slugify
from tests.conftest import seed_recipe


def _form(title):
    return {
        "title": title, "instructions_html": "<p>Bake.</p>",
        "ingredient_kind": ["item"], "ingredient_quantity": ["1"], "ingredient_quantity_max": [""],
        "ingredient_unit": ["cup"], "ingredient_item": ["flour"], "ingredient_no_scale": ["0"],
    }


def _slug(db, rid):
    return db.execute("SELECT slug FROM recipes WHERE id = ?", (rid,)).fetchone()["slug"]


@pytest.mark.parametrize("title, slug", [
    ("Brownies", "brownies"),
    ("Grandma's Chili (Spicy!)", "grandmas-chili-spicy"),
    ("Grandma’s Chili", "grandmas-chili"),
    ("Mac & Cheese", "mac-and-cheese"),
    ("Crème Brûlée", "creme-brulee"),
    ("  1-2-3   Cake  ", "1-2-3-cake"),
    ("🍪🍪", "recipe"),
    ("", "recipe"),
])
def test_slugify(title, slug):
    assert slugify(title) == slug


def test_long_titles_are_cut_at_a_word():
    slug = slugify("Very " * 40 + "Long Cake")
    assert len(slug) <= 80
    assert not slug.endswith("-")
    assert slug.split("-")[-1] == "very"


def test_same_title_gets_a_number(db):
    first = seed_recipe(db, title="Brownies")
    second = seed_recipe(db, title="Brownies")
    third = seed_recipe(db, title="brownies!")
    assert [_slug(db, r) for r in (first, second, third)] == ["brownies", "brownies-2", "brownies-3"]


def test_reserved_words_are_skipped(db):
    assert _slug(db, seed_recipe(db, title="Admin")) == "admin-2"
    assert _slug(db, seed_recipe(db, title="Shopping List")) == "shopping-list-2"


def test_recipe_page_is_at_its_slug(client, db):
    seed_recipe(db, title="Brownies")
    resp = client.get("/brownies")
    assert resp.status_code == 200
    assert b"Brownies" in resp.data


def test_unknown_slug_is_404(client, db):
    assert client.get("/no-such-thing").status_code == 404


def test_old_id_link_redirects_to_slug(client, db):
    rid = seed_recipe(db, title="Brownies")
    resp = client.get(f"/recipes/{rid}")
    assert resp.status_code == 301
    assert resp.headers["Location"] == "/brownies"
    assert client.get("/recipes/9999").status_code == 404


def test_capitals_redirect_to_the_real_slug(client, db):
    seed_recipe(db, title="Brownies")
    resp = client.get("/Brownies")
    assert resp.status_code == 301
    assert resp.headers["Location"] == "/brownies"


def test_new_recipe_lands_on_its_slug(client, db):
    resp = client.post("/recipes/new", data=_form("Lemon Bars"))
    assert resp.headers["Location"] == "/lemon-bars"


def test_rename_moves_the_slug_and_old_links_still_work(client, db):
    rid = seed_recipe(db, title="Brownies")
    resp = client.post(f"/recipes/{rid}", data=_form("Fudgy Brownies"))
    assert resp.headers["Location"] == "/fudgy-brownies"

    old = client.get("/brownies")
    assert old.status_code == 301
    assert old.headers["Location"] == "/fudgy-brownies"

    # The old name still points at this recipe, so a new one doesn't take it.
    other = seed_recipe(db, title="Brownies")
    assert _slug(db, other) == "brownies-2"

    # Renaming back reclaims it.
    client.post(f"/recipes/{rid}", data=_form("Brownies"))
    assert _slug(db, rid) == "brownies"


def test_saving_without_renaming_keeps_the_slug(client, db):
    seed_recipe(db, title="Brownies")
    rid = seed_recipe(db, title="Brownies")
    client.post(f"/recipes/{rid}", data=_form("Brownies"))
    assert _slug(db, rid) == "brownies-2"


def test_deleting_a_recipe_frees_its_slugs(client, db):
    rid = seed_recipe(db, title="Brownies")
    client.post(f"/recipes/{rid}/delete")
    assert client.get("/brownies").status_code == 404
    assert _slug(db, seed_recipe(db, title="Brownies")) == "brownies"


def test_merged_copy_links_lead_to_the_kept_recipe(client, db):
    keep = seed_recipe(db, title="Brownies")
    gone = seed_recipe(db, title="Brownies")
    with db:
        merge_recipes(db, keep, [gone], new_title="Best Brownies")
    assert _slug(db, keep) == "best-brownies"
    for old in ("/brownies", "/brownies-2"):
        resp = client.get(old)
        assert resp.status_code == 301
        assert resp.headers["Location"] == "/best-brownies"


def test_app_pages_win_over_slugs(client, db):
    assert client.get("/admin/").status_code == 200
    assert client.get("/help/shopping-list").status_code == 200


def test_migration_gives_existing_recipes_slugs_oldest_first(cfg):
    cfg.ensure_data_dirs()
    conn = get_connection(cfg.DB_PATH)
    for path in _migration_files():
        version = int(path.name.split("_", 1)[0])
        if version >= 8:
            break
        if path.suffix == ".py":
            _run_python_migration(conn, path)
        else:
            conn.executescript(path.read_text())
        conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, 'x')", (version,))
    conn.execute(
        "INSERT INTO recipes (id, title, created_at, updated_at) "
        "VALUES (9, 'Brownies', 'x', 'x'), (4, 'Brownies', 'x', 'x'), (5, 'Help', 'x', 'x')"
    )
    conn.commit()
    conn.close()

    run_migrations(cfg.DB_PATH)

    conn = get_connection(cfg.DB_PATH)
    slugs = dict(conn.execute("SELECT id, slug FROM recipes").fetchall())
    history = conn.execute("SELECT COUNT(*) FROM recipe_slugs").fetchone()[0]
    conn.close()
    assert slugs == {4: "brownies", 5: "help-2", 9: "brownies-2"}
    assert history == 3
