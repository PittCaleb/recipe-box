CREATE TABLE schema_version (
  version     INTEGER NOT NULL,
  applied_at  TEXT NOT NULL
);

CREATE TABLE categories (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
  sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE recipes (
  id                INTEGER PRIMARY KEY,
  title             TEXT NOT NULL,
  category_id       INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  contributor       TEXT,
  source            TEXT,
  servings          TEXT,
  prep_time         TEXT,
  cook_time         TEXT,
  instructions_html TEXT NOT NULL DEFAULT '',
  image_filename    TEXT,
  scan_filename     TEXT,
  source_pdf        TEXT,
  source_page       INTEGER,
  needs_review      INTEGER NOT NULL DEFAULT 0,
  favorite          INTEGER NOT NULL DEFAULT 0,
  rating            INTEGER CHECK (rating BETWEEN 1 AND 5),
  last_made         TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE TABLE ingredients (
  id           INTEGER PRIMARY KEY,
  recipe_id    INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  position     INTEGER NOT NULL,
  kind         TEXT NOT NULL DEFAULT 'item' CHECK (kind IN ('item','heading')),
  raw_text     TEXT NOT NULL,
  is_split     INTEGER NOT NULL DEFAULT 0,
  quantity     REAL,
  quantity_max REAL,
  unit         TEXT,
  item         TEXT,
  no_scale     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_ingredients_recipe ON ingredients(recipe_id, position);

CREATE TABLE notes (
  id         INTEGER PRIMARY KEY,
  recipe_id  INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  body       TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Full-text search over title, category name, contributor, and ingredient raw text.
-- Kept in sync from the service layer on every recipe save/delete (full rebuild is fine at this scale).
CREATE VIRTUAL TABLE recipes_fts USING fts5(
  title,
  category_name,
  contributor,
  ingredients_text,
  prefix='2 3 4'
);
