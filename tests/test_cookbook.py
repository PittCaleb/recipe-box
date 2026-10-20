import pymupdf

from app.rendering.cookbook import gather_cookbook_data, render_cookbook_pdf
from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def _two_categories(db):
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Breads', 0)")
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Desserts', 1)")
    db.execute("INSERT INTO categories (name, sort_order) VALUES ('Empty Category', 2)")
    db.commit()
    rows = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM categories").fetchall()}
    return rows


def test_gather_cookbook_data_filters_by_category_and_skips_empty(db):
    cats = _two_categories(db)
    r1 = seed_recipe(db, title="Bread One", category_id=cats["Breads"])
    r2 = seed_recipe(db, title="Cake One", category_id=cats["Desserts"])
    sync_fts(db, r1, "Bread One")
    sync_fts(db, r2, "Cake One")

    sections = gather_cookbook_data(db, [cats["Breads"], cats["Desserts"], cats["Empty Category"]])
    names = [s["category"]["name"] for s in sections]
    assert "Breads" in names
    assert "Desserts" in names
    assert "Empty Category" not in names  # no recipes -> skipped


def test_gather_cookbook_data_respects_selected_categories_only(db):
    cats = _two_categories(db)
    seed_recipe(db, title="Bread One", category_id=cats["Breads"])
    r2 = seed_recipe(db, title="Cake One", category_id=cats["Desserts"])
    sync_fts(db, r2, "Cake One")

    sections = gather_cookbook_data(db, [cats["Desserts"]])
    assert len(sections) == 1
    assert sections[0]["category"]["name"] == "Desserts"


_build_counter = [0]


def _build(db, cfg, category_ids, **kw):
    cfg.ensure_data_dirs()
    _build_counter[0] += 1
    out_path = cfg.TMP_DIR / f"test_cookbook_{_build_counter[0]}.pdf"
    render_cookbook_pdf(db, cfg, category_ids, "Test Cookbook", kw.get("include_images", True),
                         kw.get("include_notes", True), out_path)
    return out_path


def test_render_cookbook_pdf_structure(app, db, cfg):
    cats = _two_categories(db)
    r1 = seed_recipe(db, title="Bread One", category_id=cats["Breads"], instructions_html="<p>Bake it.</p>")
    seed_ingredient(db, r1, 0, "2 cups flour")
    sync_fts(db, r1, "Bread One")
    r2 = seed_recipe(db, title="Cake One", category_id=cats["Desserts"], instructions_html="<p>Frost it.</p>")
    seed_ingredient(db, r2, 0, "1 cup sugar")
    sync_fts(db, r2, "Cake One")

    with app.test_request_context():
        out_path = _build(db, cfg, [cats["Breads"], cats["Desserts"]])

    doc = pymupdf.open(str(out_path))
    # cover + TOC + (divider + recipe) * 2 categories = 6 pages minimum
    assert len(doc) >= 6
    full_text = "\n".join(page.get_text() for page in doc)
    assert "Test Cookbook" in full_text
    assert "Contents" in full_text
    assert "Breads" in full_text
    assert "Desserts" in full_text
    assert "Bread One" in full_text
    assert "Cake One" in full_text


def test_render_cookbook_pdf_excludes_unselected_category(app, db, cfg):
    cats = _two_categories(db)
    r1 = seed_recipe(db, title="Bread One", category_id=cats["Breads"])
    sync_fts(db, r1, "Bread One")
    r2 = seed_recipe(db, title="Cake One", category_id=cats["Desserts"])
    sync_fts(db, r2, "Cake One")

    with app.test_request_context():
        out_path = _build(db, cfg, [cats["Breads"]])

    doc = pymupdf.open(str(out_path))
    full_text = "\n".join(page.get_text() for page in doc)
    assert "Bread One" in full_text
    assert "Cake One" not in full_text


def test_render_cookbook_pdf_notes_toggle(app, db, cfg):
    cats = _two_categories(db)
    r1 = seed_recipe(db, title="Noted Bread", category_id=cats["Breads"])
    sync_fts(db, r1, "Noted Bread")
    db.execute(
        "INSERT INTO notes (recipe_id, body, created_at) VALUES (?, 'A very particular secret note', '2026-01-01T00:00:00')",
        (r1,),
    )
    db.commit()

    with app.test_request_context():
        with_notes = _build(db, cfg, [cats["Breads"]], include_notes=True)
        without_notes = _build(db, cfg, [cats["Breads"]], include_notes=False)

    text_with = "\n".join(p.get_text() for p in pymupdf.open(str(with_notes)))
    text_without = "\n".join(p.get_text() for p in pymupdf.open(str(without_notes)))
    assert "A very particular secret note" in text_with
    assert "A very particular secret note" not in text_without


# --- Routes ---

def test_cookbook_form_route(client, db):
    resp = client.get("/admin/cookbook")
    assert resp.status_code == 200
    assert b"Build cookbook PDF" in resp.data


def test_cookbook_build_route(client, db, cfg):
    cats = _two_categories(db)
    rid = seed_recipe(db, title="Routed Bread", category_id=cats["Breads"])
    sync_fts(db, rid, "Routed Bread")

    resp = client.post(
        "/admin/cookbook/build",
        data={
            "cover_title": "My Cookbook",
            "category_id": [str(cats["Breads"])],
            "include_images": "1",
            "include_notes": "1",
        },
    )
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:4] == b"%PDF"
    saved = list(cfg.EXPORTS_DIR.glob("cookbook-*.pdf"))
    assert len(saved) == 1
