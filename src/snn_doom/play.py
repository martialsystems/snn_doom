# Copyright (c) 2026 Martial Systems LLC
"""Front door: python -m snn_doom.play"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from snn_doom.demo.console import run_console
from snn_doom.teacher.maps import MAPS

ROOT = Path(__file__).resolve().parents[2]


def _v2_ready() -> tuple[bool, str]:
    ckpt = ROOT / "checkpoints" / "snn_doom_v2.json"
    tape = ROOT / "logs" / "tick_tape_v2.json"
    if not ckpt.is_file():
        return False, "v2 stitch missing (checkpoints/snn_doom_v2.json); --play stays v1. See docs/v2.md"
    if not tape.is_file():
        return False, "v2 tape missing (logs/tick_tape_v2.json)"
    try:
        data = json.loads(tape.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "v2 tape unreadable"
    if not data.get("all_match"):
        return False, "v2 tape not all_match"
    return True, "ok"


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
    p.add_argument("--no-radar", action="store_true")
    p.add_argument("--no-dead", action="store_true", help="close on death instead of HOST_DEAD")
    p.add_argument("--no-waves", action="store_true", help="do not host-respawn e1")
    p.add_argument("--wave-e2", action="store_true", help="host-respawn the statue too")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--machine", choices=("v1", "v2"), default="v1")
    args = p.parse_args(argv)
    if args.machine == "v2":
        ok, why = _v2_ready()
        if not ok:
            print(why, file=sys.stderr)
            return 2
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
        radar=not args.no_radar,
        splash=not args.no_dead,
        waves=not args.no_waves,
        wave_e2=bool(args.wave_e2),
        out=args.out,
    )
    dump = {k: stats[k] for k in ("ticks_per_sec", "n_neurons", "ticks", "score", "outcome") if k in stats}
    print(json.dumps(dump, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
