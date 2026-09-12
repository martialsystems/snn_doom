# Copyright (c) 2026 Martial Systems LLC
"""Multi-tick teacher vs net tape. One-frame fixtures can hide sequencer drift."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from snn_doom.const import N_COLS
from snn_doom.ray_parity import CASES, LOGS
from snn_doom.snn.io import read_int
from snn_doom.teacher.engine import tick
from snn_doom.teacher.state import GameState, pack_input

TAPE_N = 4
TAPE_BITS = (
    0,
    pack_input(0, 0, 1, 0),
    pack_input(0, 1, 0, 0),
    pack_input(0, 0, 0, 1),
)


def _pose_dict(state: GameState) -> dict[str, int]:
    return {
        "px": state.px,
        "py": state.py,
        "ang": state.ang,
        "ex": state.ex,
        "ey": state.ey,
        "enemy_alive": state.enemy_alive,
        "player_hit": state.player_hit,
    }


def _snn_dists(machine) -> list[int]:
    s = machine.net.spikes
    return [read_int(s, machine.dist_cols[c]) for c in range(N_COLS)]


def run_tick_tape(machine=None, extra_ticks: int = TAPE_N) -> dict[str, Any]:
    from snn_doom.modules.pipeline import build_doom_snn

    m = machine or build_doom_snn()
    tapes = []
    all_match = True
    cycle = list(TAPE_BITS)
    for name, start, first_bits in CASES:
        teacher = start
        m.reset(start)
        steps = []
        bits_seq = [first_bits] + [cycle[i % len(cycle)] for i in range(extra_ticks)]
        for i, bits in enumerate(bits_seq):
            tr = tick(teacher, bits)
            teacher = tr.state
            pix = m.tick(bits)
            st = m.read_state()
            dists = _snn_dists(m)
            want_pose = _pose_dict(teacher)
            want_d = [c.dist for c in tr.columns]
            pose_ok = st == want_pose
            dist_ok = dists == want_d
            frame_ok = bool(np.array_equal(pix, tr.pixels))
            ok = pose_ok and dist_ok and frame_ok
            all_match = all_match and ok
            steps.append(
                {
                    "i": i,
                    "bits": bits,
                    "pose_ok": pose_ok,
                    "dist_ok": dist_ok,
                    "frame_ok": frame_ok,
                    "match": ok,
                    "teacher_pose": want_pose,
                    "snn_pose": st,
                    "teacher_dist": want_d,
                    "snn_dist": dists,
                    "l1": int(np.abs(pix.astype(int) - tr.pixels.astype(int)).sum()),
                }
            )
        tapes.append({"name": name, "match": all(s["match"] for s in steps), "steps": steps})
    payload = {"all_match": all_match, "extra_ticks": extra_ticks, "tapes": tapes}
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "tick_tape.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
