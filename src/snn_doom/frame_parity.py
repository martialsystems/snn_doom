# Copyright (c) 2026 Martial Systems LLC
"""Teacher vs net frames on the five locked poses. L1 is a metric, not a law."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from snn_doom.ray_parity import CASES, LOGS
from snn_doom.teacher.engine import tick
from snn_doom.teacher.state import GameState


def teacher_frame(state: GameState, bits: int) -> np.ndarray:
    return tick(state, bits).pixels


def net_frame(machine, state: GameState, bits: int) -> np.ndarray:
    machine.reset(state)
    return machine.tick(bits)


def run_frame_parity(machine=None) -> dict[str, Any]:
    from snn_doom.modules.pipeline import build_doom_snn

    m = machine or build_doom_snn()
    cases = []
    all_match = True
    for name, state, bits in CASES:
        want = teacher_frame(state, bits)
        got = net_frame(m, state, bits)
        l1 = int(np.abs(got.astype(int) - want.astype(int)).sum())
        match = bool(np.array_equal(got, want))
        all_match = all_match and match
        cases.append({"name": name, "match": match, "l1": l1})
    payload = {"all_match": all_match, "cases": cases}
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "frame_parity.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
