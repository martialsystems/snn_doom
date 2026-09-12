# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.snn.digital import Rail, adder_n, and2, or_n
from snn_doom.snn.lif import NetBuilder


def add_adder(
    b: NetBuilder,
    a: list[Rail],
    c: list[Rail],
    cin: Rail,
    name: str,
    module: str = "ADDER_COMPARE",
) -> tuple[list[Rail], Rail]:
    return adder_n(b, a, c, cin, name, module)


def add_gt(
    b: NetBuilder,
    a: list[Rail],
    c: list[Rail],
    name: str,
    module: str = "ADDER_COMPARE",
    bias: int | None = None,
) -> Rail:
    """Unsigned a > c, MSB first."""
    gt_terms: list[int] = []
    eq_so_far: int | None = None
    width = len(a)
    for i in reversed(range(width)):
        gt_i = and2(b, a[i].t, c[i].f, f"{name}_gt_{i}", module)
        eq_t = and2(b, a[i].t, c[i].t, f"{name}_eqt_{i}", module)
        eq_f = and2(b, a[i].f, c[i].f, f"{name}_eqf_{i}", module)
        eq_i = or_n(b, [eq_t, eq_f], f"{name}_eq_{i}", module)
        if eq_so_far is None:
            gt_terms.append(gt_i)
            eq_so_far = eq_i
        else:
            gt_terms.append(and2(b, gt_i, eq_so_far, f"{name}_gtp_{i}", module))
            eq_so_far = and2(b, eq_i, eq_so_far, f"{name}_eqs_{i}", module)
    t = or_n(b, gt_terms, f"{name}_gt_t", module)
    f = b.alloc(f"{name}_gt_f", module)
    if bias is None:
        bias = b.alloc(f"{name}_bias", module)
        b.wire(bias, bias, 1.2)
    b.wire(t, f, -2.4)
    b.wire(bias, f, 1.2)
    return Rail(t, f)
