# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from pathlib import Path

from snn_doom.const import V1_NEURON_CAP, V2_NEURON_CAP
from snn_doom.play import _v2_ready, main as play_main
from snn_doom.teacher.engine import tick

REPO = Path(__file__).resolve().parents[1]


def test_v2_docs_name_cap_and_walker() -> None:
    v2 = (REPO / "docs" / "v2.md").read_text(encoding="utf-8")
    v1 = (REPO / "docs" / "v1.md").read_text(encoding="utf-8")
    for text in (v1, v2):
        assert "—" not in text
        assert "What it is not" not in text
        assert "What this is not" not in text
    assert "12,000" in v2
    assert "second chaser in `tick()`" in v2
    assert "doom.v2_cap" in v2
    assert "166,700" in v2
    assert "Phase 4" in v2
    assert "apply_enemy2" in v2
    assert V2_NEURON_CAP == 12_000
    assert V1_NEURON_CAP == 8_000
    assert not (REPO / "checkpoints" / "snn_doom_v2.json").is_file()
    assert not (REPO / "logs" / "tick_tape_v2.json").is_file()


def test_play_default_is_v1_and_v2_flag_fail_closed() -> None:
    ok, why = _v2_ready()
    assert ok is False
    assert "v2 stitch missing" in why
    assert play_main(["--machine", "v2", "--ticks", "1"]) == 2


def test_apply_enemy2_still_out_of_v1_tick() -> None:
    src = (REPO / "src" / "snn_doom" / "teacher" / "engine.py").read_text(encoding="utf-8")
    body = src[src.find("def tick(") : src.find("\ndef run(")]
    assert "apply_enemy2" not in body
    assert tick is not None


def test_v1_checkpoint_unmoved() -> None:
    import json

    v1 = json.loads((REPO / "checkpoints" / "snn_doom_v1.json").read_text(encoding="utf-8"))
    assert v1["n_neurons"] == 7973
    assert v1["cap"] == 8000
