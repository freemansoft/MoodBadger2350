# Mood Badger for Badger 2350 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port MoodBadger (Badger 2040) to a Badgeware app for the e-ink Pimoroni Badger 2350, installable from its home menu, with all references and install routes in `README.md`.

**Architecture:** A folder app, `badger/mood_badger/`, copied to `/apps` on the badge. Pure, CPython-testable logic lives in `moods.py`; `__init__.py` is a thin Badgeware layer tested against a fake runtime. A host-side Pillow tool generates the committed 4-grey PNGs from the MoodBadger JPEGs, which come from a pinned submodule.

**Tech Stack:** MicroPython on Badgeware firmware v3.1.1 (`pimoroni/badger2350`); Python 3.11, Pillow, pytest and mpy-cross on the host.

**Spec:** Inline. See Requirements and Verified Findings below; there is no separate spec document. Findings were read from `pimoroni/badger2350` at `v3.1.1` (`7f2fa36`), `pimoroni/badgeware-docs`, `simonpainter/MoodBadger` at `f22e70d`, `badger/home` and `badger/badger.github.io`.

## Requirements

1. New MicroPython app for the e-ink Badger 2350. Tufty and Blinky support may follow later, but none is built now.
2. At least two buttons move up and down through the mood images; a third cycles between image sets.
3. Port the MoodBadger images and behaviour, adapting to the 2350's different image and power-down support.
4. `README.md` holds all references and explains how to load the app and how the app store relates to it.
5. Upstream projects may be linked as submodules.

## Verified Findings

**Buttons.** All five front buttons (`BUTTON_A`, `B`, `C`, `UP`, `DOWN`) are free for apps. `BUTTON_HOME` (rear) is taken by the launcher through an IRQ set in `launch()`, which quits to the menu. RESET (rear) also returns to the menu: `main.py` checks `WAKE_RESET`.

**App store.** `badger.github.io` and `badger/home` target the GitHub Universe 2026 badge, a Tufty derivative with a 320×240 colour LCD and a different button API (`BUTTON_SELECT`, `BUTTON_BACK` and others). The site's 15 preinstalled apps are that badge's apps. The e-ink Badger ships `badge`, `clock`, `demos`, `gallery`, `hydrate`, `list`, `mass_storage`, `the_compendium`, `weather` and the `menu`. A catalog PR to `badger/home` is therefore not a route for this app, because that repo requires testing on Universe 2026 hardware. Whether the store's **Add local app** works with an e-ink badge's disk is unknown; Task 6 tests it.

**App distribution.** `pimoroni/badgeware-contrib` (MIT) is the community app repository for all three badges, and its `Badger/` folder is the e-ink equivalent of an app store. There is no installer: people copy a folder to `/apps` in disk mode, the same as a local install. Contributing is a PR adding `Badger/mood_badger/` with `__init__.py`, a 24×24 `icon.png` and a README for any extra instructions. Its CI lints Python with `ruff` from its `ci/` folder. App READMEs state the minimum firmware.

**Power.** `badge.sleep()` powers the RP2350 down and loses RAM, and a wake is a full reboot. `main.py` relaunches `state["running"]`, so the app restarts from the top. The docs say a wake returns to the menu, which disagrees with the v3.1.1 source; Task 6 confirms the behaviour. `wait_for_button_or_alarm(timeout=ms)` sleeps only when USB power is absent. The e-paper keeps its image through sleep, which is what the product needs.

**Waking press.** `_input.poll()` feeds the wake switches into `pressed` on the first poll only. `run()` makes that first poll just before the first `update()`. App code must not call `badge.poll()` or `badge.update()` before `run(update)`, or the waking press is lost.

**Framebuffer.** It lives in `.uninitialized_data`, so it holds garbage after a wake: the app must clear it before drawing. `badge.update()` also clears it afterwards, so every refresh draws the whole frame.

**Update modes.** In v3.1.1 `SSD1680::set_update_speed` is a stub that ignores its argument, so `FAST_UPDATE`, `MEDIUM_UPDATE` and `FULL_UPDATE` all use the same waveform. MoodBadger's TURBO refresh followed by a 3-second clean-up refresh has no equivalent and is dropped.

**Display.** 264×176 with four greys. `SSD1680::update` ORs the RGB channels and uses bits 7 and 6, so level bands are 0–63, 64–127, 128–191 and 192–255.

