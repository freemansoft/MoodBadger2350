import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT = 264, 176

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def pip_filled(frame, index, count=8):
    # centre pixel of pip `index` for a set of `count` moods
    top = (HEIGHT - count * 10) // 2
    return frame[(top + index * 10 + 4) * WIDTH + 254] == 0


def black(frame, x, y):
    return frame[y * WIDTH + x] == 0


def run_sim(tmp_path, button):
    subprocess.run([sys.executable, "sim/stage.py"], cwd=ROOT, check=True)
    out = tmp_path / "frames.json"
    subprocess.run(
        ["node", "sim/run_headless.mjs", "--press", button, "--frames", str(out)],
        cwd=ROOT, check=True, timeout=120,
    )
    return json.loads(out.read_text())


def test_app_boots_and_down_moves_to_next_mood(tmp_path):
    frames = run_sim(tmp_path, "DOWN")
    first, second = frames["before"], frames["after"]

    assert frames["status"] == "ok"
    assert len(first) == WIDTH * HEIGHT
    assert set(first) <= {0, 85, 170, 255}
    assert any(v == 0 for v in first[: WIDTH * 140])
    assert first != second
    assert pip_filled(second, 1)
    assert not pip_filled(second, 0)


def test_set_arrows_drawn_and_c_moves_to_next_set(tmp_path):
    frames = run_sim(tmp_path, "C")
    first, second = frames["before"], frames["after"]

    assert frames["status"] == "ok"
    # filled arrows above A (left) and C (right), drawn by the real firmware
    for frame in (first, second):
        assert black(frame, 44, 167) and black(frame, 209, 167)
    # the next set (thumbs) has two moods and opens on its first
    assert pip_filled(second, 0, count=2)
    assert not pip_filled(second, 1, count=2)


def test_browser_page_never_uses_cached_app_files():
    # A cached app file would run the old app after re-staging.
    page = (ROOT / "sim" / "index.html").read_text()
    fetches = page.count("fetch(")
    assert fetches == 3
    assert page.count('{ cache: "no-store" }') == fetches
