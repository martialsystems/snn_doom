# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.const import CELL, FRAME_H, N_COLS, V1_NEURON_CAP
from snn_doom.demo.radar import RADAR_SIZE, facing_char, radar_marks_player_cell, radar_rgb
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.state import pack_input


def test_facing_char_quarters() -> None:
    assert facing_char(0) == ">"
    assert facing_char(16) == "v"
    assert facing_char(32) == "<"
    assert facing_char(48) == "^"


def test_radar_marks_spawn_player_cell() -> None:
    s = spawn()
    st = {
        "px": s.px,
        "py": s.py,
        "ang": s.ang,
        "ex": s.ex,
        "ey": s.ey,
        "enemy_alive": s.enemy_alive,
        "ex2": s.ex2,
        "ey2": s.ey2,
        "enemy2_alive": s.enemy2_alive,
        "door": 0,
    }
    img = radar_rgb(s.map_bits, st, door=0)
    assert img.shape == (RADAR_SIZE, RADAR_SIZE, 3)
    assert radar_marks_player_cell(img, s.px, s.py)
    assert (s.px // CELL, s.py // CELL) == (1, 5)


def test_radar_does_not_mutate_frame_buffer() -> None:
    from snn_doom.modules.pipeline import build_doom_snn

    m = build_doom_snn()
    m.reset(spawn())
    before = m.decode_pixels().copy()
    st = m.read_state()
    radar_rgb(m.read_map_bits(), st, door=m.read_door())
    after = m.decode_pixels()
    np.testing.assert_array_equal(before, after)
    assert after.shape == (FRAME_H, N_COLS)


def test_play_pixels_match_decode_with_radar_on() -> None:
    from snn_doom.demo.console import run_console
    from snn_doom.modules.pipeline import build_doom_snn

    m = build_doom_snn()
    stats = run_console(
        machine=m,
        display=False,
        tty=False,
        ticks=1,
        radar=True,
        record=False,
        sound=False,
    )
    np.testing.assert_array_equal(stats["pixels"], m.decode_pixels())
    assert stats["n_neurons"] <= V1_NEURON_CAP
    m2 = build_doom_snn()
    m2.reset(spawn())
    pix = m2.tick(0)
    np.testing.assert_array_equal(stats["pixels"], pix)


def test_enemy2_still_out_of_tick() -> None:
    from snn_doom.teacher.engine import apply_enemy2, tick

    s = spawn()
    nxt = apply_enemy2(s)
    assert nxt.ex2 != s.ex2 or nxt.ey2 != s.ey2
    idle = tick(s, 0)
    assert idle.state.ex2 == s.ex2
    assert idle.state.ey2 == s.ey2
    assert pack_input(0, 0, 0, 0) == 0
