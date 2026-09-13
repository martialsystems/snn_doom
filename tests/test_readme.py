# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_readme_and_docs_prose() -> None:
    files = [
        REPO / "README.md",
        REPO / "docs" / "architecture.md",
        REPO / "docs" / "how_this_runs_doom.md",
        REPO / "docs" / "methodology.md",
        REPO / "docs" / "phase_log.md",
        REPO / "AGENTS.md",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "—" not in text, path
        assert "What it is not" not in text, path
        assert "What this is not" not in text, path
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# snn_doom\n\nA fruit fly was mapped.")
    assert "## What this is not" not in readme
    assert "inject" in readme.lower()
    assert "decode" in readme.lower()
    assert "docs/methodology.md" in readme
    method = (REPO / "docs" / "methodology.md").read_text(encoding="utf-8")
    assert "7,217" in method
    assert "124-bit" in method
    assert "ray_parity.json" in method
    assert "teacher.tick" in method
    assert "cast_ray" in method
    how = (REPO / "docs" / "how_this_runs_doom.md").read_text(encoding="utf-8")
    assert "ViZDoom" in how
    assert "cast_ray" in how


def test_architecture_stitch_matches_export() -> None:
    """Graph doc must track the freeze stitch, not the Phase 3 7,217 line."""
    v1 = json.loads((REPO / "checkpoints" / "snn_doom_v1.json").read_text(encoding="utf-8"))
    arch = (REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert f"{int(v1['n_neurons']):,}" in arch
    assert f"{int(v1['n_edges']):,}" in arch
    assert f"{int(v1['steps_per_tick']):,}" in arch
    assert "7,217 neurons, 38,722 edges" not in arch


def test_methodology_7217_is_museum_not_live() -> None:
    """7,217 is a Phase 3 history pin. Cleanup must not treat it as the running machine."""
    v1 = json.loads((REPO / "checkpoints" / "snn_doom_v1.json").read_text(encoding="utf-8"))
    method = (REPO / "docs" / "methodology.md").read_text(encoding="utf-8")
    live = f"{int(v1['n_neurons']):,}"
    assert f"Running machine: {live}" in method
    idx = method.find("7,217")
    assert idx >= 0
    window = method[max(0, idx - 100) : idx + 80]
    assert "museum" in window.lower()
    assert "not the running machine" in window.lower()
