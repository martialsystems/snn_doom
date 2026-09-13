# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.const import DOOR_IDX, SETTLE_STEPS
from snn_doom.modules.ram import add_ram1
from snn_doom.snn.digital import Rail, latch_write
from snn_doom.snn.io import drive_bit, drive_int, read_bit, zeros
from snn_doom.snn.lif import NetBuilder


def test_ram_write_set_bit_reads_back_within_settle() -> None:
    b = NetBuilder()
    addr = [Rail(*b.alloc_pair(f"a{i}", "RAM")) for i in range(6)]
    we = Rail(*b.alloc_pair("we", "RAM"))
    data = Rail(*b.alloc_pair("d", "RAM"))
    cells, out, _dec = add_ram1(b, addr, we, data, "map", "RAM")
    net = b.compile()
    net.reset()
    last = None
    for _ in range(SETTLE_STEPS):
        cur = zeros(net)
        drive_int(cur, addr, DOOR_IDX)
        drive_bit(cur, we, 1)
        drive_bit(cur, data, 1)
        last = net.step(cur)
    assert read_bit(last, cells[DOOR_IDX]) == 1
    assert read_bit(last, out) == 1


def test_ram_toggle_latch_write_settles_at_budget() -> None:
    b = NetBuilder()
    addr = [Rail(*b.alloc_pair(f"a{i}", "RAM")) for i in range(6)]
    we_never = Rail(*b.alloc_pair("we0", "RAM"))
    data = Rail(*b.alloc_pair("d", "RAM"))
    cells, _out, _dec = add_ram1(b, addr, we_never, data, "map", "RAM")
    we = Rail(*b.alloc_pair("we", "DOOR"))
    tog = Rail(cells[DOOR_IDX].f, cells[DOOR_IDX].t)
    latch_write(b, cells[DOOR_IDX], we, tog, "door_tog", "DOOR")
    net = b.compile()
    net.reset()
    for _ in range(8):
        cur = zeros(net)
        drive_bit(cur, cells[DOOR_IDX], 0)
        drive_bit(cur, we, 0)
        net.step(cur)
    assert read_bit(net.spikes, cells[DOOR_IDX]) == 0
    last = None
    for t in range(SETTLE_STEPS):
        cur = zeros(net)
        drive_bit(cur, we, 1 if t < 2 else 0)
        last = net.step(cur)
    assert read_bit(last, cells[DOOR_IDX]) == 1
