# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_readme_and_docs_prose() -> None:
    files = [
        REPO / "README.md",
        REPO / "docs" / "architecture.md",
        REPO / "docs" / "how_this_runs_doom.md",
        REPO / "docs" / "phase_log.md",
        REPO / "AGENTS.md",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "—" not in text, path
        assert "What it is not" not in text, path
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# snn_doom\n\nA fruit fly was mapped.")
    assert "## What this is not" in readme
    assert "## Methodology" in readme
    assert "## Honest scoreboard" in readme
    assert "104-bit" in readme
    assert "7,217" in readme
    assert "idle pixel L1 = 54" in readme
    assert "inject" in readme.lower()
    assert "teacher.tick" in readme
    assert "cast_ray" in readme
    how = (REPO / "docs" / "how_this_runs_doom.md").read_text(encoding="utf-8")
    assert "ViZDoom" in how
    assert "cast_ray" in how
