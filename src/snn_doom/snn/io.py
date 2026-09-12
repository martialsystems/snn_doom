# Copyright (c) 2026 Martial Systems LLC
"""Drive dual-rail / latch neurons with currents. Host injects bits this way."""
from __future__ import annotations

import numpy as np

from snn_doom.snn.digital import Rail
from snn_doom.snn.lif import LifNet

AMP = 1.2


def zeros(net: LifNet) -> np.ndarray:
    return np.zeros(net.n, dtype=np.float32)


def drive_bit(cur: np.ndarray, rail: Rail, value: int, amp: float = AMP) -> None:
    if value:
        cur[rail.t] = amp
        cur[rail.f] = 0.0
    else:
        cur[rail.t] = 0.0
        cur[rail.f] = amp


def drive_int(cur: np.ndarray, rails: list[Rail], value: int, amp: float = AMP) -> None:
    for i, rail in enumerate(rails):
        drive_bit(cur, rail, (value >> i) & 1, amp)


def drive_index(cur: np.ndarray, idx: int, amp: float = AMP) -> None:
    cur[idx] = amp


def read_bit(spikes: np.ndarray, rail: Rail) -> int:
    t = float(spikes[rail.t])
    f = float(spikes[rail.f])
    if t >= 1.0 and f < 1.0:
        return 1
    if f >= 1.0 and t < 1.0:
        return 0
    return 1 if t > f else 0


def read_int(spikes: np.ndarray, rails: list[Rail]) -> int:
    v = 0
    for i, rail in enumerate(rails):
        v |= read_bit(spikes, rail) << i
    return v


def step_driven(net: LifNet, cur: np.ndarray, n: int) -> np.ndarray:
    s = net.spikes
    for _ in range(n):
        s = net.step(cur)
    return s
