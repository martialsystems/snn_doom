# Copyright (c) 2026 Martial Systems LLC
"""Integer ray march and column-to-pixel decoder. Distillation target."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from snn_doom.const import (
    CENTER_COL,
    COLOR_ENEMY,
    COLOR_FLOOR,
    COLOR_SKY,
    COLOR_WALL,
    COS,
    FRAME_H,
    FOV_HALF,
    MAX_DIST,
    N_ANG,
    N_COLS,
    SIN,
    WORLD,
)
from snn_doom.teacher.state import GameState


@dataclass(frozen=True, slots=True)
class Column:
    dist: int
    side: int
    sprite: int

    def pack(self) -> int:
        return (self.dist & 15) | ((self.side & 1) << 4) | ((self.sprite & 1) << 5)


def _clamp_ang(a: int) -> int:
    return a % N_ANG


def column_angle(player_ang: int, col: int) -> int:
    return _clamp_ang(player_ang - FOV_HALF + col)


def cast_ray(state: GameState, ang: int) -> Column:
    """March from the player along `ang`. dist=0 is a miss at MAX_DIST."""
    x = state.px
    y = state.py
    dx = COS[ang]
    dy = SIN[ang]
    sprite = 0
    last_cx, last_cy = x >> 4, y >> 4
    for dist in range(1, MAX_DIST + 1):
        x += dx
        y += dy
        if x < 0 or y < 0 or x >= WORLD or y >= WORLD:
            return Column(dist=0, side=0, sprite=sprite)
        cx, cy = x >> 4, y >> 4
        if state.enemy_alive and (cx, cy) == (state.ex >> 4, state.ey >> 4):
            sprite = 1
        if state.cell_wall(cx, cy):
            side = 1 if abs(dx) >= abs(dy) else 0
            return Column(dist=dist, side=side, sprite=sprite)
        last_cx, last_cy = cx, cy
    del last_cx, last_cy
    return Column(dist=0, side=0, sprite=sprite)


def cast_frame(state: GameState) -> tuple[Column, ...]:
    return tuple(cast_ray(state, column_angle(state.ang, c)) for c in range(N_COLS))


def hitscan(state: GameState) -> int:
    """Center-column sprite: the heading ray visited the enemy cell before a wall."""
    return cast_ray(state, column_angle(state.ang, CENTER_COL)).sprite


def column_height(dist: int) -> int:
    if dist <= 0:
        return 0
    return max(1, FRAME_H - dist)


def is_wall_row(row: int, dist: int) -> bool:
    h = column_height(dist)
    return bool(h and abs(row - FRAME_H // 2) < max(1, h // 2))


def is_enemy_row(row: int, dist: int) -> bool:
    """Sprite blob. A subset of the wall slab except on thin / miss columns."""
    h = column_height(dist)
    return abs(row - FRAME_H // 2) <= max(1, (h // 2) // 2)


def paint_column(col: Column) -> np.ndarray:
    """16-row 2-bit color strip. Host may only copy this out of spikes."""
    pix = np.empty(FRAME_H, dtype=np.uint8)
    mid = FRAME_H // 2
    for row in range(FRAME_H):
        if col.sprite and is_enemy_row(row, col.dist):
            pix[row] = COLOR_ENEMY
        elif is_wall_row(row, col.dist):
            pix[row] = COLOR_WALL
        elif row < mid:
            pix[row] = COLOR_SKY
        else:
            pix[row] = COLOR_FLOOR
    return pix


def paint_frame(columns: tuple[Column, ...] | list[Column]) -> np.ndarray:
    if len(columns) != N_COLS:
        raise ValueError("need 16 columns")
    frame = np.zeros((FRAME_H, N_COLS), dtype=np.uint8)
    for c, col in enumerate(columns):
        frame[:, c] = paint_column(col)
    return frame


def frame_to_ascii(frame: np.ndarray) -> str:
    glyphs = {COLOR_SKY: " ", COLOR_FLOOR: ".", COLOR_WALL: "#", COLOR_ENEMY: "E"}
    lines = []
    for row in frame:
        lines.append("".join(glyphs[int(v)] for v in row))
    return "\n".join(lines)
