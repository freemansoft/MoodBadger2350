"""Shared helpers for the badge tools (badge_info, flash_firmware, install).

Looks up Pimoroni's Badgeware firmware releases on GitHub, recognises a
badge among the serial ports, and finds mounted USB drives by label.
Standard library only, so the tools run with any Python 3; the GitHub
API is used without a token (60 requests an hour is plenty).

Adapted from claude-buddy-badgeware's tools/badgeware_release.py.
"""

import datetime
import json
import os
import re
import string
import sys
import time
import urllib.request
from pathlib import Path

# badge.model values these tools handle. Badgeware derives badge.model
# from os.uname().machine: "badger", "tufty" or "blinky" (not a target).
MODELS = ("badger", "tufty")

# Each model's firmware lives in its own repo: pimoroni/badger2350 ...
REPO = "pimoroni/{}2350"
API = "https://api.github.com/repos/{repo}/releases/{which}"
USER_AGENT = "moodbadger2350-tools"

# A badge in normal (MicroPython) mode, as `mpremote devs` lists it:
#   /dev/cu.usbmodem201401 bb71... 2e8a:1101 Pimoroni Pimoroni Tufty 2350 MicroPython
DEVICE_RE = re.compile(r"\b(Badger|Tufty|Blinky) 2350\b", re.IGNORECASE)

# MicroPython's os.uname().version ends "... on YYYY-MM-DD" (build date).
BUILD_DATE_RE = re.compile(r"\bon (\d{4}-\d{2}-\d{2})\b")

# UF2 blocks start with these two little-endian magic numbers.
UF2_MAGIC = b"UF2\n" + (0x9E5D5157).to_bytes(4, "little")

# A build more than this many days before the latest release's publish
# date counts as older. Pimoroni's CI builds and publishes within hours,
# so a few days' slack only absorbs time zones and re-runs.
BUILD_SLACK_DAYS = 3


def repo_for(model):
    return REPO.format(model)


def fetch_release(model, tag=None, timeout=15):
    """The latest (non-pre-release) release for ``model``, or ``tag``."""
    which = "tags/" + tag if tag else "latest"
    url = API.format(repo=repo_for(model), which=which)
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def asset_name(model, tag, with_filesystem):
    """Pimoroni's file name, e.g. badger-v3.1.1-micropython.uf2."""
    suffix = "-with-filesystem" if with_filesystem else ""
    return "{}-{}-micropython{}.uf2".format(model, tag, suffix)


def pick_asset(release, model, with_filesystem):
    """The release asset (a dict from the API) for this model and flavour."""
    want = asset_name(model, release["tag_name"], with_filesystem)
    for asset in release.get("assets", ()):
        if asset.get("name") == want:
            return asset
    names = ", ".join(a.get("name", "?") for a in release.get("assets", ()))
    raise LookupError("{} has no {} (assets: {})".format(
        release["tag_name"], want, names or "none"))


def build_date(version):
    """'YYYY-MM-DD' from os.uname().version, or None."""
    match = BUILD_DATE_RE.search(version or "")
    return match.group(1) if match else None


def firmware_status(built, published):
    """Compare a firmware build date with a release's publish date (both
    'YYYY-MM-DD...'). Returns "current", "older", "newer" or "unknown".
    A heuristic: the firmware records when it was built, not which
    Pimoroni release it came from."""
    if not built or not published:
        return "unknown"
    gap = (datetime.date.fromisoformat(built)
           - datetime.date.fromisoformat(published[:10])).days
    if gap < -BUILD_SLACK_DAYS:
        return "older"
    if gap > BUILD_SLACK_DAYS:
        return "newer"
    return "current"


def is_uf2(head):
    """True if ``head`` (a file's first bytes) is a UF2 block."""
    return head[:8] == UF2_MAGIC


def badge_ports(devs_output):
    """[(port, model)] for every badge in `mpremote devs` output. Other
    serial devices (other boards, Bluetooth ports) are ignored."""
    found = []
    for line in devs_output.splitlines():
        match = DEVICE_RE.search(line)
        if match and line.split():
            found.append((line.split()[0], match.group(1).lower()))
    return found


def _windows_label(drive):
    import ctypes

    buf = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive), buf, len(buf), None, None, None, None, 0)
    return buf.value if ok else ""


def mount_bases():
    """Folders where USB drives are mounted on this system."""
    if sys.platform == "darwin":
        return [Path("/Volumes")]
    user = os.environ.get("USER", "")
    return [Path("/media") / user, Path("/run/media") / user, Path("/mnt")]


def find_volumes(labels, bases=None):
    """Mounted drives whose label is one of ``labels``. Labels vary in
    case (BADGER, Tufty2350), so they are compared upper-cased."""
    wanted = {label.upper() for label in labels}
    if os.name == "nt" and bases is None:
        drives = ("{}:\\".format(letter) for letter in string.ascii_uppercase[3:])
        return [Path(d) for d in drives
                if os.path.exists(d) and _windows_label(d).upper() in wanted]
    found = []
    for base in bases if bases is not None else mount_bases():
        if base.is_dir():
            found += [c for c in sorted(base.iterdir())
                      if c.is_dir() and c.name.upper() in wanted]
    return found


def wait_for(find, timeout, interval=1.0, clock=time.monotonic, sleep=time.sleep):
    """Call ``find()`` until it returns something truthy or ``timeout``
    seconds pass, and return its last result. Lets a tool wait for the
    user's button press (a drive mounting, a serial port appearing)
    instead of failing straight away. ``timeout`` 0 looks just once."""
    deadline = clock() + timeout
    while True:
        found = find()
        if found or clock() >= deadline:
            return found
        sleep(interval)
