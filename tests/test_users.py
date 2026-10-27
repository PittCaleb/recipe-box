"""Who someone is (Cloudflare Access sign-in, or the home network), and
what each kind of person may do."""
import sqlite3

from app.db import _migration_files, _run_python_migration, get_connection, run_migrations
from tests.conftest import (
    ACCESS_TEAM, PUBLIC_HOST, access_token, seed_ingredient, seed_personal, seed_recipe, sync_fts,
)


def _recipe(db, title="Pie", **kw):
    rid = seed_recipe(db, title=title, **kw)
    seed_ingredient(db, rid, 0, "1 cup flour", is_split=1, quantity=1, unit="cup", item="flour")
    sync_fts(db, rid, title, ingredients_text="1 cup flour")
    return rid


def _user_id(db, email):
    return db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]


def _form(title="Pie"):
    return {
        "title": title, "instructions_html": "<p>Bake.</p>",
        "ingredient_kind": ["item"], "ingredient_quantity": ["1"], "ingredient_quantity_max": [""],
        "ingredient_unit": ["cup"], "ingredient_item": ["flour"], "ingredient_no_scale": ["0"],
    }


# --- Migration ---

def test_migration_gives_existing_recipes_and_history_to_user_1(cfg):
    cfg.ensure_data_dirs()
    conn = get_connection(cfg.DB_PATH)
    for path in _migration_files():
        version = int(path.name.split("_", 1)[0])
        if version >= 5:
            break
        if path.suffix == ".py":
            _run_python_migration(conn, path)
        else:
            conn.executescript(path.read_text())
        conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, 'x')", (version,))
    conn.execute(
        "INSERT INTO recipes (id, title, favorite, rating, last_made, created_at, updated_at) "
        "VALUES (7, 'Old Fudge', 1, 4, '2026-01-02', 'x', 'x'), (8, 'Plain', 0, NULL, NULL, 'x', 'x')"
    )
    conn.execute("INSERT INTO notes (recipe_id, body, created_at) VALUES (7, 'Good', 'x')")
    conn.commit()
    conn.close()

    run_migrations(cfg.DB_PATH)

    conn = get_connection(cfg.DB_PATH)
    user = conn.execute("SELECT * FROM users WHERE id = 1").fetchone()
    assert (user["email"], user["is_admin"]) == ("caleb@hail2pitt.org", 1)
    assert [r["owner_id"] for r in conn.execute("SELECT owner_id FROM recipes")] == [1, 1]
    assert conn.execute("SELECT author_id FROM notes").fetchone()["author_id"] == 1
    personal = conn.execute("SELECT * FROM user_recipes").fetchall()
    assert [tuple(r) for r in personal] == [(1, 7, 1, 4, "2026-01-02")]
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(recipes)")}
    assert not columns & {"favorite", "rating", "last_made"}
    conn.close()


# --- Who is visiting ---

def test_home_visitor_is_the_admin(client, db):
    html = client.get("/").data.decode()
    assert "Welcome caleb<" in html
    assert "/admin/" in html


def test_first_signed_in_visit_creates_a_regular_user(member, db):
    resp = member.get("/")
    assert resp.status_code == 200
    assert b"Welcome pat<" in resp.data
    row = db.execute("SELECT * FROM users WHERE email = 'pat@example.com'").fetchone()
    assert (row["display_name"], row["is_admin"]) == ("Pat", 0)
    member.get("/")
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2


def test_email_case_does_not_make_a_second_user(signed_in, db):
    signed_in("Pat@Example.com").get("/")
    signed_in("pat@example.com").get("/")
    assert db.execute("SELECT COUNT(*) FROM users WHERE email LIKE 'pat@%'").fetchone()[0] == 1


def test_promoted_user_gets_admin(signed_in, db):
    signed_in("pat@example.com").get("/")
    db.execute("UPDATE users SET is_admin = 1 WHERE email = 'pat@example.com'")
    db.commit()
    assert signed_in("pat@example.com").get("/admin/").status_code == 200


