import importlib.util
from pathlib import Path

import pytest

from app.ingredients.parser import parse_amount
from app.ingredients.scaling import format_ingredient_line, scale_ingredient_line
from app.models.recipes import save_recipe
from tests.conftest import seed_ingredient, seed_recipe, sync_fts
from tests.test_split_integration import _form


def _ings(db, rid):
    return db.execute("SELECT * FROM ingredients WHERE recipe_id=? ORDER BY position", (rid,)).fetchall()


# --- Formatting a split line ---

@pytest.mark.parametrize("q, q_max, unit, item, expected", [
    (2, None, "oz", "semisweet chocolate squares", "2 oz semisweet chocolate squares"),
    (1.5, None, "cup", "milk", "1 ½ cups milk"),
    (0.5, None, "cup", "sugar", "½ cup sugar"),
    (3, None, "tsp", "salt", "3 tsp salt"),
    (1, 2, "cup", "water", "1–2 cups water"),
    (3, None, None, "eggs", "3 eggs"),
    (None, None, None, "salt to taste", "salt to taste"),
])
def test_format_ingredient_line(q, q_max, unit, item, expected):
    assert format_ingredient_line(q, q_max, unit, item) == expected


def test_unscaled_line_keeps_the_entered_unit():
    ing = {"kind": "item", "no_scale": 0, "is_split": 1, "quantity": 3.0,
           "quantity_max": None, "unit": "tsp", "item": "salt", "raw_text": "x"}
    assert scale_ingredient_line(ing, 1.0) == "3 tsp salt"
    assert scale_ingredient_line(ing, 2.0) == "2 tbsp salt"


@pytest.mark.parametrize("text, value", [
    ("2", 2.0), ("1 1/2", 1.5), ("1½", 1.5), ("1 ½", 1.5), ("¾", 0.75), ("0.5", 0.5),
    ("", None), ("abc", None), ("2 cups", None), ("1/0", None), ("0", None),
])
def test_parse_amount(text, value):
    assert parse_amount(text) == value


# --- Split is the source of truth ---

def test_save_rebuilds_text_from_split_fields(db):
    rid = save_recipe(db, None, {"title": "Mousse", "instructions_html": "", "owner_id": 1}, [
        {"kind": "item", "raw_text": "4 sq. semisweet chocolate", "is_split": 1,
         "quantity": 2.0, "unit": "oz", "item": "semisweet chocolate squares", "no_scale": 0},
    ])
    assert _ings(db, rid)[0]["raw_text"] == "2 oz semisweet chocolate squares"


def test_recipe_page_and_search_show_the_split_not_the_old_line(client, db):
    rid = save_recipe(db, None, {"title": "Mousse", "instructions_html": "", "owner_id": 1}, [
        {"kind": "item", "raw_text": "4 sq. semisweet chocolate", "is_split": 1,
         "quantity": 2.0, "unit": "oz", "item": "semisweet chocolate squares", "no_scale": 0},
    ])
    html = client.get(f"/recipes/{rid}").data.decode()
    assert "2 oz semisweet chocolate squares" in html
    assert "4 sq." not in html
    assert b"Mousse" in client.get("/api/search?q=squares").data


# --- Entering ingredients ---

def test_new_recipe_from_split_fields_only(client, db):
    resp = client.post("/recipes/new", data=_form([
        ("heading", "For the cream", "", "", "", "", "0"),
        ("item", "", "2", "", "cup", "Heavy Whipping Cream", "0"),
        ("item", "", "1/2", "", "cup", "Powdered Sugar", "0"),
        ("item", "", "", "", "", "salt to taste", "0"),
        ("item", "", "", "", "", "", "0"),
    ], title="Whipped Cream"))
    assert resp.status_code == 302
    rid = db.execute("SELECT id FROM recipes WHERE title='Whipped Cream'").fetchone()["id"]
    rows = _ings(db, rid)
    assert [r["raw_text"] for r in rows] == [
        "For the cream", "2 cups Heavy Whipping Cream", "½ cup Powdered Sugar", "salt to taste",
    ]
    assert rows[1]["is_split"] == 1 and rows[1]["quantity"] == 2.0
    assert rows[3]["is_split"] == 0 and rows[3]["no_scale"] == 1

    page = client.get(f"/recipes/{rid}").data.decode()
    assert "2 cups Heavy Whipping Cream" in page
    assert "adjust-slider" in page
    assert "(not scaled)" not in page


