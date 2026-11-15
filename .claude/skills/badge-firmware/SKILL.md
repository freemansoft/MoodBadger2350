---
name: badge-firmware
description: Check and update the Badgeware firmware on a Badger 2350 (or Tufty 2350) plugged in by USB - identify which badge is connected and what firmware it runs, compare it with Pimoroni's latest release, download the right UF2 and flash it in bootloader mode, guiding the user through the BOOT/RESET button presses. Use whenever the user wants to update, upgrade, reflash or recover badge firmware, asks which badge or firmware version is plugged in, has a new or unboxed badge, sees "System Error" or a blank/stuck badge, wonders if a bug is really an old firmware, or mentions a new pimoroni/badger2350 or tufty2350 release - even if they never say "firmware". For copying only the Mood Badger app onto a badge, use badge-deploy instead.
---

# Badge firmware

Mood Badger needs Badgeware firmware **v3.1.1 or later**, the version
pinned in `vendor/badger2350` and `vendor/tufty2350`. A badge ships with whatever Pimoroni
flashed at the factory, and an app bug can really be an old firmware,
so know the badge's model and firmware before trusting what it does.

Most steps need the user's hands on the buttons on the back of the
badge. As CLAUDE.md says, start each tool with `--wait 180` in the
background and end your turn with exactly what to press and what they
should see. If it timed out, ask what the badge's screen shows.

The tools are standard-library Python plus `mpremote` (in
`requirements-dev.txt`), run from the repository root:
`tools/badge_info.py`, `tools/flash_firmware.py` (helpers in
`tools/badgeware_release.py`). Run them as modules
(`python3 -m tools.badge_info`), because they import each other from
the `tools` package. They need `mpremote` on the PATH
(`pip install mpremote`).

## The badge's three USB modes

| Mode | How the user gets there | What the computer sees |
| --- | --- | --- |
| Normal | Press RESET once, or just plug it in | A serial port, `Pimoroni Badger 2350 MicroPython` or `Pimoroni Tufty 2350 MicroPython` in `mpremote devs` |
| Bootloader | Hold BOOT, tap RESET, let go of BOOT | A drive named `RP2350` holding `INFO_UF2.TXT` |
| Disk mode | Double-tap RESET | A drive named `BADGER` (Pimoroni's README says `Badger2350`) or `TUFTY` |

Buttons, with the **back of the badge facing the user**: BOOT is
towards the far left, RESET is just to the right of BOOT. On battery
the badge sleeps and drops off USB; plugging in USB keeps it awake.

## Steps

### 1. Identify the badge and check its firmware

If the user says the badge is plugged in and showing the menu or an
app, just run:

```bash
python3 -m tools.badge_info
```

Otherwise start `python3 -m tools.badge_info --wait 180` in the
background and ask them to plug it in with a data cable and press
RESET once.

It picks the badge out of `mpremote devs` (other boards, such as a
Particle board or Bluetooth ports, are ignored; with two badges it asks
for `--port`) and prints the model, MicroPython build and build date,
whether Mood Badger is installed, the start-up mode (menu, kiosk,
start-in-app or custom), the saved
mood, free space, and the latest release with a verdict.

- **The verdict compares dates, not version numbers.** The firmware
  records when it was built, not which release it is. "Looks current"
  means built within a few days of the latest release's publish date.
  Say that when you report it; don't claim an exact version.
- **The model comes from Badgeware itself**, which is what decides the
  firmware image. Don't infer it from the drive name or USB description.
  Over mpremote the menu's `badge` object is usually gone, so the
  source normally reads `badgeware.badge.MODEL`: the constant
  `badge.model` is set from, so it's just as good. Only
  `os.uname().machine` is a warning sign (below).
- **It interrupts whatever was running, then restarts the badge**
  with `machine.reset()` a couple of seconds later, without a button
  press. A Badger reopens the app it was showing; a Tufty (stock or
  start-in-app) opens the menu, and RESET brings Mood Badger back on a
  start-in-app Tufty. Don't run it while the user is in the middle of
  using Mood Badger.
- `model_source` of `os.uname().machine` means Badgeware didn't load:
  the firmware is damaged or not Badgeware. Reflash, and suggest
  `--with-filesystem` (step 2).

If the verdict is "looks current" and the user didn't ask for a reflash,
stop here and report.

If no badge is found: it may be asleep (press RESET), in disk mode
(eject the drive), on a charge-only cable, or not Badgeware at all. A
badge that only shows "System Error" may still be reachable in normal
mode; if not, go straight to bootloader mode, which is in ROM and always
works, and ask the user which model it is.

### 2. Choose the image (the user decides)

Every release has two images, and `flash_firmware.py` refuses to guess:

- `--firmware-only` replaces only the firmware. Apps, `main.py` and the
  saved mood stay. **The right choice for a badge already in use.**
- `--with-filesystem` also resets the badge's drive to Pimoroni's
  defaults: Mood Badger and any added apps are removed, and `main.py`
  is replaced, so **kiosk and start-in-app mode are undone**. The saved mood lives in
  `/state` on a separate internal partition and probably survives, but
  don't promise it. Good for a new badge or a damaged filesystem,
  because the default apps then match the firmware.

Explain the trade-off in a sentence or two and let the user choose.
Don't pass `--yes` (which skips the typed confirmation) unless they
have just told you to wipe it.

Before flashing a release newer than the pinned `v3.1.1`, skim its
notes for anything Mood Badger depends on: `State`, `image.load`,
`screen`/text drawing, buttons, sleep and wake (`rtc`, `powman`),
`run()`:

```bash
gh release view -R pimoroni/badger2350     # or pimoroni/tufty2350
```

Mention anything that looks risky before flashing.

### 3. Flash

Start the flash in the background with the model from step 1; it
downloads the image first, then waits for the drive:

```bash
python3 -m tools.flash_firmware --model badger --firmware-only --wait 180
```

Then tell the user, step by step: back of the badge facing them,
**hold BOOT** (far left), **tap RESET**, **let go of BOOT**. The screen
does not change, but a drive named `RP2350` appears and the flash runs
by itself. Tell them in the same message **not to press anything else
until you say it's done**: nothing on screen shows the flash is in
progress, and a RESET part-way leaves a half-written firmware (the ROM
bootloader can always recover it, but it means flashing again). End
your turn there.

`--with-filesystem` normally asks for the model name to be typed, which
a background command can't receive. Only after the user has said in
the chat that wiping the badge is fine, pass `--yes` with it.

The script downloads the UF2 from `pimoroni/<model>2350` releases
(cached in the system temp folder), checks it is a complete UF2 file,
and copies it to the `RP2350` drive. The badge restarts by itself after
a few seconds. What it opens then hasn't been checked on either badge
(it depends on the restart reason; see `badgeware-platforms`); on a
start-in-app Tufty, RESET brings Mood Badger back if it shows the menu. `--tag vX.Y.Z` picks a particular
release; `--download-only` fetches without flashing. Pre-releases (for
example `v4.0.0-ide.1`) are skipped by "latest"; use one only if the
user asks for it by tag.

The script decides whether the flash worked by waiting up to 30 s for
the badge to come back in normal mode, so read its last lines:

- **"Flash complete"**: tell the user it's done and safe to touch.
- **"still in bootloader mode"**: the badge didn't take the image (or
  someone pressed BOOT and RESET again). The `RP2350` drive is still
  mounted, so run the same command again with no button presses.
