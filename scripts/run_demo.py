#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Host: inject keys, step SNN, decode pixels, display. No teacher tick."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.demo.view import run_demo
from snn_doom.teacher.state import pack_input


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--frames", type=int, default=1)
    p.add_argument("--out", type=Path, default=ROOT / "logs" / "demo_frame.png")
    p.add_argument("--fwd", action="store_true")
    args = p.parse_args()
    bits = pack_input(0, 0, int(args.fwd), 0)
    inputs = [bits] * max(args.frames, 1)
    stats = run_demo(frames=args.frames, out=args.out, inputs=inputs)
    print(json.dumps({k: stats[k] for k in ("ticks_per_sec", "n_neurons", "spikes_per_step", "state")}, indent=2))


if __name__ == "__main__":
    main()
