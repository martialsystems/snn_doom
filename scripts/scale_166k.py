#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Scale toward the fly budget. Illegal until RAY distances lock."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from doomforge.gate import require_can_scale

require_can_scale(intent="scale_166k")
print("scale unlocked")
