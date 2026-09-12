# Copyright (c) 2026 Martial Systems LLC
"""166k refused until the whole engine is hashed, the tick tape matches, and extra units have a job."""
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
    if not bool(state.get("all_modules_frozen")):
        v.append("module_freeze_incomplete")
    if not bool(state.get("multi_tick_parity")):
        v.append("multi_tick_parity_missing")
    if not bool(state.get("extra_units_declared")):
        v.append("extra_units_undeclared")
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
            "all_modules_frozen",
            "multi_tick_parity",
            "extra_units_declared",
        ],
    )
