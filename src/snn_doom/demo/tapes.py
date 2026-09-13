# Copyright (c) 2026 Martial Systems LLC
"""Record/replay 6-bit input tapes. Ghost overlay uses the same host loop."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from snn_doom.modules.pipeline import DoomSNN, build_doom_snn
from snn_doom.teacher.maps import spawn

RUNS = Path(__file__).resolve().parents[3] / "logs" / "runs"


def save_bits(bits: list[int], path: Path | None = None) -> Path:
    RUNS.mkdir(parents=True, exist_ok=True)
    out = path or RUNS / f"{int(time.time())}.bits"
    out.write_bytes(bytes(b & 63 for b in bits))
    return out


def load_bits(path: Path) -> list[int]:
    return [b & 63 for b in path.read_bytes()]


def save_run(bits: list[int], poses: list[dict[str, int]] | None = None, path: Path | None = None) -> Path:
    out = save_bits(bits, path)
    if poses:
        payload = {"bits": [b & 63 for b in bits], "poses": poses}
        out.with_suffix(".json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return out


def load_ghost(path: Path) -> tuple[list[int], list[dict[str, int]]]:
    bits = load_bits(path)
    side = path.with_suffix(".json")
    if side.is_file():
        data = json.loads(side.read_text(encoding="utf-8"))
        poses = list(data.get("poses") or [])
        if poses:
            return bits, poses
    return bits, replay_poses(bits)


def replay_poses(bits: list[int], *, machine: DoomSNN | None = None) -> list[dict[str, int]]:
    """Ghost path: inject recorded bits, read REGISTER_FILE. No teacher tick."""
    m = machine or build_doom_snn()
    m.reset(spawn())
    poses: list[dict[str, Any]] = [m.read_state()]
    for b in bits:
        m.tick(b)
        poses.append(m.read_state())
    return poses
