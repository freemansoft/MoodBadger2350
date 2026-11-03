import json
from pathlib import Path

from PIL import Image

APP_DIR = Path(__file__).resolve().parent.parent / "badger" / "mood_badger"


def configured_images():
    config = json.loads((APP_DIR / "config.json").read_text())
    return sorted({image for mood_set in config["moods"] for _, image in mood_set})


def test_every_configured_image_exists_at_cell_size():
    images = configured_images()
    assert len(images) == 14
    for name in images:
        image = Image.open(APP_DIR / "assets" / name)
        assert (name, image.size, image.mode) == (name, (122, 136), "P")


def test_icon_is_24_by_24():
    assert Image.open(APP_DIR / "icon.png").size == (24, 24)
