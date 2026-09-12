# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

from snn_doom.const import SEED


def freeze_role(role: str, encoding: str, row: dict | None, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "role": role,
                "encoding": encoding,
                "seed": SEED,
                "hand_wired": encoding in ("dual_rail", "bistable", "oscillator", "wta"),
                "row": row,
                "frozen": encoding != "none",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
