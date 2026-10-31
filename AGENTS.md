# Recipes (recipe-box)

The family cookbook: a Flask + SQLite web app. It runs in Docker on a home NAS, behind a reverse proxy at `/recipes/`.
Read README.md (setup, configuration, people and permissions, PDF import, running in Docker), SPEC.md (the original
design) and TODO.md (the roadmap) before larger changes. This file is what those don't say. It's the guide for any coding
agent (Codex, Copilot, Cursor, Claude Code, Gemini, …) and for people contributing too; see CONTRIBUTING.md.

**This repo is public.** Machine names, users, addresses, emails and server paths never go in a committed file. (The
maintainer keeps theirs in a gitignored `CLAUDE.local.md`.) Tests and examples use made-up people and `example.com`
addresses.

## Conventions

- Plain, friendly language in UI text and summaries. Check changes on a phone (iPhone) as well as a desktop browser.
- **Pin exact versions in `requirements.txt` and pick ones with prebuilt wheels** for cp314 macOS arm64 and Linux amd64.
  The maintainer's Mac can't compile C extensions.
- Don't commit `.coverage`.

## Running and testing

- Python 3.14 venv in `.venv`: `.venv/bin/python run.py` (serves on :5050 by default; set `RECIPES_PORT` to change it);
  `.venv/bin/python -m pytest -q` (~500 tests, ~15 s).
- Test fixtures (`tests/conftest.py`):
  - `client` is a home visitor, so user 1, the admin.
  - `member` / `signed_in(email)` are clients that come in through the public address with a real RS256 token. The signing key
    is monkeypatched, so no network.
  - `seed_recipe(db, favorite=…, rating=…, last_made=…)` stores those as user 1's personal values (`seed_personal`).
- When a test suite passes on the first run, break the rule it covers to prove the tests can fail, then restore the rule.

## How it fits together

- **App factory:** `app/__init__.py`. It applies
  `ProxyFix(x_for, x_proto, x_host, x_prefix)`, because Caddy strips `/recipes` and sends `X-Forwarded-Prefix`. So **always
  use `url_for`; never hard-code paths.** `run.py` serves with waitress, and `SERVE_OPTIONS` stops it dropping
  `X-Forwarded-Proto`/`Host`/`For` before ProxyFix sees them (without it, links built over HTTPS come back `http://`).
  The session cookie is `recipes_session`, since all apps share one hostname, and it only carries flash messages.
- **Blueprints** in `app/routes/`: browse (`/`, `/api/search`), recipe (view, favorite, made, rating, notes), edit (new, edit,
  delete, images), share (PDF/PNG), media, help, `api` (read-only JSON at `/api/v1/`, for the TV app; see README),
  and the admin-only `admin`, `import_pdf` (Claude-powered PDF import) and `duplicates`.
- **JSON API:** a separate TV app relies on it. Keep it read-only and backwards compatible (add fields, don't rename them),
  and keep README's "JSON API" section up to date; it's the reference.
- **Models:** `app/models/recipes.py`. `search_recipes(..., user_id)` and `get_recipe(conn, id, user_id)` join the person's own
  `user_recipes` row in as `favorite` / `rating` / `last_made`, so templates read `r['favorite']` as before.
- **Migrations:** `app/migrations/NNN_name.sql`, or `.py` with a `migrate(conn)` that doesn't commit. They run automatically on
  startup, recorded in `schema_version`. Next number: **009**.
- **Recipe addresses** (`app/slugs.py`, since 2026-10-30): a recipe's page is `/<slug>` at the app's top level (so
  `…/recipes/brownies` behind the proxy). Its actions stay at `/recipes/<id>/…`, and the old `/recipes/<id>` page address
  301s to the slug. `save_recipe` sets the slug on create and on a title change; same titles get `-2`, `-3`, and `RESERVED`
  words are skipped. Every slug a recipe has had stays in `recipe_slugs`, so old links redirect and nobody else takes them;
  merging moves the removed copy's slugs to the kept recipe. Link with `url_for('recipe.view', slug=r['slug'])`, or
  `recipe_url(id)` from a route. A new top-level route needs its word added to `RESERVED`.
- **Photo uploads** (`app/images.py`): Pillow opens the file (HEIC via `pillow-heif`); if it can't and the file is a
  QuickTime/MP4 movie, `app/live_photo.py` (PyAV) takes the Live Photo's marked still frame. Everything is saved as an sRGB
  JPEG without metadata.
- **Placeholder pictures** (`app/placeholder_images.py`, since 2026-10-28): a recipe saved without a photo, or imported from a
  PDF, gets a drawing from Sonnet in a background thread, rendered with `rsvg-convert` (in the Docker image). The style comes
  from `app/placeholder_examples/`; the model may only use plain shapes (`check_svg`). `image_is_placeholder` marks them;
  any photo replaces one. "Replace with a new AI drawing" (`edit.draw_image`) is owner/admin only, since it deletes the current
  picture, and links only if the picture hasn't changed meanwhile. Tests never call Claude: `conftest.py` runs the job inline
  with a fixed SVG and clears the API key.
- **Search:** SQLite FTS5 (`recipes_fts`), kept in sync by `_sync_fts` on every save. Ranked with `bm25`. The project
  stays on SQLite (decided 2026-10-27): no Postgres/MySQL.
- **Templates:** icons are macros in `_icons.html` (`icon('name', size)`). Destructive forms use `data-confirm`. Macros that need
  `is_admin` etc. must be imported `with context`. The browse view state is remembered per device in
  `localStorage["recipes.browseQuery.v3"]`; rename the key to reset everyone's saved view when defaults change.

## People and permissions (since 2026-10-27, PR #12)

- **Identity:** `app/users.py`. `load_user` runs before every request except static files.
  1. A `Cf-Access-Jwt-Assertion` header must verify against `RECIPES_ACCESS_TEAM_DOMAIN`
     and `RECIPES_ACCESS_AUD`, using RS256 with keys from `/cdn-cgi/access/certs`. Its email becomes a `users` row, created
     automatically as a non-admin on the first visit.
  2. With no token, a host in `RECIPES_HOME_HOSTS` acts as user 1 (the owner, admin).
  3. Anything else gets a 403.
  4. A bad token gets a 403 even on a home host.
  5. **The plain `Cf-Access-Authenticated-User-Email` header is never trusted.**
- **Rules:**
  - everyone reads and adds;
  - owners edit their own;
  - only admins delete recipes;
  - anyone adds notes and photos;
  - a note's author or an admin deletes notes;
  - the owner or an admin removes photos;
  - `needs_review` / `needs_split` filters and flags are admin-only;
  - Print cookbook (`admin.cookbook*`) is open to all.

  Enforce on the server with `require(...)` / `abort(403)`, not just by hiding buttons. Template helpers: `current_user`,
  `is_admin`, `can_edit_recipe(r)`, `can_delete_recipe()`, `can_delete_note(n)`.
- **Schema (005):**
  - `users(id, email UNIQUE NOCASE, display_name, is_admin, created_at, last_seen_at)`;
  - `recipes.owner_id` and `notes.author_id`;
  - `user_recipes(user_id, recipe_id, favorite, rating, last_made)`.
  - The old shared `favorite` / `rating` / `last_made` columns are gone.
- **Admins are promoted by hand:** `UPDATE users SET is_admin = 1 WHERE email = '...'`. A user-management screen is in TODO.md.
- The header shows "Welcome <part of the email before @>".
