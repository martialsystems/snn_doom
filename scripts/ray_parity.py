#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.ray_parity import run_parity, run_parity_32, write_teacher_ray_32


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--cols", type=int, choices=(16, 32), default=16)
    args = p.parse_args()
    if args.cols == 32:
        from pathlib import Path

        ckpt = Path(__file__).resolve().parents[1] / "checkpoints" / "snn_doom_v2_32.json"
        if ckpt.is_file():
            payload = run_parity_32()
            print(
                json.dumps(
                    {c["name"]: {"match": c["match"], "teacher": c["teacher"], "snn": c["snn"]} for c in payload["cases"]},
                    indent=2,
                )
            )
            print("all_match", payload["all_match"])
            return
        payload = write_teacher_ray_32()
        print(json.dumps({c["name"]: c["teacher"] for c in payload["cases"]}, indent=2))
        print("n_cols", payload["n_cols"], "missing_snn", payload["missing_snn"])
        return
    payload = run_parity()
    print(json.dumps({c["name"]: {"match": c["match"], "teacher": c["teacher"], "snn": c["snn"]} for c in payload["cases"]}, indent=2))
    print("all_match", payload["all_match"])


if __name__ == "__main__":
    main()
