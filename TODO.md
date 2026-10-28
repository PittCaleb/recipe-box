# TODO

The roadmap: open items, shelved for now. Nothing here blocks using the app day to day.

## User management

Right now anyone who gets past Cloudflare Access becomes a regular user automatically, and admins are set by hand in the
database (README → People and permissions). A real version would need: a users page for admins (list, promote/demote,
rename the display name, disable someone); deciding whether new sign-ins should wait for approval instead of being
auto-created; letting people set their own display name; transferring a recipe's ownership; and what happens to a
person's recipes, notes, and favorites if they're removed.

## Recipe image export — confirm in a real browser

- [ ] On the Mac at `http://127.0.0.1:5050`, open a recipe → **Copy image**,
  paste into Messages/Notes, confirm the image arrives intact.
- [ ] **Save image** on the Mac and on a phone — confirm the PNG downloads
  and is readable. (Copy is intentionally hidden on the phone's LAN address.)

## Phase 7 — mobile check on a real device

- [ ] On your phone or tablet, open the live app (on the home Wi-Fi and through
  the public sign-in address).
- [ ] Walk through: browse/search, open a recipe, use the Adjust slider,
  add a note, take/upload a photo, print, Save image.
- [ ] Check the Cards and Text views of the browse page on a real screen and
  a phone (sticky controls bar height on small screens in particular).
- [ ] Flag anything that looks cramped, misaligned, or hard to tap.

## Known data cleanup (from Phase 1 import, not urgent)

~18 duplicate/near-duplicate recipes exist across `recipes.pdf` and
`recipes2.pdf` (same dish transcribed more than once), plus a few
contributor-attribution conflicts. All are flagged with `needs_review` and
an explanatory note.

- [ ] Work through the 18 groups in **Menu → Admin → Duplicates** (compares
  them side by side, merges or dismisses each).
- [ ] Then clear the remaining non-duplicate items in the Needs-review queue.
