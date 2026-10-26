import json
from unittest.mock import patch

import pymupdf
import pytest

from app.claude_import import ExtractedIngredient, ExtractedRecipe, PageExtraction
from app.import_jobs import _run
from app.db import get_connection
from tests.conftest import seed_recipe, sync_fts


def _make_pdf(path, pages=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()


def _recipe(title="Test Dish", category="Side Dishes", crop_box=None, **kw):
    defaults = dict(
        title=title,
        instructions_html="<p>Do the thing.</p>",
        ingredients=[ExtractedIngredient(kind="item", raw_text="1 cup flour")],
        notes=[],
        proposed_category=category,
        needs_review=False,
        crop_box=crop_box or [0.0, 0.0, 1.0, 1.0],
    )
    defaults.update(kw)
    return ExtractedRecipe(**defaults)


@pytest.fixture
def batch_cfg(cfg):
    from app.db import run_migrations
    cfg.ensure_data_dirs()
    cfg.PDF_DIR.mkdir(parents=True, exist_ok=True)
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    run_migrations(cfg.DB_PATH)
    return cfg


def _make_batch(db, pdf_filename="test.pdf"):
    db.execute(
        "INSERT INTO import_batches (source_pdf, original_filename, status, created_at, updated_at) "
        "VALUES (?, ?, 'pending', '2026-01-01T00:00:00', '2026-01-01T00:00:00')",
        (pdf_filename, pdf_filename),
    )
    db.commit()
    return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


# --- Job logic (Claude API mocked) ---

def test_run_import_job_stages_recipes(batch_cfg):
    pdf_filename = "mycards.pdf"
    _make_pdf(batch_cfg.PDF_DIR / pdf_filename, pages=2)

    conn = get_connection(batch_cfg.DB_PATH)
    batch_id = _make_batch(conn, pdf_filename)

    page_results = [
        PageExtraction(recipes=[_recipe(title="Page One Dish", crop_box=[0.0, 0.0, 1.0, 1.0])]),
        PageExtraction(recipes=[
            _recipe(title="Page Two Dish A", crop_box=[0.0, 0.0, 1.0, 0.5]),
            _recipe(title="Page Two Dish B", crop_box=[0.0, 0.5, 1.0, 1.0]),
        ]),
    ]

    with patch("app.import_jobs.extract_recipes_from_page", side_effect=page_results):
        _run(conn, batch_cfg, batch_id, pdf_filename, default_contributor=None)

    batch = conn.execute("SELECT * FROM import_batches WHERE id=?", (batch_id,)).fetchone()
    assert batch["status"] == "ready"
    assert batch["total_pages"] == 2
    assert batch["processed_pages"] == 2

    staged = conn.execute(
        "SELECT * FROM import_batch_recipes WHERE batch_id=? ORDER BY source_page, id", (batch_id,)
    ).fetchall()
    assert len(staged) == 3
    assert staged[0]["title"] == "Page One Dish"
    assert staged[1]["title"] == "Page Two Dish A"
    assert staged[2]["title"] == "Page Two Dish B"

    for row in staged:
        assert row["scan_filename"] is not None
        assert (batch_cfg.SCANS_DIR / row["scan_filename"]).exists()
        ingredients = json.loads(row["ingredients_json"])
        assert ingredients[0]["raw_text"] == "1 cup Flour"

    conn.close()


def test_run_import_job_sanitizes_instructions(batch_cfg):
    pdf_filename = "dirty.pdf"
    _make_pdf(batch_cfg.PDF_DIR / pdf_filename, pages=1)
    conn = get_connection(batch_cfg.DB_PATH)
    batch_id = _make_batch(conn, pdf_filename)

    malicious = _recipe(
        title="Sanitize Me",
        instructions_html='<p onclick="alert(1)">Hi</p><script>bad()</script>',
    )
    with patch("app.import_jobs.extract_recipes_from_page", return_value=PageExtraction(recipes=[malicious])):
        _run(conn, batch_cfg, batch_id, pdf_filename, default_contributor=None)

    row = conn.execute("SELECT instructions_html FROM import_batch_recipes WHERE batch_id=?", (batch_id,)).fetchone()
    assert "<script>" not in row["instructions_html"]
    assert "onclick" not in row["instructions_html"]
    assert "<p>Hi</p>" in row["instructions_html"]
    conn.close()


def test_run_import_job_applies_default_contributor_passthrough(batch_cfg):
    # The model is responsible for applying the default contributor; the job
    # just needs to pass it through and persist whatever comes back.
    pdf_filename = "contrib.pdf"
    _make_pdf(batch_cfg.PDF_DIR / pdf_filename, pages=1)
    conn = get_connection(batch_cfg.DB_PATH)
    batch_id = _make_batch(conn, pdf_filename)

    recipe = _recipe(title="Has Contributor", contributor="Grandma Jo")
    with patch("app.import_jobs.extract_recipes_from_page", return_value=PageExtraction(recipes=[recipe])) as mocked:
        _run(conn, batch_cfg, batch_id, pdf_filename, default_contributor="Grandma Jo")
        assert mocked.call_args.kwargs["default_contributor"] == "Grandma Jo"

    row = conn.execute("SELECT contributor FROM import_batch_recipes WHERE batch_id=?", (batch_id,)).fetchone()
    assert row["contributor"] == "Grandma Jo"
    conn.close()


def test_run_import_job_survives_a_page_failure(batch_cfg):
    pdf_filename = "flaky.pdf"
    _make_pdf(batch_cfg.PDF_DIR / pdf_filename, pages=2)
    conn = get_connection(batch_cfg.DB_PATH)
    batch_id = _make_batch(conn, pdf_filename)

    def side_effect(*args, **kwargs):
        if kwargs["page_num"] == 1:
            raise RuntimeError("simulated API error")
        return PageExtraction(recipes=[_recipe(title="Survivor")])

    with patch("app.import_jobs.extract_recipes_from_page", side_effect=side_effect):
        _run(conn, batch_cfg, batch_id, pdf_filename, default_contributor=None)

    batch = conn.execute("SELECT * FROM import_batches WHERE id=?", (batch_id,)).fetchone()
    assert batch["status"] == "ready"
    assert "page 1" in batch["error_message"]

    staged = conn.execute("SELECT * FROM import_batch_recipes WHERE batch_id=?", (batch_id,)).fetchall()
    assert len(staged) == 1
    assert staged[0]["title"] == "Survivor"
    conn.close()


def test_crop_box_is_clamped(batch_cfg):
    pdf_filename = "badbox.pdf"
    _make_pdf(batch_cfg.PDF_DIR / pdf_filename, pages=1)
    conn = get_connection(batch_cfg.DB_PATH)
    batch_id = _make_batch(conn, pdf_filename)

    recipe = _recipe(title="Bad Box", crop_box=[-0.5, -0.2, 1.8, 2.0])
    with patch("app.import_jobs.extract_recipes_from_page", return_value=PageExtraction(recipes=[recipe])):
        _run(conn, batch_cfg, batch_id, pdf_filename, default_contributor=None)

    row = conn.execute("SELECT scan_filename FROM import_batch_recipes WHERE batch_id=?", (batch_id,)).fetchone()
    assert (batch_cfg.SCANS_DIR / row["scan_filename"]).exists()
    conn.close()


# --- Routes ---

def test_upload_requires_api_key(client, db, cfg):
    cfg.ANTHROPIC_API_KEY = None
    resp = client.post("/admin/import/", data={}, follow_redirects=True)
    assert b"ANTHROPIC_API_KEY" in resp.data


def test_upload_requires_a_file(client, db, batch_cfg):
    resp = client.post("/admin/import/", data={}, follow_redirects=True)
    assert b"Choose a PDF" in resp.data


def test_upload_rejects_non_pdf(client, db, batch_cfg):
    import io
    resp = client.post(
        "/admin/import/",
        data={"pdf": (io.BytesIO(b"not a pdf"), "notes.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"doesn" in resp.data.lower()


def test_upload_creates_batch_and_saves_file(client, db, batch_cfg):
    import io
    with patch("app.routes.import_pdf.start_import_job") as mock_start:
        resp = client.post(
            "/admin/import/",
            data={"pdf": (io.BytesIO(b"%PDF-1.4 fake"), "Grandma's Cards.pdf"), "default_contributor": "Pat"},
            content_type="multipart/form-data",
        )
    assert resp.status_code == 302
    assert "/admin/import/" in resp.headers["Location"]

    batch = db.execute("SELECT * FROM import_batches").fetchone()
    assert batch is not None
    assert batch["original_filename"] == "Grandma's Cards.pdf"
    assert batch["default_contributor"] == "Pat"
    assert (batch_cfg.PDF_DIR / batch["source_pdf"]).exists()
    mock_start.assert_called_once()


def test_status_endpoint(client, db, batch_cfg):
    batch_id = _make_batch(db)
    db.execute(
        "UPDATE import_batches SET status='transcribing', total_pages=5, processed_pages=2 WHERE id=?",
        (batch_id,),
    )
    db.commit()
    resp = client.get(f"/admin/import/{batch_id}/status")
    data = resp.get_json()
    assert data["status"] == "transcribing"
    assert data["total_pages"] == 5
    assert data["processed_pages"] == 2


def test_progress_page_shows_review_once_ready(client, db, batch_cfg):
    batch_id = _make_batch(db)
    db.execute(
        """INSERT INTO import_batch_recipes
           (batch_id, source_page, title, instructions_html, proposed_category, ingredients_json, notes_json)
           VALUES (?, 1, 'Ready Dish', '<p>x</p>', 'Breads', '[]', '[]')""",
        (batch_id,),
    )
    db.execute("UPDATE import_batches SET status='ready' WHERE id=?", (batch_id,))
    db.commit()

    resp = client.get(f"/admin/import/{batch_id}")
    assert b"Ready Dish" in resp.data
    assert b"Commit selected recipes" in resp.data


def _stage_recipe(db, batch_id, **kw):
    defaults = dict(
        title="Staged Dish", contributor=None, source=None, servings=None, prep_time=None,
        cook_time=None, instructions_html="<p>Mix.</p>", proposed_category="Breads",
        needs_review=0, review_note=None, scan_filename="batch1-p001-a.jpg",
        ingredients_json=json.dumps([{"kind": "item", "raw_text": "2 cups flour", "no_scale": False}]),
        notes_json=json.dumps(["From original card: a note"]),
    )
    defaults.update(kw)
    cur = db.execute(
        """INSERT INTO import_batch_recipes
           (batch_id, source_page, title, contributor, source, servings, prep_time, cook_time,
            instructions_html, proposed_category, needs_review, review_note, scan_filename,
            ingredients_json, notes_json, included)
           VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            batch_id, defaults["title"], defaults["contributor"], defaults["source"],
            defaults["servings"], defaults["prep_time"], defaults["cook_time"],
            defaults["instructions_html"], defaults["proposed_category"], defaults["needs_review"],
            defaults["review_note"], defaults["scan_filename"], defaults["ingredients_json"],
            defaults["notes_json"],
        ),
    )
    db.commit()
    return cur.lastrowid


def test_commit_creates_real_recipes(client, db, batch_cfg):
    batch_id = _make_batch(db, "committest.pdf")
    (batch_cfg.SCANS_DIR).mkdir(parents=True, exist_ok=True)
    (batch_cfg.SCANS_DIR / "batch1-p001-a.jpg").write_bytes(b"fake")
    staged_id = _stage_recipe(db, batch_id)

    resp = client.post(
        f"/admin/import/{batch_id}/commit",
        data={f"include_{staged_id}": "1", f"title_{staged_id}": "Staged Dish", f"category_{staged_id}": "Breads"},
    )
    assert resp.status_code == 302

    recipe = db.execute("SELECT * FROM recipes WHERE title='Staged Dish'").fetchone()
    assert recipe is not None
    assert recipe["scan_filename"] == "batch1-p001-a.jpg"
    assert recipe["source_pdf"] == "committest.pdf"
    assert recipe["source_page"] == 1

    cat = db.execute("SELECT name FROM categories WHERE id=?", (recipe["category_id"],)).fetchone()
    assert cat["name"] == "Breads"

    notes = db.execute("SELECT body FROM notes WHERE recipe_id=?", (recipe["id"],)).fetchall()
    assert len(notes) == 1
    assert notes[0]["body"] == "From original card: a note"

    staged = db.execute("SELECT imported_recipe_id FROM import_batch_recipes WHERE id=?", (staged_id,)).fetchone()
    assert staged["imported_recipe_id"] == recipe["id"]

    batch = db.execute("SELECT status FROM import_batches WHERE id=?", (batch_id,)).fetchone()
    assert batch["status"] == "done"


def test_commit_creates_new_category_if_not_existing(client, db, batch_cfg):
    batch_id = _make_batch(db)
    staged_id = _stage_recipe(db, batch_id, scan_filename=None)
    client.post(
        f"/admin/import/{batch_id}/commit",
        data={f"include_{staged_id}": "1", f"category_{staged_id}": "Brand New Category"},
    )
    cat = db.execute("SELECT * FROM categories WHERE name='Brand New Category'").fetchone()
    assert cat is not None


def test_commit_skips_excluded_recipes(client, db, batch_cfg):
    batch_id = _make_batch(db)
    staged_id = _stage_recipe(db, batch_id, title="Excluded Dish", scan_filename=None)
    client.post(f"/admin/import/{batch_id}/commit", data={})  # include_X not sent -> excluded
    assert db.execute("SELECT COUNT(*) FROM recipes WHERE title='Excluded Dish'").fetchone()[0] == 0


def test_discard_removes_batch_and_scan_files(client, db, batch_cfg):
    batch_id = _make_batch(db)
    batch_cfg.SCANS_DIR.mkdir(parents=True, exist_ok=True)
    (batch_cfg.SCANS_DIR / "batch1-p001-a.jpg").write_bytes(b"fake")
    _stage_recipe(db, batch_id)

    client.post(f"/admin/import/{batch_id}/discard")

    assert db.execute("SELECT COUNT(*) FROM import_batches WHERE id=?", (batch_id,)).fetchone()[0] == 0
    assert not (batch_cfg.SCANS_DIR / "batch1-p001-a.jpg").exists()


# --- Auth gating ---

def test_import_requires_login_when_password_set(cfg):
    from app import create_app
    cfg.APP_PASSWORD = "sesame"
    app = create_app(cfg)
    client = app.test_client()
    resp = client.get("/admin/import/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_api_image_is_resized_jpeg_under_the_limit(tmp_path):
    import base64, io, os
    from PIL import Image
    from app.claude_import import MAX_B64_BYTES, MAX_LONG_EDGE, api_image_b64

    # Random noise is the worst case for compression -- like a photo page.
    page = Image.frombytes("RGB", (2250, 3000), os.urandom(2250 * 3000 * 3))
    path = tmp_path / "page.png"
    page.save(path)
    assert path.stat().st_size * 4 / 3 > 10 * 1024 * 1024  # what used to be sent

    b64 = api_image_b64(path)
    assert len(b64) <= MAX_B64_BYTES
    sent = Image.open(io.BytesIO(base64.b64decode(b64)))
    assert sent.format == "JPEG"
    assert max(sent.size) == MAX_LONG_EDGE


def test_small_page_is_not_upscaled(tmp_path):
    import base64, io
    from PIL import Image
    from app.claude_import import api_image_b64

    path = tmp_path / "small.png"
    Image.new("RGB", (800, 1000), "white").save(path)
    sent = Image.open(io.BytesIO(base64.b64decode(api_image_b64(path))))
    assert sent.size == (800, 1000)