def test_ranges_and_no_scale_are_saved(client, db):
    client.post("/recipes/new", data=_form([
        ("item", "", "1", "2", "cup", "water", "0"),
        ("item", "", "1", "", "package", "yeast", "1"),
    ], title="Bread"))
    rid = db.execute("SELECT id FROM recipes WHERE title='Bread'").fetchone()["id"]
    water, yeast = _ings(db, rid)
    assert (water["quantity"], water["quantity_max"], water["raw_text"]) == (1.0, 2.0, "1–2 cups water")
    assert yeast["no_scale"] == 1 and yeast["is_split"] == 1


@pytest.mark.parametrize("row, message", [
    (("item", "", "two", "", "cup", "flour", "0"), "isn't an amount"),
    (("item", "", "2", "1", "cup", "flour", "0"), "must be larger"),
    (("item", "", "2", "", "cup", "", "0"), "add what the ingredient is"),
])
def test_bad_rows_are_rejected_and_input_is_kept(client, db, row, message):
    resp = client.post("/recipes/new", data=_form([row], title="Oops"))
    assert resp.status_code == 400
    html = resp.data.decode()
    assert message.replace("'", "&#39;") in html
    assert f'value="{row[2]}"' in html
    assert db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 0


def test_missing_title_keeps_the_ingredients_typed(client, db):
    resp = client.post("/recipes/new", data=_form([("item", "", "2", "", "cup", "flour", "0")], title=""))
    assert resp.status_code == 400
    assert b'value="flour"' in resp.data


def test_new_recipe_form_has_split_fields_and_no_single_line(client):
    html = client.get("/recipes/new").data.decode()
    assert 'name="ingredient_quantity"' in html
    assert 'name="ingredient_unit"' in html
    assert 'name="ingredient_item"' in html
    assert 'name="ingredient_text"' not in html
    assert "split-modal" not in html
    assert 'id="ingredient-row-template"' in html


# --- Editing existing recipes ---

def test_unsplit_lines_are_prefilled_and_flagged(client, db):
    rid = seed_recipe(db, title="Old Card")
    seed_ingredient(db, rid, 0, "1 1/2 c. sugar")
    seed_ingredient(db, rid, 1, "salt to taste")
    seed_ingredient(db, rid, 2, "2 cups flour", is_split=1, quantity=2, unit="cup", item="flour")
    sync_fts(db, rid, "Old Card")
    html = client.get(f"/recipes/{rid}/edit").data.decode()
    assert html.count('class="ingredient-row is-guess"') == 1
    assert "From &ldquo;1 1/2 c. sugar&rdquo;" in html
    assert 'value="1 ½"' in html
    assert 'value="sugar"' in html
    assert 'value="salt to taste"' in html
    assert "split automatically" in html


def test_delete_button_is_not_inside_the_edit_form(client, db):
    rid = seed_recipe(db, title="Deletable")
    sync_fts(db, rid, "Deletable")
    html = client.get(f"/recipes/{rid}/edit").data.decode()
    edit_form = html[html.index('id="edit-form"'):html.index("</form>")]
    assert 'action="/recipes/%d/delete"' % rid not in edit_form
    assert 'form="delete-recipe-form"' in edit_form
    assert 'id="delete-recipe-form"' in html


# --- One-time migration ---

