-- Staging area for the web-based "upload a new PDF" import flow. Recipes
-- land here first (AI-transcribed, not yet in the real recipes table) so
-- the owner can review/edit/exclude before committing, mirroring the
-- original Phase 1 "propose, then approve" flow.

CREATE TABLE import_batches (
  id              INTEGER PRIMARY KEY,
  source_pdf      TEXT NOT NULL,       -- filename under pdf/
  original_filename TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
    -- pending -> rendering -> transcribing -> ready -> done
    --                                       -> error
  total_pages     INTEGER,
  processed_pages INTEGER NOT NULL DEFAULT 0,
  error_message   TEXT,
  default_contributor TEXT,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE import_batch_recipes (
  id                INTEGER PRIMARY KEY,
  batch_id          INTEGER NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  source_page       INTEGER NOT NULL,
  title             TEXT NOT NULL,
  contributor       TEXT,
  source            TEXT,
  servings          TEXT,
  prep_time         TEXT,
  cook_time         TEXT,
  instructions_html TEXT NOT NULL DEFAULT '',
  proposed_category TEXT,
  needs_review      INTEGER NOT NULL DEFAULT 0,
  review_note       TEXT,
  scan_filename     TEXT,
  ingredients_json  TEXT NOT NULL DEFAULT '[]',
  notes_json        TEXT NOT NULL DEFAULT '[]',
  included          INTEGER NOT NULL DEFAULT 1,
  imported_recipe_id INTEGER
);
CREATE INDEX idx_import_batch_recipes_batch ON import_batch_recipes(batch_id);
