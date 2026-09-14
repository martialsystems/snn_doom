# Copyright (c) 2026 Martial Systems LLC
"""Do not ship a SETTLE below the last green held-fwd floor."""
from __future__ import annotations

from typing import Any

from doomforge.graphs._common import binary_graph


def _evaluate(state: dict[str, Any]) -> dict[str, Any]:
    v: list[str] = []
    intent = str(state.get("intent") or "ship")
    adopt = bool(state.get("adopt"))
    if intent == "probe" and not adopt:
        return {"violations": v, "events": [{"node": "evaluate", "ok": True}]}
    settle = int(state.get("settle") or 0)
    floor = int(state.get("settle_floor") or 0)
    if floor <= 0:
        v.append("settle_probe_missing")
    elif settle < floor:
        v.append("settle_below_floor")
    return {"violations": v, "events": [{"node": "evaluate", "ok": not v}]}


def build_graph():
    return binary_graph(
        name="doom.settle_floor",
        evaluate=_evaluate,
        extra=["intent", "settle", "settle_floor", "adopt"],
    )
