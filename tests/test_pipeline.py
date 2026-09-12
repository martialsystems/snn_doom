# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.const import FRAME_H, N_COLS, V1_NEURON_CAP
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
