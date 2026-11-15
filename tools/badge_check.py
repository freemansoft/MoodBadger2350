"""Check a badge after an install, or read why it last restarted.

    python3 -m tools.badge_check files
    python3 -m tools.badge_check wake-reason
    python3 -m tools.badge_check wake-reason --after-restart 180

files: lists /system/apps/mood_badger on the badge itself and compares it
with the app folder here (names and sizes), so it shows what the badge
really holds. Run it after the eject: until then macOS may still be holding
writes, so the mounted drive can look right when the badge isn't.

wake-reason: prints powman.get_wake_reason() with its name, and what a
Tufty in start-in-app mode opens for it. With --after-restart SECONDS it
first waits for the badge to drop off USB and come back (press RESET, or
HOME, while it waits), so the reading is from that restart.

The badge must be in normal mode (menu or an app on screen). Both checks
stop the running app and end with machine.reset(), the restart HOME makes:
the badge comes back on the menu, also a Tufty in start-in-app mode
(RESET brings Mood Badger back).

Needs mpremote (pip install mpremote). Standard library otherwise.
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from tools import badge_info
from tools.install import APP, APPS, _app_files

TAG = "BADGE_CHECK "

# Runs on the badge: every file under the app folder, with its size.
FILES_SNIPPET = r"""
import json, os
root = "/system/apps/APP"
files = {}
def walk(path):
    for name in os.listdir(path):
        full = path + "/" + name
        st = os.stat(full)
        if st[0] & 0x4000:
            walk(full)
        else:
            files[full[len(root) + 1:]] = st[6]
try:
    walk(root)
    print("TAG" + json.dumps({"files": files}))
except OSError:
    print("TAG" + json.dumps({"files": None}))
""".replace("APP", APP).replace("TAG", TAG)

# Runs on the badge: the restart reason and powman's names for the codes.
WAKE_SNIPPET = r"""
import json, powman
names = {k: getattr(powman, k) for k in dir(powman) if k.startswith("WAKE_")}
print("TAG" + json.dumps({"reason": powman.get_wake_reason(), "names": names}))
""".replace("TAG", TAG)


def mpremote_command(port, snippet):
    """Run ``snippet`` on the badge, then restart it (machine.reset()) so it
    isn't left frozen at the REPL."""
    return ["mpremote", "connect", port, "exec", snippet, "reset"]


def parse_tagged(output):
    for line in output.splitlines():
        if line.startswith(TAG):
            return json.loads(line[len(TAG):])
    raise ValueError("no {}line in:\n{}".format(TAG, output))


def local_files(folder):
    """{relative path: size} of the files tools.install copies from ``folder``."""
    return {name: (Path(folder) / name).stat().st_size for name in _app_files(Path(folder))}


def compare_files(local, badge):
    """Problems found comparing {path: size} here with the badge's; {} if none."""
    junk = sorted(n for n in badge if n.split("/")[-1].startswith("._") or "__pycache__" in n)
    problems = {
        "missing": sorted(n for n in local if n not in badge),
        "different size": sorted(n for n in local if n in badge and badge[n] != local[n]),
        "not in the app": sorted(n for n in badge if n not in local and n not in junk),
        "macOS junk": junk,
    }
    return {k: v for k, v in problems.items() if v}


def wake_name(reason, names):
    for name, value in names.items():
        if value == reason:
            return name
    return "unknown ({})".format(reason)


def start_in_app_meaning(name):
    """What kiosk/start_in_app.py does after a restart with this reason."""
    if name == "WAKE_WATCHDOG":
        return "start-in-app opens the app list (HOME, machine.reset(), or an eject)"
    if name == "WAKE_DOUBLETAP":
        return "disk mode; main.py doesn't run"
    return "start-in-app opens Mood Badger"


def wait_for_restart(present, timeout, interval=0.2, clock=time.monotonic, sleep=time.sleep):
    """True once ``present()`` has gone false and then true again (the badge
    dropped off USB and came back), False if that doesn't happen in time."""
    start, gone = clock(), False
    while clock() - start < timeout:
        if not present():
            gone = True
        elif gone:
            return True
        sleep(interval)
    return False


def read(port, snippet):
    result = badge_info.run(mpremote_command(port, snippet))
    if result.returncode != 0:
        sys.exit("mpremote failed:\n" + (result.stderr or result.stdout))
    return parse_tagged(result.stdout)


def model_of(port):
    for p, model in badge_info.list_badges():
        if p == port:
            return model
    return None


def check_files(port):
    model = model_of(port) or "badger"
    src = APPS.get(model, APPS["badger"])
    badge = read(port, FILES_SNIPPET)["files"]
    if badge is None:
        sys.exit("Mood Badger isn't installed on the badge (no /system/apps/{}).".format(APP))
    local = local_files(src)
    problems = compare_files(local, badge)
    print("{} files on the badge, {} in {}".format(len(badge), len(local), src.relative_to(
        Path(__file__).resolve().parent.parent)))
    if not problems:
        print("The badge's copy matches.")
        return
    for kind, names in problems.items():
        print("{}: {}".format(kind, ", ".join(names)))
    sys.exit(1)


def check_wake(port, after_restart):
    if after_restart:
        print("Waiting up to {} s for the badge to restart (press RESET or HOME) ..."
              .format(after_restart), flush=True)
        if not wait_for_restart(lambda: port in [p for p, _ in badge_info.list_badges()],
                                after_restart):
            sys.exit("The badge didn't restart in {} s; nothing read.".format(after_restart))
        time.sleep(3)  # let MicroPython finish starting before mpremote connects
    info = read(port, WAKE_SNIPPET)
    name = wake_name(info["reason"], info["names"])
    print("Wake reason: {} = {}".format(info["reason"], name))
    print("On a Tufty: {}".format(start_in_app_meaning(name)))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("check", choices=("files", "wake-reason"))
    parser.add_argument("--port", help="the badge's serial port (default: find it)")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="wait this long for the badge to appear (default: don't wait)")
    parser.add_argument("--after-restart", type=int, default=0, metavar="SECONDS",
                        help="wake-reason: first wait this long for the badge to restart")
    args = parser.parse_args()

    if not shutil.which("mpremote"):
        sys.exit("mpremote not found. Install it with: pip install mpremote")
    port = badge_info.choose_port(args.port, args.wait)
    if args.check == "files":
        check_files(port)
    else:
        check_wake(port, args.after_restart)


if __name__ == "__main__":
    main()
