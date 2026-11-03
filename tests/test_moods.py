import json

import pytest

from moods import MAX_MOODS, SCREEN_HEIGHT, SCREEN_WIDTH, apply_input, parse_config, pip_positions, restore, set_arrows

CFG = {
    "moods": [
        [["A", "a.png"], ["B", "b.png"], ["C", "c.png"]],
        [["D", "d.png"], ["E", "e.png"]],
    ],
    "initial": [0, 1],
}


def test_down_advances_and_wraps():
    assert apply_input(CFG, 0, 0, False, True, False, False) == (0, 1)
    assert apply_input(CFG, 0, 2, False, True, False, False) == (0, 0)


def test_up_goes_back_and_wraps():
    assert apply_input(CFG, 0, 0, True, False, False, False) == (0, 2)


def test_no_input_keeps_position():
    assert apply_input(CFG, 1, 1, False, False, False, False) == (1, 1)


def test_up_and_down_together_cancel():
    assert apply_input(CFG, 0, 1, True, True, False, False) == (0, 1)


def test_next_set_moves_to_next_set_at_its_initial_mood_and_wraps():
    assert apply_input(CFG, 0, 2, False, False, False, True) == (1, 1)
    assert apply_input(CFG, 1, 0, False, False, False, True) == (0, 0)


def test_prev_set_moves_to_previous_set_at_its_initial_mood_and_wraps():
    assert apply_input(CFG, 1, 0, False, False, True, False) == (0, 0)
    assert apply_input(CFG, 0, 2, False, False, True, False) == (1, 1)


def test_set_change_beats_up_and_down():
    assert apply_input(CFG, 0, 0, True, True, False, True) == (1, 1)


def test_prev_and_next_set_together_cancel():
    assert apply_input(CFG, 0, 2, False, False, True, True) == (0, 2)


def test_single_set_change_returns_to_initial():
    single = {"moods": [CFG["moods"][0]], "initial": [2]}
    assert apply_input(single, 0, 0, False, False, False, True) == (0, 2)
    assert apply_input(single, 0, 0, False, False, True, False) == (0, 2)


def test_set_arrows_hidden_with_one_set():
    assert set_arrows(1) == []


def test_set_arrows_point_left_above_a_and_right_above_c():
    left, right = set_arrows(3)
    assert len(left) == len(right) == 3
    # the tip is the point furthest out: left for A, right for C
    assert min(left) == (38, 167)
    assert max(right) == (215, 167)


def test_set_arrows_stay_on_screen_and_clear_of_the_pips():
    for x, y in [p for arrow in set_arrows(2) for p in arrow]:
        assert 0 <= x < 250 and 0 <= y < SCREEN_HEIGHT
    assert SCREEN_WIDTH == 264


def test_restore_uses_saved_position():
    assert restore(CFG, {"set": 1, "mood": 0}) == (1, 0)


def test_restore_out_of_range_mood_falls_back_to_set_initial():
    assert restore(CFG, {"set": 1, "mood": 9}) == (1, 1)


def test_restore_out_of_range_set_falls_back_to_first_set():
    assert restore(CFG, {"set": 7, "mood": 0}) == (0, 0)


def test_restore_negative_values_fall_back():
    assert restore(CFG, {"set": -1, "mood": -1}) == (0, 0)


def test_restore_non_integer_values_fall_back():
    assert restore(CFG, {"set": "x", "mood": None}) == (0, 0)


def test_restore_empty_state_uses_first_set_initial():
    assert restore(CFG, {}) == (0, 0)


def test_parse_returns_moods_and_initial():
    assert parse_config(json.dumps(CFG)) == CFG


def test_parse_defaults_missing_initial_to_zero():
    text = '{"moods": [[["A", "a.png"]], [["B", "b.png"]]]}'
    assert parse_config(text)["initial"] == [0, 0]


def test_parse_replaces_out_of_range_initial_with_zero():
    text = '{"moods": [[["A", "a.png"]], [["B", "b.png"]]], "initial": [5, -1]}'
    assert parse_config(text)["initial"] == [0, 0]


def test_parse_fills_short_initial_with_zero():
    text = '{"moods": [[["A", "a.png"], ["B", "b.png"]], [["C", "c.png"]]], "initial": [1]}'
    assert parse_config(text)["initial"] == [1, 0]


@pytest.mark.parametrize("text", [
    "not json",
    "[]",
    "{}",
    '{"moods": []}',
    '{"moods": [[]]}',
    '{"moods": [[["only label"]]]}',
    '{"moods": [[["", "a.png"]]]}',
    '{"moods": [[[1, "a.png"]]]}',
    '{"moods": [[["A", ""]]]}',
])
def test_parse_rejects_bad_config(text):
    with pytest.raises(ValueError):
        parse_config(text)


def test_parse_rejects_set_with_too_many_moods():
    mood_set = [["M%d" % i, "m.png"] for i in range(MAX_MOODS + 1)]
    with pytest.raises(ValueError):
        parse_config(json.dumps({"moods": [mood_set]}))


def test_parse_accepts_set_at_maximum():
    mood_set = [["M%d" % i, "m.png"] for i in range(MAX_MOODS)]
    assert len(parse_config(json.dumps({"moods": [mood_set]}))["moods"][0]) == MAX_MOODS


def test_pip_positions_are_centred_for_eight():
    assert pip_positions(8) == [(250, 48 + i * 10) for i in range(8)]


def test_pip_positions_stay_on_screen_at_maximum():
    assert all(0 <= y and y + 8 <= 176 for _, y in pip_positions(MAX_MOODS))
