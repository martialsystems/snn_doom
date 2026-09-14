# Copyright (c) 2026 Martial Systems LLC
"""HOST_RADAR: top-down blit of latched REGISTER_FILE + RAM bits. 0 neurons."""
from __future__ import annotations

from typing import Any

import numpy as np

from snn_doom.const import (
    CELL,
    COS,
    DOOR_IDX,
    DOOR_X,
    DOOR_Y,
    FOV_HALF,
    MAP_CELLS,
    MAP_W,
    N_ANG,
    SIN,
    WORLD,
)

RADAR_SCALE: int = 2  # pixels per world unit; 256x256
RADAR_CELL: int = CELL * RADAR_SCALE  # 32
RADAR_SIZE: int = WORLD * RADAR_SCALE

COLOR_WALL = (36, 36, 36)
COLOR_FLOOR = (16, 16, 16)
COLOR_DOOR_CLOSED = (170, 110, 40)
COLOR_DOOR_OPEN = (40, 80, 90)
COLOR_PLAYER = (80, 220, 80)
COLOR_E1 = (220, 60, 60)
COLOR_E1_GHOST = (80, 30, 30)
COLOR_E2 = (230, 160, 40)
COLOR_E2_GHOST = (90, 60, 20)
COLOR_FOV = (70, 70, 30)
COLOR_CENTER_RAY = (255, 220, 60)
COLOR_LABEL = (240, 240, 240)

FACE_CHARS = ">v<^"

_FONT5 = {
    "P": ("11110", "10001", "11110", "10000", "10000"),
    "1": ("01100", "00100", "00100", "00100", "01110"),
    "2": ("11110", "00001", "01110", "10000", "11111"),
    "D": ("11100", "10010", "10001", "10010", "11100"),
}


def facing_char(ang: int) -> str:
    return FACE_CHARS[(int(ang) // 16) % 4]


def _put(img: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    h, w = img.shape[:2]
    if 0 <= y < h and 0 <= x < w:
        img[y, x] = color


def _fill_cell(img: np.ndarray, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    x0 = int(cx) * RADAR_CELL
    y0 = int(cy) * RADAR_CELL
    img[y0 : y0 + RADAR_CELL, x0 : x0 + RADAR_CELL] = color


def _stamp(img: np.ndarray, wx: int, wy: int, color: tuple[int, int, int], r: int) -> None:
    x = int(wx) * RADAR_SCALE
    y = int(wy) * RADAR_SCALE
    img[max(0, y - r) : y + r + 1, max(0, x - r) : x + r + 1] = color


def _line(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _put(img, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _glyph(img: np.ndarray, wx: int, wy: int, ch: str, color: tuple[int, int, int]) -> None:
    rows = _FONT5.get(ch)
    if rows is None:
        return
    x0 = int(wx) * RADAR_SCALE + 4
    y0 = int(wy) * RADAR_SCALE - 10
    for r, line in enumerate(rows):
        for c, bit in enumerate(line):
            if bit == "1":
                _put(img, x0 + c, y0 + r, color)


def radar_rgb(
    map_bits: int,
    st: dict[str, Any],
    *,
    door: int | None = None,
    ghost: dict[str, Any] | None = None,
) -> np.ndarray:
    """256x256 integer blit. Does not write FRAME_READOUT."""
    img = np.zeros((RADAR_SIZE, RADAR_SIZE, 3), dtype=np.uint8)
    img[:, :] = COLOR_FLOOR
    for i in range(MAP_CELLS):
        if (int(map_bits) >> i) & 1:
            _fill_cell(img, i % MAP_W, i // MAP_W, COLOR_WALL)
    closed = int(st.get("door", door if door is not None else (int(map_bits) >> DOOR_IDX) & 1))
    _fill_cell(img, DOOR_X, DOOR_Y, COLOR_DOOR_CLOSED if closed else COLOR_DOOR_OPEN)
    px = int(st["px"])
    py = int(st["py"])
    ang = int(st["ang"]) % N_ANG
    x0 = px * RADAR_SCALE
    y0 = py * RADAR_SCALE
    for da in range(-FOV_HALF, FOV_HALF):
        a = (ang + da) % N_ANG
        x1 = x0 + int(COS[a]) * 8
        y1 = y0 + int(SIN[a]) * 8
        color = COLOR_CENTER_RAY if da == 0 else COLOR_FOV
        _line(img, x0, y0, x1, y1, color)
    ex = int(st["ex"])
    ey = int(st["ey"])
    ex2 = int(st["ex2"])
    ey2 = int(st["ey2"])
    if int(st.get("enemy_alive") or 0):
        _stamp(img, ex, ey, COLOR_E1, r=3)
        _glyph(img, ex, ey, "1", COLOR_LABEL)
    else:
        _stamp(img, ex, ey, COLOR_E1_GHOST, r=2)
    if int(st.get("enemy2_alive") or 0):
        _stamp(img, ex2, ey2, COLOR_E2, r=3)
        _glyph(img, ex2, ey2, "2", COLOR_LABEL)
    else:
        _stamp(img, ex2, ey2, COLOR_E2_GHOST, r=2)
    _stamp(img, px, py, COLOR_PLAYER, r=3)
    _glyph(img, px, py, "P", COLOR_LABEL)
    _glyph(img, DOOR_X * CELL + CELL // 2, DOOR_Y * CELL + CELL // 2, "D", COLOR_LABEL)
    if ghost:
        _stamp(img, int(ghost.get("px", 0)), int(ghost.get("py", 0)), (180, 180, 255), r=2)
    return img


def radar_marks_player_cell(img: np.ndarray, px: int, py: int) -> bool:
    cx, cy = int(px) // CELL, int(py) // CELL
    x = cx * RADAR_CELL + RADAR_CELL // 2
    y = cy * RADAR_CELL + RADAR_CELL // 2
    return tuple(int(v) for v in img[y, x]) == COLOR_PLAYER
