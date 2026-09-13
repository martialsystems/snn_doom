# Copyright (c) 2026 Martial Systems LLC
"""8x8 wall maps. '#' wall, '.' empty. Outer ring is always wall."""
from __future__ import annotations

from dataclasses import replace

from snn_doom.const import DOOR_IDX, MAP_H, MAP_W
from snn_doom.teacher.state import GameState

DEFAULT_ROWS: tuple[str, ...] = (
    "########",
    "#......#",
    "#......#",
    "#..##..#",
    "#......#",
    "#......#",
    "#......#",
    "########",
)

HALLWAY_ROWS: tuple[str, ...] = (
    "########",
    "#......#",
    "#.####.#",
    "#......#",
    "#.####.#",
    "#......#",
    "#......#",
    "########",
)


def parse_map(rows: tuple[str, ...] | list[str]) -> int:
    if len(rows) != MAP_H:
        raise ValueError(f"need {MAP_H} rows")
    bits = 0
    for y, row in enumerate(rows):
        if len(row) != MAP_W:
            raise ValueError(f"row {y} length {len(row)}")
        for x, ch in enumerate(row):
            if ch == "#":
                bits |= 1 << (y * MAP_W + x)
            elif ch != ".":
                raise ValueError(f"bad cell {ch!r} at {x},{y}")
    return bits


def rows_of(map_bits: int) -> tuple[str, ...]:
    rows = []
    for y in range(MAP_H):
        chars = []
        for x in range(MAP_W):
            bit = (map_bits >> (y * MAP_W + x)) & 1
            chars.append("#" if bit else ".")
        rows.append("".join(chars))
    return tuple(rows)


def spawn(
    rows: tuple[str, ...] = DEFAULT_ROWS,
    px: int = 24,
    py: int = 88,
    ang: int = 0,
    ex: int = 104,
    ey: int = 40,
    enemy_alive: int = 1,
    ex2: int | None = None,
    ey2: int | None = None,
    enemy2_alive: int = 1,
    ammo: int | None = None,
) -> GameState:
    from snn_doom.const import DEFAULT_AMMO, DEFAULT_EX2, DEFAULT_EY2

    return GameState(
        map_bits=parse_map(rows),
        px=px,
        py=py,
        ang=ang,
        ex=ex,
        ey=ey,
        enemy_alive=enemy_alive,
        player_hit=0,
        ex2=DEFAULT_EX2 if ex2 is None else ex2,
        ey2=DEFAULT_EY2 if ey2 is None else ey2,
        enemy2_alive=enemy2_alive,
        ammo=DEFAULT_AMMO if ammo is None else ammo,
    )


def door_closed(state: GameState) -> int:
    return (state.map_bits >> DOOR_IDX) & 1


def with_door(state: GameState, closed: int) -> GameState:
    if closed not in (0, 1):
        raise ValueError("closed must be 0 or 1")
    bit = 1 << DOOR_IDX
    if closed:
        return replace(state, map_bits=state.map_bits | bit)
    return replace(state, map_bits=state.map_bits & ~bit)


DEFAULT_MAP_BITS: int = parse_map(DEFAULT_ROWS)
