---
name: badgeware-platforms
description: How the Badger 2350 (e-ink) and Tufty 2350 (colour LCD) differ under the same Badgeware firmware, with each difference backed by a file in vendor/badger2350 or vendor/tufty2350, and the rules app code must follow to run on both. Load it whenever you write, change, review or plan Mood Badger app code (badger/mood_badger) or any Badgeware app that runs on a Badger 2350 or Tufty 2350, port something between them, touch the boot files in kiosk/, or debug something that works on one badge but not the other - even if the user only says "make it work on the Tufty", "why is the Tufty screen black" or mentions a Blinky.
---

# Badger 2350 vs Tufty 2350

Both badges run Pimoroni's Badgeware firmware, built from near-identical
source trees, and app code looks portable. It isn't quite: the run loop,
the screen, the start-up flow and several built-in names differ. Each
row below was read from the firmware source pinned at **v3.1.1** in the
two submodules. Read the cited file before relying on a row, and
**re-check every row against the new tag before bumping either
submodule**.

## The differences

| | Badger 2350 | Tufty 2350 | Source |
| --- | --- | --- | --- |
| Screen | e-ink, keeps its image unpowered, slow refresh | colour LCD with a backlight, `display.backlight(0..1)` | `vendor/tufty2350/modules/common/badgeware/__init__.py` |
| Resolution | 264x176 | 160x120 (LORES, default) or 320x240 after `badge.mode(HIRES)` | `vendor/tufty2350/modules/common/badgeware/badge.py` (`mode()`) |
| Default pen and clear | black on white | white on black | `vendor/tufty2350/modules/common/badgeware/badge.py` (`Badge.__init__`) |
| `color.white`, `color.black` | pure white (255, 255, 255), pure black | an off-white (0xde, 0xee, 0xd6) and a dark navy (0x14, 0x1e, 0x28), from a Dawnbringer palette; use `color.rgb(255, 255, 255)` and `color.rgb(0, 0, 0)` for true black and white | pimoroni/picovector `micropython/color.cpp` (`#ifdef TUFTY`), not vendored |
| `run(update)` loop | calls `update()` only; the app calls `badge.update()` to refresh | `badge.clear()` before and `display.update()` after every `update()`, every frame (~90 fps with `VSYNC`) | `vendor/badger2350/modules/common/badgeware/__init__.py`, `vendor/tufty2350/modules/common/badgeware/__init__.py` (`_run.__call__`) |
| `badge.first_update` | set False after the first `badge.update()` | never set False | `vendor/badger2350/modules/common/badgeware/badge.py` |
| `NON_BLOCKING` | defined | not defined (NameError) | `vendor/badger2350/modules/common/badgeware/badge.py` |
| `wait_for_button_or_alarm` | defined; deep-sleeps after its timeout on battery | not defined | `vendor/badger2350/modules/common/badgeware/__init__.py` |
| Stock `main.py` | reopens the last app (`state["running"]`) unless it is gone or the wake reason is `WAKE_RESET` | always opens the menu; eats the waking press first with `badge.poll()` | `vendor/badger2350/firmware/main.py`, `vendor/tufty2350/firmware/main.py` |
| Menu | remembers the selected app | starts at the first app (`active = 0`), apps alphabetical, 6 per page | `vendor/tufty2350/firmware/apps/menu/__init__.py` |
| HOME | `do_exit()` (the app's `on_exit`), then `reset()` | same, but HOME is also BOOT, so `reset()` waits for HOME to be released, then `machine.reset()` (a watchdog reboot) | `vendor/tufty2350/modules/common/badgeware/__init__.py` (`launch`, `reset`) |
| Restart reason | `powman.get_wake_reason()` | same codes: HOME gives `WAKE_WATCHDOG` (0xf2), RESET `WAKE_RESET` (0xf1), a front button `WAKE_BUTTON_*`, USB plug-in `WAKE_VBUS_DETECT` | `vendor/tufty2350/modules/c/powman/bindings.c`, `vendor/badger2350/modules/c/powman/bindings.c` |
| Double-tap RESET | disk mode | disk mode, handled before `main.py` runs | `vendor/tufty2350/modules/common/main.py` |
| Hold RESET | - | case lights fade, then power off; a front button turns it on | `vendor/tufty2350/modules/c/powman/powman.c` (`handle_long_press`) |
| Waking button press | reaches the first `badge.poll()` | same; `run()` polls before the first `update()`, so the app sees it as pressed | `vendor/tufty2350/modules/c/input/input.cpp` |
| Disk-mode drive | `BADGER` | `TUFTY` | `vendor/badger2350/board/mpconfigboard.cmake`, `vendor/tufty2350/board/mpconfigboard.cmake` (`PIMORONI_FATFS_LABEL`) |
| `State`, filesystem helpers | same | same | `vendor/tufty2350/modules/common/badgeware/state.py`, `vendor/tufty2350/modules/common/badgeware/filesystem.py` |
| Fonts | same set | same | `vendor/tufty2350/romfs/fonts` |
| Power source | `badge.usb_connected()` | same | `vendor/tufty2350/modules/common/badgeware/badge.py` |
| Scaled blit | - | `screen.blit(img, rect(x, y, w, h))`, as `fatal_error` does | `vendor/tufty2350/modules/common/badgeware/__init__.py` |

## Rules for app code

- **Never assume the screen keeps its image.** True on the e-ink only;
  on the Tufty the run loop clears the screen before every `update()`.
- **On the Tufty, draw everything every frame.** Anything not drawn in
  this `update()` is gone after the next `display.update()`.
- **Cache decoded images** (including a failed load). At ~90 fps,
  `image.load` per frame wastes the CPU; retrying a broken file is worse.
- **Save state before refreshing or sleeping.** A deep sleep or a pulled
  battery loses anything not saved.
- **Branch on `badge.model`** (`"badger"`, `"tufty"`), never on drive
  names or screen size guesses.
- **Guard Badger-only names** (`NON_BLOCKING`, `wait_for_button_or_alarm`,
  `badge.first_update`): only use them on the Badger code path.
- **Define `on_exit()` at module level before calling `run()`.** The
  app's import blocks inside `run()`, and HOME looks `on_exit` up on the
  module, so anything defined after `run()` doesn't exist yet.
- **HIRES on the Tufty** for anything taller than 120 px.
- **Don't use `color.white`/`color.black` for a monochrome look on the
  Tufty.** They are tinted there, so a pure black-and-white picture sits in
  a visible box. Mood Badger uses `color.rgb()` on the Tufty.

## How Mood Badger handles them

- `badger/mood_badger/__init__.py`: loads config and state once, then
  branches on `badge.model`. The Badger path is the e-ink code (draws
  only on change, sleeps after 5 s on battery). The Tufty path runs in
  `HIRES | VSYNC`, draws every frame, caches the picture, ignores the
  waking press and any press on a dimmed screen, and dims the backlight.
  `on_exit()` restores full brightness on the Tufty.
- `badger/mood_badger/moods.py`: per-model layout (`LAYOUTS`) and the
  backlight rule, free of Badgeware names so they test on a desktop.
- `kiosk/start_in_app.py`: the Tufty boot file that opens Mood Badger
  unless the restart came from HOME (`WAKE_WATCHDOG`), which gets the
  stock menu flow.
- `tools/install.py`: `STOCK_MAINS` holds each model's stock `main.py`,
  `boot_mode()` names what a badge's `main.py` does, and
  `--start-in-app` is refused on a Badger (its stock `main.py` already
  returns to the last app).

Confirmed on a Tufty at v3.1.1 (2026-11-15): a single RESET reports
`WAKE_RESET` (241), `machine.reset()` (HOME, `mpremote ... reset`,
`tools.badge_info`) `WAKE_WATCHDOG` (242), and a double-tap
`WAKE_DOUBLETAP` (5). The restart after ejecting the disk-mode drive
is also `WAKE_WATCHDOG`. So anything that calls `machine.reset()`, and
every install, lands a start-in-app Tufty on the menu, not only HOME;
RESET brings Mood Badger back.

Checked by hand on that Tufty: RESET and power-on (hold RESET, then a
front button) open Mood Badger; RESET after HOME opens Mood Badger, so
the watchdog flag doesn't stick; the waking press doesn't change the
mood; dimming to 0.5 on USB and 0.15 on battery, both still readable;
the `TUFTY` layout's arrows sit above A and C.