def test_public_address_without_a_token_is_refused(app):
    c = app.test_client()
    resp = c.get("/", headers={"X-Forwarded-Host": PUBLIC_HOST})
    assert resp.status_code == 403
    assert b"sign in" in resp.data


def test_email_header_alone_is_not_trusted(app, db):
    c = app.test_client()
    headers = {"X-Forwarded-Host": PUBLIC_HOST, "Cf-Access-Authenticated-User-Email": "caleb@hail2pitt.org"}
    assert c.get("/", headers=headers).status_code == 403


def test_bad_tokens_are_refused(app, db):
    from cryptography.hazmat.primitives.asymmetric import rsa
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad = [
        "not-a-token",
        access_token("pat@example.com", aud="some-other-app"),
        access_token("pat@example.com", issuer="https://evil.example.com"),
        access_token("pat@example.com", expires_in=-60),
        access_token("pat@example.com", key=other_key),
    ]
    for token in bad:
        resp = app.test_client().get("/", headers={"X-Forwarded-Host": PUBLIC_HOST, "Cf-Access-Jwt-Assertion": token})
        assert resp.status_code == 403, token
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


def test_forged_token_on_home_network_is_refused_not_ignored(app, db):
    resp = app.test_client().get("/", headers={"Cf-Access-Jwt-Assertion": "forged"})
    assert resp.status_code == 403


def test_tokens_refused_when_access_not_configured(cfg, db):
    from app import create_app
    cfg.ACCESS_AUD = None
    c = create_app(cfg).test_client()
    resp = c.get("/", headers={"X-Forwarded-Host": PUBLIC_HOST,
                               "Cf-Access-Jwt-Assertion": access_token("pat@example.com")})
    assert resp.status_code == 403


def test_static_files_need_no_sign_in(app):
    resp = app.test_client().get("/static/css/main.css", headers={"X-Forwarded-Host": PUBLIC_HOST})
    assert resp.status_code == 200


def test_signing_keys_come_from_the_team_domain(monkeypatch):
    import app.users
    monkeypatch.undo()
    urls = []

    class FakeClient:
        def __init__(self, url):
            urls.append(url)

        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": "k"})()

    monkeypatch.setattr(app.users.jwt, "PyJWKClient", FakeClient)
    monkeypatch.setattr(app.users, "_jwks_clients", {})
    assert app.users._signing_key("t", ACCESS_TEAM) == "k"
    app.users._signing_key("t", ACCESS_TEAM)
    assert urls == [f"https://{ACCESS_TEAM}/cdn-cgi/access/certs"]


# --- What a regular user may do ---

def test_member_can_read_everything(member, db):
    rid = _recipe(db)
    assert member.get("/").status_code == 200
    assert member.get(f"/recipes/{rid}").status_code == 200
    assert member.get("/admin/cookbook").status_code == 200


def test_member_sees_no_admin_menu(member, db):
    html = member.get("/").data.decode()
    assert "New recipe" in html
    assert "Print cookbook" in html
    assert "Import a PDF" not in html
    assert "admin-submenu" not in html
    for path in ("/admin/", "/admin/categories", "/admin/needs-review", "/admin/export",
                 "/admin/duplicates/", "/admin/import/"):
        assert member.get(path).status_code == 403, path


def test_member_can_add_a_recipe_and_owns_it(member, db):
    resp = member.post("/recipes/new", data=_form("Pat's Pie"))
    assert resp.status_code == 302
    row = db.execute("SELECT * FROM recipes WHERE title = ?", ("Pat's Pie",)).fetchone()
    assert row["owner_id"] == _user_id(db, "pat@example.com")
    html = member.get(f"/recipes/{row['id']}").data.decode()
    assert "Added by Pat" in html


