"""Build the 4-grey PNGs for the Badger 2350 e-ink display.

Most images are converted from MoodBadger's JPEGs. The sent_* faces are drawn
from Google's Material Symbols font, downloaded into .cache/ on first run.

Run from the repository root: python -m tools.convert_moods
"""

import json
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "badger" / "mood_badger"
SOURCE_DIR = ROOT / "vendor" / "MoodBadger" / "moods"

CELL_SIZE = (122, 136)
ICON_SIZE = (24, 24)

# MoodBadger's Lego figure JPEGs, renamed here by mood: image stem -> JPEG stem.
# Other JPEG-sourced images (thumbs, weather) keep their MoodBadger names.
JPEG_SOURCES = {
    "fig_chilled": "happy",
    "fig_sad": "sad",
    "fig_bored": "bored",
    "fig_annoyed": "annoyed",
    "fig_angry": "angry",
    "fig_embarrassed": "embarassed",
    "fig_surprised": "surprised",
    "fig_very_happy": "very_happy",
}

# Material Symbols drawn for the sentiment set: image stem -> symbol name.
MATERIAL_FACES = {
    "sent_chilled": "sentiment_satisfied",
    "sent_sad": "sentiment_sad",
    "sent_angry": "sentiment_extremely_dissatisfied",
    "sent_very_happy": "sentiment_very_satisfied",
    "sent_sick": "sick",
    "sent_bored": "sentiment_neutral",
    "sent_frustrated": "sentiment_frustrated",
}
# Same width as the sun in day_clear.png, so the faces match the weather and thumbs.
FACE_WIDTH = 100
# Outlined style at weight 300 matches the line weight of the thumbs.
FACE_AXES = {"Fill": 0, "Grade": 0, "Optical Size": 48, "Weight": 300}
# The menu icon is a 2x2 grid of these faces, read left to right, top to bottom.
ICON_FACES = ["sent_chilled", "sent_very_happy", "sent_sad", "sent_angry"]
ICON_FACE_WIDTH = 11
# Small optical size and pure black: grey 1 px lines are too faint at icon size.
ICON_AXES = {"Fill": 0, "Grade": 0, "Optical Size": 20, "Weight": 400}
ICON_THRESHOLD = 150
FONT_URL = (
    "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
    "MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D"
)
FONT_CACHE = ROOT / ".cache" / "material"

# The SSD1680 driver ORs the RGB channels and keeps bits 7 and 6, so the panel
# shows four greys split at 64, 128 and 192.
LEVELS = (0, 85, 170, 255)


def quantise(value):
    return LEVELS[value >> 6]


def save_four_grey(canvas, dst):
    """Store palette indices, then attach a palette of the four panel greys."""
    indexed = canvas.point(lambda v: v >> 6).convert("P")
    indexed.putpalette([v for level in LEVELS for v in (level, level, level)])
    indexed.save(dst, optimize=True)


def convert_image(src, dst, size):
    """Fit src inside size (keeping aspect), centre it on white and save as a 4-grey PNG."""
    grey = ImageOps.autocontrast(Image.open(src).convert("L"))
    scale = min(size[0] / grey.width, size[1] / grey.height)
    fitted = grey.resize((round(grey.width * scale), round(grey.height * scale)), Image.LANCZOS)

    canvas = Image.new("L", size, 255)
    canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))

    save_four_grey(canvas, dst)


def draw_symbol(font, char, size, width):
    """Draw char in font, scale its inked area to width (keeping aspect) and centre it on white."""
    big = Image.new("L", (font.size * 2, font.size * 2), 0)
    ImageDraw.Draw(big).text((font.size, font.size), char, font=font, fill=255, anchor="mm")
    glyph = big.crop(big.getbbox())
    height = round(glyph.height * width / glyph.width)
    glyph = ImageOps.invert(glyph.resize((width, height), Image.LANCZOS))

    canvas = Image.new("L", size, 255)
    canvas.paste(glyph, ((size[0] - width) // 2, (size[1] - height) // 2))
    return canvas


def render_symbol(font, char, dst, size, width):
    save_four_grey(draw_symbol(font, char, size, width), dst)


def render_icon(font, chars, dst):
    """Save the four chars as a 2x2 grid filling ICON_SIZE."""
    cell = (ICON_SIZE[0] // 2, ICON_SIZE[1] // 2)
    canvas = Image.new("L", ICON_SIZE, 255)
    for i, char in enumerate(chars):
        canvas.paste(draw_symbol(font, char, cell, ICON_FACE_WIDTH), ((i % 2) * cell[0], (i // 2) * cell[1]))
    save_four_grey(canvas.point(lambda v: 0 if v < ICON_THRESHOLD else 255), dst)


def material_font(axes=FACE_AXES):
    """Return the Material Symbols font at axes and its name -> character map."""
    FONT_CACHE.mkdir(parents=True, exist_ok=True)
    paths = {}
    for ext in ("ttf", "codepoints"):
        path = FONT_CACHE / f"MaterialSymbolsOutlined.{ext}"
        if not path.exists():
            urllib.request.urlretrieve(f"{FONT_URL}.{ext}", path)
        paths[ext] = path
    font = ImageFont.truetype(str(paths["ttf"]), 480)
    font.set_variation_by_axes([axes[a["name"].decode()] for a in font.get_variation_axes()])
    chars = {}
    for line in paths["codepoints"].read_text().splitlines():
        name, code = line.split()
        chars[name] = chr(int(code, 16))
    return font, chars


def main():
    config = json.loads((APP_DIR / "config.json").read_text())
    assets = APP_DIR / "assets"
    assets.mkdir(exist_ok=True)

    names = sorted({image for mood_set in config["moods"] for _, image in mood_set})
    font = chars = None
    for name in names:
        stem = Path(name).stem
        if stem in MATERIAL_FACES:
            if font is None:
                font, chars = material_font()
            render_symbol(font, chars[MATERIAL_FACES[stem]], assets / name, CELL_SIZE, FACE_WIDTH)
        else:
            source = JPEG_SOURCES.get(stem, stem)
            convert_image(SOURCE_DIR / f"{source}.jpg", assets / name, CELL_SIZE)
        print(f"assets/{name}")

    icon_font, chars = material_font(ICON_AXES)
    render_icon(icon_font, [chars[MATERIAL_FACES[face]] for face in ICON_FACES], APP_DIR / "icon.png")
    print("icon.png")


if __name__ == "__main__":
    main()
