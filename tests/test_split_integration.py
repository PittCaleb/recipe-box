from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def _form(rows, title="Splittable"):
    """Editor form data. rows: (kind, heading, qty, max, unit, item, no_scale)."""
    data = {"title": title, "instructions_html": "<p>x</p>"}
    keys = ["ingredient_kind", "ingredient_heading", "ingredient_quantity",
            "ingredient_quantity_max", "ingredient_unit", "ingredient_item", "ingredient_no_scale"]
    for i, key in enumerate(keys):
        data[key] = [r[i] for r in rows]
    return data


def test_update_recipe_saves_split_fields(client, db):
    rid = seed_recipe(db, title="Splittable")
    sync_fts(db, rid, "Splittable")
    client.post(f"/recipes/{rid}", data=_form([("item", "", "2", "", "cup", "flour", "0")]))
    ing = db.execute("SELECT * FROM ingredients WHERE recipe_id=?", (rid,)).fetchone()
    assert ing["is_split"] == 1
    assert ing["quantity"] == 2.0
    assert ing["unit"] == "cup"
    assert ing["item"] == "flour"
    assert ing["raw_text"] == "2 cups flour"


def test_recipe_becomes_scalable_once_split(client, db):
    rid = seed_recipe(db, title="Scale Candidate")
    sync_fts(db, rid, "Scale Candidate")
    client.post(f"/recipes/{rid}", data=_form([("item", "", "2", "", "cup", "flour", "0")], "Scale Candidate"))
    resp = client.get(f"/recipes/{rid}", follow_redirects=True)
    assert b"adjust-panel" in resp.data
    assert b"adjust-slider" in resp.data


def test_recipe_not_scalable_without_any_split(client, db):
    rid = seed_recipe(db, title="Not Scalable")
    seed_ingredient(db, rid, 0, "a pinch of this and that")
    sync_fts(db, rid, "Not Scalable")
    resp = client.get(f"/recipes/{rid}", follow_redirects=True)
    assert b"adjust-panel" not in resp.data


def test_recipe_scalable_with_mix_of_split_and_no_scale(client, db):
    rid = seed_recipe(db, title="Mixed Scale")
    seed_ingredient(db, rid, 0, "2 cups flour", is_split=1, quantity=2, unit="cup", item="flour")
    seed_ingredient(db, rid, 1, "salt to taste", no_scale=1)
    sync_fts(db, rid, "Mixed Scale")
    resp = client.get(f"/recipes/{rid}", follow_redirects=True)
    assert b"adjust-panel" in resp.data


def test_recipe_not_scalable_if_any_item_unsplit_and_not_no_scale(client, db):
    rid = seed_recipe(db, title="One Unsplit")
    seed_ingredient(db, rid, 0, "2 cups flour", is_split=1, quantity=2, unit="cup", item="flour")
    seed_ingredient(db, rid, 1, "a handful of nuts")  # not split, not no_scale
    sync_fts(db, rid, "One Unsplit")
    resp = client.get(f"/recipes/{rid}", follow_redirects=True)
    assert b"adjust-panel" not in resp.data
