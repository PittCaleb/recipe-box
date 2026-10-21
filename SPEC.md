# Recipe Repository — Build Spec for Claude Code

## 0. Read this first

You are building a personal recipe web app for a single owner. The source material is two PDFs of scanned recipes. The owner will verify every recipe line by line after import, so aim for accuracy but don't stall on hard-to-read text: flag it and move on.

**Work in phases (section 10) and stop for the owner's review where marked.** Don't skip ahead.

- **Project root:** `/Users/pittcaleb/projects/recipes`
- **Source PDFs:** expected at `pdf/recipes.pdf` and `pdf/recipes2.pdf` under the project root. If they aren't there, search the project root for them and confirm the paths with the owner before starting.
- **Host for now:** the owner's Mac, run manually from Terminal. Must be reachable from phones and tablets on the home Wi-Fi.
- **Future host:** a Docker container on the owner's NAS. Don't build Docker now, but keep the app portable: no hard-coded absolute paths, all config from environment variables, and all mutable data under one data directory.
- **Browser:** Chrome on desktop, plus mobile browsers on phone and tablet. The design must be mobile-first and responsive.

---

## 1. Tech stack

| Concern | Choice |
|---|---|
| Backend | Python 3.11+, Flask, served by **waitress** (not the Flask dev server) |
| Database | SQLite (stdlib `sqlite3`), with foreign keys ON and WAL mode |
| Templates | Server-rendered Jinja2 plus small vanilla JS modules. No SPA framework and no JS build step. |
| Rich text editor | **Quill 2**, vendored into `app/static/vendor/` (no CDN; the app must work offline and on the LAN) |
| HTML sanitizing | `nh3`, allowlist only: `p, br, strong, em, ul, ol, li` |
| PDF render (import) | PyMuPDF (`pymupdf`) |
| Images | Pillow |
| PDF generation (output) | WeasyPrint. Requires `brew install pango`; document this in the README. |
| PDF → JPG | PyMuPDF rasterizes the generated PDF. Pillow stacks multi-page output into one tall JPG. |
| Tests | pytest |

Use a virtualenv (`.venv`) and a pinned `requirements.txt`.

---

## 2. Project layout

```
recipes/
  SPEC.md                  # this file
  README.md                # setup, run, troubleshooting (permissions, pango)
  requirements.txt
  run.py                   # entry point: starts waitress, prints LAN URL
  config.py                # reads env vars, provides defaults
  pdf/                     # source PDFs (read-only input)
  app/
    __init__.py            # app factory
    db.py                  # connection helper, migrations runner
    migrations/            # 001_initial.sql, 002_..., applied in order
    models/ or services/   # recipes, ingredients, notes, categories, search
    ingredients/           # parser.py (split suggestion), units.py, scaling.py
    rendering/             # pdf.py (WeasyPrint), jpg.py, cookbook.py
    sharing/               # base.py (interface), mac.py (AppleScript), smtp.py (stub)
    export/                # txt_backup.py
    routes/                # blueprints: browse, recipe, edit, admin, share, cookbook
    templates/
    static/ (css, js, vendor/quill)
  importer/
    render_pages.py        # PDF pages → PNG
    crop_scans.py          # crop boxes → scan JPGs
    load_seed.py           # seed.json → SQLite
  data/                    # RECIPES_DATA_DIR; the only mutable location
    recipes.db
    images/                # owner-uploaded photos
    scans/                 # cropped original scans from import
    exports/               # txt backups, generated cookbooks
    tmp/                   # transient render/share files
    import/                # page PNGs, seed.json, crop boxes
  tests/
```

`data/` goes in `.gitignore`. Initialize the project as a git repo.

---

## 3. Configuration (`config.py`, env vars with defaults)

| Var | Default | Purpose |
|---|---|---|
| `RECIPES_DATA_DIR` | `./data` | All mutable data |
| `RECIPES_HOST` | `0.0.0.0` | Listen on the LAN |
| `RECIPES_PORT` | `5050` | Avoid 5000, which macOS AirPlay uses |
| `RECIPES_SHARE_BACKEND` | `mac` on macOS, else `none` | `mac`, `smtp` (future), or `none` |
| `RECIPES_APP_PASSWORD` | unset | If set, editing, admin, and sharing require a simple session login. If unset, the app is fully open. |
| `RECIPES_COOKBOOK_TITLE` | `Our Family Recipes` | Default cookbook cover title |

