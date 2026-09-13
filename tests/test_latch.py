# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.demo.latch import InputLatch
from snn_doom.teacher.state import pack_input


def test_fire_and_door_are_one_shots() -> None:
    lat = InputLatch()
    lat.press(("space", "e"))
    bits, flash, _ = lat.consume()
    assert bits == pack_input(0, 0, 0, 0, 1, 1)
    assert flash.get("muzzle")
    assert flash.get("door")
    bits2, flash2, _ = lat.consume()
    assert bits2 == 0
    assert not flash2


def test_fwd_lock() -> None:
    lat = InputLatch(fwd_lock=True)
    bits, _, shown = lat.consume()
    assert bits == pack_input(0, 0, 1, 0)
    assert "up" in shown
