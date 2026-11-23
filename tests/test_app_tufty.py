"""Mood Badger on the Tufty 2350: a bigger Badger with a dimming backlight."""

from fake_badgeware import BUTTON_A, BUTTON_C, BUTTON_DOWN, BUTTON_UP, CHAR_WIDTH, HIRES, VSYNC, run_app

import moods

T = {"model": "tufty"}
IDLE = [set()] * 11          # 11 frames of 1000 ms: past DIM_AFTER_MS


def test_tufty_uses_hires_and_never_badger_only_names():
    r = run_app([set()], **T)          # NameError on NON_BLOCKING etc. would surface as r.fatal
    assert r.fatal is None and r.mode == HIRES | VSYNC


def test_tufty_redraws_every_frame_on_white():
    r = run_app([set()] * 3, **T)
    assert r.events.count("blit") == 3 and r.events.count("display") == 3


def test_tufty_scales_picture_into_layout_rect():
    r = run_app([set()], saved={"set": 0, "mood": 2}, **T)
    assert r.blits == ["assets/sent_angry.png"]
    assert r.blit_rects == [(*moods.TUFTY["image_pos"], *moods.TUFTY["image_size"])]


def test_tufty_loads_each_picture_once():
    assert run_app([set()] * 5, **T).loads == 1


def test_tufty_first_frame_press_only_wakes():
    r = run_app([{BUTTON_DOWN}], saved={"set": 0, "mood": 0}, **T)
    assert r.saved is None and r.blits[-1] == "assets/sent_chilled.png"


def test_tufty_press_while_bright_moves_mood_and_saves_before_drawing():
    r = run_app([set(), {BUTTON_DOWN}], saved={"set": 0, "mood": 0}, **T)
    assert r.saved == {"set": 0, "mood": 1}
    last_blit = len(r.events) - 1 - r.events[::-1].index("blit")
    assert r.events.index("save") < last_blit and r.blits[-1] == "assets/sent_sad.png"


def test_tufty_full_brightness_then_dims_on_battery():
    r = run_app([set()] + IDLE, usb=False, **T)
    assert r.backlight == [1.0, 0.15]


def test_tufty_dims_to_half_on_usb():
    assert run_app([set()] + IDLE, usb=True, **T).backlight == [1.0, 0.5]


def test_tufty_dim_level_follows_power_source_without_a_press():
    r = run_app([set()] + IDLE + [set()], usb=[True] * 12 + [False], **T)
    assert r.backlight == [1.0, 0.5, 0.15]


def test_tufty_any_press_while_dimmed_only_wakes():
    for press in ({BUTTON_DOWN}, {BUTTON_UP, BUTTON_DOWN}, {BUTTON_A, BUTTON_C}):
        r = run_app([set()] + IDLE + [press], usb=False, saved={"set": 0, "mood": 0}, **T)
        assert r.saved is None and r.backlight == [1.0, 0.15, 1.0]


def test_tufty_second_press_after_wake_changes_mood():
    r = run_app([set()] + IDLE + [{BUTTON_DOWN}, {BUTTON_DOWN}], usb=False, saved={"set": 0, "mood": 0}, **T)
    assert r.saved == {"set": 0, "mood": 1}


def test_tufty_c_changes_set_when_bright():
    r = run_app([set(), {BUTTON_C}], **T)
    assert r.saved["set"] == 1


def test_tufty_never_sleeps():
    r = run_app([set()] + IDLE * 3, usb=False, **T)
    assert "sleep" not in r.events and r.waits == []


def test_tufty_bad_image_draws_label_and_loads_once():
    r = run_app([set()] * 4, files_corrupt=("sent_chilled.png",), **T)
    assert r.fatal is None and r.loads == 1 and r.texts.count(("Chilled", "ignore")) == 4


def test_tufty_on_exit_restores_full_brightness():
    r = run_app([set()] + IDLE, usb=False, **T)
    r.exit()
    assert r.backlight[-1] == 1.0


def test_tufty_long_label_steps_down_to_fit_its_wider_space():
    # 15 chars: 180 px in ignore (> 170), 135 px in ziplock (fits)
    config = '{"moods": [[["Very Frustrated", "sent_sad.png"]]]}'
    r = run_app([set()], config_text=config, **T)
    assert r.texts == [("Very Frustrated", "ziplock")]
    assert len("Very Frustrated") * CHAR_WIDTH["ziplock"] <= moods.TUFTY["label_max_width"]


def test_tufty_label_that_fits_170_but_not_140_keeps_ignore():
    # 13 chars: 156 px in ignore, too wide on the Badger, fits on the Tufty
    config = '{"moods": [[["Overwhelmed!!", "sent_sad.png"]]]}'
    assert run_app([set()], config_text=config, **T).texts == [("Overwhelmed!!", "ignore")]


def test_tufty_draws_in_pure_black_and_white_like_the_pictures():
    # On the Tufty, picovector's color.white and color.black are an off-white
    # and a dark navy; the mood pictures are pure black and white.
    r = run_app([set()] * 2, **T)
    assert r.clear_pens == [(255, 255, 255)] * 2
    assert r.text_pens == [(0, 0, 0)] * 2


def test_tufty_picture_that_fails_to_draw_still_shows_the_label():
    # A crash here would repeat on every launch, because this mood is saved.
    r = run_app([set()] * 2, blit_fails=("sent_chilled.png",), **T)
    assert r.fatal is None and ("Chilled", "ignore") in r.texts
