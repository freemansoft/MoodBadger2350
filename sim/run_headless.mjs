// Boot Mood Badger in a badgeware-wasm build under Node, capture a frame,
// press one button, capture a later frame, and write both as JSON.
//
//   node sim/run_headless.mjs [--model badger|tufty] --press DOWN --frames out.json
//
// Run python3 sim/stage.py first. Frames are width*height greyscale values
// (the output's "width" and "height"): the red channel on the Badger, whose
// e-ink is grey, and the mean of red, green and blue on the Tufty.
//
// The Badger only refreshes when the app asks, so "before" is its first frame
// and "after" the frame drawn after the press. The Tufty redraws every frame
// (~90 fps), so "before" is the latest frame once it has run for SETTLE_MS,
// and "after" the latest frame SETTLE_MS after the button is let go.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SIM = join(dirname(fileURLToPath(import.meta.url)), "dist");
const BUTTON = { HOME: 0x20, A: 0x10, B: 0x08, C: 0x04, UP: 0x02, DOWN: 0x01 };
const MODELS = ["badger", "tufty"];
const VBUS_DETECT = 12;
const RTC_ALARM = 13;
const TIMEOUT_MS = 60_000;
const SETTLE_MS = 500;

const args = process.argv.slice(2);
const option = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const model = option("--model") || "badger";
const press = option("--press");
const framesPath = option("--frames");
if (!MODELS.includes(model) || !press || !(press in BUTTON) || !framesPath) {
  console.error("usage: node sim/run_headless.mjs [--model badger|tufty] " +
                "--press <A|B|C|UP|DOWN|HOME> --frames <out.json>");
  process.exit(2);
}
const DIST = join(SIM, model);

// Only the first and the latest frame are kept: the Tufty draws hundreds.
let first = null;
let latest = null;
let count = 0;
let size = { width: 0, height: 0 };
let buttons = 0;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Host contract used by the simulator's ssd1680 (Badger) and st7789 (Tufty)
// shims: an RGBA framebuffer at addr, w*h pixels.
globalThis.blitrgba = (addr, w, h) => {
  const heap = globalThis.Module.HEAPU8;
  const grey = new Array(w * h);
  for (let i = 0; i < w * h; i++) {
    const p = addr + i * 4;
    grey[i] = model === "badger" ? heap[p] : Math.round((heap[p] + heap[p + 1] + heap[p + 2]) / 3);
  }
  if (first === null) first = grey;
  latest = grey;
  count += 1;
  size = { width: w, height: h };
};
globalThis.sim_buttons = () => buttons;
// Report USB power so the firmware never tries to sleep, and no RTC alarm.
globalThis.sim_gpio_get = (gpio) => (gpio === VBUS_DETECT || gpio === RTC_ALARM ? 1 : null);

function finish(status, code, before = first) {
  writeFileSync(framesPath, JSON.stringify({
    status, frames: count, ...size, before: before || [], after: latest || [],
  }));
  process.exit(code);
}

const { loadMicroPython } = await import(join(DIST, "micropython.mjs"));
const mp = await loadMicroPython({
  url: join(DIST, "micropython.wasm"),
  heapsize: 8 * 1024 * 1024,
  stdout: (line) => console.log(line),
  stderr: (line) => console.error(line),
});

const manifest = JSON.parse(readFileSync(join(DIST, "fs", "manifest.json"), "utf8"));
for (const [devicePath, local] of manifest) {
  mp.FS.mkdirTree(dirname(devicePath));
  mp.FS.writeFile(devicePath, readFileSync(join(DIST, "fs", local)));
}

const deadline = Date.now() + TIMEOUT_MS;
const running = mp.runPythonAsync(readFileSync(join(DIST, "boot.py"), "utf8"));
running.then(
  () => finish("app exited", 1),
  (error) => { console.error(String(error)); finish("error: " + error, 1); },
);

async function waitForFrames(n) {
  while (count < n) {
    if (Date.now() > deadline) finish("timeout waiting for frame " + n, 1);
    await sleep(20);
  }
}

await waitForFrames(1);
let before = first;
if (model !== "badger") {
  await sleep(SETTLE_MS);
  before = latest;
}
const pressedAt = count;
buttons = BUTTON[press];
await sleep(300);
buttons = 0;
if (model === "badger") {
  await waitForFrames(2);
} else {
  await sleep(SETTLE_MS);
  await waitForFrames(pressedAt + 2);
}
finish("ok", 0, before);
