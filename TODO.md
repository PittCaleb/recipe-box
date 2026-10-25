# TODO

Open items, shelved for now — nothing here blocks using the app day to day.

## Recipe image export — confirm in a real browser

- [ ] On the Mac at `http://127.0.0.1:5050`, open a recipe → **Copy image**,
  paste into Messages/Notes, confirm the image arrives intact.
- [ ] **Save image** on the Mac and on a phone — confirm the PNG downloads
  and is readable. (Copy is intentionally hidden on the phone's LAN address.)

## Phase 7 — mobile check on a real device

- [ ] On your phone or tablet (same Wi-Fi as the Mac), open the LAN URL
  `run.py` prints on startup (e.g. `http://192.168.1.20:5050`).
- [ ] Walk through: browse/search, open a recipe, use the Adjust slider,
  add a note, take/upload a photo, print, Save image.
- [ ] Flag anything that looks cramped, misaligned, or hard to tap.

## Feature request — browse page: card/text view toggle

- [x] Toggle on the home page between the current image/card grid and a
  compact text-list view.
- [x] Text list: multi-column layout (1/2/3 columns by screen width), with
  alphabetical section headers (A, B, C...) and spacing between groups.
- [x] Headers switch to category names — built as an explicit A–Z /
  Category toggle rather than tied to the category filter. Category
  sections follow the Admin → Categories order.
- [x] Within each section, recipes sorted alphabetically.
- [ ] Verify the look on a real screen and a phone (sticky controls bar
  height on small screens in particular).

## Known data cleanup (from Phase 1 import, not urgent)

~18 duplicate/near-duplicate recipes exist across `recipes.pdf` and
`recipes2.pdf` (same dish transcribed more than once), plus a few
contributor-attribution conflicts. All are flagged with `needs_review` and
an explanatory note.

- [x] Built **Menu → Admin → Duplicates**: finds 18 likely-duplicate groups,
  compares them side by side, merges or dismisses each.
- [ ] Work through the 18 groups.
- [ ] Then clear the remaining non-duplicate items in the Needs-review queue.