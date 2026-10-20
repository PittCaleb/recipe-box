from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def test_parse_ingredient_endpoint(client):
    resp = client.get("/recipes/parse-ingredient?text=1 1/2 cups sugar")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["quantity"] == 1.5
    assert data["unit"] == "cup"
    assert data["item"] == "sugar"


def test_update_recipe_saves_split_fields(client, db):
    rid = seed_recipe(db, title="Splittable")
    sync_fts(db, rid, "Splittable")

    client.post(
        f"/recipes/{rid}",
        data={
            "title": "Splittable",
            "instructions_html": "<p>x</p>",
            "ingredient_kind": ["item"],
            "ingredient_text": ["2 cups flour"],
            "ingredient_no_scale": ["0"],
            "ingredient_is_split": ["1"],
            "ingredient_quantity": ["2"],
            "ingredient_quantity_max": [""],
            "ingredient_unit": ["cup"],
            "ingredient_item": ["flour"],
        },
    )
    ing = db.execute("SELECT * FROM ingredients WHERE recipe_id=?", (rid,)).fetchone()
    assert ing["is_split"] == 1
    assert ing["quantity"] == 2.0
    assert ing["unit"] == "cup"
    assert ing["item"] == "flour"
    assert ing["raw_text"] == "2 cups flour"


def test_recipe_becomes_scalable_once_split(client, db):
    rid = seed_recipe(db, title="Scale Candidate")
    sync_fts(db, rid, "Scale Candidate")
    client.post(
        f"/recipes/{rid}",
        data={
            "title": "Scale Candidate",
            "instructions_html": "<p>x</p>",
            "ingredient_kind": ["item"],
            "ingredient_text": ["2 cups flour"],
            "ingredient_no_scale": ["0"],
            "ingredient_is_split": ["1"],
            "ingredient_quantity": ["2"],
            "ingredient_quantity_max": [""],
            "ingredient_unit": ["cup"],
            "ingredient_item": ["flour"],
        },
    )
    resp = client.get(f"/recipes/{rid}")
    assert b"adjust-panel" in resp.data
    assert b"adjust-slider" in resp.data


def test_recipe_not_scalable_without_any_split(client, db):
    rid = seed_recipe(db, title="Not Scalable")
    seed_ingredient(db, rid, 0, "a pinch of this and that")
    sync_fts(db, rid, "Not Scalable")
    resp = client.get(f"/recipes/{rid}")
    assert b"adjust-panel" not in resp.data


def test_recipe_scalable_with_mix_of_split_and_no_scale(client, db):
    rid = seed_recipe(db, title="Mixed Scale")
    seed_ingredient(db, rid, 0, "2 cups flour", is_split=1, quantity=2, unit="cup", item="flour")
    seed_ingredient(db, rid, 1, "salt to taste", no_scale=1)
    sync_fts(db, rid, "Mixed Scale")
    resp = client.get(f"/recipes/{rid}")
    assert b"adjust-panel" in resp.data


def test_recipe_not_scalable_if_any_item_unsplit_and_not_no_scale(client, db):
    rid = seed_recipe(db, title="One Unsplit")
    seed_ingredient(db, rid, 0, "2 cups flour", is_split=1, quantity=2, unit="cup", item="flour")
    seed_ingredient(db, rid, 1, "a handful of nuts")  # not split, not no_scale
    sync_fts(db, rid, "One Unsplit")
    resp = client.get(f"/recipes/{rid}")
    assert b"adjust-panel" not in resp.data
