import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIOSK = ROOT / "kiosk" / "main.py"


def run_kiosk():
    calls = []
    runpy.run_path(str(KIOSK), init_globals={
        "launch": lambda path: calls.append(("launch", path)),
        "reset": lambda: calls.append(("reset",)),
    })
    return calls


def test_kiosk_launches_mood_badger_then_resets():
    # Always Mood Badger, whatever the menu last saved; reset if the app ever returns.
    assert run_kiosk() == [("launch", "/system/apps/mood_badger"), ("reset",)]


def test_kiosk_path_matches_the_app_folder():
    assert (ROOT / "badger" / "mood_badger" / "__init__.py").exists()
    assert "/system/apps/mood_badger" in KIOSK.read_text()


def test_readme_explains_kiosk_install_and_restore():
    text = (ROOT / "README.md").read_text()
    assert "kiosk/main.py" in text
    assert "vendor/badger2350/firmware/main.py" in text


# --- start-in-app: Mood Badger on power-on and RESET, the menu after HOME ----

import sys  # noqa: E402
import types  # noqa: E402

import pytest  # noqa: E402

START_IN_APP = ROOT / "kiosk" / "start_in_app.py"

# Codes from vendor/tufty2350/modules/c/powman/bindings.c
WAKE = {"WAKE_BUTTON_DOWN": 0x04, "WAKE_VBUS_DETECT": 0x07,
        "WAKE_RESET": 0xf1, "WAKE_WATCHDOG": 0xf2, "WAKE_UNKNOWN": 0xff}


class FakeBadge:
    def __init__(self, calls):
        self.calls = calls

    def poll(self):
        self.calls.append(("poll",))

    def pressed(self):
        return False

    held = released = pressed


def run_start_in_app(monkeypatch, reason, menu_returns="/system/apps/clock"):
    calls = []
    powman = types.ModuleType("powman")
    for name, value in WAKE.items():
        setattr(powman, name, value)
    powman.get_wake_reason = lambda: WAKE[reason]
    monkeypatch.setitem(sys.modules, "powman", powman)

    def launch(path):
        calls.append(("launch", path))
        return menu_returns if path == "/system/apps/menu" else None

    runpy.run_path(str(START_IN_APP), init_globals={
        "launch": launch, "reset": lambda: calls.append(("reset",)), "badge": FakeBadge(calls)})
    return calls


@pytest.mark.parametrize("reason", ["WAKE_RESET", "WAKE_BUTTON_DOWN", "WAKE_VBUS_DETECT", "WAKE_UNKNOWN"])
def test_start_in_app_opens_mood_badger_after_reset_or_power_on(monkeypatch, reason):
    # No poll: the app ignores the waking press itself, on its first frame.
    assert run_start_in_app(monkeypatch, reason) == [
        ("launch", "/system/apps/mood_badger"), ("reset",)]


def test_start_in_app_opens_menu_after_home(monkeypatch):
    assert run_start_in_app(monkeypatch, "WAKE_WATCHDOG") == [
        ("poll",), ("launch", "/system/apps/menu"), ("launch", "/system/apps/clock"), ("reset",)]


def test_start_in_app_menu_returning_none_just_resets(monkeypatch):
    assert run_start_in_app(monkeypatch, "WAKE_WATCHDOG", menu_returns=None) == [
        ("poll",), ("launch", "/system/apps/menu"), ("reset",)]


def test_start_in_app_menu_flow_matches_the_stock_tufty_main():
    # Guards against a firmware bump changing the flow start_in_app.py copies.
    stock = (ROOT / "vendor" / "tufty2350" / "firmware" / "main.py").read_text()
    assert 'launch("/system/apps/menu")' in stock
    assert "badge.pressed() or badge.held() or badge.released()" in stock