def test_migration_rebuilds_existing_split_lines(db):
    rid = seed_recipe(db, title="Mousse")
    seed_ingredient(db, rid, 0, "4 sq. semisweet chocolate", is_split=1, quantity=2,
                    unit="oz", item="semisweet chocolate squares")
    seed_ingredient(db, rid, 1, "3 eggs", is_split=1, quantity=3, unit="", item="eggs")
    seed_ingredient(db, rid, 2, "a pinch of love")
    sync_fts(db, rid, "Mousse", ingredients_text="4 sq. semisweet chocolate")

    path = Path(__file__).parent.parent / "app/migrations/004_rebuild_split_ingredient_text.py"
    spec = importlib.util.spec_from_file_location("m004", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(db)
    db.commit()

    rows = _ings(db, rid)
    assert [r["raw_text"] for r in rows] == ["2 oz semisweet chocolate squares", "3 eggs", "a pinch of love"]
    assert rows[0]["quantity"] == 2.0 and rows[0]["item"] == "semisweet chocolate squares"
    assert rows[1]["unit"] is None
    fts = db.execute("SELECT ingredients_text FROM recipes_fts WHERE rowid=?", (rid,)).fetchone()[0]
    assert "squares" in fts and "4 sq." not in fts


def test_range_field_hidden_behind_link_unless_used(client, db):
    rid = seed_recipe(db, title="Ranges")
    seed_ingredient(db, rid, 0, "2-3 cups water", is_split=1, quantity=2, quantity_max=3, unit="cup", item="water")
    seed_ingredient(db, rid, 1, "1 cup flour", is_split=1, quantity=1, unit="cup", item="flour")
    sync_fts(db, rid, "Ranges")
    html = client.get(f"/recipes/{rid}/edit").data.decode()
    water, flour = html.split('class="ingredient-row"')[1:3]
    assert 'value="3"' in water and 'data-range-add hidden' in water
    assert 'value=""' in flour.split("ingredient_quantity_max")[1][:120]
    assert 'autocomplete="off" hidden>' in flour
    assert "+ range" in flour


# --- Nothing typed is lost when a save fails ---

def _bad_save_form(title="Hand Typed", **extra):
    data = _form([("item", "", "0", "", "", "salt (optional)", "0")], title=title)
    data.update({
        "contributor": "Aunt Bea", "source": "Notebook", "servings": "4",
        "prep_time": "10 min", "cook_time": "20 min",
        "instructions_html": "<p>Whisk <strong>gently</strong> for ten minutes.</p><script>x()</script>",
    })
    data.update(extra)
    return data


def test_failed_new_recipe_keeps_every_field(client, db):
    resp = client.post("/recipes/new", data=_bad_save_form())
    assert resp.status_code == 400
    html = resp.data.decode()
    for expected in ('value="Hand Typed"', 'value="Aunt Bea"', 'value="Notebook"', 'value="4"',
                     'value="10 min"', 'value="20 min"',
                     "<p>Whisk <strong>gently</strong> for ten minutes.</p>",
                     'value="salt (optional)"', "leave it blank if there"):
        assert expected in html, expected
    assert "<script>x()</script>" not in html
    assert db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 0


def test_failed_edit_keeps_unsaved_changes_and_note_edits(client, db):
    rid = seed_recipe(db, title="Saved Title", instructions_html="<p>Old steps.</p>")
    sync_fts(db, rid, "Saved Title")
    db.execute("INSERT INTO notes (recipe_id, body, created_at) VALUES (?, 'old note', '2026-01-01')", (rid,))
    db.commit()
    note_id = db.execute("SELECT id FROM notes WHERE recipe_id=?", (rid,)).fetchone()["id"]

    resp = client.post(f"/recipes/{rid}", data=_bad_save_form(
        title="Edited Title", **{f"note_body_{note_id}": "edited note"}))
    assert resp.status_code == 400
    html = resp.data.decode()
    assert 'value="Edited Title"' in html
    assert "Whisk <strong>gently</strong>" in html
    assert "Old steps." not in html
    assert "edited note" in html
    assert f'action="/recipes/{rid}"' in html
    assert db.execute("SELECT title FROM recipes WHERE id=?", (rid,)).fetchone()["title"] == "Saved Title"


def test_normal_edit_page_still_shows_saved_values(client, db):
    rid = seed_recipe(db, title="Saved", contributor="Pat", instructions_html="<p>Steps.</p>")
    sync_fts(db, rid, "Saved")
    html = client.get(f"/recipes/{rid}/edit").data.decode()
    assert 'value="Saved"' in html and 'value="Pat"' in html and "<p>Steps.</p>" in html
