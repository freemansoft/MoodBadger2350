---
name: mood-docs
description: Writing and formatting standard for Mood Badger's Markdown (README.md, badger/mood_badger/README.md, CLAUDE.md, docs/, sim/wasm/SOURCE.md and the skill files). Use whenever you create or edit any .md file in this repo, and before every commit that includes Markdown, since the pre-commit hook and CI reject unformatted files. Covers prettier (the version in .prettier-version), line style, tables, tone and spelling, which doc owns which topic, link anchors, and the tests that pin doc content.
---

# Mood Badger documentation standard

(Adapted from freemansoft/claude-buddy-badgeware's `buddy-docs` skill.)

## Formatting: prettier, pinned

All Markdown is formatted with prettier at the version in `.prettier-version`, with the settings in `.prettierrc.json` (`proseWrap: preserve`). The version lives only in that file, so everyone's tables and lists come out byte-identical; an unpinned `npx prettier` can reformat files nobody touched. `tests/project/test_dev_tools.py` fails if any other file writes the version number after `prettier@`, so in docs write `prettier@$(cat .prettier-version)`.

After editing Markdown, and before committing:

```bash
npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --write <changed .md files>
git ls-files -z '*.md' | xargs -0 npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --check
```

The second command is CI's check. It only sees tracked files, so check a new, not yet added `.md` file by name as well.

`.githooks/pre-commit` checks the staged `.md` files (and lints staged Python) and blocks the commit if any fail. It's active when `git config core.hooksPath` prints `.githooks`; if it doesn't, tell the user rather than setting it silently. Don't bypass the hook with `--no-verify`; format the files instead.

To change the prettier version, edit `.prettier-version` only, then reformat every tracked `.md` file with the new version in the same commit.

## Line style

`proseWrap: preserve` means prettier never rewraps prose, so the line style is whatever the file already uses:

- **One line per paragraph or list item:** `README.md`, `CLAUDE.md`, `badger/mood_badger/README.md` and `docs/superpowers/plans/`. This is the repo's main style; use it for new files.
- **Hand-wrapped at about 75 columns:** the older skill files (`badge-deploy`, `badge-firmware`, `badge-verify`, `badgeware-platforms`), `sim/wasm/SOURCE.md` and `docs/superpowers/specs/`. When editing one of these, wrap new prose to match the lines around it, with list continuation lines indented to the item's text. The front matter `description` is always one line.

Other layout rules:

- Tables are never wrapped; prettier aligns them, and wide tables are fine (the README has several). Keep cells short enough to scan and put long explanations in prose below.
- Code, commands, file paths and config keys go in backticks. Shell blocks are `sh` in the README and `bash` in the skills; JSON examples are `json`.
- Badge buttons are bold in user-facing docs (**RESET**, **HOME**, **UP**), plain capitals in skills.
- `**Bold lead-in:**` for the key term at the start of a bullet.

## Tone and spelling

The README and the app's README are for people setting up a badge for a child, often not programmers. Write plain, short sentences.

- British spelling, matching the existing docs: _colour_, _behaviour_, _licence_ (the noun), _customising_.
- One word for one thing: Pimoroni's launcher is always "the menu", never another name (`tests/project/test_docs.py` checks every doc it lists for the old one). The badges are "Badger 2350" and "Tufty 2350", or "Badger" and "Tufty" once that's clear.
- Say what happens, with the number: "sleeps after 5 seconds on battery", "dims after 10 seconds".
- Be honest about what's unverified. Anything not yet seen on a real badge says so ("not yet measured", "haven't been seen on a badge"), and the `badgeware-platforms` skill keeps the record of what was checked on hardware.
- Explain why, briefly, when a choice isn't obvious.

## Which doc owns what

Each topic has one home. Other docs summarise and link to it instead of copying it, so they can't drift apart.

| Topic                                                                            | Home                                                   |
| -------------------------------------------------------------------------------- | ------------------------------------------------------ |
| What the app is, Badger vs Tufty for users, install, controls, power, moods      | `README.md`                                            |
| What the badge opens: menu, start-in-app, kiosk                                  | `README.md` "What the badge opens"                     |
| The short guide that travels with the app folder (and to `badgeware-contrib`)    | `badger/mood_badger/README.md`                         |
| Development setup, checks, test layers in brief, simulator use                   | `README.md` "Development"                              |
| Instructions for Claude: commands, button-press and `mpremote` rules, plugins    | `CLAUDE.md`                                            |
| Badger vs Tufty in the firmware, with source references and what was confirmed   | `badgeware-platforms` skill                            |
| Which test layers a change needs, simulator and hardware checks, hand checklists | `badge-verify` skill                                   |
| Installing the app and setting what the badge opens                              | `badge-deploy` skill                                   |
| Checking and flashing firmware                                                   | `badge-firmware` skill; `README.md` "Install" in brief |
| Where the simulator builds came from, how to update them, the host contract      | `sim/wasm/SOURCE.md` (and `sim/wasm/VERSION.json`)     |
| Markdown standard                                                                | this skill                                             |
| Past designs and plans                                                           | `docs/superpowers/specs/`, `docs/superpowers/plans/`   |
| Licences: MIT code, Apache 2.0 Material images                                   | `README.md` "Licence", `LICENSE`, `assets/LICENSE`     |

The files under `docs/superpowers/` are dated records of past work. Leave what they say as written; don't update them to match later changes.

When you change a number (a timeout, the firmware version, the 16-mood limit, the 122×136 image size), grep the docs for the old value: some numbers appear in several places on purpose, as summaries. `v3.1.1`, for example, is in the README, the app's README, `CLAUDE.md`, the skills and `tools/install.py`.

## Links and anchors

- Link between docs with relative paths (`kiosk/main.py`, `badger/mood_badger/README.md`).
- Renaming a heading changes its anchor. Before renaming, grep the repo for `#<old-anchor>` and fix every link; `tests/project/test_docs.py` fails on a README link to a missing heading.
- External references go in the README's References section, with what each one is used for.

## Tests that pin doc content

Docs are tested like code; run `.venv/bin/pytest -q` after a doc change.

- `tests/project/test_docs.py`: the README's Mac copy command and internal links; the licence text; the name of the menu; and that every `vendor/`, `tests/`, `tools/`, `sim/`, `kiosk/` and `badger/` file and every `python3 -m tools.<name>` that the README, `CLAUDE.md`, the app README, `sim/wasm/SOURCE.md` and the skills cite exists. Move or rename a file, and the docs that cite it fail here.
- `tests/project/test_skills.py`: every skill's front matter names its folder and has a description.
- `tests/tools/test_update_sim.py`: `sim/wasm/SOURCE.md` names the same build as `VERSION.json`.
- `tests/project/test_dev_tools.py`: no file other than `.prettier-version` names the prettier version.

If a test fails because a doc was deliberately changed, update the test in the same change.
