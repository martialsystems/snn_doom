# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np
import pytest

from snn_doom.const import (
    CENTER_COL,
    COLOR_ENEMY,
    COLOR_WALL,
    COS,
    DOOR_X,
    DOOR_Y,
    FRAME_H,
    N_ANG,
    N_COLS,
    STATE_BITS,
    WORLD,
)
from snn_doom.teacher.engine import (
    apply_door,
    apply_enemy,
    apply_enemy2,
    apply_fire,
    apply_move,
    apply_pickup,
    apply_turn,
    run,
    tick,
)
from snn_doom.teacher.maps import DEFAULT_ROWS, door_closed, parse_map, rows_of, spawn, with_door
from snn_doom.teacher.render import cast_ray, column_angle, frame_to_ascii, hitscan, paint_frame
from snn_doom.teacher.state import GameState, pack_input, unpack_input


def test_state_bits_under_budget() -> None:
    assert STATE_BITS == 127
    assert STATE_BITS < 256


def test_pack_roundtrip() -> None:
    s = spawn()
    assert GameState.unpack(s.pack()) == s
    packed = s.pack()
    assert packed.bit_length() <= STATE_BITS


def test_map_parse_rows() -> None:
    bits = parse_map(DEFAULT_ROWS)
    assert rows_of(bits) == DEFAULT_ROWS
    s = spawn()
    assert s.cell_wall(0, 0)
    assert not s.cell_wall(1, 1)
    assert s.cell_wall(3, 3)


def test_input_pack() -> None:
    assert pack_input(1, 0, 1, 0) == 0b0101
    assert unpack_input(0b1100) == (0, 0, 1, 1, 0, 0)
    assert pack_input(0, 0, 0, 0, 1) == 0b10000
    assert unpack_input(0b10000) == (0, 0, 0, 0, 1, 0)
    assert pack_input(0, 0, 0, 0, 0, 1) == 0b100000
    assert unpack_input(0b100000) == (0, 0, 0, 0, 0, 1)
    with pytest.raises(ValueError):
        pack_input(2, 0, 0, 0)


