# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.snn.digital import oscillator_ring
from snn_doom.snn.lif import NetBuilder


def add_ring(b: NetBuilder, n: int, module: str = "SEQUENCER") -> list[int]:
    return oscillator_ring(b, n, module)
