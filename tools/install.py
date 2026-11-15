"""Copy Mood Badger onto a Badgeware badge in USB disk mode.

1. Double-tap RESET on the back of the badge. It mounts as a USB drive
   (BADGER on a Badger 2350; TUFTY or similar on a Tufty 2350).
2. From the repository root, run one of:

    python3 -m tools.install --eject             # app only
    python3 -m tools.install --kiosk --eject     # app, and make it the only app
    python3 -m tools.install --menu --eject      # app, and bring the menu back
    python3 -m tools.install --dest /Volumes/BADGER

3. The badge restarts when the drive is ejected. Press RESET if it
   stays on the disk mode screen.

Only apps/mood_badger is replaced (and main.py, with --kiosk or --menu).
Other apps stay, and the saved mood stays: it is in /state, on the
badge's internal LittleFS, which isn't part of the drive.

Standard library only; works on macOS, Windows and Linux.
"""

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

from tools import badgeware_release as rel

ROOT = Path(__file__).resolve().parent.parent
APP = "mood_badger"

# The app folder to install for each badge.model. Add "tufty" here when
# a Tufty build of Mood Badger exists (e.g. ROOT / "tufty" / APP).
APPS = {"badger": ROOT / "badger" / APP}

# Disk mode drive labels. The Badger's is set by PIMORONI_FATFS_LABEL in
# vendor/badger2350/board/mpconfigboard.cmake; the rest are seen in the
# wild or in Pimoroni's READMEs.
DRIVE_MODELS = {"BADGER": "badger", "BADGER2350": "badger",
                "TUFTY": "tufty", "TUFTY2350": "tufty"}

KIOSK_MAIN = ROOT / "kiosk" / "main.py"
# The stock main.py from the pinned firmware (v3.1.1). A newer firmware
# may ship a different one; take it from that release if they differ.
STOCK_MAIN = ROOT / "vendor" / "badger2350" / "firmware" / "main.py"

JUNK = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "._*")


def is_kiosk(main_py):
    """True if a main.py launches Mood Badger directly (kiosk/main.py)."""
    return 'launch("/system/apps/{}")'.format(APP) in main_py


def model_for_drive(root):
    return DRIVE_MODELS.get(Path(root).name.upper())


def looks_like_badge(root):
    return (root / "apps").is_dir() and (root / "main.py").is_file()


def _ignore_missing(_func, _path, exc):
    """rmtree error handler. On macOS a FAT drive holds "._" companion
    files that vanish with their main file; one already gone is fine."""
    if not isinstance(exc, FileNotFoundError):
        raise exc


def _remove_tree(path):
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_ignore_missing)
    else:
        shutil.rmtree(path, onerror=lambda f, p, info: _ignore_missing(f, p, info[1]))


def staging_dir(root):
    """Where the new copy is built: at the drive's root, outside apps/,
    so the menu never lists a half-copied app (it lists apps/ folders
    holding an __init__.py)."""
    return root / ".{}.new".format(APP)


def remove_appledouble(folder):
    """Delete the "._" files macOS writes beside each file on a FAT
    drive. It adds a com.apple.provenance attribute to every file a
    process writes, and FAT can only store it as a 4 KB "._" file. The
    badge never reads them; they only waste space."""
    partner = folder.parent / ("._" + folder.name)
    junk = [partner] if partner.is_file() else []
    junk += [p for p in folder.rglob("._*") if p.is_file()]
    for path in junk:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def install_app(src, root):
    """Replace apps/<APP> on the drive at ``root`` with ``src``, leaving
    out caches and macOS metadata. Returns the target folder.

    The copy is built and checked in staging_dir() first, then swapped
    in with renames, so if the copy is interrupted (a RESET, a pulled
    cable) the old app is still there and still works."""
    target = root / "apps" / APP
    staging = staging_dir(root)
    old = root / ".{}.old".format(APP)
    for leftover in (staging, old):
        if leftover.exists():
            _remove_tree(leftover)

    shutil.copytree(src, staging, ignore=JUNK, copy_function=shutil.copyfile)
    remove_appledouble(staging)
    bad = verify_copy(src, staging)
    if bad:
        raise OSError("copy check failed for: {}".format(", ".join(bad)))

    if target.exists():
        target.rename(old)
    staging.rename(target)
    if old.exists():
        _remove_tree(old)
    remove_appledouble(target)
    return target


