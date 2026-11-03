"""Convert MoodBadger JPEGs into 4-grey PNGs for the Badger 2350 e-ink display.

Run from the repository root: python -m tools.convert_moods
"""

import json
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "badger" / "mood_badger"
SOURCE_DIR = ROOT / "vendor" / "MoodBadger" / "moods"

CELL_SIZE = (122, 136)
ICON_SIZE = (24, 24)
ICON_SOURCE = "happy"

# The SSD1680 driver ORs the RGB channels and keeps bits 7 and 6, so the panel
# shows four greys split at 64, 128 and 192.
LEVELS = (0, 85, 170, 255)


def quantise(value):
    return LEVELS[value >> 6]


def convert_image(src, dst, size):
    """Fit src inside size (keeping aspect), centre it on white and save as a 4-grey PNG."""
    grey = ImageOps.autocontrast(Image.open(src).convert("L"))
    scale = min(size[0] / grey.width, size[1] / grey.height)
    fitted = grey.resize((round(grey.width * scale), round(grey.height * scale)), Image.LANCZOS)

    canvas = Image.new("L", size, 255)
    canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))

    # Store palette indices, then attach a palette of the four panel greys.
    indexed = canvas.point(lambda v: v >> 6).convert("P")
    indexed.putpalette([v for level in LEVELS for v in (level, level, level)])
    indexed.save(dst, optimize=True)


def main():
    config = json.loads((APP_DIR / "config.json").read_text())
    assets = APP_DIR / "assets"
    assets.mkdir(exist_ok=True)

    names = sorted({image for mood_set in config["moods"] for _, image in mood_set})
    for name in names:
        stem = Path(name).stem
        convert_image(SOURCE_DIR / f"{stem}.jpg", assets / name, CELL_SIZE)
        print(f"assets/{name}")

    convert_image(SOURCE_DIR / f"{ICON_SOURCE}.jpg", APP_DIR / "icon.png", ICON_SIZE)
    print("icon.png")


if __name__ == "__main__":
    main()
