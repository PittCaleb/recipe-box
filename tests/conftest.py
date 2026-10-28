import time
from datetime import datetime

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import create_app
from app.db import get_connection
from config import Config


@pytest.fixture
def cfg(tmp_path):
    c = Config()
    c.PDF_DIR = tmp_path / "pdf"
    c.DATA_DIR = tmp_path / "data"
    # A key in .env must never reach the tests; ones that need it set their own.
    c.ANTHROPIC_API_KEY = None
    return c


FAKE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1200" width="1600" height="1200">'
    '<rect width="1600" height="1200" fill="#8c5a3c"/><ellipse cx="800" cy="600" rx="500" ry="320" fill="#f6f1ea"/></svg>'
)


@pytest.fixture(autouse=True)
def fake_placeholder_drawing(monkeypatch):
    """Placeholder pictures are drawn inline from a fixed SVG, never by Claude.
    The list records each recipe title that was drawn."""
    import app.placeholder_images as placeholders
    drawn = []

    def draw(title, *args, **kwargs):
        drawn.append(title)
        return FAKE_SVG
    monkeypatch.setattr(placeholders, "RUN_IN_BACKGROUND", False)
    monkeypatch.setattr(placeholders, "draw_placeholder_svg", draw)
    return drawn


ACCESS_TEAM = "team.example.com"
ACCESS_AUD = "test-aud"
PUBLIC_HOST = "recipes.example.com"
_ACCESS_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def access_token(email, aud=ACCESS_AUD, issuer=f"https://{ACCESS_TEAM}", key=_ACCESS_KEY, expires_in=600):
    """A Cloudflare Access style token, signed by the test key."""
    claims = {"email": email, "aud": [aud], "iss": issuer, "exp": int(time.time()) + expires_in}
    return jwt.encode(claims, key, algorithm="RS256")


@pytest.fixture(autouse=True)
def access_keys(monkeypatch):
    """Token signatures check against the test key instead of fetching
    Cloudflare's."""
    import app.users
    monkeypatch.setattr(app.users, "_signing_key", lambda token, team: _ACCESS_KEY.public_key())


@pytest.fixture
def app(cfg):
    cfg.ACCESS_TEAM_DOMAIN = ACCESS_TEAM
    cfg.ACCESS_AUD = ACCESS_AUD
    return create_app(cfg)


@pytest.fixture
def client(app):
    """A home-network visitor: no sign-in, acts as user 1 (the admin)."""
    return app.test_client()


@pytest.fixture
def signed_in(app):
    """signed_in("pat@example.com") is a client for someone who came in
    through the public address and signed in with that email."""
    def make(email):
        c = app.test_client()
        c.environ_base["HTTP_X_FORWARDED_HOST"] = PUBLIC_HOST
        c.environ_base["HTTP_CF_ACCESS_JWT_ASSERTION"] = access_token(email)
        return c
    return make


@pytest.fixture
def member(signed_in):
    """A regular (non-admin) user."""
    return signed_in("pat@example.com")


@pytest.fixture
def db(cfg):
    cfg.ensure_data_dirs()
    from app.db import run_migrations
    run_migrations(cfg.DB_PATH)
    conn = get_connection(cfg.DB_PATH)
    yield conn
    conn.close()


def seed_recipe(conn, **overrides):
    now = datetime.now().isoformat(timespec="seconds")
    defaults = {
        "title": "Test Recipe",
        "category_id": None,
        "contributor": None,
        "source": None,
        "servings": None,
        "prep_time": None,
        "cook_time": None,
        "instructions_html": "<p>Do the thing.</p>",
        "image_filename": None,
        "scan_filename": None,
        "source_pdf": None,
        "source_page": None,
        "needs_review": 0,
        "owner_id": 1,
        "created_at": now,
        "updated_at": now,
    }
    # favorite / rating / last_made are user 1's own.
    personal = {k: overrides.pop(k) for k in ("favorite", "rating", "last_made") if k in overrides}
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" for _ in defaults)
    cur = conn.execute(
        f"INSERT INTO recipes ({cols}) VALUES ({placeholders})",
        list(defaults.values()),
    )
    if personal:
        seed_personal(conn, cur.lastrowid, **personal)
    conn.commit()
    return cur.lastrowid


def seed_personal(conn, recipe_id, user_id=1, favorite=0, rating=None, last_made=None):
    conn.execute(
        "INSERT OR REPLACE INTO user_recipes (user_id, recipe_id, favorite, rating, last_made) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, recipe_id, favorite, rating, last_made),
    )
    conn.commit()


def seed_ingredient(conn, recipe_id, position, raw_text, kind="item", **overrides):
    defaults = {
        "recipe_id": recipe_id,
        "position": position,
        "kind": kind,
        "raw_text": raw_text,
        "is_split": 0,
        "quantity": None,
        "quantity_max": None,
        "unit": None,
        "item": None,
        "no_scale": 0,
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" for _ in defaults)
    conn.execute(
        f"INSERT INTO ingredients ({cols}) VALUES ({placeholders})",
        list(defaults.values()),
    )
    conn.commit()


def sync_fts(conn, recipe_id, title, category_name="", contributor="", ingredients_text=""):
    conn.execute(
        "INSERT INTO recipes_fts (rowid, title, category_name, contributor, ingredients_text) "
        "VALUES (?, ?, ?, ?, ?)",
        (recipe_id, title, category_name, contributor, ingredients_text),
    )
    conn.commit()
