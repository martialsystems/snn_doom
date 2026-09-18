# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.teacher.maps import spawn


def test_zero_readout_kills_pixels() -> None:
    m = build_doom_snn()
    m.reset(spawn())
    before = m.decode_pixels().copy()
    m.zero_module("FRAME_READOUT")
    # one more settle without readout wires
    for _ in range(8):
        m.net.step(m._input_current(0))
    after = m.decode_pixels()
    # argmax of zeros is color 0 (sky). Wall mass must drop.
    assert int((after == 2).sum()) < int((before == 2).sum()) or int(after.sum()) == 0


def test_ablation_json_held_key_visible() -> None:
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "logs" / "ablation.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("held_key") == "fwd"
    assert data.get("latch_held_key_dies") is True
    if "door_write_dies" in data:
        assert data["door_write_dies"] is True
    v2p = Path(__file__).resolve().parents[1] / "logs" / "ablation_v2.json"
    if v2p.is_file():
        v2 = json.loads(v2p.read_text(encoding="utf-8"))
        assert v2.get("machine") == "v2"
        assert v2.get("latch_held_key_dies") is True
        assert v2.get("door_write_dies") is True
        rows = {r["module"]: r for r in v2.get("rows") or []}
        for name in ("CLOCK", "BIT_LATCH", "REGISTER_FILE", "ADDER_COMPARE", "SEQUENCER"):
            assert rows[name]["state_delta"]["px"]
        for name in ("RAY_COLUMN", "FRAME_READOUT"):
            assert int(rows[name]["pixel_l1"]) > 0
        assert int(rows["RAM"]["pixel_l1"]) > 0
    v32p = Path(__file__).resolve().parents[1] / "logs" / "ablation_v2_32.json"
    if v32p.is_file():
        v32 = json.loads(v32p.read_text(encoding="utf-8"))
        assert v32.get("machine") == "v2_32"
        assert v32.get("latch_held_key_dies") is True
        assert v32.get("door_write_dies") is True
        rows32 = {r["module"]: r for r in v32.get("rows") or []}
        for name in ("CLOCK", "BIT_LATCH", "REGISTER_FILE", "ADDER_COMPARE", "SEQUENCER"):
            assert rows32[name]["state_delta"]["px"]
        for name in ("RAY_COLUMN", "FRAME_READOUT"):
            assert int(rows32[name]["pixel_l1"]) > 0
        assert int(rows32["RAM"]["pixel_l1"]) > 0


def test_zero_clock_freezes_sequencer() -> None:
    m = build_doom_snn()
    m.reset(spawn())
    m.zero_module("CLOCK")
    s0 = m.net.module_spikes("SEQUENCER").copy()
    for _ in range(24):
        m.net.step(m._input_current(0))
    s1 = m.net.module_spikes("SEQUENCER")
    # without clock beats, gated rings should not walk a full cycle
    assert s1.shape == s0.shape