**Images.** `jpegdec` is not used here; PNG through `image.load` is the app convention. Stock apps ship both 8-bit RGBA and 8-bit colormap PNGs (`gallery/images/duck.png`). Upstream art is 115×128 (faces) and 100×100 (thumbs, weather).

**Sprite sheets are not used.** A wake draws exactly one image, so a sheet would decode every mood in a set to show one. Single PNGs are faster and smaller to load, and a caregiver can add a mood by dropping in a file, which upstream documents as a customisation feature.

**Simulators.** None of these has been run yet, so the app is tested with a fake runtime plus the real device unless a simulator task is added. `badgeware-wasm` has a `badger2350` variant with a simulated 264×176, 4-grey SSD1680 and is the closest match. It has no Badger release download: CI artifacts or an Emscripten build provide it. Its host page runs a demo, not the firmware, and it has no `powman` module, so it needs a small loader and stub. `badgeware-simulator` is a native desktop build on an older `io`-based API and needs a shim. `badgeware-web-simulator` and `badgeware-ide` state Tufty only. None models sleep, wake or refresh time.

**Licensing.** `simonpainter/MoodBadger` has no licence file. Its art is not cleared for redistribution until the author grants that.

## Global Constraints

- App folder name: `mood_badger` (the menu shows **Mood Badger**). State key: `"mood_badger"`.
- Minimum firmware: `v3.1.1`.
- `moods.py` and `__init__.py` must compile under `mpy-cross` and must not import `typing` or `dataclasses`.
- Screen layout: image cell 122×136 at (61, 2); label centred on x=122, top y=142, maximum width 236; pips 8×8 at x=250, spaced 10, from `y0 = (176 - count * 10) // 2`.
- Maximum 16 moods in a set, the most the pip column fits.
- Controls: `BUTTON_UP` is previous, `BUTTON_DOWN` is next (matching upstream `main.py`; upstream's README has them reversed), `BUTTON_B` is next set. `BUTTON_A` and `BUTTON_C` do nothing.
- Config keeps upstream's schema (`moods`, `initial`) with `.png` image names, and `initial` stays optional, as in upstream's README example.
- Generated PNGs are committed, so installing needs no tooling.
- Do not add a `LICENSE` file, push publicly or open a `badgeware-contrib` PR until the human partner has resolved Licensing above. That repo is MIT, so the art must be cleared first.

## Review Focus

1. **A press during an e-ink refresh:** it should still register, not vanish. Pinned by `test_press_during_refresh_is_not_dropped` (Task 3) and measured in Task 6.
2. **The press that wakes the badge:** one press moves exactly one mood, and it is not swallowed by the reboot. Pinned by `test_wake_press_moves_one_mood` (Task 3).
3. **Saved state left stale by a config edit:** a caregiver removes moods and the saved index no longer exists; the app should show a valid mood, not crash. Pinned by `test_restore_*` (Task 2) and `test_stale_state_recovers` (Task 3).
4. **A caregiver's typo in `config.json` or a missing PNG:** a bad config gives a readable error, and a missing image still shows the label. Pinned by `test_parse_rejects_*` (Task 2), `test_bad_config_reports_error` and `test_missing_image_still_draws_label` (Task 3).
5. **A long label on a child's badge:** it should stay on screen. Pinned by `test_long_label_uses_smaller_font` (Task 3).

---

### Task 1: Project setup and image pipeline

**Files:**
- Create: `.gitignore`, `requirements-dev.txt`, `.gitmodules`, `vendor/badger2350`, `vendor/MoodBadger`
- Create: `badger/mood_badger/config.json`, `badger/mood_badger/icon.png`, `badger/mood_badger/assets/*.png`
- Create: `tools/convert_moods.py`
- Test: `tests/test_convert_moods.py`, `tests/test_app_assets.py`
- Modify: `CLAUDE.md` (the intro now wrongly omits the `SessionStart` hook)

**Interfaces:**
- Produces: `tools.convert_moods.quantise(value: int) -> int`
- Produces: `tools.convert_moods.convert_image(src: Path, dst: Path, size: tuple[int, int]) -> None`
- Produces: `badger/mood_badger/config.json` and the PNGs it names

- [ ] **Step 1: Commit the existing project files and add dependencies**

Correct the `CLAUDE.md` intro to say a `SessionStart` hook installs the plugins. Then run:

```bash
git add .claude/settings.json CLAUDE.md docs/superpowers/plans
git commit -m "chore: add Claude Code plugin setup and port plan"
git submodule add https://github.com/pimoroni/badger2350 vendor/badger2350
git -C vendor/badger2350 checkout v3.1.1
git submodule add https://github.com/simonpainter/MoodBadger vendor/MoodBadger
git -C vendor/MoodBadger checkout f22e70d
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
```

`requirements-dev.txt` lists `pillow`, `pytest` and `mpy-cross`. `.gitignore` covers `.venv/`, `__pycache__/` and `.pytest_cache/`.

- [ ] **Step 2: Write the failing converter tests**

```python
@pytest.mark.parametrize("value,expected", [
    (0, 0), (63, 0), (64, 85), (127, 85), (128, 170), (191, 170), (192, 255), (255, 255),
])
def test_quantise_matches_firmware_bit_planes(value, expected):
    assert quantise(value) == expected

def test_output_has_cell_size_and_only_four_levels(tmp_path):
    # source: 100x100 RGB horizontal black-to-white gradient JPEG
    convert_image(src, dst, (122, 136))
    out = Image.open(dst)
    assert out.size == (122, 136) and out.mode == "P"
    assert {v for _, v in out.convert("L").getcolors()} <= {0, 85, 170, 255}

def test_square_source_keeps_aspect_and_is_centred(tmp_path):
    # source: solid black 100x100
    convert_image(src, dst, (122, 136))
    assert ImageOps.invert(Image.open(dst).convert("L")).getbbox() == (0, 7, 122, 129)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_convert_moods.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.convert_moods'`

- [ ] **Step 4: Implement `tools/convert_moods.py`**

`quantise` maps the four firmware bands to 0, 85, 170, 255. `convert_image` converts to L, applies `ImageOps.autocontrast`, scales with LANCZOS to fit `size` (scaling up as well as down, preserving aspect), centres on a white canvas, applies `quantise`, and saves as an 8-bit palettised PNG. `main()` reads `badger/mood_badger/config.json`, converts each distinct image from `vendor/MoodBadger/moods/<stem>.jpg` to `badger/mood_badger/assets/<stem>.png` at (122, 136), and writes `icon.png` at (24, 24) from `happy.jpg`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_convert_moods.py -v`
Expected: PASS

- [ ] **Step 6: Write `config.json`, generate assets and pin them with a test**

`config.json` keeps the upstream stem spellings in filenames and fixes the label spellings:

| Set | Entries (label, file) |
| --- | --- |
| 0 | Chilled `happy`; Sad `sad`; Bored `bored`; Annoyed `annoyed`; Angry `angry`; Embarrassed `embarassed`; Surprised `surprised`; Very Happy `very_happy` |
| 1 | Agree `thumb_up`; Disagree `thumb_down` |
| 2 | Clear `day_clear`; Part Cloudy `day_part_cloudy`; Rainy `day_rainy`; Storm `day_storm` |

`"initial": [0, 0, 0]`. Every file has a `.png` suffix. Upstream's duplicated third set exists only for its A/B/C shortcuts; the weather images replace it because cycling would otherwise show the same set twice.

```python
def test_every_configured_image_exists_at_cell_size(): ...  # 14 images, each 122x136, mode "P"
def test_icon_is_24_by_24(): ...
```

Run: `.venv/bin/python -m tools.convert_moods && .venv/bin/pytest tests/ -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add .gitignore .gitmodules requirements-dev.txt vendor tools tests badger
git commit -m "feat: convert MoodBadger art to 4-grey Badger 2350 PNGs"
```

---

### Task 2: Mood logic

**Files:**
- Create: `badger/mood_badger/moods.py`
- Test: `tests/test_moods.py`

**Interfaces:**
- Consumes: `config.json` schema from Task 1
- Produces, in `moods`:
  - `MAX_MOODS = 16`
  - `parse_config(text: str) -> dict` raises `ValueError`; the result always has a full, in-range `initial`
  - `restore(config: dict, saved: dict) -> tuple` returns `(set_index, mood_index)`
  - `apply_input(config: dict, set_index: int, mood_index: int, up: bool, down: bool, cycle: bool) -> tuple`
  - `pip_positions(count: int) -> list` of `(x, y)`

- [ ] **Step 1: Write the failing tests**

```python
CFG = {"moods": [[["A", "a.png"], ["B", "b.png"], ["C", "c.png"]], [["D", "d.png"], ["E", "e.png"]]],
       "initial": [0, 1]}

def test_down_advances_and_wraps():
    assert apply_input(CFG, 0, 0, False, True, False) == (0, 1)
    assert apply_input(CFG, 0, 2, False, True, False) == (0, 0)

def test_up_goes_back_and_wraps():
    assert apply_input(CFG, 0, 0, True, False, False) == (0, 2)

def test_up_and_down_together_cancel():
    assert apply_input(CFG, 0, 1, True, True, False) == (0, 1)

def test_cycle_moves_to_next_set_at_its_initial_mood_and_wraps():
    assert apply_input(CFG, 0, 2, False, False, True) == (1, 1)
    assert apply_input(CFG, 1, 0, False, False, True) == (0, 0)

def test_cycle_beats_up_and_down():
    assert apply_input(CFG, 0, 0, True, True, True) == (1, 1)

def test_single_set_cycle_returns_to_initial():
    # with one set, cycle gives (0, initial[0])

def test_restore_uses_saved_position():
    assert restore(CFG, {"set": 1, "mood": 0}) == (1, 0)

def test_restore_out_of_range_mood_falls_back_to_set_initial():
    assert restore(CFG, {"set": 1, "mood": 9}) == (1, 1)

def test_restore_out_of_range_set_falls_back_to_first_set():
    assert restore(CFG, {"set": 7, "mood": 0}) == (0, 0)

def test_restore_non_integer_values_fall_back():
    assert restore(CFG, {"set": "x", "mood": None}) == (0, 0)

def test_parse_defaults_missing_initial_to_zero():
    # {"moods": [[["A", "a.png"]], [["B", "b.png"]]]} gives initial == [0, 0]

def test_parse_replaces_out_of_range_initial_with_zero(): ...

@pytest.mark.parametrize("text", [
    "not json", "{}", '{"moods": []}', '{"moods": [[]]}', '{"moods": [[["only label"]]]}',
    '{"moods": [[["", "a.png"]]]}', '{"moods": [[[1, "a.png"]]]}',
])
def test_parse_rejects_bad_config(text):
    with pytest.raises(ValueError):
        parse_config(text)

def test_parse_rejects_set_with_too_many_moods():  # MAX_MOODS + 1 entries
    ...

def test_pip_positions_are_centred_for_eight():
    assert pip_positions(8) == [(250, 48 + i * 10) for i in range(8)]

def test_pip_positions_stay_on_screen_at_maximum():
    assert all(0 <= y and y + 8 <= 176 for _, y in pip_positions(MAX_MOODS))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_moods.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'moods'`. Add `badger/mood_badger` to `sys.path` in `tests/conftest.py`.

- [ ] **Step 3: Implement `badger/mood_badger/moods.py`**

Use only `json` from the standard library. Convert JSON decode failures to `ValueError` with a readable message, because MicroPython and CPython raise different types. `restore` keeps a valid set with an invalid mood, using that set's `initial`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_moods.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add badger/mood_badger/moods.py tests/test_moods.py tests/conftest.py
git commit -m "feat: add mood navigation, config parsing and state restore"
```

---

### Task 3: Badgeware app

**Files:**
- Create: `badger/mood_badger/__init__.py`
- Test: `tests/fake_badgeware.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: everything in `moods` from Task 2; `config.json` and `assets/` from Task 1
- Consumes Badgeware builtins: `screen`, `badge`, `image`, `color`, `font`, `shape`, `vec2`, `State`, `run`, `file_exists`, `wait_for_button_or_alarm`, `fatal_error`, `MEDIUM_UPDATE`, `NON_BLOCKING`, `BUTTON_UP`, `BUTTON_DOWN`, `BUTTON_B`
- Produces: `tests.fake_badgeware.run_app(ticks: list, saved: dict | None = None, config_text: str | None = None, files_missing: tuple = ()) -> Result`. `ticks` holds one set of pressed buttons per `update()` call. `Result` has `events: list` (in-order strings such as `"clear"`, `"save"`, `"display"`, `"wait"`), `blits: list` of image paths, `texts: list` of `(text, font)`, `saved: dict`, `mode: int`, `fatal: str | None`.

The app relies on `launch()` for `chdir` and `sys.path`, so all paths are relative. `run_app` copies the same behaviour with `os.chdir` to `badger/mood_badger`, then uses `runpy.run_path("__init__.py", init_globals=...)` with fakes. Its fake `run` calls `update` once per entry in `ticks`, and its fake `fatal_error` records the message and stops. Its `measure_text` returns 12 pixels per character for `font.ignore` and 7 for `font.smart`.

- [ ] **Step 1: Write the failing tests**

```python
def test_first_tick_draws_saved_mood_once():
    r = run_app([set()], saved={"set": 0, "mood": 2})
    assert r.events.count("display") == 1 and r.blits == ["assets/bored.png"]
    assert ("Bored", "ignore") in r.texts

def test_framebuffer_cleared_before_drawing():
    r = run_app([set()])
    assert r.events.index("clear") < r.events.index("blit")

def test_no_press_after_first_draw_does_not_refresh():
    assert run_app([set(), set(), set()]).events.count("display") == 1

def test_wake_press_moves_one_mood():
    # the press is already in `pressed` on tick 0, as after a wake
    r = run_app([{BUTTON_DOWN}], saved={"set": 0, "mood": 0})
    assert r.saved == {"set": 0, "mood": 1}
    assert r.blits == ["assets/sad.png"] and r.events.count("display") == 1

def test_state_saved_before_display_refresh():
    r = run_app([set(), {BUTTON_DOWN}])
    assert r.events.index("save") < r.events.index("display", r.events.index("display") + 1)

def test_b_cycles_set():
    r = run_app([set(), {BUTTON_B}], saved={"set": 0, "mood": 3})
    assert r.saved == {"set": 1, "mood": 0} and r.blits[-1] == "assets/thumb_up.png"

@pytest.mark.parametrize("button", [BUTTON_A, BUTTON_C, BUTTON_HOME])
def test_unmapped_buttons_do_not_refresh(button):
    assert run_app([set(), {button}]).events.count("display") == 1

def test_press_during_refresh_is_not_dropped():
    r = run_app([set(), {BUTTON_DOWN}, {BUTTON_DOWN}], saved={"set": 0, "mood": 0})
    assert r.mode & NON_BLOCKING
    assert r.saved == {"set": 0, "mood": 2}

def test_stale_state_recovers():
    assert run_app([set()], saved={"set": 9, "mood": 9}).blits == ["assets/happy.png"]

def test_app_never_polls_before_run():
    # the fake badge raises if poll() or update() runs before run(update)

def test_each_update_waits_with_sleep_timeout():
    # wait_for_button_or_alarm is called once per tick with timeout=5000

def test_missing_image_still_draws_label():
    r = run_app([set()], saved={"set": 0, "mood": 0}, files_missing=("assets/happy.png",))
    assert r.blits == [] and ("Chilled", "ignore") in r.texts

def test_bad_config_reports_error():
    assert "config.json" in run_app([set()], config_text="not json").fatal

def test_long_label_uses_smaller_font():
    r = run_app([set()], config_text='{"moods": [[["' + "W" * 25 + '", "happy.png"]]]}')
    assert r.texts[0][1] == "smart"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_app.py -v`
Expected: FAIL because `badger/mood_badger/__init__.py` does not exist

- [ ] **Step 3: Implement `badger/mood_badger/__init__.py`**

Module level, with no `badge.poll()` or `badge.update()`: read and parse `config.json`, calling `fatal_error("Mood Badger", ...)` with a message naming `config.json` on `OSError` or `ValueError`. Load state with `State.load("mood_badger", state)` and apply `moods.restore`. Call `badge.mode(MEDIUM_UPDATE | NON_BLOCKING)`. End with `run(update)`.

`update()` runs in this order:
1. `moods.apply_input` from `badge.pressed(...)`.
2. If the position changed, update state and `State.save`.
3. If it changed or `badge.first_update`, draw the frame, then `badge.update()`.
4. `wait_for_button_or_alarm(timeout=SLEEP_AFTER_MS)`, with `SLEEP_AFTER_MS = 5000`.

`draw()` clears with `screen.pen = color.white; screen.clear()`, blits the image at `vec2(61, 2)` if `file_exists`, draws the label, then the pips. The active pip is a filled `shape.rectangle`; the rest use `.stroke(1)`. The label uses `font.ignore`, or `font.smart` if `measure_text` exceeds 236. `MEDIUM_UPDATE` is chosen to match `gallery`, though v3.1.1 ignores it. `NON_BLOCKING` lets `wait_for_button_or_alarm` keep polling during a refresh.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Verify both app modules compile for MicroPython**

Run: `.venv/bin/python -m mpy_cross -o /dev/null badger/mood_badger/__init__.py && .venv/bin/python -m mpy_cross -o /dev/null badger/mood_badger/moods.py && echo OK`
Expected: `OK`

- [ ] **Step 6: Lint to `badgeware-contrib` standard**

Add `ruff` to `requirements-dev.txt`. `vendor/badger2350/ci/ruff.toml` declares the firmware's builtins; use it as the closest local match to the contrib CI.

Run: `.venv/bin/ruff check --config vendor/badger2350/ci/ruff.toml badger/mood_badger`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add requirements-dev.txt badger/mood_badger/__init__.py tests/fake_badgeware.py tests/test_app.py
git commit -m "feat: add Mood Badger app for Badger 2350"
```

---

### Task 4: Browser simulator (badgeware-wasm)

Runs the real firmware Python from `vendor/badger2350` and the unmodified app in `pimoroni/badgeware-wasm`'s Badger build. It checks layout, art, labels and navigation; it does not model sleep, wake, refresh time or e-paper contrast, so Task 6 is still required.

**Files:**
- Create: `sim/wasm/micropython.mjs`, `sim/wasm/micropython.wasm`, `sim/wasm/SOURCE.md` (artifact id, `badgeware-wasm` commit, MIT notice)
- Create: `sim/stage.py`, `sim/stubs/*.py`, `sim/boot.py`, `sim/index.html`, `sim/run_headless.mjs`
- Modify: `.gitignore` (adds `sim/dist/`)
- Test: `tests/test_sim.py`

**Interfaces:**
- Consumes: `badger/mood_badger/` from Tasks 1–3; `vendor/badger2350` at `v3.1.1`
- Produces: `python3 sim/stage.py` writes `sim/dist/` (a servable site: the host page, the wasm pair, and `fs/` plus `fs/manifest.json` listing every file to write into the MicroPython filesystem)
- Produces: `node sim/run_headless.mjs --press DOWN --frames out.json` boots the app, takes a frame, presses one button, takes a frame, and writes both frames' raw greyscale bytes and a status string

**Fixed decisions:**
- Use the `badgeware-badger2350-asyncify` CI artifact. It runs in Node and in every browser; `jspi` does not run in Node 18. The binaries are committed because the artifact expires on 2026-12-22. The fallback is `tools/build.sh badger2350 asyncify-fast` from `badgeware-wasm` with Emscripten.
- The filesystem copies the firmware layout: `vendor/badger2350/modules/common/badgeware/*.py` at `/.frozen/badgeware/`, `firmware/main.py` at `/system/main.py`, fonts from `romfs/fonts/` wherever the `picovector` font loader looks for them, and the app at `/system/apps/mood_badger/`.
- Sim-only code lives in `sim/` and never changes the app. `sim/stubs/` supplies the modules the wasm build lacks (at least `powman` and `pcf85063a`). `powman.sleep()` yields and returns: sleep is not modelled. VBUS reports connected, so the firmware never sleeps.
- `sim/boot.py` imports the badgeware package and then replaces `builtins.wait_for_button_or_alarm` with a copy that calls `time.sleep_ms(10)` each loop. The firmware version busy-waits, and in a single-threaded browser that starves key events. `boot.py` launches `/system/apps/mood_badger` directly, skipping the menu.
- `index.html` is adapted from `badgeware-wasm`'s `host/index.html`, keeping its `blitrgba`, `sim_buttons` and key map. Arrow keys are UP and DOWN; `a`, `b`, `c` and `h` are the other buttons. It shows the frame at 3× scale on a white background.

- [ ] **Step 1: Write the failing test**

```python
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

def test_app_boots_and_down_moves_to_next_mood(tmp_path):
    # runs stage.py, then run_headless.mjs --press DOWN --frames tmp_path/f.json
    first, second = frames["before"], frames["after"]
    assert frames["status"] == "ok"
    assert len(first) == 264 * 176
    assert set(first) <= {0, 85, 170, 255}
    assert any(v == 0 for v in first[: 264 * 140])      # image or label drew black
    assert first != second                                # DOWN changed the screen
    assert pip_filled(second, 1) and not pip_filled(second, 0)  # pip 1 now active
```

`pip_filled(frame, i)` checks the centre pixel of pip `i` for 8 moods (x=254, y=52+i*10) is black.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_sim.py -v`
Expected: FAIL because `sim/stage.py` does not exist

- [ ] **Step 3: Fetch and commit the wasm build**

Run: `gh run download -R pimoroni/badgeware-wasm -n badgeware-badger2350-asyncify -D sim/wasm` with the newest successful `main` run, then record the run's commit and artifact id in `sim/wasm/SOURCE.md`.
Expected: `sim/wasm/micropython.mjs` and `sim/wasm/micropython.wasm` exist

- [ ] **Step 4: Implement staging, stubs, boot, host page and headless runner**

Grow the stubs from the import errors the headless runner reports, one module at a time. Stop and report if the firmware needs a change to `vendor/` or the app to boot.

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_sim.py -v`
Expected: PASS

- [ ] **Step 6: Check it by eye in a browser**

Run: `python3 sim/stage.py && python3 -m http.server -d sim/dist 8000`, open `http://localhost:8000/`, and step through every mood and set.
Expected: matches the Task 3 layout. Record any surprises in the commit message.

- [ ] **Step 7: Commit**

```bash
git add .gitignore sim tests/test_sim.py
git commit -m "feat: run Mood Badger in the badgeware-wasm Badger simulator"
```

---

### Task 5: README and developer notes

**Files:**
- Create: `README.md`, `badger/mood_badger/README.md`
- Modify: `CLAUDE.md`
- Test: `tests/test_readme.py`

**Interfaces:**
- Consumes: controls, paths and firmware version from Global Constraints; findings from Verified Findings

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("required", [
    "https://badgewa.re", "https://badgewa.re/docs", "https://github.com/pimoroni/badger2350",
    "https://github.com/pimoroni/badgeware-docs", "https://github.com/simonpainter/MoodBadger",
    "https://badger.github.io/", "https://badger.github.io/apps/", "https://github.com/badger/home",
    "https://github.com/pimoroni/badgeware-contrib",
    "https://github.com/orgs/pimoroni/repositories?q=badgeware",
    "https://github.com/pimoroni/badgeware-simulator", "https://github.com/pimoroni/badgeware-web-simulator",
    "https://github.com/pimoroni/badgeware-wasm", "https://github.com/pimoroni/badgeware-ide",
    "https://github.com/pimoroni/badgeware-cpp", "https://github.com/pimoroni/badgeware-fonts",
    "https://github.com/pimoroni/picovector-micropython",
    "https://github.com/pimoroni/tufty2350", "https://github.com/pimoroni/blinky2350",
    "/apps/mood_badger", "v3.1.1",
])
def test_readme_contains_reference(required):
    assert required in Path("README.md").read_text()

def test_app_readme_states_controls_and_minimum_firmware():
    text = Path("badger/mood_badger/README.md").read_text()
    assert "v3.1.1" in text and "config.json" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_readme.py -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: Write `README.md` and update `CLAUDE.md`**

`README.md` sections:
1. **What it is:** purpose, credit to MoodBadger.
2. **Install:** double-tap RESET, the disk appears (Pimoroni's README calls it `Badger2350`, the docs say `BADGER`), copy `badger/mood_badger` into `apps` to give `/apps/mood_badger`, safely eject, press RESET.
3. **Controls:** a table including HOME and RESET, and a note that all five front buttons are app-usable.
4. **How power works:** draw, save, sleep after 5 seconds on battery, any front button wakes and acts, the image stays on the e-paper. Sleep does not happen on USB power.
5. **Customising:** the `config.json` schema, the 16-mood limit, regenerating assets with `tools/convert_moods.py`.
6. **Differences from MoodBadger (2040):** a table of screen, greys, PNG versus JPEG, no TURBO refresh, sleep and state storage, B cycling replacing A/B/C shortcuts, and sprite sheets not used and why.
7. **Sharing the app:** `badgeware-contrib` is the e-ink route. Cover the steps to contribute to `Badger/mood_badger/`: copy the app folder, add `icon.png` and its README, pass `ruff`, open a PR. Also say how others install from that repo.
8. **The app store:** that `badger.github.io` serves the Universe 2026 colour badge, what that means for this app, and why a `badger/home` catalog PR is not the route. A future Tufty port could use that route or `badgeware-contrib`'s `Tufty/` folder.
9. **Family and future:** Tufty and Blinky links, not yet supported.
10. **References:** every link in the test, plus `try.badgewa.re` and the firmware releases page. Group the Pimoroni repositories in this table and link the org search so new ones can be found:

| Repository | Use here |
| --- | --- |
| `badger2350` | E-ink firmware and stock apps; the source of truth for behaviour |
| `badgeware-docs` | Source of the `badgewa.re/docs` site |
| `badgeware-contrib` | Community apps; where to share Mood Badger |
| `badgeware-wasm` | WebAssembly simulator with a Badger variant |
| `badgeware-simulator` | Native desktop simulator |
| `badgeware-web-simulator` | Browser simulator at `try.badgewa.re`, Tufty only |
| `badgeware-ide` | Prototype browser IDE, Tufty only |
| `picovector-micropython` | Graphics engine behind `image`, `screen` and `shape` |
| `badgeware-fonts` | Builds fonts for Badgeware |
| `badgeware-cpp` | C++ alternative to MicroPython; not used here |
| `tufty2350`, `blinky2350` | Firmware for the other badges |

11. **Development:** venv, pytest, mpy-cross, ruff, submodule init, and running the simulator with what it does and does not model.

`badger/mood_badger/README.md` travels with the app, so it stands alone: what the app is, controls, how to edit `config.json`, and that it requires v3.1.1 or later firmware.

`CLAUDE.md`: add the test, compile and lint commands, and state that hardware behaviour must be read from `vendor/badger2350` because the docs can lag the source.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md tests/test_readme.py
git commit -m "docs: add README with install routes and references"
```

---

### Task 6: Hardware verification

Needs the human partner with a Badger 2350 on firmware v3.1.1 and battery power. The fake runtime cannot prove this task; do not mark it done from tests. Record each result in the commit message.

**Files:**
- Modify: `README.md` (only where results differ), `badger/mood_badger/__init__.py` (only if a timing fails)

**Interfaces:**
- Consumes: the installed app from Tasks 1–5

- [ ] **Step 1: Install and launch.** Follow the README exactly.
Expected: **Mood Badger** with its icon in the menu; the app opens on Chilled.

- [ ] **Step 2: Check rendering.** View all 14 moods.
Expected: images crisp, labels on screen, all labels readable at arm's length, pips correct. "Embarrassed" and "Part Cloudy" in `font.ignore` are the widest cases.

- [ ] **Step 3: Measure refresh time** with a stopwatch.
Expected: a refresh ends well inside the 5-second sleep timeout. If not, raise `SLEEP_AFTER_MS` to the measured time plus 3 seconds and update the test and README.

- [ ] **Step 4: Check sleep and wake on battery, with USB unplugged.** Wait 10 seconds, then press DOWN once.
Expected: the image stays visible through sleep; the badge reopens this app rather than the menu; it moves exactly one mood. If it opens the menu, stop and report, because the design relies on `main.py` relaunching `state["running"]`.

- [ ] **Step 5: Check input edges.** Press DOWN repeatedly during a refresh; press B through all sets; press HOME.
Expected: no crash; the final screen matches the saved state; B reaches all three sets and wraps; HOME returns to the menu.

- [ ] **Step 6: Check persistence.** Select a mood, press HOME, reopen the app, then press RESET and reopen.
Expected: the selected mood is restored both times.

- [ ] **Step 7: Check bad input.** Temporarily rename one PNG, separately replace one with a JPEG renamed to `.png`, and separately break `config.json` on the badge.
Expected: the label shows without its image in both image cases, and the app keeps working; a readable error names `config.json`. Restore the files.

- [ ] **Step 8: Try the store's Add local app.** Open `https://badger.github.io/apps/` and try **Open BADGER disk** with the e-ink badge in disk mode.
Expected: either result is acceptable. Record in the README's app store section whether it worked.

- [ ] **Step 9: Commit the results**

```bash
git add README.md badger/mood_badger/__init__.py tests/test_app.py
git commit -m "docs: record Badger 2350 hardware verification results"
```
