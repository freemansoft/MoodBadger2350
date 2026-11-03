import pytest
from PIL import Image, ImageOps

from tools.convert_moods import convert_image, quantise

CELL = (122, 136)


@pytest.mark.parametrize("value,expected", [
    (0, 0), (63, 0), (64, 85), (127, 85), (128, 170), (191, 170), (192, 255), (255, 255),
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


def test_material_faces_name_real_symbols():
    from tools.convert_moods import MATERIAL_FACES

    assert MATERIAL_FACES == {
        "sent_chilled": "sentiment_satisfied",
        "sent_sad": "sentiment_sad",
        "sent_angry": "sentiment_extremely_dissatisfied",
        "sent_very_happy": "sentiment_very_satisfied",
        "sent_sick": "sick",
        "sent_bored": "sentiment_neutral",
        "sent_frustrated": "sentiment_frustrated",
    }


def test_lego_figures_come_from_moodbadgers_jpegs():
    from tools.convert_moods import JPEG_SOURCES, SOURCE_DIR

    assert JPEG_SOURCES["fig_chilled"] == "happy"
    assert JPEG_SOURCES["fig_embarrassed"] == "embarassed"
    for stem in JPEG_SOURCES.values():
        assert (SOURCE_DIR / f"{stem}.jpg").exists(), stem


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

    assert ICON_FACES == ["sent_chilled", "sent_very_happy", "sent_sad", "sent_angry"]
    assert set(ICON_FACES) <= set(MATERIAL_FACES)