- **"didn't come back on USB"**: ask what the screen shows. The menu
  means it worked. Otherwise ask for one RESET press and check with
  `badge_info --wait 30`.

Flashing the other model's firmware doesn't brick a badge (the
bootloader is in ROM), but nothing works until the right image is on
it. That's why the model must come from step 1, not from a guess.

### 4. Confirm

The badge takes a few seconds to come back on USB after flashing, so
run `python3 -m tools.badge_info --wait 60` (ask the user to press RESET
once if it doesn't appear). Expect a model source of
`badgeware.badge.MODEL` (or `badge.model`) and a "looks current"
verdict.

### 5. Afterwards

- **After `--with-filesystem`**, Mood Badger is gone and `main.py` is
  the stock one, so kiosk and start-in-app mode are off. Offer to
  reinstall it with the badge-deploy skill (with `--kiosk` or
  `--start-in-app` if the step 1 "Start-up" line said so).
- **If the release is newer than the pinned `v3.1.1`**, say so. Moving
  the project to it is a separate change, not part of flashing:
  bumping the `vendor/badger2350` or `vendor/tufty2350` submodule,
  updating every "3.1.1" mention (find them with
  `grep -rn "3\.1\.1" --exclude-dir=vendor --exclude-dir=.venv --exclude-dir=docs .`),
  re-checking the `badgeware-platforms` skill's table, then the test
  suite and the simulator. Offer it; don't do it unasked.
- Report: model, firmware before and after (build dates), which image
  was flashed, and anything the user should check by hand on the badge.

## Tufty 2350

Badger vs Tufty differences: see the `badgeware-platforms` skill.

The tools already handle the Tufty: `badge_info` reads `badge.model`
as `"tufty"`, and `flash_firmware --model tufty` fetches from
`pimoroni/tufty2350`. The button procedure is the same. Things to
note when working with one:

- After flashing a Tufty, offer the badge-deploy skill with
  `--start-in-app` (the normal Tufty setup) if Mood Badger isn't on it,
  or if `--with-filesystem` just reset its `main.py`.
- Tufty releases include pre-releases such as the Badgeware IDE preview
  (`v4.0.0-ide.1`). "Latest" skips them; flash one only on request.
