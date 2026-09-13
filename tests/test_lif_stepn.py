# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.snn.lif import LifNet, NetBuilder


def _xor_net() -> LifNet:
    b = NetBuilder()
    a = b.alloc("a", "BIT_LATCH")
    c = b.alloc("c", "BIT_LATCH")
    o = b.alloc("o", "BIT_LATCH")
    b.wire(a, o, 1.2)
    b.wire(c, o, 1.2)
    return b.compile()


def test_step_n_matches_step_loop() -> None:
    net = _xor_net()
    cur = np.zeros(net.n, dtype=np.float32)
    cur[0] = 1.2
    a = _xor_net()
    a.step_n(8, cur)
    b = _xor_net()
    for _ in range(8):
        b.step(cur)
    np.testing.assert_allclose(a.v, b.v, atol=1e-6)
    np.testing.assert_allclose(a.spikes, b.spikes, atol=1e-6)
