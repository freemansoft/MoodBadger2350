# Kiosk boot file: makes Mood Badger the only app on a Badger or Tufty 2350.
#
# Copy this file over main.py at the root of the badge's drive (disk mode).
# Power-on, RESET, HOME and waking from sleep all start Mood Badger; the menu
# is never shown. Double-tap RESET still enters disk mode, so to undo this,
# copy that badge's stock main.py back over it (vendor/badger2350 or
# vendor/tufty2350, firmware/main.py), or run python3 -m tools.install --menu.

launch("/system/apps/mood_badger")
reset()
