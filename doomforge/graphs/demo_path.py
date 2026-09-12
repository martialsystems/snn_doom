# Copyright (c) 2026 Martial Systems LLC
"""Demo host surface: no teacher.tick / cast_ray in the demo import graph."""
from __future__ import annotations

from typing import Any

from doomforge.graphs._common import binary_graph


def _evaluate(state: dict[str, Any]) -> dict[str, Any]:
    v: list[str] = []
    hits = list(state.get("demo_banned_hits") or [])
    if hits:
        v.append("demo_calls_teacher_engine")
    return {"violations": v, "events": [{"node": "evaluate", "ok": not v, "hits": hits}]}


def build_graph():
    return binary_graph(
        name="doom.demo_path",
        evaluate=_evaluate,
        extra=["demo_banned_hits"],
    )
