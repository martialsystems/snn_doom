# Copyright (c) 2026 Martial Systems LLC
"""Dual-rail / bistable LIF gates. tau=0: v=I, spike iff weighted input >= 1."""
from __future__ import annotations

from dataclasses import dataclass

from snn_doom.snn.lif import NetBuilder

W_AND2 = 0.6
W_AND3 = 0.4
W_AND6 = 0.2
W_OR = 1.2
W_HOLD = 1.2
W_INH = -2.4
W_FORCE = 4.0
W_KICK = 1.2


@dataclass(frozen=True, slots=True)
class Rail:
    t: int
    f: int


def and2(b: NetBuilder, a: int, c: int, name: str, module: str) -> int:
    n = b.alloc(name, module)
    b.wire(a, n, W_AND2)
    b.wire(c, n, W_AND2)
    return n


def and3(b: NetBuilder, a: int, c: int, d: int, name: str, module: str) -> int:
    n = b.alloc(name, module)
    b.wire(a, n, W_AND3)
    b.wire(c, n, W_AND3)
    b.wire(d, n, W_AND3)
    return n


def or_n(b: NetBuilder, srcs: list[int], name: str, module: str) -> int:
    n = b.alloc(name, module)
    for s in srcs:
        b.wire(s, n, W_OR)
    return n


def xor_rail(b: NetBuilder, a: Rail, c: Rail, name: str, module: str) -> Rail:
    tf = and2(b, a.t, c.f, f"{name}_tf", module)
    ft = and2(b, a.f, c.t, f"{name}_ft", module)
    tt = and2(b, a.t, c.t, f"{name}_tt", module)
    ff = and2(b, a.f, c.f, f"{name}_ff", module)
    t = or_n(b, [tf, ft], f"{name}_t", module)
    f = or_n(b, [tt, ff], f"{name}_f", module)
    return Rail(t, f)


def or_rail(b: NetBuilder, a: Rail, c: Rail, name: str, module: str) -> Rail:
    t = or_n(b, [a.t, c.t], f"{name}_t", module)
    f = and2(b, a.f, c.f, f"{name}_f", module)
    return Rail(t, f)


def and_rail(b: NetBuilder, a: Rail, c: Rail, name: str, module: str) -> Rail:
    t = and2(b, a.t, c.t, f"{name}_t", module)
    f = or_n(b, [a.f, c.f], f"{name}_f", module)
    return Rail(t, f)


def const_bias(b: NetBuilder, module: str = "CLOCK") -> int:
    n = b.alloc("bias", module)
    b.wire(n, n, W_HOLD)
    return n


def oscillator_ring(b: NetBuilder, period: int, module: str = "CLOCK") -> list[int]:
    cells = [b.alloc(f"clk_{i}", module) for i in range(period)]
    for i, n in enumerate(cells):
        b.wire(n, cells[(i + 1) % period], W_KICK)
    return cells


def gated_ring(b: NetBuilder, period: int, gate: int, module: str) -> list[int]:
    """One-hot ring that advances only when `gate` spikes."""
    cells = [b.alloc(f"{module}_s{i}", module) for i in range(period)]
    for i, n in enumerate(cells):
        b.wire(n, n, W_HOLD)
        adv = and2(b, n, gate, f"{module}_adv{i}", module)
        b.wire(adv, n, W_INH)
        b.wire(adv, cells[(i + 1) % period], W_FORCE)
    return cells


def bistable(b: NetBuilder, name: str, module: str) -> Rail:
    t = b.alloc(f"{name}_t", module)
    f = b.alloc(f"{name}_f", module)
    b.wire(t, t, W_HOLD)
    b.wire(f, f, W_HOLD)
    b.wire(t, f, W_INH)
    b.wire(f, t, W_INH)
    return Rail(t, f)


def latch_write(b: NetBuilder, q: Rail, we: Rail, data: Rail, name: str, module: str) -> None:
    set_t = and2(b, we.t, data.t, f"{name}_set_t", module)
    set_f = and2(b, we.t, data.f, f"{name}_set_f", module)
    b.wire(set_t, q.t, W_FORCE)
    b.wire(set_t, q.f, W_INH)
    b.wire(set_f, q.f, W_FORCE)
    b.wire(set_f, q.t, W_INH)


def full_adder(b: NetBuilder, a: Rail, c: Rail, cin: Rail, name: str, module: str) -> tuple[Rail, Rail]:
    axb = xor_rail(b, a, c, f"{name}_axb", module)
    s = xor_rail(b, axb, cin, f"{name}_sum", module)
    ab = and_rail(b, a, c, f"{name}_ab", module)
    ac = and_rail(b, a, cin, f"{name}_ac", module)
    bc = and_rail(b, c, cin, f"{name}_bc", module)
    cout1 = or_rail(b, ab, ac, f"{name}_c1", module)
    cout = or_rail(b, cout1, bc, f"{name}_cout", module)
    return s, cout


def adder_n(b: NetBuilder, a: list[Rail], c: list[Rail], cin: Rail, name: str, module: str) -> tuple[list[Rail], Rail]:
    if len(a) != len(c):
        raise ValueError("adder width mismatch")
    sums: list[Rail] = []
    carry = cin
    for i, (ai, ci) in enumerate(zip(a, c)):
        s, carry = full_adder(b, ai, ci, carry, f"{name}_{i}", module)
        sums.append(s)
    return sums, carry


def mux_rail(b: NetBuilder, sel: Rail, a: Rail, c: Rail, name: str, module: str) -> Rail:
    """sel.t chooses a, sel.f chooses c."""
    at = and2(b, sel.t, a.t, f"{name}_at", module)
    af = and2(b, sel.t, a.f, f"{name}_af", module)
    ct = and2(b, sel.f, c.t, f"{name}_ct", module)
    cf = and2(b, sel.f, c.f, f"{name}_cf", module)
    return Rail(or_n(b, [at, ct], f"{name}_t", module), or_n(b, [af, cf], f"{name}_f", module))


def mux_int(b: NetBuilder, sel: Rail, a: list[Rail], c: list[Rail], name: str, module: str) -> list[Rail]:
    return [mux_rail(b, sel, ai, ci, f"{name}_{i}", module) for i, (ai, ci) in enumerate(zip(a, c))]


def decoder_bits(b: NetBuilder, addr: list[Rail], name: str, module: str) -> list[int]:
    nbits = len(addr)
    nout = 1 << nbits
    w = 1.1 / nbits
    lines = []
    for i in range(nout):
        cell = b.alloc(f"{name}_{i}", module)
        for bit, rail in enumerate(addr):
            src = rail.t if (i >> bit) & 1 else rail.f
            b.wire(src, cell, w)
        lines.append(cell)
    return lines
