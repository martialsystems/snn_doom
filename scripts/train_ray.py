#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from snn_doom.modules.train import freeze_role
from snn_doom.snn.bakeoff import run_bakeoff

data = run_bakeoff()
role = "RAY_COLUMN"
enc = data["winners"][role]
row = next((r for r in data["rows"] if r["role"] == role and r["encoding"] == enc), None)
freeze_role(role, enc, row, ROOT / "checkpoints" / "ray.json")
print(role, enc)
