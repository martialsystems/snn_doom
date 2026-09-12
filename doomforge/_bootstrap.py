# Copyright (c) 2026 Martial Systems LLC
"""Put GraphForge + this repo on sys.path."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CANDIDATES = [Path.home() / "graphforge", REPO.parent / "graphforge"]


def ensure_paths() -> Path:
    for p in (ROOT, REPO, REPO / "src"):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
    for gf in CANDIDATES:
        src = gf / "src"
        if src.is_dir():
            if str(src) not in sys.path:
                sys.path.insert(0, str(src))
            return gf
    raise FileNotFoundError("GraphForge not found at ~/graphforge")
