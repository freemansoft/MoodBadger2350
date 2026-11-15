"""Identify the Badgeware badge on USB and check its firmware.

The badge must be in normal mode (menu or an app on screen), not disk
mode, and awake. mpremote interrupts whatever is running to read it,
so afterwards this restarts the badge (a hard reset, like pressing
RESET): it goes back to the menu, or to Mood Badger in kiosk or
start-in-app mode.
--no-restart leaves it stopped, its screen frozen, until RESET.

    python3 -m tools.badge_info              # finds the badge
    python3 -m tools.badge_info --port /dev/cu.usbmodem1101
    python3 -m tools.badge_info --json       # machine-readable

Reports the model (from badge.model), the MicroPython build and build
date, whether Mood Badger is installed, what main.py starts, the
saved mood, and the latest Badgeware release for that model with a
verdict on whether the firmware is current. The firmware doesn't record
its Pimoroni release number, so the verdict compares dates.

Needs mpremote (pip install mpremote). Standard library otherwise.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time

from tools import badgeware_release as rel
from tools.install import APP, boot_mode

# The "Start-up" row, for each install.boot_mode() result.
START_UP_TEXT = {
    "kiosk": "Mood Badger only (kiosk)",
    "start-in-app": "Mood Badger, HOME opens the menu (start-in-app)",
    "menu": "Pimoroni menu",
    "custom": "custom main.py",
    None: "unknown",
}

# Runs on the badge. badge.model is set from badgeware.badge.MODEL, so
# read that (or the menu's own badge object, if it's still around). Only
# if Badgeware failed to load, fall back to the os.uname() slice it uses.
# The user filesystem is mounted read-only at /system; /state is on the
# separate LittleFS root.
DEVICE_SNIPPET = r"""
import builtins, json, os, sys
u = os.uname()
info = {"machine": u.machine, "release": u.release, "version": u.version}
try:
    import badgeware.badge
except Exception:
    pass
b = getattr(builtins, "badge", None)
mod = None
for key in sys.modules:
    if key == "badgeware.badge" or key.endswith("badgeware/badge"):
        mod = sys.modules[key]
if b is not None and hasattr(b, "model"):
    info["model"], info["model_source"] = b.model, "badge.model"
elif mod is not None and hasattr(mod, "MODEL"):
    info["model"], info["model_source"] = mod.MODEL, "badgeware.badge.MODEL"
else:
    info["model"], info["model_source"] = u.machine[9:-17].lower(), "os.uname().machine"
try:
    info["apps"] = sorted(os.listdir("/system/apps"))
except OSError:
    info["apps"] = None
try:
    info["main_py"] = open("/system/main.py").read()
except OSError:
    info["main_py"] = None
try:
    info["state"] = open("/state/APP.json").read()
except OSError:
    info["state"] = None
try:
    s = os.statvfs("/system")
    info["free_kb"] = s[0] * s[3] // 1024
except OSError:
    info["free_kb"] = None
