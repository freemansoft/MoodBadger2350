# MoodBadger2350

Mood Badger: a MicroPython Badgeware app for the Pimoroni Badger 2350 (e-ink) and Tufty 2350 (colour LCD), ported from MoodBadger. One app folder, `badger/mood_badger/`, runs on both; see `README.md` for layout and references.

## Development

- Set up: `git submodule update --init`, then `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`, then `git config core.hooksPath .githooks` (the pre-commit hook checks staged Markdown with prettier, runs `ruff check` on staged Python, and compiles staged `badger/mood_badger` and `kiosk` files with mpy-cross)
- Dev tools are pinned: every line of `requirements-dev.txt` is `==` (`tests/project/test_dev_tools.py` checks), and prettier's version is only in `.prettier-version`. Bump a pin on purpose, then rerun every check
- Test: `.venv/bin/pytest` (includes a headless simulator run when `node` is installed)
- MicroPython syntax: `for f in badger/mood_badger/*.py kiosk/*.py; do .venv/bin/python -m mpy_cross -o /dev/null "$f"; done` (the `kiosk/` boot files go on the badge too)
- Lint: `.venv/bin/ruff check .` (`ruff.toml` extends Pimoroni's `vendor/badger2350/ci/ruff.toml`; `tests/project/test_ruff_config.py` fails if the Tufty's copy ever differs). `ruff format` is not used: Pimoroni's firmware CI only runs `ruff check`, and the formatter would rewrite most files
- Markdown: `npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --write <files>`; the version is only in `.prettier-version`, which the hook and CI read. The `mood-docs` skill has the rest of the Markdown standard
- CI (`.github/workflows/ci.yml`) runs the lint, MicroPython syntax, tests and Markdown checks on every PR and push to `main`
- Simulator: `python3 sim/stage.py && python3 -m http.server -d sim/dist 8000`, then `/badger/` or `/tufty/`. Headless: `node sim/run_headless.mjs --model tufty --press DOWN --frames out.json`. `python3 -m tools.update_sim --check` compares the pinned wasm builds and firmware tags (`sim/wasm/VERSION.json`) with Pimoroni's latest (needs `gh` and the network); without `--check` it downloads them (see `sim/wasm/SOURCE.md`)
- Project skills: `badgeware-platforms` (how the Badger and Tufty differ; read it before writing app code for either), `badge-verify` (which test layers a change needs, simulator and hardware checks, hand checklists), `badge-deploy` (install the app and set what the badge opens), `badge-firmware` (check or flash firmware) and `mood-docs` (Markdown standard and which doc owns which topic; read it before editing any `.md` file). The tools they drive run as modules from the repository root (`python3 -m tools.install`)
- Button presses on a real badge: start the tool with `--wait 180` in the background and end the turn with the instructions; tell the user not to touch the badge until the tool says "Ejected" or "Flash complete". Never assume a press happened; read the result
- Ad-hoc `mpremote`: take the port whose `mpremote devs` line names the badge you mean (`Badger 2350` or `Tufty 2350`; other boards are often plugged in too), and end with `reset` (`mpremote connect <port> exec "..." reset`), or the badge stays frozen on its last screen until RESET. `reset` is `machine.reset()`: a Badger reopens the app it was showing, and a Tufty (stock or start-in-app) opens the menu (RESET brings Mood Badger back on a start-in-app Tufty). `/system` (the drive) is read-only from MicroPython, so files only change in disk mode
- Check a copy from the badge's side after the eject (`python3 -m tools.badge_check files`), not by reading the mounted drive: macOS holds writes in its cache until the eject

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
