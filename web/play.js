// Copyright (c) 2026 Martial Systems LLC
import { bitsFromKeys, cellCenter, drawRadar, drawView, freeCells, ingestKey } from "./host.js";

const SCALE = 32;
const held = new Set();
let fire = false;
let door = false;
let dead = false;
let restart = false;
let score = 0;
let e1Was = 1;
let coolE1 = 0;
let busy = false;
let meta = null;
let spawn = null;
let last = null;

const worker = new Worker("./worker.js", { type: "module" });
const view = document.getElementById("view");
const radar = document.getElementById("radar");
const hud = document.getElementById("hud");
const splash = document.getElementById("splash");
const status = document.getElementById("status");
const vctx = view.getContext("2d");
const rctx = radar.getContext("2d");

function setStatus(t) {
  status.textContent = t;
}

worker.onmessage = (ev) => {
  const msg = ev.data;
  last = msg;
  busy = false;
  if (!meta) return;
  if (msg.type === "ready") {
    setStatus("LIF ready. 7,973 units.");
    paint(msg);
    return;
  }
  if (msg.state && e1Was && !msg.state.enemy_alive) {
    score += 1;
    coolE1 = 1;
  }
  e1Was = msg.state ? msg.state.enemy_alive : e1Was;
  if (msg.state && msg.state.hp <= 0) dead = true;
  if (!dead && coolE1) {
    coolE1 -= 1;
    if (coolE1 === 0 && msg.state && !msg.state.enemy_alive) {
      const cells = freeCells(msg.map_bits, msg.state, msg.door, meta);
      if (cells.length) {
        const pick = cells[(Math.random() * cells.length) | 0];
        const [ex, ey] = cellCenter(pick[0], pick[1], meta.cell);
        const st = { ...msg.state, ex, ey, enemy_alive: 1, map_bits: msg.map_bits };
        busy = true;
        worker.postMessage({ type: "reset", state: st });
        e1Was = 1;
        paint(msg);
        splash.classList.toggle("on", dead);
        return;
      }
    }
  }
  paint(msg);
  splash.classList.toggle("on", dead);
  if (msg.ms) setStatus(`${(1000 / Math.max(msg.ms, 1)).toFixed(1)} ticks/sec · ${msg.n} LIF`);
};

function paint(msg) {
  if (!msg.pixels || !meta) return;
  drawView(vctx, msg.pixels, meta.n_cols, meta.frame_h, SCALE, meta.center_col);
  drawRadar(rctx, meta, msg.map_bits, msg.state, msg.door);
  const st = msg.state;
  hud.textContent =
    `px ${st.px} py ${st.py} ang ${st.ang}  e1 ${st.ex},${st.ey} ${st.enemy_alive}  e2 ${st.ex2},${st.ey2} ${st.enemy2_alive}\n` +
    `ammo ${st.ammo} hp ${st.hp} score ${score} door ${msg.door} hs ${msg.hitscan} shot ${msg.shot}`;
}

function tick() {
  if (busy || !meta) return;
  if (restart) {
    dead = false;
    restart = false;
    score = 0;
    e1Was = 1;
    coolE1 = 0;
    held.clear();
    fire = false;
    door = false;
    splash.classList.remove("on");
    busy = true;
    worker.postMessage({ type: "reset", state: { ...spawn } });
    return;
  }
  const bits = dead ? 0 : bitsFromKeys(held, fire, door);
  fire = false;
  door = false;
  busy = true;
  worker.postMessage({ type: "tick", bits });
}

function onDown(e) {
  const toks = ingestKey(e.key);
  if (toks.includes("quit")) return;
  if (dead && toks.includes("restart")) {
    restart = true;
    tick();
    return;
  }
  if (dead) return;
  for (const t of toks) {
    if (t === "fire") fire = true;
    else if (t === "door") door = true;
    else if (t === "left" || t === "right" || t === "up" || t === "down") held.add(t);
  }
  e.preventDefault();
}

function onUp(e) {
  const toks = ingestKey(e.key);
  for (const t of toks) held.delete(t);
}

window.addEventListener("keydown", onDown);
window.addEventListener("keyup", onUp);
document.getElementById("restart").onclick = () => {
  restart = true;
  tick();
};
document.querySelectorAll("[data-k]").forEach((btn) => {
  const send = (on) => {
    const t = btn.getAttribute("data-k");
    if (t === "fire") fire = true;
    else if (t === "door") door = true;
    else if (on) held.add(t);
    else held.delete(t);
  };
  btn.addEventListener("pointerdown", (e) => {
    send(true);
    e.preventDefault();
  });
  btn.addEventListener("pointerup", () => send(false));
  btn.addEventListener("pointerleave", () => send(false));
});

setStatus("Loading 7,973 LIF stitch…");
fetch("./pack/net.json")
  .then((r) => r.json())
  .then((m) => {
    meta = m;
    spawn = { ...m.spawn };
    view.width = m.n_cols * SCALE;
    view.height = m.frame_h * SCALE;
    radar.width = 256;
    radar.height = 256;
    worker.postMessage({ type: "load", jsonUrl: "./pack/net.json", binUrl: "./pack/net.bin" });
  })
  .catch((err) => setStatus("load failed: " + err));

setInterval(tick, 50);
