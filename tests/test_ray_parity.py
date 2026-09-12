# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

from snn_doom.const import N_COLS
from snn_doom.ray_parity import CASES, LOGS, teacher_dists

REPO = Path(__file__).resolve().parents[1]


def test_teacher_fixture_is_sixteen_ints() -> None:
    assert len(CASES) == 4
    names = [c[0] for c in CASES]
    assert names == ["idle", "forward", "turn", "wall_graze"]
    for name, state, bits in CASES:
        dists = teacher_dists(state, bits)
        assert len(dists) == N_COLS, name
        assert all(isinstance(d, int) and 0 <= d <= 15 for d in dists)


def test_ray_parity_artifact_shape_if_present() -> None:
    path = LOGS / "ray_parity.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "all_match" in data
    assert len(data["cases"]) == 4
    for case in data["cases"]:
        assert len(case["teacher"]) == 16
        assert len(case["snn"]) == 16
