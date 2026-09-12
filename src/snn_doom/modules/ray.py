# Copyright (c) 2026 Martial Systems LLC
"""One-column march: x,y latches + 8-bit adder + map RAM + dist latch.

The march index is an 8-cell ring in this module so the host only steps LIF.
"""
from __future__ import annotations

from snn_doom.const import MAP_CELLS, MAX_DIST
from snn_doom.modules.alu import add_adder
from snn_doom.modules.latch import add_reg, add_write
from snn_doom.modules.ram import add_ram1
from snn_doom.snn.digital import Rail, and2, bistable, or_n
from snn_doom.snn.lif import NetBuilder


def _twos_rails(b: NetBuilder, name: str, module: str, width: int = 8) -> list[Rail]:
    return [Rail(*b.alloc_pair(f"{name}_{i}", module)) for i in range(width)]


def build_one_column(b: NetBuilder, encoding: str = "dual_rail") -> dict:
    del encoding
    module = "RAY_COLUMN"
    x = add_reg(b, "ray_x", 8, module)
    y = add_reg(b, "ray_y", 8, module)
    dx = _twos_rails(b, "dx", module)
    dy = _twos_rails(b, "dy", module)
    cin0 = Rail(*b.alloc_pair("cin0", module))
    cin1 = Rail(*b.alloc_pair("cin1", module))
    sum_x, _ = add_adder(b, x, dx, cin0, "addx", "ADDER_COMPARE")
    sum_y, _ = add_adder(b, y, dy, cin1, "addy", "ADDER_COMPARE")
    # Map address: bits 4..6 of x and y (cell coords).
    addr = [x[4], x[5], x[6], y[4], y[5], y[6]]
    we = Rail(*b.alloc_pair("map_we", "RAM"))
    data = Rail(*b.alloc_pair("map_d", "RAM"))
    cells, ram_out, dec = add_ram1(b, addr, we, data, "map", "RAM")
    hit = bistable(b, "hit", module)
    dist = add_reg(b, "dist", 4, module)
    march = [b.alloc(f"m{i}", module) for i in range(MAX_DIST)]
    for i, n in enumerate(march):
        b.wire(n, march[(i + 1) % MAX_DIST], 1.2)
    # Capture dist when RAM hits and not already hit: dist bit k = march k.
    we_hit = Rail(and2(b, ram_out.t, hit.f, "we_hit", module), hit.t)
    b.wire(we_hit.t, hit.t, 2.4)
    b.wire(we_hit.t, hit.f, -2.4)
    for k in range(4):
        srcs = [and2(b, march[i], we_hit.t, f"cap_{i}_{k}", module) for i in range(MAX_DIST) if (i + 1) & (1 << k)]
        if srcs:
            pulse = or_n(b, srcs, f"dist_set_{k}", module)
            b.wire(pulse, dist[k].t, 2.4)
            b.wire(pulse, dist[k].f, -2.4)
    # Advance x,y to sum when no hit yet, gated by a capture pulse on every march beat.
    # Bake-off harness re-injects x/y; stitch wires this to a clock. Exposed as rails.
    extra = {
        "x": x,
        "y": y,
        "dx": dx,
        "dy": dy,
        "cin0": cin0,
        "cin1": cin1,
        "sum_x": sum_x,
        "sum_y": sum_y,
        "we": we,
        "data": data,
        "ram_out": ram_out,
        "ram_cells": cells,
        "dec": dec,
        "hit": hit,
        "dist": dist,
        "march": march,
        "n_in": 8 + 8 + 8 + 8 + MAP_CELLS,
        "n_out": 4,
        "addr": addr,
    }
    return extra
