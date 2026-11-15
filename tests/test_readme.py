import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("required", [
    "https://badgewa.re", "https://badgewa.re/docs", "https://github.com/pimoroni/badger2350",
    "https://github.com/pimoroni/badgeware-docs", "https://github.com/simonpainter/MoodBadger",
    "https://badger.github.io/", "https://badger.github.io/apps/", "https://github.com/badger/home",
    "https://github.com/pimoroni/badgeware-contrib",
    "https://github.com/orgs/pimoroni/repositories?q=badgeware",
    "https://github.com/pimoroni/badgeware-simulator", "https://github.com/pimoroni/badgeware-web-simulator",
    "https://github.com/pimoroni/badgeware-wasm", "https://github.com/pimoroni/badgeware-ide",
    "https://github.com/pimoroni/badgeware-cpp", "https://github.com/pimoroni/badgeware-fonts",
    "https://github.com/pimoroni/picovector-micropython",
    "https://github.com/pimoroni/tufty2350", "https://github.com/pimoroni/blinky2350",
    "https://shop.pimoroni.com/en-us/products/badger-2350?variant=55801169707387",
    "https://learn.pimoroni.com/article/badgeware-tube-status-app",
    "https://forums.pimoroni.com/t/migrating-a-badger2040-app-to-badger2350-moodbadger",
    "/apps/mood_badger", "v3.1.1",
])
def test_readme_contains_reference(required):
    assert required in (ROOT / "README.md").read_text()


def test_readme_gives_a_mac_copy_command_that_skips_junk_files():
    text = (ROOT / "README.md").read_text()
    assert "rsync -rv --exclude __pycache__ --exclude '.*' badger/mood_badger/ /Volumes/" in text
    assert "diskutil eject" in text


def test_app_readme_states_controls_and_minimum_firmware():
    text = (ROOT / "badger" / "mood_badger" / "README.md").read_text()
    assert "v3.1.1" in text and "config.json" in text


def test_mood_images_carry_their_apache_licence():
    # The images are Google Material icons; Apache 2.0 needs its text shipped with them.
    licence = (ROOT / "badger" / "mood_badger" / "assets" / "LICENSE").read_text()
    assert "Apache License" in licence and "Version 2.0, January 2004" in licence
    for path in ("README.md", "LICENSE", "badger/mood_badger/README.md"):
        text = (ROOT / path).read_text()
        assert "Material" in text and "Apache License 2.0" in text, path
        assert "not cleared for redistribution" not in text and "remain his" not in text, path


def test_readme_explains_start_in_app_for_the_tufty():
    text = (ROOT / "README.md").read_text()
    assert "--start-in-app" in text
    assert "vendor/tufty2350/firmware/main.py" in text


def _slug(heading):
    # GitHub's heading anchors: lower case, punctuation dropped, spaces to hyphens.
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def test_readme_internal_links_resolve():
    text = (ROOT / "README.md").read_text()
    anchors = {_slug(h) for h in re.findall(r"^#+ (.+)$", text, re.MULTILINE)}
    links = set(re.findall(r"\]\(#([\w-]+)\)", text))
    assert links and links <= anchors, links - anchors


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + 1)
    return text[start:end if end > 0 else None]


def test_readme_start_up_section_covers_both_badges_and_kiosk():
    text = (ROOT / "README.md").read_text()
    assert "## On a Tufty 2350" not in text, "start-up behaviour lives in one section"
    section = _section(text, "## What the badge opens")
    for needed in ("--start-in-app", "--kiosk", "--menu", "/Volumes/BADGER", "/Volumes/TUFTY",
                   "vendor/badger2350/firmware/main.py", "vendor/tufty2350/firmware/main.py",
                   "kiosk/main.py", "kiosk/start_in_app.py"):
        assert needed in section, needed
    kiosk = section[section.index("### Kiosk mode"):]
    assert "start-in-app" in kiosk, "kiosk mode must say it replaces start-in-app on a Tufty"
