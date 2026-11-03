"""A recording stand-in for the Badgeware builtins the app uses.

run_app() copies the app to a temp directory (as launch() would chdir into it),
injects fakes as globals, and runs __init__.py with one update() per tick.
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

# Pixels per character, so tests can push labels past the width limit.
CHAR_WIDTH = {"ignore": 12, "smart": 7}


class _Stop(Exception):
    pass


class Result:
    def __init__(self):
        self.events = []
        self.blits = []
        self.texts = []
        self.waits = []
        self.saved = None
        self.mode = None
        self.fatal = None
        self.early_calls = []


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
    def __init__(self, filled=True):
        self.filled = filled

    def stroke(self, width):
        return _Shape(filled=False)


class _Shapes:
    @staticmethod
    def rectangle(x, y, w, h):
        return _Shape()


class _Image:
    def __init__(self, path):
        self.path = path
        self.width, self.height = 122, 136


class _ImageModule:
    @staticmethod
    def load(path):
        if not os.path.exists(path):
            raise OSError(path)
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

    def text(self, text, x, y):
        self._r.events.append("text")
        self._r.texts.append((text, self.font.name))

    def measure_text(self, text):
        return len(text) * CHAR_WIDTH.get(self.font.name, 10), 20

    def shape(self, s):
        self._r.events.append("shape")


class _Badge:
    def __init__(self, result):
        self._r = result
        self.running = False
        self.first_update = True
        self.current = set()

    def poll(self):
        if not self.running:
            self._r.early_calls.append("poll")

    def pressed(self, button=None):
        return button in self.current

    def update(self):
        if not self.running:
            self._r.early_calls.append("update")
        self._r.events.append("display")
        self.first_update = False

    def mode(self, value=None):
        self._r.mode = value


def run_app(ticks, saved=None, config_text=None, files_missing=()):
    result = Result()
    badge = _Badge(result)

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
        badge.running = True
        for pressed in ticks:
            badge.current = set(pressed)
            update()

    def wait_for_button_or_alarm(timeout=30_000):
        result.events.append("wait")
        result.waits.append(timeout)

    def fatal_error(title, error):
        result.fatal = str(error)
        raise _Stop()

    def file_exists(path):
        return os.path.exists(path)

    fakes = {
        "screen": _Screen(result), "badge": badge, "image": _ImageModule(),
        "color": _Colors(), "font": _Fonts(), "shape": _Shapes(),
        "vec2": lambda x, y: (x, y), "State": State, "run": run,
        "file_exists": file_exists, "wait_for_button_or_alarm": wait_for_button_or_alarm,
        "fatal_error": fatal_error, "MEDIUM_UPDATE": MEDIUM_UPDATE, "NON_BLOCKING": NON_BLOCKING,
        "BUTTON_A": BUTTON_A, "BUTTON_B": BUTTON_B, "BUTTON_C": BUTTON_C,
        "BUTTON_UP": BUTTON_UP, "BUTTON_DOWN": BUTTON_DOWN, "BUTTON_HOME": BUTTON_HOME,
    }

    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        app = Path(tmp) / "mood_badger"
        shutil.copytree(APP_DIR, app, ignore=shutil.ignore_patterns("__pycache__"))
        if config_text is not None:
            (app / "config.json").write_text(config_text)
        for name in files_missing:
            (app / name).unlink()
        os.chdir(app)
        try:
            runpy.run_path("__init__.py", init_globals=fakes)
        except _Stop:
            pass
        finally:
            os.chdir(previous)
    return result
