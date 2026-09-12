# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

from snn_doom.const import SEED

try:
    from doomforge.evidence import ROLE_FILES, write_freeze_manifest
except ImportError:
    ROLE_FILES = {}
    write_freeze_manifest = None  # type: ignore[assignment]


def freeze_role(role: str, encoding: str, row: dict | None, dest: Path | None = None) -> Path:
    root = Path(__file__).resolve().parents[3]
    if dest is None:
        name = ROLE_FILES.get(role, role.lower() + ".json")
        dest = root / "checkpoints" / name
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
    if write_freeze_manifest is not None:
        write_freeze_manifest()
    return dest
