// Copyright (c) 2026 Martial Systems LLC
import { DoomNet } from "./engine.js";

let net = null;

self.onmessage = async (ev) => {
  const msg = ev.data;
  if (msg.type === "load") {
    const meta = await (await fetch(msg.jsonUrl)).json();
    const buf = await (await fetch(msg.binUrl)).arrayBuffer();
    net = new DoomNet(meta, buf);
    net.reset(meta.spawn);
    postResult("ready", 0);
    return;
  }
  if (!net) return;
  if (msg.type === "reset") {
    net.reset(msg.state);
    postResult("reset", 0);
    return;
  }
  if (msg.type === "tick") {
    const t0 = performance.now();
    net.tick(msg.bits);
    postResult("tick", performance.now() - t0);
  }
};

function postResult(type, ms) {
  const pixels = net.decodePixels().slice();
  self.postMessage({
    type,
    ms,
    pixels,
    state: net.readState(),
    map_bits: net.readMapBits(),
    door: net.readDoor(),
    hitscan: net.readHitscan(),
    shot: net.readShot(),
    n: net.n,
  });
}
