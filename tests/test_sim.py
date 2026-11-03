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


def test_app_boots_and_down_moves_to_next_mood(tmp_path):
    subprocess.run([sys.executable, "sim/stage.py"], cwd=ROOT, check=True)
    out = tmp_path / "frames.json"
    subprocess.run(
        ["node", "sim/run_headless.mjs", "--press", "DOWN", "--frames", str(out)],
        cwd=ROOT, check=True, timeout=120,
    )
    frames = json.loads(out.read_text())
    first, second = frames["before"], frames["after"]

    assert frames["status"] == "ok"
    assert len(first) == WIDTH * HEIGHT
    assert set(first) <= {0, 85, 170, 255}
    assert any(v == 0 for v in first[: WIDTH * 140])
    assert first != second
    assert pip_filled(second, 1)
    assert not pip_filled(second, 0)
