def list_categories(conn):
    return conn.execute(
        "SELECT id, name, sort_order, "
        "(SELECT COUNT(*) FROM recipes WHERE recipes.category_id = categories.id) AS recipe_count "
        "FROM categories ORDER BY sort_order, name COLLATE NOCASE"
    ).fetchall()


def add_category(conn, name):
    name = name.strip()
    if not name:
        return None
    max_sort = conn.execute("SELECT COALESCE(MAX(sort_order), -1) FROM categories").fetchone()[0]
    with conn:
        cur = conn.execute(
            "INSERT INTO categories (name, sort_order) VALUES (?, ?)", (name, max_sort + 1)
        )
    return cur.lastrowid


def rename_category(conn, category_id, name):
    name = name.strip()
    if not name:
        return
    with conn:
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))


def delete_category(conn, category_id):
    with conn:
        conn.execute("UPDATE recipes SET category_id = NULL WHERE category_id = ?", (category_id,))
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))


def move_category(conn, category_id, direction):
    rows = conn.execute("SELECT id, sort_order FROM categories ORDER BY sort_order").fetchall()
    ids = [r["id"] for r in rows]
    if category_id not in ids:
        return
    idx = ids.index(category_id)
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if swap_idx < 0 or swap_idx >= len(ids):
        return
    a, b = rows[idx], rows[swap_idx]
    with conn:
        conn.execute("UPDATE categories SET sort_order = ? WHERE id = ?", (b["sort_order"], a["id"]))
        conn.execute("UPDATE categories SET sort_order = ? WHERE id = ?", (a["sort_order"], b["id"]))
