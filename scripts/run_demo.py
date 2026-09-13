#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Host: inject keys, step SNN, decode pixels, display. No teacher tick."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from doomforge.gate import require_demo_path
from snn_doom.demo.view import run_demo
from snn_doom.teacher.state import pack_input


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--frames", type=int, default=None)
    p.add_argument("--out", type=Path, default=ROOT / "logs" / "demo_frame.png")
    p.add_argument("--fwd", action="store_true")
    p.add_argument("--play", action="store_true", help="live console window")
    p.add_argument("--tty", action="store_true", help="live terminal console")
    args = p.parse_args()
    require_demo_path()
    play = bool(args.play or args.tty or args.frames == 0)
    if play:
        from snn_doom.demo.console import run_console

        n = 0 if args.frames is None else args.frames
        pressed: set[str] = set()
        if args.fwd:
            pressed.add("up")
        stats = run_console(
            ticks=n,
            display=not args.tty,
            tty=bool(args.tty),
            pressed=pressed,
            out=None if args.tty else args.out,
        )
    else:
        n = 1 if args.frames is None else args.frames
        bits = pack_input(0, 0, int(args.fwd), 0)
        inputs = [bits] * max(n, 1)
        stats = run_demo(frames=max(n, 1), out=args.out, inputs=inputs)
    dump = {k: stats[k] for k in ("ticks_per_sec", "n_neurons", "spikes_per_step", "state") if k in stats}
    print(json.dumps(dump, indent=2))


if __name__ == "__main__":
    main()
