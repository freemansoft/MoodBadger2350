# MoodBadger2350

Mood Badger: a MicroPython Badgeware app for the e-ink Pimoroni Badger 2350, ported from MoodBadger. The app is `badger/mood_badger/`; see `README.md` for layout and references.

## Development

- Set up: `git submodule update --init`, then `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`
- Test: `.venv/bin/pytest` (includes a headless simulator run when `node` is installed)
- MicroPython syntax: `.venv/bin/python -m mpy_cross -o /dev/null <file>` for each app module
- Lint: `.venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger`
- Simulator: `python3 sim/stage.py && python3 -m http.server -d sim/dist 8000`
- Real badge: use the project skills `badge-deploy` (copy the app in disk mode) and `badge-firmware` (check or flash firmware in bootloader mode). They drive `tools/badge_info.py`, `tools/install.py` and `tools/flash_firmware.py`, which run as modules (`python3 -m tools.install`). For a button press, start the tool with `--wait 180` in the background and end the turn with the instructions; tell the user not to touch the badge until the tool says "Ejected" or "Flash complete"
- Ad-hoc `mpremote`: take the port whose `mpremote devs` line says `Badger 2350` (a Tufty and other boards are often plugged in too), and end with `reset` (`mpremote connect <port> exec "..." reset`), or the badge stays frozen on its last screen until RESET. `/system` (the drive) is read-only from MicroPython, so files only change in disk mode
- Check a copy from the badge's side after the eject (list `/system/apps/mood_badger` over `mpremote`), not by reading the mounted drive: macOS holds writes in its cache until the eject
- Badger vs Tufty differences (run loop, screen, boot flow, missing names): see the `badgeware-platforms` skill before writing app code for either badge

Read hardware and runtime behaviour from the firmware source in `vendor/badger2350` and `vendor/tufty2350` (both pinned to `v3.1.1`), not only from badgewa.re/docs: the docs can lag the source. Keep `badger/mood_badger/moods.py` free of Badgeware names so it stays testable on a desktop, and never call `badge.poll()` or `badge.update()` before `run(update)`, or the button press that woke the badge is lost.

## Claude Code plugins

This project requires the plugins below. They are declared in `.claude/settings.json`, and Claude Code offers to install them when you trust the project folder. If it doesn't, install them by hand:

```sh
claude plugin install superpowers@claude-plugins-official --scope project
claude plugin install skill-creator@claude-plugins-official --scope project
claude plugin install claude-md-management@claude-plugins-official --scope project
```

| Plugin                 | Marketplace                          | Use it for                                                                                                 |
| ---------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `superpowers`          | `anthropics/claude-plugins-official` | Brainstorming, plans, TDD, systematic debugging, code review, verification                                 |
| `skill-creator`        | `anthropics/claude-plugins-official` | Creating and improving skills, running skill evals, tuning skill descriptions                              |
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

### CLAUDE.md management

Use `claude-md-management:claude-md-improver` to check CLAUDE.md against the code after larger changes, and `/revise-claude-md` at the end of a session that turned up something future sessions need.

### Skill creator

Use `skill-creator:skill-creator` to add a project skill under `.claude/skills/`, or to improve an existing one, including measuring it with evals and tuning its description so it triggers reliably.

Its trigger evals (`run_eval.py`, `run_loop.py`) run every query in this repo at once while the real skill is still installed, so Claude may pick the real skill or another run's copy, which counts as a miss. Patch a copy of the scripts to give each query its own project folder (symlinks to the repo, without the skill under test or `settings.local.json`).
