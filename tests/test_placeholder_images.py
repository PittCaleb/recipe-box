import io
import shutil
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import app.placeholder_images as placeholders
from app.duplicates import merge_recipes
from app.images import thumb_filename
from app.placeholder_images import PlaceholderError, check_svg, extract_svg, make_placeholder, recipe_prompt
from tests.conftest import FAKE_SVG, seed_recipe

# The autouse fixture swaps in a fake; these tests need the real one.
REAL_DRAW = placeholders.draw_placeholder_svg

needs_rsvg = pytest.mark.skipif(shutil.which("rsvg-convert") is None, reason="rsvg-convert isn't installed")


def _new_recipe_form(title="Brand New Dish", **extra):
    return {
        "title": title,
        "category_id": "",
        "ingredient_kind": ["item"],
        "ingredient_heading": [""],
        "ingredient_quantity": ["1"],
        "ingredient_quantity_max": [""],
        "ingredient_unit": ["cup"],
        "ingredient_item": ["flour"],
        "ingredient_no_scale": ["0"],
        "instructions_html": "<p>Mix it.</p>",
        **extra,
    }


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color=(200, 50, 50)).save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---- new recipes ------------------------------------------------------------

@needs_rsvg
def test_new_recipe_without_photo_gets_a_placeholder(client, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    resp = client.post("/recipes/new", data=_new_recipe_form(), content_type="multipart/form-data",
                       follow_redirects=True)
    assert b"placeholder picture is being drawn" in resp.data
    row = db.execute("SELECT * FROM recipes WHERE title = 'Brand New Dish'").fetchone()
    assert fake_placeholder_drawing == ["Brand New Dish"]
    assert row["image_is_placeholder"] == 1
    assert (cfg.IMAGES_DIR / row["image_filename"]).exists()
    assert (cfg.IMAGES_DIR / thumb_filename(row["image_filename"])).exists()
    with Image.open(cfg.IMAGES_DIR / row["image_filename"]) as im:
        assert im.size == (1600, 1200)


def test_new_recipe_with_photo_gets_no_placeholder(client, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    resp = client.post("/recipes/new", data=_new_recipe_form(image=(_png_bytes(), "photo.png")),
                       content_type="multipart/form-data", follow_redirects=True)
    assert b"placeholder picture is being drawn" not in resp.data
    row = db.execute("SELECT * FROM recipes WHERE title = 'Brand New Dish'").fetchone()
    assert fake_placeholder_drawing == []
    assert row["image_filename"] is not None
    assert row["image_is_placeholder"] == 0


def test_no_placeholder_without_an_api_key(client, db, cfg, fake_placeholder_drawing):
    resp = client.post("/recipes/new", data=_new_recipe_form(), content_type="multipart/form-data",
                       follow_redirects=True)
    assert b"placeholder picture is being drawn" not in resp.data
    row = db.execute("SELECT * FROM recipes WHERE title = 'Brand New Dish'").fetchone()
    assert fake_placeholder_drawing == []
    assert row["image_filename"] is None


def test_editing_a_recipe_does_not_draw_one(client, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    rid = seed_recipe(db, title="Old Favorite")
    client.post(f"/recipes/{rid}", data=_new_recipe_form("Old Favorite"), content_type="multipart/form-data")
    assert fake_placeholder_drawing == []


@needs_rsvg
def test_real_photo_replaces_placeholder(client, db, cfg):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    client.post("/recipes/new", data=_new_recipe_form(), content_type="multipart/form-data")
    row = db.execute("SELECT * FROM recipes WHERE title = 'Brand New Dish'").fetchone()
    placeholder = row["image_filename"]

    client.post(f"/recipes/{row['id']}/image", data={"image": (_png_bytes(), "photo.png")},
                content_type="multipart/form-data")
    row = db.execute("SELECT * FROM recipes WHERE id = ?", (row["id"],)).fetchone()
    assert row["image_is_placeholder"] == 0
    with Image.open(cfg.IMAGES_DIR / row["image_filename"]) as im:
        assert im.size == (50, 50)  # the photo, not the 1600x1200 drawing
    if row["image_filename"] != placeholder:
        assert not (cfg.IMAGES_DIR / placeholder).exists()


# ---- the job ------------------------------------------------------------------

@needs_rsvg
def test_photo_added_while_drawing_wins(db, cfg):
    cfg.ensure_data_dirs()
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    rid = seed_recipe(db, title="Race")

    def draw(*args, **kwargs):
        db.execute("UPDATE recipes SET image_filename = 'recipe-1-photo.jpg' WHERE id = ?", (rid,))
        db.commit()
        return FAKE_SVG
    with patch.object(placeholders, "draw_placeholder_svg", draw):
        assert make_placeholder(db, cfg, rid) is None
    row = db.execute("SELECT * FROM recipes WHERE id = ?", (rid,)).fetchone()
    assert row["image_filename"] == "recipe-1-photo.jpg"
    assert row["image_is_placeholder"] == 0
    assert list(cfg.IMAGES_DIR.iterdir()) == []


def test_recipe_that_has_a_picture_is_skipped(db, cfg, fake_placeholder_drawing):
    rid = seed_recipe(db, title="Has One", image_filename="recipe-1-x.jpg")
    assert make_placeholder(db, cfg, rid) is None
    assert fake_placeholder_drawing == []


def test_failed_drawing_leaves_recipe_alone(db, cfg, capsys):
    cfg.ensure_data_dirs()
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    rid = seed_recipe(db, title="Unlucky")

    def draw(*args, **kwargs):
        raise PlaceholderError("The reply had no SVG in it.")
    with patch.object(placeholders, "draw_placeholder_svg", draw):
        assert placeholders.start_placeholder_job(cfg, [rid]) is True
    assert db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0] is None
    assert "Couldn't draw a placeholder picture for recipe" in capsys.readouterr().out


@needs_rsvg
def test_pdf_import_draws_placeholders_for_imported_recipes(client, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    db.execute("INSERT INTO import_batches (source_pdf, original_filename, status, created_at, updated_at) "
               "VALUES ('t.pdf', 't.pdf', 'ready', 'now', 'now')")
    for page, title in ((1, "First Import"), (2, "Second Import")):
        db.execute("INSERT INTO import_batch_recipes (batch_id, source_page, title) VALUES (1, ?, ?)", (page, title))
    db.commit()
    ids = [r[0] for r in db.execute("SELECT id FROM import_batch_recipes ORDER BY id")]
    form = {f"include_{i}": "1" for i in ids}
    resp = client.post("/admin/import/1/commit", data=form, follow_redirects=True)
    assert b"Placeholder pictures are being drawn" in resp.data
    assert fake_placeholder_drawing == ["First Import", "Second Import"]
    flags = [r[0] for r in db.execute("SELECT image_is_placeholder FROM recipes ORDER BY id")]
    assert flags == [1, 1]


# ---- prompt and SVG checks ------------------------------------------------------

def test_prompt_has_title_category_ingredients_and_plain_instructions():
    prompt = recipe_prompt("Snowballs", "Cookies", ["1 cup Crisco", "Powdered sugar"],
                           "<p>Roll in <strong>sugar</strong>.</p>")
    assert "Recipe: Snowballs" in prompt
    assert "Category: Cookies" in prompt
    assert "- 1 cup Crisco" in prompt
    assert "Roll in sugar ." in prompt
    assert "<strong>" not in prompt


def test_extract_svg_from_a_chatty_reply():
    assert extract_svg(f"Here you go:\n```svg\n{FAKE_SVG}\n```") == FAKE_SVG
    with pytest.raises(PlaceholderError):
        extract_svg("Sorry, no picture today.")


def test_plain_shapes_pass_the_check():
    assert check_svg(FAKE_SVG) == FAKE_SVG


@pytest.mark.parametrize("bad", [
    '<image href="file:///etc/passwd" width="10" height="10"/>',
    '<text x="10" y="10">Hi</text>',
    '<script>alert(1)</script>',
    '<use href="#a"/>',
    '<rect width="10" height="10" fill="url(#g)"/>',
    '<rect width="10" height="10" onload="x()"/>',
    '<foreignObject width="10" height="10"/>',
])
def test_anything_but_plain_shapes_is_rejected(bad):
    svg = FAKE_SVG.replace("</svg>", bad + "</svg>")
    with pytest.raises(PlaceholderError):
        check_svg(svg)


def test_doctype_is_rejected():
    with pytest.raises(PlaceholderError):
        check_svg('<!DOCTYPE svg [<!ENTITY x "y">]>' + FAKE_SVG)


def _client_replying(stop_reason, text=None):
    reply = MagicMock(stop_reason=stop_reason, content=[MagicMock(type="text", text=text)] if text else [])
    client = MagicMock()
    client.beta.messages.stream.return_value.__enter__.return_value.get_final_message.return_value = reply
    return client


def test_draw_asks_sonnet_with_cached_examples_and_fallbacks():
    client = _client_replying("end_turn", f"```svg\n{FAKE_SVG}\n```")
    with patch("app.placeholder_images.anthropic.Anthropic", return_value=client):
        svg = REAL_DRAW("Pie", "Pies", ["Eggs"], "", api_key="k", model="claude-sonnet-5-5")
    assert svg == FAKE_SVG
    kwargs = client.beta.messages.stream.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5"
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    assert kwargs["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert "Chocolate Chess Pie" in kwargs["system"][-1]["text"]


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_refused_or_cut_off_drawing_is_an_error(stop_reason):
    with patch("app.placeholder_images.anthropic.Anthropic", return_value=_client_replying(stop_reason, FAKE_SVG)):
        with pytest.raises(PlaceholderError):
            REAL_DRAW("Pie", None, [], "", api_key="k", model="m")


# ---- duplicates and migration -----------------------------------------------------

def test_merge_keeps_real_photo_over_placeholder(db):
    keep = seed_recipe(db, title="Soup", image_filename="recipe-1-drawn.jpg", image_is_placeholder=1)
    other = seed_recipe(db, title="Soup copy", image_filename="recipe-2-photo.jpg")
    orphaned = merge_recipes(db, keep, [other])
    row = db.execute("SELECT * FROM recipes WHERE id = ?", (keep,)).fetchone()
    assert row["image_filename"] == "recipe-2-photo.jpg"
    assert row["image_is_placeholder"] == 0
    assert ("image", "recipe-1-drawn.jpg") in orphaned


def test_migration_flags_the_first_drawn_set(tmp_path):
    from app.db import get_connection, run_migrations
    path = tmp_path / "old.db"
    run_migrations(path)
    conn = get_connection(path)
    conn.execute("DELETE FROM schema_version WHERE version = 6")
    conn.execute("ALTER TABLE recipes DROP COLUMN image_is_placeholder")
    for i, name in enumerate(("recipe-5-20261028180254.jpg", "recipe-6-20261023211548.jpg", None)):
        conn.execute("INSERT INTO recipes (title, image_filename, created_at, updated_at) VALUES (?, ?, 'now', 'now')",
                     (f"R{i}", name))
    conn.commit()
    conn.close()
    run_migrations(path)
    conn = get_connection(path)
    flags = [r[0] for r in conn.execute("SELECT image_is_placeholder FROM recipes ORDER BY id")]
    conn.close()
    assert flags == [1, 0, 0]


# ---- drawing a new picture on request -----------------------------------------------

def _existing_photo(cfg, name="recipe-1-photo.jpg"):
    cfg.ensure_data_dirs()
    Image.new("RGB", (50, 50)).save(cfg.IMAGES_DIR / name)
    Image.new("RGB", (50, 50)).save(cfg.IMAGES_DIR / thumb_filename(name))
    return name


@needs_rsvg
def test_redraw_replaces_a_real_photo(client, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    photo = _existing_photo(cfg)
    rid = seed_recipe(db, title="Swap Me", image_filename=photo)
    resp = client.post(f"/recipes/{rid}/image/draw", follow_redirects=True)
    assert b"A new picture is being drawn" in resp.data
    row = db.execute("SELECT * FROM recipes WHERE id = ?", (rid,)).fetchone()
    assert fake_placeholder_drawing == ["Swap Me"]
    assert row["image_filename"] != photo
    assert row["image_is_placeholder"] == 1
    assert not (cfg.IMAGES_DIR / photo).exists()
    assert not (cfg.IMAGES_DIR / thumb_filename(photo)).exists()


@needs_rsvg
def test_redraw_a_drawing_you_dont_like(client, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    old = _existing_photo(cfg, "recipe-1-drawn.jpg")
    rid = seed_recipe(db, title="Try Again", image_filename=old, image_is_placeholder=1)
    client.post(f"/recipes/{rid}/image/draw")
    row = db.execute("SELECT * FROM recipes WHERE id = ?", (rid,)).fetchone()
    assert row["image_filename"] != old
    assert row["image_is_placeholder"] == 1
    assert not (cfg.IMAGES_DIR / old).exists()


@needs_rsvg
def test_redraw_with_no_picture_yet(client, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    rid = seed_recipe(db, title="Bare")
    client.post(f"/recipes/{rid}/image/draw")
    assert db.execute("SELECT image_is_placeholder FROM recipes WHERE id = ?", (rid,)).fetchone()[0] == 1


@needs_rsvg
def test_redraw_leaves_a_photo_added_meanwhile(db, cfg):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    old = _existing_photo(cfg, "recipe-1-drawn.jpg")
    rid = seed_recipe(db, title="Race", image_filename=old, image_is_placeholder=1)

    def draw(*args, **kwargs):
        db.execute("UPDATE recipes SET image_filename = 'recipe-1-new-photo.jpg', image_is_placeholder = 0 WHERE id = ?", (rid,))
        db.commit()
        return FAKE_SVG
    with patch.object(placeholders, "draw_placeholder_svg", draw):
        assert make_placeholder(db, cfg, rid, replacing=old) is None
    row = db.execute("SELECT * FROM recipes WHERE id = ?", (rid,)).fetchone()
    assert row["image_filename"] == "recipe-1-new-photo.jpg"
    assert sorted(p.name for p in cfg.IMAGES_DIR.iterdir()) == sorted([old, thumb_filename(old)])


def test_only_owner_or_admin_can_redraw(member, db, cfg, fake_placeholder_drawing):
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    rid = seed_recipe(db, title="Not Yours", image_filename="recipe-1-photo.jpg")
    assert member.post(f"/recipes/{rid}/image/draw").status_code == 403
    assert fake_placeholder_drawing == []


def test_redraw_button_shows_only_with_a_key(client, db, cfg):
    rid = seed_recipe(db, title="Buttons", image_filename="recipe-1-photo.jpg")
    assert b"new AI drawing" not in client.get(f"/recipes/{rid}").data
    assert b"new AI drawing" not in client.get(f"/recipes/{rid}/edit").data
    cfg.ANTHROPIC_API_KEY = "test-key-not-real"
    assert b"Replace with a new AI drawing" in client.get(f"/recipes/{rid}").data
    assert b"Replace with a new AI drawing" in client.get(f"/recipes/{rid}/edit").data


def test_redraw_without_a_key_says_so(client, db, cfg, fake_placeholder_drawing):
    rid = seed_recipe(db, title="No Key")
    resp = client.post(f"/recipes/{rid}/image/draw", follow_redirects=True)
    assert b"ANTHROPIC_API_KEY isn" in resp.data
    assert fake_placeholder_drawing == []
