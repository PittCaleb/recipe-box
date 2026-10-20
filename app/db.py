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
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)


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
            sql = path.read_text()
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, datetime.now().isoformat(timespec="seconds")),
            )
            conn.commit()
    finally:
        conn.close()
