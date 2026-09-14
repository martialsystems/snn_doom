# Copyright (c) 2026 Martial Systems LLC
"""Refuse laws. Verify-before-done is the finish gate. This file is the edge."""
from __future__ import annotations

from typing import Any


def laws() -> list[dict[str, Any]]:
    from snn_doom.const import FLIES_BUDGET

    from doomforge import evidence
    from doomforge.graphs.demo_path import build_graph as demo_path
    from doomforge.graphs.module_freeze import build_graph as module_freeze
    from doomforge.graphs.scale_166k import build_graph as scale_166k
    from doomforge.graphs.settle_floor import build_graph as settle_floor
    from doomforge.graphs.teacher_green import build_graph as teacher_green
    from doomforge.graphs.v1_cap import build_graph as v1_cap
    from doomforge.graphs.v2_cap import build_graph as v2_cap

    frozen = evidence.frozen_map()
    return [
        {
            "id": "doom.teacher_green",
            "build": teacher_green,
            "state": {"intent": "bakeoff", "teacher_green": evidence.teacher_green()},
            "allow_decisions": ["allow"],
        },
        {
            "id": "doom.module_freeze",
            "build": module_freeze,
            "state": {"intent": "train_ray", "frozen": frozen},
            "allow_decisions": ["allow"],
        },
        {
            "id": "doom.demo_path",
            "build": demo_path,
            "state": {"demo_banned_hits": evidence.scan_demo_banned_hits()},
            "allow_decisions": ["allow"],
        },
        {
            "id": "doom.scale_166k",
            "build": scale_166k,
            "state": {
                "intent": "",
                "ray_distances_exact": evidence.ray_distances_exact(),
                "ablations_isolate": evidence.ablations_isolate(),
                "latch_held_key_dies": evidence.latch_held_key_dies(),
                "all_modules_frozen": evidence.all_modules_frozen(),
                "multi_tick_parity": evidence.multi_tick_parity(),
                "extra_units_declared": evidence.extra_units_declared(),
            },
            "allow_decisions": ["allow"],
        },
        {
            "id": "doom.v1_cap",
            "build": v1_cap,
            "state": {
                "intent": "stitch",
                "n_neurons": evidence.v1_neurons(),
                "estimated_new_neurons": 0,
                "cap": evidence.v1_cap(),
            },
            "allow_decisions": ["allow"],
        },
        {
            "id": "doom.v2_cap",
            "build": v2_cap,
            "state": {
                "intent": "",
                "n_neurons": evidence.v2_neurons(),
                "estimated_new_neurons": 0,
                "cap": evidence.v2_cap(),
                "flies_budget": FLIES_BUDGET,
            },
            "allow_decisions": ["allow"],
        },
        {
            "id": "doom.settle_floor",
            "build": settle_floor,
            "state": {
                "intent": "ship",
                "settle": evidence.settle_live(),
                "settle_floor": evidence.settle_floor(),
                "adopt": False,
            },
            "allow_decisions": ["allow"],
        },
    ]
