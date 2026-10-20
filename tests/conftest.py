from datetime import datetime

import pytest

from app import create_app
from app.db import get_connection
from config import Config


@pytest.fixture
def cfg(tmp_path):
    c = Config()
    c.DATA_DIR = tmp_path / "data"
    return c


@pytest.fixture
def app(cfg):
    return create_app(cfg)


@pytest.fixture
def client(app):
    return app.test_client()


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
        "favorite": 0,
        "rating": None,
        "last_made": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" for _ in defaults)
    cur = conn.execute(
        f"INSERT INTO recipes ({cols}) VALUES ({placeholders})",
        list(defaults.values()),
    )
    conn.commit()
    return cur.lastrowid


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
