# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

from snn_doom.ray_parity import CASES, LOGS
from snn_doom.tick_tape import TAPE_N

REPO = Path(__file__).resolve().parents[1]


def test_tick_tape_artifact_when_logged() -> None:
    path = LOGS / "tick_tape.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("all_match") is True
    assert data.get("extra_ticks") == TAPE_N
    assert len(data["tapes"]) == len(CASES)
    for tape in data["tapes"]:
        assert tape["match"] is True
        assert len(tape["steps"]) == 1 + TAPE_N
        for step in tape["steps"]:
            assert step["pose_ok"] is True
            assert step["dist_ok"] is True
            assert step["frame_ok"] is True
            assert step["l1"] == 0
