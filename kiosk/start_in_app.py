# Start-in-app boot file for a Tufty 2350: opens Mood Badger on power-on,
# RESET, waking and USB plug-in, but the app list when the restart came
# from HOME.
#
# Copy this file over main.py at the root of the badge's drive (disk mode),
# or run python3 -m tools.install --start-in-app. Double-tap RESET still
# enters disk mode; copy vendor/tufty2350/firmware/main.py back over it to
# undo this.
#
# HOME calls reset(), which on the Tufty is machine.reset(): a watchdog
# reboot. Nothing else gives WAKE_WATCHDOG (except dismissing an error
# screen, which also lands on the menu), so no state has to be saved to
# tell the two apart. Codes: vendor/tufty2350/modules/c/powman/bindings.c.

import powman

if powman.get_wake_reason() == powman.WAKE_WATCHDOG:
    # The stock Tufty main.py's menu flow (vendor/tufty2350/firmware/main.py).
    badge.poll()  # eat the press that restarted the badge
    app = launch("/system/apps/menu")
    if app is not None:
        # Don't pass the menu's button press into the chosen app.
        while badge.pressed() or badge.held() or badge.released():
            badge.poll()
        launch(app)
else:
    # Mood Badger ignores the waking press itself, on its first frame.
    launch("/system/apps/mood_badger")

reset()
