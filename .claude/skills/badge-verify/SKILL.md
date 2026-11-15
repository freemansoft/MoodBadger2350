---
name: badge-verify
description: How to test and verify a Mood Badger change on both badges (Badger 2350 e-ink and Tufty 2350 LCD) - which test layers a change needs, the exact commands (pytest with the fake Badgeware, mpy-cross and ruff, the headless and browser badgeware-wasm simulator for each badge, rendering simulator frames to images), and the real-hardware checks (badge_info, install, checking the copy from the badge's side, reading wake reasons with a watcher) with a hand checklist for each badge. Use it whenever you change badger/mood_badger, kiosk/, tools/ or sim/, bump firmware, finish a feature, prepare or review a PR, or the user asks to test, verify, smoke-test, check on the badge, "make sure it still works on the Badger", or try something in the simulator - even if they only say "is it done?".
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

| Change | Layers |
| --- | --- |
| `moods.py` logic, config parsing | 1, 2 |
| `__init__.py` (drawing, buttons, backlight, sleep) | 1-4, then 5 on both badges |
| Layout numbers, pictures, labels, `config.json` | 1-4 (look at both pages), then 5 |
| `kiosk/*.py` boot files | 1, then 5 with a wake-reason check |
| `tools/*.py` | 1, then the tool once against a real badge |
| `sim/` | 1, 3, 4 |
| Firmware bump (`vendor/*`) | all, on both badges, after re-checking the `badgeware-platforms` table |

## 1. Unit tests (seconds)

```bash
.venv/bin/pytest -q
```

This includes layer 3 when `node` is installed. The app tests run the
real `badger/mood_badger/__init__.py` against `tests/fake_badgeware.py`:

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
.venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger
```

CPython accepts things MicroPython doesn't; mpy-cross catches them. The
ruff config lists Badgeware's builtins, so an undefined name is an error.

## 3. Headless simulator (seconds per run)

```bash
python3 sim/stage.py
node sim/run_headless.mjs --model tufty --press DOWN --frames /tmp/out.json
```

This runs the real firmware Python and the unmodified app in Pimoroni's
badgeware-wasm builds (`sim/wasm/<model>/`). The JSON has `status`, `width`,
`height`, and `before`/`after` frames as grey bytes. The tests in
`tests/test_sim.py` check pixels in them. To look at a frame without a
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
installs. For every step that needs a button press, start the command
with a wait **in the background**, end your turn with exactly what to
press, and tell the user not to touch the badge until you report
"Ejected" or the result. Never assume a press happened: read the result.

- **Two badges plugged in:** the tools ask for `--port`; `mpremote devs`
  names each one (`Badger 2350`, `Tufty 2350`). A badge on battery sleeps
  and drops off USB: ask the user to plug it in and press RESET.
- **Every mpremote read ends with `machine.reset()`**, the restart HOME
  makes. A Tufty in start-in-app mode then shows the app list, which is
  expected; RESET brings Mood Badger back. Don't read the badge while the
  user is checking what the screen shows: ask first, then read.

Steps:

1. `python3 -m tools.badge_info`: model, firmware current, start-up mode.
2. Install: `python3 -m tools.install --wait 180 --eject` (add
   `--start-in-app` on a Tufty), then double-tap RESET. Expect `Start-up:`
   as intended and "Ejected".
3. Check the copy from the badge's side (macOS can hold writes until the
   eject, so the mounted drive can look right when the badge isn't):
   `python3 -m tools.badge_check files`.
4. Boot files or firmware changed: confirm the restart reasons. Run
   `python3 -m tools.badge_check wake-reason --after-restart 180` in the
   background and ask for a single RESET tap: expect `WAKE_RESET` (241).
   `machine.reset()`, HOME and the restart after an eject give
   `WAKE_WATCHDOG` (242). A double-tap gives `WAKE_DOUBLETAP` (5) and
   disk mode. If the user double-tapped, say so; it isn't a fault.
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
7. HOME opens the app list; then RESET opens Mood Badger.
8. Mood Badger opens from the app list.
9. Hold RESET until the case lights fade (off), then a front button:
   Mood Badger with the same mood; that press doesn't change it.

### Badger 2350 checklist

1. Open Mood Badger: same layout as before.
2. UP/DOWN and A/C work (hold each until the e-ink starts to change).
3. Unplug USB, wait ~5 s to sleep, press DOWN: wakes **and** moves one mood.
4. HOME goes to the menu.

## Reporting

Say which layers ran and their results (test counts, the `Start-up:` line,
the file check, the wake reasons, which checklist items the user
confirmed), and name any layer you skipped and why. In a PR's test plan,
tick only what actually ran.
