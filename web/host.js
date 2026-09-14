// Copyright (c) 2026 Martial Systems LLC
// Host juice: keys, radar, dead, waves. Does not paint FRAME_READOUT.

const PALETTE = [
  [80, 140, 200],
  [90, 80, 60],
  [180, 180, 180],
  [200, 40, 40],
];

export function bitsFromKeys(held, fire, door) {
  let b = 0;
  if (held.has("left")) b |= 1;
  if (held.has("right")) b |= 2;
  if (held.has("up")) b |= 4;
  if (held.has("down")) b |= 8;
  if (fire) b |= 16;
  if (door) b |= 32;
  return b;
}

export function ingestKey(key) {
  if (!key) return [];
  const k = String(key).toLowerCase();
  if (k === "a" || k === "arrowleft") return ["left"];
  if (k === "d" || k === "arrowright") return ["right"];
  if (k === "w" || k === "arrowup") return ["up"];
  if (k === "s" || k === "arrowdown") return ["down"];
  if (k === " " || k === "space" || k === "f") return ["fire"];
  if (k === "e" || k === "q") return ["door"];
  if (k === "r") return ["restart"];
  if (k === "escape" || k === "esc") return ["quit"];
  return [k];
}

export function drawView(ctx, pixels, cols, rows, scale, headingCol) {
  const img = ctx.createImageData(cols * scale, rows * scale);
  const d = img.data;
  for (let y = 0; y < rows; y++) {
    for (let c = 0; c < cols; c++) {
      const col = PALETTE[pixels[y * cols + c] || 0];
      for (let dy = 0; dy < scale; dy++) {
        for (let dx = 0; dx < scale; dx++) {
          const i = ((y * scale + dy) * cols * scale + (c * scale + dx)) * 4;
          d[i] = col[0];
          d[i + 1] = col[1];
          d[i + 2] = col[2];
          d[i + 3] = 255;
        }
      }
    }
  }
  if (headingCol != null) {
    const x0 = headingCol * scale;
    for (let y = 0; y < rows * scale; y++) {
      for (let dx = 0; dx < Math.max(scale >> 3, 1); dx++) {
        const i = (y * cols * scale + x0 + dx) * 4;
        d[i] = 255;
        d[i + 1] = 220;
        d[i + 2] = 80;
      }
    }
  }
  ctx.putImageData(img, 0, 0);
}

function fillCell(data, w, cx, cy, cell, rgb) {
  const x0 = cx * cell;
  const y0 = cy * cell;
  for (let y = 0; y < cell; y++) {
    for (let x = 0; x < cell; x++) {
      const i = ((y0 + y) * w + (x0 + x)) * 4;
      data[i] = rgb[0];
      data[i + 1] = rgb[1];
      data[i + 2] = rgb[2];
      data[i + 3] = 255;
    }
  }
}

function stamp(data, w, h, wx, wy, scale, rgb, r) {
  const x = wx * scale;
  const y = wy * scale;
  for (let dy = -r; dy <= r; dy++) {
    for (let dx = -r; dx <= r; dx++) {
      const xx = x + dx;
      const yy = y + dy;
      if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
      const i = (yy * w + xx) * 4;
      data[i] = rgb[0];
      data[i + 1] = rgb[1];
      data[i + 2] = rgb[2];
      data[i + 3] = 255;
    }
  }
}

export function drawRadar(ctx, meta, mapBits, st, door) {
  const scale = 2;
  const size = 128 * scale;
  const cell = meta.cell * scale;
  const img = ctx.createImageData(size, size);
  const d = img.data;
  d.fill(0);
  for (let i = 3; i < d.length; i += 4) d[i] = 255;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      d[i] = 16;
      d[i + 1] = 16;
      d[i + 2] = 16;
    }
  }
  for (let i = 0; i < 64; i++) {
    if ((mapBits >>> i) & 1) fillCell(d, size, i % 8, (i / 8) | 0, cell, [36, 36, 36]);
  }
  fillCell(d, size, meta.door_x, meta.door_y, cell, door ? [170, 110, 40] : [40, 80, 90]);
  const px = st.px;
  const py = st.py;
  const ang = st.ang % meta.n_ang;
  const x0 = px * scale;
  const y0 = py * scale;
  const half = meta.fov_half;
  for (let da = -half; da < half; da++) {
    const a = (ang + da + meta.n_ang) % meta.n_ang;
    const x1 = x0 + meta.cos[a] * 8;
    const y1 = y0 + meta.sin[a] * 8;
    const rgb = da === 0 ? [255, 220, 60] : [70, 70, 30];
    line(d, size, x0, y0, x1, y1, rgb);
  }
  if (st.enemy_alive) stamp(d, size, size, st.ex, st.ey, scale, [220, 60, 60], 3);
  else stamp(d, size, size, st.ex, st.ey, scale, [80, 30, 30], 2);
  if (st.enemy2_alive) stamp(d, size, size, st.ex2, st.ey2, scale, [230, 160, 40], 3);
  else stamp(d, size, size, st.ex2, st.ey2, scale, [90, 60, 20], 2);
  stamp(d, size, size, px, py, scale, [80, 220, 80], 3);
  ctx.putImageData(img, 0, 0);
}

function line(data, w, x0, y0, x1, y1, rgb) {
  x0 |= 0;
  y0 |= 0;
  x1 |= 0;
  y1 |= 0;
  let dx = Math.abs(x1 - x0);
  let dy = -Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1;
  const sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for (;;) {
    if (x0 >= 0 && y0 >= 0 && x0 < w && y0 < w) {
      const i = (y0 * w + x0) * 4;
      data[i] = rgb[0];
      data[i + 1] = rgb[1];
      data[i + 2] = rgb[2];
      data[i + 3] = 255;
    }
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) {
      err += dy;
      x0 += sx;
    }
    if (e2 <= dx) {
      err += dx;
      y0 += sy;
    }
  }
}

export function freeCells(mapBits, st, door, meta) {
  const pc = [st.px >> 4, st.py >> 4];
  const e2 = [st.ex2 >> 4, st.ey2 >> 4];
  const base = [];
  for (let cy = 0; cy < 8; cy++) {
    for (let cx = 0; cx < 8; cx++) {
      if ((mapBits >>> (cy * 8 + cx)) & 1) continue;
      if (cx === pc[0] && cy === pc[1]) continue;
      if (cx === e2[0] && cy === e2[1]) continue;
      if (cx === meta.door_x && cy === meta.door_y && door) continue;
      base.push([cx, cy]);
    }
  }
  const blocked = new Set();
  const ang = st.ang % meta.n_ang;
  const half = meta.fov_half;
  for (let da = -half; da < half; da++) {
    const a = (ang + da + meta.n_ang) % meta.n_ang;
    let x = st.px;
    let y = st.py;
    for (let s = 0; s < meta.max_dist; s++) {
      x += meta.cos[a];
      y += meta.sin[a];
      const cx = x >> 4;
      const cy = y >> 4;
      if (cx < 0 || cy < 0 || cx >= 8 || cy >= 8) break;
      if (cx === pc[0] && cy === pc[1]) continue;
      blocked.add(cx + "," + cy);
      if ((mapBits >>> (cy * 8 + cx)) & 1) break;
    }
  }
  const off = base.filter((c) => !blocked.has(c[0] + "," + c[1]));
  if (off.length) return off;
  return base;
}

export function cellCenter(cx, cy, cell) {
  return [cx * cell + (cell >> 1), cy * cell + (cell >> 1)];
}
