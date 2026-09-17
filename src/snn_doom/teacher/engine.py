# Copyright (c) 2026 Martial Systems LLC
"""One game tick: turn, move, enemy step, collide, raycast, paint.

This is the distillation target. The SNN must match `tick` bit-for-bit.
Python in the demo path may not call these functions.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from snn_doom.const import (
    COS,
    DOOR_IDX,
    ENEMY_STEP,
    MOVE_DIV,
    N_ANG,
    PICKUP_AMMO,
    PICKUP_X,
    PICKUP_Y,
    SIN,
    VIEW_16,
    VIEW_32,
    ViewSpec,
    WORLD,
)
from snn_doom.teacher.render import Column, cast_frame, column_angle, paint_frame
from snn_doom.teacher.state import GameState, unpack_input


def _clip(v: int) -> int:
    if v < 0:
        return 0
    if v >= WORLD:
        return WORLD - 1
    return v


def apply_turn(state: GameState, turn_left: int, turn_right: int) -> GameState:
    if turn_left == turn_right:
        return state
    delta = -2 if turn_left else 2
    return replace(state, ang=(state.ang + delta) % N_ANG)


def apply_move(state: GameState, fwd: int, back: int) -> GameState:
    if fwd == back:
        return state
    sign = 1 if fwd else -1
    nx = _clip(state.px + sign * (COS[state.ang] // MOVE_DIV))
    ny = _clip(state.py + sign * (SIN[state.ang] // MOVE_DIV))
    if state.wall_at_world(nx, ny):
        return state
    return replace(state, px=nx, py=ny)


def _try_enemy_axis(state: GameState, nx: int, ny: int) -> GameState | None:
    nx = _clip(nx)
    ny = _clip(ny)
    if state.wall_at_world(nx, ny):
        return None
    return replace(state, ex=nx, ey=ny)


def apply_enemy(state: GameState) -> GameState:
    """One enemy step inside the engine, not a host-side controller."""
    if not state.enemy_alive:
        return state
    dx = 0
    if state.px > state.ex:
        dx = ENEMY_STEP
    elif state.px < state.ex:
        dx = -ENEMY_STEP
    dy = 0
    if state.py > state.ey:
        dy = ENEMY_STEP
    elif state.py < state.ey:
        dy = -ENEMY_STEP
    # X-then-Y chase: matches the SNN ALU (one compare, no abs-of-delta).
    moved = None
    if dx != 0:
        moved = _try_enemy_axis(state, state.ex + dx, state.ey)
    if moved is None and dy != 0:
        moved = _try_enemy_axis(state, state.ex, state.ey + dy)
    return moved if moved is not None else state


def apply_enemy2(state: GameState) -> GameState:
    """Second walker. Same X-then-Y chase on (ex2,ey2)."""
    if not state.enemy2_alive:
        return state

    def _try(nx: int, ny: int) -> GameState | None:
        nx = _clip(nx)
        ny = _clip(ny)
        if state.wall_at_world(nx, ny):
            return None
        return replace(state, ex2=nx, ey2=ny)

    dx = 0
    if state.px > state.ex2:
        dx = ENEMY_STEP
    elif state.px < state.ex2:
        dx = -ENEMY_STEP
    dy = 0
    if state.py > state.ey2:
        dy = ENEMY_STEP
    elif state.py < state.ey2:
        dy = -ENEMY_STEP
    moved = None
    if dx != 0:
        moved = _try(state.ex2 + dx, state.ey2)
    if moved is None and dy != 0:
        moved = _try(state.ex2, state.ey2 + dy)
    return moved if moved is not None else state


def apply_pickup(state: GameState) -> GameState:
    if not state.pickup_alive:
        return state
    if (state.px >> 4, state.py >> 4) != (PICKUP_X, PICKUP_Y):
        return state
    return replace(
        state,
        ammo=PICKUP_AMMO,
        pickup_alive=0,
    )


def _heading_enemy_hits(state: GameState, view: ViewSpec = VIEW_16) -> tuple[int, int]:
    """Which living enemies the heading ray visits before a wall."""
    from snn_doom.const import COS, MAX_DIST, SIN, WORLD

    x = state.px
    y = state.py
    ang = column_angle(state.ang, view.center_col, view=view)
    dx = COS[ang]
    dy = SIN[ang]
    hit1 = 0
    hit2 = 0
    for _ in range(1, MAX_DIST + 1):
        x += dx
        y += dy
        if x < 0 or y < 0 or x >= WORLD or y >= WORLD:
            break
        cx, cy = x >> 4, y >> 4
        if state.enemy_alive and (cx, cy) == (state.ex >> 4, state.ey >> 4):
            hit1 = 1
        if state.enemy2_alive and (cx, cy) == (state.ex2 >> 4, state.ey2 >> 4):
            hit2 = 1
        if state.cell_wall(cx, cy):
            break
    return hit1, hit2


def apply_fire(
    state: GameState, fire: int, heading_sprite: int, view: ViewSpec = VIEW_16
) -> tuple[GameState, int]:
    """Consume one ammo if present. Kill heading-ray enemies only when ammo was > 0."""
    if not fire or state.ammo <= 0:
        return state, 0
    hit1, hit2 = _heading_enemy_hits(state, view)
    shot = int(bool(heading_sprite and (hit1 or hit2)))
    s = replace(
        state,
        ammo=state.ammo - 1,
        enemy_alive=0 if hit1 else state.enemy_alive,
        enemy2_alive=0 if hit2 else state.enemy2_alive,
    )
    return s, shot


def apply_door(state: GameState, door: int) -> GameState:
    """Flip the door occupancy after paint. Next pose sees the new bit."""
    if not door:
        return state
    return replace(state, map_bits=state.map_bits ^ (1 << DOOR_IDX))


def apply_collide(state: GameState) -> GameState:
    same1 = (
        state.enemy_alive
        and (state.px >> 4) == (state.ex >> 4)
        and (state.py >> 4) == (state.ey >> 4)
    )
    same2 = (
        state.enemy2_alive
        and (state.px >> 4) == (state.ex2 >> 4)
        and (state.py >> 4) == (state.ey2 >> 4)
    )
    if not same1 and not same2:
        return state
    hp = max(state.hp - 1, 0)
    return replace(
        state,
        enemy_alive=0 if same1 else state.enemy_alive,
        enemy2_alive=0 if same2 else state.enemy2_alive,
        hp=hp,
        player_hit=1 if hp == 0 else 0,
    )


@dataclass(frozen=True, slots=True)
class TickResult:
    state: GameState
    columns: tuple[Column, ...]
    pixels: np.ndarray
    shot: int = 0


def tick(state: GameState, input_bits: int) -> TickResult:
    """v1 teacher. e2 is a statue. Walking e2 is tick_v2."""
    return _engine_tick(state, input_bits, walk_e2=False)


def run(state: GameState, inputs: list[int] | tuple[int, ...]) -> list[TickResult]:
    out: list[TickResult] = []
    s = state
    for bits in inputs:
        r = tick(s, bits)
        out.append(r)
        s = r.state
    return out


def _engine_tick(
    state: GameState, input_bits: int, *, walk_e2: bool, view: ViewSpec = VIEW_16
) -> TickResult:
    turn_l, turn_r, fwd, back, fire, door = unpack_input(input_bits)
    if state.player_hit:
        columns = cast_frame(state, view=view)
        pixels = paint_frame(columns, view=view)
        s = apply_door(state, door)
        return TickResult(state=s, columns=columns, pixels=pixels, shot=0)
    s = apply_turn(state, turn_l, turn_r)
    s = apply_move(s, fwd, back)
    s = apply_pickup(s)
    s = apply_enemy(s)
    if walk_e2:
        s = apply_enemy2(s)
    s = apply_collide(s)
    columns = cast_frame(s, view=view)
    pixels = paint_frame(columns, view=view)
    if s.player_hit:
        s = apply_door(s, door)
        return TickResult(state=s, columns=columns, pixels=pixels, shot=0)
    s, shot = apply_fire(s, fire, columns[view.center_col].sprite, view=view)
    s = apply_door(s, door)
    return TickResult(state=s, columns=columns, pixels=pixels, shot=shot)


def tick_v2(state: GameState, input_bits: int) -> TickResult:
    """v2 teacher. Second chaser enters after apply_enemy. Same ENEMY_STEP. 16 columns."""
    return _engine_tick(state, input_bits, walk_e2=True, view=VIEW_16)


def tick_v2_32(state: GameState, input_bits: int) -> TickResult:
    """32-col VIEW teacher. Walking e2. Heading gun is CENTER_COL_32."""
    return _engine_tick(state, input_bits, walk_e2=True, view=VIEW_32)
