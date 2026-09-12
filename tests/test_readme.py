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
    assert readme.startswith("# snn_doom\n")
    assert "104-bit" in readme or "104-bit" in (REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "inject" in readme.lower()
    how = (REPO / "docs" / "how_this_runs_doom.md").read_text(encoding="utf-8")
    assert "ViZDoom" in how
    assert "cast_ray" in how
