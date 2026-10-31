# TODO

The roadmap: open items, shelved for now. Nothing here blocks using the app day to day.

## User management

Right now anyone who gets past Cloudflare Access becomes a regular user automatically, and admins are set by hand in the
database (README → People and permissions). A real version would need: a users page for admins (list, promote/demote,
rename the display name, disable someone); deciding whether new sign-ins should wait for approval instead of being
auto-created; letting people set their own display name; transferring a recipe's ownership; and what happens to a
person's recipes, notes, and favorites if they're removed.

## Personal details in the git history

The current files are clean: machine names, addresses and emails live in the gitignored `CLAUDE.local.md`. But this repo
is already public, and five commits from 2026-10-26 to 10-28 (`0d85be1`, `b285a84`, `1f51cd0`, `55bb231`, `014b95c`)
still contain the owner's home hostname and LAN IP, the NAS SSH login and paths, the owner's email and the Cloudflare
Access team domain. None are passwords or keys. Options: leave them, or rewrite history (`git filter-repo --replace-text`)
and force-push, which changes every commit ID since then and means re-cloning. GitHub may keep cached views of old
commits for a while, so treat the values as already seen either way.

Also for contributors: there's no LICENSE yet, so nobody else may legally reuse the code. Pick one (e.g. MIT).
