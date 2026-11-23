"""Tests for the badge tools in tools/: the pure logic that the
badge-firmware and badge-deploy skills rely on. Nothing here touches a
real badge, USB drive or the network."""

from pathlib import Path

import pytest

from tools import badgeware_release as rel
from tools import badge_info, flash_firmware, install

ROOT = Path(__file__).resolve().parent.parent

# `mpremote devs` on a desk with a Tufty, a Particle board and Bluetooth ports.
DEVS = """\
/dev/cu.BoseQC45 None 0000:0000 None None
/dev/cu.debug-console None 0000:0000 None None
/dev/cu.usbmodem201401 bb713395bda7b3ab 2e8a:1101 Pimoroni Pimoroni Tufty 2350 MicroPython
/dev/cu.usbmodem20111101 e00fce68115b752338ceb4ef 2b04:c00d Particle Boron CDC Mode
"""


# --- badgeware_release -------------------------------------------------------

def test_badge_ports_finds_only_badges():
    assert rel.badge_ports(DEVS) == [("/dev/cu.usbmodem201401", "tufty")]


def test_badge_ports_finds_a_badger_and_a_tufty():
    devs = DEVS + "/dev/cu.usbmodem1101 abc 2e8a:1101 Pimoroni Pimoroni Badger 2350 MicroPython\n"
    assert rel.badge_ports(devs) == [
        ("/dev/cu.usbmodem201401", "tufty"), ("/dev/cu.usbmodem1101", "badger")]


def test_asset_names_match_pimoroni_releases():
    assert rel.asset_name("badger", "v3.1.1", False) == "badger-v3.1.1-micropython.uf2"
    assert rel.asset_name("tufty", "v3.1.1", True) == "tufty-v3.1.1-micropython-with-filesystem.uf2"


def test_pick_asset_chooses_the_flavour_and_explains_a_miss():
    release = {"tag_name": "v3.1.1", "assets": [
        {"name": "badger-v3.1.1-micropython-with-filesystem.uf2"},
        {"name": "badger-v3.1.1-micropython.uf2"}]}
    assert rel.pick_asset(release, "badger", False)["name"] == "badger-v3.1.1-micropython.uf2"
    assert rel.pick_asset(release, "badger", True)["name"].endswith("-with-filesystem.uf2")
    with pytest.raises(LookupError, match="tufty-v3.1.1-micropython.uf2"):
        rel.pick_asset(release, "tufty", False)


def test_build_date_comes_from_the_micropython_version():
    version = "v1.29.0-gc on 2026-09-23 (GNU 14.2.1 MinSizeRel)"
    assert rel.build_date(version) == "2026-09-23"
    assert rel.build_date("no date here") is None


@pytest.mark.parametrize("built,published,status", [
    ("2026-09-23", "2026-09-23T12:11:22Z", "current"),
    ("2026-09-21", "2026-09-23T12:11:22Z", "current"),
    ("2026-09-14", "2026-09-23T12:11:22Z", "older"),
    ("2026-10-05", "2026-09-23T12:11:22Z", "newer"),
    (None, "2026-09-23T12:11:22Z", "unknown"),
])
def test_firmware_status_compares_build_and_release_dates(built, published, status):
    assert rel.firmware_status(built, published) == status


def test_is_uf2_checks_the_block_magic():
    assert rel.is_uf2(b"UF2\n\x57\x51\x5d\x9e" + b"\0" * 24)
    assert not rel.is_uf2(b"<html>not a uf2 file")


def test_find_volumes_matches_labels_case_insensitively(tmp_path):
    (tmp_path / "BADGER").mkdir()
    (tmp_path / "Tufty2350").mkdir()
    (tmp_path / "Macintosh HD").mkdir()
    found = rel.find_volumes(("BADGER", "TUFTY2350"), bases=[tmp_path])
    assert sorted(p.name for p in found) == ["BADGER", "Tufty2350"]


# --- badge_info ----------------------------------------------------------------

def test_parse_info_reads_the_marked_line():
    out = 'MicroPython chatter\nBADGE_INFO {"model": "badger"}\n'
    assert badge_info.parse_info(out) == {"model": "badger"}