On startup, `run.py` prints both `http://localhost:PORT` and `http://<mac-lan-ip>:PORT`.

---

## 4. Database schema

Use numbered SQL migration files plus a `schema_version` table. Timestamps are ISO-8601 strings in local time.

```sql
CREATE TABLE categories (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
  sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE recipes (
  id                INTEGER PRIMARY KEY,
  title             TEXT NOT NULL,
  category_id       INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  contributor       TEXT,            -- free-form
  source            TEXT,            -- cookbook/website/card, if known
  servings          TEXT,            -- as written, e.g. "6-8" or "2 dozen"
  prep_time         TEXT,
  cook_time         TEXT,
  instructions_html TEXT NOT NULL DEFAULT '',   -- sanitized HTML
  image_filename    TEXT,            -- in data/images/, max one per recipe
  scan_filename     TEXT,            -- in data/scans/, from import
  source_pdf        TEXT,            -- e.g. "recipes2.pdf"
  source_page       INTEGER,         -- 1-based
  needs_review      INTEGER NOT NULL DEFAULT 0,
  favorite          INTEGER NOT NULL DEFAULT 0,
  rating            INTEGER CHECK (rating BETWEEN 1 AND 5),
  last_made         TEXT,            -- date only, YYYY-MM-DD; single value
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE TABLE ingredients (
  id           INTEGER PRIMARY KEY,
  recipe_id    INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  position     INTEGER NOT NULL,
  kind         TEXT NOT NULL DEFAULT 'item' CHECK (kind IN ('item','heading')),
  raw_text     TEXT NOT NULL,        -- exactly as written; always kept
  is_split     INTEGER NOT NULL DEFAULT 0,
  quantity     REAL,                 -- set when is_split
  quantity_max REAL,                 -- for ranges like "2-3"
  unit         TEXT,                 -- canonical unit key or NULL (count items)
  item         TEXT,                 -- remainder, e.g. "flour, sifted"
  no_scale     INTEGER NOT NULL DEFAULT 0   -- e.g. "salt to taste"
);
CREATE INDEX idx_ingredients_recipe ON ingredients(recipe_id, position);

CREATE TABLE notes (
  id         INTEGER PRIMARY KEY,
  recipe_id  INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  body       TEXT NOT NULL,
  created_at TEXT NOT NULL           -- auto-stamped
);
```

**Search:** Create an FTS5 virtual table indexing title, category name, contributor, and ingredient raw text. Keep it in sync from the service layer on every recipe save or delete; a full rebuild is acceptable at this scale. Use prefix matching so "choc" finds "chocolate". Rank title matches above ingredient matches.

**Scalable recipe:** A recipe is scalable when every `kind='item'` ingredient has either `is_split=1` with a quantity, or `no_scale=1`, and at least one ingredient is split. Compute this on read; don't store it.

---

## 5. Phase 1: PDF import pipeline

This is a separate step that runs before the web app is built. Its output is a populated database plus cropped scans.

1. **Render pages.** `importer/render_pages.py` renders every page of both PDFs to PNG at 200–300 DPI in `data/import/pages/`.
2. **Find scans.** Each recipe is at most one page, but a page may hold one or two recipe scans, side by side or stacked. View each page image yourself and record a crop box per recipe in `data/import/crops.json`.
3. **Crop.** `importer/crop_scans.py` saves each scan as `data/scans/{pdfstem}-p{page:03d}-{a|b}.jpg`, with a max of 2000px on the long side.
4. **Transcribe** each crop into `data/import/seed.json`. This file is an import artifact only; the database is the system of record. Rules:
   - **Contributor:** everything from `recipes2.pdf` is `Pat Cohen`. For `recipes.pdf`, fill it only if a name is clearly shown on the card; otherwise leave it blank.
   - Keep the wording, spelling, and abbreviations **as written**. Don't modernize or "fix" anything.
   - **Ingredients:** one entry per line, exactly as written, into `raw_text`. Sub-group labels ("For the crust:") become `kind='heading'`. Do **not** split ingredients during import.
   - **Instructions:** simple `<p>` paragraphs matching the card's breaks. Use `<ol>`/`<ul>` only if the card is clearly numbered or bulleted.
   - Fill servings, times, and source only if they're present on the card.
   - **Uncertain text:** write your best guess wrapped as `[?guess?]` and set `needs_review=1`. If no title is visible, invent a descriptive one and set `needs_review=1`.
   - **Margin or handwritten annotations** become a note with the body prefixed `From original card: `.
   - Record `source_pdf`, `source_page`, and `scan_filename` for each recipe.
