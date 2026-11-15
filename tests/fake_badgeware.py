"""A recording stand-in for the Badgeware builtins the app uses.

run_app() copies the app to a temp directory (as launch() would chdir into it),
injects fakes as globals, and runs __init__.py with one update() per tick.

model="badger" (the default) fakes the Badger 2350's builtins. model="tufty"
fakes the Tufty 2350's instead: its run() clears the screen before and
refreshes the display after every update(), its badge has a backlight, and
the Badger-only names (NON_BLOCKING, wait_for_button_or_alarm,
badge.first_update) don't exist, so touching them fails the run.
"""

import os
import runpy
import shutil
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "badger" / "mood_badger"

BUTTON_A, BUTTON_B, BUTTON_C = "A", "B", "C"
BUTTON_UP, BUTTON_DOWN, BUTTON_HOME = "UP", "DOWN", "HOME"
MEDIUM_UPDATE = 2 << 4
NON_BLOCKING = 1 << 9
HIRES = 0b01
VSYNC = 0b10

# Pixels per character, so tests can push labels past the width limit.
CHAR_WIDTH = {"ignore": 12, "ziplock": 9, "smart": 7, "winds": 5}
TEXT_HEIGHT = 20


class _Stop(Exception):
    pass


class Result:
    def __init__(self):
        self.events = []
        self.blits = []
        self.texts = []
        self.text_y = []
        self.arrows = []
        self.waits = []
        self.saved = None
        self.mode = None
        self.fatal = None
        self.early_calls = []
        self.backlight = []
        self.blit_rects = []
        self.loads = 0
        self.exit = None


class _Font:
    def __init__(self, name):
        self.name = name


class _Fonts:
    def __getattr__(self, name):
        return _Font(name)


class _Colors:
    white = "white"
    black = "black"


class _Shape:
    def __init__(self, filled=True, points=None):
        self.filled = filled
        self.points = points

    def stroke(self, width):
        return _Shape(filled=False)


class _Shapes:
    @staticmethod
    def rectangle(x, y, w, h):
        return _Shape()

    @staticmethod
    def custom(points):
        return _Shape(points=[tuple(p) for p in points])


class _Image:
    def __init__(self, path):
        self.path = path
        self.width, self.height = 122, 136


