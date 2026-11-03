import pytest

from fake_badgeware import (
    BUTTON_A, BUTTON_B, BUTTON_C, BUTTON_DOWN, BUTTON_HOME, NON_BLOCKING, run_app,
)


def test_first_tick_draws_saved_mood_once():
    r = run_app([set()], saved={"set": 0, "mood": 2})
    assert r.events.count("display") == 1
    assert r.blits == ["assets/bored.png"]
    assert ("Bored", "ignore") in r.texts


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


def test_b_cycles_set():
    r = run_app([set(), {BUTTON_B}], saved={"set": 0, "mood": 3})
    assert r.saved == {"set": 1, "mood": 0}
    assert r.blits[-1] == "assets/thumb_up.png"


@pytest.mark.parametrize("button", [BUTTON_A, BUTTON_C, BUTTON_HOME])
def test_unmapped_buttons_do_not_refresh(button):
    r = run_app([set(), {button}])
    assert r.events.count("display") == 1
    assert r.saved is None


def test_press_during_refresh_is_not_dropped():
    r = run_app([set(), {BUTTON_DOWN}, {BUTTON_DOWN}], saved={"set": 0, "mood": 0})
    assert r.mode & NON_BLOCKING
    assert r.saved == {"set": 0, "mood": 2}


def test_stale_state_recovers():
    assert run_app([set()], saved={"set": 9, "mood": 9}).blits == ["assets/happy.png"]


def test_app_never_polls_before_run():
    assert run_app([set()]).early_calls == []


def test_each_update_waits_with_sleep_timeout():
    assert run_app([set(), set()]).waits == [5000, 5000]


def test_missing_image_still_draws_label():
    r = run_app([set()], saved={"set": 0, "mood": 0}, files_missing=("assets/happy.png",))
    assert r.blits == []
    assert ("Chilled", "ignore") in r.texts


def test_bad_config_reports_error():
    assert "config.json" in run_app([set()], config_text="not json").fatal


def test_invalid_config_structure_reports_error():
    assert "config.json" in run_app([set()], config_text='{"moods": [[]]}').fatal


def test_missing_config_reports_error():
    assert "config.json" in run_app([set()], files_missing=("config.json",)).fatal


def test_long_label_uses_smaller_font():
    r = run_app([set()], config_text='{"moods": [[["' + "W" * 25 + '", "happy.png"]]]}')
    assert r.texts[0][1] == "smart"
