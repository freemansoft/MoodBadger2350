---
name: badge-deploy
description: Copy the Mood Badger app (badger/mood_badger) onto a real Badger 2350 or Tufty 2350 over USB disk mode, without touching the firmware - runs the project checks first, makes sure the badge's firmware is current, guides the user through double-tapping RESET, copies only the app's own files, verifies the copy and ejects. Also sets what the badge starts up into: kiosk mode (Mood Badger as the only app), start-in-app mode (the normal Tufty setup: Mood Badger at start-up, HOME opens the menu) or the stock menu. Use whenever the user wants to install, update, deploy, push, sync or try Mood Badger (or a changed config.json, mood image or label) on the physical badge, says the badge still shows the old version, or asks about kiosk or start-in-app mode on the device - even if they just say "put it on the badge". For flashing or checking firmware use badge-firmware.
---

# Deploying Mood Badger to a badge

This updates **only** the app: `apps/mood_badger` on the badge's drive,
plus `main.py` when the user asks to change what the badge starts up into. Firmware is
the badge-firmware skill's job.

Why disk mode, not `mpremote cp`: the badge mounts its user drive
read-only at `/system` while MicroPython runs, so the app can only be
written from the computer while the badge is in disk mode (double-tap
RESET). On the drive, `apps/mood_badger` is `/system/apps/mood_badger`
on the badge. The saved mood is in `/state`, on a separate internal
partition that isn't on the drive, so updating the app keeps it.

The user's hands are needed for the button presses. Don't make them
come back and type "done": the tools take `--wait SECONDS` and watch
for the drive or serial port themselves. Start the command with
`--wait 180` **in the background** (Bash `run_in_background`), then end
your turn with the button instructions, so they are the last thing the
user reads. You are notified when the command finishes; read its
output then. If it timed out, ask what the badge's screen shows.

Run the tools from the repository root as modules
(`python3 -m tools.install`); they are standard-library Python.

## Steps

### 1. Check the app before it goes on the badge

A broken import or bad `config.json` shows an error screen on the badge,
which may be a child's only way to say how they feel. Run the project's
checks and **stop if any fail**: report the failure and offer to fix it
instead of copying.

```bash
.venv/bin/pytest -q
for f in badger/mood_badger/*.py; do .venv/bin/python -m mpy_cross -o /dev/null "$f"; done
.venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger
```

If `.venv` is missing, set it up as `CLAUDE.md` says. The pytest run
includes a headless simulator run when `node` is installed. Skip the
checks only if the user explicitly says to.

### 2. Make sure the badge's firmware is current

Mood Badger needs firmware v3.1.1 or later. If the badge is in normal
mode (menu or an app on screen), run:

```bash
python3 -m tools.badge_info
```

It reports the model, whether the firmware looks current, whether Mood
Badger is installed and the "Start-up" mode (menu, kiosk,
start-in-app or custom). Note it so you can tell the user if it changes. It restarts the badge when it
has finished (the menu reappears after a couple of seconds), so the
user doesn't need to press anything. A Tufty in start-in-app mode
comes back on the menu too, because this restart is the one HOME makes;
that is expected, and RESET brings Mood Badger back.

- **Firmware OLDER than the latest release, or no build date:** stop
  and use the badge-firmware skill first, then come back.
- **Model is neither `badger` nor `tufty`:** Mood Badger has no build
  for it. Stop and say so.
- **No badge found:** it may be asleep, already in disk mode (go to
  step 3 if the `BADGER` or `TUFTY` drive is mounted), or on a charge-only cable.
  Start `python3 -m tools.badge_info --wait 180` in the background and
  ask the user to press RESET once.

If the badge is already in disk mode, the firmware can't be read. Say
so, and continue only if the user confirms the firmware is current or
was checked earlier in this session.

### 3 and 4. Disk mode, then copy

Start the install in the background; it waits for the drive:

```bash
python3 -m tools.install --wait 180 --eject
```

