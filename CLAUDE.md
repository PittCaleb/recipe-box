@AGENTS.md

# Working with the owner (Claude Code)

AGENTS.md, imported above, is the project guide that every coding agent reads. This file adds how the owner works, for Claude
Code on the owner's machine. `CLAUDE.local.md` (gitignored) has the machine, the server and the deploy commands.

- **Commit, push and open a PR only when asked.** The usual words are "commit this, push it and create the pr". Branch off
  an up-to-date `main` for each piece of work. Bundle related work into one PR rather than splitting it finely.
- **Deploying touches production.** Do it when the owner says to ("go ahead and deploy"); the permission check blocks it
  otherwise. The steps are in `CLAUDE.local.md`.
- **The NAS copy is the live data.** `data/` on the Mac is only a copy; refresh it with
  `scripts/pull-live-data.sh` (stop the local app first). Never copy local data over the NAS.
- This Mac can't compile C extensions (the Xcode license was never accepted, so clang refuses to run), hence the
  prebuilt-wheels rule in AGENTS.md.

## Deploying

See `CLAUDE.local.md` for the server, the commands and the checks. In short: merge the PR, wait for the **Docker image**
Action (`gh run list --limit 1`), snapshot the live database if a migration is going out, update the container, then check
the home and public addresses. Right after a restart there's a few seconds of 502 while the app starts, so retry before
worrying. New settings must be in the server's env file **before** the image that needs them starts.

- **Before deploying a migration,** copy the live database (from the latest backup archive on the NAS, or a fresh snapshot)
  to the scratchpad, run the migration against the copy, and render every page as admin and as a member.
- Snapshot the live DB in the container right before deploying (command in `CLAUDE.local.md`).
