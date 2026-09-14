# Copyright (c) 2026 Martial Systems LLC
"""HOST_WAVES: respawn e1 from RAM bits. 0 neurons. Not a stitch ALU."""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Any

from snn_doom.const import (
    CELL,
    COS,
    DOOR_X,
    DOOR_Y,
    FOV_HALF,
    MAP_H,
    MAP_W,
    MAX_DIST,
    N_ANG,
    SIN,
)
from snn_doom.demo.dead import write_latches
from snn_doom.teacher.state import GameState


def latches_to_state(st: dict[str, Any], map_bits: int) -> GameState:
    return GameState(
        map_bits=int(map_bits),
        px=int(st["px"]),
        py=int(st["py"]),
        ang=int(st["ang"]),
        ex=int(st["ex"]),
        ey=int(st["ey"]),
        enemy_alive=int(st["enemy_alive"]),
        player_hit=int(st.get("player_hit") or 0),
        ex2=int(st["ex2"]),
        ey2=int(st["ey2"]),
        enemy2_alive=int(st["enemy2_alive"]),
        ammo=int(st["ammo"]),
        hp=int(st.get("hp") or 0),
        pickup_alive=int(st.get("pickup_alive") or 0),
    )


def _open_cell(map_bits: int, cx: int, cy: int) -> bool:
    if cx < 0 or cy < 0 or cx >= MAP_W or cy >= MAP_H:
        return False
    return not ((int(map_bits) >> (cy * MAP_W + cx)) & 1)


def heading_and_fov_cells(px: int, py: int, ang: int, map_bits: int) -> tuple[tuple[int, int] | None, set[tuple[int, int]]]:
    """Cells the 16 FOV rays enter. Host COS/SIN march. Not teacher.cast_ray."""
    pc = (int(px) >> 4, int(py) >> 4)
    heading: tuple[int, int] | None = None
    fov: set[tuple[int, int]] = set()
    for da in range(-FOV_HALF, FOV_HALF):
        a = (int(ang) + da) % N_ANG
        x, y = int(px), int(py)
        for _ in range(MAX_DIST):
            x += int(COS[a])
            y += int(SIN[a])
            cx, cy = x >> 4, y >> 4
            if cx < 0 or cy < 0 or cx >= MAP_W or cy >= MAP_H:
                break
            if (cx, cy) == pc:
                continue
            fov.add((cx, cy))
            if da == 0 and heading is None:
                heading = (cx, cy)
            if not _open_cell(map_bits, cx, cy):
                break
    return heading, fov


def free_cells(
    map_bits: int,
    *,
    px: int,
    py: int,
    ex2: int,
    ey2: int,
    door: int,
    ang: int | None = None,
) -> list[tuple[int, int]]:
    pc = (int(px) >> 4, int(py) >> 4)
    e2 = (int(ex2) >> 4, int(ey2) >> 4)
    base: list[tuple[int, int]] = []
    for cy in range(MAP_H):
        for cx in range(MAP_W):
            if not _open_cell(map_bits, cx, cy):
                continue
            if (cx, cy) == pc or (cx, cy) == e2:
                continue
            if (cx, cy) == (DOOR_X, DOOR_Y) and int(door) == 1:
                continue
            base.append((cx, cy))
    if ang is None or not base:
        return base
    heading, fov = heading_and_fov_cells(px, py, int(ang), map_bits)
    blocked = set(fov)
    if heading is not None:
        blocked.add(heading)
    off = [c for c in base if c not in blocked]
    if off:
        return off
    return base


def pick_spawn_cell(
    map_bits: int,
    *,
    px: int,
    py: int,
    ex2: int,
    ey2: int,
    door: int,
    ang: int,
    rng: random.Random,
) -> tuple[int, int] | None:
    base = free_cells(map_bits, px=px, py=py, ex2=ex2, ey2=ey2, door=door)
    if not base:
        return None
    heading, fov = heading_and_fov_cells(px, py, ang, map_bits)
    blocked = set(fov)
    if heading is not None:
        blocked.add(heading)
    off = [c for c in base if c not in blocked]
    if off:
        return rng.choice(off)
    return farthest_cell(base, px, py)


