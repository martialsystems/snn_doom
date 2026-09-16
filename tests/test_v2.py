# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
from pathlib import Path

from snn_doom.const import V1_NEURON_CAP, V2_NEURON_CAP
from snn_doom.play import _v2_ready, main as play_main
from snn_doom.teacher.engine import tick, tick_v2
from snn_doom.teacher.maps import spawn

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


def test_apply_enemy2_still_out_of_v1_tick() -> None:
    src = (REPO / "src" / "snn_doom" / "teacher" / "engine.py").read_text(encoding="utf-8")
    body = src[src.find("def tick(") : src.find("\ndef run(")]
    assert "apply_enemy2" not in body
    s = spawn()
    idle = tick(s, 0)
    assert idle.state.ex2 == s.ex2
    assert idle.state.ey2 == s.ey2


def test_tick_v2_second_chaser_walks() -> None:
    s = spawn()
    nxt = tick_v2(s, 0)
    assert nxt.state.ex2 != s.ex2 or nxt.state.ey2 != s.ey2
    assert nxt.state.ex != s.ex or nxt.state.ey != s.ey
    src = (REPO / "src" / "snn_doom" / "teacher" / "engine.py").read_text(encoding="utf-8")
    v2_body = src[src.find("def tick_v2(") :]
    assert "walk_e2=True" in v2_body


def test_v1_checkpoint_unmoved() -> None:
    v1 = json.loads((REPO / "checkpoints" / "snn_doom_v1.json").read_text(encoding="utf-8"))
    assert v1["n_neurons"] == 7973
    assert v1["cap"] == 8000


def test_v2_stitch_and_tape_when_exported() -> None:
    ckpt = REPO / "checkpoints" / "snn_doom_v2.json"
    tape = REPO / "logs" / "tick_tape_v2.json"
    if not ckpt.is_file() or not tape.is_file():
        ok, why = _v2_ready()
        assert ok is False
        assert "v2 stitch missing" in why or "v2 tape" in why
        assert play_main(["--machine", "v2", "--ticks", "1"]) == 2
        return
    v2 = json.loads(ckpt.read_text(encoding="utf-8"))
    assert v2["n_neurons"] <= V2_NEURON_CAP
    assert v2["n_neurons"] == 9077
    assert v2["cap"] == V2_NEURON_CAP
    arch = (REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert f"{int(v2['n_neurons']):,}" in arch
    assert f"{int(v2['n_edges']):,}" in arch
    data = json.loads(tape.read_text(encoding="utf-8"))
    assert data.get("all_match") is True
    assert data.get("machine") == "v2"
    assert data["held"]["match"] is True
    assert data["two_chaser"]["match"] is True
    assert data["two_chaser"]["e2_moved"] is True
    ok, why = _v2_ready()
    assert ok is True, why
    assert play_main(["--ticks", "1"]) == 0
    assert play_main(["--machine", "v2", "--ticks", "1"]) == 0


def test_play_default_stays_v1() -> None:
    play = (REPO / "src" / "snn_doom" / "play.py").read_text(encoding="utf-8")
    assert 'choices=("v1", "v2"), default="v1"' in play
    demo = (REPO / "scripts" / "run_demo.py").read_text(encoding="utf-8")
    assert 'choices=("v1", "v2"), default="v1"' in demo
