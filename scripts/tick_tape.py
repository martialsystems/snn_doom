#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.tick_tape import run_tick_tape, run_tick_tape_v2, run_tick_tape_v2_32


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--machine", choices=("v1", "v2", "v2_32"), default="v1")
    args = p.parse_args()
    if args.machine == "v2_32":
        payload = run_tick_tape_v2_32()
    elif args.machine == "v2":
        payload = run_tick_tape_v2()
    else:
        payload = run_tick_tape()
    summary = {
        "all_match": payload["all_match"],
        "machine": payload.get("machine"),
        "extra_ticks": payload["extra_ticks"],
        "held_ticks": payload["held_ticks"],
        "tapes": {t["name"]: t["match"] for t in payload["tapes"]},
        "held": payload["held"]["match"],
        "held_hitscan": sum(s["teacher_hitscan"] for s in payload["held"]["steps"]),
        "trigger": payload["trigger"]["match"],
        "trigger_miss_alive": payload["trigger"]["miss"]["steps"][0]["teacher_pose"]["enemy_alive"],
        "trigger_kill_alive": payload["trigger"]["kill"]["steps"][0]["teacher_pose"]["enemy_alive"],
        "held_fire": payload["held_fire"]["match"],
        "held_fire_kills": sum(s["teacher_shot"] for s in payload["held_fire"]["steps"]),
        "death": payload["death"]["match"],
        "door": payload["door"]["match"],
        "door_block": payload["door"]["block"]["match"],
        "door_open": payload["door"]["open"]["match"],
        "door_close": payload["door"]["close"]["match"],
        "second": payload["second"]["match"],
        "ammo_dry": payload["ammo_dry"]["match"],
        "pickup": payload["pickup"]["match"],
        "two_chaser": (payload.get("two_chaser") or {}).get("match"),
        "two_chaser_e2_moved": (payload.get("two_chaser") or {}).get("e2_moved"),
    }
    print(json.dumps(summary, indent=2))
    if not payload["all_match"]:
        for tape in payload["tapes"]:
            if tape["match"]:
                continue
            bad = [s["i"] for s in tape["steps"] if not s["match"]]
            print(tape["name"], "fail steps", bad)
        if not payload["held"]["match"]:
            bad = [s["i"] for s in payload["held"]["steps"] if not s["match"]]
            print("held_fwd fail steps", bad)
        if not payload["trigger"]["match"]:
            print("trigger miss", payload["trigger"]["miss"]["match"], "kill", payload["trigger"]["kill"]["match"])
        if not payload["held_fire"]["match"]:
            bad = [s["i"] for s in payload["held_fire"]["steps"] if not s["match"] or s["teacher_shot"]]
            print("held_fire fail steps", bad)
        if not payload["death"]["match"]:
            print("death fail", [s["i"] for s in payload["death"]["steps"] if not s["match"]])
        if not payload["door"]["match"]:
            for name in ("block", "open", "close"):
                part = payload["door"][name]
                if not part["match"]:
                    print("door", name, [s["i"] for s in part["steps"] if not s["match"]])


if __name__ == "__main__":
    main()
