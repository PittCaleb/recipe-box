import pytest

from app import create_app
from tests.conftest import seed_recipe, sync_fts


@pytest.fixture
def protected_app(cfg):
    cfg.APP_PASSWORD = "sesame"
    return create_app(cfg)


@pytest.fixture
def protected_client(protected_app):
    return protected_app.test_client()


def test_browse_and_view_open_without_login(protected_client, db):
    rid = seed_recipe(db, title="Open Recipe")
    sync_fts(db, rid, "Open Recipe")
    assert protected_client.get("/").status_code == 200
    assert protected_client.get(f"/recipes/{rid}").status_code == 200


def test_edit_requires_login_when_password_set(protected_client, db):
    resp = protected_client.get("/recipes/new")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_requires_login_when_password_set(protected_client):
    resp = protected_client.get("/admin/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_wrong_password_rejected(protected_client):
    resp = protected_client.post("/login", data={"password": "nope"})
    assert resp.status_code == 200
    assert b"Incorrect password" in resp.data


def test_correct_password_grants_access(protected_client):
    resp = protected_client.post("/login", data={"password": "sesame"}, follow_redirects=True)
    assert resp.status_code == 200
    assert protected_client.get("/recipes/new").status_code == 200
    assert protected_client.get("/admin/").status_code == 200


def test_logout_revokes_access(protected_client):
    protected_client.post("/login", data={"password": "sesame"})
    assert protected_client.get("/recipes/new").status_code == 200
    protected_client.post("/logout")
    resp = protected_client.get("/recipes/new")
    assert resp.status_code == 302


def test_no_password_means_fully_open(client):
    assert client.get("/recipes/new").status_code == 200
    assert client.get("/admin/").status_code == 200
