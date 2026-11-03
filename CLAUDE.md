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

This project requires the plugins below. They are declared in `.claude/settings.json`, and a `SessionStart` hook there installs any that are missing, at project scope. To install them by hand:

```sh
claude plugin install superpowers@claude-plugins-official --scope project
claude plugin install skill-creator@claude-plugins-official --scope project
```

| Plugin          | Marketplace                          | Use it for                                                                       |
| --------------- | ------------------------------------ | -------------------------------------------------------------------------------- |
| `superpowers`   | `anthropics/claude-plugins-official` | Brainstorming, plans, TDD, systematic debugging, code review, verification       |
| `skill-creator` | `anthropics/claude-plugins-official` | Creating and improving skills, running skill evals, tuning skill descriptions    |

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

### Skill creator

Use `skill-creator:skill-creator` to add a project skill under `.claude/skills/`, or to improve an existing one, including measuring it with evals and tuning its description so it triggers reliably.
