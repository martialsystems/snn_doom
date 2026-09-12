# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

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
    assert "104-bit" in method
    assert "idle pixel L1 = 54" in method
    assert "teacher.tick" in method
    assert "cast_ray" in method
    how = (REPO / "docs" / "how_this_runs_doom.md").read_text(encoding="utf-8")
    assert "ViZDoom" in how
    assert "cast_ray" in how
