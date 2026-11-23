# Mood Badger on the Tufty 2350: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One `badger/mood_badger` app that runs on the Badger 2350 unchanged and on the Tufty 2350 as a "bigger Badger" with a dimming backlight, plus a start-in-app boot file, Tufty-aware tools, a Tufty simulator and a `badgeware-platforms` skill.

**Architecture:** Pure layout and backlight rules go in `moods.py` (no Badgeware names, desktop-testable). `__init__.py` loads config and state once, then branches on `badge.model`: the existing Badger code path untouched, and a Tufty path that redraws every frame in HIRES and drives `display.backlight()`. A new `kiosk/start_in_app.py` picks Mood Badger or the menu from `powman.get_wake_reason()`. Tools learn per-model stock `main.py` files and a three-way start-up mode.

**Tech Stack:** MicroPython (Badgeware v3.1.1, picovector), Python 3 standard library tools, pytest, Node for the headless simulator, badgeware-wasm builds.

**Spec:** `docs/superpowers/specs/2026-11-14-tufty-support-design.md`

## Global Constraints

- Firmware pinned at `v3.1.1` for both badges; read behaviour from `vendor/badger2350` and `vendor/tufty2350`.
- The Badger's behaviour and drawing do not change. Every existing Badger test keeps passing; existing tests may only gain a `model="badger"` default, not changed assertions.
- `badger/mood_badger/moods.py` contains no Badgeware names.
- Nothing in the Badger path calls `badge.poll()` or `badge.update()` before `run(update)`.
- Tufty code never references `NON_BLOCKING`, `wait_for_button_or_alarm`, or `badge.first_update` (absent or meaningless on the Tufty).
- Backlight: full `1.0` on any press; after `10_000` ms idle, `0.5` on USB, `0.15` on battery. Never `0`.
- A press while dimmed, and any press on the Tufty's first frame, only brighten; they never change mood or set.
- The app never calls `badge.sleep()` or any deep sleep on the Tufty.
- Each badge keeps its own `State` "mood_badger" (`{"set", "mood"}`); same key and format on both.
- Start-in-app: `WAKE_WATCHDOG` → stock Tufty menu flow; anything else → `launch("/system/apps/mood_badger")`. Tufty only.
- Every app module passes `.venv/bin/python -m mpy_cross -o /dev/null <file>` and `.venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **USB unplugged while dimmed:** the level drops from 0.5 to 0.15 on the next frame with no press. Test in Task 3 (`test_tufty_dim_level_follows_power_source_without_a_press`).
2. **Missing or undecodable picture on the Tufty:** the label still draws every frame, and the app does not retry `image.load` 90 times a second. Test in Task 3 (`test_tufty_bad_image_draws_label_and_loads_once`).
3. **Both UP and DOWN (or A and C) pressed on a dimmed screen:** only wakes, no save. Test in Task 3 (`test_tufty_any_press_while_dimmed_only_wakes`).
4. **HOME pressed while dimmed:** the menu must not open dimmed. Test in Task 3 (`test_tufty_on_exit_restores_full_brightness`).
5. **A main.py that is neither ours nor stock** (user-edited): tools must report it as `custom`, not as kiosk or menu, and `--menu` must still restore the right stock file for that model. Test in Task 4 (`test_boot_mode_reports_custom_main_py`).

---

### Task 1: Vendor the Tufty firmware and add the `badgeware-platforms` skill

**Files:**

- Create: `vendor/tufty2350` (git submodule, `https://github.com/pimoroni/tufty2350`, checked out at tag `v3.1.1`)
- Modify: `.gitmodules`
- Create: `.claude/skills/badgeware-platforms/SKILL.md`
- Modify: `CLAUDE.md` (Development section: setup line already covers submodules; add one line pointing to the skill; change "Read hardware and runtime behaviour from the firmware source in `vendor/badger2350`" to name both submodules)
- Modify: `.claude/skills/badge-deploy/SKILL.md`, `.claude/skills/badge-firmware/SKILL.md` (one-line pointer each, in their "Tufty 2350" sections)
- Test: `tests/test_platform_skill.py`

**Interfaces:**

- Produces: `vendor/tufty2350/...` paths used by Tasks 4 and 5 (`vendor/tufty2350/firmware/main.py`, `vendor/tufty2350/modules/common/badgeware`, `vendor/tufty2350/romfs/fonts`).

- [ ] **Step 1: Add the submodule**

