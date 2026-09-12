#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from doomforge.gate import require_can_train
from snn_doom.modules.train import freeze_role
from snn_doom.ray_parity import run_parity

require_can_train("train_ray")
parity = run_parity()
role = "RAY_COLUMN"
if not parity.get("all_match"):
    freeze_role(role, "none", None)
    raise SystemExit("RAY distances not bit-exact vs teacher; not frozen")
freeze_role(role, "dual_rail", {"parity": True})
print(role, "dual_rail")
