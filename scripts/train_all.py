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
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.const import ROLES, SEED
from snn_doom.snn.bakeoff import write_bakeoff


def main() -> None:
    bake = write_bakeoff(ROOT / "logs" / "bakeoff.json", ROOT / "docs" / "bakeoff.md")
    ckpt_dir = ROOT / "checkpoints"
    ckpt_dir.mkdir(exist_ok=True)
    frozen = {}
    for role in ROLES:
        enc = bake["winners"][role]
        row = next(r for r in bake["rows"] if r["role"] == role and r["encoding"] == enc) if enc != "none" else None
        payload = {
            "role": role,
            "encoding": enc,
            "seed": SEED,
            "hand_wired": enc in ("dual_rail", "bistable", "oscillator", "wta"),
            "row": row,
            "frozen": enc != "none",
        }
        path = ckpt_dir / f"{role.lower()}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        frozen[role] = enc
        print(f"freeze {role} -> {enc}")
    bundle = ckpt_dir / "v1.json"
    bundle.write_text(json.dumps({"seed": SEED, "modules": frozen, "bakeoff": "logs/bakeoff.json"}, indent=2) + "\n")
    print("wrote", bundle)


if __name__ == "__main__":
    main()
