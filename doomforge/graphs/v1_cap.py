# Copyright (c) 2026 Martial Systems LLC
"""Published stitch and leftover spend may not exceed V1_NEURON_CAP."""
from __future__ import annotations

from typing import Any

from doomforge.graphs._common import binary_graph


def _evaluate(state: dict[str, Any]) -> dict[str, Any]:
    v: list[str] = []
    n = int(state.get("n_neurons") or 0)
    est = int(state.get("estimated_new_neurons") or 0)
    cap = int(state.get("cap") or 0)
    if cap <= 0 or n < 0:
        v.append("checkpoint_missing")
    elif n + est > cap:
        v.append("over_cap")
    return {"violations": v, "events": [{"node": "evaluate", "ok": not v}]}


def build_graph():
    return binary_graph(
        name="doom.v1_cap",
        evaluate=_evaluate,
        extra=["intent", "n_neurons", "estimated_new_neurons", "cap"],
    )
