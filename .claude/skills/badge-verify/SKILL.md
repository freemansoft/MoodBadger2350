---
name: badge-verify
description: How to test and verify a Mood Badger change on both badges (Badger 2350 e-ink and Tufty 2350 LCD) - which test layers a change needs, the exact commands (pytest with the fake Badgeware, mpy-cross and ruff, the headless and browser badgeware-wasm simulator for each badge, rendering simulator frames to images), and the real-hardware checks (badge_info, install, checking the copy from the badge's side, reading wake reasons with a watcher) with a hand checklist for each badge. Use it whenever you change badger/mood_badger, kiosk/, tools/ or sim/, bump firmware, finish a feature, prepare or review a PR, or the user asks to test, verify, smoke-test, check on the badge, "make sure it still works on the Badger", or try something in the simulator - even if they only say "is it done?". For the install itself use badge-deploy; for firmware, badge-firmware.
---

# Verifying Mood Badger on both badges

Mood Badger is a communication aid a child relies on, and the Badger is in
real use, so a change isn't done until it has passed every layer it can
break. The layers get slower and need more of the user's time as you go
down; each catches things the one above can't. Run them in this order and
stop to fix anything that fails before moving on.

Read the `badgeware-platforms` skill first if the change touches app code:
most cross-badge bugs come from the run loop, screen and start-up
differences listed there.

## Which layers a change needs

| Change                                             | Layers                                                                 |
| -------------------------------------------------- | ---------------------------------------------------------------------- |
| `moods.py` logic, config parsing                   | 1, 2                                                                   |
| `__init__.py` (drawing, buttons, backlight, sleep) | 1-4, then 5 on both badges                                             |
| Layout numbers, pictures, labels, `config.json`    | 1-4 (look at both pages), then 5                                       |
| `kiosk/*.py` boot files                            | 1, then 5 with a wake-reason check                                     |
| `tools/*.py`                                       | 1, then the tool once against a real badge                             |
| `sim/`                                             | 1, 3, 4                                                                |
| Firmware bump (`vendor/*`)                         | all, on both badges, after re-checking the `badgeware-platforms` table |

## 1. Unit tests (seconds)

```bash
.venv/bin/pytest -q
```

This includes layer 3 when `node` is installed. The app tests run the
real `badger/mood_badger/__init__.py` against `tests/app/fake_badgeware.py`:

- `run_app(ticks, model="badger" | "tufty", usb=True | [per tick], frame_ms=1000, saved=..., config_text=..., files_missing=..., files_corrupt=..., blit_fails=...)`. Each tick is the set of buttons pressed that frame.
- `model="tufty"` models the Tufty's `run()` (a clear before every
  `update()`, a display refresh after it) and leaves out the Badger-only
  names (`NON_BLOCKING`, `wait_for_button_or_alarm`, `badge.first_update`),
  so using one fails the test.
- The result records `events`, `blits`, `blit_rects`, `texts`, `saved`,
  `backlight`, `loads`, `clear_pens`, `text_pens`, `waits` and `exit`
  (the module's `on_exit`).
- The fake's `pressed` is level-based: a button in two ticks counts as two
  presses. On the badge it fires once, when the button goes down, so give
  each press its own tick with an empty tick between.

Write the failing test before the change (superpowers TDD). A test that
passes before the change tests nothing.

## 2. MicroPython checks (seconds)

```bash
for f in badger/mood_badger/*.py kiosk/*.py; do .venv/bin/python -m mpy_cross -o /dev/null "$f"; done
.venv/bin/ruff check .
```

CPython accepts things MicroPython doesn't; mpy-cross catches them. The
ruff config lists Badgeware's builtins, so an undefined name is an error.
`ruff.toml` extends Pimoroni's `vendor/badger2350/ci/ruff.toml` and covers
the whole repository, not only the app.

The pre-commit hook runs the same ruff and mpy-cross checks on the staged
Python, so a commit can't skip them. The tools are pinned in
`requirements-dev.txt`; if `.venv` has other versions, reinstall it.

If the change touches Markdown, also run
`npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --check <files>`;
CI and the pre-commit hook fail on unformatted Markdown. The `mood-docs`
skill has the rest of the Markdown standard.

## 3. Headless simulator (seconds per run)

```bash
python3 sim/stage.py
node sim/run_headless.mjs --model tufty --press DOWN --frames /tmp/out.json
```

This runs the real firmware Python and the unmodified app in Pimoroni's
badgeware-wasm builds (`sim/wasm/<model>/`). The JSON has `status`, `width`,
`height`, and `before`/`after` frames as grey bytes. The tests in
`tests/sim/test_sim.py` check pixels in them. To look at a frame without a
browser, write it as an image and read it:

```bash
python3 - <<'EOF'
import json
d = json.load(open("/tmp/out.json"))
open("/tmp/after.pgm", "wb").write(b"P5 %d %d 255\n" % (d["width"], d["height"]) + bytes(d["after"]))
EOF
sips -s format png /tmp/after.pgm --out /tmp/after.png   # macOS; then Read the PNG
```

This is how the Tufty's off-white `color.white` was found: the tests
passed, but the picture sat in a visible box.

The builds are pinned in `sim/wasm/VERSION.json` (with the firmware tag
each runs with). Before a firmware bump, or when the simulator and a real
badge disagree, see whether Pimoroni has newer ones:

```bash
python3 -m tools.update_sim --check   # exits 1 if a newer build or firmware tag exists
```

It needs the GitHub CLI logged in and the network; `tests/tools/test_update_sim.py`
stubs both. Without `--check` it downloads the newest builds and moves the
submodules: that is a firmware bump, so run every layer afterwards and
follow `sim/wasm/SOURCE.md`.

## 4. Browser simulator (the user looks)

```bash
python3 sim/stage.py && python3 -m http.server -d sim/dist 8000
```

Open `http://localhost:8000/badger/` and `/tufty/`. Keys: arrows are UP
and DOWN; `a`, `b`, `c`, `h` are A, B, C, HOME. The Tufty page dims after
10 s, as on USB. If Claude in Chrome is connected, check it yourself;
otherwise ask the user to look at both pages. The simulator doesn't model
sleep, waking, e-ink refresh, battery power or restart reasons; those need
layer 5.

## 5. Real badges (the user's hands)

Use the `badge-firmware` and `badge-deploy` skills for firmware and
installs, and CLAUDE.md's rule for button presses (a background
`--wait`, instructions last, hands off until the result).

