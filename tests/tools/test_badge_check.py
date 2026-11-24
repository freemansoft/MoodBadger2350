"""Tests for tools/badge_check.py: the pure logic behind checking a badge
after an install (files on the badge's side) and reading its restart
reason. Nothing here touches a real badge."""

import pytest

from tools import badge_check


def test_device_snippets_compile():
    # CPython's compiler: catches syntax errors before the badge does.
    compile(badge_check.FILES_SNIPPET, "<badge>", "exec")
    compile(badge_check.WAKE_SNIPPET, "<badge>", "exec")


def test_local_files_are_what_install_copies_with_sizes(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "__init__.py").write_text("app")
    (tmp_path / "assets" / "a.png").write_bytes(b"12345")
    (tmp_path / "._junk").write_bytes(b"x")
    assert badge_check.local_files(tmp_path) == {"__init__.py": 3, "assets/a.png": 5}


def test_compare_files_matching():
    files = {"__init__.py": 3, "assets/a.png": 5}
    assert badge_check.compare_files(files, dict(files)) == {}


def test_compare_files_reports_missing_extra_size_and_junk():
    local = {"__init__.py": 3, "assets/a.png": 5, "moods.py": 9}
    badge = {"__init__.py": 3, "assets/a.png": 4, "old.py": 1, "._moods.py": 4096}
    assert badge_check.compare_files(local, badge) == {
        "missing": ["moods.py"],
        "different size": ["assets/a.png"],
        "not in the app": ["old.py"],
        "macOS junk": ["._moods.py"],
    }


def test_parse_tagged_line():
    out = 'noise\nBADGE_CHECK {"reason": 241}\n'
    assert badge_check.parse_tagged(out) == {"reason": 241}
    with pytest.raises(ValueError):
        badge_check.parse_tagged("no tag here")


@pytest.mark.parametrize("reason,name", [
    (241, "WAKE_RESET"), (99, "unknown (99)")])
def test_wake_name(reason, name):
    names = {"WAKE_RESET": 241, "WAKE_WATCHDOG": 242, "WAKE_DOUBLETAP": 5}
    assert badge_check.wake_name(reason, names) == name


@pytest.mark.parametrize("reason,meaning", [
    ("WAKE_RESET", "Mood Badger"), ("WAKE_WATCHDOG", "the menu"), ("WAKE_DOUBLETAP", "disk mode")])
def test_start_in_app_meaning(reason, meaning):
    assert meaning in badge_check.start_in_app_meaning(reason)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_wait_for_restart_needs_the_badge_to_leave_and_come_back():
    clock = FakeClock()
    # present, present, gone (RESET pressed), gone, back
    seen = iter([True, True, False, False, True])
    assert badge_check.wait_for_restart(lambda: next(seen), timeout=60, interval=1,
                                        clock=clock.time, sleep=clock.sleep)
    assert clock.now == 4


def test_wait_for_restart_times_out_if_nothing_happens():
    clock = FakeClock()
    assert not badge_check.wait_for_restart(lambda: True, timeout=10, interval=1,
                                            clock=clock.time, sleep=clock.sleep)


def test_mpremote_commands_end_with_a_reset():
    for snippet in (badge_check.FILES_SNIPPET, badge_check.WAKE_SNIPPET):
        cmd = badge_check.mpremote_command("/dev/x", snippet)
        assert cmd[:3] == ["mpremote", "connect", "/dev/x"] and cmd[-1] == "reset"
