# Copyright (c) 2026 Martial Systems LLC
"""Multi-tick teacher vs net tape. One-frame fixtures can hide sequencer drift."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from snn_doom.const import CENTER_COL, N_COLS
from snn_doom.ray_parity import CASES, LOGS
from snn_doom.snn.io import read_bit, read_int
from snn_doom.teacher.engine import tick
from snn_doom.teacher.render import hitscan
from snn_doom.teacher.state import GameState, pack_input

TAPE_N = 4
HELD_N = 32
HELD_BITS = pack_input(0, 0, 1, 0)
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


def _snn_hitscan(machine) -> int:
    return read_bit(machine.net.spikes, machine.sprite_cols[CENTER_COL])


def _step(i: int, bits: int, teacher: GameState, machine, pix, tr) -> dict[str, Any]:
    st = machine.read_state()
    dists = _snn_dists(machine)
    want_pose = _pose_dict(teacher)
    want_d = [c.dist for c in tr.columns]
    want_hs = hitscan(teacher)
    got_hs = _snn_hitscan(machine)
    pose_ok = st == want_pose
    dist_ok = dists == want_d
    frame_ok = bool(np.array_equal(pix, tr.pixels))
    hitscan_ok = got_hs == want_hs
    ok = pose_ok and dist_ok and frame_ok and hitscan_ok
    return {
        "i": i,
        "bits": bits,
        "pose_ok": pose_ok,
        "dist_ok": dist_ok,
        "frame_ok": frame_ok,
        "hitscan_ok": hitscan_ok,
        "match": ok,
        "teacher_pose": want_pose,
        "snn_pose": st,
        "teacher_dist": want_d,
        "snn_dist": dists,
        "teacher_hitscan": want_hs,
        "snn_hitscan": got_hs,
        "l1": int(np.abs(pix.astype(int) - tr.pixels.astype(int)).sum()),
    }


def _run_bits(machine, start: GameState, bits_seq: list[int]) -> list[dict[str, Any]]:
    teacher = start
    machine.reset(start)
    steps = []
    for i, bits in enumerate(bits_seq):
        tr = tick(teacher, bits)
        teacher = tr.state
        pix = machine.tick(bits)
        steps.append(_step(i, bits, teacher, machine, pix, tr))
    return steps


def run_tick_tape(machine=None, extra_ticks: int = TAPE_N, held_ticks: int = HELD_N) -> dict[str, Any]:
    from snn_doom.modules.pipeline import build_doom_snn
    from snn_doom.teacher.maps import spawn

    m = machine or build_doom_snn()
    tapes = []
    all_match = True
    cycle = list(TAPE_BITS)
    for name, start, first_bits in CASES:
        bits_seq = [first_bits] + [cycle[i % len(cycle)] for i in range(extra_ticks)]
        steps = _run_bits(m, start, bits_seq)
        ok = all(s["match"] for s in steps)
        all_match = all_match and ok
        tapes.append({"name": name, "match": ok, "steps": steps})
    held_steps = _run_bits(m, spawn(), [HELD_BITS] * held_ticks)
    held_ok = all(s["match"] for s in held_steps)
    all_match = all_match and held_ok
    payload = {
        "all_match": all_match,
        "extra_ticks": extra_ticks,
        "held_ticks": held_ticks,
        "held_key": "fwd",
        "tapes": tapes,
        "held": {"name": "held_fwd", "match": held_ok, "steps": held_steps},
    }
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "tick_tape.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload

