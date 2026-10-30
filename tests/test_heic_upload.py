import io

from PIL import Image

from tests.conftest import seed_recipe

EXIF_ORIENTATION = 0x0112


def _heic_bytes(size=(300, 200), orientation=None):
    """An iPhone-style HEIC photo; orientation 6 means "turn 90° to display"."""
    im = Image.new("RGB", size, (200, 50, 50))
    kwargs = {}
    if orientation:
        exif = Image.Exif()
        exif[EXIF_ORIENTATION] = orientation
        kwargs["exif"] = exif.tobytes()
    buf = io.BytesIO()
    im.save(buf, "HEIF", **kwargs)
    buf.seek(0)
    return buf


def _upload(client, rid, data, filename="IMG_0001.HEIC", content_type="image/heic"):
    return client.post(
        f"/recipes/{rid}/image",
        data={"image": (data, filename, content_type)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def _saved(db, cfg, rid):
    name = db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0]
    assert name is not None
    return Image.open(cfg.IMAGES_DIR / name)


def test_heic_photo_is_saved_as_jpeg(client, db, cfg):
    rid = seed_recipe(db, title="Phone Photo")
    _upload(client, rid, _heic_bytes())
    with _saved(db, cfg, rid) as im:
        assert im.format == "JPEG"
        assert im.size == (300, 200)


def test_rotated_heic_photo_stands_the_right_way_up(client, db, cfg):
    rid = seed_recipe(db, title="Portrait")
    _upload(client, rid, _heic_bytes(orientation=6))
    with _saved(db, cfg, rid) as im:
        assert im.size == (200, 300)


def test_heic_sent_without_a_proper_type_still_works(client, db, cfg):
    rid = seed_recipe(db, title="Mac Upload")
    _upload(client, rid, _heic_bytes(), content_type="application/octet-stream")
    with _saved(db, cfg, rid) as im:
        assert im.format == "JPEG"


def test_heic_on_a_new_recipe(client, db, cfg):
    client.post("/recipes/new", data={
        "title": "New With HEIC", "category_id": "",
        "ingredient_kind": ["item"], "ingredient_heading": [""], "ingredient_quantity": ["1"],
        "ingredient_quantity_max": [""], "ingredient_unit": ["cup"], "ingredient_item": ["flour"],
        "ingredient_no_scale": ["0"], "instructions_html": "<p>Mix.</p>",
        "image": (_heic_bytes(), "IMG_0002.HEIC", "image/heic"),
    }, content_type="multipart/form-data")
    row = db.execute("SELECT id, image_is_placeholder FROM recipes WHERE title = 'New With HEIC'").fetchone()
    assert row["image_is_placeholder"] == 0
    with _saved(db, cfg, row["id"]) as im:
        assert im.format == "JPEG"


def test_a_file_that_isnt_a_picture_is_still_refused(client, db):
    rid = seed_recipe(db, title="Not A Photo")
    resp = _upload(client, rid, io.BytesIO(b"not really a picture"), "notes.heic", "application/octet-stream")
    assert b"File is not a readable image." in resp.data
    assert db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0] is None


def test_other_file_types_are_refused(client, db):
    rid = seed_recipe(db, title="Text File")
    resp = _upload(client, rid, io.BytesIO(b"hello"), "notes.txt", "text/plain")
    assert b"Unsupported image type: text/plain" in resp.data


def test_upload_fields_offer_heic_files(client, db):
    rid = seed_recipe(db, title="Picker")
    for page in (f"/recipes/{rid}", f"/recipes/{rid}/edit"):
        assert b'accept="image/*,.heic,.heif"' in client.get(page, follow_redirects=True).data