```bash
git submodule add https://github.com/pimoroni/tufty2350 vendor/tufty2350
git -C vendor/tufty2350 checkout v3.1.1
```

Expected: `git -C vendor/tufty2350 describe --tags` prints `v3.1.1`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_platform_skill.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "badgeware-platforms" / "SKILL.md"


def test_skill_has_frontmatter_name_and_description():
    text = SKILL.read_text()
    assert text.startswith("---\nname: badgeware-platforms\ndescription: ")


def test_every_vendor_path_cited_in_the_skill_exists():
    cited = set(re.findall(r"vendor/(?:badger2350|tufty2350)/[\w./-]+", SKILL.read_text()))
    assert cited, "the skill must cite firmware source"
    missing = [p for p in sorted(cited) if not (ROOT / p.rstrip(".")).exists()]
    assert missing == []


def test_tufty_submodule_is_pinned_to_v3_1_1():
    assert (ROOT / "vendor" / "tufty2350" / "firmware" / "main.py").exists()
    assert "tufty2350" in (ROOT / ".gitmodules").read_text()


def test_other_skills_and_claude_md_point_to_it():
    for path in (ROOT / "CLAUDE.md",
                 ROOT / ".claude/skills/badge-deploy/SKILL.md",
                 ROOT / ".claude/skills/badge-firmware/SKILL.md"):
        assert "badgeware-platforms" in path.read_text(), path
```

- [ ] **Step 3: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_platform_skill.py -v`
Expected: FAIL (skill file missing).

- [ ] **Step 4: Write `.claude/skills/badgeware-platforms/SKILL.md`**

Frontmatter `name: badgeware-platforms`; a pushy description: load it whenever writing, changing, reviewing or planning Mood Badger app code (or any Badgeware app) that runs on a Badger 2350 or Tufty 2350, porting between them, or debugging something that works on one badge but not the other, even if the user only says "make it work on the Tufty". Body:

- The difference table from the spec's "Constraints and facts" section, with every Source cell rewritten as a full `vendor/badger2350/...` or `vendor/tufty2350/...` path (e.g. `vendor/tufty2350/modules/common/badgeware/__init__.py`, `vendor/tufty2350/modules/c/powman/bindings.c`, `vendor/tufty2350/firmware/apps/menu/__init__.py`).
- Rows the spec table lacks: Tufty menu always starts at the first app (`active = 0`) and lists apps alphabetically; on the Tufty HOME is also BOOT, so a restart while HOME is held enters the bootloader (`reset()` waits for release); the waking button press reaches the first `badge.poll()` (`vendor/tufty2350/modules/c/input/input.cpp`), and the stock Tufty `main.py` eats it.
- Rules for app code that follow (one line each, with the why): never assume the screen keeps its image; on the Tufty draw every frame because `run()` clears first; cache decoded images; save state before refreshing or sleeping; branch on `badge.model`, never on drive names; guard Badger-only names.
- How Mood Badger handles each difference today (pointers to `badger/mood_badger/__init__.py`, `kiosk/start_in_app.py`, `tools/install.py`), and "re-check these rows against the new tag before bumping either submodule".

- [ ] **Step 5: Add the pointers** in `CLAUDE.md`, `badge-deploy` and `badge-firmware` (one line each: "Badger vs Tufty differences: see the `badgeware-platforms` skill").

- [ ] **Step 6: Run tests**

Run: `.venv/bin/pytest -q`
Expected: all pass (152 + 4).

- [ ] **Step 7: Commit**

```bash
git add .gitmodules vendor/tufty2350 .claude/skills CLAUDE.md tests/test_platform_skill.py
git commit -m "feat: vendor tufty2350 v3.1.1 and add badgeware-platforms skill"
```

---

### Task 2: Per-model layout and backlight rules in `moods.py`

**Files:**

- Modify: `badger/mood_badger/moods.py`
- Test: `tests/test_moods.py`

**Interfaces:**

- Produces (all in `moods.py`):
  - `BADGER` and `TUFTY`: dicts with keys `screen_w, screen_h, image_pos, image_size, label_centre_x, label_max_width, arrow_a_x, arrow_c_x, arrow_mid_y, arrow_half, pip_x, pip_size, pip_spacing`.
  - `LAYOUTS = {"badger": BADGER, "tufty": TUFTY}`
  - `set_arrows(set_count, layout=BADGER) -> list[list[tuple]]`
  - `pip_positions(count, layout=BADGER) -> list[tuple]`
  - `DIM_AFTER_MS = 10_000`, `BRIGHT = 1.0`, `DIM_USB = 0.5`, `DIM_BATTERY = 0.15`
  - `backlight_level(idle_ms: int, on_usb: bool) -> float`
