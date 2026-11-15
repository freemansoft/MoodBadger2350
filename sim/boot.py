# Simulator boot (both badges): load the real badgeware firmware package, then launch
# Mood Badger directly (skipping the menu). The host page runs this after it
# has written the staged files into the MicroPython filesystem.

import board
import builtins
import machine
import os
import sys
import time

# The simulator's board module lacks the RTC alarm pin that rtc.alarm_status()
# reads. The hosts report it high, the firmware's "no alarm" state.
if not hasattr(board, "RTC_ALARM"):
    board.RTC_ALARM = machine.Pin("RTC_ALARM")

os.chdir("/")
sys.path.insert(0, "/lib")      # sim stubs: powman, pcf85063a
sys.path.insert(0, "/frozen")   # firmware badgeware package (see stage.py)

import badgeware  # noqa: E402, F401


# The Badger firmware's version busy-waits on button polls. In a single-threaded
# browser that starves the page of key events, so yield on every pass. The
# Tufty firmware has no such function (its run() yields after every frame),
# so don't add one there: the app must not depend on it.
def wait_for_button_or_alarm(timeout=30_000):
    t_start = time.ticks_ms()
    while True:
        badge.poll()
        if badge.pressed():
            break
        if rtc.alarm_status():
            break
        if timeout is not None and time.ticks_diff(time.ticks_ms(), t_start) > timeout and not badge.usb_connected():
            badge.sleep()
        time.sleep_ms(10)


if hasattr(builtins, "wait_for_button_or_alarm"):
    builtins.wait_for_button_or_alarm = wait_for_button_or_alarm

launch("/system/apps/mood_badger")
