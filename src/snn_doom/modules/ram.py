# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.snn.digital import Rail, and2, bistable, decoder_bits, latch_write, or_n
from snn_doom.snn.lif import NetBuilder


def add_ram1(
    b: NetBuilder,
    addr: list[Rail],
    we: Rail,
    data: Rail,
    name: str,
    module: str = "RAM",
) -> tuple[list[Rail], Rail, list[int]]:
    n_cells = 1 << len(addr)
    cells = [bistable(b, f"{name}_c{i}", module) for i in range(n_cells)]
    dec = decoder_bits(b, addr, f"{name}_dec", module)
    for i, q in enumerate(cells):
        we_i = Rail(and2(b, we.t, dec[i], f"{name}_we_{i}", module), we.f)
        latch_write(b, q, we_i, data, f"{name}_w{i}", module)
    rt = [and2(b, dec[i], cells[i].t, f"{name}_rt{i}", module) for i in range(n_cells)]
    rf = [and2(b, dec[i], cells[i].f, f"{name}_rf{i}", module) for i in range(n_cells)]
    out = Rail(
        or_n(b, rt, f"{name}_out_t", module),
        or_n(b, rf, f"{name}_out_f", module),
    )
    return cells, out, dec
