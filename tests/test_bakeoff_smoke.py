# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.snn.encodings import build_clock, build_latch
from snn_doom.snn.bakeoff import eval_clock, eval_latch
from snn_doom.snn.score import score_row


def test_clock_oscillator_beats_rate() -> None:
    osc = eval_clock(build_clock("oscillator"))
    rate = eval_clock(build_clock("rate"))
    osc["noise_robustness"] = osc["accuracy"]
    rate["noise_robustness"] = rate["accuracy"]
    assert osc["accuracy"] > rate["accuracy"]
    assert score_row(osc) > 0.3


def test_latch_bistable_holds() -> None:
    row = eval_latch(build_latch("bistable"))
    assert row["accuracy"] >= 0.9
