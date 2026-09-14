# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import pytest

from doomforge.gate import (
    LawBlockedError,
    require_can_bakeoff,
    require_can_scale,
    require_can_train,
    require_demo_path,
    require_settle_floor,
    require_v1_cap,
    require_v2_cap,
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
                "all_modules_frozen": True,
                "multi_tick_parity": True,
                "extra_units_declared": True,
            },
            allow_decisions=["allow"],
            law_id="doom.scale_166k",
            raise_error=True,
        )


def test_scale_refused_without_extra_units_job() -> None:
    with pytest.raises(LawBlockedError):
        require_law(
            build_scale(),
            {
                "intent": "scale_166k",
                "ray_distances_exact": True,
                "ablations_isolate": True,
                "latch_held_key_dies": True,
                "all_modules_frozen": True,
                "multi_tick_parity": True,
                "extra_units_declared": False,
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
    from doomforge.evidence import frozen_map, ray_distances_exact

    require_can_bakeoff()
    require_can_train("train_ray")
    require_demo_path()
    require_v1_cap()
    require_v2_cap()
    require_settle_floor()
    if frozen_map().get("RAY_COLUMN") and ray_distances_exact():
        require_can_train("train_readout")
    else:
        with pytest.raises(LawBlockedError):
            require_can_train("train_readout")
    with pytest.raises(LawBlockedError):
        require_can_scale()


def test_v1_cap_blocks_over_8000() -> None:
    with pytest.raises(LawBlockedError):
        require_v1_cap(n_neurons=8001, intent="export")
    with pytest.raises(LawBlockedError):
        require_v1_cap(n_neurons=7973, estimated_new_neurons=40, intent="leftover_spend")
    require_v1_cap(n_neurons=7973, estimated_new_neurons=0, intent="export")


def test_settle_floor_blocks_24_while_probe_red() -> None:
    from doomforge.evidence import settle_floor, settle_live

    assert settle_live() == 29
    assert settle_floor() == 29
    with pytest.raises(LawBlockedError):
        require_settle_floor(settle=24, intent="ship")
    require_settle_floor(settle=29, intent="ship")
    require_settle_floor(settle=24, intent="probe", adopt=False)


def test_v2_cap_named_12k_blocks_flies() -> None:
    from snn_doom.const import V2_NEURON_CAP

    assert V2_NEURON_CAP == 12_000
    require_v2_cap(n_neurons=8_000, estimated_new_neurons=40, intent="export")
    with pytest.raises(LawBlockedError):
        require_v2_cap(n_neurons=12_001, intent="export")
    with pytest.raises(LawBlockedError):
        require_v2_cap(n_neurons=166_700, intent="export")
    require_v2_cap(intent="document")


def test_auditor_does_not_call_v1_cap_gate() -> None:
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "src" / "snn_doom" / "qol" / "auditor.py").read_text(
        encoding="utf-8"
    )
    assert "require_v1_cap" not in src
    assert "require_settle_floor" not in src