def test_member_can_edit_own_recipe_but_not_delete_it(member, db):
    member.post("/recipes/new", data=_form("Pat's Pie"))
    rid = db.execute("SELECT id FROM recipes WHERE title = ?", ("Pat's Pie",)).fetchone()["id"]

    html = member.get(f"/recipes/{rid}").data.decode()
    assert f"/recipes/{rid}/edit" in html
    assert "Delete recipe" not in html
    assert member.get(f"/recipes/{rid}/edit").status_code == 200
    assert "Delete recipe" not in member.get(f"/recipes/{rid}/edit").data.decode()

    assert member.post(f"/recipes/{rid}", data=_form("Pat's Better Pie")).status_code == 302
    assert db.execute("SELECT title FROM recipes WHERE id = ?", (rid,)).fetchone()["title"] == "Pat's Better Pie"

    assert member.post(f"/recipes/{rid}/delete").status_code == 403
    assert db.execute("SELECT COUNT(*) FROM recipes WHERE id = ?", (rid,)).fetchone()[0] == 1


def test_member_cannot_edit_or_delete_someone_elses_recipe(member, db):
    rid = _recipe(db, "Caleb's Pie")
    html = member.get(f"/recipes/{rid}").data.decode()
    assert f"/recipes/{rid}/edit" not in html
    assert "Added by Caleb" in html
    assert member.get(f"/recipes/{rid}/edit").status_code == 403
    assert member.post(f"/recipes/{rid}", data=_form("Hijacked")).status_code == 403
    assert member.post(f"/recipes/{rid}/delete").status_code == 403
    assert db.execute("SELECT title FROM recipes WHERE id = ?", (rid,)).fetchone()["title"] == "Caleb's Pie"


def test_member_cannot_set_needs_review(member, db):
    member.post("/recipes/new", data={**_form("Flagged?"), "needs_review": "1"})
    assert db.execute("SELECT needs_review FROM recipes WHERE title = 'Flagged?'").fetchone()[0] == 0


def test_owner_edit_keeps_admins_needs_review_flag(member, db):
    member.post("/recipes/new", data=_form("Pat's Pie"))
    rid = db.execute("SELECT id FROM recipes WHERE title = ?", ("Pat's Pie",)).fetchone()["id"]
    db.execute("UPDATE recipes SET needs_review = 1 WHERE id = ?", (rid,))
    db.commit()
    member.post(f"/recipes/{rid}", data=_form("Pat's Pie"))
    assert db.execute("SELECT needs_review FROM recipes WHERE id = ?", (rid,)).fetchone()[0] == 1


def test_admin_can_edit_and_delete_anyones_recipe(client, member, db):
    member.post("/recipes/new", data=_form("Pat's Pie"))
    rid = db.execute("SELECT id FROM recipes WHERE title = ?", ("Pat's Pie",)).fetchone()["id"]
    assert client.get(f"/recipes/{rid}/edit").status_code == 200
    assert client.post(f"/recipes/{rid}/delete").status_code == 302
    assert db.execute("SELECT COUNT(*) FROM recipes WHERE id = ?", (rid,)).fetchone()[0] == 0


# --- Notes and photos ---

def test_member_notes_and_who_may_delete_them(client, member, db):
    rid = _recipe(db)
    client.post(f"/recipes/{rid}/notes", data={"body": "Caleb's note"})
    member.post(f"/recipes/{rid}/notes", data={"body": "Pat's note"})
    notes = {r["body"]: r for r in db.execute("SELECT * FROM notes WHERE recipe_id = ?", (rid,))}
    assert notes["Pat's note"]["author_id"] == _user_id(db, "pat@example.com")

    html = member.get(f"/recipes/{rid}").data.decode()
    assert "Pat&#39;s note" in html and "&middot; Pat" in html
    assert html.count("Delete this note?") == 1

    caleb_note = notes["Caleb's note"]["id"]
    pat_note = notes["Pat's note"]["id"]
    assert member.post(f"/recipes/{rid}/notes/{caleb_note}/delete").status_code == 403
    assert member.post(f"/recipes/{rid}/notes/{pat_note}/delete").status_code == 302
    assert client.post(f"/recipes/{rid}/notes/{caleb_note}/delete").status_code == 302
    assert db.execute("SELECT COUNT(*) FROM notes WHERE recipe_id = ?", (rid,)).fetchone()[0] == 0


