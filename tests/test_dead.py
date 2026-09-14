# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.const import (
    DEFAULT_AMMO,
    DEFAULT_ANG,
    DEFAULT_HP,
    DEFAULT_PX,
    DEFAULT_PY,
    FRAME_H,
    N_COLS,
    V1_NEURON_CAP,
)
from snn_doom.demo.dead import HostDead, restore_spawn
from snn_doom.teacher.maps import spawn


def test_splash_latches_when_hp_zero() -> None:
    from snn_doom.modules.pipeline import build_doom_snn

    m = build_doom_snn()
    m.reset(spawn(px=24, py=24, ex=24, ey=24, hp=1))
    host = HostDead()
    assert host.dead is False
    pix = m.tick(0)
    st = m.read_state()
    assert st["hp"] == 0
    assert host.observe_hp(st["hp"]) is True
    assert host.dead is True
    np.testing.assert_array_equal(pix, m.decode_pixels())
    assert pix.shape == (FRAME_H, N_COLS)
    assert host.gate_bits(0b111111) == 0
    assert m.net.n == 7973
    assert m.net.n <= V1_NEURON_CAP


def test_splash_does_not_write_frame_buffer() -> None:
    from snn_doom.modules.pipeline import build_doom_snn

    m = build_doom_snn()
    m.reset(spawn(px=24, py=24, ex=24, ey=24, hp=1))
    m.tick(0)
    before = m.decode_pixels().copy()
    host = HostDead()
    host.observe_hp(0)
    banner = host.tty_banner()
    after = m.decode_pixels()
    np.testing.assert_array_equal(before, after)
    assert "YOU DIED" in banner
    assert "R restart" in banner
    assert "HOST_DEAD" in banner


def test_restart_restores_spawn_defaults() -> None:
    from snn_doom.modules.pipeline import build_doom_snn

    m = build_doom_snn()
    m.reset(spawn(px=24, py=24, ex=24, ey=24, hp=1))
    m.tick(0)
    assert m.read_state()["hp"] == 0
    host = HostDead()
    host.observe_hp(0)
    st = restore_spawn(m, spawn())
    host.hide()
    assert host.dead is False
    assert st["px"] == DEFAULT_PX
    assert st["py"] == DEFAULT_PY
    assert st["ang"] == DEFAULT_ANG
    assert st["hp"] == DEFAULT_HP
    assert st["ammo"] == DEFAULT_AMMO
    assert st["player_hit"] == 0


def test_demo_path_and_neuron_count() -> None:
    from pathlib import Path

    from doomforge.evidence import scan_demo_banned_hits, v1_neurons
    from doomforge.gate import require_demo_path

    require_demo_path()
    assert scan_demo_banned_hits() == []
    assert v1_neurons() == 7973
    dead_src = (Path(__file__).resolve().parents[1] / "src" / "snn_doom" / "demo" / "dead.py").read_text(
        encoding="utf-8"
    )
    assert "teacher.tick" not in dead_src
    assert "cast_ray(" not in dead_src
    assert "apply_enemy" not in dead_src
    assert "apply_move" not in dead_src
    assert "paint_frame" not in dead_src
    assert "build_doom_snn" not in dead_src


def test_no_dead_still_closes_on_lose() -> None:
    from snn_doom.demo.round import RoundState

    rnd = RoundState(limit=64)
    assert rnd.observe({"enemy_alive": 1, "enemy2_alive": 1, "hp": 0, "player_hit": 1}) == "lose"
