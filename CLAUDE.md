# MoodBadger2350

Mood Badger: a MicroPython Badgeware app for the e-ink Pimoroni Badger 2350, ported from MoodBadger. The app is `badger/mood_badger/`; see `README.md` for layout and references.

## Development

- Set up: `git submodule update --init`, then `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`
- Test: `.venv/bin/pytest` (includes a headless simulator run when `node` is installed)
- MicroPython syntax: `.venv/bin/python -m mpy_cross -o /dev/null <file>` for each app module
- Lint: `.venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger`
- Simulator: `python3 sim/stage.py && python3 -m http.server -d sim/dist 8000`

Read hardware and runtime behaviour from the firmware source in `vendor/badger2350` (pinned to `v3.1.1`), not only from badgewa.re/docs: the docs can lag the source. Keep `badger/mood_badger/moods.py` free of Badgeware names so it stays testable on a desktop, and never call `badge.poll()` or `badge.update()` before `run(update)`, or the button press that woke the badge is lost.

## Claude Code plugins

This project requires the plugins below. They are declared in `.claude/settings.json`, and Claude Code offers to install them when you trust the project folder. If it doesn't, install them by hand:

```sh
claude plugin install superpowers@claude-plugins-official --scope project
claude plugin install claude-md-management@claude-plugins-official --scope project
```

| Plugin                 | Marketplace                          | Use it for                                                                                                 |
| ---------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `superpowers`          | `anthropics/claude-plugins-official` | Brainstorming, plans, TDD, systematic debugging, code review, verification                                 |
| `claude-md-management` | `anthropics/claude-plugins-official` | Auditing CLAUDE.md against the code (`claude-md-improver`), saving session learnings (`/revise-claude-md`) |

Plugin skills are namespaced: invoke `superpowers:brainstorming`, not `brainstorming`.

### Superpowers

Check for a relevant superpowers skill before starting work, and use it when one applies:

- New features or behavior changes: `superpowers:brainstorming`, then `superpowers:writing-plans`
- Carrying out a plan: `superpowers:executing-plans` or `superpowers:subagent-driven-development`
- Writing code: `superpowers:test-driven-development`
- Bugs and unexpected behavior: `superpowers:systematic-debugging`
- Before claiming work is done: `superpowers:verification-before-completion`
- Reviews: `superpowers:requesting-code-review`, `superpowers:receiving-code-review`
- Wrapping up: `superpowers:finishing-a-development-branch`
- Adding or improving a project skill under `.claude/skills/`: `superpowers:writing-skills`

### CLAUDE.md management

Use `claude-md-management:claude-md-improver` to check CLAUDE.md against the code after larger changes, and `/revise-claude-md` at the end of a session that turned up something future sessions need.
