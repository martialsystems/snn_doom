#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.teacher.maps import MAPS, spawn


def main() -> None:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "web" / "pack"
    m = build_doom_snn()
    s0 = spawn(rows=MAPS["door"], door_closed=1)
    m.reset(s0)
    pix = m.tick(0)
    payload = {
        "pixels": pix.flatten().astype(int).tolist(),
        "state": m.read_state(),
        "map_bits": m.read_map_bits(),
        "door": m.read_door(),
        "hitscan": m.read_hitscan(),
        "shot": m.read_shot(),
    }
    (dest / "expect_tick0.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    print("wrote", dest / "expect_tick0.json", "n", m.net.n)


if __name__ == "__main__":
    main()
