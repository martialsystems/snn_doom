#!/usr/bin/env node
// Copyright (c) 2026 Martial Systems LLC
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { DoomNet } from "./engine.js";

const dir = path.dirname(fileURLToPath(import.meta.url));
const pack = path.join(dir, "pack");
const meta = JSON.parse(fs.readFileSync(path.join(pack, "net.json"), "utf8"));
const raw = fs.readFileSync(path.join(pack, "net.bin"));
const buf = raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength);
const net = new DoomNet(meta, buf);
const t0 = Date.now();
net.reset(meta.spawn);
const tReset = Date.now() - t0;
const t1 = Date.now();
const out = net.tick(0);
const tTick = Date.now() - t1;
const st = net.readState();
const expectPath = path.join(pack, "expect_tick0.json");
if (!fs.existsSync(expectPath)) {
  console.log(JSON.stringify({ reset_ms: tReset, tick_ms: tTick, state: st, n: meta.n }));
  process.exit(0);
}
const expect = JSON.parse(fs.readFileSync(expectPath, "utf8"));
let pixMismatch = 0;
for (let i = 0; i < expect.pixels.length; i++) {
  if (out.pixels[i] !== expect.pixels[i]) pixMismatch += 1;
}
const poseKeys = ["px", "py", "ang", "ex", "ey", "enemy_alive", "hp", "ammo", "ex2", "ey2"];
const poseOk = poseKeys.every((k) => st[k] === expect.state[k]);
const report = {
  reset_ms: tReset,
  tick_ms: tTick,
  pixMismatch,
  poseOk,
  js: st,
  py: expect.state,
};
console.log(JSON.stringify(report));
if (!poseOk) process.exit(1);
