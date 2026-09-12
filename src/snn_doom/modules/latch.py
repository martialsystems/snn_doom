# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.snn.digital import Rail, bistable, latch_write
from snn_doom.snn.lif import NetBuilder


def add_reg(b: NetBuilder, name: str, width: int, module: str = "REGISTER_FILE") -> list[Rail]:
    return [bistable(b, f"{name}_{i}", module) for i in range(width)]


def add_write(b: NetBuilder, q: list[Rail], we: Rail, data: list[Rail], name: str, module: str = "REGISTER_FILE") -> None:
    for i, (qi, di) in enumerate(zip(q, data)):
        latch_write(b, qi, we, di, f"{name}_{i}", module)
