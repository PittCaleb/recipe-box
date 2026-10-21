CREATE TABLE duplicate_dismissals (
  recipe_a   INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  recipe_b   INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  PRIMARY KEY (recipe_a, recipe_b),
  CHECK (recipe_a < recipe_b)
);
