# TODO

The roadmap: open items, shelved for now. Nothing here blocks using the app day to day.

## User management

Right now anyone who gets past Cloudflare Access becomes a regular user automatically, and admins are set by hand in the
database (README → People and permissions). A real version would need: a users page for admins (list, promote/demote,
rename the display name, disable someone); deciding whether new sign-ins should wait for approval instead of being
auto-created; letting people set their own display name; transferring a recipe's ownership; and what happens to a
person's recipes, notes, and favorites if they're removed.

## License

There's no LICENSE yet, so nobody else may legally reuse the code. Pick one (e.g. MIT).
