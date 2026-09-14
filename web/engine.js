// Copyright (c) 2026 Martial Systems LLC
// Browser LIF host. Same discrete equation as snn_doom.snn.lif (tau=0).
export const AMP = 1.2;

function readBit(spikes, rail) {
  const t = spikes[rail[0]];
  const f = spikes[rail[1]];
  if (t >= 1 && f < 1) return 1;
  if (f >= 1 && t < 1) return 0;
  return t > f ? 1 : 0;
}

function readInt(spikes, rails) {
  let v = 0;
  for (let i = 0; i < rails.length; i++) v |= readBit(spikes, rails[i]) << i;
  return v;
}

function driveBit(cur, rail, value, amp = AMP) {
  if (value) {
    cur[rail[0]] = amp;
    cur[rail[1]] = 0;
  } else {
    cur[rail[0]] = 0;
    cur[rail[1]] = amp;
  }
}

function driveInt(cur, rails, value, amp = AMP) {
  for (let i = 0; i < rails.length; i++) driveBit(cur, rails[i], (value >> i) & 1, amp);
}

export class DoomNet {
  constructor(meta, buf) {
    this.meta = meta;
    this.n = meta.n;
    const nnz = meta.nnz;
    let o = 0;
    this.indptr = new Int32Array(buf, o, this.n + 1);
    o += (this.n + 1) * 4;
    this.indices = new Int32Array(buf, o, nnz);
    o += nnz * 4;
    this.csrW = new Float32Array(buf, o, nnz);
    o += nnz * 4;
    this.thresh = new Float32Array(buf, o, this.n);
    this.spikes = new Uint8Array(this.n);
    this.I = new Float32Array(this.n);
    this.pixels = new Uint8Array(meta.frame_h * meta.n_cols);
  }

  zeroSpikes() {
    this.spikes.fill(0);
  }

  stepN(nSteps, current) {
    const n = this.n;
    const spikes = this.spikes;
    const I = this.I;
    const thresh = this.thresh;
    const indptr = this.indptr;
    const indices = this.indices;
    const csrW = this.csrW;
    let acc = 0;
    for (let step = 0; step < nSteps; step++) {
      I.set(current);
      for (let src = 0; src < n; src++) {
        if (spikes[src] === 0) continue;
        const a = indptr[src];
        const b = indptr[src + 1];
        const s = spikes[src];
        for (let e = a; e < b; e++) {
          const d = indices[e];
          I[d] = Math.fround(I[d] + Math.fround(csrW[e] * s));
        }
      }
      for (let j = 0; j < n; j++) {
        if (I[j] >= thresh[j]) {
          spikes[j] = 1;
          acc += 1;
        } else spikes[j] = 0;
      }
    }
    return acc / Math.max(nSteps, 1);
  }

  inputCurrent(bits) {
    const cur = new Float32Array(this.n);
    const m = this.meta;
    cur[m.bias] = AMP;
    for (let i = 0; i < m.in_rails.length; i++) {
      driveBit(cur, m.in_rails[i], (bits >> i) & 1);
    }
    return cur;
  }

  driveState(cur, st) {
    const m = this.meta;
    cur[m.bias] = AMP;
    driveInt(cur, m.px, st.px);
    driveInt(cur, m.py, st.py);
    driveInt(cur, m.ang, st.ang);
    driveInt(cur, m.ex, st.ex);
    driveInt(cur, m.ey, st.ey);
    driveBit(cur, m.enemy_alive, st.enemy_alive);
    driveBit(cur, m.player_hit, st.player_hit);
    driveInt(cur, m.ex2, st.ex2);
    driveInt(cur, m.ey2, st.ey2);
    driveBit(cur, m.enemy2_alive, st.enemy2_alive);
    driveInt(cur, m.ammo, st.ammo);
    driveInt(cur, m.hp, st.hp);
    driveBit(cur, m.pickup_alive, st.pickup_alive);
    for (let i = 0; i < m.ram_cells.length; i++) {
      driveBit(cur, m.ram_cells[i], (st.map_bits >> i) & 1);
    }
  }

  reset(st) {
    this.zeroSpikes();
    const cur = new Float32Array(this.n);
    this.driveState(cur, st);
    this.stepN(6, cur);
    const kick = new Float32Array(this.n);
    kick[this.meta.bias] = AMP;
    for (const k of this.meta.kick) kick[k] = AMP;
    this.stepN(1, kick);
  }

  tick(bits) {
    const cur = this.inputCurrent(bits);
    const sps = this.stepN(this.meta.steps_per_tick, cur);
    return { pixels: this.decodePixels(), spikesPerStep: sps };
  }

  decodePixels() {
    const m = this.meta;
    const pix = this.pixels;
    const spikes = this.spikes;
    const cols = m.n_cols;
    const h = m.frame_h;
    const nc = m.n_colors;
    const P = m.pixels;
    for (let c = 0; c < cols; c++) {
      for (let y = 0; y < h; y++) {
        let best = 0;
        let bi = 0;
        const cell = P[c][y];
        for (let k = 0; k < nc; k++) {
          const v = spikes[cell[k]];
          if (v > best) {
            best = v;
            bi = k;
          }
        }
        pix[y * cols + c] = bi;
      }
    }
    return pix;
  }

  readState() {
    const s = this.spikes;
    const m = this.meta;
    return {
      px: readInt(s, m.px),
      py: readInt(s, m.py),
      ang: readInt(s, m.ang),
      ex: readInt(s, m.ex),
      ey: readInt(s, m.ey),
      enemy_alive: readBit(s, m.enemy_alive),
      player_hit: readBit(s, m.player_hit),
      ex2: readInt(s, m.ex2),
      ey2: readInt(s, m.ey2),
      enemy2_alive: readBit(s, m.enemy2_alive),
      ammo: readInt(s, m.ammo),
      hp: readInt(s, m.hp),
      pickup_alive: readBit(s, m.pickup_alive),
    };
  }

  readMapBits() {
    const s = this.spikes;
    let bits = 0;
    const cells = this.meta.ram_cells;
    for (let i = 0; i < cells.length; i++) {
      if (readBit(s, cells[i])) bits |= 1 << i;
    }
    return bits >>> 0;
  }

  readDoor() {
    return readBit(this.spikes, this.meta.ram_cells[this.meta.door_idx]);
  }

  readHitscan() {
    return readBit(this.spikes, this.meta.sprite_cols[this.meta.center_col]);
  }

  readShot() {
    return this.spikes[this.meta.shot] >= 1 ? 1 : 0;
  }
}

export async function loadPack(base = ".") {
  const meta = await (await fetch(`${base}/net.json`)).json();
  const buf = await (await fetch(`${base}/net.bin`)).arrayBuffer();
  return new DoomNet(meta, buf);
}
