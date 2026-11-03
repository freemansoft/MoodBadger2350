import json
from pathlib import Path

from PIL import Image

APP_DIR = Path(__file__).resolve().parent.parent / "badger" / "mood_badger"


def configured_images():
    config = json.loads((APP_DIR / "config.json").read_text())
    return sorted({image for mood_set in config["moods"] for _, image in mood_set})


def test_every_configured_image_exists_at_cell_size():
    images = configured_images()
    assert len(images) == 21
    for name in images:
        image = Image.open(APP_DIR / "assets" / name)
        assert (name, image.size, image.mode) == (name, (122, 136), "P")


def test_icon_is_24_by_24():
    assert Image.open(APP_DIR / "icon.png").size == (24, 24)


def test_material_face_set_has_the_seven_moods_in_order():
    config = json.loads((APP_DIR / "config.json").read_text())
    assert config["moods"][0] == [
        ["Chilled", "sent_chilled.png"], ["Sad", "sent_sad.png"], ["Angry", "sent_angry.png"],
        ["Very Happy", "sent_very_happy.png"], ["Sick", "sent_sick.png"],
        ["Bored", "sent_bored.png"], ["Frustrated", "sent_frustrated.png"],
    ]
    assert len(config["initial"]) == 4


def test_lego_figure_set_uses_fig_names():
    config = json.loads((APP_DIR / "config.json").read_text())
    assert [image for _, image in config["moods"][1]] == [
        "fig_chilled.png", "fig_sad.png", "fig_bored.png", "fig_annoyed.png",
        "fig_angry.png", "fig_embarrassed.png", "fig_surprised.png", "fig_very_happy.png",
    ]


def test_each_set_shares_one_file_prefix_of_its_own():
    config = json.loads((APP_DIR / "config.json").read_text())
    prefixes = []
    for mood_set in config["moods"]:
        set_prefixes = {image.split("_")[0] for _, image in mood_set}
        assert len(set_prefixes) == 1, set_prefixes
        prefixes += set_prefixes
    assert prefixes == ["sent", "fig", "thumb", "day"]
