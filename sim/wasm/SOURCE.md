# badgeware-wasm builds

`badger/` and `tufty/` each hold `micropython.mjs` and `micropython.wasm`: the
`badgeware-badger2350-asyncify` and `badgeware-tufty2350-asyncify` CI
artifacts from [pimoroni/badgeware-wasm](https://github.com/pimoroni/badgeware-wasm),
from the same run, committed here because GitHub deletes CI artifacts after
90 days. They run with the firmware Python from `vendor/badger2350` and
`vendor/tufty2350`.

`VERSION.json` is the machine-readable pin (build commit, run and date, and
each badge's firmware tag) that `tools/update_sim.py` reads and writes. This
file is the record for people; `tests/test_update_sim.py` checks that the two
name the same build.

|                 |                                            |
| --------------- | ------------------------------------------ |
| Commit          | `8cc5b05a1a07a823eb68ca1952b3603fe4d769bf` |
| Workflow run    | `35841227054` (2026-09-23)                 |
| Badger artifact | `10740953689`, expires 2026-12-22          |
| Tufty artifact  | `10741935374`, expires 2026-12-22          |
| Firmware        | `v3.1.1` (Badger and Tufty submodules)     |
| Licence         | MIT, Copyright (c) Pimoroni Ltd            |

## Checking for and pulling newer builds

With the GitHub CLI logged in (`gh auth login`), from the repository root:

```sh
python3 -m tools.update_sim --check   # pinned vs latest; exits 1 if newer
python3 -m tools.update_sim           # download the newest builds, move the submodules
```

The update downloads both builds and checks out the latest firmware tag in
each submodule, and only then replaces `badger/`, `tufty/` and
`VERSION.json`; if anything fails first, nothing here changes. Afterwards,
update the table above (commit, run, artifact ids from
`gh run view <run-id> -R pimoroni/badgeware-wasm`), recheck the host contract
below, run `.venv/bin/pytest`, and commit `sim/wasm` and `vendor/`.

To do it by hand, download newer artifacts:

```sh
gh run download -R pimoroni/badgeware-wasm <run-id> -n badgeware-badger2350-asyncify -D sim/wasm/badger
gh run download -R pimoroni/badgeware-wasm <run-id> -n badgeware-tufty2350-asyncify -D sim/wasm/tufty
```

Or build them with the Emscripten SDK from a `badgeware-wasm` checkout:

```sh
tools/build.sh badger2350 asyncify-fast
tools/build.sh tufty2350 asyncify-fast
```

The `asyncify` builds are used because they run in Node as well as every
browser; the `jspi` builds do not run in Node 18.

## Host contract (checked at the commit above)

Both builds call the same host functions, which `sim/index.html` and
`sim/run_headless.mjs` provide:

- `blitrgba(addr, w, h)`: an RGBA framebuffer in `Module.HEAPU8`, on every
  display update. The Badger's `ssd1680` shim sends 264x176; the Tufty's
  `st7789` shim sends 160x120 or, after `badge.mode(HIRES)`, 320x240.
- `backlight(value)` (optional, Tufty only): `display.backlight(0..1)`.
- `sim_buttons()`: pressed buttons as an active-high bitmask.
- `sim_gpio_get(gpio)`: VBUS_DETECT (12) and RTC_ALARM (13) are read here.

The `machine` shim (`simulator/modules/machine.py`) maps the Tufty's pin names,
including `LIGHT_SENSE`, which the Tufty's `badge.py` reads at import.