print("BADGE_INFO " + json.dumps(info))
""".replace("APP", APP)


def run(cmd, timeout=30):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def list_badges():
    return rel.badge_ports(run(["mpremote", "devs"]).stdout)


def choose_port(port, wait=0):
    """The badge's serial port: ``port`` if given, else the only badge
    that `mpremote devs` lists, so mpremote can't pick another board.
    With ``wait``, keep looking that many seconds (after a RESET or a
    flash the badge takes a few seconds to come back on USB)."""
    if port:
        return port
    badges = list_badges()
    if not badges and wait:
        print("Waiting up to {} s for the badge on USB (normal mode) ...".format(wait),
              flush=True)
        badges = rel.wait_for(list_badges, wait, interval=2)
        if badges:
            time.sleep(2)  # let MicroPython finish starting before mpremote connects
    if not badges:
        sys.exit(
            "No badge found on USB. It must be plugged in with a data cable,\n"
            "awake, and in normal mode (menu or an app showing), not disk mode.\n"
            "`mpremote devs` lists what's connected.")
    if len(badges) > 1:
        listed = "\n".join("  {}  ({})".format(p, m) for p, m in badges)
        sys.exit("More than one badge connected; pick one with --port:\n" + listed)
    return badges[0][0]


def parse_info(output):
    for line in output.splitlines():
        if line.startswith("BADGE_INFO "):
            return json.loads(line[len("BADGE_INFO "):])
    raise ValueError("no BADGE_INFO line in:\n" + output)


def mpremote_command(port, restart=True):
    """The mpremote call that reads the badge. mpremote stops the running
    program to do it, which leaves the screen frozen on its last picture,
    so by default it ends with a hard reset (like pressing RESET) and the
    badge restarts into the menu, or Mood Badger in kiosk or start-in-app mode."""
    cmd = ["mpremote", "connect", port, "exec", DEVICE_SNIPPET]
    return cmd + ["reset"] if restart else cmd


def read_badge(port, restart=True):
    result = run(mpremote_command(port, restart))
    if result.returncode != 0:
        sys.exit("mpremote failed:\n" + (result.stderr or result.stdout))
    return parse_info(result.stdout)


def latest_for(model):
    """(release dict, None) or (None, reason)."""
    if model not in rel.MODELS:
        return None, "not a supported badge"
    try:
        return rel.fetch_release(model), None
    except (OSError, ValueError) as e:  # offline, rate-limited ...
        return None, "couldn't reach GitHub ({})".format(e)


def summarise(port, info, release):
    """Add derived fields (build date, verdict, app, boot mode) to ``info``."""
    info["port"] = port
    info["build_date"] = rel.build_date(info["version"])
    apps = info.get("apps")
    info["app_installed"] = None if apps is None else APP in apps
    info["boot_mode"] = None if info.get("main_py") is None else boot_mode(info["main_py"])
    if release:
        info["latest_tag"] = release["tag_name"]
        info["latest_published"] = release.get("published_at", "")[:10]
        info["firmware_status"] = rel.firmware_status(
            info["build_date"], info["latest_published"])
    return info


def report(info, why_not):
    model = info["model"]
    built = info["build_date"]
    lines = [
        ("Port", info["port"]),
        ("Model", "{}  (from {})".format(model, info["model_source"])),
        ("Board", info["machine"]),
        ("MicroPython", "{}  ({})".format(info["release"], info["version"])),
        ("Mood Badger", {True: "installed", False: "not installed", None: "unknown"}[
            info["app_installed"]]),
        ("Start-up", START_UP_TEXT[info["boot_mode"]]),
        ("Saved mood", info.get("state") or "none"),
        ("Free space", "{} KB".format(info["free_kb"]) if info.get("free_kb") is not None
         else "unknown"),
    ]
    if "latest_tag" in info:
        verdict = {
            "current": "looks current (built {})".format(built),
            "older": "OLDER: built {}, before the latest release".format(built),
            "newer": "built {}, after the latest release (pre-release or custom?)".format(built),
            "unknown": "can't tell (no build date in the version string)",
        }[info["firmware_status"]]
        lines.append(("Latest", "{} {}, published {}".format(
            rel.repo_for(model), info["latest_tag"], info["latest_published"])))
        lines.append(("Firmware", verdict))
    else:
        lines.append(("Latest", why_not))

    width = max(len(k) for k, _ in lines) + 1
    for key, value in lines:
        print("{} {}".format((key + ":").ljust(width), value))
    if model not in rel.MODELS:
        print("\nThese tools support {} only.".format(" and ".join(rel.MODELS)))



def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", help="the badge's serial port (default: find it)")
    parser.add_argument("--json", action="store_true", help="print the details as JSON")
    parser.add_argument("--offline", action="store_true",
                        help="don't look up the latest release")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="wait this long for the badge to appear (default: don't wait)")
    parser.add_argument("--no-restart", action="store_true",
                        help="leave the badge stopped at the REPL instead of restarting it")
    args = parser.parse_args()

    if not shutil.which("mpremote"):
        sys.exit("mpremote not found. Install it with: pip install mpremote")
    port = choose_port(args.port, args.wait)
    info = read_badge(port, restart=not args.no_restart)
    release, why_not = ((None, "not checked (--offline)") if args.offline
                        else latest_for(info["model"]))
    info = summarise(port, info, release)
    if args.json:
        info.pop("main_py", None)
        print(json.dumps(info, indent=2))
    else:
        report(info, why_not)


if __name__ == "__main__":
    main()
