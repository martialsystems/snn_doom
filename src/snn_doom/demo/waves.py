# Copyright (c) 2026 Martial Systems LLC
"""HOST_WAVES: respawn e1 from RAM bits. 0 neurons. Not a stitch ALU."""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Any

from snn_doom.const import CELL, DOOR_X, DOOR_Y, MAP_H, MAP_W
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


def free_cells(
    map_bits: int,
    *,
    px: int,
    py: int,
    ex2: int,
    ey2: int,
    door: int,
) -> list[tuple[int, int]]:
    pc = (int(px) >> 4, int(py) >> 4)
    e2 = (int(ex2) >> 4, int(ey2) >> 4)
    out: list[tuple[int, int]] = []
    for cy in range(MAP_H):
        for cx in range(MAP_W):
            if (map_bits >> (cy * MAP_W + cx)) & 1:
                continue
            if (cx, cy) == pc or (cx, cy) == e2:
                continue
            if (cx, cy) == (DOOR_X, DOOR_Y) and int(door) == 1:
                continue
            out.append((cx, cy))
    return out


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
        cells = free_cells(
            map_bits,
            px=st["px"],
            py=st["py"],
            ex2=st["ex2"],
            ey2=st["ey2"],
            door=door,
        )
        if who == "e2":
            cells = [c for c in cells if c != (int(st["ex"]) >> 4, int(st["ey"]) >> 4)]
        if not cells:
            return last
        cx, cy = self.rng.choice(cells)
        wx, wy = cell_center(cx, cy)
        s = latches_to_state(st, map_bits)
        if who == "e1":
            s = replace(s, ex=wx, ey=wy, enemy_alive=1)
        else:
            s = replace(s, ex2=wx, ey2=wy, enemy2_alive=1)
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
