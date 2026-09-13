#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""SETTLE 24 is allowed only if held-fwd pose+16 dist+hitscan match. 29 stays otherwise."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import snn_doom.const as const

SETTLE_CANDIDATE = 24
HELD_N = 32


def _reload() -> None:
    import snn_doom.modules.pipeline as pipeline
    import snn_doom.tick_tape as tick_tape

    importlib.reload(const)
    importlib.reload(pipeline)
    importlib.reload(tick_tape)


def main() -> None:
    from snn_doom.const import (
        DOOR_WINDOWS,
        MARCH_LEN,
        N_COLS,
        POSE_WINDOWS,
        SETTLE_STEPS,
    )
    from snn_doom.modules.pipeline import build_doom_snn
    from snn_doom.teacher.engine import tick
    from snn_doom.teacher.maps import spawn
    from snn_doom.teacher.state import pack_input
    from snn_doom.tick_tape import _snn_dists, _snn_hitscan

    baseline = SETTLE_STEPS
    const.SETTLE_STEPS = SETTLE_CANDIDATE
    const.STEPS_PER_TICK = SETTLE_CANDIDATE * (POSE_WINDOWS + N_COLS * MARCH_LEN + DOOR_WINDOWS)
    import snn_doom.modules.pipeline as pipeline
    importlib.reload(pipeline)
    m = pipeline.build_doom_snn()
    teacher = spawn()
    m.reset(teacher)
    bits = pack_input(0, 0, 1, 0)
    steps = []
    ok = True
    for i in range(HELD_N):
        tr = tick(teacher, bits)
        teacher = tr.state
        pix = m.tick(bits)
        st = m.read_state()
        want = {
            "px": teacher.px,
            "py": teacher.py,
            "ang": teacher.ang,
            "ex": teacher.ex,
            "ey": teacher.ey,
            "enemy_alive": teacher.enemy_alive,
        }
        got = {k: st[k] for k in want}
        dists = _snn_dists(m)
        want_d = [c.dist for c in tr.columns]
        hs = _snn_hitscan(m)
        want_hs = tr.columns[8].sprite
        pose_ok = got == want
        dist_ok = dists == want_d
        hs_ok = hs == want_hs
        match = pose_ok and dist_ok and hs_ok
        ok = ok and match
        steps.append(
            {
                "i": i,
                "pose_ok": pose_ok,
                "dist_ok": dist_ok,
                "hitscan_ok": hs_ok,
                "match": match,
                "teacher": want,
                "snn": got,
            }
        )
        if not match:
            break
    payload = {
        "candidate": SETTLE_CANDIDATE,
        "baseline": baseline,
        "held_ticks": HELD_N,
        "match": ok,
        "adopted": False,
        "n_neurons": m.net.n,
        "steps": steps,
        "note": "29 stays unless this tape is green",
    }
    out = ROOT / "logs" / "settle_probe.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("candidate", "baseline", "match", "adopted", "n_neurons")}, indent=2))
    const.SETTLE_STEPS = baseline
    const.STEPS_PER_TICK = baseline * (POSE_WINDOWS + N_COLS * MARCH_LEN + DOOR_WINDOWS)
    if not ok:
        print("SETTLE 24 failed held-fwd; keeping", baseline)


if __name__ == "__main__":
    main()
