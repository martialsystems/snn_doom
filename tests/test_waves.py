# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.const import FRAME_H, N_COLS, V1_NEURON_CAP
from snn_doom.demo.round import RoundState
from snn_doom.demo.waves import HostWaves, heading_and_fov_cells
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.state import pack_input


def _last(m) -> dict:
    return {
        "pixels": m.decode_pixels(),
        "state": m.read_state(),
        "map_bits": m.read_map_bits(),
        "door": m.read_door(),
    }


def test_kill_e1_stays_play_then_respawns() -> None:
    from snn_doom.modules.pipeline import build_doom_snn

    m = build_doom_snn()
    look = spawn(px=104, py=88, ang=48, ex=104, ey=40)
    m.reset(look)
    fire = pack_input(0, 0, 0, 0, 1)
    m.tick(fire)
    last = _last(m)
    assert last["state"]["enemy_alive"] == 0
    rnd = RoundState()
    rnd.e1_was = 1
    rnd.e2_was = 1
    assert rnd.observe(last["state"]) == "play"
    assert rnd.score == 1
    waves = HostWaves(seed=7, quiet=1)
    last = waves.follow(m, last, tick=1, score=rnd.score)
    assert last["state"]["enemy_alive"] == 0
    m.tick(0)
    last = _last(m)
    last = waves.follow(m, last, tick=2, score=rnd.score)
    st = last["state"]
    assert st["enemy_alive"] == 1
    cell = (st["ex"] >> 4, st["ey"] >> 4)
    assert cell != (look.px >> 4, look.py >> 4)
    assert cell != (look.ex2 >> 4, look.ey2 >> 4)
    heading, fov = heading_and_fov_cells(st["px"], st["py"], st["ang"], last["map_bits"])
    if heading is not None:
        assert cell != heading
    np.testing.assert_array_equal(last["pixels"], m.decode_pixels())
    assert last["pixels"].shape == (FRAME_H, N_COLS)
    assert waves.log and waves.log[0]["who"] == "e1"
    assert waves.log[0]["seed"] == 7
    assert m.net.n == 7973
    assert m.net.n <= V1_NEURON_CAP


def test_no_waves_kill_does_not_quit_policy() -> None:
    from snn_doom.modules.pipeline import build_doom_snn

    rnd = RoundState()
    live = {"enemy_alive": 0, "enemy2_alive": 1, "hp": 3, "player_hit": 0}
    assert rnd.observe(live) == "play"
    assert rnd.score == 1
    m = build_doom_snn()
    look = spawn(px=104, py=88, ang=48, ex=104, ey=40)
    m.reset(look)
    m.tick(pack_input(0, 0, 0, 0, 1))
    last = _last(m)
    assert last["state"]["enemy_alive"] == 0
    waves = HostWaves(enabled=False, seed=7)
    m.tick(0)
    last = _last(m)
    last = waves.follow(m, last, tick=2, score=1)
    assert last["state"]["enemy_alive"] == 0
    assert rnd.observe(last["state"]) == "play"


def test_decode_identity_with_radar_dead_waves() -> None:
    from snn_doom.demo.console import run_console
    from snn_doom.modules.pipeline import build_doom_snn

    m = build_doom_snn()
    stats = run_console(
        machine=m,
        display=False,
        tty=False,
        ticks=1,
        radar=True,
        splash=True,
        waves=True,
        record=False,
        sound=False,
    )
    np.testing.assert_array_equal(stats["pixels"], m.decode_pixels())
    assert stats["n_neurons"] == 7973


def test_waves_demo_path() -> None:
    from pathlib import Path

    from doomforge.evidence import scan_demo_banned_hits, v1_neurons
    from doomforge.gate import require_demo_path

    require_demo_path()
    assert scan_demo_banned_hits() == []
    assert v1_neurons() == 7973
    src = (Path(__file__).resolve().parents[1] / "src" / "snn_doom" / "demo" / "waves.py").read_text(
        encoding="utf-8"
    )
    assert "teacher.tick" not in src
    assert "cast_ray(" not in src
    assert "apply_enemy" not in src
    assert "apply_move" not in src
    assert "paint_frame" not in src


def test_host_waves_qol_is_waste() -> None:
    from pathlib import Path

    from snn_doom.qol.auditor import audit_proposal, load_proposal

    r = audit_proposal(load_proposal(Path(__file__).resolve().parents[1] / "proposals" / "host_waves.yaml"))
    assert r["verdict"] == "REJECT_WASTE"
    assert r["estimated_new_neurons"] == 0
