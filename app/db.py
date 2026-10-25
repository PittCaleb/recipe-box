import importlib.util
import sqlite3
from datetime import datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _applied_versions(conn):
    try:
        rows = conn.execute("SELECT version FROM schema_version").fetchall()
        return {row["version"] for row in rows}
    except sqlite3.OperationalError:
        return set()


def _migration_files():
    # .py migrations are for data fixes SQL can't express; each defines
    # migrate(conn) and must not commit (the runner does).
    files = [*MIGRATIONS_DIR.glob("*.sql"), *MIGRATIONS_DIR.glob("[0-9]*.py")]
    return sorted(files, key=lambda p: p.name)


def _run_python_migration(conn, path):
    spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(conn)


def run_migrations(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    try:
        applied = _applied_versions(conn)
        for path in _migration_files():
            version = int(path.name.split("_", 1)[0])
            if version in applied:
                continue
            if path.suffix == ".py":
                _run_python_migration(conn, path)
            else:
                conn.executescript(path.read_text())
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, datetime.now().isoformat(timespec="seconds")),
            )
            conn.commit()
    finally:
        conn.close()
