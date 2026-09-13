# Copyright (c) 2026 Martial Systems LLC
"""Stitched Doom SNN: host injects keys, steps a fixed LIF budget, reads pixels.

CLOCK is a SETTLE-period ring. SEQUENCER is gated pose/column/march rings.
The datapath (REG, ALU, RAM, RAY, READOUT) computes the teacher tick.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from snn_doom.const import (
    AMMO_BITS,
    CENTER_COL,
    COS,
    DEATH_TICKS,
    DOOR_IDX,
    FOV_HALF,
    FRAME_H,
    MARCH_LEN,
    MOVE_DIV,
    N_ANG,
    N_COLS,
    N_COLORS,
    N_INPUT_BITS,
    SETTLE_STEPS,
    SIN,
    STEPS_PER_TICK,
    V1_NEURON_CAP,
)
from snn_doom.modules.alu import add_adder, add_gt
from snn_doom.modules.latch import add_reg, add_write
from snn_doom.modules.ram import add_ram1
from snn_doom.modules.readout import build_fixed_readout
from snn_doom.snn.digital import (
    W_FORCE,
    W_HOLD,
    W_INH,
    Rail,
    and2,
    and3,
    bistable,
    decoder_bits,
    gated_ring,
    latch_write,
    mux_int,
    or_n,
    oscillator_ring,
)
from snn_doom.snn.io import drive_bit, drive_index, drive_int, read_bit, read_int, zeros
from snn_doom.snn.lif import LifNet, NetBuilder
from snn_doom.teacher.state import GameState, unpack_input


def _const_int(b: NetBuilder, value: int, width: int, name: str, module: str, bias: int) -> list[Rail]:
    rails: list[Rail] = []
    for i in range(width):
        t, f = b.alloc_pair(f"{name}_{i}", module)
        if (value >> i) & 1:
            b.wire(bias, t, 1.2)
        else:
            b.wire(bias, f, 1.2)
        rails.append(Rail(t, f))
    return rails


def _rom(b: NetBuilder, dec: list[int], table: tuple[int, ...], width: int, name: str, module: str) -> list[Rail]:
    rails = [Rail(*b.alloc_pair(f"{name}_{k}", module)) for k in range(width)]
    for i, val in enumerate(table):
        u = val & ((1 << width) - 1)
        for k in range(width):
            if (u >> k) & 1:
                b.wire(dec[i], rails[k].t, 1.2)
            else:
                b.wire(dec[i], rails[k].f, 1.2)
    return rails


def _we(b: NetBuilder, pulse: int, name: str, bias: int) -> Rail:
    t = b.alloc(f"{name}_t", "SEQUENCER")
    f = b.alloc(f"{name}_f", "SEQUENCER")
    b.wire(pulse, t, 1.2)
    b.wire(bias, f, 1.2)
    b.wire(pulse, f, W_INH)
    return Rail(t, f)


def _cell_eq(b: NetBuilder, a: list[Rail], c: list[Rail], name: str) -> int:
    parts = []
    for i in range(4, 7):
        t = and2(b, a[i].t, c[i].t, f"{name}_t{i}", "ADDER_COMPARE")
        f = and2(b, a[i].f, c[i].f, f"{name}_f{i}", "ADDER_COMPARE")
        parts.append(or_n(b, [t, f], f"{name}_{i}", "ADDER_COMPARE"))
    acc = parts[0]
    for i, p in enumerate(parts[1:], 1):
        acc = and2(b, acc, p, f"{name}_and{i}", "ADDER_COMPARE")
    return acc


@dataclass
class DoomSNN:
    net: LifNet
    clk: list[int]
    bias: int
    in_rails: list[Rail]
    px: list[Rail]
    py: list[Rail]
    ang: list[Rail]
    ex: list[Rail]
    ey: list[Rail]
    enemy_alive: Rail
    player_hit: Rail
    ex2: list[Rail]
    ey2: list[Rail]
    enemy2_alive: Rail
    ammo: list[Rail]
    ram_cells: list[Rail]
    dist_cols: list[list[Rail]]
    sprite_cols: list[Rail]
    pixels: list[list[list[int]]]
    shot: int
    steps_per_tick: int
    kick: list[int]
    last_spikes_per_step: float = 0.0
    pose_ring: list[int] = field(default_factory=list)
    col_ring: list[int] = field(default_factory=list)
    march_ring: list[int] = field(default_factory=list)

    def reset(self, state: GameState) -> None:
        self.net.reset()
        cur = zeros(self.net)
        drive_index(cur, self.bias)
        drive_int(cur, self.px, state.px)
        drive_int(cur, self.py, state.py)
        drive_int(cur, self.ang, state.ang)
        drive_int(cur, self.ex, state.ex)
        drive_int(cur, self.ey, state.ey)
        drive_bit(cur, self.enemy_alive, state.enemy_alive)
        drive_bit(cur, self.player_hit, state.player_hit)
        drive_int(cur, self.ex2, state.ex2)
        drive_int(cur, self.ey2, state.ey2)
        drive_bit(cur, self.enemy2_alive, state.enemy2_alive)
        drive_int(cur, self.ammo, state.ammo)
        for i, cell in enumerate(self.ram_cells):
            drive_bit(cur, cell, (state.map_bits >> i) & 1)
        for _ in range(6):
            self.net.step(cur)
        kick = zeros(self.net)
        drive_index(kick, self.bias)
        for k in self.kick:
            drive_index(kick, k)
        self.net.step(kick)

    def _input_current(self, input_bits: int) -> np.ndarray:
        cur = zeros(self.net)
        drive_index(cur, self.bias)
        for rail, bit in zip(self.in_rails, unpack_input(input_bits)):
            drive_bit(cur, rail, bit)
        return cur

    def tick(self, input_bits: int) -> np.ndarray:
        cur = self._input_current(input_bits)
        acc = 0.0
        for _ in range(self.steps_per_tick):
            s = self.net.step(cur)
            acc += float(s.sum())
        self.last_spikes_per_step = acc / max(self.steps_per_tick, 1)
        return self.decode_pixels()

    def decode_pixels(self) -> np.ndarray:
        s = self.net.spikes
        frame = np.zeros((FRAME_H, N_COLS), dtype=np.uint8)
        for c in range(N_COLS):
            for r in range(FRAME_H):
                vals = [float(s[self.pixels[c][r][k]]) for k in range(N_COLORS)]
                frame[r, c] = int(np.argmax(vals))
        return frame

    def read_hitscan(self) -> int:
        """Center-column sprite latch. Same bit as the painted heading column."""
        return read_bit(self.net.spikes, self.sprite_cols[CENTER_COL])

    def read_shot(self) -> int:
        """Fire AND heading sprite. Host may copy this; kill already wrote enemy_alive."""
        return int(self.net.spikes[self.shot] >= 1.0)

    def read_door(self) -> int:
        """Door occupancy bit in map RAM (1 closed)."""
        return read_bit(self.net.spikes, self.ram_cells[DOOR_IDX])

    def read_state(self) -> dict[str, int]:
        s = self.net.spikes
        return {
            "px": read_int(s, self.px),
            "py": read_int(s, self.py),
            "ang": read_int(s, self.ang),
            "ex": read_int(s, self.ex),
            "ey": read_int(s, self.ey),
            "enemy_alive": read_bit(s, self.enemy_alive),
            "player_hit": read_bit(s, self.player_hit),
            "ex2": read_int(s, self.ex2),
            "ey2": read_int(s, self.ey2),
            "enemy2_alive": read_bit(s, self.enemy2_alive),
            "ammo": read_int(s, self.ammo),
        }

    def raster(self) -> dict[str, np.ndarray]:
        return {name: self.net.module_spikes(name).copy() for name in sorted(set(self.net.module))}

    def zero_module(self, name: str) -> None:
        self.net.zero_module(name)


def build_doom_snn() -> DoomSNN:
    b = NetBuilder()
    bias = b.alloc("bias", "CLOCK")
    b.wire(bias, bias, 1.2)
    clk = oscillator_ring(b, SETTLE_STEPS, "CLOCK")
    beat = clk[-1]

    pose_busy = bistable(b, "pose_busy", "SEQUENCER")
    ray_busy = bistable(b, "ray_busy", "SEQUENCER")
    death_pending = bistable(b, "death_pending", "SEQUENCER")
    death_busy = bistable(b, "death_busy", "SEQUENCER")
    door_busy = bistable(b, "door_busy", "SEQUENCER")
    pose_gate = and2(b, beat, pose_busy.t, "pose_gate", "SEQUENCER")
    ray_gate = and2(b, beat, ray_busy.t, "ray_gate", "SEQUENCER")
    pose_ring = gated_ring(b, 5, pose_gate, "SEQUENCER_POSE")
    # Relabel module for ablation: SEQUENCER_* still starts with SEQUENCER? zero_module is exact.
    # Use module name SEQUENCER for all sequencer neurons by patching after alloc is awkward.
    # Delay march/col so add/test still sees the current one-hot (teacher dist is that step).
    march_gate = b.alloc("march_gate", "SEQUENCER")
    b.wire(ray_gate, march_gate, 1.2)
    march_ring = gated_ring(b, MARCH_LEN, march_gate, "SEQUENCER")
    col_adv = and2(b, march_gate, march_ring[-1], "col_adv", "SEQUENCER")
    col_ring = gated_ring(b, N_COLS, col_adv, "SEQUENCER")
    # End of pose: last pose state AND beat -> pose_busy off, ray_busy on.
    pose_end = and2(b, pose_gate, pose_ring[-1], "pose_end", "SEQUENCER")
    b.wire(pose_end, pose_busy.f, W_FORCE)
    b.wire(pose_end, pose_busy.t, W_INH)
    b.wire(pose_end, ray_busy.t, W_FORCE)
    b.wire(pose_end, ray_busy.f, W_INH)
    frame_end = and3(b, col_adv, col_ring[-1], march_ring[-1], "frame_end", "SEQUENCER")
    # Door window after last march. Pose re-arm waits for door_end so RAM does not mutate mid-march.
    b.wire(frame_end, door_busy.t, W_FORCE)
    b.wire(frame_end, door_busy.f, W_INH)
    b.wire(frame_end, ray_busy.f, W_FORCE)
    b.wire(frame_end, ray_busy.t, W_INH)
    b.wire(frame_end, pose_busy.f, W_FORCE)
    b.wire(frame_end, pose_busy.t, W_INH)
    b.wire(frame_end, march_ring[0], W_FORCE)
    for i in range(1, MARCH_LEN):
        b.wire(frame_end, march_ring[i], W_INH)
    b.wire(frame_end, col_ring[0], W_FORCE)
    for i in range(1, N_COLS):
        b.wire(frame_end, col_ring[i], W_INH)
    door_gate = and2(b, beat, door_busy.t, "door_gate", "SEQUENCER")
    door_end = door_gate
    b.wire(door_end, pose_busy.t, W_FORCE)
    b.wire(door_end, pose_busy.f, W_INH)
    b.wire(door_end, door_busy.f, W_FORCE)
    b.wire(door_end, door_busy.t, W_INH)
    b.wire(door_end, pose_ring[0], W_FORCE)
    for i in range(1, 5):
        b.wire(door_end, pose_ring[i], W_INH)

    in_rails = [Rail(*b.alloc_pair(f"in_{i}", "BIT_LATCH")) for i in range(N_INPUT_BITS)]
    turn_l, turn_r, fwd, back, fire, door = in_rails
    left_only = and2(b, turn_l.t, turn_r.f, "left_only", "BIT_LATCH")
    right_only = and2(b, turn_r.t, turn_l.f, "right_only", "BIT_LATCH")
    fwd_only = and2(b, fwd.t, back.f, "fwd_only", "BIT_LATCH")
    back_only = and2(b, back.t, fwd.f, "back_only", "BIT_LATCH")
    do_turn = Rail(or_n(b, [left_only, right_only], "do_turn_t", "BIT_LATCH"), and2(b, turn_l.f, turn_r.f, "do_turn_f", "BIT_LATCH"))
    # do_turn.f should also be 1 on both-pressed: and(not left_only, not right_only)
    both_or_none_t = and2(b, b.alloc("tmp_dt", "BIT_LATCH"), b.alloc("tmp_dt2", "BIT_LATCH"), "skip_turn_t", "BIT_LATCH")
    del both_or_none_t
    skip_t = b.alloc("skip_turn_t2", "BIT_LATCH")
    b.wire(bias, skip_t, 1.2)
    b.wire(left_only, skip_t, W_INH)
    b.wire(right_only, skip_t, W_INH)
    do_turn = Rail(or_n(b, [left_only, right_only], "do_turn_t2", "BIT_LATCH"), skip_t)
    do_move = Rail(or_n(b, [fwd_only, back_only], "do_move_t", "BIT_LATCH"), and2(b, fwd.f, back.f, "do_move_f0", "BIT_LATCH"))
    skip_m = b.alloc("skip_move", "BIT_LATCH")
    b.wire(bias, skip_m, 1.2)
    b.wire(fwd_only, skip_m, W_INH)
    b.wire(back_only, skip_m, W_INH)
    do_move = Rail(do_move.t, skip_m)

    px = add_reg(b, "px", 8, "REGISTER_FILE")
    py = add_reg(b, "py", 8, "REGISTER_FILE")
    ang = add_reg(b, "ang", 6, "REGISTER_FILE")
    ex = add_reg(b, "ex", 8, "REGISTER_FILE")
    ey = add_reg(b, "ey", 8, "REGISTER_FILE")
    enemy_alive = bistable(b, "alive", "REGISTER_FILE")
    player_hit = bistable(b, "hit", "REGISTER_FILE")
    ex2 = add_reg(b, "ex2", 8, "REGISTER_FILE")
    ey2 = add_reg(b, "ey2", 8, "REGISTER_FILE")
    enemy2_alive = bistable(b, "alive2", "REGISTER_FILE")
    ammo = add_reg(b, "ammo", AMMO_BITS, "REGISTER_FILE")

    cin0 = Rail(*b.alloc_pair("cin0", "ADDER_COMPARE"))
    b.wire(bias, cin0.f, 1.2)
    zero8 = _const_int(b, 0, 8, "zero8", "ADDER_COMPARE", bias)
    two6 = _const_int(b, 2, 6, "two6", "ADDER_COMPARE", bias)
    neg2_6 = _const_int(b, (N_ANG - 2) % N_ANG, 6, "neg2", "ADDER_COMPARE", bias)
    zero6 = _const_int(b, 0, 6, "zero6", "ADDER_COMPARE", bias)
    turn_amt_lr = mux_int(b, Rail(left_only, right_only), neg2_6, two6, "tdelta", "ADDER_COMPARE")
    # If right_only, sel.f of Rail(left,right) is right_only... Rail(left_only, right_only) is not dual-rail valid if both 0.
    turn_amt = mux_int(b, do_turn, turn_amt_lr, zero6, "tamt", "ADDER_COMPARE")
    ang2, _ = add_adder(b, ang, turn_amt, cin0, "angadd", "ADDER_COMPARE")

    ang_dec = decoder_bits(b, ang, "ang_dec", "ADDER_COMPARE")
    cos_move = tuple(c // MOVE_DIV for c in COS)
    sin_move = tuple(c // MOVE_DIV for c in SIN)
    cos_r = _rom(b, ang_dec, cos_move, 8, "cos", "ADDER_COMPARE")
    sin_r = _rom(b, ang_dec, sin_move, 8, "sin", "ADDER_COMPARE")
    ncos = tuple(((-c) & 0xFF) for c in cos_move)
    nsin = tuple(((-c) & 0xFF) for c in sin_move)
    ncos_r = _rom(b, ang_dec, ncos, 8, "ncos", "ADDER_COMPARE")
    nsin_r = _rom(b, ang_dec, nsin, 8, "nsin", "ADDER_COMPARE")
    step_dx = mux_int(b, Rail(fwd_only, back_only), cos_r, ncos_r, "sdx", "ADDER_COMPARE")
    step_dy = mux_int(b, Rail(fwd_only, back_only), sin_r, nsin_r, "sdy", "ADDER_COMPARE")
    dx = mux_int(b, do_move, step_dx, zero8, "dx", "ADDER_COMPARE")
    dy = mux_int(b, do_move, step_dy, zero8, "dy", "ADDER_COMPARE")
    cin1 = Rail(*b.alloc_pair("cin1", "ADDER_COMPARE"))
    b.wire(bias, cin1.f, 1.2)
    nx, _ = add_adder(b, px, dx, cin1, "nx", "ADDER_COMPARE")
    cin2 = Rail(*b.alloc_pair("cin2", "ADDER_COMPARE"))
    b.wire(bias, cin2.f, 1.2)
    ny, _ = add_adder(b, py, dy, cin2, "ny", "ADDER_COMPARE")

    we_never = Rail(*b.alloc_pair("we_never", "RAM"))
    b.wire(bias, we_never.f, 1.2)
    data_ram = Rail(*b.alloc_pair("d_ram", "RAM"))
    addr_n = [nx[4], nx[5], nx[6], ny[4], ny[5], ny[6]]
    ram_cells, ram_n, _ = add_ram1(b, addr_n, we_never, data_ram, "map", "RAM")
    # Door write uses the old we_ram port as a 2-step pulse on this cell only.
    door_early = or_n(b, [clk[2], clk[3]], "door_early", "DOOR")
    we_ram_t = and3(b, door_busy.t, door.t, door_early, "we_ram_t", "DOOR")
    we_ram_f = b.alloc("we_ram_f", "DOOR")
    b.wire(bias, we_ram_f, 1.2)
    b.wire(we_ram_t, we_ram_f, W_INH)
    we_ram = Rail(we_ram_t, we_ram_f)
    latch_write(
        b,
        ram_cells[DOOR_IDX],
        we_ram,
        Rail(ram_cells[DOOR_IDX].f, ram_cells[DOOR_IDX].t),
        "door_tog",
        "DOOR",
    )
    wall_t = or_n(b, [ram_n.t, nx[7].t, ny[7].t], "wall_t", "RAM")
    wall_f = and3(b, ram_n.f, nx[7].f, ny[7].f, "wall_f", "RAM")
    wall = Rail(wall_t, wall_f)
    commit = and2(b, do_move.t, wall.f, "commit_move", "ADDER_COMPARE")
    ncommit = or_n(b, [do_move.f, wall.t], "ncommit", "ADDER_COMPARE")
    commit_r = Rail(commit, ncommit)
    px_next = mux_int(b, commit_r, nx, px, "pxn", "REGISTER_FILE")
    py_next = mux_int(b, commit_r, ny, py, "pyn", "REGISTER_FILE")

    two8 = _const_int(b, 2, 8, "two8", "ADDER_COMPARE", bias)
    ntwo8 = _const_int(b, (-2) & 0xFF, 8, "ntwo8", "ADDER_COMPARE", bias)
    gt_x = add_gt(b, px, ex, "gtx", "ADDER_COMPARE", bias)
    lt_x = add_gt(b, ex, px, "ltx", "ADDER_COMPARE", bias)
    gt_y = add_gt(b, py, ey, "gty", "ADDER_COMPARE", bias)
    lt_y = add_gt(b, ey, py, "lty", "ADDER_COMPARE", bias)
    ne_x = or_n(b, [gt_x.t, lt_x.t], "nex", "ADDER_COMPARE")
    eq_x = and2(b, gt_x.f, lt_x.f, "eqx", "ADDER_COMPARE")
    ne_y = or_n(b, [gt_y.t, lt_y.t], "ney", "ADDER_COMPARE")
    edx = mux_int(b, gt_x, two8, ntwo8, "edx", "ADDER_COMPARE")
    edx = mux_int(b, Rail(ne_x, eq_x), edx, zero8, "edxz", "ADDER_COMPARE")
    edy = mux_int(b, gt_y, two8, ntwo8, "edy", "ADDER_COMPARE")
    eq_y = and2(b, gt_y.f, lt_y.f, "eqy", "ADDER_COMPARE")
    edy = mux_int(b, Rail(ne_y, eq_y), edy, zero8, "edyz", "ADDER_COMPARE")
    use_x = Rail(ne_x, eq_x)
    e_dx = mux_int(b, use_x, edx, zero8, "en_dx", "ADDER_COMPARE")
    e_dy = mux_int(b, use_x, zero8, edy, "en_dy", "ADDER_COMPARE")
    cin3 = Rail(*b.alloc_pair("cin3", "ADDER_COMPARE"))
    b.wire(bias, cin3.f, 1.2)
    nex, _ = add_adder(b, ex, e_dx, cin3, "nexadd", "ADDER_COMPARE")
    cin4 = Rail(*b.alloc_pair("cin4", "ADDER_COMPARE"))
    b.wire(bias, cin4.f, 1.2)
    ney, _ = add_adder(b, ey, e_dy, cin4, "neyadd", "ADDER_COMPARE")
    addr_e = [nex[4], nex[5], nex[6], ney[4], ney[5], ney[6]]
    dec_e = decoder_bits(b, addr_e, "dec_e", "RAM")
    ram_e = or_n(b, [and2(b, dec_e[i], ram_cells[i].t, f"ert{i}", "RAM") for i in range(len(ram_cells))], "ram_e", "RAM")
    ewall = or_n(b, [ram_e, nex[7].t, ney[7].t], "ewall", "RAM")
    not_ewall = b.alloc("not_ewall", "RAM")
    b.wire(bias, not_ewall, 1.2)
    b.wire(ewall, not_ewall, W_INH)
    ecommit_t = and2(b, enemy_alive.t, not_ewall, "ecommit_t", "ADDER_COMPARE")
    ecommit_f = or_n(b, [enemy_alive.f, ewall], "ecommit_f", "ADDER_COMPARE")
    ecommit = Rail(ecommit_t, ecommit_f)
    ex_next = mux_int(b, ecommit, nex, ex, "exn", "REGISTER_FILE")
    ey_next = mux_int(b, ecommit, ney, ey, "eyn", "REGISTER_FILE")
    same = and2(b, _cell_eq(b, px, ex, "cx"), _cell_eq(b, py, ey, "cy"), "same_cell", "ADDER_COMPARE")
    hit_set = and2(b, same, enemy_alive.t, "hit_set", "ADDER_COMPARE")
    same2 = and2(b, _cell_eq(b, px, ex2, "cx2"), _cell_eq(b, py, ey2, "cy2"), "same_cell2", "ADDER_COMPARE")
    hit_set2 = and2(b, same2, enemy2_alive.t, "hit_set2", "ADDER_COMPARE")

    rx = add_reg(b, "rx", 8, "RAY_COLUMN")
    ry = add_reg(b, "ry", 8, "RAY_COLUMN")
    rhit = bistable(b, "rhit", "RAY_COLUMN")
    col_off = tuple((c - FOV_HALF) % N_ANG for c in range(N_COLS))
    sel_dx = [Rail(*b.alloc_pair(f"sdx_{k}", "RAY_COLUMN")) for k in range(8)]
    sel_dy = [Rail(*b.alloc_pair(f"sdy_{k}", "RAY_COLUMN")) for k in range(8)]
    for c in range(N_COLS):
        table_c = tuple(COS[(a + col_off[c]) % N_ANG] for a in range(N_ANG))
        table_s = tuple(SIN[(a + col_off[c]) % N_ANG] for a in range(N_ANG))
        crc = _rom(b, ang_dec, table_c, 8, f"cosc{c}", "RAY_COLUMN")
        src = _rom(b, ang_dec, table_s, 8, f"sinc{c}", "RAY_COLUMN")
        for k in range(8):
            b.wire(and2(b, col_ring[c], crc[k].t, f"cdxt{c}{k}", "RAY_COLUMN"), sel_dx[k].t, 1.2)
            b.wire(and2(b, col_ring[c], crc[k].f, f"cdxf{c}{k}", "RAY_COLUMN"), sel_dx[k].f, 1.2)
            b.wire(and2(b, col_ring[c], src[k].t, f"cdyt{c}{k}", "RAY_COLUMN"), sel_dy[k].t, 1.2)
            b.wire(and2(b, col_ring[c], src[k].f, f"cdyf{c}{k}", "RAY_COLUMN"), sel_dy[k].f, 1.2)
    cin5 = Rail(*b.alloc_pair("cin5", "ADDER_COMPARE"))
    b.wire(bias, cin5.f, 1.2)
    rxn, _ = add_adder(b, rx, sel_dx, cin5, "rxadd", "ADDER_COMPARE")
    cin6 = Rail(*b.alloc_pair("cin6", "ADDER_COMPARE"))
    b.wire(bias, cin6.f, 1.2)
    ryn, _ = add_adder(b, ry, sel_dy, cin6, "ryadd", "ADDER_COMPARE")
    addr_r = [rxn[4], rxn[5], rxn[6], ryn[4], ryn[5], ryn[6]]
    dec_r = decoder_bits(b, addr_r, "dec_r", "RAM")
    ram_r = or_n(b, [and2(b, dec_r[i], ram_cells[i].t, f"rrt{i}", "RAM") for i in range(len(ram_cells))], "ram_r", "RAM")
    rwall = or_n(b, [ram_r, rxn[7].t, ryn[7].t], "rwall", "RAY_COLUMN")

    dist_cols = [add_reg(b, f"dist{c}", 4, "RAY_COLUMN") for c in range(N_COLS)]
    sprite_cols = [bistable(b, f"sp{c}", "RAY_COLUMN") for c in range(N_COLS)]
    heading_e1 = bistable(b, "hd1", "RAY_COLUMN")
    heading_e2 = bistable(b, "hd2", "RAY_COLUMN")

    ro = build_fixed_readout(b, "wta")
    for c in range(N_COLS):
        for k in range(4):
            b.wire(dist_cols[c][k].t, ro["dist_bits"][c][k].t, 1.2)
            b.wire(dist_cols[c][k].f, ro["dist_bits"][c][k].f, 1.2)
        b.wire(sprite_cols[c].t, ro["sprite_bits"][c].t, 1.2)
        b.wire(sprite_cols[c].f, ro["sprite_bits"][c].f, 1.2)

    # Pose captures at end of each pose state.
    we_ang = _we(
        b,
        and3(b, pose_gate, pose_ring[0], player_hit.f, "p_turn", "SEQUENCER"),
        "we_ang",
        bias,
    )
    we_xy = _we(
        b,
        and3(b, pose_gate, pose_ring[1], player_hit.f, "p_move", "SEQUENCER"),
        "we_xy",
        bias,
    )
    we_e = _we(
        b,
        and3(b, pose_gate, pose_ring[2], player_hit.f, "p_enemy", "SEQUENCER"),
        "we_e",
        bias,
    )
    p_hit = and2(b, pose_gate, pose_ring[3], "p_hit", "SEQUENCER")
    p_load = and2(b, pose_gate, pose_ring[4], "p_load", "SEQUENCER")
    add_write(b, ang, we_ang, ang2, "w_ang", "REGISTER_FILE")
    add_write(b, px, we_xy, px_next, "w_px", "REGISTER_FILE")
    add_write(b, py, we_xy, py_next, "w_py", "REGISTER_FILE")
    add_write(b, ex, we_e, ex_next, "w_ex", "REGISTER_FILE")
    add_write(b, ey, we_e, ey_next, "w_ey", "REGISTER_FILE")
    hs1 = and2(b, p_hit, hit_set, "hs1", "SEQUENCER")
    hs2 = and2(b, p_hit, hit_set2, "hs2", "SEQUENCER")
    hs = or_n(b, [hs1, hs2], "hs", "SEQUENCER")
    b.wire(hs, player_hit.t, W_FORCE)
    b.wire(hs, player_hit.f, W_INH)
    b.wire(hs1, enemy_alive.f, W_FORCE)
    b.wire(hs1, enemy_alive.t, W_INH)
    b.wire(hs2, enemy2_alive.f, W_FORCE)
    b.wire(hs2, enemy2_alive.t, W_INH)
    b.wire(hs, death_pending.t, W_FORCE)
    b.wire(hs, death_pending.f, W_INH)

    we_load = _we(b, p_load, "we_load", bias)
    add_write(b, rx, we_load, px, "load_x", "RAY_COLUMN")
    add_write(b, ry, we_load, py, "load_y", "RAY_COLUMN")
    b.wire(p_load, rhit.f, W_FORCE)
    b.wire(p_load, rhit.t, W_INH)

    # New column: march[0] reloads pose into the ray latches. Direction is combinational.
    new_col = and2(b, ray_gate, march_ring[0], "new_col", "SEQUENCER")
    we_col = _we(b, new_col, "we_col", bias)
    add_write(b, rx, we_col, px, "col_x", "RAY_COLUMN")
    add_write(b, ry, we_col, py, "col_y", "RAY_COLUMN")
    b.wire(new_col, rhit.f, W_FORCE)
    b.wire(new_col, rhit.t, W_INH)
    for c in range(N_COLS):
        clr = and2(b, new_col, col_ring[c], f"spclr{c}", "RAY_COLUMN")
        b.wire(clr, sprite_cols[c].f, W_FORCE)
        b.wire(clr, sprite_cols[c].t, W_INH)

    # March step: if not hit, x,y := sum; if wall, capture dist = march_index+1 into active col.
    not_m0 = b.alloc("not_m0", "SEQUENCER")
    b.wire(bias, not_m0, 1.2)
    b.wire(march_ring[0], not_m0, W_INH)
    do_step = and3(b, ray_gate, rhit.f, not_m0, "do_step", "RAY_COLUMN")
    we_step = Rail(do_step, rhit.t)
    add_write(b, rx, we_step, rxn, "step_x", "RAY_COLUMN")
    add_write(b, ry, we_step, ryn, "step_y", "RAY_COLUMN")
    capture = and2(b, do_step, rwall, "capture", "RAY_COLUMN")
    b.wire(capture, rhit.t, W_FORCE)
    b.wire(capture, rhit.f, W_INH)
    for c in range(N_COLS):
        cap_c = and2(b, capture, col_ring[c], f"capc{c}", "RAY_COLUMN")
        for m in range(1, MARCH_LEN):
            cap_m = and2(b, cap_c, march_ring[m], f"cap{c}_{m}", "RAY_COLUMN")
            # Capture lands one one-hot late vs the add that hit. Teacher dist is that add's index.
            dval = m - 1
            for k in range(4):
                if (dval >> k) & 1:
                    b.wire(cap_m, dist_cols[c][k].t, W_FORCE)
                    b.wire(cap_m, dist_cols[c][k].f, W_INH)
                else:
                    b.wire(cap_m, dist_cols[c][k].f, W_FORCE)
                    b.wire(cap_m, dist_cols[c][k].t, W_INH)
        # Sprite if the march visits the enemy cell, not only at the wall hit.
        vis = and2(b, do_step, col_ring[c], f"vis{c}", "RAY_COLUMN")
        sprx = _cell_eq(b, rxn, ex, f"sprx{c}")
        spry = _cell_eq(b, ryn, ey, f"spry{c}")
        sxy = and2(b, sprx, spry, f"sxy{c}", "RAY_COLUMN")
        spr = and3(b, vis, sxy, enemy_alive.t, f"spr{c}", "RAY_COLUMN")
        sprx2 = _cell_eq(b, rxn, ex2, f"sprx2{c}")
        spry2 = _cell_eq(b, ryn, ey2, f"spry2{c}")
        sxy2 = and2(b, sprx2, spry2, f"sxy2{c}", "RAY_COLUMN")
        spr2 = and3(b, vis, sxy2, enemy2_alive.t, f"spr2{c}", "RAY_COLUMN")
        spr_any = or_n(b, [spr, spr2], f"spra{c}", "RAY_COLUMN")
        b.wire(spr_any, sprite_cols[c].t, W_FORCE)
        b.wire(spr_any, sprite_cols[c].f, W_INH)
        if c == CENTER_COL:
            clr_h = and2(b, new_col, col_ring[c], "hdclr", "RAY_COLUMN")
            b.wire(clr_h, heading_e1.f, W_FORCE)
            b.wire(clr_h, heading_e1.t, W_INH)
            b.wire(clr_h, heading_e2.f, W_FORCE)
            b.wire(clr_h, heading_e2.t, W_INH)
            b.wire(spr, heading_e1.t, W_FORCE)
            b.wire(spr, heading_e1.f, W_INH)
            b.wire(spr2, heading_e2.t, W_FORCE)
            b.wire(spr2, heading_e2.f, W_INH)

    # Fire AND heading sprite. Kill on the last column's last march window (SETTLE long).
    ammo_nz = or_n(b, [ammo[i].t for i in range(AMMO_BITS)], "ammo_nz", "REGISTER_FILE")
    shot = and3(b, fire.t, sprite_cols[CENTER_COL].t, ammo_nz, "shot", "SEQUENCER")
    end_hold = and2(b, col_ring[-1], march_ring[-1], "end_hold", "SEQUENCER")
    kill1 = and3(b, end_hold, fire.t, and2(b, heading_e1.t, ammo_nz, "k1a", "SEQUENCER"), "kill1", "SEQUENCER")
    kill2 = and3(b, end_hold, fire.t, and2(b, heading_e2.t, ammo_nz, "k2a", "SEQUENCER"), "kill2", "SEQUENCER")
    b.wire(kill1, enemy_alive.f, W_FORCE)
    b.wire(kill1, enemy_alive.t, W_INH)
    b.wire(kill2, enemy2_alive.f, W_FORCE)
    b.wire(kill2, enemy2_alive.t, W_INH)
    # Consume ammo after paint, in the door window. 2-step pulse, late in SETTLE so the 3-bit add settles.
    take = and2(b, fire.t, ammo_nz, "ammo_take", "REGISTER_FILE")
    skip_ammo = b.alloc("ammo_hold", "REGISTER_FILE")
    b.wire(bias, skip_ammo, 1.2)
    b.wire(take, skip_ammo, W_INH)
    take_r = Rail(take, skip_ammo)
    neg1 = _const_int(b, 7, AMMO_BITS, "aneg1", "ADDER_COMPARE", bias)
    cin_a = Rail(*b.alloc_pair("cina", "ADDER_COMPARE"))
    b.wire(bias, cin_a.f, 1.2)
    ammo_m1, _ = add_adder(b, ammo, neg1, cin_a, "ammo_sub", "ADDER_COMPARE")
    ammo_next = mux_int(b, take_r, ammo_m1, ammo, "amnext", "REGISTER_FILE")
    ammo_pulse = or_n(b, [clk[2], clk[3]], "ammo_pulse", "REGISTER_FILE")
    we_ammo = _we(b, and2(b, door_busy.t, ammo_pulse, "we_ammo_p", "REGISTER_FILE"), "we_ammo", bias)
    add_write(b, ammo, we_ammo, ammo_next, "w_ammo", "REGISTER_FILE")

    # Death: arm after the contact frame, then DEATH_TICKS freeze ticks, then re-arm.
    ray_start = and3(b, ray_gate, march_ring[0], col_ring[0], "ray_start", "SEQUENCER")
    death_adv = and2(b, ray_start, death_busy.t, "death_adv", "SEQUENCER")
    death_cells = [b.alloc(f"death_{i}", "SEQUENCER") for i in range(DEATH_TICKS)]
    for i, cell in enumerate(death_cells):
        b.wire(cell, cell, W_HOLD)
        step = and2(b, cell, death_adv, f"death_step{i}", "SEQUENCER")
        b.wire(step, cell, W_INH)
        if i + 1 < DEATH_TICKS:
            b.wire(step, death_cells[i + 1], W_FORCE)
        else:
            b.wire(step, death_busy.f, W_FORCE)
            b.wire(step, death_busy.t, W_INH)
            b.wire(step, player_hit.f, W_FORCE)
            b.wire(step, player_hit.t, W_INH)
            for c in death_cells:
                b.wire(step, c, W_INH)
    arm = and2(b, end_hold, death_pending.t, "death_arm", "SEQUENCER")
    b.wire(arm, death_busy.t, W_FORCE)
    b.wire(arm, death_busy.f, W_INH)
    b.wire(arm, death_pending.f, W_FORCE)
    b.wire(arm, death_pending.t, W_INH)
    b.wire(arm, death_cells[0], W_FORCE)
    for cell in death_cells[1:]:
        b.wire(arm, cell, W_INH)

    # gated_ring for pose used module SEQUENCER_POSE; retag by compiling then... keep both.
    # Relabel SEQUENCER_POSE -> we will treat it as SEQUENCER in zero_module tests by also zeroing it.
    net = b.compile()
    # Merge SEQUENCER_POSE into SEQUENCER for ablation.
    net.module = ["SEQUENCER" if m == "SEQUENCER_POSE" else m for m in net.module]
    if net.n > V1_NEURON_CAP:
        raise RuntimeError(f"v1 net {net.n} exceeds cap {V1_NEURON_CAP}")
    return DoomSNN(
        net=net,
        clk=clk,
        bias=bias,
        in_rails=in_rails,
        px=px,
        py=py,
        ang=ang,
        ex=ex,
        ey=ey,
        enemy_alive=enemy_alive,
        player_hit=player_hit,
        ex2=ex2,
        ey2=ey2,
        enemy2_alive=enemy2_alive,
        ammo=ammo,
        ram_cells=ram_cells,
        dist_cols=dist_cols,
        sprite_cols=sprite_cols,
        pixels=ro["pixels"],
        shot=shot,
        steps_per_tick=STEPS_PER_TICK,
        kick=[clk[0], bias, pose_busy.t, pose_ring[0], march_ring[0], col_ring[0], ray_busy.f, door_busy.f],
        pose_ring=pose_ring,
        col_ring=col_ring,
        march_ring=march_ring,
    )
