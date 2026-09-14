# Copyright (c) 2026 Martial Systems LLC
"""v2 stitch may not exceed V2_NEURON_CAP and may not use the fly budget."""
from __future__ import annotations

from typing import Any

from doomforge.graphs._common import binary_graph

STITCH_INTENTS = frozenset({"stitch", "export", "leftover_spend", "v2"})


def _evaluate(state: dict[str, Any]) -> dict[str, Any]:
    v: list[str] = []
    intent = str(state.get("intent") or "")
    if intent not in STITCH_INTENTS:
        return {"violations": v, "events": [{"node": "evaluate", "ok": True}]}
    n = int(state.get("n_neurons") or 0)
    est = int(state.get("estimated_new_neurons") or 0)
    cap = int(state.get("cap") or 0)
    flies = int(state.get("flies_budget") or 0)
    if flies and n + est >= flies:
        v.append("flies_budget")
    if cap <= 0:
        v.append("cap_unnamed")
    elif n < 0:
        v.append("checkpoint_missing")
    elif n + est > cap:
        v.append("over_cap")
    return {"violations": v, "events": [{"node": "evaluate", "ok": not v}]}


def build_graph():
    return binary_graph(
        name="doom.v2_cap",
        evaluate=_evaluate,
        extra=["intent", "n_neurons", "estimated_new_neurons", "cap", "flies_budget"],
    )
