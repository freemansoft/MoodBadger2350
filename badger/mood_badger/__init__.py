# Mood Badger: show how you feel on a Badger 2350 or Tufty 2350.
#
# UP and DOWN step through the moods; A and C go to the previous and next set.
# The menu's launch() has already made this folder the working directory.
#
# Badger restarts this file from the top every time it wakes, and the waking
# button press is only reported by the first poll inside run(). So nothing
# here may call badge.poll() or badge.update() before run(update).
#
# The two badges differ in ways that matter here (see the badgeware-platforms
# skill): the Badger's e-ink keeps its picture, so it draws only on a change
# and then sleeps; the Tufty's run() clears the screen before every frame, so
# it draws every frame, and dims its backlight instead of sleeping.

import moods

SLEEP_AFTER_MS = 5000

# Largest first; a label uses the first font it fits in, or the last one.
LABEL_FONTS = (font.ignore, font.ziplock, font.smart, font.winds)

try:
    with open("config.json") as f:
        config = moods.parse_config(f.read())
except (OSError, ValueError) as e:
    fatal_error("Mood Badger", "Problem with config.json: {}".format(e))

state = {"set": 0, "mood": config["initial"][0]}
State.load("mood_badger", state)
state["set"], state["mood"] = moods.restore(config, state)

TUFTY = badge.model == "tufty"
layout = moods.TUFTY if TUFTY else moods.BADGER

# The pictures are pure black and white. On the Tufty, color.white and
# color.black are an off-white and a dark navy, which would box them in.
PAPER = color.rgb(255, 255, 255) if TUFTY else color.white
INK = color.rgb(0, 0, 0) if TUFTY else color.black


def on_exit():
    # HOME: never leave the Tufty's menu at the dim level.
    if TUFTY:
        display.backlight(moods.BRIGHT)


def draw_label_and_marks(mood_set, mood_index):
    label = mood_set[mood_index][0]

    screen.pen = INK
    for label_font in LABEL_FONTS:
        screen.font = label_font
        width, height = screen.measure_text(label)
        if width <= layout["label_max_width"]:
            break
    screen.text(label, layout["label_centre_x"] - width / 2, layout["arrow_mid_y"] - height / 2)

    # A and C change set; the arrows above them say so. Hidden with only one set.
    for arrow in moods.set_arrows(len(config["moods"]), layout):
        screen.shape(shape.custom([vec2(x, y) for x, y in arrow]))

    # one pip per mood in this set, filled for the current one
    size = layout["pip_size"]
    for i, (x, y) in enumerate(moods.pip_positions(len(mood_set), layout)):
        pip = shape.rectangle(x, y, size, size)
        screen.shape(pip if i == mood_index else pip.stroke(1))


def load_picture(image_name):
    # A missing or undecodable image still shows the label. Crashing here
    # would repeat on every launch, because this mood is already saved.
    path = "assets/" + image_name
    if file_exists(path):
        try:
            return image.load(path)
        except Exception:  # noqa: BLE001
            pass
    return None


# --- Badger 2350: e-ink, draw on change, sleep on battery --------------------

def draw(mood_set, mood_index):
    # The framebuffer holds garbage after a wake, so always start from white.
    screen.pen = PAPER
    screen.clear()

    picture = load_picture(mood_set[mood_index][1])
    if picture is not None:
        screen.blit(picture, vec2(*layout["image_pos"]))

    draw_label_and_marks(mood_set, mood_index)


def update():
    set_index, mood_index = moods.apply_input(
        config, state["set"], state["mood"],
        badge.pressed(BUTTON_UP), badge.pressed(BUTTON_DOWN),
        badge.pressed(BUTTON_A), badge.pressed(BUTTON_C),
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


# --- Tufty 2350: LCD, draw every frame, dim the backlight --------------------

# last_press: badge.ticks of the last press, None before the first frame.
# level: the backlight level last set. picture: (image name, decoded image or
# None), so a picture is decoded once, and a broken one isn't retried every
# frame, until the mood changes.
tufty = {"last_press": None, "level": None, "picture": (None, None)}


def update_tufty():
    now = badge.ticks
    on_usb = badge.usb_connected()

    if tufty["last_press"] is None:
        # First frame: the press that woke the badge only wakes it.
        tufty["last_press"] = now
    elif badge.pressed():
        dimmed = moods.backlight_level(now - tufty["last_press"], on_usb) < moods.BRIGHT
        tufty["last_press"] = now
        # A press on a dimmed screen only brightens it, so the child sees
        # the current mood before changing it.
        if not dimmed:
            set_index, mood_index = moods.apply_input(
                config, state["set"], state["mood"],
                badge.pressed(BUTTON_UP), badge.pressed(BUTTON_DOWN),
                badge.pressed(BUTTON_A), badge.pressed(BUTTON_C),
            )
            if (set_index, mood_index) != (state["set"], state["mood"]):
                state["set"], state["mood"] = set_index, mood_index
                State.save("mood_badger", state)

    level = moods.backlight_level(now - tufty["last_press"], on_usb)
    if level != tufty["level"]:
        display.backlight(level)
        tufty["level"] = level

    mood_set = config["moods"][state["set"]]
    image_name = mood_set[state["mood"]][1]
    if tufty["picture"][0] != image_name:
        tufty["picture"] = (image_name, load_picture(image_name))

    screen.pen = PAPER
    screen.clear()
    picture = tufty["picture"][1]
    if picture is not None:
        x, y = layout["image_pos"]
        w, h = layout["image_size"]
        screen.blit(picture, rect(x, y, w, h))
    draw_label_and_marks(mood_set, state["mood"])


if TUFTY:
    badge.mode(HIRES | VSYNC)
    run(update_tufty)
else:
    # MEDIUM_UPDATE matches the gallery app; firmware v3.1.1 ignores the speed.
    # NON_BLOCKING keeps polling buttons while the e-paper refreshes.
    badge.mode(MEDIUM_UPDATE | NON_BLOCKING)
    run(update)
