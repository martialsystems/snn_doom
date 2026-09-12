# Copyright (c) 2026 Martial Systems LLC
"""module_i frozen before train module_{i+1}. RAY has no freeze until parity."""
from __future__ import annotations

from typing import Any

from doomforge.graphs._common import binary_graph

ORDER = (
    "CLOCK",
    "BIT_LATCH",
    "REGISTER_FILE",
    "ADDER_COMPARE",
    "RAM",
    "SEQUENCER",
    "RAY_COLUMN",
    "FRAME_READOUT",
)

TRAIN_INTENT = {
    "train_clock": "CLOCK",
    "train_latch": "BIT_LATCH",
    "train_reg": "REGISTER_FILE",
    "train_alu": "ADDER_COMPARE",
    "train_ram": "RAM",
    "train_seq": "SEQUENCER",
    "train_ray": "RAY_COLUMN",
    "train_readout": "FRAME_READOUT",
}


def prior_of(role: str) -> str | None:
    if role not in ORDER:
        return None
    i = ORDER.index(role)
    if i == 0:
        return None
    return ORDER[i - 1]


def _evaluate(state: dict[str, Any]) -> dict[str, Any]:
    v: list[str] = []
    intent = str(state.get("intent") or "")
    role = TRAIN_INTENT.get(intent)
    if role is None:
        return {"violations": v, "events": [{"node": "evaluate", "ok": True}]}
    prior = prior_of(role)
    if prior is None:
        return {"violations": v, "events": [{"node": "evaluate", "ok": True}]}
    frozen = state.get("frozen") or {}
    if not bool(frozen.get(prior)):
        v.append(f"{prior}_not_frozen")
    return {"violations": v, "events": [{"node": "evaluate", "ok": not v}]}


def build_graph():
    return binary_graph(
        name="doom.module_freeze",
        evaluate=_evaluate,
        extra=["intent", "frozen"],
    )
