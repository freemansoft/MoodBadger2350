"""Download Pimoroni's Badgeware firmware and flash it onto a badge.

Find the model first with `python3 -m tools.badge_info` (it reads
badge.model). The bootloader drive can't say which badge it is, so you
pass the model here.

Every release has two images; choose one every time:

  --firmware-only    replaces only the firmware. Apps, main.py and the
                     saved mood stay. Right for a badge already in use.
  --with-filesystem  ALSO resets the badge's drive to Pimoroni's
                     defaults: every app, Mood Badger included, and
                     main.py (so kiosk and start-in-app mode are
                     undone). Good for a new badge, so its default
                     apps match the firmware.

Then put the badge in bootloader mode: hold BOOT, tap RESET, let go of
BOOT. A drive named RP2350 appears. Run:

    python3 -m tools.flash_firmware --model badger --firmware-only
    python3 -m tools.flash_firmware --model badger --with-filesystem
    python3 -m tools.flash_firmware --model tufty --firmware-only --tag v3.1.1
    python3 -m tools.flash_firmware --model badger --firmware-only --download-only

The badge restarts by itself when the copy finishes. Standard
library only; works on macOS, Windows and Linux.

Adapted from claude-buddy-badgeware's tools/flash_firmware.py.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from tools import badgeware_release as rel

BOOT_LABEL = "RP2350"
CACHE = Path(tempfile.gettempdir()) / "badgeware-firmware"
# Seconds to wait for the badge to boot the new firmware and reappear.
RESTART_TIMEOUT = 30


def find_boot_drives():
    """Mounted RP2350 bootloader drives (they hold INFO_UF2.TXT)."""
    return [d for d in rel.find_volumes((BOOT_LABEL,)) if (d / "INFO_UF2.TXT").is_file()]


def _mpremote_devs():
    try:
        return subprocess.run(["mpremote", "devs"], capture_output=True, text=True,
                              timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def wait_for_restart(model, timeout, list_devs=_mpremote_devs, interval=2):
    """The serial port of a ``model`` badge back in normal mode, or None
    if none appears within ``timeout`` seconds. Its return is the sure
    sign the badge took the image and booted it."""
    def find():
        return [port for port, found in rel.badge_ports(list_devs()) if found == model]
    ports = rel.wait_for(find, timeout, interval=interval)
    return ports[0] if ports else None


def download(asset):
    """Fetch ``asset`` into the cache (reused if already complete) and
    check it is a whole UF2 file."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / asset["name"]
    size = asset.get("size")
    if not (path.is_file() and path.stat().st_size == size):
        print("Downloading {} ({:.1f} MB) ...".format(asset["name"], (size or 0) / 1e6))
        req = urllib.request.Request(
            asset["browser_download_url"], headers={"User-Agent": rel.USER_AGENT})
        part = path.with_suffix(".part")
        with urllib.request.urlopen(req, timeout=60) as resp, open(part, "wb") as out:
            shutil.copyfileobj(resp, out)
        part.replace(path)
    if size is not None and path.stat().st_size != size:
        sys.exit("Download is {} bytes, expected {}; try again.".format(
            path.stat().st_size, size))
    with open(path, "rb") as f:
        if not rel.is_uf2(f.read(8)):
            sys.exit("{} isn't a UF2 file; not flashing it.".format(path))
    return path


def confirm_wipe(model, yes):
    print(
        "\n--with-filesystem resets the badge's drive to Pimoroni's defaults.\n"
        "Mood Badger and any other added apps are removed, and main.py is\n"
        "replaced (kiosk and start-in-app mode are undone). Use --firmware-only to keep them.")
    if yes:
        return
    answer = input("Type the model name ({}) to go ahead: ".format(model)).strip().lower()
    if answer != model:
        sys.exit("Not flashed.")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True, choices=rel.MODELS,
                        help="badge.model, as tools.badge_info reports it")
    flavour = parser.add_mutually_exclusive_group(required=True)
    flavour.add_argument("--firmware-only", action="store_true", help="keep apps and files")
    flavour.add_argument("--with-filesystem", action="store_true",
                         help="also reset all apps and files to Pimoroni's defaults")
    parser.add_argument("--tag", help="release tag, e.g. v3.1.1 (default: latest release)")
    parser.add_argument("--dest", help="the RP2350 drive (default: find it)")
    parser.add_argument("--download-only", action="store_true",
                        help="download and check the file, but don't flash")
    parser.add_argument("--yes", action="store_true",
                        help="skip the --with-filesystem confirmation")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="wait this long for the RP2350 drive (default: don't wait)")
    args = parser.parse_args()

    try:
        release = rel.fetch_release(args.model, args.tag)
        asset = rel.pick_asset(release, args.model, args.with_filesystem)
    except (OSError, ValueError, LookupError) as e:
        sys.exit("Couldn't get the release from GitHub: {}".format(e))
    print("{} {} (published {})".format(
        rel.repo_for(args.model), release["tag_name"], release.get("published_at", "")[:10]))
    path = download(asset)
    print("Firmware file: {}".format(path))
    if args.download_only:
        return

    if args.dest:
        dest = Path(args.dest)
        if not (dest / "INFO_UF2.TXT").is_file():
            sys.exit("{} isn't an RP2350 bootloader drive (no INFO_UF2.TXT).".format(dest))
    else:
        drives = find_boot_drives()
        if not drives and args.wait:
            print("Waiting up to {} s for the RP2350 drive (hold BOOT, tap RESET, "
                  "let go of BOOT) ...".format(args.wait), flush=True)
            drives = rel.wait_for(find_boot_drives, args.wait)
        if not drives:
            sys.exit("No RP2350 drive found. Hold BOOT, tap RESET, let go of BOOT,\n"
                     "wait for the RP2350 drive, then run this again (or pass --dest).")
        if len(drives) > 1:
            sys.exit("More than one RP2350 drive; pick one with --dest: "
                     + ", ".join(str(d) for d in drives))
        dest = drives[0]

    if args.with_filesystem:
        confirm_wipe(args.model, args.yes)
    print("Flashing {} firmware to {} ...".format(args.model, dest))
    print("(This must be a {}: the bootloader can't tell.)".format(args.model.capitalize()))
    print("Don't press any buttons until this says the flash is complete.", flush=True)
    try:
        shutil.copyfile(path, dest / path.name)
    except OSError:
        # The drive vanishes as soon as the badge takes the image, which
        # some systems (macOS) report as an error at the end of the copy.
        # Whether it worked is decided below, by the badge coming back.
        pass
    print("Copied. Waiting for the badge to restart ...", flush=True)
    port = wait_for_restart(args.model, RESTART_TIMEOUT)
    if port:
        print("Flash complete: the {} is back in normal mode on {}.".format(
            args.model.capitalize(), port))
        print("Check it with: python3 -m tools.badge_info")
    elif (dest / "INFO_UF2.TXT").is_file():
        sys.exit("The badge is still in bootloader mode, so it didn't take the image.\n"
                 "Run this again; the RP2350 drive is still there, so no buttons are needed.")
    else:
        sys.exit("The badge didn't come back on USB within {} s. If its screen shows the\n"
                 "menu, the flash worked (or mpremote is missing). Otherwise press RESET once,\n"
                 "then check it with: python3 -m tools.badge_info --wait 30".format(
                     RESTART_TIMEOUT))


if __name__ == "__main__":
    main()
