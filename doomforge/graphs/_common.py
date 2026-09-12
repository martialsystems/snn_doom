# Copyright (c) 2026 Martial Systems LLC
"""Shared allow/block graph builder."""
from __future__ import annotations

from typing import Any, Callable

from doomforge._bootstrap import ensure_paths

ensure_paths()

from graphforge import END, START, StateGraph, last_value, operator_add
from graphforge.state import ChannelSpec, StateSchema


def binary_graph(
    *,
    name: str,
    evaluate: Callable[[dict[str, Any]], dict[str, Any]],
    extra: list[str],
) -> StateGraph:
    specs = [ChannelSpec(k, last_value, default=False) for k in extra]
    specs += [
        ChannelSpec("violations", last_value, default=[]),
        ChannelSpec("decision", last_value, default=None),
        ChannelSpec("events", operator_add, default=[]),
    ]
    g = StateGraph(StateSchema.from_specs(specs), name=name)

    def allow(state: dict[str, Any]) -> dict[str, Any]:
        del state
        return {"decision": "allow", "events": [{"node": "allow"}]}

    def block(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": "block",
            "events": [{"node": "block", "violations": state.get("violations") or []}],
        }

    def route(state: dict[str, Any]) -> str:
        return "ok" if not (state.get("violations") or []) else "bad"

    g.add_node("evaluate", evaluate)
    g.add_node("allow", allow)
    g.add_node("block", block)
    g.add_edge(START, "evaluate")
    g.add_conditional_edges("evaluate", route, {"ok": "allow", "bad": "block"})
    g.add_edge("allow", END)
    g.add_edge("block", END)
    return g
