#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Refuse paths for doomforge laws."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

from doomforge.gate import (
    LawBlockedError,
    require_can_bakeoff,
    require_can_scale,
    require_can_train,
    require_demo_path,
    require_settle_floor,
    require_v1_cap,
)


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
    require_v1_cap()
    require_settle_floor()
    try:
        require_v1_cap(n_neurons=8001, intent="export")
        raise SystemExit("expected v1 cap block on 8001")
    except LawBlockedError:
        pass
    try:
        require_settle_floor(settle=24, intent="ship")
        raise SystemExit("expected settle floor block on 24")
    except LawBlockedError:
        pass
    print("doomforge sanity pass")


if __name__ == "__main__":
    main()
