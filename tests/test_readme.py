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
        REPO / "docs" / "v1.md",
        REPO / "docs" / "v2.md",
        REPO / "docs" / "v2_32.md",
        REPO / "AGENTS.md",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "—" not in text, path
        if path.name != "README.md":
            assert "What it is not" not in text, path
            assert "What this is not" not in text, path
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "# snn_doom\n\nA fruit fly was mapped." in readme
    assert "## What this is not" not in readme
    assert "## What it is not" in readme
    assert "docs/v1.md" in readme
    assert "docs/v2.md" in readme
    assert "docs/v2_32.md" in readme
    assert "martialgames.net/snn-doom/" in readme
    assert readme.index("docs/v1.md") < readme.index("## Play")
    assert "inject" in readme.lower()
    assert "decode" in readme.lower()
    assert "docs/methodology.md" in readme
    assert "--play" in readme
    assert "python -m snn_doom.play" in readme
    assert "--scale" in readme
    assert (REPO / "docs" / "play.gif").is_file()
    assert (REPO / "docs" / "dead.gif").is_file()
    assert (REPO / "docs" / "tty.png").is_file()
    assert "docs/play.gif" in readme
    assert "docs/dead.gif" in readme
    assert "HOST_RADAR" in readme
    assert "HOST_DEAD" in readme
    assert "six keys" in readme
    method = (REPO / "docs" / "methodology.md").read_text(encoding="utf-8")
    assert "7,217" in method
    assert "127-bit" in method
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
    assert "REGISTER_FILE (px,py,ang,ex,ey,ex2,ey2,flags,ammo,hp,pickup)" in arch
    assert "e1 or e2" in arch
    assert "ammo is greater than 0" in arch
    assert "heading ray visited" in arch
    assert "AND the fifth key with the heading column sprite" not in arch


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


def test_methods_card_and_citation() -> None:
    methods = (REPO / "METHODS.yaml").read_text(encoding="utf-8")
    assert "science_lock:" in methods
    assert "pre_specified: false" in methods
    assert "—" not in methods
    assert "What it is not" not in methods
    cite = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    assert "cff-version: 1.2.0" in cite
    assert "Martial Systems LLC" in cite
