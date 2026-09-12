# Copyright (c) 2026 Martial Systems LLC
"""166k refused until RAY distances lock and ablations isolate, including LATCH."""
from __future__ import annotations

from typing import Any

from doomforge.graphs._common import binary_graph

SCALE_INTENTS = frozenset({"scale_166k", "malecns_init", "fly_budget"})


def _evaluate(state: dict[str, Any]) -> dict[str, Any]:
    v: list[str] = []
    intent = str(state.get("intent") or "")
    if intent not in SCALE_INTENTS:
        return {"violations": v, "events": [{"node": "evaluate", "ok": True}]}
    if not bool(state.get("ray_distances_exact")):
        v.append("ray_distances_not_exact")
    if not bool(state.get("ablations_isolate")):
        v.append("ablations_not_isolating")
    if not bool(state.get("latch_held_key_dies")):
        v.append("latch_ablation_silent")
    if not bool(state.get("ray_frozen")):
        v.append("ray_not_frozen")
    return {"violations": v, "events": [{"node": "evaluate", "ok": not v}]}


def build_graph():
    return binary_graph(
        name="doom.scale_166k",
        evaluate=_evaluate,
        extra=[
            "intent",
            "ray_distances_exact",
            "ablations_isolate",
            "latch_held_key_dies",
            "ray_frozen",
        ],
    )
