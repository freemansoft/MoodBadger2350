# Mood Badger on the Tufty 2350: design

Date: 2026-11-14. Status: for the user's approval.

## Intent

Mood Badger is a visual communication aid for neurodivergent children:
they press buttons to show how they feel. Today it runs only on the
e-ink Badger 2350. This work makes the same app run on the Pimoroni
Tufty 2350, which has a colour LCD, so a child can use either badge.
For now the Tufty shows the same black-and-white mood pictures as the
Badger.

The Badger and Tufty run the same Badgeware firmware family, but they
behave differently in ways that are easy to get wrong, and that so far
could only be found by reading firmware source. A new project skill
writes those differences down once, so later work (and later Claude
sessions) reasons about both badges correctly.

## Goals

1. One app folder, `badger/mood_badger`, runs on both badges. It checks
   `badge.model` at start-up and picks that badge's layout and display
   behaviour. Same `config.json`, same pictures, and the same saved-state
   key and format (`State` "mood_badger"). Each badge keeps its own
   saved mood on its own flash; nothing copies it between badges.
2. On the Tufty it looks like a bigger Badger: black on white, picture in
   the middle, label below it, set arrows above A and C, a pip column on
   the right. The pictures are scaled up (about 1.5x) to fill the larger
   screen.
3. Tufty backlight behaviour (the user's design):
   - Any button press sets the backlight to full brightness.
   - After 10 s with no press, it dims: to about 15% on battery, about
     50% on USB power. It stays dimmed, still showing the mood, until a
     press or until the user powers the badge off.
   - A press while dimmed only brightens the screen. It does not change
     the mood or the set. The next press does.
   - Moving from USB to battery while dimmed takes effect without a
     press (the dim level follows the current power source).
   - The press that powers the Tufty on (in kiosk mode it reaches the
     app's first `update()`; see `modules/c/input/input.cpp`) only wakes
     it: the saved mood is shown and the press is ignored. The Badger
     keeps its current behaviour, where the waking press moves the mood,
     so this is handled in the Tufty code path, not in `kiosk/main.py`.
   - Leaving Mood Badger (HOME) restores full brightness, so the menu is
     never left at the dim level.
4. Mood Badger never puts the Tufty into deep sleep. (On the Tufty, a
   wake from deep sleep always opens Pimoroni's app list, not the last
   app, unless the badge is in kiosk mode.) Users power the Tufty off by
   holding RESET until the case lights fade; any front button turns it
   back on. The app's README says so.
5. The Badger's behaviour does not change at all: same layout, same
   e-ink refresh logic, same sleep after 5 s on battery, same handling
   of the button press that woke it. Its existing tests keep passing
   unchanged except where they need the model set.
6. A project skill, `.claude/skills/badgeware-platforms/SKILL.md`, holds
   the Badger/Tufty difference table (below), each row backed by a file
   reference in the firmware source, plus the rules for app code that
   follow from it. Its description makes it load whenever someone writes
   or changes app code that must run on either badge, or plans Tufty
   (or Blinky) work. `badge-deploy`, `badge-firmware` and `CLAUDE.md`
   point to it.
7. **Start-in-app mode, the normal Tufty setup.** A new boot file
   (for example `kiosk/start_in_app.py`) replaces the Tufty's
   `main.py`. It opens Mood Badger on power-on, RESET, a button press
   after a hold-RESET power-off, and USB plug-in, but opens Pimoroni's
   app list when the restart came from HOME. It tells them apart with
   `powman.get_wake_reason()` only, so nothing is saved across reboots
   (the user's reason for choosing this):
   - `WAKE_WATCHDOG` (HOME calls `reset()`, which calls
     `machine.reset()`, a watchdog reboot): run the stock menu flow,
     as the Tufty's `firmware/main.py` does.
   - anything else: `launch("/system/apps/mood_badger")`.
   - `WAKE_DOUBLETAP` never reaches `main.py` (`modules/common/main.py`
     enters disk mode first).
   From the menu, picking any app works as normal. Known side effects,
   accepted: dismissing an error screen also restarts with
   `WAKE_WATCHDOG`, so it lands on the menu; HOME in the menu stays in
   the menu. `tools.install` gets a flag for it (for example
   `--start-in-app`) beside `--kiosk` and `--menu`, and `badge_info`
   reports which boot file is installed (stock, kiosk or start-in-app).
   The wake-reason behaviour is read from source; confirming it on the
   user's Tufty is part of the hardware check.
8. The deploy and firmware tooling handles a Tufty end to end:
   `tools.install` copies the same app to a `TUFTY` drive, `--menu`
   restores the Tufty's own stock `main.py` (not the Badger's), and
   kiosk mode works on both.
9. The Tufty firmware source is vendored like the Badger's:
   `vendor/tufty2350` submodule pinned to `v3.1.1`, so code and the
   skill can cite it.
10. The browser simulator can run the app as a Tufty as well as a
   Badger, using the `badgeware-tufty2350-asyncify` build from the same
   pimoroni/badgeware-wasm run (35841227054) the Badger build came from,
   so the Tufty layout can be checked without hardware.

## Non-goals

- Colour pictures, or any Tufty-only look. Same monochrome assets now;
  colour is a later project.
- Blinky 2350 support.
- Changing Badger behaviour or layout.
- A separate Tufty copy of the app or its assets.
- Deep sleep or any auto power-off on the Tufty.
- Using the Tufty's light sensor for brightness.

## Anti-goals (would make this a failure even if it "works")

- A press on a dimmed screen changes the mood. The child must see the
  current mood before they can change it.
- The Tufty shows a blank or black screen while Mood Badger is running.
  The mood must always be visible, dimmed or not.
- A badge's saved mood is lost or reset by reinstalling the app,
  reflashing firmware-only, or power-cycling. (Each badge has its own
  saved mood.)
- Any regression on the Badger, which is in real use.

## Constraints and facts (from firmware source, both pinned at v3.1.1)

Paths are relative to `vendor/badger2350` and `vendor/tufty2350`.

| | Badger 2350 | Tufty 2350 | Source |
| --- | --- | --- | --- |
| Screen | e-ink, keeps its image unpowered, slow refresh | colour LCD with backlight (`display.backlight(0..1)`) | `modules/common/badgeware/__init__.py` |
| Resolution | 264x176 | 160x120 (LORES, the default) or 320x240 (`badge.mode(HIRES)`) | Tufty `__init__.py` end, `badge.py` `mode()` |
| Default pen/clear | black on white | white on black | `badge.py` `Badge.__init__` |
| `run()` loop | calls `update()` only; app calls `badge.update()` to refresh | calls `badge.clear()` before and `display.update()` after every `update()`, every frame (~90 fps with VSYNC) | `__init__.py` `_run.__call__` |
| `badge.first_update` | set False after the first `badge.update()` | never set False | `badge.py` `update()` |
| `NON_BLOCKING` | defined | not defined (NameError) | `badge.py` builtins |
| `wait_for_button_or_alarm` | defined; sleeps after timeout on battery | not defined | Badger `__init__.py` |
| Wake from deep sleep | returns to the last app (`state["running"]`) | `firmware/main.py` always opens the menu | `firmware/main.py` |
| Restart reason | `powman.get_wake_reason()`; stock `main.py` opens the menu on `WAKE_RESET` | same function; HOME gives `WAKE_WATCHDOG`, RESET `WAKE_RESET`, button power-on `WAKE_BUTTON_*` | Tufty `modules/c/powman/bindings.c` |
| Hold RESET | — | case lights fade, then power off; buttons wake | Tufty `modules/c/powman/powman.c` `handle_long_press` |
| Disk-mode drive | `BADGER` | `TUFTY` | `board/mpconfigboard.cmake` `PIMORONI_FATFS_LABEL` |
| `State`, filesystem helpers | same | same | `state.py`, `filesystem.py` identical |
| Fonts | same set (`ignore`, `ziplock`, `smart`, `winds` used) | same | `romfs/fonts` |
| Power source | `badge.usb_connected()` | same | `badge.py` |
| Scaled blit | — | `screen.blit(img, rect(x, y, w, h))` (used by `fatal_error`) | Tufty `__init__.py` |

Other constraints:

- Keep `moods.py` free of Badgeware names (CLAUDE.md); per-model layout
  numbers can live there as plain data, as the Badger's already do.
- Badger rule stays: nothing calls `badge.poll()` or `badge.update()`
  before `run(update)`.
- Mood pictures are 122x136, 2-bit palette PNGs. They do not fit the
  Tufty's LORES height (120), so the Tufty runs in HIRES.
- The app is MicroPython; run the existing mpy-cross and ruff checks.

## Decided by the user

- Same monochrome pictures on both badges, for now.
- Dim after 10 s: about 15% on battery, about 50% on USB. Never dark.
- A press on a dimmed screen only brightens it.
- The app never deep-sleeps the Tufty; powering off is left to users.
- Tufty looks like a bigger Badger.
- Each badge keeps its own saved mood (not synced between badges).
- One `badgeware-platforms` skill holding the difference table.
- The normal Tufty setup is start-in-app mode (goal 7), using the
  restart reason, chosen over kiosk mode (menu needs a computer) and a
  press-HOME-twice start-up window (a delay on every start, timing to
  learn) because nothing has to be saved across reboots.

## Claude's calls (the user can overrule)

- One shared app folder with a model switch, not two copies.
- Scale factor about 1.5x (picture about 183x204); exact layout numbers
  are the builder's, keeping the Badger's arrangement and leaving room
  for the label and arrows below the picture.
- The power-on press on a Tufty only wakes it, by the same principle as
  "a press on a dimmed screen only brightens it".
- Leaving the app restores full brightness.
- Full brightness = backlight 1.0; dimmed = 0.15 battery, 0.5 USB.
- Add `vendor/tufty2350` and Tufty support in the simulator.
- Start-in-app mode targets the Tufty. The Badger keeps its stock
  `main.py` (which already returns to the last app after a wake) or
  kiosk mode; the installer may allow start-in-app on a Badger only if
  the Badger's `powman` reports the same wake reasons, which the builder
  checks in `vendor/badger2350`.
- The start-in-app file eats the waking press before opening the menu,
  as the stock `firmware/main.py` does, and does not eat it before
  launching Mood Badger (the app ignores it itself, goal 3).
- Kiosk mode (`--kiosk`) stays available on both badges.
- `kiosk/main.py` stays one file for both badges (it already only
  calls `launch("/system/apps/mood_badger")`); its comment drops
  "on a Badger 2350".

## Left to the builder

- How the app splits Badger and Tufty code (separate draw/update
  functions, a small per-model module, etc.), as long as `moods.py`
  stays Badgeware-free and Badger behaviour is unchanged.
- Whether the Tufty redraws every frame or renders once into an
  off-screen image and blits it each frame (the run loop clears the
  screen before every `update()` either way).
- How `tests/fake_badgeware.py` models the Tufty's run loop, backlight
  and power source, and the tests for the backlight rules (full on
  press, dim after 10 s, level by power source, press-while-dim only
  brightens).
- How `install.py` picks the stock `main.py` per model, and the drive
  name and model wiring for `TUFTY`.
- Simulator page changes to choose Badger or Tufty.
- README and app README updates (Tufty usage, power off by holding
  RESET, the simulator choice).
- Real-hardware check on the user's Tufty at the end, through the
  `badge-firmware` and `badge-deploy` skills (firmware check first,
  then deploy with start-in-app mode, then the user checks by hand: the
  backlight rules, HOME opens the menu, RESET and power-on open Mood
  Badger, and the saved mood is kept).
