-- Marks a recipe's picture as a drawn placeholder rather than a real photo,
-- so a real photo always replaces it. The 59 drawn on 2026-10-28 all share
-- that run's timestamp in their filenames.
ALTER TABLE recipes ADD COLUMN image_is_placeholder INTEGER NOT NULL DEFAULT 0;

UPDATE recipes SET image_is_placeholder = 1
WHERE image_filename LIKE 'recipe-%-20261028180254.jpg';
