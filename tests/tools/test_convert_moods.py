import json
from pathlib import Path

import pytest
from PIL import Image, ImageOps

from tools.convert_moods import convert_image, quantise

CELL = (122, 136)


@pytest.mark.parametrize("value,expected", [
    (63, 0), (64, 85), (127, 85), (128, 170), (191, 170), (192, 255),
])
def test_quantise_matches_firmware_bit_planes(value, expected):
    assert quantise(value) == expected


def test_output_has_cell_size_and_only_four_levels(tmp_path):
    src, dst = tmp_path / "gradient.jpg", tmp_path / "gradient.png"
    gradient = Image.new("RGB", (100, 100))
    for x in range(100):
        for y in range(100):
            v = x * 255 // 99
            gradient.putpixel((x, y), (v, v, v))
    gradient.save(src)

    convert_image(src, dst, CELL)

    out = Image.open(dst)
    assert out.size == CELL and out.mode == "P"
    assert {v for _, v in out.convert("L").getcolors()} <= {0, 85, 170, 255}


def test_square_source_keeps_aspect_and_is_centred(tmp_path):
    src, dst = tmp_path / "square.jpg", tmp_path / "square.png"
    Image.new("RGB", (100, 100), (0, 0, 0)).save(src)

    convert_image(src, dst, CELL)

    assert ImageOps.invert(Image.open(dst).convert("L")).getbbox() == (0, 7, 122, 129)


def test_symbol_is_drawn_at_the_requested_width_centred_in_four_greys(tmp_path):
    from PIL import ImageFont
    from tools.convert_moods import render_symbol

    dst = tmp_path / "o.png"
    render_symbol(ImageFont.load_default(200), "O", dst, CELL, 100)

    out = Image.open(dst)
    assert out.size == CELL and out.mode == "P"
    assert {v for _, v in out.convert("L").getcolors()} <= {0, 85, 170, 255}
    left, top, right, bottom = ImageOps.invert(out.convert("L")).getbbox()
    assert right - left in (99, 100, 101)
    assert abs((left + right) - CELL[0]) <= 1 and abs((top + bottom) - CELL[1]) <= 1


def test_every_configured_photo_has_its_moodbadger_jpeg():
    # main() draws the Material faces and converts every other configured
    # image from vendor/MoodBadger/moods/<stem>.jpg (renamed by JPEG_SOURCES).
    from tools.convert_moods import APP_DIR, JPEG_SOURCES, MATERIAL_FACES, SOURCE_DIR

    config = json.loads((APP_DIR / "config.json").read_text())
    stems = {Path(image).stem for mood_set in config["moods"] for _, image in mood_set} - set(MATERIAL_FACES)
    assert stems
    for stem in sorted(stems):
        assert (SOURCE_DIR / f"{JPEG_SOURCES.get(stem, stem)}.jpg").exists(), stem


def test_icon_is_a_two_by_two_grid_of_symbols(tmp_path):
    from PIL import ImageFont
    from tools.convert_moods import render_icon

    dst = tmp_path / "icon.png"
    render_icon(ImageFont.load_default(200), ["O", "O", "O", "O"], dst)

    out = ImageOps.invert(Image.open(dst).convert("L"))
    assert out.size == (24, 24)
    # pure black and white: grey 1 px lines are too faint at icon size
    assert {v for _, v in out.getcolors()} <= {0, 255}
    for box in ((0, 0, 12, 12), (12, 0, 24, 12), (0, 12, 12, 24), (12, 12, 24, 24)):
        assert out.crop(box).getbbox() is not None, box


def test_icon_uses_four_sent_faces():
    from tools.convert_moods import ICON_FACES, MATERIAL_FACES

    # A 2x2 grid, drawn from the faces' Material symbols.
    assert len(ICON_FACES) == 4 and set(ICON_FACES) <= set(MATERIAL_FACES)
