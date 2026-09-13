# Copyright (c) 2026 Martial Systems LLC
"""One game tick: turn, move, enemy step, collide, raycast, paint.

This is the distillation target. The SNN must match `tick` bit-for-bit.
Python in the demo path may not call these functions.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from snn_doom.const import CENTER_COL, COS, DEATH_TICKS, DOOR_IDX, ENEMY_STEP, MOVE_DIV, N_ANG, SIN, WORLD
from snn_doom.teacher.render import Column, cast_frame, paint_frame
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


def apply_fire(state: GameState, fire: int, heading_sprite: int) -> tuple[GameState, int]:
    """Kill if fire is held and the heading column saw a living enemy. Paint already ran."""
    shot = int(bool(fire and heading_sprite and state.enemy_alive))
    if not shot:
        return state, 0
    return replace(state, enemy_alive=0), 1


def apply_door(state: GameState, door: int) -> GameState:
    """Flip the door occupancy after paint. Next pose sees the new bit."""
    if not door:
        return state
    return replace(state, map_bits=state.map_bits ^ (1 << DOOR_IDX))


def apply_collide(state: GameState) -> GameState:
    if not state.enemy_alive:
        return state
    same = (state.px >> 4) == (state.ex >> 4) and (state.py >> 4) == (state.ey >> 4)
    if not same:
        return state
    return replace(state, enemy_alive=0, player_hit=1, death_left=DEATH_TICKS)


@dataclass(frozen=True, slots=True)
class TickResult:
    state: GameState
    columns: tuple[Column, ...]
    pixels: np.ndarray
    shot: int = 0


def tick(state: GameState, input_bits: int) -> TickResult:
    turn_l, turn_r, fwd, back, fire, door = unpack_input(input_bits)
    if state.player_hit:
        columns = cast_frame(state)
        pixels = paint_frame(columns)
        left = state.death_left - 1
        s = replace(
            state,
            death_left=max(left, 0),
            player_hit=1 if left > 0 else 0,
            enemy_alive=0,
        )
        s = apply_door(s, door)
        return TickResult(state=s, columns=columns, pixels=pixels, shot=0)
    s = apply_turn(state, turn_l, turn_r)
    s = apply_move(s, fwd, back)
    s = apply_enemy(s)
    s = apply_collide(s)
    columns = cast_frame(s)
    pixels = paint_frame(columns)
    if s.player_hit:
        s = apply_door(s, door)
        return TickResult(state=s, columns=columns, pixels=pixels, shot=0)
    s, shot = apply_fire(s, fire, columns[CENTER_COL].sprite)
    s = apply_door(s, door)
    return TickResult(state=s, columns=columns, pixels=pixels, shot=shot)


def run(state: GameState, inputs: list[int] | tuple[int, ...]) -> list[TickResult]:
    out: list[TickResult] = []
    s = state
    for bits in inputs:
        r = tick(s, bits)
        out.append(r)
        s = r.state
    return out
