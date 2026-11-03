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