5. **Propose categories. STOP for owner approval.** Present a list of roughly 8–14 single-level categories (e.g., Appetizers, Soups, Mains – Beef, Desserts – Cookies…, chosen to fit the actual recipes), plus the proposed category for each recipe as a table. Apply them only after the owner approves or edits them.
6. **Load.** `importer/load_seed.py` loads into SQLite. It refuses to run if `recipes` already has rows unless given `--force`, which wipes and reloads. This protects the owner's later edits.
7. **Report:** total recipes per PDF, plus a list of every `needs_review` recipe with its page number.

---

## 6. Web app features

### 6.1 Browse and search (home page)
- A search box with live results (debounced), matching on name, ingredient, category, and contributor.
- A category filter as chips or a dropdown, plus an "All" option.
- Sort options: name A–Z, recently made, recently added.
- Filter toggles: "Needs review" and "Favorites".
- Each result card shows the title, category, image thumbnail (if any), and last made date (if any).

### 6.2 Recipe view
Shows the title, category, contributor, source, servings and times, image, ingredients (headings styled distinctly), instructions (rich text), last made, and notes newest-first with date stamps. Empty fields are hidden entirely. A small "Needs review" badge appears when the flag is set.

Action buttons (they should collapse sensibly on mobile):
- **I made this:** sets `last_made` to today, with a one-tap confirmation. The date stays editable in edit mode.
- **Add note:** a textarea modal. The note is saved with an automatic timestamp.
- **Add image / Replace image:** see 6.6.
- **Adjust:** only shown when the recipe is scalable. See 6.5.
- **Print:** the browser's print dialog with a clean print stylesheet.
- **Save PDF:** downloads the server-generated PDF.
- **Email:** see 6.7.
- **Text:** iMessage, see 6.7.
- **View original scan:** opens the scan in a lightbox; shown only if `scan_filename` is set. On desktop, edit mode shows the scan side by side with the form to make verification easier.
- **Edit**
- **Favorite toggle**

### 6.3 Edit mode and new recipe
- Every field is editable: title, category (dropdown), contributor (free text), source, servings, times, rating, favorite, needs_review checkbox, last made (date picker), and instructions.
- **Instructions** use Quill with a minimal toolbar: Bold, Italic, Bulleted list, Numbered list, Clear formatting. The owner's main use will be selecting scanned block text and converting it to a list. The HTML is sanitized server-side before saving.
- **Ingredient editor:** one row per ingredient, showing its raw text.
  - Rows can be added, deleted, and reordered with up/down buttons (these work on touch). Rows can be toggled between item and heading.
  - A **Split** button per row opens the suggestion described in 6.4.
  - A **Don't scale** toggle per row.
  - Split rows show a compact "qty · unit · item" chip next to the raw text.
- Notes are editable and deletable here.
- **Save** writes everything in one transaction and updates `updated_at` and the search index.
- **New recipe** (from the header) opens the same form, empty, so a recipe can be typed in from scratch.
- **Delete recipe** asks for confirmation, then performs a hard delete: database rows (with cascade), the image file, and the scan file.

### 6.4 Ingredient splitting
`app/ingredients/parser.py` suggests `{quantity, quantity_max, unit, item}` from the raw text. The owner confirms or fixes the suggestion in a small form, and saving it sets `is_split=1`. The raw text is never changed by splitting.

The parser must handle:
- Whole numbers, decimals, simple fractions, and mixed numbers ("1 1/2"), including unicode fractions (½ ⅓ ¼ ¾ ⅔ ⅛).
- Ranges ("2-3", "2 to 3").
- Parenthetical sizes: "1 (8 oz) package cream cheese" gives quantity 1, unit "package", and item "(8 oz) cream cheese".
- Unit synonyms: c./cup/cups; T/Tbsp/tbs/tablespoon (a **capital T means tablespoon**); t/tsp/teaspoon (a **lowercase t means teaspoon**); oz; lb/lbs/#; fl oz; pt; qt; gal; ml; l; g; kg; stick; can; package/pkg; clove; pinch; dash.
- Lines with no number ("salt to taste") return no quantity, and the UI suggests "Don't scale" instead.

