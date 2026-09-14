#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Export the frozen v1 stitch for a browser LIF host. Same discrete equation."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from doomforge.gate import require_settle_floor, require_v1_cap
from snn_doom.const import (
    CELL,
    CENTER_COL,
    COS,
    DIGITAL_THRESH,
    DOOR_IDX,
    DOOR_X,
    DOOR_Y,
    FOV_HALF,
    FRAME_H,
    MAX_DIST,
    N_ANG,
    N_COLS,
    N_COLORS,
    N_INPUT_BITS,
    SIN,
    STEPS_PER_TICK,
    V1_NEURON_CAP,
)
from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.snn.io import AMP
from snn_doom.teacher.maps import MAPS, spawn


def _rail(r) -> list[int]:
    return [int(r.t), int(r.f)]


def _rails(rs) -> list[list[int]]:
    return [_rail(r) for r in rs]


def main() -> None:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "web" / "pack"
    dest.mkdir(parents=True, exist_ok=True)
    m = build_doom_snn()
    require_v1_cap(n_neurons=m.net.n, intent="export")
    require_settle_floor(intent="export")
    net = m.net
    s0 = spawn(rows=MAPS["door"], door_closed=1)
    meta = {
        "n": int(net.n),
        "nnz": int(net.indices.size),
        "steps_per_tick": int(m.steps_per_tick),
        "cap": V1_NEURON_CAP,
        "amp": float(AMP),
        "thresh_const": float(DIGITAL_THRESH),
        "n_cols": N_COLS,
        "frame_h": FRAME_H,
        "n_colors": N_COLORS,
        "n_ang": N_ANG,
        "n_inputs": N_INPUT_BITS,
        "center_col": CENTER_COL,
        "fov_half": FOV_HALF,
        "cell": CELL,
        "max_dist": MAX_DIST,
        "door_idx": DOOR_IDX,
        "door_x": DOOR_X,
        "door_y": DOOR_Y,
        "cos": list(COS),
        "sin": list(SIN),
        "bias": int(m.bias),
        "kick": [int(k) for k in m.kick],
        "shot": int(m.shot),
        "in_rails": _rails(m.in_rails),
        "px": _rails(m.px),
        "py": _rails(m.py),
        "ang": _rails(m.ang),
        "ex": _rails(m.ex),
        "ey": _rails(m.ey),
        "enemy_alive": _rail(m.enemy_alive),
        "player_hit": _rail(m.player_hit),
        "ex2": _rails(m.ex2),
        "ey2": _rails(m.ey2),
        "enemy2_alive": _rail(m.enemy2_alive),
        "ammo": _rails(m.ammo),
        "hp": _rails(m.hp),
        "pickup_alive": _rail(m.pickup_alive),
        "ram_cells": _rails(m.ram_cells),
        "sprite_cols": [_rail(r) for r in m.sprite_cols],
        "dist_cols": [_rails(col) for col in m.dist_cols],
        "pixels": m.pixels,
        "spawn": {
            "map_bits": int(s0.map_bits),
            "px": s0.px,
            "py": s0.py,
            "ang": s0.ang,
            "ex": s0.ex,
            "ey": s0.ey,
            "enemy_alive": s0.enemy_alive,
            "player_hit": s0.player_hit,
            "ex2": s0.ex2,
            "ey2": s0.ey2,
            "enemy2_alive": s0.enemy2_alive,
            "ammo": s0.ammo,
            "hp": s0.hp,
            "pickup_alive": s0.pickup_alive,
        },
    }
    (dest / "net.json").write_text(json.dumps(meta, separators=(",", ":")) + "\n", encoding="utf-8")
    blob = b"".join(
        [
            net.indptr.astype("<i4").tobytes(),
            net.indices.astype("<i4").tobytes(),
            net.csr_w.astype("<f4").tobytes(),
            net.thresh.astype("<f4").tobytes(),
        ]
    )
    (dest / "net.bin").write_bytes(blob)
    print(
        json.dumps(
            {
                "n": meta["n"],
                "nnz": meta["nnz"],
                "json_bytes": (dest / "net.json").stat().st_size,
                "bin_bytes": (dest / "net.bin").stat().st_size,
                "dir": str(dest),
            }
        )
    )


if __name__ == "__main__":
    main()
