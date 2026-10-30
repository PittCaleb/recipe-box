import io

from PIL import Image

from tests.conftest import seed_ingredient, seed_recipe, sync_fts


def _printable(db, title="Printable Pie"):
    rid = seed_recipe(db, title=title, instructions_html="<p>Bake it.</p>")
    seed_ingredient(db, rid, 0, "1 cup flour")
    sync_fts(db, rid, title)
    return rid


# --- PDF ---

def test_download_pdf(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = _printable(db)
    resp = client.get(f"/recipes/{rid}/pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:4] == b"%PDF"
    assert "Printable-Pie" in resp.headers["Content-Disposition"]


def test_download_pdf_404_for_missing_recipe(client, db, cfg):
    cfg.ensure_data_dirs()
    assert client.get("/recipes/9999/pdf").status_code == 404


# --- Image ---

def test_image_inline_is_a_png_for_the_clipboard(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = _printable(db)
    resp = client.get(f"/recipes/{rid}/image")
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"
    assert "attachment" not in resp.headers.get("Content-Disposition", "")
    img = Image.open(io.BytesIO(resp.data))
    assert img.format == "PNG"
    # Trimmed to content: a short recipe is far shorter than a full
    # letter page (11in at 150dpi = 1650px), but still full text width.
    assert img.width > 900
    assert 100 < img.height < 1000


def test_image_download_is_an_attachment(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = _printable(db, title="Grandma's Pie!")
    resp = client.get(f"/recipes/{rid}/image?download=1")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    assert "attachment" in disposition
    assert "Grandmas-Pie.png" in disposition


def test_image_404_for_missing_recipe(client, db, cfg):
    cfg.ensure_data_dirs()
    assert client.get("/recipes/9999/image").status_code == 404


# --- Recipe page controls ---

def test_recipe_page_has_export_controls_and_no_email_or_text(client, db, cfg):
    rid = _printable(db)
    resp = client.get(f"/recipes/{rid}", follow_redirects=True)
    assert b"Save PDF" in resp.data
    assert f"/recipes/{rid}/image?download=1".encode() in resp.data
    assert b'id="copy-image-btn" hidden' in resp.data
    assert f'data-image-url="/recipes/{rid}/image"'.encode() in resp.data
    for gone in (b"email-modal", b"text-modal", b"data-share-form", b'aria-label="Email"', b'aria-label="Text"'):
        assert gone not in resp.data


def test_email_and_text_routes_are_gone(client, db, cfg):
    rid = _printable(db)
    assert client.post(f"/recipes/{rid}/email").status_code in (404, 405)
    assert client.post(f"/recipes/{rid}/text").status_code in (404, 405)


def test_exports_open_to_everyone(member, cfg, db):
    cfg.ensure_data_dirs()
    client = member
    rid = _printable(db)
    assert client.get(f"/recipes/{rid}/pdf").status_code == 200
    assert client.get(f"/recipes/{rid}/image").status_code == 200