Then tell the user: back of the badge facing them, **double-tap RESET**
(just right of BOOT, which is far left). The screen shows "USB Disk
Mode" and a drive named `BADGER` appears (Pimoroni's README calls it
`Badger2350`); the copy then runs by itself. In the same message, tell
them **not to press anything else until you say the drive has
ejected**: the disk mode screen doesn't change while files are copied
(only the case lights flicker), so it looks idle when it isn't. End
your turn there.

Why this matters: a RESET before the eject cuts the badge off while
the Mac still holds written data in its cache. Files can end up
missing, empty or cut short without any error on the Mac's side; the
copy check reads the Mac's cache, so only a clean eject proves the
files reached the badge.

If the badge is already in disk mode, the command finds the drive at
once; no button press is needed.

The script finds the badge's drive, refuses to copy to a model with no
Mood Badger build, builds the new copy in a hidden `.mood_badger.new`
folder at the drive's root (outside `apps/`, so the menu never lists
it), compares every file with the source, then swaps it into
`apps/mood_badger`. An interrupted copy leaves the old app in place. It
leaves out `__pycache__` and `.pyc` files, deletes the `._` files
macOS writes on FAT drives, prints `Start-up: <mode>`, and ejects.

Leave `main.py` alone unless the user asked about the start-up mode,
or this is a Tufty's first install (see "Tufty 2350" below):

- `--start-in-app` (Tufty only; refused on a Badger): `kiosk/start_in_app.py`
  replaces `main.py`. Power-on, RESET and USB plug-in open Mood Badger;
  HOME opens Pimoroni's app list. It tells them apart by the restart
  reason (`WAKE_WATCHDOG` after HOME), so nothing is saved.

- `--kiosk` makes Mood Badger the only app: `kiosk/main.py` replaces
  `main.py`, so power-on, RESET, HOME and waking all start Mood Badger.
  Double-tap RESET still reaches disk mode, so this can't lock anyone
  out.
- `--menu` brings the menu back by restoring that model's stock
  `main.py` from `vendor/<model>2350/firmware/main.py`. That file is from firmware
  v3.1.1; if the badge runs a newer firmware, say that the stock file
  from that release is the safer one.

Use `--dest /Volumes/<name>` if the drive has an unusual name, and
`--model badger` or `--model tufty` if its name doesn't say which badge it is.

If the copy check fails, run the command again. If it keeps failing,
the drive may be full (badge_info's free space line) or the cable flaky.

### 5. Confirm on the badge

Check the copy from the badge's side first, with
`python3 -m tools.badge_check files` (it restarts the badge onto the
menu). The `badge-verify` skill has the hand checklist for each badge.

Only after the script prints "Ejected", tell the user it's safe to
touch the badge. It restarts into the menu by itself, or straight into
Mood Badger in kiosk mode. In start-in-app mode it also restarts into the
app list (the eject's restart is a watchdog reboot, like HOME; seen on a
real Tufty), so tell the user to press RESET once to open Mood Badger.
If the disk mode screen is still up after
10 seconds, they press RESET once. If the eject failed, have them eject
the drive from Finder before pressing anything. Ask them to open Mood Badger and check the change
they made: the mood, label or image they edited, and that UP/DOWN
and A/C still move between moods and sets. On a Badger the e-ink takes
a moment to refresh, so they should hold each button until the screen
starts to change. On a Tufty the first press on a dimmed screen only
brightens it.

Report what was copied (file count), the start-up mode, and anything the
user should look at by hand.

## Tufty 2350

Badger vs Tufty differences: see the `badgeware-platforms` skill.

The Tufty gets the same `badger/mood_badger` folder; the app checks
`badge.model` itself. Its drive is `TUFTY`. The steps are the same, with
these differences:

- **Start-in-app is the normal Tufty setup.** The Tufty's stock
  `main.py` always opens the app list, so without it the child has to
  find Mood Badger in the list after every power-on. On a Tufty's first
  install, offer `--start-in-app` unless the user wants the menu or
  kiosk mode. HOME then opens the app list; RESET or power-on brings
  Mood Badger back.
- `badge_info` and `--menu` use the Tufty's own stock `main.py`
  (`vendor/tufty2350/firmware/main.py`), never the Badger's.
- The screen dims after 10 s; a press on a dim screen only brightens
  it. Powering off is holding RESET until the case lights fade.
