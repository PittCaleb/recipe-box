# Recipes

A family recipe web app (Flask + SQLite), running in Docker on a home NAS. See
"Running in Docker" below; it also runs straight from a checkout for development.

> **Note:** `pdf/` (source scans) and `data/` (the database, images, and
> everything else generated from them) are gitignored and not part of this
> repo — they contain real recipes and family info. A fresh clone starts
> with an empty database; see "Getting recipes from a PDF into the app"
> below to load your own recipes.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
brew install pango   # required by WeasyPrint for PDF generation
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY if you want PDF import -- see below
```

Every setting is a plain environment variable (see Configuration below);
`.env` is just a convenient, gitignored place to keep them so you don't have
to `export` them in every terminal session. The app loads it automatically
on startup via `python-dotenv`. A real environment variable (set by your
shell, Docker, launchd, etc.) always takes priority over `.env`.

## Running

```bash
python run.py
```

This prints the local URL and the LAN URL (for phones/tablets on the same Wi-Fi).

## Browsing

The home page lists recipes as **Cards** (a picture per recipe) or **Text**
(a compact list in 1, 2 or 3 columns depending on screen width), grouped
**A–Z** (letter headers) or by **Category** (headers in the Admin →
Categories order). Within each group, recipes are sorted alphabetically.
Each device remembers the view it was last left on.

## Configuration

All settings are environment variables with sensible defaults; see `config.py`:

| Var | Default | Purpose |
|---|---|---|
| `RECIPES_DATA_DIR` | `./data` | All mutable data (db, images, scans, exports) |
| `RECIPES_HOST` | `0.0.0.0` | Listen address |
| `RECIPES_PORT` | `5050` | Port (5000 is taken by macOS AirPlay) |
| `RECIPES_HOME_HOSTS` | `localhost,127.0.0.1` | Hostnames with no sign-in; visitors there act as the owner (user 1) |
| `RECIPES_ACCESS_TEAM_DOMAIN` | unset | Cloudflare Access team domain, e.g. `yourteam.cloudflareaccess.com` |
| `RECIPES_ACCESS_AUD` | unset | The Access application's Audience (AUD) tag |
| `RECIPES_COOKBOOK_TITLE` | `Our Family Recipes` | Default cookbook cover title |
| `ANTHROPIC_API_KEY` | unset | Required for **Admin → Import a new PDF** and for drawn placeholder pictures (see below) |
| `RECIPES_IMPORT_MODEL` | `claude-opus-5-5` | Model used to transcribe uploaded PDFs |
| `RECIPES_PLACEHOLDER_MODEL` | `claude-sonnet-5-5` | Model that draws placeholder pictures |
| `RECIPES_PDF_DIR` | `./pdf` | Where source and uploaded PDFs live |

## People and permissions

Everyone can read every recipe, print, share, and add new recipes. On top of that:

| | Admin | A recipe's owner | Everyone else |
|---|---|---|---|
| Edit a recipe | any | their own | no |
| Delete a recipe | yes | no | no |
| Add a note, add or replace the photo | yes | yes | yes |
| Delete a note | any | their own notes | their own notes |
| Remove the photo | yes | yes | no |
| Admin menu: import, duplicates, categories, needs review, export | yes | no | no |

Favorites, ratings, and "I made this" are each person's own.

Who someone is: through the public address, Cloudflare Access signs them in, and the app reads their email from the
signed token Access adds to each request (checked against `RECIPES_ACCESS_TEAM_DOMAIN` and `RECIPES_ACCESS_AUD`). The
first time someone new arrives they get a regular account. On a home address (`RECIPES_HOME_HOSTS`) there is no sign-in
and everyone acts as user 1, the owner. Any other request without a valid token is refused.

To make someone an admin (there's no screen for it yet):
```sh
sqlite3 data/recipes.db "UPDATE users SET is_admin = 1 WHERE email = 'them@example.com';"
```

## Getting recipes from a PDF into the app

A scanned PDF of recipe cards doesn't turn itself into structured recipes —
something has to read each card. There are three ways to do that, in order
of least to most manual effort. **None of them is mandatory** — pick
whichever fits what you have access to.

### Option A: Admin → Import a new PDF (automatic, costs a little money)

Upload a PDF from the browser and the app does everything: renders each
page, calls the Claude API to transcribe every recipe it finds (title,
ingredients, instructions, contributor, category guess, a crop box per
recipe), crops a scan image per recipe, and stages it all for your review —
nothing touches your real collection until you hit **Commit** (or
**Discard** to throw the batch away). Details and known limitations below.

Requires an `ANTHROPIC_API_KEY` (see the next section) and costs roughly a
few cents per page in API usage. Best if you want the least manual work and
don't mind the small cost.

### Option B: Transcribe it yourself with an AI coding assistant (free if you already have one)

This is literally how this project's own 65 recipes were imported — no
separate API key was used, because the transcription was done by an AI
coding assistant (e.g. Claude Code) reading each page image interactively
in the same way it reads any other file, using whatever Claude access the
person was already paying for (Pro/Max/Claude Code), not the pay-as-you-go
API.

The steps (the same ones **SPEC.md section 5** describes in full, including
the exact transcription rules the assistant should follow — wording as
written, sub-group headings, `[?guess?]` markers, margin notes, etc.):

1. Put your PDF at `pdf/<something>.pdf`.
2. `python -m importer.render_pages` — renders every page to
   `data/import/pages/*.png`.
3. Ask your assistant to look at each rendered page and write
   `data/import/seed.json` (recipe data) and `data/import/crops.json` (crop
   boxes), following SPEC.md section 5's rules. For more than a handful of
   pages, expect this to be a real back-and-forth working session, not one
   prompt — that's normal; it's exactly how the original import went.
4. `python -m importer.crop_scans` — crops a scan image per recipe from
   `crops.json`.
5. `python -m importer.load_seed` — loads `seed.json` into the database.
   Refuses to run if `recipes` already has rows (protects your existing
   data) — pass `--force` to wipe and reload instead.

No `ANTHROPIC_API_KEY` needed for this path — it rides on whatever Claude
access you already have, not a separate Console account.

### Option C: Type it in by hand (free, no AI at all)

Run `python -m importer.render_pages` to get page images in
`data/import/pages/`, keep those open next to the browser, and use the
app's own **New recipe** form to type each one in — no scripts, no AI,
just data entry. Slowest option, but it needs nothing beyond the app
itself.

---

## Getting an Anthropic API key

Only needed for **Option A** above. Skip this whole section if you're using
Option B or C.

1. Go to **[console.anthropic.com](https://console.anthropic.com)** and sign
   up or log in. This is the **developer console**, separate from a
   claude.ai subscription — a claude.ai Pro/Max plan doesn't include API
   access, and API usage isn't covered by one.
2. If this is a new account, add a payment method under **Settings →
   Billing** and add a small amount of credit. API usage is billed per
   request (pay-as-you-go, no subscription) — transcribing a page of a
   recipe card costs a few cents, so even a $5 balance covers a large batch.
3. Go to **Settings → API Keys** (left sidebar).
4. Click **Create Key**, give it a name you'll recognize later (e.g.
   `recipes-app`), and create it.
5. Copy the key immediately — it's only shown once. It starts with
   `sk-ant-`.
6. Paste it into `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
7. Restart the app (`python run.py`) if it was already running.

Keep this key private — anyone with it can run up charges on your account.
Don't paste it into a chat, commit it, or put it anywhere other than `.env`
(which is gitignored) or a real environment variable. If you ever suspect
it leaked, revoke it from the same **API Keys** page and create a new one.

## Option A details: importing a new PDF from the browser

Without `ANTHROPIC_API_KEY` set, the Import page shows a warning instead of
starting a job. Once it's set, **Admin → Import a new PDF** runs in a
background thread; the progress page polls and updates itself, so you can
navigate away — any batch that isn't committed yet shows up under
**Admin → Unfinished imports** so you can get back to it.

Known limitation: each page is transcribed independently, with no awareness
of neighboring pages. A recipe whose instructions continue onto another
page — adjacent or not, same as a couple of recipes in the original
collection — won't be stitched together automatically. It comes through
with `needs_review` set and a note that the instructions look cut off; you
finish it by hand afterward (open the recipe, check the next page's scan if
needed, and paste in the rest) via the normal edit screen.

## Photos

Add or replace a recipe's photo from the recipe page (**Replace image**) or
the edit page. JPEG, PNG, WebP and iPhone HEIC all work, and everything is
saved as a JPEG (with a thumbnail), turned the right way up and without the
photo's location data. If a Live Photo arrives as just its short movie
(sometimes still named `.HEIC`), the app uses the frame the iPhone marked as
the photo.

## Placeholder pictures

A recipe without a photo gets a drawn picture so the page doesn't look bare:
a flat illustration of the dish on the same wooden table as all the others.
They're drawn by Claude (Sonnet) from the title, category, ingredients and
instructions, using a few of the hand-drawn set in
`app/placeholder_examples/` as the style guide, then turned into a JPEG with
`rsvg-convert` (`brew install librsvg` on the Mac; it's in the Docker image).
Each one costs a few cents and takes 10–60 seconds in the background.

- A new recipe saved without a photo gets one, and so does each recipe from
  a PDF import.
- On a recipe, **Replace image → Replace with a new AI drawing** (also under
  Image on the edit page) draws a fresh one in place of the current picture,
  photo or drawing. Owners and admins only, since the current one is deleted.
- Uploading a real photo always replaces a drawing.
- Drawings are marked `image_is_placeholder = 1` in `recipes`.
- Nothing happens without `ANTHROPIC_API_KEY`. If a drawing fails, the
  recipe just stays without a picture and the error goes to the app's log.

The first 59 were drawn by hand in code: `scripts/placeholder-images/`
(`scenes.py`, `scenes2.py`, `16.svg`) holds them, and `sheet.py` makes a
contact sheet.

## Sharing a recipe

The app doesn't send anything itself — no email or message accounts to set
up. Each recipe page has export buttons, and you share the result however
you like:

- **Print** — the browser's print dialog, with a print-friendly layout.
- **Save PDF** — downloads the recipe as a PDF.
- **Save image** — downloads the recipe as one PNG image (handy for a text
  message or a photo album).
- **Copy image** — puts that same PNG on your clipboard to paste anywhere.
  Browsers only allow this on `https://` or `localhost`, so the button only
  appears when the app is opened that way (e.g. `http://127.0.0.1:5050` on
  the Mac itself). On a phone using the LAN address, use **Save image**.

## JSON API (for other apps)

A small read-only API, there for a TV app. It answers the same way the
pages do: from a home address it acts as the owner; through the public
address it needs a sign-in.

| Request | Returns |
|---|---|
| `GET /api/v1/recipes` | `{"total": n, "recipes": [...]}`: every recipe, by name. Narrow it with `?q=` (search, best match first), `?category=<id>`, `?favorites=1`; order it with `?sort=name\|category\|recent_made\|recent_added` |
| `GET /api/v1/recipes/<id>` | One recipe: the list fields plus `source`, `owner`, `ingredients` (`kind` is `item` or `heading`, plus `text`), `steps` (the instructions as plain-text steps), `instructions_html` and `notes` |
| `GET /api/v1/categories` | `{"categories": [{"id", "name", "recipe_count"}]}` in menu order |

Each recipe in a list has `id`, `title`, `category` (`{id, name}` or null),
`contributor`, `servings`, `prep_time`, `cook_time`, `image_url`,
`image_is_placeholder`, `favorite`, `rating`, `last_made` (the asker's
own), `slug` and `web_url`. The URLs are full addresses, so they work as they are.
The API looks recipes up by `id`, which never changes; `slug` (and so
`web_url`) changes when a recipe is renamed.
An unknown recipe gets `404 {"error": "not found"}`.

## Tests

```bash
pytest
```

## Running in Docker

The live copy runs as a Docker container on a home NAS, behind a reverse
proxy that serves it under `/recipes/` (the app follows the proxy's
`X-Forwarded-Prefix`, so any sub-path works). **The server's data is the live
copy**; data on a development machine is only a copy, refreshed with
`scripts/pull-live-data.sh` (stop the local app first).

- Merging to `main` runs the **Docker image** GitHub Action, which builds and
  pushes `ghcr.io/pittcaleb/recipe-box:latest` (a few minutes; watch the
  repo's Actions tab). Pull that image on the server and restart the
  container to ship a change.
- Everything that changes (database, photos, scans, import files, PDFs) lives
  in `/data` inside the container, mounted from the host.
- Settings are the environment variables under Configuration, plus
  `RECIPES_SECRET_KEY` (signs the session cookie). Put a new setting in place
  before starting the image that needs it; restart to change one.
- Migrations run by themselves when the container starts.
- Copy files to the server with `rsync`; it has no SFTP, so `scp` fails.
