# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.const import (
    ACC_GATE,
    NEURON_REF,
    SCORE_W_ACC,
    SCORE_W_NEUR,
    SCORE_W_NOISE,
    SCORE_W_SPIK,
    SCORE_W_STAB,
)


def score_row(row: dict) -> float:
    acc = float(row["accuracy"])
    stab = float(row["stability"])
    noise = float(row["noise_robustness"])
    neur = 1.0 - min(float(row["n_neurons"]) / NEURON_REF, 1.0)
    spk = 1.0 - min(float(row["spikes_per_step"]) / max(float(row["n_neurons"]), 1.0), 1.0)
    return (
        SCORE_W_ACC * acc
        + SCORE_W_STAB * stab
        + SCORE_W_NOISE * noise
        + SCORE_W_NEUR * neur
        + SCORE_W_SPIK * spk
    )


def passes_gate(role: str, accuracy: float) -> bool:
    return accuracy >= ACC_GATE[role]
