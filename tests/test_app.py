import pytest

from fake_badgeware import (
    BUTTON_A, BUTTON_B, BUTTON_C, BUTTON_DOWN, BUTTON_HOME, NON_BLOCKING, TEXT_HEIGHT, run_app,
)

import moods


def test_first_tick_draws_saved_mood_once():
    r = run_app([set()], saved={"set": 0, "mood": 2})
    assert r.events.count("display") == 1
    assert r.blits == ["assets/bored.png"]
    assert ("Bored", "ziplock") in r.texts


def test_framebuffer_cleared_before_drawing():
    r = run_app([set()])
    assert r.events.index("clear") < r.events.index("blit")


def test_no_press_after_first_draw_does_not_refresh():
    assert run_app([set(), set(), set()]).events.count("display") == 1


def test_wake_press_moves_one_mood():
    # After a wake, the waking press is already in `pressed` on the first tick.
    r = run_app([{BUTTON_DOWN}], saved={"set": 0, "mood": 0})
    assert r.saved == {"set": 0, "mood": 1}
    assert r.blits == ["assets/sad.png"]
    assert r.events.count("display") == 1


def test_state_saved_before_display_refresh():
    r = run_app([set(), {BUTTON_DOWN}])
    second_display = r.events.index("display", r.events.index("display") + 1)
    assert r.events.index("save") < second_display


def test_c_moves_to_next_set():
    r = run_app([set(), {BUTTON_C}], saved={"set": 0, "mood": 3})
    assert r.saved == {"set": 1, "mood": 0}
    assert r.blits[-1] == "assets/thumb_up.png"


def test_a_moves_to_previous_set_wrapping_to_the_last():
    r = run_app([set(), {BUTTON_A}], saved={"set": 0, "mood": 3})
    assert r.saved == {"set": 2, "mood": 0}
    assert r.blits[-1] == "assets/day_clear.png"


@pytest.mark.parametrize("button", [BUTTON_B, BUTTON_HOME])
def test_unmapped_buttons_do_not_refresh(button):
    r = run_app([set(), {button}])
    assert r.events.count("display") == 1
    assert r.saved is None


def test_press_during_refresh_is_not_dropped():
    r = run_app([set(), {BUTTON_DOWN}, {BUTTON_DOWN}], saved={"set": 0, "mood": 0})
    assert r.mode & NON_BLOCKING
    assert r.saved == {"set": 0, "mood": 2}


def test_press_caught_by_display_update_is_not_lost():
    # A press held as the refresh finishes is seen by badge.update()'s own poll;
    # waiting would poll again and drop it.
    r = run_app([set()], saved={"set": 0, "mood": 0}, update_polls=[{BUTTON_DOWN}])
    assert r.saved == {"set": 0, "mood": 1}
    assert r.blits == ["assets/happy.png", "assets/sad.png"]


def test_stale_state_recovers():
    assert run_app([set()], saved={"set": 9, "mood": 9}).blits == ["assets/happy.png"]


def test_app_never_polls_before_run():
    assert run_app([set()]).early_calls == []


def test_each_update_waits_with_sleep_timeout():
    assert run_app([set(), set()]).waits == [5000, 5000]


def test_missing_image_still_draws_label():
    r = run_app([set()], saved={"set": 0, "mood": 0}, files_missing=("assets/happy.png",))
    assert r.blits == []
    assert ("Chilled", "ziplock") in r.texts


def test_undecodable_image_still_draws_label_and_keeps_working():
    # The saved mood is redrawn on every launch, so a crash here would loop forever.
    r = run_app([set(), {BUTTON_DOWN}], saved={"set": 0, "mood": 0}, files_corrupt=("assets/happy.png",))
    assert r.fatal is None
    assert ("Chilled", "ziplock") in r.texts
    assert r.blits == ["assets/sad.png"]


def test_bad_config_reports_error():
    assert "config.json" in run_app([set()], config_text="not json").fatal


def test_invalid_config_structure_reports_error():
    assert "config.json" in run_app([set()], config_text='{"moods": [[]]}').fatal


def test_missing_config_reports_error():
    assert "config.json" in run_app([set()], files_missing=("config.json",)).fatal


def label_font(label):
    # two sets, so the arrows are shown and the label must fit between them
    r = run_app([set()], config_text='{"moods": [[["' + label + '", "happy.png"]], [["x", "sad.png"]]]}')
    return r.texts[0][1]


def test_label_uses_ziplock_font():
    assert run_app([set()]).texts == [("Chilled", "ziplock")]


def test_label_that_fits_between_the_arrows_keeps_ziplock():
    # 15 characters of Ziplock (9 px each in the fake) is 135 px, inside the 140 px gap
    assert label_font("W" * 15) == "ziplock"


def test_label_too_wide_for_ziplock_steps_down_to_smart():
    # 16 characters: 144 px of Ziplock is too wide, 112 px of Smart fits
    assert label_font("W" * 16) == "smart"


def test_label_too_wide_for_smart_steps_down_to_winds():
    # 21 characters: 147 px of Smart is too wide
    assert label_font("W" * 21) == "winds"


def test_label_is_vertically_centred_on_the_arrows():
    assert run_app([set()]).text_y == [moods.ARROW_MID_Y - TEXT_HEIGHT / 2]


def test_set_arrows_drawn_above_a_and_c_with_several_sets():
    assert run_app([set()]).arrows == moods.set_arrows(3)


def test_no_set_arrows_with_a_single_set():
    assert run_app([set()], config_text='{"moods": [[["Chilled", "happy.png"]]]}').arrows == []
