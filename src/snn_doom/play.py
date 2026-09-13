# Copyright (c) 2026 Martial Systems LLC
"""Front door: python -m snn_doom.play"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from snn_doom.demo.console import run_console
from snn_doom.teacher.maps import MAPS


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="snn-doom-play")
    p.add_argument("--tty", action="store_true")
    p.add_argument("--lab", action="store_true", help="show spike raster")
    p.add_argument("--fast", action="store_true", help="skip raster (default in --play)")
    p.add_argument("--scale", type=int, default=32)
    p.add_argument("--map", dest="map_name", default="door", choices=sorted(MAPS))
    p.add_argument("--fwd", action="store_true")
    p.add_argument("--ticks", type=int, default=0)
    p.add_argument("--ghost", type=Path, default=None)
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    stats = run_console(
        ticks=args.ticks,
        display=not args.tty,
        tty=bool(args.tty),
        lab=bool(args.lab) and not args.fast,
        scale=args.scale,
        map_name=args.map_name,
        door_closed=args.map_name == "door",
        fwd_lock=bool(args.fwd),
        ghost=args.ghost,
        sound=not args.quiet,
        out=args.out,
    )
    dump = {k: stats[k] for k in ("ticks_per_sec", "n_neurons", "ticks", "score", "outcome") if k in stats}
    print(json.dumps(dump, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
