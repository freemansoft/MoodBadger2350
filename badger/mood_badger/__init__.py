# Mood Badger: show how you feel on a Badger 2350.
#
# UP and DOWN step through the moods, B cycles between mood sets.
# The menu's launch() has already made this folder the working directory.
#
# Badger restarts this file from the top every time it wakes, and the waking
# button press is only reported by the first poll inside run(). So nothing
# here may call badge.poll() or badge.update() before run(update).

import moods

SLEEP_AFTER_MS = 5000

IMAGE_POS = (61, 2)
LABEL_CENTRE_X = 122
LABEL_TOP = 142
LABEL_MAX_WIDTH = 236
LARGE_FONT = font.ignore
SMALL_FONT = font.smart

try:
    with open("config.json") as f:
        config = moods.parse_config(f.read())
except (OSError, ValueError) as e:
    fatal_error("Mood Badger", "Problem with config.json: {}".format(e))

state = {"set": 0, "mood": config["initial"][0]}
State.load("mood_badger", state)
state["set"], state["mood"] = moods.restore(config, state)

# MEDIUM_UPDATE matches the gallery app; firmware v3.1.1 ignores the speed.
# NON_BLOCKING keeps polling buttons while the e-paper refreshes.
badge.mode(MEDIUM_UPDATE | NON_BLOCKING)


def draw(mood_set, mood_index):
    label, image_name = mood_set[mood_index]

    # The framebuffer holds garbage after a wake, so always start from white.
    screen.pen = color.white
    screen.clear()

    path = "assets/" + image_name
    if file_exists(path):
        screen.blit(image.load(path), vec2(*IMAGE_POS))

    screen.pen = color.black
    screen.font = LARGE_FONT
    width, _ = screen.measure_text(label)
    if width > LABEL_MAX_WIDTH:
        screen.font = SMALL_FONT
        width, _ = screen.measure_text(label)
    screen.text(label, LABEL_CENTRE_X - width / 2, LABEL_TOP)

    # one pip per mood in this set, filled for the current one
    for i, (x, y) in enumerate(moods.pip_positions(len(mood_set))):
        pip = shape.rectangle(x, y, moods.PIP_SIZE, moods.PIP_SIZE)
        screen.shape(pip if i == mood_index else pip.stroke(1))


def update():
    set_index, mood_index = moods.apply_input(
        config, state["set"], state["mood"],
        badge.pressed(BUTTON_UP), badge.pressed(BUTTON_DOWN), badge.pressed(BUTTON_B),
    )
    changed = (set_index, mood_index) != (state["set"], state["mood"])

    # Save before refreshing so a sleep or power loss mid-refresh keeps the choice.
    if changed:
        state["set"], state["mood"] = set_index, mood_index
        State.save("mood_badger", state)

    if changed or badge.first_update:
        draw(config["moods"][set_index], mood_index)
        badge.update()
        # badge.update() polls the buttons as it finishes. Waiting would poll
        # again and lose a press made during the refresh, so handle it now.
        if badge.pressed():
            return

    # Sleeps after SLEEP_AFTER_MS on battery; any front button wakes the badge.
    wait_for_button_or_alarm(timeout=SLEEP_AFTER_MS)


run(update)
