# Copyright (c) 2026 Martial Systems LLC
"""Stitched Doom SNN: host injects keys, steps a fixed LIF budget, reads pixels.

CLOCK is a SETTLE-period ring. SEQUENCER is gated pose/column/march rings.
The datapath (REG, ALU, RAM, RAY, READOUT) computes the teacher tick.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from snn_doom.const import (
    COS,
    FRAME_H,
    MAX_DIST,
    MOVE_DIV,
    N_ANG,
    N_COLS,
    N_COLORS,
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
    W_INH,
    Rail,
    and2,
    and3,
    bistable,
    decoder_bits,
    gated_ring,
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
    ram_cells: list[Rail]
    dist_cols: list[list[Rail]]
    sprite_cols: list[Rail]
    pixels: list[list[list[int]]]
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
        tl, tr, fwd, back = unpack_input(input_bits)
        drive_bit(cur, self.in_rails[0], tl)
        drive_bit(cur, self.in_rails[1], tr)
        drive_bit(cur, self.in_rails[2], fwd)
        drive_bit(cur, self.in_rails[3], back)
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
    pose_gate = and2(b, beat, pose_busy.t, "pose_gate", "SEQUENCER")
    ray_gate = and2(b, beat, ray_busy.t, "ray_gate", "SEQUENCER")
    pose_ring = gated_ring(b, 5, pose_gate, "SEQUENCER_POSE")
    # Relabel module for ablation: SEQUENCER_* still starts with SEQUENCER? zero_module is exact.
    # Use module name SEQUENCER for all sequencer neurons by patching after alloc is awkward.
    march_ring = gated_ring(b, MAX_DIST, ray_gate, "SEQUENCER")
    col_adv = and2(b, ray_gate, march_ring[-1], "col_adv", "SEQUENCER")
    col_ring = gated_ring(b, N_COLS, col_adv, "SEQUENCER")
    # End of pose: last pose state AND beat -> pose_busy off, ray_busy on.
    pose_end = and2(b, pose_gate, pose_ring[-1], "pose_end", "SEQUENCER")
    b.wire(pose_end, pose_busy.f, W_FORCE)
    b.wire(pose_end, pose_busy.t, W_INH)
    b.wire(pose_end, ray_busy.t, W_FORCE)
    b.wire(pose_end, ray_busy.f, W_INH)
    frame_end = and3(b, col_adv, col_ring[-1], march_ring[-1], "frame_end", "SEQUENCER")
    # after last column, stay in ray_busy until host finishes STEPS; next tick() does not reset rings
    # unless reset() is called. tick() is one frame: STEPS includes pose+ray. Kick pose at reset only.

    in_rails = [Rail(*b.alloc_pair(f"in_{i}", "BIT_LATCH")) for i in range(4)]
    turn_l, turn_r, fwd, back = in_rails
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

    we_ram = Rail(*b.alloc_pair("we_ram", "RAM"))
    b.wire(bias, we_ram.f, 1.2)
    data_ram = Rail(*b.alloc_pair("d_ram", "RAM"))
    addr_n = [nx[4], nx[5], nx[6], ny[4], ny[5], ny[6]]
    ram_cells, ram_n, _ = add_ram1(b, addr_n, we_ram, data_ram, "map", "RAM")
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

    rx = add_reg(b, "rx", 8, "RAY_COLUMN")
    ry = add_reg(b, "ry", 8, "RAY_COLUMN")
    rdx = add_reg(b, "rdx", 8, "RAY_COLUMN")
    rdy = add_reg(b, "rdy", 8, "RAY_COLUMN")
    rhit = bistable(b, "rhit", "RAY_COLUMN")
    cin5 = Rail(*b.alloc_pair("cin5", "ADDER_COMPARE"))
    b.wire(bias, cin5.f, 1.2)
    rxn, _ = add_adder(b, rx, rdx, cin5, "rxadd", "ADDER_COMPARE")
    cin6 = Rail(*b.alloc_pair("cin6", "ADDER_COMPARE"))
    b.wire(bias, cin6.f, 1.2)
    ryn, _ = add_adder(b, ry, rdy, cin6, "ryadd", "ADDER_COMPARE")
    addr_r = [rxn[4], rxn[5], rxn[6], ryn[4], ryn[5], ryn[6]]
    dec_r = decoder_bits(b, addr_r, "dec_r", "RAM")
    ram_r = or_n(b, [and2(b, dec_r[i], ram_cells[i].t, f"rrt{i}", "RAM") for i in range(len(ram_cells))], "ram_r", "RAM")
    rwall = or_n(b, [ram_r, rxn[7].t, ryn[7].t], "rwall", "RAY_COLUMN")

    col_off = tuple((c - 8) % N_ANG for c in range(N_COLS))
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

    dist_cols = [add_reg(b, f"dist{c}", 4, "RAY_COLUMN") for c in range(N_COLS)]
    sprite_cols = [Rail(*b.alloc_pair(f"sp{c}", "RAY_COLUMN")) for c in range(N_COLS)]

    ro = build_fixed_readout(b, "wta")
    for c in range(N_COLS):
        for k in range(4):
            b.wire(dist_cols[c][k].t, ro["dist_bits"][c][k].t, 1.2)
            b.wire(dist_cols[c][k].f, ro["dist_bits"][c][k].f, 1.2)
        b.wire(sprite_cols[c].t, ro["sprite_bits"][c].t, 1.2)
        b.wire(sprite_cols[c].f, ro["sprite_bits"][c].f, 1.2)

    # Pose captures at end of each pose state.
    we_ang = _we(b, and2(b, pose_gate, pose_ring[0], "p_turn", "SEQUENCER"), "we_ang", bias)
    we_xy = _we(b, and2(b, pose_gate, pose_ring[1], "p_move", "SEQUENCER"), "we_xy", bias)
    we_e = _we(b, and2(b, pose_gate, pose_ring[2], "p_enemy", "SEQUENCER"), "we_e", bias)
    p_hit = and2(b, pose_gate, pose_ring[3], "p_hit", "SEQUENCER")
    p_load = and2(b, pose_gate, pose_ring[4], "p_load", "SEQUENCER")
    add_write(b, ang, we_ang, ang2, "w_ang", "REGISTER_FILE")
    add_write(b, px, we_xy, px_next, "w_px", "REGISTER_FILE")
    add_write(b, py, we_xy, py_next, "w_py", "REGISTER_FILE")
    add_write(b, ex, we_e, ex_next, "w_ex", "REGISTER_FILE")
    add_write(b, ey, we_e, ey_next, "w_ey", "REGISTER_FILE")
    hs = and2(b, p_hit, hit_set, "hs", "SEQUENCER")
    b.wire(hs, player_hit.t, W_FORCE)
    b.wire(hs, player_hit.f, W_INH)

    we_load = _we(b, p_load, "we_load", bias)
    add_write(b, rx, we_load, px, "load_x", "RAY_COLUMN")
    add_write(b, ry, we_load, py, "load_y", "RAY_COLUMN")
    add_write(b, rdx, we_load, sel_dx, "load_dx", "RAY_COLUMN")
    add_write(b, rdy, we_load, sel_dy, "load_dy", "RAY_COLUMN")
    b.wire(p_load, rhit.f, W_FORCE)
    b.wire(p_load, rhit.t, W_INH)

    # New column: march[0] and ray beat reloads ray from pose and selected dir.
    new_col = and2(b, ray_gate, march_ring[0], "new_col", "SEQUENCER")
    we_col = _we(b, new_col, "we_col", bias)
    add_write(b, rx, we_col, px, "col_x", "RAY_COLUMN")
    add_write(b, ry, we_col, py, "col_y", "RAY_COLUMN")
    add_write(b, rdx, we_col, sel_dx, "col_dx", "RAY_COLUMN")
    add_write(b, rdy, we_col, sel_dy, "col_dy", "RAY_COLUMN")
    b.wire(new_col, rhit.f, W_FORCE)
    b.wire(new_col, rhit.t, W_INH)

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
        for m in range(1, MAX_DIST):
            cap_m = and2(b, cap_c, march_ring[m], f"cap{c}_{m}", "RAY_COLUMN")
            dval = m
            for k in range(4):
                if (dval >> k) & 1:
                    b.wire(cap_m, dist_cols[c][k].t, W_FORCE)
                    b.wire(cap_m, dist_cols[c][k].f, W_INH)
                else:
                    b.wire(cap_m, dist_cols[c][k].f, W_FORCE)
                    b.wire(cap_m, dist_cols[c][k].t, W_INH)
        spr = and2(b, cap_c, _cell_eq(b, rxn, ex, f"sprx{c}"), f"spr{c}", "RAY_COLUMN")
        # sprite if enemy cell equals ray cell; cheap: same as collide using rxn/ryn vs ex/ey
        spy = _cell_eq(b, ryn, ey, f"spry{c}")
        spr = and2(b, spr, spy, f"spr2{c}", "RAY_COLUMN")
        b.wire(spr, sprite_cols[c].t, W_FORCE)
        b.wire(spr, sprite_cols[c].f, W_INH)

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
        ram_cells=ram_cells,
        dist_cols=dist_cols,
        sprite_cols=sprite_cols,
        pixels=ro["pixels"],
        steps_per_tick=STEPS_PER_TICK,
        kick=[clk[0], bias, pose_busy.t, pose_ring[0], march_ring[0], col_ring[0], ray_busy.f],
        pose_ring=pose_ring,
        col_ring=col_ring,
        march_ring=march_ring,
    )
