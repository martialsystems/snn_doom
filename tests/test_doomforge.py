# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import pytest

from doomforge.gate import (
    LawBlockedError,
    require_can_bakeoff,
    require_can_scale,
    require_can_train,
    require_demo_path,
)
from doomforge.graphs.module_freeze import build_graph as build_freeze
from doomforge.graphs.scale_166k import build_graph as build_scale
from doomforge.graphs.teacher_green import build_graph as build_teacher
from doomforge._bootstrap import ensure_paths

ensure_paths()

from graphforge.product_law import require_law


def test_teacher_green_blocks_bakeoff_without_suite() -> None:
    with pytest.raises(LawBlockedError):
        require_law(
            build_teacher(),
            {"intent": "bakeoff", "teacher_green": False},
            allow_decisions=["allow"],
            law_id="doom.teacher_green",
            raise_error=True,
        )


def test_teacher_green_allows_bakeoff_when_green() -> None:
    require_law(
        build_teacher(),
        {"intent": "bakeoff", "teacher_green": True},
        allow_decisions=["allow"],
        law_id="doom.teacher_green",
        raise_error=True,
    )


def test_readout_train_blocked_without_ray_freeze() -> None:
    frozen = {
        "CLOCK": True,
        "BIT_LATCH": True,
        "REGISTER_FILE": True,
        "ADDER_COMPARE": True,
        "RAM": True,
        "SEQUENCER": True,
        "RAY_COLUMN": False,
        "FRAME_READOUT": False,
    }
    with pytest.raises(LawBlockedError):
        require_law(
            build_freeze(),
            {"intent": "train_readout", "frozen": frozen},
            allow_decisions=["allow"],
            law_id="doom.module_freeze",
            raise_error=True,
        )


def test_ray_train_allowed_when_seq_frozen() -> None:
    frozen = {
        "CLOCK": True,
        "BIT_LATCH": True,
        "REGISTER_FILE": True,
        "ADDER_COMPARE": True,
        "RAM": True,
        "SEQUENCER": True,
        "RAY_COLUMN": False,
        "FRAME_READOUT": False,
    }
    require_law(
        build_freeze(),
        {"intent": "train_ray", "frozen": frozen},
        allow_decisions=["allow"],
        law_id="doom.module_freeze",
        raise_error=True,
    )


def test_scale_refused_until_ray_locks() -> None:
    with pytest.raises(LawBlockedError):
        require_law(
            build_scale(),
            {
                "intent": "scale_166k",
                "ray_distances_exact": False,
                "ablations_isolate": True,
                "latch_held_key_dies": True,
                "ray_frozen": True,
            },
            allow_decisions=["allow"],
            law_id="doom.scale_166k",
            raise_error=True,
        )


def test_scale_idle_intent_allowed() -> None:
    require_law(
        build_scale(),
        {"intent": ""},
        allow_decisions=["allow"],
        law_id="doom.scale_166k",
        raise_error=True,
    )


def test_gate_live_edges() -> None:
    require_can_bakeoff()
    require_can_train("train_ray")
    require_demo_path()
    with pytest.raises(LawBlockedError):
        require_can_train("train_readout")
    with pytest.raises(LawBlockedError):
        require_can_scale()
