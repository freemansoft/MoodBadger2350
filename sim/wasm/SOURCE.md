# badgeware-wasm Badger build

`micropython.mjs` and `micropython.wasm` are the `badgeware-badger2350-asyncify`
CI artifact from [pimoroni/badgeware-wasm](https://github.com/pimoroni/badgeware-wasm),
committed here because GitHub deletes CI artifacts after 90 days.

| | |
| --- | --- |
| Commit | `8cc5b05a1a07a823eb68ca1952b3603fe4d769bf` |
| Workflow run | `35841227054` (2026-09-23) |
| Artifact | `10740953689`, expires 2026-12-22 |
| Licence | MIT, Copyright (c) Pimoroni Ltd |

To replace them, download a newer artifact:

```sh
gh run download -R pimoroni/badgeware-wasm <run-id> -n badgeware-badger2350-asyncify -D sim/wasm
```

Or build them with the Emscripten SDK from a `badgeware-wasm` checkout:

```sh
tools/build.sh badger2350 asyncify-fast
```

The `asyncify` build is used because it runs in Node as well as every browser;
the `jspi` build does not run in Node 18.
