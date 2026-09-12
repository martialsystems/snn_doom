# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

from snn_doom.ray_parity import CASES, LOGS

REPO = Path(__file__).resolve().parents[1]


def test_frame_parity_artifact_when_logged() -> None:
    path = LOGS / "frame_parity.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("all_match") is True
    assert len(data["cases"]) == 5
    names = [c["name"] for c in data["cases"]]
    assert names == [c[0] for c in CASES]
    for case in data["cases"]:
        assert case["l1"] == 0
        assert case["match"] is True
