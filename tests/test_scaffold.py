from app import create_app
from app.db import get_connection, run_migrations


def test_migrations_create_expected_tables(cfg):
    cfg.ensure_data_dirs()
    run_migrations(cfg.DB_PATH)
    conn = get_connection(cfg.DB_PATH)
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    conn.close()
    for expected in ("schema_version", "categories", "recipes", "ingredients", "notes"):
        assert expected in tables


def test_migrations_are_idempotent(cfg):
    cfg.ensure_data_dirs()
    run_migrations(cfg.DB_PATH)
    run_migrations(cfg.DB_PATH)  # should not raise or duplicate


def test_foreign_keys_and_wal_enabled(cfg):
    cfg.ensure_data_dirs()
    run_migrations(cfg.DB_PATH)
    conn = get_connection(cfg.DB_PATH)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    conn.close()


def test_app_factory_serves_index(cfg):
    app = create_app(cfg)
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Recipes" in resp.data
