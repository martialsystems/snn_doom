#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""ASCII teacher engine. Distillation target only, not the demo path."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.teacher.engine import tick
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.render import frame_to_ascii
from snn_doom.teacher.state import pack_input


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--fwd", action="store_true")
    args = p.parse_args()
    s = spawn()
    bits = pack_input(0, 0, int(args.fwd), 0)
    for i in range(args.steps):
        r = tick(s, bits)
        s = r.state
        print(f"t={i} px={s.px} py={s.py} ang={s.ang} ex={s.ex} ey={s.ey} hit={s.player_hit}")
        print(frame_to_ascii(r.pixels))
        print()


if __name__ == "__main__":
    main()
