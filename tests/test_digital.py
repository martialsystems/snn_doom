# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.snn.digital import Rail, adder_n, bistable, const_bias, latch_write, oscillator_ring
from snn_doom.snn.io import drive_bit, drive_index, drive_int, read_int, zeros
from snn_doom.snn.lif import NetBuilder


def test_oscillator_period() -> None:
    b = NetBuilder()
    cells = oscillator_ring(b, 8, "CLOCK")
    net = b.compile()
    net.reset()
    cur = zeros(net)
    drive_index(cur, cells[0])
    hits = []
    for t in range(24):
        s = net.step(cur if t == 0 else zeros(net))
        hits.append(int(s[cells[0]] >= 1.0))
    # kicked cell spikes at 0, then every 8
    assert hits[0] == 1
    assert hits[8] == 1
    assert hits[16] == 1
    assert sum(hits) == 3


def test_bistable_holds() -> None:
    b = NetBuilder()
    q = bistable(b, "q", "BIT_LATCH")
    we = Rail(*b.alloc_pair("we", "BIT_LATCH"))
    d = Rail(*b.alloc_pair("d", "BIT_LATCH"))
    latch_write(b, q, we, d, "w", "BIT_LATCH")
    net = b.compile()
    net.reset()
    for _ in range(4):
        cur = zeros(net)
        drive_bit(cur, we, 1)
        drive_bit(cur, d, 1)
        net.step(cur)
    for _ in range(20):
        s = net.step(zeros(net))
        assert s[q.t] >= 1.0
        assert s[q.f] < 1.0
    for _ in range(4):
        cur = zeros(net)
        drive_bit(cur, we, 1)
        drive_bit(cur, d, 0)
        net.step(cur)
    for _ in range(20):
        s = net.step(zeros(net))
        assert s[q.f] >= 1.0
        assert s[q.t] < 1.0


def test_four_bit_adder() -> None:
    b = NetBuilder()
    a = [Rail(*b.alloc_pair(f"a{i}", "ADDER_COMPARE")) for i in range(4)]
    c = [Rail(*b.alloc_pair(f"c{i}", "ADDER_COMPARE")) for i in range(4)]
    cin = Rail(*b.alloc_pair("cin", "ADDER_COMPARE"))
    sums, cout = adder_n(b, a, c, cin, "s", "ADDER_COMPARE")
    net = b.compile()
    cases = [(0, 0), (1, 2), (7, 8), (15, 1), (5, 11)]
    for av, cv in cases:
        net.reset()
        last = None
        for _ in range(20):
            cur = zeros(net)
            drive_int(cur, a, av)
            drive_int(cur, c, cv)
            drive_bit(cur, cin, 0)
            last = net.step(cur)
        got = read_int(last, sums)
        want = (av + cv) & 15
        assert got == want, f"{av}+{cv} got {got} want {want} cout={last[cout.t]}"


def test_eight_bit_add_settles_within_budget() -> None:
    from snn_doom.const import SETTLE_STEPS
    from snn_doom.snn.digital import Rail, adder_n
    from snn_doom.snn.io import drive_bit, drive_int, read_int, zeros
    from snn_doom.snn.lif import NetBuilder

    b = NetBuilder()
    a = [Rail(*b.alloc_pair(f"a{i}", "ADDER_COMPARE")) for i in range(8)]
    c = [Rail(*b.alloc_pair(f"c{i}", "ADDER_COMPARE")) for i in range(8)]
    cin = Rail(*b.alloc_pair("cin", "ADDER_COMPARE"))
    sums, _cout = adder_n(b, a, c, cin, "s", "ADDER_COMPARE")
    net = b.compile()
    # 30+6 dropped bit 5 at 11 steps. 127+1 is 0 at 23 steps, exact at 24.
    assert SETTLE_STEPS >= 24
    for av, cv, want in ((30, 6, 36), (24, 6, 30), (127, 1, 128), (88, 250, 82)):
        net.reset()
        last = None
        for _ in range(SETTLE_STEPS):
            cur = zeros(net)
            drive_int(cur, a, av)
            drive_int(cur, c, cv)
            drive_bit(cur, cin, 0)
            last = net.step(cur)
        got = read_int(last, sums)
        assert got == want, f"{av}+{cv} got {got} want {want}"
    # Floor: one step under the 127+1 first_ok is a miss.
    net.reset()
    last = None
    for _ in range(23):
        cur = zeros(net)
        drive_int(cur, a, 127)
        drive_int(cur, c, 1)
        drive_bit(cur, cin, 0)
        last = net.step(cur)
    assert read_int(last, sums) != 128


def test_bias_stays_on() -> None:
    b = NetBuilder()
    n = const_bias(b)
    net = b.compile()
    net.reset()
    cur = zeros(net)
    drive_index(cur, n)
    net.step(cur)
    for _ in range(10):
        s = net.step(zeros(net))
        assert s[n] >= 1.0
