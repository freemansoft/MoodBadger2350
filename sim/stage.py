"""Stage a servable simulator site in sim/dist.

The site holds the host page, the badgeware-wasm Badger build, and fs/: every
file the page writes into the simulated badge's filesystem, listed in
fs/manifest.json as [device path, file under fs/] pairs.

Run from anywhere: python3 sim/stage.py
"""

import json
import shutil
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
FIRMWARE = ROOT / "vendor" / "badger2350"
DIST = SIM / "dist"

# The firmware imports its own submodules as __import__(".frozen/badgeware/x"),
# which only resolves for frozen modules. MicroPython reads the leading dot of a
# filesystem path as a relative import, so the sim stages the package at
# /frozen and rewrites those imports in the staged copies (never in vendor/).
FROZEN_IMPORT = '__import__(".frozen/'
STAGED_IMPORT = '__import__("/frozen/'

# device directory -> local source directory
TREES = [
    ("/frozen/badgeware", FIRMWARE / "modules" / "common" / "badgeware"),
    ("/rom/fonts", FIRMWARE / "romfs" / "fonts"),
    ("/system/apps/mood_badger", ROOT / "badger" / "mood_badger"),
    ("/lib", SIM / "stubs"),
]


def stage():
    if DIST.exists():
        shutil.rmtree(DIST)
    fs = DIST / "fs"
    fs.mkdir(parents=True)

    for name in ("micropython.mjs", "micropython.wasm"):
        shutil.copy2(SIM / "wasm" / name, DIST / name)
    shutil.copy2(SIM / "index.html", DIST / "index.html")
    shutil.copy2(SIM / "boot.py", DIST / "boot.py")

    manifest = []
    rewrites = 0
    for device_dir, source in TREES:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name.startswith("."):
                continue
            relative = path.relative_to(source).as_posix()
            local = (device_dir.strip("/") + "/" + relative)
            (fs / local).parent.mkdir(parents=True, exist_ok=True)
            if device_dir == "/frozen/badgeware" and path.suffix == ".py":
                text = path.read_text()
                rewrites += text.count(FROZEN_IMPORT)
                (fs / local).write_text(text.replace(FROZEN_IMPORT, STAGED_IMPORT))
            else:
                shutil.copy2(path, fs / local)
            manifest.append([device_dir + "/" + relative, local])

    if rewrites == 0:
        raise SystemExit(f"no {FROZEN_IMPORT} imports found; the firmware layout changed")

    (fs / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return len(manifest)


if __name__ == "__main__":
    print(f"staged {stage()} files in {DIST.relative_to(ROOT)}")
