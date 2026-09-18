#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.state import pack_input

MODULES = (
    "CLOCK",
    "BIT_LATCH",
    "REGISTER_FILE",
    "ADDER_COMPARE",
    "RAM",
    "SEQUENCER",
    "RAY_COLUMN",
    "FRAME_READOUT",
    "DOOR",
)

WALK_E2 = False
VIEW = None


def _build():
    return build_doom_snn(walk_e2=WALK_E2, view=VIEW)


def _pass(bits: int, label: str) -> dict:
    s0 = spawn()
    base = _build()
    base.reset(s0)
    pix0 = base.tick(bits)
    st0 = base.read_state()
    rows = []
    for name in MODULES:
        m = _build()
        m.reset(s0)
        m.zero_module(name)
        pix = m.tick(bits)
        st = m.read_state()
        row = {
            "module": name,
            "pixel_l1": int(abs(pix.astype(int) - pix0.astype(int)).sum()),
            "state_delta": {k: int(st[k] != st0[k]) for k in st0},
            "pixels_nonzero": int((pix != 0).sum()),
        }
        rows.append(row)
        print(label, name, row["pixel_l1"], row["state_delta"])
    return {"baseline_state": st0, "rows": rows, "spawn_px": s0.px}


def main() -> None:
    import argparse

    global WALK_E2, VIEW

    p = argparse.ArgumentParser()
    p.add_argument("--machine", choices=("v1", "v2", "v2_32"), default="v1")
    args = p.parse_args()
    WALK_E2 = args.machine in {"v2", "v2_32"}
    if args.machine == "v2_32":
        from snn_doom.const import VIEW_32

        VIEW = VIEW_32
    else:
        VIEW = None
    idle = _pass(0, "idle")
    fwd = _pass(pack_input(0, 0, 1, 0), "fwd")
    by = {r["module"]: r for r in fwd["rows"]}
    latch = by.get("BIT_LATCH") or {}
    latch_held_key_dies = bool(fwd["baseline_state"]["px"] != fwd["spawn_px"]) and bool(
        (latch.get("state_delta") or {}).get("px")
    )
    from snn_doom.const import DOOR_X
    from snn_doom.teacher.maps import with_door

    door_bits = pack_input(0, 0, 0, 0, 0, 1)
    fwd_bits = pack_input(0, 0, 1, 0)
    closed = with_door(spawn(), 1)

    def _walk_after_toggle(zero_door: bool) -> tuple[int, int]:
        m = _build()
        m.reset(closed)
        if zero_door:
            m.zero_module("DOOR")
        m.tick(door_bits)
        for _ in range(12):
            m.tick(fwd_bits)
        st = m.read_state()
        return st["px"], m.read_door()

    px_ok, d_ok = _walk_after_toggle(False)
    px_dead, d_dead = _walk_after_toggle(True)
    door_write_dies = bool(d_ok == 0 and d_dead == 1 and px_ok > px_dead)
    payload = {
        "idle": {k: v for k, v in idle.items() if k != "spawn_px"},
        "fwd": {k: v for k, v in fwd.items() if k != "spawn_px"},
        "baseline_state": fwd["baseline_state"],
        "held_key": "fwd",
        "latch_held_key_dies": latch_held_key_dies,
        "rows": fwd["rows"],
        "door_write_dies": door_write_dies,
        "door_ablate": {
            "open_px": px_ok,
            "open_door": d_ok,
            "ablate_px": px_dead,
            "ablate_door": d_dead,
            "passed_cell": int(px_ok >> 4 >= DOOR_X),
        },
    }
    payload["machine"] = "v2_32" if VIEW is not None else ("v2" if WALK_E2 else "v1")
    if VIEW is not None:
        out_name = "ablation_v2_32.json"
    elif WALK_E2:
        out_name = "ablation_v2.json"
    else:
        out_name = "ablation.json"
    out = ROOT / "logs" / out_name
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
