from unittest.mock import patch

import pytest

from app.sharing.base import ShareResult, SharingBackend
from app.sharing.validate import validate_email, validate_imessage_target
from tests.conftest import seed_ingredient, seed_recipe, sync_fts


class FakeBackend(SharingBackend):
    def __init__(self, email_ok=True, imessage_ok=True):
        self.email_ok = email_ok
        self.imessage_ok = imessage_ok
        self.sent_emails = []
        self.sent_imessages = []

    def supports_email(self):
        return True

    def supports_imessage(self):
        return True

    def send_email(self, to, subject, body, attachment_path):
        self.sent_emails.append((to, subject, body, attachment_path))
        return ShareResult(self.email_ok, "Sent." if self.email_ok else "Mail.app refused.")

    def send_imessage(self, to, body, attachment_path):
        self.sent_imessages.append((to, body, attachment_path))
        return ShareResult(self.imessage_ok, "Sent." if self.imessage_ok else "Messages refused.")


# --- Validation ---

@pytest.mark.parametrize("value,expected", [
    ("caleb@example.com", "caleb@example.com"),
    ("  caleb@example.com  ", "caleb@example.com"),
    ("not-an-email", None),
    ("missing@domain", None),
    ("", None),
    (None, None),
])
def test_validate_email(value, expected):
    assert validate_email(value) == expected


@pytest.mark.parametrize("value,valid", [
    ("caleb@example.com", True),
    ("555-123-4567", True),
    ("+1 (555) 123-4567", True),
    ("5551234567", True),
    ("123", False),
    ("not a phone or email", False),
    ("", False),
])
def test_validate_imessage_target(value, valid):
    assert (validate_imessage_target(value) is not None) == valid


# --- PDF download ---

def test_download_pdf(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Printable Pie", instructions_html="<p>Bake it.</p>")
    seed_ingredient(db, rid, 0, "1 cup flour")
    sync_fts(db, rid, "Printable Pie")

    resp = client.get(f"/recipes/{rid}/pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:4] == b"%PDF"
    assert "Printable-Pie" in resp.headers["Content-Disposition"]


def test_download_pdf_404_for_missing_recipe(client, db, cfg):
    cfg.ensure_data_dirs()
    assert client.get("/recipes/9999/pdf").status_code == 404


# --- Email route ---

def test_email_requires_valid_address(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Emailable")
    sync_fts(db, rid, "Emailable")

    resp = client.post(f"/recipes/{rid}/email", data={"to": "not-an-email"})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_email_sends_via_backend(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Emailable Two")
    sync_fts(db, rid, "Emailable Two")

    fake = FakeBackend()
    with patch("app.routes.share.get_backend", return_value=fake):
        resp = client.post(
            f"/recipes/{rid}/email",
            data={"to": "owner@example.com", "message": "Try this one"},
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert len(fake.sent_emails) == 1
    to, subject, message, attachment = fake.sent_emails[0]
    assert to == "owner@example.com"
    assert subject == "Recipe: Emailable Two"
    assert message == "Try this one"
    assert str(attachment).endswith(".pdf")


def test_email_reports_backend_failure(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Emailable Three")
    sync_fts(db, rid, "Emailable Three")

    fake = FakeBackend(email_ok=False)
    with patch("app.routes.share.get_backend", return_value=fake):
        resp = client.post(f"/recipes/{rid}/email", data={"to": "owner@example.com"})
    body = resp.get_json()
    assert body["success"] is False
    assert "refused" in body["message"]


def test_email_unsupported_backend(client, db, cfg):
    cfg.ensure_data_dirs()
    cfg.SHARE_BACKEND = "none"
    rid = seed_recipe(db, title="No Backend")
    sync_fts(db, rid, "No Backend")
    resp = client.post(f"/recipes/{rid}/email", data={"to": "owner@example.com"})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


# --- Text route ---

def test_text_requires_valid_target(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Textable")
    sync_fts(db, rid, "Textable")
    fake = FakeBackend()
    with patch("app.routes.share.get_backend", return_value=fake):
        resp = client.post(f"/recipes/{rid}/text", data={"to": "nope"})
    assert resp.status_code == 400
    assert len(fake.sent_imessages) == 0


def test_text_sends_via_backend(client, db, cfg):
    cfg.ensure_data_dirs()
    rid = seed_recipe(db, title="Textable Two")
    seed_ingredient(db, rid, 0, "1 cup flour")
    sync_fts(db, rid, "Textable Two")

    fake = FakeBackend()
    with patch("app.routes.share.get_backend", return_value=fake):
        resp = client.post(f"/recipes/{rid}/text", data={"to": "555-123-4567"})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    assert len(fake.sent_imessages) == 1
    to, message, attachment = fake.sent_imessages[0]
    assert to == "555-123-4567"
    assert str(attachment).endswith(".jpg")


# --- Recipe view button visibility ---

def test_share_buttons_hidden_when_backend_unsupported(client, db, cfg):
    cfg.ensure_data_dirs()
    cfg.SHARE_BACKEND = "none"
    rid = seed_recipe(db, title="Buttons Hidden")
    sync_fts(db, rid, "Buttons Hidden")
    resp = client.get(f"/recipes/{rid}")
    assert b'data-open-modal="email-modal"' not in resp.data
    assert b'data-open-modal="text-modal"' not in resp.data
    assert b"Save PDF" in resp.data
