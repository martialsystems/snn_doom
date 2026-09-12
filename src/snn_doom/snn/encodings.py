# Copyright (c) 2026 Martial Systems LLC
"""Role x encoding constructors. No fly cell-type names."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from snn_doom.snn.digital import (
    W_HOLD,
    W_INH,
    W_KICK,
    Rail,
    adder_n,
    and2,
    bistable,
    const_bias,
    decoder_bits,
    latch_write,
    or_n,
    oscillator_ring,
)
from snn_doom.snn.lif import LifNet, NetBuilder


@dataclass
class EncodedNet:
    net: LifNet
    n_in: int
    n_out: int
    encoding: str
    role: str
    extra: dict

    def reset(self) -> None:
        self.net.reset()


def _drive(n: int, idx: list[int], values: np.ndarray, amp: float = 1.2) -> np.ndarray:
    cur = np.zeros(n, dtype=np.float32)
    for i, v in zip(idx, values):
        cur[i] = amp if v else 0.0
    return cur


def build_clock(encoding: str, period: int = 8) -> EncodedNet:
    b = NetBuilder()
    extra: dict = {"period": period}
    if encoding == "oscillator":
        cells = oscillator_ring(b, period, "CLOCK")
        extra["cells"] = cells
        extra["out"] = cells[0]
        extra["kick"] = cells[0]
        net = b.compile()
        return EncodedNet(net, 0, 1, encoding, "CLOCK", extra)
    if encoding == "dual_rail":
        cells = oscillator_ring(b, period, "CLOCK")
        extra["out"] = cells[0]
        extra["kick"] = cells[0]
        extra["cells"] = cells
        net = b.compile()
        return EncodedNet(net, 0, 1, encoding, "CLOCK", extra)
    if encoding == "wta":
        cells = [b.alloc(f"wta_{i}", "CLOCK") for i in range(period)]
        for i, n in enumerate(cells):
            b.wire(n, cells[(i + 1) % period], W_KICK)
            for j, m in enumerate(cells):
                if i != j:
                    b.wire(n, m, W_INH * 0.5)
        extra["out"] = cells[0]
        extra["kick"] = cells[0]
        extra["cells"] = cells
        net = b.compile()
        return EncodedNet(net, 0, 1, encoding, "CLOCK", extra)
    if encoding == "bistable":
        # A pair cannot tick; it holds. Include it so the bake-off can fail it.
        q = bistable(b, "clk", "CLOCK")
        extra["out"] = q.t
        extra["kick"] = q.t
        net = b.compile()
        return EncodedNet(net, 0, 1, encoding, "CLOCK", extra)
    hidden = 32 if encoding == "population" else 8
    cells = [b.alloc(f"h_{i}", "CLOCK") for i in range(hidden)]
    out = b.alloc("out", "CLOCK")
    bias = const_bias(b, "CLOCK")
    for n in cells:
        b.wire(bias, n, 0.4)
        b.wire(n, out, 0.3)
        b.wire(n, n, 0.2)
    extra["out"] = out
    extra["kick"] = bias
    extra["cells"] = cells
    net = b.compile()
    return EncodedNet(net, 0, 1, encoding, "CLOCK", extra)


def build_latch(encoding: str) -> EncodedNet:
    b = NetBuilder()
    extra: dict = {}
    if encoding in ("bistable", "dual_rail"):
        q = bistable(b, "q", "BIT_LATCH")
        we_t = b.alloc("we_t", "BIT_LATCH")
        we_f = b.alloc("we_f", "BIT_LATCH")
        d_t = b.alloc("d_t", "BIT_LATCH")
        d_f = b.alloc("d_f", "BIT_LATCH")
        latch_write(b, q, Rail(we_t, we_f), Rail(d_t, d_f), "w", "BIT_LATCH")
        extra.update({"q": q, "we_t": we_t, "d_t": d_t, "d_f": d_f, "we_f": we_f, "out": q.t})
        net = b.compile()
        return EncodedNet(net, 3, 1, encoding, "BIT_LATCH", extra)
    if encoding == "wta":
        t = b.alloc("t", "BIT_LATCH")
        f = b.alloc("f", "BIT_LATCH")
        b.wire(t, t, W_HOLD)
        b.wire(f, f, W_HOLD)
        b.wire(t, f, W_INH)
        b.wire(f, t, W_INH)
        extra.update({"out": t, "t": t, "f": f})
        net = b.compile()
        return EncodedNet(net, 2, 1, encoding, "BIT_LATCH", extra)
    n = 16 if encoding == "population" else 4
    cells = [b.alloc(f"h_{i}", "BIT_LATCH") for i in range(n)]
    inp = b.alloc("in", "BIT_LATCH")
    out = b.alloc("out", "BIT_LATCH")
    for c in cells:
        b.wire(inp, c, 0.8)
        b.wire(c, out, 0.4)
        b.wire(c, c, 0.7 if encoding == "rate" else 0.2)
    extra.update({"out": out, "in": inp, "cells": cells})
    net = b.compile()
    return EncodedNet(net, 1, 1, encoding, "BIT_LATCH", extra)


def build_register_file(encoding: str, n_reg: int = 4, width: int = 4) -> EncodedNet:
    b = NetBuilder()
    extra: dict = {"n_reg": n_reg, "width": width, "regs": []}
    if encoding not in ("bistable", "dual_rail", "wta"):
        # Analog bag: one hidden layer, will lose hold.
        n = 64
        cells = [b.alloc(f"h_{i}", "REGISTER_FILE") for i in range(n)]
        extra["cells"] = cells
        extra["in_idx"] = [b.alloc(f"in_{i}", "REGISTER_FILE") for i in range(n_reg + width + 1)]
        extra["out_idx"] = [b.alloc(f"out_{i}", "REGISTER_FILE") for i in range(width)]
        for src in extra["in_idx"]:
            for c in cells:
                b.wire(src, c, 0.15)
        for c in cells:
            for o in extra["out_idx"]:
                b.wire(c, o, 0.15)
            b.wire(c, c, 0.4)
        net = b.compile()
        return EncodedNet(net, len(extra["in_idx"]), width, encoding, "REGISTER_FILE", extra)
    regs: list[list[Rail]] = []
    for r in range(n_reg):
        row = [bistable(b, f"r{r}b{k}", "REGISTER_FILE") for k in range(width)]
        regs.append(row)
    extra["regs"] = regs
    extra["we"] = [b.alloc(f"we_{r}", "REGISTER_FILE") for r in range(n_reg)]
    extra["data"] = [b.alloc_pair(f"d{k}", "REGISTER_FILE") for k in range(width)]
    extra["sel"] = [b.alloc(f"sel_{r}", "REGISTER_FILE") for r in range(n_reg)]
    for r, row in enumerate(regs):
        we = Rail(extra["we"][r], b.alloc(f"we_{r}_f", "REGISTER_FILE"))
        for k, q in enumerate(row):
            dt, df = extra["data"][k]
            latch_write(b, q, we, Rail(dt, df), f"r{r}b{k}", "REGISTER_FILE")
    extra["out"] = []
    for k in range(width):
        srcs = []
        for r, row in enumerate(regs):
            srcs.append(and2(b, extra["sel"][r], row[k].t, f"rd_{r}_{k}", "REGISTER_FILE"))
        extra["out"].append(or_n(b, srcs, f"out_{k}", "REGISTER_FILE"))
    net = b.compile()
    return EncodedNet(net, n_reg + width + n_reg, width, encoding, "REGISTER_FILE", extra)


def build_adder(encoding: str, width: int = 4) -> EncodedNet:
    b = NetBuilder()
    extra: dict = {"width": width}
    if encoding in ("dual_rail", "bistable"):
        a = [Rail(*b.alloc_pair(f"a{i}", "ADDER_COMPARE")) for i in range(width)]
        c = [Rail(*b.alloc_pair(f"c{i}", "ADDER_COMPARE")) for i in range(width)]
        cin = Rail(*b.alloc_pair("cin", "ADDER_COMPARE"))
        sums, cout = adder_n(b, a, c, cin, "s", "ADDER_COMPARE")
        gt_bits = []
        # a>b: compare from MSB, (a and not b) and equal-so-far on higher bits.
        eq_so_far = None
        for i in reversed(range(width)):
            gt_i = and2(b, a[i].t, c[i].f, f"gt_{i}", "ADDER_COMPARE")
            eq_i = and2(b, a[i].t, c[i].t, f"eqt_{i}", "ADDER_COMPARE")
            eq_i2 = and2(b, a[i].f, c[i].f, f"eqf_{i}", "ADDER_COMPARE")
            eq = or_n(b, [eq_i, eq_i2], f"eq_{i}", "ADDER_COMPARE")
            if eq_so_far is None:
                gt_bits.append(gt_i)
                eq_so_far = eq
            else:
                gt_bits.append(and2(b, gt_i, eq_so_far, f"gtp_{i}", "ADDER_COMPARE"))
                eq_so_far = and2(b, eq, eq_so_far, f"eqs_{i}", "ADDER_COMPARE")
        gt = or_n(b, gt_bits, "gt", "ADDER_COMPARE")
        extra.update({"a": a, "c": c, "cin": cin, "sums": sums, "cout": cout, "gt": gt, "eq": eq_so_far})
        net = b.compile()
        return EncodedNet(net, 2 * width, width + 2, encoding, "ADDER_COMPARE", extra)
    n = 128 if encoding == "population" else 48
    ins = [b.alloc(f"in_{i}", "ADDER_COMPARE") for i in range(2 * width)]
    hid = [b.alloc(f"h_{i}", "ADDER_COMPARE") for i in range(n)]
    outs = [b.alloc(f"out_{i}", "ADDER_COMPARE") for i in range(width + 2)]
    rng = np.random.default_rng(0)
    for i in ins:
        for h in hid:
            b.wire(i, h, float(rng.normal(0.05, 0.15)))
    for h in hid:
        for o in outs:
            b.wire(h, o, float(rng.normal(0.02, 0.1)))
        b.wire(h, h, 0.1)
    extra.update({"in": ins, "out": outs, "hid": hid})
    net = b.compile()
    return EncodedNet(net, 2 * width, width + 2, encoding, "ADDER_COMPARE", extra)


def build_ram(encoding: str, n_cells: int = 16) -> EncodedNet:
    b = NetBuilder()
    extra: dict = {"n_cells": n_cells}
    nbits = int(np.log2(n_cells))
    if encoding in ("bistable", "dual_rail", "wta"):
        addr = [Rail(*b.alloc_pair(f"a{i}", "RAM")) for i in range(nbits)]
        cells = [bistable(b, f"c{i}", "RAM") for i in range(n_cells)]
        we = Rail(*b.alloc_pair("we", "RAM"))
        data = Rail(*b.alloc_pair("d", "RAM"))
        dec = decoder_bits(b, addr, "dec", "RAM")
        for i, q in enumerate(cells):
            we_i = Rail(and2(b, we.t, dec[i], f"we_{i}", "RAM"), we.f)
            latch_write(b, q, we_i, data, f"w{i}", "RAM")
        read_t = [
            and2(b, dec[i], cells[i].t, f"rt{i}", "RAM") for i in range(n_cells)
        ]
        read_f = [
            and2(b, dec[i], cells[i].f, f"rf{i}", "RAM") for i in range(n_cells)
        ]
        extra["out_t"] = or_n(b, read_t, "out_t", "RAM")
        extra["out_f"] = or_n(b, read_f, "out_f", "RAM")
        extra.update({"addr": addr, "we": we, "data": data, "cells": cells, "dec": dec})
        net = b.compile()
        return EncodedNet(net, nbits + 2, 1, encoding, "RAM", extra)
    n = 64
    extra["in"] = [b.alloc(f"in_{i}", "RAM") for i in range(nbits + 2)]
    extra["hid"] = [b.alloc(f"h_{i}", "RAM") for i in range(n)]
    extra["out"] = b.alloc("out", "RAM")
    rng = np.random.default_rng(1)
    for i in extra["in"]:
        for h in extra["hid"]:
            b.wire(i, h, float(rng.normal(0.05, 0.2)))
    for h in extra["hid"]:
        b.wire(h, extra["out"], float(rng.normal(0.05, 0.2)))
        b.wire(h, h, 0.5)
    net = b.compile()
    return EncodedNet(net, nbits + 2, 1, encoding, "RAM", extra)


def build_sequencer(encoding: str, n_states: int = 8) -> EncodedNet:
    b = NetBuilder()
    extra: dict = {"n_states": n_states}
    if encoding in ("oscillator", "wta", "dual_rail"):
        cells = oscillator_ring(b, n_states, "SEQUENCER")
        extra["cells"] = cells
        extra["kick"] = cells[0]
        extra["out"] = cells
        net = b.compile()
        return EncodedNet(net, 0, n_states, encoding, "SEQUENCER", extra)
    if encoding == "bistable":
        cells = [bistable(b, f"s{i}", "SEQUENCER") for i in range(n_states)]
        extra["cells"] = [c.t for c in cells]
        extra["kick"] = cells[0].t
        extra["out"] = extra["cells"]
        net = b.compile()
        return EncodedNet(net, 0, n_states, encoding, "SEQUENCER", extra)
    n = 24
    hid = [b.alloc(f"h_{i}", "SEQUENCER") for i in range(n)]
    extra["out"] = [b.alloc(f"s_{i}", "SEQUENCER") for i in range(n_states)]
    extra["kick"] = hid[0]
    for i, h in enumerate(hid):
        b.wire(h, hid[(i + 1) % n], 0.8)
        b.wire(h, extra["out"][i % n_states], 0.4)
    net = b.compile()
    return EncodedNet(net, 0, n_states, encoding, "SEQUENCER", extra)


def build_ray(encoding: str) -> EncodedNet:
    """One column: pose (8+8+6) plus 64 map bits in, 4-bit dist out.

    Dual-rail/bistable: a tiny march of 15 steps sharing the digital adder and a
    64-cell RAM. Analog encodings: random recurrent net, trained later.
    """
    b = NetBuilder()
    extra: dict = {}
    if encoding in ("dual_rail", "bistable"):
        from snn_doom.modules.ray import build_one_column

        extra = build_one_column(b, encoding)
        net = b.compile()
        return EncodedNet(net, extra["n_in"], 4, encoding, "RAY_COLUMN", extra)
    n = 128 if encoding == "population" else 64
    extra["in"] = [b.alloc(f"in_{i}", "RAY_COLUMN") for i in range(8 + 8 + 6 + 64)]
    extra["hid"] = [b.alloc(f"h_{i}", "RAY_COLUMN") for i in range(n)]
    extra["out"] = [b.alloc(f"o_{i}", "RAY_COLUMN") for i in range(4)]
    rng = np.random.default_rng(2)
    for i in extra["in"]:
        for h in extra["hid"]:
            b.wire(i, h, float(rng.normal(0.02, 0.08)))
    for h in extra["hid"]:
        for o in extra["out"]:
            b.wire(h, o, float(rng.normal(0.02, 0.08)))
        b.wire(h, h, 0.2)
    net = b.compile()
    return EncodedNet(net, len(extra["in"]), 4, encoding, "RAY_COLUMN", extra)


def build_readout(encoding: str) -> EncodedNet:
    """16 dist values (4-bit) to 16x16x4 color WTA, or analog bag."""
    b = NetBuilder()
    extra: dict = {}
    if encoding in ("wta", "population", "dual_rail"):
        from snn_doom.modules.readout import build_fixed_readout

        extra = build_fixed_readout(b, encoding)
        net = b.compile()
        return EncodedNet(net, extra["n_in"], extra["n_out"], encoding, "FRAME_READOUT", extra)
    n = 64
    extra["in"] = [b.alloc(f"in_{i}", "FRAME_READOUT") for i in range(16 * 4)]
    extra["hid"] = [b.alloc(f"h_{i}", "FRAME_READOUT") for i in range(n)]
    extra["out"] = [b.alloc(f"o_{i}", "FRAME_READOUT") for i in range(16 * 16)]
    rng = np.random.default_rng(3)
    for i in extra["in"]:
        for h in extra["hid"]:
            b.wire(i, h, float(rng.normal(0.02, 0.1)))
    for h in extra["hid"]:
        for o in extra["out"]:
            b.wire(h, o, float(rng.normal(0.01, 0.05)))
    net = b.compile()
    return EncodedNet(net, 64, 256, encoding, "FRAME_READOUT", extra)


BUILDERS = {
    "CLOCK": build_clock,
    "BIT_LATCH": build_latch,
    "REGISTER_FILE": build_register_file,
    "ADDER_COMPARE": build_adder,
    "RAM": build_ram,
    "SEQUENCER": build_sequencer,
    "RAY_COLUMN": build_ray,
    "FRAME_READOUT": build_readout,
}
