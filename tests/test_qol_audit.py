# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from pathlib import Path

from snn_doom.qol.auditor import SCORE_WEIGHTS, audit_proposal, load_proposal, scan_dir

REPO = Path(__file__).resolve().parents[1]
PROPOSALS = REPO / "proposals"


def test_weights_sum_to_one() -> None:
    assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9
    assert SCORE_WEIGHTS["observable"] == 0.30
    assert SCORE_WEIGHTS["named_job_ablation"] == 0.20
    assert SCORE_WEIGHTS["parity"] == 0.15


def test_load_moving_enemy2_yaml() -> None:
    p = load_proposal(PROPOSALS / "moving_enemy2.yaml")
    assert p["name"] == "moving_second_sprite"
    assert p["estimated_new_neurons"] == 86
    assert p["must_not_break"][0] == "ray_parity"
    assert "muxed register" in p["alternatives"][1]


def test_moving_enemy2_accept_with_cap() -> None:
    report = audit_proposal(load_proposal(PROPOSALS / "moving_enemy2.yaml"))
    assert report["verdict"] == "ACCEPT_WITH_CAP"
    assert report["headroom"] < 0
    assert report["baseline_neurons"] == 7973
    assert any(o["player_actionable"] for o in report["observable_deltas"])
    assert report["named_job_ok"]["ok"] is True
    assert report["teacher_specifiable"]["ok"] is True
    assert "doom.v1_cap" in report["gates_failed"]
    assert report["cheaper_alternative"]["neurons"] == 40
    assert "—" not in str(report)


def test_mux_still_over_headroom() -> None:
    report = audit_proposal(load_proposal(PROPOSALS / "mux_enemy2.yaml"))
    assert report["verdict"] == "ACCEPT_WITH_CAP"
    assert report["estimated_new_neurons"] == 40
    assert report["headroom"] < 0
    assert "doom.v1_cap" in report["gates_failed"]


def test_view_32_proposal_under_v2_cap() -> None:
    from snn_doom.const import V2_NEURON_CAP

    p = load_proposal(PROPOSALS / "view_32.yaml")
    assert p["name"] == "view_32"
    assert p["estimated_new_neurons"] == 3200
    assert p["ablation_target"]
    report = audit_proposal(p, cap=V2_NEURON_CAP)
    assert report["verdict"] in {"ACCEPT", "ACCEPT_WITH_CAP"}
    assert report["cap"] == V2_NEURON_CAP
    assert "doom.v1_cap" not in report["gates_failed"]
    assert any(o["player_actionable"] for o in report["observable_deltas"])
    assert report["teacher_specifiable"]["ok"] is True
    assert "—" not in str(report)


def test_mux_accepts_under_v2_cap() -> None:
    from snn_doom.const import V2_NEURON_CAP

    report = audit_proposal(load_proposal(PROPOSALS / "mux_enemy2.yaml"), cap=V2_NEURON_CAP)
    assert report["cap"] == V2_NEURON_CAP
    assert report["headroom"] > 0
    assert report["verdict"] in {"ACCEPT", "ACCEPT_WITH_CAP"}
    assert "doom.v1_cap" not in report["gates_failed"]
    assert report["cap_law"] == "doom.v2_cap"


def test_waste_and_law_proposals() -> None:
    settle = audit_proposal(load_proposal(PROPOSALS / "settle_padding.yaml"))
    analog = audit_proposal(load_proposal(PROPOSALS / "analog_tau.yaml"))
    fly = audit_proposal(load_proposal(PROPOSALS / "fly_166k.yaml"))
    pal = audit_proposal(load_proposal(PROPOSALS / "host_palette.yaml"))
    radar = audit_proposal(load_proposal(PROPOSALS / "host_radar.yaml"))
    dead = audit_proposal(load_proposal(PROPOSALS / "host_dead.yaml"))
    waves = audit_proposal(load_proposal(PROPOSALS / "host_waves.yaml"))
    spare = audit_proposal(load_proposal(PROPOSALS / "spare_latches.yaml"))
    assert settle["verdict"] == "REJECT_WASTE"
    assert analog["verdict"] == "REJECT_BREAKS_LAW"
    assert "doom.demo_path" in analog["gates_failed"]
    assert fly["verdict"] == "REJECT_BREAKS_LAW"
    assert fly["fly_scale_refused"] is True
    assert "doom.scale_166k" in fly["gates_failed"]
    assert pal["verdict"] == "REJECT_WASTE"
    assert radar["verdict"] == "REJECT_WASTE"
    assert dead["verdict"] == "REJECT_WASTE"
    assert waves["verdict"] == "REJECT_WASTE"
    assert spare["verdict"] == "REJECT_WASTE"


def test_scan_writes_all_names() -> None:
    reports = scan_dir(PROPOSALS)
    names = {(r.get("proposal") or {}).get("name") for r in reports}
    assert "moving_second_sprite" in names
    assert "fly_scale_init" in names
    assert len(reports) >= 7


def test_auditor_does_not_import_demo_engine() -> None:
    import snn_doom.qol.auditor as aud

    src = Path(aud.__file__).read_text(encoding="utf-8")
    assert "teacher.tick" not in src
    assert "cast_ray(" not in src
    assert "paint_frame" not in src
    assert "build_doom_snn" not in src
    assert "require_v1_cap" not in src
    assert "require_settle_floor" not in src
