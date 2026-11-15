import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT = 264, 176

sys.path.insert(0, str(ROOT / "badger" / "mood_badger"))
import moods  # noqa: E402

TUFTY = moods.TUFTY

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def pip_filled(frame, index, count=8):
    # centre pixel of pip `index` for a set of `count` moods
    top = (HEIGHT - count * 10) // 2
    return frame[(top + index * 10 + 4) * WIDTH + 254] == 0


def black(frame, x, y):
    return frame[y * WIDTH + x] == 0


def run_sim(tmp_path, button, model="badger"):
    subprocess.run([sys.executable, "sim/stage.py"], cwd=ROOT, check=True)
    out = tmp_path / "frames.json"
    subprocess.run(
        ["node", "sim/run_headless.mjs", "--model", model, "--press", button, "--frames", str(out)],
        cwd=ROOT, check=True, timeout=120,
    )
    return json.loads(out.read_text())


# Tufty frames are colour; the runner reduces each pixel to one grey byte.
def tufty_dark(frame, x, y):
    return frame[y * 320 + x] < 64


def tufty_white(frame, x, y):
    return frame[y * 320 + x] > 191


def tufty_pip_filled(frame, index, count):
    x, y = moods.pip_positions(count, TUFTY)[index]
    half = TUFTY["pip_size"] // 2
    return tufty_dark(frame, x + half, y + half)


def test_app_boots_and_down_moves_to_next_mood(tmp_path):
    frames = run_sim(tmp_path, "DOWN")
    first, second = frames["before"], frames["after"]

    assert frames["status"] == "ok"
    assert len(first) == WIDTH * HEIGHT
    assert set(first) <= {0, 85, 170, 255}
    assert any(v == 0 for v in first[: WIDTH * 140])
    assert first != second
    # the first set (Material faces) has seven moods
    assert pip_filled(second, 1, count=7)
    assert not pip_filled(second, 0, count=7)


def test_set_arrows_drawn_and_c_moves_to_next_set(tmp_path):
    frames = run_sim(tmp_path, "C")
    first, second = frames["before"], frames["after"]

    assert frames["status"] == "ok"
    # filled arrows above A (left) and C (right), drawn by the real firmware
    for frame in (first, second):
        assert black(frame, 44, 157) and black(frame, 209, 157)
    # the next set (Lego faces) has eight moods and opens on its first
    assert pip_filled(second, 0, count=8)
    assert not pip_filled(second, 1, count=8)


def test_browser_page_never_uses_cached_app_files():
    # A cached app file would run the old app after re-staging.
    page = (ROOT / "sim" / "index.html").read_text()
    fetches = page.count("fetch(")
    assert fetches == 3
    assert page.count('{ cache: "no-store" }') == fetches


def test_tufty_boots_full_resolution_and_down_moves_to_next_mood(tmp_path):
    frames = run_sim(tmp_path, "DOWN", model="tufty")
    after = frames["after"]

    assert frames["status"] == "ok"
    assert (frames["width"], frames["height"]) == (320, 240)
    assert len(after) == 320 * 240
    assert frames["before"] != after
    # the first set (Material faces) has seven moods
    assert tufty_pip_filled(after, 1, 7) and not tufty_pip_filled(after, 0, 7)
    # pure white, matching the pictures' own white (the Tufty's color.white is off-white)
    assert after[5 * 320 + 5] == 255


def test_tufty_set_arrows_drawn_and_c_moves_to_next_set(tmp_path):
    frames = run_sim(tmp_path, "C", model="tufty")
    before, after = frames["before"], frames["after"]

    assert frames["status"] == "ok"
    for frame in (before, after):
        assert tufty_dark(frame, TUFTY["arrow_a_x"] + 1, TUFTY["arrow_mid_y"])
        assert tufty_dark(frame, TUFTY["arrow_c_x"] - 1, TUFTY["arrow_mid_y"])
    # the next set (Lego faces) has eight moods and opens on its first
    assert tufty_pip_filled(after, 0, 8) and not tufty_pip_filled(after, 1, 8)
