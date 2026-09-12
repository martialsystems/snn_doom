# Copyright (c) 2026 Martial Systems LLC
"""Bake-off and later trains require the teacher suite green on HEAD."""
from __future__ import annotations

from typing import Any

from doomforge.graphs._common import binary_graph

BAKEOFF_INTENTS = frozenset({"bakeoff", "train_all", "train_clock"})


def _evaluate(state: dict[str, Any]) -> dict[str, Any]:
    v: list[str] = []
    intent = str(state.get("intent") or "")
    if intent in BAKEOFF_INTENTS or intent.startswith("train_"):
        if not bool(state.get("teacher_green")):
            v.append("teacher_suite_not_green")
    return {"violations": v, "events": [{"node": "evaluate", "ok": not v}]}


def build_graph():
    return binary_graph(
        name="doom.teacher_green",
        evaluate=_evaluate,
        extra=["intent", "teacher_green"],
    )
