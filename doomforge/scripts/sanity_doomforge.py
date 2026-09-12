#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Refuse paths for doomforge laws."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from doomforge.gate import LawBlockedError, require_can_bakeoff, require_can_scale, require_can_train, require_demo_path


def main() -> None:
    require_can_bakeoff()
    require_can_train("train_ray")
    require_demo_path()
    from doomforge.evidence import frozen_map, ray_distances_exact

    if frozen_map().get("RAY_COLUMN") and ray_distances_exact():
        require_can_train("train_readout")
    else:
        try:
            require_can_train("train_readout")
            raise SystemExit("expected RAY freeze block on train_readout")
        except LawBlockedError:
            pass
    try:
        require_can_scale()
        print("scale law would allow; not starting 166k")
    except LawBlockedError as exc:
        print("scale still blocked:", exc)
    print("doomforge sanity pass")


if __name__ == "__main__":
    main()
