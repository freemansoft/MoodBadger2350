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


def test_app_readme_states_controls_and_minimum_firmware():
    text = (ROOT / "badger" / "mood_badger" / "README.md").read_text()
    assert "v3.1.1" in text and "config.json" in text