def farthest_cell(cells: list[tuple[int, int]], px: int, py: int) -> tuple[int, int]:
    pcx, pcy = int(px) >> 4, int(py) >> 4
    return max(cells, key=lambda c: (c[0] - pcx) * (c[0] - pcx) + (c[1] - pcy) * (c[1] - pcy))


def cell_center(cx: int, cy: int) -> tuple[int, int]:
    return cx * CELL + CELL // 2, cy * CELL + CELL // 2


class HostWaves:
    """After e1 dies, wait one tick, write a new chaser cell through reset."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        wave_e2: bool = False,
        seed: int = 0,
        quiet: int = 1,
    ) -> None:
        self.enabled = bool(enabled)
        self.wave_e2 = bool(wave_e2)
        self.seed = int(seed)
        self.quiet = max(int(quiet), 1)
        self.rng = random.Random(self.seed)
        self._cool_e1 = 0
        self._cool_e2 = 0
        self._e1 = 1
        self._e2 = 1
        self.log: list[dict[str, Any]] = []

    def follow(
        self,
        machine,
        last: dict[str, Any],
        *,
        tick: int,
        score: int,
    ) -> dict[str, Any]:
        if not self.enabled:
            st = last["state"]
            self._e1 = int(st.get("enemy_alive") or 0)
            self._e2 = int(st.get("enemy2_alive") or 0)
            return last
        st = last["state"]
        e1 = int(st.get("enemy_alive") or 0)
        e2 = int(st.get("enemy2_alive") or 0)
        fell1 = self._e1 and not e1
        fell2 = self._e2 and not e2
        self._e1 = e1
        self._e2 = e2
        if fell1:
            self._cool_e1 = self.quiet
        elif self._cool_e1:
            self._cool_e1 -= 1
            if self._cool_e1 == 0 and not e1:
                last = self._respawn(machine, last, tick=tick, score=score, who="e1")
                self._e1 = int(last["state"]["enemy_alive"])
        if self.wave_e2 and fell2:
            self._cool_e2 = self.quiet
        elif self.wave_e2 and self._cool_e2:
            self._cool_e2 -= 1
            if self._cool_e2 == 0 and not int(last["state"].get("enemy2_alive") or 0):
                last = self._respawn(machine, last, tick=tick, score=score, who="e2")
                self._e2 = int(last["state"]["enemy2_alive"])
        return last

    def _respawn(
        self,
        machine,
        last: dict[str, Any],
        *,
        tick: int,
        score: int,
        who: str,
    ) -> dict[str, Any]:
        st = last["state"]
        map_bits = int(last["map_bits"])
        door = int(last.get("door") or 0)
        picked = pick_spawn_cell(
            map_bits,
            px=int(st["px"]),
            py=int(st["py"]),
            ex2=int(st["ex2"]),
            ey2=int(st["ey2"]),
            door=door,
            ang=int(st["ang"]),
            rng=self.rng,
        )
        if picked is None:
            return last
        cx, cy = picked
        keep_ang = int(st["ang"])
        wx, wy = cell_center(cx, cy)
        s = latches_to_state(st, map_bits)
        if who == "e1":
            s = replace(s, ex=wx, ey=wy, enemy_alive=1)
        else:
            s = replace(s, ex2=wx, ey2=wy, enemy2_alive=1)
        assert s.ang == keep_ang
        st2 = write_latches(machine, s)
        last = dict(last)
        last["state"] = st2
        last["pixels"] = machine.decode_pixels()
        last["map_bits"] = machine.read_map_bits()
        last["door"] = machine.read_door()
        self.log.append(
            {
                "seed": self.seed,
                "cell": [cx, cy],
                "tick": int(tick),
                "score": int(score),
                "who": who,
            }
        )
        return last
