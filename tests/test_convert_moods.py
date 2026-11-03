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
