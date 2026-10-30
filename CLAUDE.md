# Recipes (recipe-box)

The family cookbook: a Flask + SQLite web app. It runs in Docker on a home NAS, behind a reverse proxy at `/recipes/`.
Read README.md (setup, configuration, people and permissions, PDF import, running in Docker), SPEC.md (the original
design) and TODO.md (the roadmap) before larger changes. This file is what those don't say.

**This repo is public.** Machine names, users, addresses, emails and server paths go in `CLAUDE.local.md` (gitignored, read
alongside this file), never in a committed file. Tests and examples use made-up people and `example.com` addresses.

## Working with the owner

- **Commit, push and open a PR only when asked.** The usual words are "commit this, push it and create the pr". Branch off
  an up-to-date `main` for each piece of work. Bundle related work into one PR rather than splitting it finely.
- **Never commit `config.py`'s local change** (`RECIPES_PORT` default 5052; the committed default is 5050) or `.coverage`.
  When `config.py` has real changes: set the port back to 5050, `git add config.py`, then restore 5052.
- **Deploying touches production.** Do it when the owner says to ("go ahead and deploy"); the permission check blocks it
  otherwise. The steps are in `CLAUDE.local.md`.
- **The NAS copy is the live data.** `data/` on the Mac is only a copy; refresh it with
  `scripts/pull-live-data.sh` (stop the local app first). Never copy local data over the NAS.
- Plain, friendly language in UI text and summaries. Check changes on a phone (iPhone) as well as the Mac.

## Running and testing

- Python 3.14 venv in `.venv`: `.venv/bin/python run.py` (serves on :5052 locally); `.venv/bin/python -m pytest -q`
  (~400 tests, ~10 s).
- **Pin exact versions in `requirements.txt` and pick ones with prebuilt wheels** for cp314 macOS arm64 and Linux amd64. This
  Mac can't compile C extensions (the Xcode license was never accepted, so clang refuses to run).
- Test fixtures (`tests/conftest.py`):
  - `client` is a home visitor, so user 1, the admin.
  - `member` / `signed_in(email)` are clients that come in through the public address with a real RS256 token. The signing key
    is monkeypatched, so no network.
  - `seed_recipe(db, favorite=…, rating=…, last_made=…)` stores those as user 1's personal values (`seed_personal`).
- When a test suite passes on the first run, break the rule it covers to prove the tests can fail, then restore the rule.

## How it fits together

- **App factory:** `app/__init__.py`. It applies
  `ProxyFix(x_for, x_proto, x_host, x_prefix)`, because Caddy strips `/recipes` and sends `X-Forwarded-Prefix`. So **always
  use `url_for`; never hard-code paths.** The session cookie is `recipes_session`, since all apps share one hostname, and it only
  carries flash messages.
- **Blueprints** in `app/routes/`: browse (`/`, `/api/search`), recipe (view, favorite, made, rating, notes), edit (new, edit,
  delete, images), share (PDF/PNG), media, help, `api` (read-only JSON at `/api/v1/`, for the TV app; see README),
  and the admin-only `admin`, `import_pdf` (Claude-powered PDF import) and `duplicates`.
- **Models:** `app/models/recipes.py`. `search_recipes(..., user_id)` and `get_recipe(conn, id, user_id)` join the person's own
  `user_recipes` row in as `favorite` / `rating` / `last_made`, so templates read `r['favorite']` as before.
- **Migrations:** `app/migrations/NNN_name.sql`, or `.py` with a `migrate(conn)` that doesn't commit. They run automatically on
  startup, recorded in `schema_version`. Next number: **008**.
  - Before deploying a migration, copy the live database (from the latest backup archive on the NAS) to the scratchpad, run the
    migration against the copy, and render every page as admin and as a member.
  - Snapshot the live DB in the container right before deploying (command in `CLAUDE.local.md`).
- **Photo uploads** (`app/images.py`): Pillow opens the file (HEIC via `pillow-heif`); if it can't and the file is a
  QuickTime/MP4 movie, `app/live_photo.py` (PyAV) takes the Live Photo's marked still frame. Everything is saved as an sRGB
  JPEG without metadata.
- **Placeholder pictures** (`app/placeholder_images.py`, since 2026-10-28): a recipe saved without a photo, or imported from a
  PDF, gets a drawing from Sonnet in a background thread, rendered with `rsvg-convert` (in the Docker image). The style comes
  from `app/placeholder_examples/`; the model may only use plain shapes (`check_svg`). `image_is_placeholder` marks them;
  any photo replaces one. "Replace with a new AI drawing" (`edit.draw_image`) is owner/admin only, since it deletes the current
  picture, and links only if the picture hasn't changed meanwhile. Tests never call Claude: `conftest.py` runs the job inline
  with a fixed SVG and clears the API key.
- **Search:** SQLite FTS5 (`recipes_fts`), kept in sync by `_sync_fts` on every save. Ranked with `bm25`. The owner chose to stay on
  SQLite (2026-10-27): no Postgres/MySQL.
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

## Deploying

See `CLAUDE.local.md` for the server, the commands and the checks. In short: merge the PR, wait for the **Docker image**
Action (`gh run list --limit 1`), snapshot the live database if a migration is going out, update the container, then check
the home and public addresses. Right after a restart there's a few seconds of 502 while the app starts, so retry before
worrying. New settings must be in the server's env file **before** the image that needs them starts.
