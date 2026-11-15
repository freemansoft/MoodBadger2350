# Mood navigation, config parsing and saved-state recovery.
# Pure logic with no Badgeware dependencies so it can be tested on a desktop.

import json

# The pip column on the right of the screen fits 16 pips.
MAX_MOODS = 16

PIP_X = 250
PIP_SIZE = 8
PIP_SPACING = 10
SCREEN_WIDTH = 264
SCREEN_HEIGHT = 176

# Set arrows sit along the bottom edge, above buttons A (left) and C (right).
# The x positions follow the stock Hydrate app's A and C hints.
ARROW_A_X = 43
ARROW_C_X = 210
# Midway down the strip between the picture (bottom at 138) and the screen edge.
ARROW_MID_Y = 157
ARROW_HALF = 5

# Where things go on each badge, keyed by badge.model. The Badger's numbers
# are the constants above. The Tufty (320x240 in HIRES) is a bigger Badger:
# the 122x136 picture scaled 1.5x, with the arrow x positions scaled by
# 320/264 so they sit above its A and C buttons.
BADGER = {
    "screen_w": SCREEN_WIDTH, "screen_h": SCREEN_HEIGHT,
    "image_pos": (61, 2), "image_size": (122, 136),
    "label_centre_x": 122, "label_max_width": 140,
    "arrow_a_x": ARROW_A_X, "arrow_c_x": ARROW_C_X,
    "arrow_mid_y": ARROW_MID_Y, "arrow_half": ARROW_HALF,
    "pip_x": PIP_X, "pip_size": PIP_SIZE, "pip_spacing": PIP_SPACING,
}
TUFTY = {
    "screen_w": 320, "screen_h": 240,
    "image_pos": (59, 4), "image_size": (183, 204),
    "label_centre_x": 150, "label_max_width": 170,
    "arrow_a_x": 52, "arrow_c_x": 255,
    "arrow_mid_y": 224, "arrow_half": 7,
    "pip_x": 300, "pip_size": 10, "pip_spacing": 13,
}
LAYOUTS = {"badger": BADGER, "tufty": TUFTY}

# Tufty backlight: full on any press; dimmed (never dark, so the mood stays
# visible) after DIM_AFTER_MS with no press, brighter on USB than on battery.
DIM_AFTER_MS = 10_000
BRIGHT = 1.0
DIM_USB = 0.5
DIM_BATTERY = 0.15


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


def apply_input(config, set_index, mood_index, up, down, prev_set, next_set):
    """Apply one frame of button input.

    A set change wins over up and down and opens the new set at its initial mood.
    Pressing both of a pair (up and down, or prev and next set) cancels it.
    With a single set, the set buttons do nothing.
    """
    set_step = (1 if next_set else 0) - (1 if prev_set else 0)
    if set_step and len(config["moods"]) > 1:
        new_set = (set_index + set_step) % len(config["moods"])
        return new_set, config["initial"][new_set]

    step = (1 if down else 0) - (1 if up else 0)
    count = len(config["moods"][set_index])
    return set_index, (mood_index + step) % count


def set_arrows(set_count, layout=BADGER):
    """Triangles hinting at the set buttons, as lists of (x, y); none for a single set."""
    if set_count < 2:
        return []
    a, c, mid, half = layout["arrow_a_x"], layout["arrow_c_x"], layout["arrow_mid_y"], layout["arrow_half"]
    top, bottom = mid - half, mid + half
    left = [(a - half, mid), (a + half, top), (a + half, bottom)]
    right = [(c + half, mid), (c - half, top), (c - half, bottom)]
    return [left, right]


def pip_positions(count, layout=BADGER):
    """Top-left corners of the pips for a set of count moods, centred vertically."""
    spacing = layout["pip_spacing"]
    top = (layout["screen_h"] - count * spacing) // 2
    return [(layout["pip_x"], top + i * spacing) for i in range(count)]


def backlight_level(idle_ms, on_usb):
    """Tufty backlight level after idle_ms with no button press."""
    if idle_ms < DIM_AFTER_MS:
        return BRIGHT
    return DIM_USB if on_usb else DIM_BATTERY