def test_device_snippet_is_valid_micropython_syntax():
    compile(badge_info.DEVICE_SNIPPET, "<badge>", "exec")


@pytest.mark.parametrize("path,mode", [
    (ROOT / "kiosk" / "main.py", "kiosk"),
    (ROOT / "kiosk" / "start_in_app.py", "start-in-app"),
    (ROOT / "vendor" / "badger2350" / "firmware" / "main.py", "menu"),
    (ROOT / "vendor" / "tufty2350" / "firmware" / "main.py", "menu"),
])
def test_boot_mode_of_each_known_file(path, mode):
    assert install.boot_mode(path.read_text()) == mode


def test_boot_mode_reports_custom_main_py():
    assert install.boot_mode('print("hi")\n') == "custom"
    edited = install.STOCK_MAINS["badger"].read_text() + "\nprint('mine')\n"
    assert install.boot_mode(edited) == "custom"


def test_boot_mode_ignores_trailing_whitespace_on_a_stock_file():
    assert install.boot_mode(install.STOCK_MAINS["tufty"].read_text() + "\n\n") == "menu"


def summary(main_py):
    info = {"version": "v1.26.0 on 2025-11-20", "apps": ["menu", "mood_badger"], "main_py": main_py,
            "model": "tufty", "model_source": "badge.model", "machine": "x", "release": "1.26"}
    return badge_info.summarise("/dev/x", info, None)


def test_badge_info_reports_the_start_up_mode(capsys):
    info = summary((ROOT / "kiosk" / "start_in_app.py").read_text())
    assert info["boot_mode"] == "start-in-app" and "kiosk" not in info
    badge_info.report(info, "offline")
    assert "Start-up:" in capsys.readouterr().out


@pytest.mark.parametrize("mode,text", [
    ("kiosk", "Mood Badger only (kiosk)"),
    ("start-in-app", "Mood Badger, HOME opens the menu (start-in-app)"),
    ("menu", "Pimoroni menu"),
    ("custom", "custom main.py"),
    (None, "unknown"),
])
def test_badge_info_start_up_text(mode, text):
    assert badge_info.START_UP_TEXT[mode] == text


# --- install -------------------------------------------------------------------

def fake_drive(base, label="BADGER"):
    """A badge drive in disk mode: main.py and apps/ with another app."""
    root = base / label
    (root / "apps" / "menu").mkdir(parents=True)
    (root / "apps" / "menu" / "__init__.py").write_text("menu")
    (root / "main.py").write_text("stock main")
    return root


def fake_app(base):
    src = base / "src" / "mood_badger"
    (src / "assets").mkdir(parents=True)
    (src / "__init__.py").write_text("app")
    (src / "assets" / "a.png").write_bytes(b"png")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "moods.cpython-311.pyc").write_bytes(b"pyc")
    (src / ".DS_Store").write_bytes(b"junk")
    (src / "._icon.png").write_bytes(b"junk")
    return src


def test_model_comes_from_the_drive_label():
    assert install.model_for_drive(Path("/Volumes/BADGER")) == "badger"
    assert install.model_for_drive(Path("/Volumes/Tufty2350")) == "tufty"
    assert install.model_for_drive(Path("/Volumes/USBSTICK")) is None


def test_tufty_drive_installs_the_same_app():
    assert install.APPS["badger"] == ROOT / "badger" / "mood_badger"
    assert install.APPS["tufty"] == install.APPS["badger"]
    assert install.model_for_drive(Path("/Volumes/TUFTY")) == "tufty"


def test_menu_restores_the_stock_main_for_that_model(tmp_path):
    badger, tufty = install.STOCK_MAINS["badger"], install.STOCK_MAINS["tufty"]
    assert badger.read_text() != tufty.read_text()
    root = fake_drive(tmp_path, "TUFTY")
    install.set_main(root, tufty)
    assert (root / "main.py").read_text() == tufty.read_text()


