#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Freeze FRAME_READOUT only after five-pose frames match and ablations split."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from doomforge.evidence import ablations_isolate, latch_held_key_dies
from doomforge.gate import require_can_train
from snn_doom.frame_parity import run_frame_parity
from snn_doom.modules.train import freeze_role
from snn_doom.ray_parity import run_parity

require_can_train("train_readout")
ray = run_parity()
if not ray.get("all_match"):
    freeze_role("FRAME_READOUT", "none", None)
    raise SystemExit("RAY distances not locked; readout not frozen")
frames = run_frame_parity()
if not frames.get("all_match"):
    freeze_role("FRAME_READOUT", "none", None)
    raise SystemExit("frames not stable under argmax; readout not frozen")
subprocess.run([sys.executable, str(ROOT / "scripts" / "ablate.py")], cwd=ROOT, check=True)
if not ablations_isolate():
    freeze_role("FRAME_READOUT", "none", None)
    raise SystemExit("ablations do not isolate; readout not frozen")
ablation = json.loads((ROOT / "logs" / "ablation.json").read_text(encoding="utf-8"))
rows = {r["module"]: r for r in ablation.get("rows") or []}
ray_row = rows.get("RAY_COLUMN") or {}
ro_row = rows.get("FRAME_READOUT") or {}
if (ray_row.get("state_delta") or {}).get("px"):
    freeze_role("FRAME_READOUT", "none", None)
    raise SystemExit("RAY ablation moved pose")
if (ro_row.get("state_delta") or {}).get("px"):
    freeze_role("FRAME_READOUT", "none", None)
    raise SystemExit("READOUT ablation moved pose")
if int(ray_row.get("pixel_l1") or 0) <= 0 or int(ro_row.get("pixel_l1") or 0) <= 0:
    freeze_role("FRAME_READOUT", "none", None)
    raise SystemExit("RAY/READOUT ablation did not change pixels")
if not latch_held_key_dies():
    freeze_role("FRAME_READOUT", "none", None)
    raise SystemExit("LATCH held-key witness missing")
path = freeze_role(
    "FRAME_READOUT",
    "wta",
    {
        "frame_parity": True,
        "cases": [c["name"] for c in frames["cases"]],
        "l1": {c["name"]: c["l1"] for c in frames["cases"]},
    },
)
print("FRAME_READOUT wta", path)