class _ImageModule:
    def __init__(self, result):
        self._r = result

    def load(self, path):
        self._r.loads += 1
        if not os.path.exists(path):
            raise OSError(path)
        with open(path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                # picovector's decoder rejects it; the exact error type is undocumented
                raise RuntimeError("cannot decode " + path)
        return _Image(path)


class _Screen:
    def __init__(self, result):
        self._r = result
        self.pen = None
        self.font = _Font("sins")

    def clear(self):
        self._r.events.append("clear")

    def blit(self, img, pos):
        self._r.events.append("blit")
        self._r.blits.append(img.path)
        self._r.blit_rects.append(tuple(pos))

    def text(self, text, x, y):
        self._r.events.append("text")
        self._r.texts.append((text, self.font.name))
        self._r.text_y.append(y)

    def measure_text(self, text):
        return len(text) * CHAR_WIDTH.get(self.font.name, 10), TEXT_HEIGHT

    def shape(self, s):
        self._r.events.append("shape")
        if s.points is not None:
            self._r.arrows.append(s.points)


class _Display:
    def __init__(self, result):
        self._r = result

    def backlight(self, value):
        self._r.backlight.append(value)


class _Badge:
    def __init__(self, result, update_polls, model="badger", usb=True):
        self._r = result
        self.model = model
        self.running = False
        if model == "badger":
            self.first_update = True
        self.ticks = 0
        self.frame = 0
        self._usb = usb
        self.current = set()
        # Button sets seen by the poll at the end of each badge.update(). A press
        # caught there survives into the next update() unless a wait polls again.
        self._update_polls = list(update_polls)
        self.carried = False

    def poll(self):
        if not self.running:
            self._r.early_calls.append("poll")

    def pressed(self, button=None):
        # Like the firmware: no argument returns every pressed button.
        if button is None:
            return tuple(self.current)
        return button in self.current

    def update(self):
        if not self.running:
            self._r.early_calls.append("update")
        self._r.events.append("display")
        self.first_update = False
        if self._update_polls:
            self.current = set(self._update_polls.pop(0))
            self.carried = bool(self.current)

    def mode(self, value=None):
        self._r.mode = value

    def usb_connected(self):
        if isinstance(self._usb, (list, tuple)):
            return self._usb[min(self.frame, len(self._usb) - 1)]
        return self._usb

    def sleep(self):
        self._r.events.append("sleep")


def run_app(ticks, saved=None, config_text=None, files_missing=(), update_polls=(), files_corrupt=(),
            model="badger", usb=True, frame_ms=1000):
    """Run the app for one update() per entry in ticks (a set of buttons
    pressed that frame). usb is the power source, or a list with one value
    per tick; on the Tufty, badge.ticks advances frame_ms per tick."""
    result = Result()
    badge = _Badge(result, update_polls, model, usb)
    screen = _Screen(result)

    class State:
        @staticmethod
        def load(app, defaults):
            assert app == "mood_badger"
            if saved is not None:
                defaults.update(saved)
            return saved is not None

        @staticmethod
        def save(app, data):
            assert app == "mood_badger"
            result.events.append("save")
            result.saved = dict(data)

    def run(update):
        # One update() per tick, plus an extra one whenever a press caught by
        # badge.update() is still pending because the app skipped its wait.
        badge.running = True
        pending = list(ticks)
        while pending or badge.carried:
            if badge.carried:
                badge.carried = False
            else:
                badge.current = set(pending.pop(0))
            update()

    def run_tufty(update):
        # Like the Tufty's _run: clear, update(), display.update(), poll.
        badge.running = True
        for i, buttons in enumerate(ticks):
            badge.frame, badge.ticks = i, i * frame_ms
            badge.current = set(buttons)
            screen.clear()
            update()
            result.events.append("display")

    def wait_for_button_or_alarm(timeout=30_000):
        # Its first poll replaces whatever badge.update() last saw.
        badge.carried = False
        result.events.append("wait")
        result.waits.append(timeout)

    def fatal_error(title, error):
        result.fatal = str(error)
        raise _Stop()

    def file_exists(path):
        return os.path.exists(path)

    fakes = {
        "screen": screen, "badge": badge, "image": _ImageModule(result),
        "color": _Colors(), "font": _Fonts(), "shape": _Shapes(),
        "vec2": lambda x, y: (x, y), "State": State,
        "file_exists": file_exists, "fatal_error": fatal_error, "MEDIUM_UPDATE": MEDIUM_UPDATE,
        "BUTTON_A": BUTTON_A, "BUTTON_B": BUTTON_B, "BUTTON_C": BUTTON_C,
        "BUTTON_UP": BUTTON_UP, "BUTTON_DOWN": BUTTON_DOWN, "BUTTON_HOME": BUTTON_HOME,
    }
    if model == "badger":
        fakes.update({"run": run, "wait_for_button_or_alarm": wait_for_button_or_alarm,
                      "NON_BLOCKING": NON_BLOCKING})
    else:
        fakes.update({"run": run_tufty, "display": _Display(result), "HIRES": HIRES, "VSYNC": VSYNC,
                      "rect": lambda x, y, w, h: (x, y, w, h)})

    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        app = Path(tmp) / "mood_badger"
        shutil.copytree(APP_DIR, app, ignore=shutil.ignore_patterns("__pycache__"))
        if config_text is not None:
            (app / "config.json").write_text(config_text)
        for name in files_missing:
            (app / name).unlink()
        for name in files_corrupt:
            (app / name).write_bytes(b"\xff\xd8\xff\xe0 a JPEG renamed to .png")
        os.chdir(app)
        try:
            app_globals = runpy.run_path("__init__.py", init_globals=fakes)
            result.exit = app_globals.get("on_exit")
        except _Stop:
            pass
        finally:
            os.chdir(previous)
    return result
