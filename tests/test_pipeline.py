# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.const import CENTER_COL, FRAME_H, N_COLS, V1_NEURON_CAP
from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.teacher.maps import spawn


def test_pipeline_builds_under_cap() -> None:
    m = build_doom_snn()
    assert m.net.n <= V1_NEURON_CAP
    assert m.net.n > 100
    mods = set(m.net.module)
    for name in (
        "CLOCK",
        "BIT_LATCH",
        "REGISTER_FILE",
        "ADDER_COMPARE",
        "RAM",
        "SEQUENCER",
        "RAY_COLUMN",
        "FRAME_READOUT",
        "DOOR",
    ):
        assert name in mods, mods


def test_pipeline_reset_and_frame_shape() -> None:
    m = build_doom_snn()
    m.reset(spawn())
    frame = m.decode_pixels()
    assert frame.shape == (FRAME_H, N_COLS)
    assert frame.dtype == np.uint8


def test_pipeline_pose_matches_teacher() -> None:
    from snn_doom.teacher.engine import tick
    from snn_doom.teacher.state import pack_input

    m = build_doom_snn()
    s0 = spawn()
    m.reset(s0)
    m.tick(0)
    st = m.read_state()
    tr = tick(s0, 0)
    assert st["px"] == tr.state.px
    assert st["py"] == tr.state.py
    assert st["ang"] == tr.state.ang
    assert st["ex"] == tr.state.ex
    assert st["ey"] == tr.state.ey
    m.reset(s0)
    m.tick(pack_input(0, 0, 1, 0))
    st = m.read_state()
    tr = tick(s0, pack_input(0, 0, 1, 0))
    assert st["px"] == tr.state.px
    pix = m.decode_pixels()
    assert (pix == 2).any()


def test_pipeline_hitscan_center_column() -> None:
    from snn_doom.teacher.engine import tick
    from snn_doom.teacher.render import hitscan

    m = build_doom_snn()
    miss = spawn()
    m.reset(miss)
    m.tick(0)
    tr = tick(miss, 0)
    assert m.read_hitscan() == hitscan(tr.state) == 0
    look = spawn(px=104, py=88, ang=48, ex=104, ey=40)
    m.reset(look)
    m.tick(0)
    tr = tick(look, 0)
    assert hitscan(tr.state) == 1
    assert m.read_hitscan() == 1


def test_pipeline_fire_miss_then_kill() -> None:
    from snn_doom.teacher.engine import tick
    from snn_doom.teacher.state import pack_input

    fire = pack_input(0, 0, 0, 0, 1)
    m = build_doom_snn()
    miss = spawn()
    m.reset(miss)
    pix = m.tick(fire)
    tr = tick(miss, fire)
    assert tr.shot == 0
    assert tr.state.enemy_alive == 1
    assert m.read_shot() == 0
    assert m.read_state()["enemy_alive"] == 1
    assert m.read_hitscan() == 0
    np.testing.assert_array_equal(pix, tr.pixels)
    look = spawn(px=104, py=88, ang=48, ex=104, ey=40)
    m.reset(look)
    pix = m.tick(fire)
    tr = tick(look, fire)
    assert tr.columns[CENTER_COL].sprite == 1
    assert tr.shot == 1
    assert tr.state.enemy_alive == 0
    assert m.read_hitscan() == 1
    assert m.read_shot() == 1
    assert m.read_state()["enemy_alive"] == 0
    np.testing.assert_array_equal(pix, tr.pixels)


def test_pipeline_death_freeze_then_rearm() -> None:
    from snn_doom.const import DEATH_TICKS
    from snn_doom.teacher.engine import tick
    from snn_doom.teacher.state import pack_input

    m = build_doom_snn()
    s0 = spawn(px=24, py=24, ex=24, ey=24)
    m.reset(s0)
    fwd = pack_input(0, 0, 1, 0)
    tr = tick(s0, 0)
    pix = m.tick(0)
    assert m.read_state()["player_hit"] == 1
    assert m.read_state()["enemy_alive"] == 0
    np.testing.assert_array_equal(pix, tr.pixels)
    held = tr.state.px
    s = tr.state
    for _ in range(DEATH_TICKS):
        tr = tick(s, fwd)
        pix = m.tick(fwd)
        st = m.read_state()
        assert st["px"] == held
        assert st["enemy_alive"] == 0
        assert st["player_hit"] == tr.state.player_hit
        np.testing.assert_array_equal(pix, tr.pixels)
        s = tr.state
    tr = tick(s, fwd)
    pix = m.tick(fwd)
    assert m.read_state()["player_hit"] == 0
    assert m.read_state()["px"] > held
    np.testing.assert_array_equal(pix, tr.pixels)


def test_pipeline_door_block_toggle_pass() -> None:
    from snn_doom.const import DOOR_X
    from snn_doom.teacher.engine import tick
    from snn_doom.teacher.maps import with_door
    from snn_doom.teacher.state import pack_input

    m = build_doom_snn()
    fwd = pack_input(0, 0, 1, 0)
    door = pack_input(0, 0, 0, 0, 0, 1)
    closed = with_door(spawn(), 1)
    m.reset(closed)
    last_px = closed.px
    blocked = False
    s = closed
    for _ in range(12):
        tr = tick(s, fwd)
        pix = m.tick(fwd)
        st = m.read_state()
        assert st["px"] == tr.state.px
        np.testing.assert_array_equal(pix, tr.pixels)
        assert m.read_door() == 1
        if tr.state.px == last_px:
            blocked = True
            break
        last_px = tr.state.px
        s = tr.state
    assert blocked
    m.reset(closed)
    tr = tick(closed, door)
    pix = m.tick(door)
    assert tr.state.px == closed.px
    assert m.read_door() == 0
    np.testing.assert_array_equal(pix, tr.pixels)
    s = tr.state
    passed = False
    for _ in range(12):
        tr = tick(s, fwd)
        pix = m.tick(fwd)
        assert m.read_state()["px"] == tr.state.px
        np.testing.assert_array_equal(pix, tr.pixels)
        s = tr.state
        if s.px >> 4 >= DOOR_X:
            passed = True
            break
    assert passed