def test_start_in_app_refused_on_a_badger(tmp_path, monkeypatch):
    root = fake_drive(tmp_path)
    monkeypatch.setattr("sys.argv", ["install", "--dest", str(root), "--model", "badger", "--start-in-app"])
    with pytest.raises(SystemExit) as stop:
        install.main()
    assert str(stop.value) == ("Start-in-app mode is for the Tufty 2350; the Badger already returns "
                               "to Mood Badger after a wake. Nothing copied.")
    assert not (root / "apps" / "mood_badger").exists()
    assert (root / "main.py").read_text() == "stock main"


def test_install_copies_app_files_only(tmp_path):
    root, src = fake_drive(tmp_path), fake_app(tmp_path)
    install.install_app(src, root)
    target = root / "apps" / "mood_badger"
    copied = sorted(str(p.relative_to(target)) for p in target.rglob("*") if p.is_file())
    assert copied == ["__init__.py", "assets/a.png"]
    assert (root / "apps" / "menu" / "__init__.py").exists(), "other apps are left alone"
    assert (root / "main.py").read_text() == "stock main", "main.py is left alone"


def test_install_removes_files_dropped_from_the_app(tmp_path):
    root, src = fake_drive(tmp_path), fake_app(tmp_path)
    stale = root / "apps" / "mood_badger" / "assets" / "old.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old")
    install.install_app(src, root)
    assert not stale.exists()


def test_verify_copy_reports_missing_and_changed_files(tmp_path):
    root, src = fake_drive(tmp_path), fake_app(tmp_path)
    install.install_app(src, root)
    target = root / "apps" / "mood_badger"
    assert install.verify_copy(src, target) == []
    (target / "assets" / "a.png").write_bytes(b"truncated-and-changed")
    (target / "__init__.py").unlink()
    assert sorted(install.verify_copy(src, target)) == ["__init__.py", "assets/a.png"]


def test_kiosk_install_and_restore(tmp_path):
    root = fake_drive(tmp_path)
    install.set_main(root, install.KIOSK_MAIN)
    assert install.boot_mode((root / "main.py").read_text()) == "kiosk"
    install.set_main(root, install.STOCK_MAINS["badger"])
    assert install.boot_mode((root / "main.py").read_text()) == "menu"
    assert (root / "main.py").read_text() == install.STOCK_MAINS["badger"].read_text()


def test_start_in_app_install(tmp_path):
    root = fake_drive(tmp_path, "TUFTY")
    install.set_main(root, install.START_IN_APP_MAIN)
    assert install.boot_mode((root / "main.py").read_text()) == "start-in-app"


def test_looks_like_badge_needs_apps_and_main(tmp_path):
    assert install.looks_like_badge(fake_drive(tmp_path))
    (tmp_path / "STICK").mkdir()
    assert not install.looks_like_badge(tmp_path / "STICK")


# --- waiting for the user's button press ---------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_wait_for_returns_as_soon_as_something_appears():
    clock, polls = FakeClock(), []

    def find():
        polls.append(clock.now)
        return ["/Volumes/BADGER"] if clock.now >= 3 else []

    found = rel.wait_for(find, timeout=60, interval=1, clock=clock.time, sleep=clock.sleep)
    assert found == ["/Volumes/BADGER"]
    assert polls == [0, 1, 2, 3]


def test_wait_for_gives_up_after_the_timeout():
    clock = FakeClock()
    found = rel.wait_for(list, timeout=10, interval=1, clock=clock.time, sleep=clock.sleep)
    assert found == []
    assert clock.now == 10


def test_wait_for_with_no_timeout_looks_once():
    clock = FakeClock()
    assert rel.wait_for(list, timeout=0, clock=clock.time, sleep=clock.sleep) == []
    assert clock.now == 0


# --- surviving interruptions and macOS metadata ---------------------------------

def test_a_failed_copy_leaves_the_old_app_working(tmp_path, monkeypatch):
    root, src = fake_drive(tmp_path), fake_app(tmp_path)
    old = root / "apps" / "mood_badger"
    old.mkdir()
    (old / "__init__.py").write_text("old app")

    def unplugged(*_args, **_kwargs):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(install.shutil, "copytree", unplugged)
    with pytest.raises(OSError):
        install.install_app(src, root)
    assert (old / "__init__.py").read_text() == "old app"