- Existing module constants (`PIP_X`, `PIP_SIZE`, `PIP_SPACING`, `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `ARROW_A_X`, `ARROW_C_X`, `ARROW_MID_Y`, `ARROW_HALF`) stay, equal to the `BADGER` values, so existing tests and the Badger path are unchanged.

Values:

- `BADGER`: `screen_w 264, screen_h 176, image_pos (61, 2), image_size (122, 136), label_centre_x 122, label_max_width 140, arrow_a_x 43, arrow_c_x 210, arrow_mid_y 157, arrow_half 5, pip_x 250, pip_size 8, pip_spacing 10`.
- `TUFTY` (320x240, picture scaled 1.5x to 183x204): `screen_w 320, screen_h 240, image_pos (59, 4), image_size (183, 204), label_centre_x 150, label_max_width 170, arrow_a_x 52, arrow_c_x 255, arrow_mid_y 224, arrow_half 7, pip_x 300, pip_size 10, pip_spacing 13`. (Arrow x = Badger's scaled by 320/264; check against the real buttons in Task 6.)

- [ ] **Step 1: Write the failing tests** (add to `tests/test_moods.py`)

```python
from moods import BADGER, TUFTY, LAYOUTS, backlight_level, DIM_AFTER_MS


def test_badger_layout_matches_the_existing_constants():
    assert BADGER["pip_x"] == moods.PIP_X and BADGER["arrow_mid_y"] == moods.ARROW_MID_Y
    assert set_arrows(3, BADGER) == set_arrows(3)
    assert pip_positions(8, BADGER) == pip_positions(8)


def test_layouts_keyed_by_badge_model():
    assert LAYOUTS == {"badger": BADGER, "tufty": TUFTY}


def test_tufty_picture_is_the_badger_picture_scaled_one_and_a_half():
    assert TUFTY["image_size"] == (183, 204)
    x, y = TUFTY["image_pos"]
    assert x + 183 < TUFTY["pip_x"] and y + 204 < TUFTY["arrow_mid_y"] - TUFTY["arrow_half"]


def test_tufty_arrows_and_pips_stay_on_screen_and_apart():
    for x, y in [p for arrow in set_arrows(2, TUFTY) for p in arrow]:
        assert 0 <= x < TUFTY["pip_x"] and 0 <= y < 240
    assert all(0 <= y and y + TUFTY["pip_size"] <= 240 for _, y in pip_positions(MAX_MOODS, TUFTY))


@pytest.mark.parametrize("idle_ms,on_usb,level", [
    (0, False, 1.0), (DIM_AFTER_MS - 1, False, 1.0), (DIM_AFTER_MS, False, 0.15),
    (0, True, 1.0), (DIM_AFTER_MS, True, 0.5), (10 * 60_000, False, 0.15),
])
def test_backlight_level(idle_ms, on_usb, level):
    assert backlight_level(idle_ms, on_usb) == level


def test_backlight_never_goes_dark():
    assert min(backlight_level(10**9, usb) for usb in (True, False)) > 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_moods.py -v`
Expected: FAIL with ImportError on `BADGER`.

- [ ] **Step 3: Implement** the dicts, `LAYOUTS`, the `layout=BADGER` parameter on `set_arrows` and `pip_positions` (read the dict instead of module constants), and `backlight_level`. Define `BADGER` from the existing module constants so there is one source of truth.

- [ ] **Step 4: Run tests and app checks**

Run: `.venv/bin/pytest -q && .venv/bin/python -m mpy_cross -o /dev/null badger/mood_badger/moods.py && .venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger`
Expected: all pass, no output from mpy_cross, ruff "All checks passed!".

- [ ] **Step 5: Commit**

```bash
git add badger/mood_badger/moods.py tests/test_moods.py
git commit -m "feat: per-model layouts and Tufty backlight rules in moods.py"
```

---

### Task 3: The Tufty code path in the app

**Files:**

- Modify: `badger/mood_badger/__init__.py`
- Modify: `tests/fake_badgeware.py`
- Create: `tests/test_app_tufty.py`
- Modify: `badger/mood_badger/README.md` (Tufty controls, dimming, "hold RESET until the case lights fade to power off")

**Interfaces:**

- Consumes: `moods.LAYOUTS`, `moods.TUFTY`, `moods.set_arrows(n, layout)`, `moods.pip_positions(n, layout)`, `moods.backlight_level`, `moods.DIM_AFTER_MS`, `moods.BRIGHT`.
- Produces:
  - `on_exit()` defined at module level in `__init__.py` **before** `run(...)` (Badgeware's `launch()` calls it when HOME is pressed): on the Tufty sets `display.backlight(1.0)`; on the Badger does nothing.
  - `run_app(ticks, ..., model="badger", usb=True, frame_ms=1000)` in the fake. With `model="tufty"`: no `NON_BLOCKING`, `wait_for_button_or_alarm` or `badge.first_update` in the injected globals/badge; `run()` calls `screen.clear()` before every `update()` and records `"display"` after it, like the Tufty's `_run`; `badge.ticks` advances by `frame_ms` per tick; `badge.usb_connected()` returns `usb`, which may be a list (one value per tick); a `display` fake records `backlight(v)` calls in `result.backlight`; `rect(x, y, w, h)` and `HIRES`, `VSYNC` exist; `screen.blit(img, r)` records `r` in `result.blit_rects`; `image.load` calls counted in `result.loads`; `result.exit` holds the module's `on_exit` (read from the run globals after the app returns).

Tufty behaviour to implement (Badger branch is the existing code, moved under `if badge.model != "tufty":` unchanged):

- `badge.mode(HIRES | VSYNC)`; `layout = moods.LAYOUTS["tufty"]`.
- Per frame: first frame ignores presses; otherwise if `moods.backlight_level(idle, usb) < moods.BRIGHT` any press only resets the idle timer; otherwise apply `moods.apply_input(...)` and save state on change (before drawing).
- Call `display.backlight(level)` only when the level changes.
- Draw every frame: white clear, the picture scaled into `rect(*image_pos, *image_size)`, label, arrows, pips (same fonts and fallbacks as the Badger, from `layout`).
- Cache the decoded picture by file name; a failed load is cached as "no picture" until the mood changes.

- [ ] **Step 1: Extend the fake** as in Interfaces; keep every existing Badger default so `tests/test_app.py` runs unchanged.

- [ ] **Step 2: Run the existing app tests to confirm the fake still serves the Badger**

Run: `.venv/bin/pytest tests/test_app.py -q`
Expected: all pass.

- [ ] **Step 3: Write the failing Tufty tests** in `tests/test_app_tufty.py`

```python
from fake_badgeware import BUTTON_A, BUTTON_C, BUTTON_DOWN, BUTTON_UP, CHAR_WIDTH, HIRES, VSYNC, run_app
import moods

T = dict(model="tufty")
IDLE = [set()] * 11          # 11 frames of 1000 ms: past DIM_AFTER_MS


def test_tufty_uses_hires_and_never_badger_only_names():
    r = run_app([set()], **T)          # NameError on NON_BLOCKING etc. would surface as r.fatal
    assert r.fatal is None and r.mode == HIRES | VSYNC

def test_tufty_redraws_every_frame_on_white():
    r = run_app([set()] * 3, **T)
    assert r.events.count("blit") == 3 and r.events.count("display") == 3

def test_tufty_scales_picture_into_layout_rect():
    r = run_app([set()], saved={"set": 0, "mood": 2}, **T)
    assert r.blits == ["assets/sent_angry.png"]
    assert r.blit_rects == [(*moods.TUFTY["image_pos"], *moods.TUFTY["image_size"])]

def test_tufty_loads_each_picture_once():
    assert run_app([set()] * 5, **T).loads == 1

def test_tufty_first_frame_press_only_wakes():
    r = run_app([{BUTTON_DOWN}], saved={"set": 0, "mood": 0}, **T)
    assert r.saved is None and r.blits[-1] == "assets/sent_chilled.png"

def test_tufty_press_while_bright_moves_mood_and_saves_before_drawing():
    r = run_app([set(), {BUTTON_DOWN}], saved={"set": 0, "mood": 0}, **T)
    assert r.saved == {"set": 0, "mood": 1}
    last_blit = len(r.events) - 1 - r.events[::-1].index("blit")
    assert r.events.index("save") < last_blit and r.blits[-1] == "assets/sent_sad.png"

def test_tufty_full_brightness_then_dims_on_battery():
    r = run_app([set()] + IDLE, usb=False, **T)
    assert r.backlight == [1.0, 0.15]

def test_tufty_dims_to_half_on_usb():
    assert run_app([set()] + IDLE, usb=True, **T).backlight == [1.0, 0.5]

def test_tufty_dim_level_follows_power_source_without_a_press():
    r = run_app([set()] + IDLE + [set()], usb=[True] * 12 + [False], **T)
    assert r.backlight == [1.0, 0.5, 0.15]

def test_tufty_any_press_while_dimmed_only_wakes():
    for press in ({BUTTON_DOWN}, {BUTTON_UP, BUTTON_DOWN}, {BUTTON_A, BUTTON_C}):
        r = run_app([set()] + IDLE + [press], usb=False, saved={"set": 0, "mood": 0}, **T)
        assert r.saved is None and r.backlight == [1.0, 0.15, 1.0]

def test_tufty_second_press_after_wake_changes_mood():
    r = run_app([set()] + IDLE + [{BUTTON_DOWN}, {BUTTON_DOWN}], usb=False, saved={"set": 0, "mood": 0}, **T)
    assert r.saved == {"set": 0, "mood": 1}

def test_tufty_c_changes_set_when_bright():
    r = run_app([set(), {BUTTON_C}], **T)
    assert r.saved["set"] == 1

def test_tufty_never_sleeps():
    r = run_app([set()] + IDLE * 3, usb=False, **T)
    assert "sleep" not in r.events and r.waits == []

def test_tufty_bad_image_draws_label_and_loads_once():
    r = run_app([set()] * 4, files_corrupt=("sent_chilled.png",), **T)
    assert r.fatal is None and r.loads == 1 and r.texts.count(("Chilled", "ignore")) == 4

def test_tufty_on_exit_restores_full_brightness():
    r = run_app([set()] + IDLE, usb=False, **T)
    r.exit()
    assert r.backlight[-1] == 1.0

def test_tufty_long_label_steps_down_to_fit_its_wider_space():
    # 15 chars: 180 px in ignore (> 170), 135 px in ziplock (fits)
    config = '{"moods": [[["Very Frustrated", "sent_sad.png"]]]}'
    r = run_app([set()], config_text=config, **T)
    assert r.texts == [("Very Frustrated", "ziplock")]
    assert len("Very Frustrated") * CHAR_WIDTH["ziplock"] <= moods.TUFTY["label_max_width"]


def test_tufty_label_that_fits_170_but_not_140_keeps_ignore():
    # 13 chars: 156 px in ignore, too wide on the Badger, fits on the Tufty
    config = '{"moods": [[["Overwhelmed!!", "sent_sad.png"]]]}'
    assert run_app([set()], config_text=config, **T).texts == [("Overwhelmed!!", "ignore")]
```

The fake exports `HIRES = 0b01` and `VSYNC = 0b10` (the Tufty's values).

Add one Badger test to `tests/test_app.py`: `test_badger_on_exit_does_nothing` (`run_app([set()]).exit()` leaves `r.backlight == []`).

- [ ] **Step 4: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_app_tufty.py -v`
Expected: FAIL (app has no Tufty path; first failure is a NameError on `NON_BLOCKING` reported in `r.fatal` or a missing `wait_for_button_or_alarm`).

- [ ] **Step 5: Implement the Tufty path and `on_exit()`** in `__init__.py` as described above. Keep the shared config load, `State.load` and `moods.restore` at the top, before the model branch.

- [ ] **Step 6: Run all tests and app checks**

Run: `.venv/bin/pytest -q && for f in badger/mood_badger/*.py; do .venv/bin/python -m mpy_cross -o /dev/null "$f"; done && .venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger`
Expected: all pass, including the unchanged Badger tests and the headless Badger simulator test.

- [ ] **Step 7: Update `badger/mood_badger/README.md`** (Tufty section: same buttons; screen dims after 10 s, a press while dim only brightens; no auto power-off; hold RESET until the case lights fade to power off; any front button turns it on). Run `.venv/bin/pytest tests/test_readme.py -q`, expect pass.

- [ ] **Step 8: Commit**

```bash
git add badger/mood_badger tests/fake_badgeware.py tests/test_app.py tests/test_app_tufty.py
git commit -m "feat: run Mood Badger on the Tufty 2350 with a dimming backlight"
```

---

### Task 4: Start-in-app boot file and Tufty-aware tools

**Files:**

- Create: `kiosk/start_in_app.py`
- Modify: `kiosk/main.py` (comment only: works on both badges; restore the stock file for that model)
- Modify: `tools/install.py`, `tools/badge_info.py`
- Modify: `.claude/skills/badge-deploy/SKILL.md` (replace the "Tufty 2350" section: Tufty is supported; `--start-in-app` is the normal Tufty setup; what HOME/RESET do), `.claude/skills/badge-firmware/SKILL.md` (Tufty section: after flashing a Tufty, offer badge-deploy with `--start-in-app`; `--with-filesystem` resets `main.py`, undoing it)
- Modify: `README.md` ("Using the install tools" table: `--start-in-app`; Tufty paragraph)
- Test: `tests/test_kiosk.py`, `tests/test_badge_tools.py`, `tests/test_readme.py`

**Interfaces:**

- Consumes: `vendor/tufty2350/firmware/main.py` (Task 1).
- Produces:
  - `install.APPS = {"badger": ROOT/"badger"/APP, "tufty": ROOT/"badger"/APP}`
  - `install.STOCK_MAINS = {"badger": ROOT/"vendor/badger2350/firmware/main.py", "tufty": ROOT/"vendor/tufty2350/firmware/main.py"}` (replaces `STOCK_MAIN`)
  - `install.START_IN_APP_MAIN = ROOT/"kiosk"/"start_in_app.py"`
  - `install.boot_mode(main_py: str) -> str`, one of `"kiosk"`, `"start-in-app"`, `"menu"`, `"custom"`. `"menu"` = equals a file in `STOCK_MAINS` after stripping trailing whitespace; `"start-in-app"` = contains `launch("/system/apps/mood_badger")` and `WAKE_WATCHDOG`; `"kiosk"` = contains the launch line without `WAKE_WATCHDOG`; else `"custom"`. Replaces `is_kiosk` everywhere.
  - CLI: `--kiosk`, `--start-in-app`, `--menu` mutually exclusive. `--start-in-app` on a non-Tufty model exits with "Start-in-app mode is for the Tufty 2350; the Badger already returns to Mood Badger after a wake. Nothing copied." before copying. The final line becomes `Start-up: <mode>`.
  - `badge_info`: `info["boot_mode"]` replaces `info["kiosk"]`; the report row is `("Start-up", ...)` with text `Mood Badger only (kiosk)`, `Mood Badger, HOME opens the menu (start-in-app)`, `Pimoroni menu`, or `custom main.py`.

`kiosk/start_in_app.py` (exact logic; Tufty `firmware/main.py` is the model for the menu branch):

```python
import powman

if powman.get_wake_reason() == powman.WAKE_WATCHDOG:
    badge.poll()  # eat the press that restarted the badge, as the stock main.py does
    app = launch("/system/apps/menu")
    if app is not None:
        while badge.pressed() or badge.held() or badge.released():
            badge.poll()
        launch(app)
else:
    launch("/system/apps/mood_badger")
reset()
```

- [ ] **Step 1: Write the failing tests**

In `tests/test_kiosk.py` (run the file with `runpy`, a fake `powman` in `sys.modules`, and fake `launch`, `reset`, `badge`):

- `test_start_in_app_opens_mood_badger_after_reset_or_power_on` — for each of `WAKE_RESET`, `WAKE_BUTTON_DOWN`, `WAKE_VBUS_DETECT`, `WAKE_UNKNOWN`: calls == `[("launch", "/system/apps/mood_badger"), ("reset",)]`, and `badge.poll` not called (the app ignores the waking press itself).
- `test_start_in_app_opens_menu_after_home` — `WAKE_WATCHDOG`, menu `launch` returns `"/system/apps/clock"`: calls == `[("launch", "/system/apps/menu"), ("launch", "/system/apps/clock"), ("reset",)]` and `badge.poll` was called before the first launch.
- `test_start_in_app_menu_returning_none_just_resets` — menu returns `None`: `[("launch", "/system/apps/menu"), ("reset",)]`.
- `test_start_in_app_menu_flow_matches_the_stock_tufty_main` — `vendor/tufty2350/firmware/main.py` still contains `launch("/system/apps/menu")` and `badge.pressed() or badge.held() or badge.released()` (guards against a firmware bump changing the flow we copied).

In `tests/test_badge_tools.py`:

- `test_boot_mode_of_each_known_file` — parametrize: `kiosk/main.py` → `"kiosk"`, `kiosk/start_in_app.py` → `"start-in-app"`, both `STOCK_MAINS` → `"menu"`.
- `test_boot_mode_reports_custom_main_py` — `'print("hi")\n'` → `"custom"`; the stock Badger file with an extra line appended → `"custom"`.
- `test_tufty_drive_installs_the_same_app` — `install.APPS["tufty"] == install.APPS["badger"]`; `model_for_drive(Path("/Volumes/TUFTY")) == "tufty"`.
- `test_menu_restores_the_stock_main_for_that_model` — `set_main(root, STOCK_MAINS["tufty"])` writes the Tufty file, not the Badger one (the two differ: assert they differ first).
- `test_start_in_app_refused_on_a_badger` — run `install.main()` with `sys.argv = ["install", "--dest", str(root), "--model", "badger", "--start-in-app"]` on a fake drive (as the existing CLI tests build one): `SystemExit` with the message above, and `apps/mood_badger` was not created.
- Update the existing kiosk tests to `boot_mode` and `STOCK_MAINS["badger"]`; update `badge_info` summary tests for `boot_mode` and the "Start-up" row.

In `tests/test_readme.py`: `--start-in-app` and `vendor/tufty2350/firmware/main.py` appear in `README.md`.

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_kiosk.py tests/test_badge_tools.py tests/test_readme.py -q`
Expected: FAIL (no `start_in_app.py`, no `boot_mode`).

- [ ] **Step 3: Implement** `kiosk/start_in_app.py`, the `install.py` and `badge_info.py` changes, then the README and skill edits listed under Files. `start_in_app.py` must also pass `mpy_cross`.

- [ ] **Step 4: Run all tests**

Run: `.venv/bin/pytest -q && .venv/bin/python -m mpy_cross -o /dev/null kiosk/start_in_app.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add kiosk tools tests README.md .claude/skills
git commit -m "feat: start-in-app boot file and Tufty support in the install tools"
```

---

### Task 5: Tufty in the simulator

**Files:**

- Move: `sim/wasm/micropython.{mjs,wasm}` → `sim/wasm/badger/`; add `sim/wasm/tufty/micropython.{mjs,wasm}`; update `sim/wasm/SOURCE.md` (both artifacts, same run 35841227054)
- Modify: `sim/stage.py`, `sim/boot.py`, `sim/index.html`, `sim/run_headless.mjs`, `tests/test_sim.py`, `CLAUDE.md` (Simulator line), `README.md` (simulator section)
- Create: `sim/dist/index.html` is generated, not committed (landing page with links to `badger/` and `tufty/`)

**Interfaces:**

- Produces:
  - `stage.stage(model: str) -> int` stages into `sim/dist/<model>/` from `vendor/<model>2350`, `sim/wasm/<model>/`; `python3 sim/stage.py` stages both and writes the landing page.
  - `node sim/run_headless.mjs --model <badger|tufty> --press <BUTTON> --frames <out.json>`; output adds `"width"` and `"height"`.
  - `index.html` sizes its canvas from the first `blitrgba(addr, w, h)` call (3x scale) and titles itself from `location.pathname` (Badger 2350 / Tufty 2350). One file serves both.

- [ ] **Step 1: Download the Tufty build and inspect its host contract**

```bash
mkdir -p sim/wasm/badger sim/wasm/tufty
git mv sim/wasm/micropython.mjs sim/wasm/micropython.wasm sim/wasm/badger/
gh run download -R pimoroni/badgeware-wasm 35841227054 -n badgeware-tufty2350-asyncify -D sim/wasm/tufty
```

Read the Tufty display shim in pimoroni/badgeware-wasm at commit `8cc5b05a1a07a823eb68ca1952b3603fe4d769bf` (`gh api repos/pimoroni/badgeware-wasm/contents/...?ref=8cc5b05`): confirm it calls `blitrgba(addr, w, h)` like the Badger's ssd1680 shim, what `display.backlight` does, and which `machine.Pin` names exist (`badge.py` reads `LIGHT_SENSE` on the Tufty). Record findings in `SOURCE.md`. If the contract differs, adapt `run_headless.mjs`/`index.html` to it; if `LIGHT_SENSE` is missing, add it in `sim/boot.py` the way `RTC_ALARM` is added today.

- [ ] **Step 2: Write the failing tests** in `tests/test_sim.py` (parametrize `run_sim(tmp_path, button, model="badger")`; Badger tests unchanged apart from the model argument):
- `test_tufty_boots_full_resolution_and_down_moves_to_next_mood` — `frames["width"], frames["height"] == 320, 240`; status `ok`; the "after" frame's pip 1 of 7 is filled at `moods.pip_positions(7, moods.TUFTY)[1]` (centre pixel dark) and pip 0 is not; the background pixel at `(5, 5)` is white.
- `test_tufty_set_arrows_drawn_and_c_moves_to_next_set` — dark pixels at the arrow centres `(TUFTY["arrow_a_x"] + 1, TUFTY["arrow_mid_y"])` and `(TUFTY["arrow_c_x"] - 1, TUFTY["arrow_mid_y"])`; pip 0 of 8 filled after C.
- `test_browser_page_never_uses_cached_app_files` stays (3 fetches, all `no-store`).

Frames on the Tufty are RGB; `run_headless.mjs` reduces each pixel to one grey byte (as the Badger path does with the red channel), so "dark" is `< 64` and "white" is `> 191`.

- [ ] **Step 3: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_sim.py -v`
Expected: Tufty tests FAIL (`--model` unknown).

- [ ] **Step 4: Implement** the staging, headless runner, page and boot changes. The Tufty runs at ~90 fps, so the headless runner takes "before" as the latest frame just before pressing (after at least 500 ms of frames) and "after" as the latest frame 500 ms after release, not frames 1 and 2. Keep the Badger's frame-count behaviour.

- [ ] **Step 5: Run all tests, then look at it**

Run: `.venv/bin/pytest -q`
Expected: all pass.
Then `python3 sim/stage.py && python3 -m http.server -d sim/dist 8000` and open `http://localhost:8000/tufty/`: picture centred and larger than on `/badger/`, label below, arrows above A and C, pips on the right. Take a screenshot for the PR.

- [ ] **Step 6: Commit**

```bash
git add sim tests/test_sim.py CLAUDE.md README.md
git commit -m "feat: run Mood Badger as a Tufty 2350 in the simulator"
```

---

### Task 6: Check on the real Tufty

Manual, with the user's hands on the badge; follow the `badge-firmware` and `badge-deploy` skills (background `--wait 180`, end the turn with the button instructions, "don't touch until Ejected / Flash complete").

- [ ] **Step 1:** `python3 -m tools.badge_info --port <the Tufty's port>`: model `tufty`, firmware "looks current" against tufty2350 v3.1.1. If not, flash `--firmware-only` with badge-firmware first.
- [ ] **Step 2:** Confirm the restart reasons the boot file depends on. After the user presses RESET once: `mpremote connect <port> exec "import powman; print(powman.get_wake_reason(), powman.WAKE_RESET)" reset` prints equal numbers. After the user opens any app from the menu and presses HOME: the same command prints `powman.WAKE_WATCHDOG`'s value (242). If either differs, stop and report; the boot file's rule is wrong.
- [ ] **Step 3:** Deploy: `python3 -m tools.install --wait 180 --start-in-app --eject` (double-tap RESET). Expect `Start-up: start-in-app` and "Ejected".
- [ ] **Step 4:** Verify the copy from the badge's side: `mpremote connect <port> exec "import os; print(sorted(os.listdir('/system/apps/mood_badger')))" reset` lists the same files as `badger/mood_badger` (no `__pycache__`, no `._` files).
- [ ] **Step 5:** The user checks by hand and reports: (a) badge opens in Mood Badger after RESET and after power-off/on (hold RESET until the case lights fade, then press a front button); (b) HOME opens the menu, and Mood Badger can be reopened from it; (c) full brightness, dims after ~10 s (about half on USB; about 15% on battery, unplugged); (d) a press on a dim screen only brightens, the next press changes the mood; (e) A and C change set, and the arrows sit above the A and C buttons (if not, adjust `TUFTY["arrow_a_x"]`/`["arrow_c_x"]` and redeploy); (f) the mood survives a RESET.
- [ ] **Step 6:** Record anything the hardware contradicted in the `badgeware-platforms` skill and commit:

```bash
git add .claude/skills/badgeware-platforms badger/mood_badger/moods.py tests
git commit -m "fix: align Tufty layout and notes with the real badge"
```

(Skip the commit if nothing changed.)