def test_owner_editing_cannot_rewrite_other_peoples_notes(client, member, db):
    member.post("/recipes/new", data=_form("Pat's Pie"))
    rid = db.execute("SELECT id FROM recipes WHERE title = ?", ("Pat's Pie",)).fetchone()["id"]
    client.post(f"/recipes/{rid}/notes", data={"body": "Caleb's note"})
    note_id = db.execute("SELECT id FROM notes WHERE recipe_id = ?", (rid,)).fetchone()["id"]

    assert f"note_body_{note_id}" not in member.get(f"/recipes/{rid}/edit").data.decode()
    member.post(f"/recipes/{rid}", data={**_form("Pat's Pie"), f"note_body_{note_id}": "rewritten"})
    assert db.execute("SELECT body FROM notes WHERE id = ?", (note_id,)).fetchone()["body"] == "Caleb's note"


def test_photo_add_open_to_all_but_removal_is_owner_or_admin(member, db, cfg):
    rid = _recipe(db, image_filename="caleb.jpg")
    html = member.get(f"/recipes/{rid}").data.decode()
    assert "Replace image" in html
    assert "Remove image" not in html
    assert member.post(f"/recipes/{rid}/image/delete").status_code == 403
    assert db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0] == "caleb.jpg"
    # Upload goes through (an empty upload just returns to the recipe).
    assert member.post(f"/recipes/{rid}/image", data={}).status_code == 302


# --- Personal favorites, ratings, and "I made this" ---

def test_favorites_and_made_are_per_person(client, member, db):
    rid = _recipe(db, favorite=1, last_made="2026-01-02")

    html = member.get(f"/recipes/{rid}").data.decode()
    assert 'aria-label="Add to favorites"' in html
    assert "You last made this" not in html
    assert b"Pie" not in member.get("/api/search?favorites=1").data

    member.post(f"/recipes/{rid}/favorite")
    member.post(f"/recipes/{rid}/made")
    assert b"Pie" in member.get("/api/search?favorites=1").data
    assert "You last made this" in member.get(f"/recipes/{rid}").data.decode()

    client.post(f"/recipes/{rid}/favorite")  # Caleb un-hearts; Pat's stays.
    assert b"Pie" not in client.get("/api/search?favorites=1").data
    assert b"Pie" in member.get("/api/search?favorites=1").data
    assert "Jan 2, 2026" in client.get(f"/recipes/{rid}").data.decode()


def test_recently_made_sort_uses_your_own_dates(member, db):
    _recipe(db, "Apple", last_made="2026-05-05")  # Caleb made it; Pat never has.
    banana = _recipe(db, "Banana")
    member.get("/")
    seed_personal(db, banana, user_id=_user_id(db, "pat@example.com"), last_made="2026-01-01")
    html = member.get("/api/search?sort=recent_made").data.decode()
    assert html.index("Banana") < html.index("Apple")


def test_rating_is_per_person_and_clicking_again_clears_it(client, member, db):
    rid = _recipe(db, rating=5)
    member.post(f"/recipes/{rid}/rating", data={"rating": "3"})
    pat = _user_id(db, "pat@example.com")
    rating = lambda uid: db.execute(
        "SELECT rating FROM user_recipes WHERE recipe_id = ? AND user_id = ?", (rid, uid)
    ).fetchone()["rating"]
    assert (rating(1), rating(pat)) == (5, 3)
    assert 'aria-label="Clear your rating"' in member.get(f"/recipes/{rid}").data.decode()
    member.post(f"/recipes/{rid}/rating", data={"rating": "3"})
    assert rating(pat) is None
    assert member.post(f"/recipes/{rid}/rating", data={"rating": "9"}).status_code == 400


# --- Admin-only worklist ---

def test_worklist_chips_and_flags_are_admin_only(client, member, db):
    _recipe(db, "Flagged", needs_review=1)
    assert 'name="needs_review"' in client.get("/").data.decode()
    html = member.get("/").data.decode()
    assert 'name="needs_review"' not in html
    assert 'name="needs_split"' not in html
    assert "Needs review" not in html
    # The filter itself is ignored for regular users.
    _recipe(db, "Unflagged")
    assert b"Unflagged" in member.get("/api/search?needs_review=1").data
