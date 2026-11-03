# Mood navigation, config parsing and saved-state recovery.
# Pure logic with no Badgeware dependencies so it can be tested on a desktop.

import json

# The pip column on the right of the screen fits 16 pips.
MAX_MOODS = 16

PIP_X = 250
PIP_SIZE = 8
PIP_SPACING = 10
SCREEN_HEIGHT = 176


def _is_text(value):
    return type(value) is str and value != ""


def parse_config(text):
    """Return {"moods": [...], "initial": [...]} or raise ValueError."""
    try:
        data = json.loads(text)
    except ValueError:
        raise ValueError("config.json is not valid JSON") from None

    if type(data) is not dict:
        raise ValueError("config.json must be a JSON object")

    mood_sets = data.get("moods")
    if type(mood_sets) is not list or not mood_sets:
        raise ValueError('config.json needs a non-empty "moods" list')

    for set_number, mood_set in enumerate(mood_sets):
        if type(mood_set) is not list or not mood_set:
            raise ValueError("mood set {} is empty".format(set_number))
        if len(mood_set) > MAX_MOODS:
            raise ValueError("mood set {} has more than {} moods".format(set_number, MAX_MOODS))
        for mood in mood_set:
            if type(mood) is not list or len(mood) != 2 or not _is_text(mood[0]) or not _is_text(mood[1]):
                raise ValueError("mood set {} has an entry that is not [label, image]".format(set_number))

    # "initial" is optional; missing or out-of-range entries fall back to the first mood.
    given = data.get("initial")
    if type(given) is not list:
        given = []
    initial = []
    for set_number, mood_set in enumerate(mood_sets):
        value = given[set_number] if set_number < len(given) else 0
        initial.append(value if type(value) is int and 0 <= value < len(mood_set) else 0)

    return {"moods": mood_sets, "initial": initial}


def restore(config, saved):
    """Turn saved state into a valid (set_index, mood_index) for this config."""
    mood_sets = config["moods"]
    set_index = saved.get("set")
    if type(set_index) is not int or not 0 <= set_index < len(mood_sets):
        return 0, config["initial"][0]

    mood_index = saved.get("mood")
    if type(mood_index) is not int or not 0 <= mood_index < len(mood_sets[set_index]):
        return set_index, config["initial"][set_index]

    return set_index, mood_index


def apply_input(config, set_index, mood_index, up, down, cycle):
    """Apply one frame of button input. Cycle wins; up and down together cancel."""
    if cycle:
        next_set = (set_index + 1) % len(config["moods"])
        return next_set, config["initial"][next_set]

    step = (1 if down else 0) - (1 if up else 0)
    count = len(config["moods"][set_index])
    return set_index, (mood_index + step) % count


def pip_positions(count):
    """Top-left corners of the pips for a set of count moods, centred vertically."""
    top = (SCREEN_HEIGHT - count * PIP_SPACING) // 2
    return [(PIP_X, top + i * PIP_SPACING) for i in range(count)]
