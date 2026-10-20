# Recipes

A personal recipe web app, served on the home Wi-Fi from the owner's Mac.

> **Note:** `pdf/` (source scans) and `data/` (the database, images, and
> everything else generated from them) are gitignored and not part of this
> repo — they contain real recipes and family info. A fresh clone starts
> with an empty database; see "Re-running the PDF import" below to load
> your own recipes.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
brew install pango   # required by WeasyPrint for PDF generation
pip install -r requirements.txt
```

## Running

```bash
python run.py
```

This prints the local URL and the LAN URL (for phones/tablets on the same Wi-Fi).

## Configuration

All settings are environment variables with sensible defaults; see `config.py`:

| Var | Default | Purpose |
|---|---|---|
| `RECIPES_DATA_DIR` | `./data` | All mutable data (db, images, scans, exports) |
| `RECIPES_HOST` | `0.0.0.0` | Listen address |
| `RECIPES_PORT` | `5050` | Port (5000 is taken by macOS AirPlay) |
| `RECIPES_SHARE_BACKEND` | `mac` on macOS, else `none` | `mac`, `smtp`, or `none` |
| `RECIPES_APP_PASSWORD` | unset | If set, editing/admin/sharing require login |
| `RECIPES_COOKBOOK_TITLE` | `Our Family Recipes` | Default cookbook cover title |

## macOS permissions (for email/text sharing)

Email and Text on a recipe page work by having the server run a small
AppleScript (via `osascript`) that tells Mail.app or Messages.app to send on
your behalf. The first time each happens, macOS shows a permission prompt:

- **"Terminal" (or "Python") wants access to control "Mail".** Click **OK**.
- **"Terminal" (or "Python") wants access to control "Messages".** Click **OK**.

If you click **Don't Allow** by accident (or need to re-enable later), go to
**System Settings → Privacy & Security → Automation**, find Terminal (or
whichever app is running `python run.py`), and turn on the Mail and Messages
toggles.

A few things worth knowing:
- **Mail.app and Messages.app must be signed in and set up** on this Mac —
  the app drives them, it doesn't implement email/iMessage itself.
- **Text** requires an active iMessage account signed in to Messages.app;
  sending to a non-iMessage phone number (green-bubble SMS) isn't supported
  by this integration.
- Attachments sent over Messages are first copied into
  `~/Pictures/RecipeShare/` — Messages can silently fail to attach files
  from arbitrary paths, and sending from that folder works around it. That
  folder will accumulate copies over time; it's safe to empty periodically.
- If `RECIPES_APP_PASSWORD` is set, Email/Text (like Edit and Admin) require
  logging in first.

## Re-running the PDF import

See `importer/` and SPEC.md section 5. The loader refuses to run if the
`recipes` table already has rows, to protect your edits — pass `--force` to
wipe and reload.

## Tests

```bash
pytest
```

## Future: Docker on the NAS

Not built yet. The app already avoids hard-coded paths and keeps all
mutable state under one data directory, so it should containerize cleanly
when that time comes.
