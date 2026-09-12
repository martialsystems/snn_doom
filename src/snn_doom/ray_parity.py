# Copyright (c) 2026 Martial Systems LLC
"""Teacher vs net: 16 column distances on idle, forward, turn, wall-graze."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from snn_doom.const import N_COLS
from snn_doom.snn.io import read_int
from snn_doom.teacher.engine import tick
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.render import Column, cast_frame
from snn_doom.teacher.state import GameState, pack_input

REPO = Path(__file__).resolve().parents[2]
LOGS = REPO / "logs"

CASES = (
    ("idle", spawn(), 0),
    ("forward", spawn(), pack_input(0, 0, 1, 0)),
    ("turn", spawn(), pack_input(0, 1, 0, 0)),
    (
        "wall_graze",
        spawn(px=3 * 16 + 4, py=4 * 16 + 8, ang=48),
        0,
    ),
)


def teacher_dists(state: GameState, bits: int) -> list[int]:
    nxt = tick(state, bits).state
    cols: tuple[Column, ...] = cast_frame(nxt)
    return [c.dist for c in cols]


def net_dists(machine, state: GameState, bits: int) -> list[int]:
    machine.reset(state)
    machine.tick(bits)
    spikes = machine.net.spikes
    return [read_int(spikes, machine.dist_cols[c]) for c in range(N_COLS)]


def run_parity(machine=None) -> dict[str, Any]:
    from snn_doom.modules.pipeline import build_doom_snn

    m = machine or build_doom_snn()
    cases = []
    all_match = True
    for name, state, bits in CASES:
        want = teacher_dists(state, bits)
        got = net_dists(m, state, bits)
        match = got == want
        all_match = all_match and match
        cases.append({"name": name, "teacher": want, "snn": got, "match": match})
    payload = {"all_match": all_match, "cases": cases}
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "ray_parity.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
