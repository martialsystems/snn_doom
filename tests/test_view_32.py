# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from snn_doom.const import (
    CENTER_COL,
    CENTER_COL_32,
    FRAME_H,
    FOV_HALF_32,
    N_ANG,
    N_COLS,
    N_COLS_32,
    STEPS_PER_TICK,
    STEPS_PER_TICK_32,
    VIEW_16,
    VIEW_32,
    V1_NEURON_CAP,
    V2_NEURON_CAP,
)
from snn_doom.teacher.engine import tick, tick_v2, tick_v2_32
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.render import cast_frame, column_angle, hitscan, paint_frame
from snn_doom.teacher.state import pack_input

REPO = Path(__file__).resolve().parents[1]


def test_16_col_constants_hold() -> None:
    assert N_COLS == 16
    assert CENTER_COL == 8
    assert VIEW_16.n_cols == 16
    assert VIEW_16.center_col == 8
    assert N_COLS_32 == 32
    assert FOV_HALF_32 == 16
    assert CENTER_COL_32 == 16
    assert VIEW_32.n_cols == 32
    assert VIEW_32.center_col == 16
    assert STEPS_PER_TICK_32 == 29 * (5 + 32 * 16 + 1)
    assert STEPS_PER_TICK_32 > STEPS_PER_TICK
    assert V2_NEURON_CAP == 12_000
    assert V1_NEURON_CAP == 8_000


def test_32_col_fan_is_integer_and_heading_is_center() -> None:
    angs = [column_angle(0, c, view=VIEW_32) for c in range(N_COLS_32)]
    assert angs[0] == (0 - FOV_HALF_32) % N_ANG
    assert angs[CENTER_COL_32] == 0
    assert len(set(angs)) == N_COLS_32
    assert column_angle(0, CENTER_COL_32, view=VIEW_32) == 0
    sixteen = [column_angle(0, c) for c in range(N_COLS)]
    assert sixteen[CENTER_COL] == 0
    assert len(set(sixteen)) == N_COLS


def test_tick_v2_32_paints_32x18_and_16_col_ticks_hold() -> None:
    s = spawn()
    r16 = tick(s, 0)
    r2 = tick_v2(s, 0)
    r32 = tick_v2_32(s, 0)
    assert r16.pixels.shape == (FRAME_H, N_COLS)
    assert r2.pixels.shape == (FRAME_H, N_COLS)
    assert r32.pixels.shape == (FRAME_H, N_COLS_32)
    assert len(r32.columns) == 32
    assert r16.state.ex2 == s.ex2
    assert r2.state.ex2 != s.ex2 or r2.state.ey2 != s.ey2
    assert r32.state.ex2 == r2.state.ex2
    assert r32.state.ey2 == r2.state.ey2


def test_32_col_heading_hitscan_and_fire_stay_one_gun() -> None:
    miss = spawn()
    r = tick_v2_32(miss, 0)
    assert hitscan(r.state, view=VIEW_32) == 0
    assert r.columns[CENTER_COL_32].sprite == 0
    look = spawn(px=104, py=88, ang=48, ex=104, ey=40)
    idle = tick_v2_32(look, 0)
    assert column_angle(idle.state.ang, CENTER_COL_32, view=VIEW_32) == idle.state.ang
    assert idle.columns[CENTER_COL_32].sprite == 1
    fire = pack_input(0, 0, 0, 0, 1)
    shot = tick_v2_32(look, fire)
    assert shot.shot == 1
    assert shot.state.enemy_alive == 0
    assert shot.state.enemy2_alive == 1
    east = tick_v2_32(spawn(), fire)
    assert east.shot == 0
    assert east.state.enemy_alive == 1
    assert east.state.ammo == spawn().ammo - 1


def test_32_col_distances_are_max_dist_ints() -> None:
    s = spawn()
    r = tick_v2_32(s, 0)
    dists = [c.dist for c in r.columns]
    assert len(dists) == 32
    assert all(0 <= d <= 15 for d in dists)
    again = tick_v2_32(s, 0)
    assert [c.dist for c in again.columns] == dists
    painted = paint_frame(r.columns, view=VIEW_32)
    np.testing.assert_array_equal(painted, r.pixels)


def test_teacher_ray_32_log() -> None:
    from snn_doom.ray_parity import CASES, write_teacher_ray_32

    payload = write_teacher_ray_32()
    path = REPO / "logs" / "teacher_ray_32.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["n_cols"] == 32
    assert data["view"] == "VIEW_32"
    assert len(data["cases"]) == len(CASES)
    for case in data["cases"]:
        assert len(case["teacher"]) == 32
        assert all(isinstance(d, int) and 0 <= d <= 15 for d in case["teacher"])
    assert payload == data


def test_play_v2_32_fail_closed_without_stitch() -> None:
    from snn_doom.play import _v2_32_ready, main as play_main

    ckpt = REPO / "checkpoints" / "snn_doom_v2_32.json"
    tape = REPO / "logs" / "tick_tape_v2_32.json"
    if ckpt.is_file() and tape.is_file():
        return
    ok, why = _v2_32_ready()
    assert ok is False
    assert "v2_32" in why or "32" in why
    assert play_main(["--machine", "v2_32", "--ticks", "1"]) == 2


def test_v1_v2_checkpoints_unmoved() -> None:
    v1 = json.loads((REPO / "checkpoints" / "snn_doom_v1.json").read_text(encoding="utf-8"))
    v2 = json.loads((REPO / "checkpoints" / "snn_doom_v2.json").read_text(encoding="utf-8"))
    assert v1["n_neurons"] == 7973
    assert v1["cap"] == 8000
    assert v2["n_neurons"] == 9077
    assert v2["cap"] == 12000
    play = (REPO / "src" / "snn_doom" / "play.py").read_text(encoding="utf-8")
    assert 'default="v1"' in play
    assert "v2_32" in play


def test_docs_v2_32_prose() -> None:
    path = REPO / "docs" / "v2_32.md"
    text = path.read_text(encoding="utf-8")
    assert "—" not in text
    assert "What it is not" not in text
    assert "32 columns" in text
    assert "doom.v2_cap" in text
    assert "snn_doom_v2_32.json" in text
    assert "tick_v2_32" in text
