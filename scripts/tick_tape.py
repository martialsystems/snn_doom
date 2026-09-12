#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.tick_tape import run_tick_tape


def main() -> None:
    payload = run_tick_tape()
    summary = {
        "all_match": payload["all_match"],
        "extra_ticks": payload["extra_ticks"],
        "tapes": {t["name"]: t["match"] for t in payload["tapes"]},
    }
    print(json.dumps(summary, indent=2))
    if not payload["all_match"]:
        for tape in payload["tapes"]:
            if tape["match"]:
                continue
            bad = [s["i"] for s in tape["steps"] if not s["match"]]
            print(tape["name"], "fail steps", bad)


if __name__ == "__main__":
    main()
