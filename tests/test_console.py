# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.const import DOOR_IDX, DOOR_X, DOOR_Y, FRAME_H, N_COLS
from snn_doom.demo.console import _silence_mpl_keys, render_tty, run_console
from snn_doom.demo.view import (
    COLOR_DOOR_CLOSED,
    COLOR_DOOR_OPEN,
    COLOR_E2,
    COLOR_FLOOR,
    COLOR_PLAYER,
    ingest_key,
    keys_to_bits,
    map_rgb,
)
from snn_doom.teacher.maps import DEFAULT_ROWS, parse_map, spawn
from snn_doom.teacher.state import pack_input


def test_ingest_key_aliases() -> None:
    assert ingest_key("w") == ("up",)
    assert ingest_key("a") == ("left",)
    assert ingest_key("s") == ("down",)
    assert ingest_key("d") == ("right",)
    assert ingest_key(" ") == ("space",)
    assert ingest_key("f") == ("space",)
    assert ingest_key("ctrl+w") == ("space",)
    assert ingest_key("e") == ("e",)
    assert ingest_key("q") == ("e",)
    assert ingest_key("escape") == ("escape",)
    assert keys_to_bits(set()) == 0
    assert keys_to_bits({"up"}) == pack_input(0, 0, 1, 0)
    assert keys_to_bits({"w"}) == pack_input(0, 0, 1, 0)
    assert keys_to_bits({"space"}) == pack_input(0, 0, 0, 0, 1, 0)
    assert keys_to_bits({"e"}) == pack_input(0, 0, 0, 0, 0, 1)


def test_map_rgb_marks_door_e2_player() -> None:
    open_bits = parse_map(DEFAULT_ROWS)
    closed = open_bits | (1 << DOOR_IDX)
    img_o = map_rgb(
        open_bits,
        24,
        88,
        104,
        40,
        ang=0,
        enemy_alive=1,
        ex2=40,
        ey2=40,
        enemy2_alive=1,
    )
    img_c = map_rgb(
        closed,
        24,
        88,
        104,
        40,
        ang=0,
        enemy_alive=1,
        ex2=40,
        ey2=40,
        enemy2_alive=1,
    )
    scale = 16
    assert tuple(img_o[DOOR_Y * scale + 8, DOOR_X * scale + 8]) == COLOR_DOOR_OPEN
    assert tuple(img_c[DOOR_Y * scale + 8, DOOR_X * scale + 8]) == COLOR_DOOR_CLOSED
    assert tuple(img_o[40, 40]) == COLOR_E2
    assert tuple(img_o[88, 24]) == COLOR_PLAYER
    img_dead = map_rgb(open_bits, 24, 88, 104, 40, enemy2_alive=0, ex2=40, ey2=40)
    assert tuple(img_dead[40, 40]) == COLOR_FLOOR


def test_render_tty_shows_entities() -> None:
    s = spawn()
    st = {
        "px": s.px,
        "py": s.py,
        "ang": s.ang,
        "ex": s.ex,
        "ey": s.ey,
        "enemy_alive": 1,
        "ex2": s.ex2,
        "ey2": s.ey2,
        "enemy2_alive": 1,
        "ammo": 7,
        "player_hit": 0,
    }
    pixels = np.zeros((FRAME_H, N_COLS), dtype=np.uint8)
    pixels[0, 0] = 2
    text = render_tty(
        pixels,
        st,
        s.map_bits,
        pressed={"up"},
        tps=1.0,
        n_neurons=7958,
        spikes_per_step=1.0,
        door=0,
    )
    assert "snn_doom console" in text
    assert "P" in text
    assert "1" in text
    assert "2" in text
    assert "ammo 7" in text
    assert text.splitlines()[1].startswith("W")
    assert "—" not in text
    assert "What it is not" not in text


def test_silence_mpl_keys_drops_game_collisions() -> None:
    import matplotlib as mpl

    names = ("keymap.quit", "keymap.save", "keymap.fullscreen")
    old = {k: list(mpl.rcParams[k]) for k in names}
    try:
        _silence_mpl_keys()
        for key in names:
            assert list(mpl.rcParams[key]) == []
    finally:
        for k, v in old.items():
            mpl.rcParams[k] = v


def test_console_host_fwd_tick() -> None:
    stats = run_console(display=False, tty=False, ticks=1, pressed={"up"}, record=False, sound=False)
    assert stats["ticks"] == 1
    assert stats["state"]["px"] == 28
    assert stats["state"]["py"] == 88
    assert stats["pixels"].shape == (FRAME_H, N_COLS)
    assert stats["map_bits"] == spawn().map_bits


def test_headless_run_demo_png(tmp_path) -> None:
    from snn_doom.demo.view import run_demo

    out = tmp_path / "demo.png"
    stats = run_demo(frames=1, out=out, inputs=[0])
    assert out.is_file()
    assert out.stat().st_size > 0
    assert stats["state"]["px"] == 24
    assert stats["pixels"].shape == (FRAME_H, N_COLS)