Unit tests are required, with at least 30 realistic old-recipe-card lines.

### 6.5 Adjust (scaling)
- Shown only on scalable recipes.
- A slider with discrete stops, left to right: **¼, ⅓, ½, ⅔, 1, 1½, 2, 3, 4**, defaulting to 1. The selected multiplier is shown prominently.
- Scaling is view-only and never saved. A clear "Scaled ×2" banner appears while it's active, along with a Reset button.
- Split ingredients are re-rendered as the scaled quantity in the best unit, followed by the item. `no_scale` lines are shown unchanged with a subtle "not scaled" hint.
- **Unit conversion (`units.py`, `scaling.py`):**
  - Volume converts within tsp → tbsp → cup (3 tsp = 1 tbsp, 16 tbsp = 1 cup).
  - Weight converts within oz → lb (16 oz = 1 lb).
  - Choose the most readable unit. Values under 1 tbsp display as tsp. Values of 1/4 cup or more display as cups. Use a compound form when it reads better (e.g., "1 cup + 2 tbsp").
  - Display kitchen fractions (nearest ⅛, using ⅓ and ⅔ where closer), never long decimals.
  - Count units (eggs, cans, cloves, packages, sticks) are multiplied without conversion and rounded to the nearest ½ or ¼. Show "about" when rounding changes the value by more than about 5%.
  - Pinch and dash are never converted, just multiplied ("2 pinches").
  - Metric units scale within metric (g → kg, ml → l).
- Unit tests are required for the conversion and rounding rules.

### 6.6 Images
- Exactly one image per recipe.
- On mobile, the upload field offers both the camera and the photo library (`accept="image/*"`).
- Server-side processing: apply EXIF orientation (`ImageOps.exif_transpose`), strip metadata, resize to a max of 1600px on the long side, and save as JPEG quality 85 to `data/images/recipe-{id}-{timestamp}.jpg`.
- Generate a 400px thumbnail for list cards.
- Replacing an image deletes the old files. Removing the image is also an option.

### 6.7 Print, PDF, email, and iMessage

> **Superseded (2026-10-20):** email and iMessage sending were removed. They
> only worked by driving Mail.app/Messages.app on the host Mac, which can't
> carry over to a NAS/Docker deployment and always sent from the owner's
> accounts. Replaced by **Save image** (one stacked PNG, same rendering as the
> JPG below) and **Copy image** (clipboard; https/localhost only). Print and
> Save PDF are unchanged. The original design is kept below for reference.
- **Recipe PDF:** WeasyPrint from a dedicated print template that includes the title, metadata, image, ingredients, instructions, and notes. The result should look like a clean, modern recipe page.
- **Recipe JPG** (for iMessage): render the same PDF, rasterize it with PyMuPDF at about 150 DPI, and stack pages vertically into one JPG.
- **Email:** a modal asks for a recipient address (typed each time) and an optional message. The server builds the PDF and **sends immediately** via Mail.app using AppleScript (`osascript`), with the PDF attached and the subject "Recipe: {title}". The UI shows success or failure.
- **Text:** a modal asks for a phone number or iMessage email (typed each time). The server builds the JPG and **sends immediately** via Messages using AppleScript to the iMessage service. Known issue: Messages may silently fail to send attachments from arbitrary paths. If so, copy the file into `~/Pictures/RecipeShare/` first and send from there. Test this for real.
- Both share actions are accessible from the phone; the Mac does the sending.
- **Sharing abstraction:** `sharing/base.py` defines `send_email(to, subject, body, attachment)` and `send_imessage(to, body, attachment)`. `mac.py` implements both. `smtp.py` is a stub for email on the future NAS. When the backend can't do something (e.g., iMessage on the NAS), the UI hides that button.
- **README:** explain the one-time macOS prompts to allow Terminal (or Python) to control Mail and Messages under System Settings → Privacy & Security → Automation.

