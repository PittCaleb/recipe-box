# Contributing

Thanks for taking a look. This is a small family cookbook app, so changes are welcome but kept simple.

## Getting set up

Follow README.md → Setup and Running. You need Python 3.14; PDF generation also needs `pango` (`brew install pango` on a
Mac). No API key is needed unless you're working on PDF import or placeholder pictures, and the tests never call it.

```bash
.venv/bin/python run.py          # http://localhost:5050
.venv/bin/python -m pytest -q    # the whole suite, about 15 seconds
```

## Making a change

- Branch off an up-to-date `main` and open a pull request. One PR per piece of work; related changes can go together.
- Add or update tests for what you change, and make sure the whole suite passes.
- Read **AGENTS.md** before a larger change. It explains how the app fits together and the rules to keep, such as building
  every link with `url_for` (the app runs under a `/recipes/` prefix), enforcing permissions on the server, and keeping
  the JSON API backwards compatible. If you use a coding agent, it reads AGENTS.md itself.
- Pin exact versions in `requirements.txt`, choosing releases with prebuilt wheels for Python 3.14 on macOS arm64 and
  Linux amd64.
- Keep UI text plain and friendly, and check pages on a phone as well as a desktop browser.
- **This repo is public:** use made-up people and `example.com` addresses in tests and examples, and never commit real
  names, addresses, server details or keys.
