"""Behind the NAS reverse proxy the app is served at /recipes; the proxy
sends X-Forwarded-Prefix and every generated link must include it."""
from tests.conftest import seed_recipe, sync_fts

PREFIX = {"X-Forwarded-Prefix": "/recipes"}


def test_links_include_prefix(client, db):
    rid = seed_recipe(db, title="Prefixed Pie")
    sync_fts(db, rid, "Prefixed Pie")
    html = client.get("/", headers=PREFIX).get_data(as_text=True)
    assert 'href="/recipes/static/' in html
    assert f'href="/recipes/recipes/{rid}"' in html
    assert 'data-search-url="/recipes/api/search"' in html

    page = client.get(f"/recipes/{rid}", headers=PREFIX).get_data(as_text=True)
    assert f'action="/recipes/recipes/{rid}/favorite"' in page


def test_redirects_include_prefix(client, db):
    rid = seed_recipe(db, title="Prefixed Pie")
    resp = client.post(f"/recipes/{rid}/favorite", headers=PREFIX)
    assert resp.headers["Location"].startswith("/recipes/")


def test_no_prefix_when_run_directly(client, db):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/static/' in html


def test_session_cookie_name_is_app_specific(app):
    assert app.config["SESSION_COOKIE_NAME"] == "recipes_session"
