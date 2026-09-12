#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.snn.bakeoff import write_bakeoff


def main() -> None:
    data = write_bakeoff(ROOT / "logs" / "bakeoff.json", ROOT / "docs" / "bakeoff.md")
    print("winners", data["winners"])
    failed = [r for r in data["rows"] if r.get("error")]
    if failed:
        print("errors", len(failed))
        for r in failed:
            print(r["role"], r["encoding"], r["error"])


if __name__ == "__main__":
    main()
