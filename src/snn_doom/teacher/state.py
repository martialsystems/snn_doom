# Copyright (c) 2026 Martial Systems LLC
"""Packed game state. Teacher and SNN share this layout."""
from __future__ import annotations

from dataclasses import dataclass

from snn_doom.const import (
    DEFAULT_AMMO,
    DEFAULT_ANG,
    DEFAULT_EX,
    DEFAULT_EX2,
    DEFAULT_EY,
    DEFAULT_EY2,
    DEFAULT_PX,
    DEFAULT_PY,
    MAP_CELLS,
    N_ANG,
    STATE_BITS,
    STATE_LAYOUT,
    WORLD,
)


def _get(packed: int, name: str) -> int:
    off, width = STATE_LAYOUT[name]
    return (packed >> off) & ((1 << width) - 1)


def _set(packed: int, name: str, value: int) -> int:
    off, width = STATE_LAYOUT[name]
    mask = (1 << width) - 1
    if value < 0 or value > mask:
        raise ValueError(f"{name}={value} does not fit in {width} bits")
    packed &= ~(mask << off)
    packed |= (value & mask) << off
    return packed


@dataclass(frozen=True, slots=True)
class GameState:
    map_bits: int
    px: int
    py: int
    ang: int
    ex: int
    ey: int
    enemy_alive: int
    player_hit: int
    ex2: int = DEFAULT_EX2
    ey2: int = DEFAULT_EY2
    enemy2_alive: int = 1
    ammo: int = DEFAULT_AMMO
    death_left: int = 0  # sequencer-internal; not packed

    def __post_init__(self) -> None:
        if self.map_bits < 0 or self.map_bits >= (1 << MAP_CELLS):
            raise ValueError("map_bits overflow")
        for name in ("px", "py", "ex", "ey", "ex2", "ey2"):
            v = getattr(self, name)
            if v < 0 or v >= WORLD:
                raise ValueError(f"{name}={v} out of world")
        if self.ang < 0 or self.ang >= N_ANG:
            raise ValueError(f"ang={self.ang} out of range")
        if self.enemy_alive not in (0, 1) or self.player_hit not in (0, 1):
            raise ValueError("flag bits must be 0 or 1")
        if self.enemy2_alive not in (0, 1):
            raise ValueError("flag bits must be 0 or 1")
        if self.ammo < 0 or self.ammo > 7:
            raise ValueError("ammo must fit in 3 bits")
        if self.death_left < 0:
            raise ValueError("death_left must be >= 0")

    def pack(self) -> int:
        packed = 0
        packed = _set(packed, "map_bits", self.map_bits)
        packed = _set(packed, "px", self.px)
        packed = _set(packed, "py", self.py)
        packed = _set(packed, "ang", self.ang)
        packed = _set(packed, "ex", self.ex)
        packed = _set(packed, "ey", self.ey)
        packed = _set(packed, "enemy_alive", self.enemy_alive)
        packed = _set(packed, "player_hit", self.player_hit)
        packed = _set(packed, "ex2", self.ex2)
        packed = _set(packed, "ey2", self.ey2)
        packed = _set(packed, "enemy2_alive", self.enemy2_alive)
        packed = _set(packed, "ammo", self.ammo)
        return packed

    @classmethod
    def unpack(cls, packed: int) -> GameState:
        if packed < 0 or packed >= (1 << STATE_BITS):
            raise ValueError("packed state overflow")
        return cls(
            map_bits=_get(packed, "map_bits"),
            px=_get(packed, "px"),
            py=_get(packed, "py"),
            ang=_get(packed, "ang"),
            ex=_get(packed, "ex"),
            ey=_get(packed, "ey"),
            enemy_alive=_get(packed, "enemy_alive"),
            player_hit=_get(packed, "player_hit"),
            ex2=_get(packed, "ex2"),
            ey2=_get(packed, "ey2"),
            enemy2_alive=_get(packed, "enemy2_alive"),
            ammo=_get(packed, "ammo"),
        )

    def cell_wall(self, cx: int, cy: int) -> bool:
        if cx < 0 or cy < 0 or cx >= 8 or cy >= 8:
            return True
        bit = cy * 8 + cx
        return bool((self.map_bits >> bit) & 1)

    def wall_at_world(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= WORLD or y >= WORLD:
            return True
        return self.cell_wall(x >> 4, y >> 4)


def pack_input(
    turn_left: int,
    turn_right: int,
    fwd: int,
    back: int,
    fire: int = 0,
    door: int = 0,
) -> int:
    for v in (turn_left, turn_right, fwd, back, fire, door):
        if v not in (0, 1):
            raise ValueError("input bits must be 0 or 1")
    return (
        turn_left
        | (turn_right << 1)
        | (fwd << 2)
        | (back << 3)
        | (fire << 4)
        | (door << 5)
    )


def unpack_input(bits: int) -> tuple[int, int, int, int, int, int]:
    if bits < 0 or bits > 63:
        raise ValueError("input bits overflow")
    return (
        bits & 1,
        (bits >> 1) & 1,
        (bits >> 2) & 1,
        (bits >> 3) & 1,
        (bits >> 4) & 1,
        (bits >> 5) & 1,
    )
