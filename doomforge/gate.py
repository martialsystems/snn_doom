# Copyright (c) 2026 Martial Systems LLC
"""Call sites for refuse laws. VBD is evidence. This module is the edge."""
from __future__ import annotations

from typing import Any

from doomforge._bootstrap import ensure_paths

ensure_paths()

from graphforge.product_law import LawBlockedError, require_law

from doomforge import evidence
from doomforge.graphs.demo_path import build_graph as build_demo
from doomforge.graphs.module_freeze import TRAIN_INTENT, build_graph as build_freeze
from doomforge.graphs.scale_166k import build_graph as build_scale
from doomforge.graphs.teacher_green import build_graph as build_teacher


def require_teacher_green(*, intent: str) -> None:
    require_law(
        build_teacher(),
        {"intent": intent, "teacher_green": evidence.teacher_green()},
        allow_decisions=["allow"],
        law_id="doom.teacher_green",
        thread_id=intent,
        raise_error=True,
    )


def require_can_train(intent: str) -> None:
    require_teacher_green(intent=intent)
    require_law(
        build_freeze(),
        {"intent": intent, "frozen": evidence.frozen_map()},
        allow_decisions=["allow"],
        law_id="doom.module_freeze",
        thread_id=intent,
        raise_error=True,
    )


def require_can_bakeoff() -> None:
    require_teacher_green(intent="bakeoff")


def require_demo_path() -> None:
    require_law(
        build_demo(),
        {"demo_banned_hits": evidence.scan_demo_banned_hits()},
        allow_decisions=["allow"],
        law_id="doom.demo_path",
        thread_id="demo",
        raise_error=True,
    )


def require_can_scale(*, intent: str = "scale_166k") -> None:
    require_law(
        build_scale(),
        {
            "intent": intent,
            "ray_distances_exact": evidence.ray_distances_exact(),
            "ablations_isolate": evidence.ablations_isolate(),
            "latch_held_key_dies": evidence.latch_held_key_dies(),
            "all_modules_frozen": evidence.all_modules_frozen(),
            "multi_tick_parity": evidence.multi_tick_parity(),
            "extra_units_declared": evidence.extra_units_declared(),
        },
        allow_decisions=["allow"],
        law_id="doom.scale_166k",
        thread_id=intent,
        raise_error=True,
    )


def require_can_train_role(role: str) -> None:
    inv = {v: k for k, v in TRAIN_INTENT.items()}
    intent = inv.get(role)
    if intent is None:
        raise ValueError(f"no train intent for {role}")
    require_can_train(intent)


__all__ = [
    "LawBlockedError",
    "require_teacher_green",
    "require_can_train",
    "require_can_train_role",
    "require_can_bakeoff",
    "require_demo_path",
    "require_can_scale",
]
