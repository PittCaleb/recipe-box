# TODO

Open items, shelved for now — nothing here blocks using the app day to day.

## Phase 5 — confirm real sharing sends

- [ ] Open a recipe → **Email**, send to a real address, confirm it arrives.
  First attempt will trigger a macOS prompt: "Terminal (or Python) wants
  access to control Mail." Click OK.
- [ ] Open a recipe → **Text**, send to a real phone/iMessage address, confirm
  it arrives. First attempt will trigger a similar prompt for Messages.
- [ ] If either fails, report the exact error text back — the sharing code
  is in `app/sharing/mac.py`.

## Phase 7 — mobile check on a real device

- [ ] On your phone or tablet (same Wi-Fi as the Mac), open the LAN URL
  `run.py` prints on startup (e.g. `http://192.168.0.137:5050`).
- [ ] Walk through: browse/search, open a recipe, use the Adjust slider,
  add a note, take/upload a photo, print.
- [ ] Flag anything that looks cramped, misaligned, or hard to tap.

## Known data cleanup (from Phase 1 import, not urgent)

~18 duplicate/near-duplicate recipes exist across `recipes.pdf` and
`recipes2.pdf` (same dish transcribed more than once), plus a few
contributor-attribution conflicts. All are flagged with `needs_review` and
an explanatory note — see **Admin → Needs-review queue** to work through
them whenever you feel like it.
