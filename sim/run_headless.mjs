// Boot Mood Badger in the badgeware-wasm Badger build under Node, capture a
// frame, press one button, capture the next frame, and write both as JSON.
//
//   node sim/run_headless.mjs --press DOWN --frames out.json
//
// Run python3 sim/stage.py first. Frames are 264*176 greyscale values.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DIST = join(dirname(fileURLToPath(import.meta.url)), "dist");
const BUTTON = { HOME: 0x20, A: 0x10, B: 0x08, C: 0x04, UP: 0x02, DOWN: 0x01 };
const VBUS_DETECT = 12;
const RTC_ALARM = 13;
const TIMEOUT_MS = 60_000;

const args = process.argv.slice(2);
const option = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const press = option("--press");
const framesPath = option("--frames");
if (!press || !(press in BUTTON) || !framesPath) {
  console.error("usage: node sim/run_headless.mjs --press <A|B|C|UP|DOWN|HOME> --frames <out.json>");
  process.exit(2);
}

const frames = [];
let buttons = 0;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Host contract used by the simulator's ssd1680 and machine shims.
globalThis.blitrgba = (addr, w, h) => {
  const heap = globalThis.Module.HEAPU8;
  const grey = new Array(w * h);
  for (let i = 0; i < w * h; i++) grey[i] = heap[addr + i * 4];
  frames.push(grey);
};
globalThis.sim_buttons = () => buttons;
// Report USB power so the firmware never tries to sleep, and no RTC alarm.
globalThis.sim_gpio_get = (gpio) => (gpio === VBUS_DETECT || gpio === RTC_ALARM ? 1 : null);

function finish(status, code) {
  const before = frames[0] || [];
  const after = frames[frames.length - 1] || [];
  writeFileSync(framesPath, JSON.stringify({ status, frames: frames.length, before, after }));
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

async function waitForFrames(count) {
  while (frames.length < count) {
    if (Date.now() > deadline) finish("timeout waiting for frame " + count, 1);
    await sleep(20);
  }
}

await waitForFrames(1);
buttons = BUTTON[press];
await sleep(300);
buttons = 0;
await waitForFrames(2);
finish("ok", 0);