### 6.8 Print cookbook
- A page in the header or admin area to build the cookbook. It offers category checkboxes (all checked by default), a cover title (defaulting to `RECIPES_COOKBOOK_TITLE`), and include-images and include-notes toggles (both on by default).
- The output is a single PDF via WeasyPrint with:
  - A cover page showing the title and date.
  - A **table of contents** with page numbers, using WeasyPrint `target-counter`, grouped by category.
  - A category divider page before each category's recipes.
  - Each recipe starting on a new page.
  - Page numbers in the footer.
- Show a progress spinner while the PDF generates. The file is saved to `data/exports/` and downloaded.

### 6.9 Admin
- **Categories:** add, rename, reorder, and delete. Deleting a category leaves its recipes uncategorized; warn first with a count.
- **Export backup (.txt):** see section 7.
- **Needs-review queue:** a list of flagged recipes linking to edit mode with the scan shown side by side.

---

## 7. Plain-text backup export

This is a manual button in Admin. Its purpose is a portable export that can be read by a person or parsed later to move the data to another system. It writes `data/exports/recipes-backup-YYYY-MM-DD-HHMM.txt` and also downloads it.

The file is UTF-8 with a header line (app name, export timestamp, recipe count), then one block per recipe sorted by category and then title:

```
==================================================
RECIPE: Grandma's Pound Cake
ID: 42
CATEGORY: Desserts – Cakes
CONTRIBUTOR: Pat Cohen
SOURCE:
SERVINGS: 12
PREP TIME:
COOK TIME: 1 hr 15 min
RATING: 5
FAVORITE: yes
LAST MADE: 2026-09-14
NEEDS REVIEW: no
IMAGE FILE: recipe-42-20260914.jpg
SCAN FILE: recipes2-p007-a.jpg
ORIGIN: recipes2.pdf page 7
CREATED: ...
UPDATED: ...

INGREDIENTS:
## For the glaze:                          <- heading
- 2 cups flour, sifted   [qty=2 unit=cup item="flour, sifted"]
- salt to taste          [no-scale]
- 3 eggs                 <- unsplit lines have no bracket

INSTRUCTIONS:
(HTML converted to text: paragraphs separated by blank lines,
 bullets as "- ", numbered lists as "1. ", **bold**, *italic*)

NOTES:
[2026-09-14 18:22] Used less sugar, still great.
```

Every field is written even when empty, so the format stays stable. Image binaries are not included, only the filenames. Write a round-trip test that parses the export and checks it against the database.

---

## 8. Design
- Modern and clean, mobile-first. Use a neutral palette with one accent color, generous whitespace, and a readable system font stack. Ingredients and instructions should be large enough to read at arm's length in a kitchen.
- On desktop, the recipe view uses two columns (ingredients on the left, instructions on the right). On mobile it's a single column.
- The print stylesheet and the WeasyPrint templates share a look but hide all buttons.
- Follow accessibility basics: labels, focus states, adequate contrast, and touch targets of at least 44px.

---

## 9. Quality
- Use parameterized SQL everywhere. All multi-table writes happen in a single transaction.
- Sanitize rich text server-side. Validate uploads (image MIME type, size limit of about 25 MB).
- Validate email and phone inputs before calling AppleScript, and pass values as arguments, never by string-concatenating them into the script.
- Write pytest coverage for the parser, scaling and units, sanitizing, the export round-trip, and the CRUD services.
- The README covers setup (`python3 -m venv`, `brew install pango`, `pip install -r requirements.txt`), running (`python run.py`), finding the phone URL, macOS permissions, re-running the import, and future Docker notes.

---

## 10. Build phases (stop and report after each)
0. **Scaffold:** venv, config, database, migrations, app factory, base layout. Commit.
1. **Import (section 5):** render, crop, transcribe, then **STOP for category approval**, then load and report. Commit.
2. **Browse, search, and recipe view** (6.1, 6.2 without the share buttons).
3. **Edit, new, and delete;** categories admin; images; notes; I made this; needs-review queue.
4. **Ingredient splitting and Adjust scaling,** with tests.
5. **Print, PDF, and JPG; email and iMessage.** Test real sends with the owner.
6. **Cookbook PDF and txt backup,** with tests.
7. **Polish pass on mobile:** test on a phone over Wi-Fi.

After each phase, summarize what was built, what to try, and any open questions.
