#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.ray_parity import run_parity


def main() -> None:
    payload = run_parity()
    print(json.dumps({c["name"]: {"match": c["match"], "teacher": c["teacher"], "snn": c["snn"]} for c in payload["cases"]}, indent=2))
    print("all_match", payload["all_match"])


if __name__ == "__main__":
    main()
