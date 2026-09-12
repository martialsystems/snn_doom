# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.snn.digital import oscillator_ring
from snn_doom.snn.lif import NetBuilder


def add_clock(b: NetBuilder, period: int = 8) -> list[int]:
    return oscillator_ring(b, period, "CLOCK")