def _app_files(folder):
    """Relative paths of the files install_app copies (the JUNK filter)."""
    files = []
    for path in sorted(folder.rglob("*")):
        rel_path = path.relative_to(folder)
        if path.is_file() and not any(
                part == "__pycache__" or part.startswith(".") or part.endswith(".pyc")
                for part in rel_path.parts):
            files.append(str(rel_path))
    return files


def verify_copy(src, target):
    """Relative paths of app files that are missing or differ on the drive."""
    bad = []
    for name in _app_files(src):
        copy = target / name
        if not copy.is_file() or not filecmp.cmp(src / name, copy, shallow=False):
            bad.append(name)
    return bad


def set_main(root, main_py):
    """Replace the drive's main.py with ``main_py`` (kiosk or stock)."""
    shutil.copyfile(main_py, root / "main.py")


def eject(root):
    """Eject the drive so the badge restarts. True if it worked."""
    if sys.platform == "darwin":
        cmd = ["diskutil", "eject", str(root)]
    elif sys.platform.startswith("linux"):
        cmd = ["umount", str(root)]
    else:
        return False
    return subprocess.run(cmd, capture_output=True).returncode == 0


def find_badge_drives():
    return [d for d in rel.find_volumes(DRIVE_MODELS) if looks_like_badge(d)]


def choose_drive(dest, wait=0):
    if dest:
        root = Path(dest)
        if not looks_like_badge(root):
            sys.exit("{} doesn't look like a badge drive (no apps/ or main.py).".format(root))
        return root
    found = find_badge_drives()
    if not found and wait:
        print("Waiting up to {} s for the badge's drive (double-tap RESET) ...".format(wait),
              flush=True)
        found = rel.wait_for(find_badge_drives, wait)
    if not found:
        sys.exit("No badge drive found. Double-tap RESET on the badge to enter\n"
                 "disk mode, wait for the drive to appear, or pass --dest.")
    if len(found) > 1:
        sys.exit("Several badge drives found ({}); pass --dest.".format(
            ", ".join(map(str, found))))
    return found[0]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", help="root of the badge's drive (holds apps/ and main.py)")
    parser.add_argument("--model", choices=rel.MODELS,
                        help="badge model, if the drive's label doesn't say")
    boot = parser.add_mutually_exclusive_group()
    boot.add_argument("--kiosk", action="store_true",
                      help="also make Mood Badger the only app (kiosk/main.py)")
    boot.add_argument("--menu", action="store_true",
                      help="also restore the stock main.py, bringing the menu back")
    parser.add_argument("--eject", action="store_true", help="eject the drive afterwards")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="wait this long for the drive to appear (default: don't wait)")
    args = parser.parse_args()

    root = choose_drive(args.dest, args.wait)
    model = args.model or model_for_drive(root)
    if model is None:
        sys.exit("Can't tell which badge {} is from its name; pass --model.".format(root))
    if model not in APPS:
        sys.exit("Mood Badger has no {} build yet (only: {}). Nothing copied.".format(
            model, ", ".join(APPS)))

    src = APPS[model]
    print("Copying to {}. Don't press any buttons until this says it has ejected."
          .format(root), flush=True)
    try:
        target = install_app(src, root)
    except OSError as e:
        sys.exit("The copy failed ({}).\nThe old Mood Badger is still in place. If the "
                 "drive is still mounted, run this again.".format(e))
    print("Installed {} files to {}".format(len(_app_files(src)), target))

    if args.kiosk:
        set_main(root, KIOSK_MAIN)
        print("Kiosk mode on: main.py now starts Mood Badger.")
    elif args.menu:
        set_main(root, STOCK_MAIN)
        print("Menu restored: main.py is the stock one from vendor/badger2350 (v3.1.1).")
    print("Kiosk mode: {}".format("on" if is_kiosk((root / "main.py").read_text()) else "off"))

    if args.eject:
        if eject(root):
            print("Ejected. The badge restarts by itself; if the disk screen is still\n"
                  "showing after 10 seconds, press RESET once.")
        else:
            print("Couldn't eject {}. Don't press RESET yet: eject it from Finder\n"
                  "first, or some files may not reach the badge.".format(root))
    else:
        print("Eject the drive before pressing any button: until it is ejected,\n"
              "some files may still be on their way to the badge.")


if __name__ == "__main__":
    main()
