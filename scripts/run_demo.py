#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Host: inject keys, step SNN, decode pixels, display. No teacher tick.

Default is --play. Headless CI uses --frames N.
"""
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
from snn_doom.teacher.maps import MAPS
from snn_doom.teacher.state import pack_input


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--frames", type=int, default=None)
    p.add_argument("--out", type=Path, default=ROOT / "logs" / "demo_frame.png")
    p.add_argument("--fwd", action="store_true")
    p.add_argument("--play", action="store_true", help="live console window (default)")
    p.add_argument("--tty", action="store_true", help="live terminal console")
    p.add_argument("--lab", action="store_true", help="show spike raster")
    p.add_argument("--fast", action="store_true")
    p.add_argument("--scale", type=int, default=32)
    p.add_argument("--map", dest="map_name", default="door", choices=sorted(MAPS))
    p.add_argument("--ghost", type=Path, default=None)
    p.add_argument("--no-radar", action="store_true")
    p.add_argument("--no-dead", action="store_true")
    p.add_argument("--no-waves", action="store_true")
    p.add_argument("--wave-e2", action="store_true")
    p.add_argument("--machine", choices=("v1", "v2"), default="v1")
    args = p.parse_args()
    require_demo_path()
    machine = None
    if args.machine == "v2":
        from snn_doom.play import _v2_ready
        from snn_doom.modules.pipeline import build_doom_snn

        ok, why = _v2_ready()
        if not ok:
            print(why, file=sys.stderr)
            raise SystemExit(2)
        machine = build_doom_snn(walk_e2=True)
    headless = args.frames is not None and args.frames > 0 and not args.play and not args.tty
    if headless:
        n = args.frames
        bits = pack_input(0, 0, int(args.fwd), 0)
        inputs = [bits] * max(n, 1)
        stats = run_demo(frames=max(n, 1), out=args.out, inputs=inputs, machine=machine)
    else:
        from snn_doom.demo.console import run_console

        n = 0 if args.frames is None else args.frames
        stats = run_console(
            machine=machine,
            ticks=n,
            display=not args.tty,
            tty=bool(args.tty),
            lab=bool(args.lab) and not args.fast,
            scale=args.scale,
            map_name=args.map_name,
            door_closed=args.map_name == "door",
            fwd_lock=bool(args.fwd),
            ghost=args.ghost,
            radar=not args.no_radar,
            splash=not args.no_dead,
            waves=not args.no_waves,
            wave_e2=bool(args.wave_e2),
            out=None if args.tty else args.out,
        )
    dump = {k: stats[k] for k in ("ticks_per_sec", "n_neurons", "spikes_per_step", "state", "score", "outcome") if k in stats}
    print(json.dumps(dump, indent=2, default=str))


if __name__ == "__main__":
    main()
