#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Train/freeze each module against the teacher, then export a checkpoint.

Winners that already pass as hand-wired digital priors are frozen as-is.
Analog encodings that fail the gate stay failed; this script does not hide that.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from doomforge.evidence import write_freeze_manifest
from doomforge.gate import require_can_bakeoff
from doomforge.graphs.module_freeze import ORDER
from snn_doom.const import ROLES, SEED
from snn_doom.modules.train import freeze_role
from snn_doom.snn.bakeoff import write_bakeoff
from snn_doom.ray_parity import run_parity


def main() -> None:
    require_can_bakeoff()
    bake = write_bakeoff(ROOT / "logs" / "bakeoff.json", ROOT / "docs" / "bakeoff.md")
    parity = run_parity()
    ckpt_dir = ROOT / "checkpoints"
    ckpt_dir.mkdir(exist_ok=True)
    frozen = {}
    ray_ok = bool(parity.get("all_match"))
    for role in ORDER:
        enc = bake["winners"].get(role, "none")
        if role == "RAY_COLUMN" and not ray_ok:
            enc = "none"
        if role == "FRAME_READOUT" and not ray_ok:
            print("skip FRAME_READOUT: RAY not frozen")
            continue
        row = next((r for r in bake["rows"] if r["role"] == role and r["encoding"] == enc), None)
        freeze_role(role, enc, row)
        frozen[role] = enc
        print(f"freeze {role} -> {enc}")
    write_freeze_manifest()
    bundle = ckpt_dir / "v1.json"
    bundle.write_text(json.dumps({"seed": SEED, "modules": frozen, "bakeoff": "logs/bakeoff.json"}, indent=2) + "\n")
    print("wrote", bundle)


if __name__ == "__main__":
    main()