- **Two badges plugged in:** the tools ask for `--port`; `mpremote devs`
  names each one (`Badger 2350`, `Tufty 2350`). A badge on battery sleeps
  and drops off USB: ask the user to plug it in and press RESET.
- **Every mpremote read ends with `machine.reset()`.** A Badger then
  reopens the app it was showing; a Tufty (stock or start-in-app) shows
  the menu, which is expected, and RESET brings Mood Badger back on a
  start-in-app Tufty. Don't read the badge while the user is checking
  what the screen shows: ask first, then read.

Steps:

1. `python3 -m tools.badge_info`: model, firmware current, start-up mode.
2. Install with the `badge-deploy` skill (it has the hands-off
   instructions). Expect `Start-up:` as intended and "Ejected".
3. Check the copy from the badge's side (macOS can hold writes until the
   eject, so the mounted drive can look right when the badge isn't):
   `python3 -m tools.badge_check files`. Expect no "missing", "different
   size", "not in the app" or "macOS junk" (`._` or `__pycache__`) lines.
4. Boot files or firmware changed: confirm the restart reasons. Run
   `python3 -m tools.badge_check wake-reason --after-restart 180` in the
   background and ask for a single RESET tap: expect `WAKE_RESET` (241).
   `machine.reset()`, HOME and the restart after an eject give
   `WAKE_WATCHDOG` (242). A double-tap gives `WAKE_DOUBLETAP` (5) and
   disk mode. If the user double-tapped, say so; it isn't a fault. The
   `badgeware-platforms` skill holds these codes and what was confirmed
   on hardware; update it if a badge reports something else.
5. Hand checklist below, for each badge the change can affect. Ask the
   user to report anything that looks wrong at each step.

### Tufty 2350 checklist

1. RESET once: Mood Badger opens (picture, label, ◀ ▶, pips).
2. ◀ and ▶ sit above the A and C buttons.
3. UP/DOWN change the mood; A/C change the set.
4. Left alone ~10 s on USB: dims to about half.
5. A press while dimmed only brightens; the next press changes the mood.
6. Dim again, unplug USB: drops to about 15% without a press; the mood
   is still readable in room light.
7. HOME opens the menu.
8. Choose Mood Badger in the menu: it opens.
9. HOME, then RESET: Mood Badger opens, not the menu.
10. Hold RESET until the case lights fade (off), then a front button:
    Mood Badger with the same mood; that press doesn't change it.
11. After a firmware flash only: note what it opens, and record it in
    `badgeware-platforms` (not yet seen).

### Badger 2350 checklist

1. Open Mood Badger: same layout as before.
2. UP/DOWN and A/C work (hold each until the e-ink starts to change).
3. Unplug USB, wait ~5 s to sleep, press DOWN: wakes **and** moves one mood.
4. HOME goes to the menu.
5. RESET opens the menu.
6. With Mood Badger showing, after an install or a `badge_check` run:
   note what the badge shows (the source says Mood Badger; not yet
   seen) and record it in `badgeware-platforms`.
7. If `kiosk/main.py` changed and the badge is in kiosk mode: RESET and
   HOME both open Mood Badger.

## Reporting

Say which layers ran and their results (test counts, the `Start-up:` line,
the file check, the wake reasons, which checklist items the user
confirmed), and name any layer you skipped and why. In a PR's test plan,
tick only what actually ran.
