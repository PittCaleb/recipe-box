-- People are known by the email they sign in with (see app/users.py).
-- User 1 (the owner; set their real sign-in email with
--   UPDATE users SET email = '...' WHERE id = 1;)
-- owns everything that existed before; anyone else is added on their
-- first visit as a regular user. Promote someone to admin with:
--   UPDATE users SET is_admin = 1 WHERE email = 'them@example.com';
CREATE TABLE users (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
  display_name  TEXT NOT NULL,
  is_admin      INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL,
  last_seen_at  TEXT
);

INSERT INTO users (id, email, display_name, is_admin, created_at)
VALUES (1, 'owner@example.com', 'Owner', 1, strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'));

ALTER TABLE recipes ADD COLUMN owner_id INTEGER REFERENCES users(id);
UPDATE recipes SET owner_id = 1;

ALTER TABLE notes ADD COLUMN author_id INTEGER REFERENCES users(id);
UPDATE notes SET author_id = 1;

-- Favorites, ratings, and "I made this" are each person's own. The shared
-- values recorded so far become user 1's.
CREATE TABLE user_recipes (
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  recipe_id  INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  favorite   INTEGER NOT NULL DEFAULT 0,
  rating     INTEGER CHECK (rating BETWEEN 1 AND 5),
  last_made  TEXT,
  PRIMARY KEY (user_id, recipe_id)
);
CREATE INDEX idx_user_recipes_recipe ON user_recipes(recipe_id);

INSERT INTO user_recipes (user_id, recipe_id, favorite, rating, last_made)
SELECT 1, id, favorite, rating, last_made FROM recipes
WHERE favorite = 1 OR rating IS NOT NULL OR last_made IS NOT NULL;

ALTER TABLE recipes DROP COLUMN favorite;
ALTER TABLE recipes DROP COLUMN rating;
ALTER TABLE recipes DROP COLUMN last_made;