def test_staging_is_outside_apps_so_the_menu_never_lists_it(tmp_path):
    root = fake_drive(tmp_path)
    assert install.staging_dir(root).parent == root
    assert install.staging_dir(root).name.startswith(".")


def test_leftovers_from_an_interrupted_install_are_cleared(tmp_path):
    root, src = fake_drive(tmp_path), fake_app(tmp_path)
    leftover = install.staging_dir(root) / "half.png"
    leftover.parent.mkdir()
    leftover.write_bytes(b"half")
    install.install_app(src, root)
    assert not install.staging_dir(root).exists()
    assert (root / "apps" / "mood_badger" / "__init__.py").read_text() == "app"


def test_appledouble_files_are_removed(tmp_path):
    app = tmp_path / "apps" / "mood_badger"
    (app / "assets").mkdir(parents=True)
    for name in ("__init__.py", "assets/a.png"):
        (app / name).write_text("real")
    for name in ("._mood_badger",):
        (app.parent / name).write_bytes(b"\0" * 4096)
    for name in (".___init__.py", "._assets", "assets/._a.png"):
        (app / name).write_bytes(b"\0" * 4096)
    install.remove_appledouble(app)
    left = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file())
    assert left == ["apps/mood_badger/__init__.py", "apps/mood_badger/assets/a.png"]


def test_setting_main_removes_its_appledouble_file(tmp_path):
    # macOS writes ._main.py beside main.py on the badge's FAT drive.
    root = fake_drive(tmp_path)
    (root / "._main.py").write_bytes(b"\0" * 4096)
    install.set_main(root, install.KIOSK_MAIN)
    assert not (root / "._main.py").exists()
    assert (root / "main.py").read_text() == install.KIOSK_MAIN.read_text()


def test_badge_info_restarts_the_badge_after_reading_it():
    # mpremote stops the running program; without a reset the badge sits
    # on a frozen screen until someone presses RESET.
    cmd = badge_info.mpremote_command("/dev/cu.usbmodem1101")
    assert cmd[:4] == ["mpremote", "connect", "/dev/cu.usbmodem1101", "exec"]
    assert cmd[-1] == "reset"
    assert "reset" not in badge_info.mpremote_command("/dev/x", restart=False)


# --- flash_firmware: knowing when the flash has finished ----------------------

BADGER_DEVS = "/dev/cu.usbmodem201401 43a7 2e8a:1100 Pimoroni Pimoroni Badger 2350 MicroPython\n"


def test_flash_is_confirmed_when_the_badge_is_back_in_normal_mode():
    answers = iter(["", "", BADGER_DEVS])
    port = flash_firmware.wait_for_restart(
        "badger", timeout=10, list_devs=lambda: next(answers), interval=0)
    assert port == "/dev/cu.usbmodem201401"


def test_flash_confirmation_ignores_other_badges_and_gives_up():
    tufty_only = DEVS  # a Tufty and a Particle board, but no Badger
    port = flash_firmware.wait_for_restart(
        "badger", timeout=0, list_devs=lambda: tufty_only, interval=0)
    assert port is None


def test_start_in_app_eject_says_to_press_reset(tmp_path, monkeypatch, capsys):
    # The restart after the disk-mode eject is a watchdog reboot (seen on a
    # real Tufty: WAKE_WATCHDOG), so start-in-app lands on the menu.
    root = fake_drive(tmp_path, "TUFTY")
    monkeypatch.setattr(install, "APPS", {"tufty": fake_app(tmp_path)})
    monkeypatch.setattr(install, "eject", lambda root: True)
    monkeypatch.setattr("sys.argv", ["install", "--dest", str(root), "--start-in-app", "--eject"])
    install.main()
    out = capsys.readouterr().out
    assert "Start-up: start-in-app" in out
    assert "menu: press RESET once to open Mood Badger" in out
