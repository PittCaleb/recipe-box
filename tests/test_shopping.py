import json
import re

import pytest

from app.ingredients.parser import parse_ingredient
from app.ingredients.scaling import MULTIPLIER_STOPS
from app.shopping import shopping_entry, shopping_list, shopping_name
from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def _ing(raw, split=False, no_scale=0, kind="item"):
    base = {"kind": kind, "raw_text": raw, "no_scale": no_scale, "is_split": 0,
            "quantity": None, "quantity_max": None, "unit": None, "item": None}
    if split:
        base.update(is_split=1, **parse_ingredient(raw))
    return base


@pytest.mark.parametrize("item, expected", [
    ("heavy whipping cream", "Heavy whipping cream"),
    ("butter, softened", "Butter"),
    ("(2 sticks) butter, chunked", "Butter"),
    ("(185g) confectioners' sugar, sifted", "Confectioners' sugar"),
    ("small onion; diced", "Small onion"),
    ("fat-free, less-sodium chicken broth", "Fat-free, less-sodium chicken broth"),
    ("egg whites, room temp. (about 12)", "Egg whites"),
    ("black pepper, freshly ground", "Black pepper"),
])
def test_shopping_name(item, expected):
    assert shopping_name(item) == expected


@pytest.mark.parametrize("raw, expected", [
    ("2 cups heavy whipping cream", "Heavy whipping cream (2 cups)"),
    ("1 t. vanilla", "Vanilla (1 tsp)"),
    ("1 pound Crisco", "Crisco (1 lb)"),
    ("3 eggs", "Eggs (3)"),
    ("1 egg", "Egg (1)"),
    ("2 sticks butter, softened", "Butter (2 sticks)"),
    ("8 (1/8-inch-thick) slices peeled fresh ginger", "Peeled fresh ginger (8 slices)"),
    ("10 drops green food coloring", "Green food coloring (10 drops)"),
    ("2-3 cups water", "Water (2–3 cups)"),
])
def test_entry_puts_name_first_and_amount_in_parentheses(raw, expected):
    assert shopping_entry(_ing(raw)) == expected
    assert shopping_entry(_ing(raw, split=True)) == expected


@pytest.mark.parametrize("raw", ["salt to taste", "salt", "dash salt", "1 pinch nutmeg", "Savory Herb Gravy"])
def test_no_entry_without_a_real_amount(raw):
    assert shopping_entry(_ing(raw)) is None


def test_heading_has_no_entry():
    assert shopping_entry(_ing("For the glaze:", kind="heading")) is None


def test_split_lines_follow_the_multiplier_but_unsplit_and_no_scale_do_not():
    assert shopping_entry(_ing("2 cups cream", split=True), 0.5) == "Cream (1 cup)"
    assert shopping_entry(_ing("3 eggs", split=True), 1 / 3) == "Egg (1)"
    assert shopping_entry(_ing("2 cups cream"), 0.5) == "Cream (2 cups)"
    assert shopping_entry(_ing("2 cups cream", split=True, no_scale=1), 0.5) == "Cream (2 cups)"


def test_list_combines_compatible_units():
    lines = [_ing(r) for r in (
        "2 cup flour", "1 pound Crisco", "2 tablespoon flour", "1 pound Crisco",
        "2 eggs", "1 egg", "4 oz cream cheese", "1/2 pound cream cheese",
    )]
    assert shopping_list(lines) == [
        "Flour (2 ⅛ cups)", "Crisco (2 lb)", "Eggs (3)", "Cream cheese (12 oz)",
    ]


def test_list_keeps_incompatible_or_ranged_lines_separate():
    lines = [_ing(r) for r in ("1 cup butter", "2 sticks butter", "1-2 apples", "2 apples", "salt to taste")]
    assert shopping_list(lines) == ["Butter (1 cup)", "Butter (2 sticks)", "Apples (1–2)", "Apples (2)"]


def test_list_matches_plural_and_singular_spellings():
    assert shopping_list([_ing("1 egg"), _ing("2 eggs")]) == ["Eggs (3)"]


# --- Recipe page ---

def _recipe(db, lines, split=False):
    rid = seed_recipe(db, title="Shop Test")
    for pos, raw in enumerate(lines):
        kw = {"is_split": 1, **parse_ingredient(raw)} if split else {}
        seed_ingredient(db, rid, pos, raw, **kw)
    sync_fts(db, rid, "Shop Test")
    return rid


def _shopping_json(html):
    m = re.search(r'<script type="application/json" id="shopping-data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_page_has_button_per_shoppable_line_and_add_all(client, db):
    rid = _recipe(db, ["2 cups cream", "salt to taste", "3 eggs"])
    html = client.get(f"/recipes/{rid}", follow_redirects=True).data.decode()
    assert html.count('class="icon-btn icon-btn--sm shop-btn') == 2
    assert 'data-shop-index="1"' not in html
    assert 'id="shop-all-btn"' in html
    assert 'aria-label="Copy shopping list as text"' in html
    data = _shopping_json(html)
    assert data["shortcut"] == "Add to Shopping List"
    assert len(data["stops"]) == 1
    assert data["stops"][0]["items"] == ["Cream (2 cups)", None, "Eggs (3)"]
    assert data["stops"][0]["all"] == ["Cream (2 cups)", "Eggs (3)"]


def test_scalable_recipe_has_entries_for_every_slider_stop(client, db):
    rid = _recipe(db, ["2 cups cream", "3 eggs"], split=True)
    data = _shopping_json(client.get(f"/recipes/{rid}", follow_redirects=True).data.decode())
    assert len(data["stops"]) == len(MULTIPLIER_STOPS)
    half = data["stops"][MULTIPLIER_STOPS.index(0.5)]
    assert half["items"] == ["Cream (1 cup)", "Eggs (1 ½)"]


def test_no_shopping_controls_when_nothing_has_an_amount(client, db):
    rid = _recipe(db, ["salt to taste", "pepper"])
    html = client.get(f"/recipes/{rid}", follow_redirects=True).data.decode()
    assert "shop-all-btn" not in html
    assert "shopping-data" not in html


def test_setup_modal_and_help_link_present(client, db):
    rid = _recipe(db, ["2 cups cream"])
    html = client.get(f"/recipes/{rid}", follow_redirects=True).data.decode()
    assert 'id="shop-setup-modal"' in html
    assert "/help/shopping-list" in html


def test_help_page_open_to_everyone(member, db):
    resp = member.get("/help/shopping-list")
    assert resp.status_code == 200
    assert b"Add to Shopping List" in resp.data
    assert b"Split Text" in resp.data


def test_menu_links_to_help(client, db):
    assert b"/help/shopping-list" in client.get("/").data


def test_about_page_open_to_everyone_and_in_the_menu(member, db):
    resp = member.get("/about")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "About the author" in html
    assert "https://github.com/PittCaleb" in html
    menu = member.get("/").data.decode()
    assert menu.index('href="/about"') < menu.index('href="/help/shopping-list"')