def test_turn_wraps_and_cancels() -> None:
    s = spawn()
    left = apply_turn(s, 1, 0)
    assert left.ang == (s.ang - 2) % N_ANG
    both = apply_turn(s, 1, 1)
    assert both.ang == s.ang
    wrapped = s
    for _ in range(N_ANG // 2):
        wrapped = apply_turn(wrapped, 0, 1)
    assert wrapped.ang == s.ang


def test_move_blocked_by_wall() -> None:
    s = spawn(px=18, py=24, ang=32)  # facing west; one step crosses into cell 0
    blocked = apply_move(s, 1, 0)
    assert blocked.px == s.px
    assert blocked.py == s.py
    east = spawn(px=24, py=88, ang=0)
    moved = apply_move(east, 1, 0)
    assert moved.px > east.px
    assert moved.py == east.py


def test_move_uses_heading() -> None:
    s = spawn(px=64, py=88, ang=0)
    fwd = apply_move(s, 1, 0)
    assert fwd.px == s.px + COS[0] // 2
    both = apply_move(s, 1, 1)
    assert both.px == s.px


def test_enemy_closes_manhattan() -> None:
    s = spawn()
    before = abs(s.px - s.ex) + abs(s.py - s.ey)
    after_s = apply_enemy(s)
    after = abs(after_s.px - after_s.ex) + abs(after_s.py - after_s.ey)
    assert after < before
    dead = GameState(
        map_bits=s.map_bits,
        px=s.px,
        py=s.py,
        ang=s.ang,
        ex=s.ex,
        ey=s.ey,
        enemy_alive=0,
        player_hit=0,
    )
    assert apply_enemy(dead) == dead


def test_enemy_does_not_walk_through_walls() -> None:
    # Player west of a pillar, enemy east of it, same row as pillar.
    s = spawn(px=24, py=24 + 16 * 3, ang=0, ex=104, ey=24 + 16 * 3)
    # row 3 has walls at (3,3) and (4,3). Enemy stepping west hits the pillar.
    nxt = apply_enemy(s)
    assert not nxt.wall_at_world(nxt.ex, nxt.ey)


def test_collide_hurts_not_pauses() -> None:
    s = spawn(px=24, py=24, ex=24, ey=24, hp=3)
    r = tick(s, 0)
    assert r.state.hp == 2
    assert r.state.player_hit == 0
    assert r.state.enemy_alive == 0
    live = tick(r.state, pack_input(0, 0, 1, 0))
    assert live.state.px > r.state.px


def test_hp_zero_is_dead() -> None:
    s = spawn(px=24, py=24, ex=24, ey=24, hp=1)
    r0 = tick(s, 0)
    assert r0.state.hp == 0
    assert r0.state.player_hit == 1
    held = r0.state.px
    r = tick(r0.state, pack_input(0, 0, 1, 0))
    assert r.state.px == held
    assert r.state.player_hit == 1


def test_ray_hits_east_wall() -> None:
    s = spawn(px=24, py=88, ang=0)
    col = cast_ray(s, 0)
    assert col.dist > 0
    assert col.dist <= 15
    # 24 -> cell 7 wall at x>=112, step 8, so dist around 11-12
    assert 8 <= col.dist <= 14


def test_center_column_sees_pillar_when_facing_it() -> None:
    # Pillars at (3,3) and (4,3). Stand at (3.5, 5.5) looking north (ang=48, -y).
    s = spawn(px=3 * 16 + 8, py=5 * 16 + 8, ang=48)
    col = cast_ray(s, 48)
    assert col.dist > 0
    assert col.dist < 8


def test_framebuffer_shape_and_walls() -> None:
    s = spawn()
    r = tick(s, 0)
    assert r.pixels.shape == (FRAME_H, N_COLS)
    assert r.pixels.dtype == np.uint8
    assert int(r.pixels.max()) <= 3
    assert (r.pixels == COLOR_WALL).any()
    ascii_frame = frame_to_ascii(r.pixels)
    assert len(ascii_frame.splitlines()) == FRAME_H


def test_tick_deterministic() -> None:
    s = spawn()
    a = tick(s, pack_input(0, 1, 1, 0))
    b = tick(s, pack_input(0, 1, 1, 0))
    assert a.state == b.state
    assert a.columns == b.columns
    np.testing.assert_array_equal(a.pixels, b.pixels)


def test_run_episode_enemy_moves_inside_engine() -> None:
    s = spawn()
    frames = run(s, [0] * 8)
    assert frames[-1].state.ex != s.ex or frames[-1].state.ey != s.ey
    packed = [f.state.pack() for f in frames]
    assert packed == [tick(spawn() if i == 0 else frames[i - 1].state, 0).state.pack() for i, _ in enumerate(frames)]


def test_world_bounds() -> None:
    s = spawn(px=WORLD - 1, py=WORLD - 1, ang=0)
    r = tick(s, pack_input(0, 0, 1, 0))
    assert 0 <= r.state.px < WORLD
    assert 0 <= r.state.py < WORLD


def test_column_angles_cover_fov() -> None:
    angs = [column_angle(0, c) for c in range(N_COLS)]
    assert angs[0] == (0 - 8) % N_ANG
    assert len(set(angs)) == N_COLS
    assert column_angle(0, CENTER_COL) == 0


def test_hitscan_center_column_misses_when_looking_east() -> None:
    s = spawn()
    r = tick(s, 0)
    assert hitscan(r.state) == 0
    assert r.columns[CENTER_COL].sprite == 0


def test_hitscan_center_column_hits_enemy_when_facing_it() -> None:
    s = spawn(px=104, py=88, ang=48, ex=104, ey=40)
    r = tick(s, 0)
    assert column_angle(r.state.ang, CENTER_COL) == r.state.ang
    assert hitscan(r.state) == 1
    assert r.columns[CENTER_COL].sprite == 1


def test_fire_misses_when_heading_ray_is_empty() -> None:
    s = spawn()
    r = tick(s, pack_input(0, 0, 0, 0, 1))
    assert r.columns[CENTER_COL].sprite == 0
    assert r.shot == 0
    assert r.state.enemy_alive == 1
    dead, shot = apply_fire(s, 1, 0)
    assert shot == 0
    assert dead.enemy_alive == 1


def test_fire_kills_when_heading_ray_sees_enemy() -> None:
    s = spawn(px=104, py=88, ang=48, ex=104, ey=40)
    idle = tick(s, 0)
    assert idle.columns[CENTER_COL].sprite == 1
    assert idle.state.enemy_alive == 1
    r = tick(s, pack_input(0, 0, 0, 0, 1))
    assert r.columns[CENTER_COL].sprite == 1
    assert r.shot == 1
    assert r.state.enemy_alive == 0
    assert r.state.enemy2_alive == 1
    assert r.state.ammo == s.ammo - 1
    assert hitscan(r.state) == 0
    again = tick(r.state, pack_input(0, 0, 0, 0, 1))
    assert again.shot == 0
    assert again.state.enemy_alive == 0
    assert again.columns[CENTER_COL].sprite == 0


def test_sprite_paint_is_blob_not_wall_overwrite() -> None:
    from snn_doom.teacher.render import Column, is_enemy_row, is_wall_row, paint_column

    mid = FRAME_H // 2
    blob = paint_column(Column(dist=10, side=0, sprite=1))
    wall = paint_column(Column(dist=10, side=0, sprite=0))
    l1 = int(np.abs(blob.astype(int) - wall.astype(int)).sum())
    enemy_rows = [r for r in range(FRAME_H) if blob[r] == COLOR_ENEMY]
    assert enemy_rows == [r for r in range(FRAME_H) if is_enemy_row(r, 10)]
    assert l1 == len(enemy_rows)
    wall_only = [r for r in range(FRAME_H) if wall[r] == COLOR_WALL and blob[r] != COLOR_ENEMY]
    assert wall_only
    assert is_enemy_row(mid, 10)
    assert is_wall_row(wall_only[0], 10)
    assert not is_enemy_row(wall_only[0], 10)


def test_default_door_is_open() -> None:
    s = spawn()
    assert DOOR_X == 4 and DOOR_Y == 5
    assert door_closed(s) == 0
    assert not s.cell_wall(DOOR_X, DOOR_Y)


def test_closed_door_blocks_east_walk() -> None:
    s = with_door(spawn(), 1)
    assert door_closed(s) == 1
    fwd = pack_input(0, 0, 1, 0)
    last = s
    blocked = False
    for _ in range(16):
        r = tick(last, fwd)
        if r.state.px == last.px:
            blocked = True
            break
        last = r.state
    assert blocked
    assert last.px < DOOR_X * 16


def test_door_toggle_opens_then_pass() -> None:
    s = with_door(spawn(), 1)
    r = tick(s, pack_input(0, 0, 0, 0, 0, 1))
    assert door_closed(r.state) == 0
    assert r.state.px == s.px
    fwd = pack_input(0, 0, 1, 0)
    last = r.state
    for _ in range(16):
        nxt = tick(last, fwd).state
        if nxt.px == last.px:
            raise AssertionError("open door still blocked")
        last = nxt
        if last.px >> 4 >= DOOR_X:
            break
    assert last.px >> 4 >= DOOR_X


def test_door_toggle_closes_in_front_and_blocks() -> None:
    s = spawn()
    assert door_closed(s) == 0
    fwd = pack_input(0, 0, 1, 0)
    last = s
    while (last.px + 4) >> 4 < DOOR_X:
        last = tick(last, fwd).state
    assert (last.px + 4) >> 4 == DOOR_X
    closed = tick(last, pack_input(0, 0, 0, 0, 0, 1)).state
    assert door_closed(closed) == 1
    blocked = tick(closed, fwd)
    assert blocked.state.px == closed.px


def test_apply_door_is_after_paint() -> None:
    s = with_door(spawn(), 1)
    r = tick(s, pack_input(0, 0, 0, 0, 0, 1))
    # This tick still marched a closed door; occupancy flips after paint.
    assert door_closed(r.state) == 0
    assert apply_door(s, 1).map_bits != s.map_bits


def test_view_frame_is_taller() -> None:
    s = spawn()
    r = tick(s, 0)
    assert r.pixels.shape == (FRAME_H, N_COLS)
    assert FRAME_H == 18


def test_second_sprite_on_heading_is_not_spawn_east() -> None:
    s = spawn()
    r = tick(s, 0)
    assert hitscan(r.state) == 0
    look = spawn(px=40, py=88, ang=48)
    r = tick(look, 0)
    assert r.columns[CENTER_COL].sprite == 1
    assert r.state.enemy2_alive == 1


def test_fire_kills_second_sprite_only() -> None:
    s = spawn(px=40, py=88, ang=48)
    r = tick(s, pack_input(0, 0, 0, 0, 1))
    assert r.shot == 1
    assert r.state.enemy2_alive == 0
    assert r.state.enemy_alive == 1
    assert r.state.ammo == s.ammo - 1


def test_ammo_zero_does_not_kill() -> None:
    s = spawn(px=104, py=88, ang=48, ammo=0)
    r = tick(s, pack_input(0, 0, 0, 0, 1))
    assert r.shot == 0
    assert r.state.enemy_alive == 1
    assert r.state.ammo == 0


def test_ammo_one_kills_and_empties() -> None:
    s = spawn(px=104, py=88, ang=48, ammo=1)
    r = tick(s, pack_input(0, 0, 0, 0, 1))
    assert r.shot == 1
    assert r.state.enemy_alive == 0
    assert r.state.ammo == 0


def test_fire_miss_still_consumes_ammo() -> None:
    s = spawn(ammo=3)
    r = tick(s, pack_input(0, 0, 0, 0, 1))
    assert r.shot == 0
    assert r.state.enemy_alive == 1
    assert r.state.ammo == 2


def test_pickup_adds_ammo() -> None:
    from snn_doom.const import PICKUP_AMMO, PICKUP_X, PICKUP_Y

    s = spawn(px=PICKUP_X * 16 + 8, py=PICKUP_Y * 16 + 8, ammo=1)
    r = tick(s, 0)
    assert r.state.pickup_alive == 0
    assert r.state.ammo == 7


def test_enemy2_chase_spec_not_in_tick() -> None:
    s = spawn()
    nxt = apply_enemy2(s)
    assert nxt.ex2 != s.ex2 or nxt.ey2 != s.ey2
    idle = tick(s, 0)
    assert idle.state.ex2 == s.ex2
    assert idle.state.ey2 == s.ey2


def test_play_maps_parse() -> None:
    from snn_doom.teacher.maps import MAPS, spawn as sp

    for name, rows in MAPS.items():
        bits = parse_map(rows)
        assert rows_of(bits) == rows
    closed = sp(rows=MAPS["door"], door_closed=1)
    assert door_closed(closed) == 1
