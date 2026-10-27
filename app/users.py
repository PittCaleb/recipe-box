"""Who is making this request, and what they may do.

Through the public address, Cloudflare Access signs people in and adds a
signed token (the Cf-Access-Jwt-Assertion header) to every request. The
email comes from that token after checking its signature, issuer, and
audience. The plain Cf-Access-Authenticated-User-Email header is never
trusted: anyone on the home network could send it.

Requests to a home address (RECIPES_HOME_HOSTS) have no sign-in and act as
user 1, the owner. Any other request without a valid token is refused.
"""
from datetime import datetime

import jwt
from flask import abort, current_app, g, request

from app import get_db

HOME_USER_ID = 1
ADMIN_BLUEPRINTS = {"admin", "import_pdf", "duplicates"}
# Print cookbook lives under /admin but only reads recipes, so everyone gets it.
OPEN_ADMIN_ENDPOINTS = {"admin.cookbook", "admin.cookbook_build"}

_jwks_clients = {}


def _signing_key(token, team_domain):
    client = _jwks_clients.get(team_domain)
    if client is None:
        client = jwt.PyJWKClient(f"https://{team_domain}/cdn-cgi/access/certs")
        _jwks_clients[team_domain] = client
    return client.get_signing_key_from_jwt(token).key


def access_email(token, cfg):
    """The signed-in email from a Cloudflare Access token, or None if the
    token isn't valid for this app."""
    if not (cfg.ACCESS_TEAM_DOMAIN and cfg.ACCESS_AUD):
        current_app.logger.warning("Got an Access token, but RECIPES_ACCESS_TEAM_DOMAIN/AUD aren't set")
        return None
    try:
        claims = jwt.decode(
            token, _signing_key(token, cfg.ACCESS_TEAM_DOMAIN), algorithms=["RS256"],
            audience=cfg.ACCESS_AUD, issuer=f"https://{cfg.ACCESS_TEAM_DOMAIN}",
            options={"require": ["exp", "email"]},
        )
    except jwt.PyJWTError as exc:
        current_app.logger.warning("Rejected Access token: %s", exc)
        return None
    return claims["email"].strip().lower()


def default_display_name(email):
    name = email.split("@", 1)[0]
    return name[:1].upper() + name[1:]


def get_or_create_user(conn, email):
    now = datetime.now().isoformat(timespec="seconds")
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:
        with conn:
            conn.execute(
                "INSERT INTO users (email, display_name, is_admin, created_at, last_seen_at) "
                "VALUES (?, ?, 0, ?, ?)",
                (email, default_display_name(email), now, now),
            )
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    # One write a day is plenty for "last seen".
    if (row["last_seen_at"] or "")[:10] != now[:10]:
        with conn:
            conn.execute("UPDATE users SET last_seen_at = ? WHERE id = ?", (now, row["id"]))
    return row


def _request_host():
    return request.host.rsplit(":", 1)[0].lower()


def load_user():
    """before_request: sets g.user, or refuses the request."""
    if request.endpoint == "static":
        return None
    cfg = current_app.config["RECIPES_CONFIG"]
    db = get_db()

    token = request.headers.get("Cf-Access-Jwt-Assertion")
    if token:
        email = access_email(token, cfg)
        if email is None:
            abort(403, "Your sign-in couldn't be verified. Reload the page to sign in again.")
        g.user = dict(get_or_create_user(db, email))
    elif _request_host() in cfg.HOME_HOSTS:
        g.user = dict(db.execute("SELECT * FROM users WHERE id = ?", (HOME_USER_ID,)).fetchone())
    else:
        abort(403, "Please sign in through the recipe site's public address.")

    if (request.blueprint in ADMIN_BLUEPRINTS and request.endpoint not in OPEN_ADMIN_ENDPOINTS
            and not g.user["is_admin"]):
        abort(403, "That page is only for admins.")
    return None


def current_user():
    return g.get("user")


def is_admin():
    user = current_user()
    return bool(user and user["is_admin"])


def can_edit_recipe(recipe):
    user = current_user()
    return bool(user) and (bool(user["is_admin"]) or recipe["owner_id"] == user["id"])


def can_delete_recipe():
    return is_admin()


def can_delete_note(note):
    user = current_user()
    return bool(user) and (bool(user["is_admin"]) or note["author_id"] == user["id"])


def require(allowed):
    if not allowed:
        abort(403, "You can't change that recipe.")
