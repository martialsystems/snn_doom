# Copyright (c) 2026 Martial Systems LLC
"""Judge a neuron-spend proposal against the frozen stitch. Does not grow the net."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from snn_doom.const import (
    ACC_GATE,
    FLIES_BUDGET,
    STATE_FIELDS,
    V1_NEURON_CAP,
    V2_NEURON_CAP,
)
from snn_doom.qol.yaml_lite import load as load_yaml

REPO = Path(__file__).resolve().parents[3]
LOGS = REPO / "logs"
CKPT = REPO / "checkpoints" / "snn_doom_v1.json"
TEACHER_ENGINE = REPO / "src" / "snn_doom" / "teacher" / "engine.py"
PIPELINE = REPO / "src" / "snn_doom" / "modules" / "pipeline.py"

SCORE_WEIGHTS: dict[str, float] = {
    "observable": 0.30,
    "named_job_ablation": 0.20,
    "parity": 0.15,
    "cost": 0.15,
    "cap_named": 0.10,
    "spec_not_waste": 0.10,
}

VERDICT_ACCEPT = "ACCEPT"
VERDICT_CAP = "ACCEPT_WITH_CAP"
VERDICT_WASTE = "REJECT_WASTE"
VERDICT_LAW = "REJECT_BREAKS_LAW"

EXISTING_MODULES = (
    "CLOCK",
    "BIT_LATCH",
    "REGISTER_FILE",
    "ADDER_COMPARE",
    "RAM",
    "SEQUENCER",
    "RAY_COLUMN",
    "FRAME_READOUT",
    "DOOR",
)

TAPE_ALIASES = {
    "ray_parity": "ray_parity",
    "held_fwd_tape": "held",
    "held_fwd": "held",
    "held_fire": "held_fire",
    "door": "door",
    "ammo_zero_cannot_kill": "ammo_dry",
    "ammo_dry": "ammo_dry",
    "death": "death",
    "fire": "trigger",
    "trigger": "trigger",
    "second": "second",
    "pickup": "pickup",
    "tick_tape": "all_match",
}

WASTE_RE = re.compile(
    r"\b(padding|spare latch|just in case|capacity for later|unused readout|"
    r"settle\s*padding|analog tau|palette|matplotlib|blit|console hud|"
    r"fly cell|malecns|166,?700|166k)\b",
    re.I,
)
HOST_COSMETIC_RE = re.compile(
    r"\b(host[- ]side|overlay|blit|palette|matplotlib|console color|python hud)\b",
    re.I,
)
FLY_RE = re.compile(r"\b(166,?700|166k|fly[- ]scale|malecns|fly cell[- ]type)\b", re.I)
SETTLE_DROP_RE = re.compile(r"\bsettle\s*(=|:)?\s*(1[0-9]|2[0-8])\b", re.I)
ANALOG_RE = re.compile(r"\banalog\b.*\btau\b|\btau\s*=\s*0\.8\b|\bbptt\b", re.I)
NEURON_RE = re.compile(r"(\d+)\s*neurons", re.I)
ILLEGAL_ALT_RE = re.compile(r"illegal|demo path|fakes engine|host-side|overlay", re.I)

STATE_NAMES = {name for name, _ in STATE_FIELDS}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_proposal(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = load_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a mapping")
    data["_path"] = str(path)
    if not data.get("name"):
        data["name"] = path.stem
    return data


def load_baseline(compare: Path | None = None, cap: int | None = None) -> dict[str, Any]:
    path = compare or CKPT
    data = _read_json(path)
    n = int(data.get("n_neurons") or 0)
    e = int(data.get("n_edges") or 0)
    named = int(cap) if cap is not None else int(data.get("cap") or V1_NEURON_CAP)
    return {
        "path": str(path),
        "n_neurons": n,
        "n_edges": e,
        "cap": named,
        "modules": list(data.get("modules") or EXISTING_MODULES),
        "counts": dict(data.get("counts") or {}),
        "steps_per_tick": int(data.get("steps_per_tick") or 0),
    }


def _tick_body() -> str:
    text = TEACHER_ENGINE.read_text(encoding="utf-8") if TEACHER_ENGINE.is_file() else ""
    start = text.find("def tick(")
    end = text.find("\ndef run(", start)
    return text[start:end] if start >= 0 else text


def _pipeline_text() -> str:
    return PIPELINE.read_text(encoding="utf-8") if PIPELINE.is_file() else ""


def _live_logs() -> dict[str, Any]:
    ray = _read_json(LOGS / "ray_parity.json")
    tape = _read_json(LOGS / "tick_tape.json")
    ablate = _read_json(LOGS / "ablation.json")
    settle = _read_json(LOGS / "settle_probe.json")
    return {"ray": ray, "tape": tape, "ablate": ablate, "settle": settle}


def _blob(p: dict[str, Any]) -> str:
    parts = [
        str(p.get("claimed_job") or ""),
        str(p.get("claimed_qol") or ""),
        str(p.get("teacher_delta") or ""),
        str(p.get("view_delta") or ""),
        str(p.get("ablation_target") or ""),
        " ".join(str(x) for x in p.get("new_modules_or_edges") or []),
        " ".join(str(x) for x in p.get("new_state_bits") or []),
    ]
    return " ".join(parts)


def _ablation_tag(p: dict[str, Any]) -> str:
    raw = str(p.get("ablation_target") or "").strip()
    raw = re.sub(r"^module\s+tag\s+", "", raw, flags=re.I)
    return raw.replace(" ", "_").upper() if raw else ""


def _parse_alternatives(p: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in p.get("alternatives") or []:
        if isinstance(item, dict):
            text = str(item.get("name") or item.get("text") or item)
            neurons = item.get("neurons")
            if neurons is None:
                m = NEURON_RE.search(text)
                neurons = int(m.group(1)) if m else None
            legal = item.get("legal")
            if legal is None:
                legal = not bool(ILLEGAL_ALT_RE.search(text))
            out.append({"text": text, "neurons": neurons, "legal": bool(legal)})
            continue
        text = str(item)
        m = NEURON_RE.search(text)
        neurons = int(m.group(1)) if m else (0 if re.search(r"\b0 neurons\b", text, re.I) else None)
        legal = not bool(ILLEGAL_ALT_RE.search(text))
        out.append({"text": text, "neurons": neurons, "legal": legal})
    return out


def _tape_ok(logs: dict[str, Any], alias: str) -> bool | None:
    key = TAPE_ALIASES.get(alias, alias)
    if key == "ray_parity":
        return bool(logs["ray"].get("all_match")) if logs["ray"] else None
    tape = logs["tape"]
    if not tape:
        return None
    if key == "all_match":
        return bool(tape.get("all_match"))
    node = tape.get(key)
    if isinstance(node, dict):
        return bool(node.get("match"))
    if key == "held":
        return bool((tape.get("held") or {}).get("match"))
    return None


def _observables(p: dict[str, Any], tick_body: str) -> list[dict[str, Any]]:
    job = str(p.get("claimed_job") or "")
    qol = str(p.get("claimed_qol") or "")
    teacher = str(p.get("teacher_delta") or "")
    view = str(p.get("view_delta") or "")
    bits = [str(x) for x in p.get("new_state_bits") or []]
    blob = f"{job} {qol} {teacher} {view}"
    rows: list[dict[str, Any]] = []

    def add(channel: str, before: str, after: str, actionable: bool) -> None:
        rows.append(
            {
                "channel": channel,
                "before": before,
                "after": after,
                "player_actionable": actionable,
            }
        )

    if re.search(r"second enemy|e2|ex2|enemy2", blob, re.I) and re.search(
        r"step|walk|march|chase", blob, re.I
    ):
        live = "apply_enemy2(" in tick_body
        add(
            "teacher_state.ex2",
            "stationary statue at (2,2)" if not live else "already walks",
            "X-then-Y chase each pose",
            True,
        )
        add(
            "decoded_frame",
            "COLOR_ENEMY blob only if heading visits (2,2)",
            "second moving column blob; contact still decrements HP",
            True,
        )
    if re.search(r"\bdoor\b", blob, re.I) and re.search(r"second|another|new door", blob, re.I):
        add("teacher_state.map_bits", "one door cell (4,5)", "another toggle gate", True)
    if re.search(r"projectile|bullet flight", blob, re.I):
        add("teacher_state", "hitscan instant", "projectile with flight time", True)
    if re.search(r"32 column|view.?32|n_cols\s*=\s*32", blob, re.I):
        add("decoded_frame", "16 columns", "32 columns", True)
    if re.search(r"health|hit points|\bhp\b", blob, re.I) and "hp" in tick_body.lower():
        add("teacher_state.hp", "already 2-bit HP in tick", "no new observable", False)
    if re.search(r"pickup|ammo pack", blob, re.I) and "apply_pickup" in tick_body:
        add("teacher_state.ammo", "pickup already fills 7", "no new observable", False)
    if view and re.search(r"column blob|COLOR_ENEMY|sprite", view, re.I):
        if not any(r["channel"] == "decoded_frame" for r in rows):
            add("decoded_frame", "current 16x18x4 paint", view, True)
    hidden = [b for b in bits if b not in STATE_NAMES and not re.search(r"step|enable|door|hp|ammo", b, re.I)]
    if hidden and not rows:
        add("hidden_bits", "not in STATE_FIELDS", ",".join(hidden), False)
    if not rows and WASTE_RE.search(blob):
        add("none", "no player-visible delta", "internal only", False)
    if not rows:
        add(
            "unspecified",
            "frozen stitch",
            (teacher or view or job or "unnamed"),
            bool(teacher or view) and not WASTE_RE.search(blob),
        )
    return rows


def _parity_risks(p: dict[str, Any], logs: dict[str, Any]) -> list[dict[str, Any]]:
    blob = _blob(p)
    risks: list[dict[str, Any]] = []
    must = [str(x) for x in p.get("must_not_break") or []]

    def add(tape: str, why: str, live_ok: bool | None) -> None:
        alias = TAPE_ALIASES.get(tape, tape)
        listed = tape in must or alias in must
        if tape == "tick_tape" and any(x in must for x in ("held_fwd_tape", "held_fwd", "ray_parity", "door")):
            listed = True
        risks.append({"tape": tape, "why": why, "live_green": live_ok, "listed": listed})

    if re.search(r"RAY_COLUMN|column distance|N_COLS|32 column", blob) or "RAY_COLUMN" in blob:
        add("ray_parity", "RAY or column-count change can desync 16 distances", _tape_ok(logs, "ray_parity"))
    if re.search(r"e2|enemy2|second enemy|ex2", blob, re.I) and re.search(r"step|walk|chase|march", blob, re.I):
        add(
            "held_fwd_tape",
            "walking e2 can enter a heading column; held-fwd requires hitscan 0 and frame L1 0",
            _tape_ok(logs, "held_fwd_tape"),
        )
        add("tick_tape", "e2 pose bits and frames are on the multi-tick tape", _tape_ok(logs, "tick_tape"))
    if SETTLE_DROP_RE.search(blob) or re.search(r"drop SETTLE|SETTLE below", blob, re.I):
        settle_ok = bool(logs["settle"].get("match")) if logs["settle"] else False
        add("held_fwd_tape", "SETTLE below 29 skipped an enemy step on held-fwd (probe at 24 failed)", settle_ok)
    elif re.search(r"SETTLE|CLOCK", blob, re.I):
        add("held_fwd_tape", "CLOCK/SETTLE edits change steps per tick and can desync held-fwd", _tape_ok(logs, "held_fwd_tape"))
    if re.search(r"\bdoor\b", blob, re.I):
        add("door", "door occupancy pulse is a 2-step we_ram window", _tape_ok(logs, "door"))
    if re.search(r"ammo|fire|hitscan", blob, re.I):
        add("ammo_zero_cannot_kill", "ammo/fire datapath shares the heading sprite latch", _tape_ok(logs, "ammo_dry"))
    if re.search(r"READOUT|FRAME|16x18|32 column", blob, re.I):
        add("tick_tape", "frame_ok is on every tape step", _tape_ok(logs, "tick_tape"))
    if not risks:
        add("tick_tape", "any stitch edit can drift sequencer re-arm", _tape_ok(logs, "tick_tape"))
    return risks


def _named_job_ok(p: dict[str, Any]) -> tuple[bool, str]:
    job = str(p.get("claimed_job") or "").strip()
    tag = _ablation_tag(p)
    if not job or len(job) < 12:
        return False, "claimed_job is empty or shorter than one sentence"
    if "\n" in job:
        return False, "claimed_job must be one sentence"
    if not tag:
        return False, "ablation_target is missing"
    if tag in EXISTING_MODULES:
        return False, f"ablation_target {tag} is an existing module; zeroing it would also kill the old job"
    if tag in ACC_GATE:
        return False, f"ablation_target {tag} is a bake-off role; name a new cluster"
    return True, f"cluster {tag}: {job}"


def _teacher_specifiable(p: dict[str, Any], tick_body: str) -> tuple[bool, str]:
    delta = str(p.get("teacher_delta") or "").strip()
    blob = _blob(p)
    if not delta:
        return False, "teacher_delta is empty"
    if HOST_COSMETIC_RE.search(delta) and not re.search(r"apply_|state\.|map_bits|ex2", delta, re.I):
        return False, "teacher_delta is a host paint hack"
    if ANALOG_RE.search(blob):
        return False, "analog tau is bake-off only; demo path is digital tau=0"
    if FLY_RE.search(blob) and not re.search(r"apply_|STATE_", delta):
        return False, "fly cell types are not features"
    engine = TEACHER_ENGINE.read_text(encoding="utf-8") if TEACHER_ENGINE.is_file() else ""
    if re.search(r"ex2|enemy2|second sprite", delta, re.I):
        if "def apply_enemy2" in engine:
            if "apply_enemy2(" in tick_body:
                return True, "already in tick(); neuron spend would duplicate a live spec"
            return True, "apply_enemy2 exists and is not called from tick(); teacher can express the delta"
    if re.search(r"apply_door|map_bits|DOOR_IDX", delta):
        return True, "door occupancy is already a teacher bit"
    if re.search(r"apply_|GameState|STATE_FIELDS|map_bits|hp|ammo", delta):
        return True, "delta names teacher state or apply_* "
    return False, "teacher_delta does not name a teacher field or apply_* function"


def audit_proposal(
    p: dict[str, Any], *, compare: Path | None = None, cap: int | None = None
) -> dict[str, Any]:
    baseline = load_baseline(compare, cap=cap)
    logs = _live_logs()
    tick_body = _tick_body()
    pipe = _pipeline_text()
    blob = _blob(p)
    est_n = int(p.get("estimated_new_neurons") or 0)
    est_e = int(p.get("estimated_new_edges") or 0)
    headroom = int(baseline["cap"]) - int(baseline["n_neurons"]) - est_n
    extras_declared = (REPO / "config" / "scale_extra_units.json").is_file()
    fly = bool(FLY_RE.search(blob) or (baseline["n_neurons"] + est_n >= FLIES_BUDGET))
    fly_refused = bool(fly and not extras_declared)

    observables = _observables(p, tick_body)
    actionable = [o for o in observables if o.get("player_actionable")]
    already_live = any(
        "already in tick" in str(o.get("before") or "") or str(o.get("after") or "").startswith("already walks")
        for o in observables
    )
    named_ok, named_reason = _named_job_ok(p)
    spec_ok, spec_reason = _teacher_specifiable(p, tick_body)
    risks = _parity_risks(p, logs)
    alts = _parse_alternatives(p)
    legal_alts = [a for a in alts if a["legal"] and a["neurons"] is not None]
    cheaper = None
    if legal_alts:
        cheaper = min(legal_alts, key=lambda a: int(a["neurons"]))
        if cheaper["neurons"] >= est_n:
            cheaper = {**cheaper, "reason": "not cheaper than the proposal"}
        else:
            cheaper = {**cheaper, "reason": f"{cheaper['neurons']} < {est_n}"}
    illegal_impl = bool(re.search(r"overlay|fakes engine", blob, re.I)) and est_n == 0 and not spec_ok
    waste_text = bool(WASTE_RE.search(blob))
    analog = bool(ANALOG_RE.search(blob))
    settle_drop = bool(SETTLE_DROP_RE.search(blob))
    host_cosmetic = bool(HOST_COSMETIC_RE.search(blob)) and not spec_ok
    tag = _ablation_tag(p)
    isolation_note = (
        "zeroing "
        + (tag or "the new cluster")
        + " must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape"
    )
    if tag in EXISTING_MODULES:
        isolation_note = f"zeroing {tag} would also kill the existing {tag} job; isolation shape would change"

    # scores
    obs_score = 1.0 if actionable and not already_live else (0.25 if actionable and already_live else 0.0)
    if waste_text and not actionable:
        obs_score = 0.0
    job_score = 1.0 if named_ok else (0.4 if str(p.get("claimed_job") or "").strip() else 0.0)
    live_green = bool(logs["ray"].get("all_match")) and bool(logs["tape"].get("all_match"))
    high_risk = [r for r in risks if r["live_green"] is False]
    listed_ok = all(r["listed"] for r in risks if "held_fwd" in r["tape"] or r["tape"] in ("ray_parity", "door"))
    if settle_drop and not bool(logs["settle"].get("match")):
        parity_score = 0.0
    elif analog:
        parity_score = 0.0
    elif not live_green:
        parity_score = 0.0
    elif high_risk:
        parity_score = 0.4
    elif any("held_fwd" in r["tape"] for r in risks):
        parity_score = 0.7 if listed_ok else 0.4
    else:
        parity_score = 1.0 if listed_ok or not risks else 0.8

    cheaper_wins = bool(
        cheaper
        and cheaper.get("neurons") is not None
        and int(cheaper["neurons"]) < est_n
        and "not cheaper" not in str(cheaper.get("reason") or "")
    )
    if illegal_impl:
        cost_score = 0.0
    elif cheaper_wins:
        cost_score = 0.5
    else:
        cost_score = 1.0

    if fly_refused:
        cap_score = 0.0
    elif est_n <= 0 and waste_text:
        cap_score = 0.0
    elif headroom >= 0 and est_n > 0:
        cap_score = 1.0
    elif headroom < 0 and named_ok:
        cap_score = 0.5
    elif est_n == 0 and spec_ok and actionable:
        cap_score = 1.0
    else:
        cap_score = 0.0

    if analog or fly_refused or host_cosmetic or (waste_text and not actionable):
        spec_score = 0.0
    elif spec_ok:
        spec_score = 1.0
    else:
        spec_score = 0.3

    parts = {
        "observable": obs_score,
        "named_job_ablation": job_score,
        "parity": parity_score,
        "cost": cost_score,
        "cap_named": cap_score,
        "spec_not_waste": spec_score,
    }
    score = sum(SCORE_WEIGHTS[k] * parts[k] for k in SCORE_WEIGHTS)

    gates: list[str] = []
    reasons: list[str] = []
    if fly_refused:
        gates.append("doom.scale_166k")
        reasons.append("Fly-scale 166,700 is refused until extra units have a named job.")
    if analog:
        gates.append("doom.demo_path")
        reasons.append("Analog tau belongs in bake-off, not the digital demo stitch.")
    if illegal_impl or (host_cosmetic and est_n == 0 and not spec_ok):
        gates.append("doom.demo_path")
        reasons.append("Host overlay that fakes engine work is banned on the demo path.")
    if settle_drop and not bool(logs["settle"].get("match")):
        gates.append("doom.settle_floor")
        reasons.append("SETTLE 24 failed the 32-tick held-fwd tape; 29 is the floor.")
    if headroom < 0:
        cap_law = "doom.v2_cap" if int(baseline["cap"]) == V2_NEURON_CAP else "doom.v1_cap"
        gates.append(cap_law)
        reasons.append(
            f"Estimated {est_n} neurons plus baseline {baseline['n_neurons']} exceeds cap {baseline['cap']} (headroom {headroom})."
        )
    if not named_ok:
        gates.append("doom.named_job")
        reasons.append(named_reason)
    if not spec_ok:
        gates.append("doom.teacher_specifiable")
        reasons.append(spec_reason)
    if waste_text and not actionable:
        gates.append("doom.host_cosmetics")
        reasons.append("Text matches a waste pattern and there is no player-actionable observable.")
    if not live_green:
        gates.append("doom.tick_tape" if not logs["tape"].get("all_match") else "doom.ray_parity")
        reasons.append("Live parity logs are not all_match; do not spend neurons on a red stitch.")

    if fly_refused or analog or illegal_impl or (settle_drop and not bool(logs["settle"].get("match"))):
        verdict = VERDICT_LAW
    elif (not actionable) or (waste_text and not actionable) or score < 0.50 or already_live:
        verdict = VERDICT_WASTE
        if already_live:
            reasons.append("Teacher tick already implements this observable.")
        if not actionable:
            reasons.append("No player-actionable observable: turn, fire, door, or flee has nothing new to do.")
    elif headroom < 0 and score >= 0.60:
        verdict = VERDICT_CAP
        reasons.append("Job is real; shrink to leftover units or mux an existing ALU.")
    elif score >= 0.75 and headroom >= 0:
        verdict = VERDICT_ACCEPT
        reasons.append("Named job, teacher-specifiable, under cap, cheaper legal alt does not dominate.")
    elif score >= 0.60:
        verdict = VERDICT_CAP
        reasons.append("Acceptable QoL with a cheaper alt or tight headroom.")
    else:
        verdict = VERDICT_WASTE
        reasons.append(f"Score {score:.2f} is below 0.60.")

    if cheaper and cheaper.get("neurons") is not None and int(cheaper["neurons"]) < est_n:
        reasons.append(
            f"Cheaper legal alternative: {cheaper['text']} ({cheaper['neurons']} neurons)."
        )
    reasons.append(named_reason)
    reasons.append(spec_reason)
    reasons.append(isolation_note)

    n_act = len(actionable)
    cost_per = (float(est_n) / n_act) if n_act else None
    bakeoff = bool(tag and tag in ACC_GATE) or analog or bool(re.search(r"\brate\b|\bpopulation\b|\bwta\b", blob, re.I) and "new encoding" in blob.lower())
    if tag and tag not in EXISTING_MODULES and not analog:
        bakeoff = False

    payload = {
        "proposal": {
            "name": p.get("name"),
            "claimed_job": p.get("claimed_job"),
            "claimed_qol": p.get("claimed_qol"),
            "path": p.get("_path"),
        },
        "baseline_neurons": baseline["n_neurons"],
        "baseline_edges": baseline["n_edges"],
        "cap": int(baseline["cap"]),
        "cap_law": "doom.v2_cap" if int(baseline["cap"]) == V2_NEURON_CAP else "doom.v1_cap",
        "estimated_new_neurons": est_n,
        "estimated_new_edges": est_e,
        "headroom": headroom,
        "fly_scale_refused": fly_refused,
        "named_job_ok": {"ok": named_ok, "reason": named_reason, "ablation_target": tag},
        "teacher_specifiable": {"ok": spec_ok, "reason": spec_reason},
        "observable_deltas": observables,
        "parity_risk": risks,
        "ablation_contract": isolation_note,
        "cost_per_observable": cost_per,
        "cheaper_alternative": cheaper,
        "bakeoff_need": bakeoff,
        "score": round(score, 4),
        "score_parts": {k: round(v, 4) for k, v in parts.items()},
        "score_weights": SCORE_WEIGHTS,
        "verdict": verdict,
        "reasons": reasons,
        "gates_failed": gates,
        "live_logs": {
            "ray_parity": bool(logs["ray"].get("all_match")),
            "tick_tape": bool(logs["tape"].get("all_match")),
            "latch_held_key_dies": bool(logs["ablate"].get("latch_held_key_dies")),
            "settle_24": logs["settle"].get("match"),
        },
        "pipeline_mentions_enemy2_alu": "en_dx" in pipe and "ex2" in pipe,
    }
    return payload


def verdict_of(report: dict[str, Any]) -> str:
    return str(report.get("verdict") or VERDICT_WASTE)


def render_md(report: dict[str, Any]) -> str:
    name = (report.get("proposal") or {}).get("name") or "proposal"
    lines = [
        f"# QoL audit: {name}",
        "",
        f"Verdict: {report['verdict']} (score {report['score']:.2f})",
        "",
        f"Baseline: {report['baseline_neurons']:,} neurons, {report['baseline_edges']:,} edges, cap {int(report.get('cap') or V1_NEURON_CAP):,}.",
        f"Ask: {report['estimated_new_neurons']:,} neurons, {report['estimated_new_edges']:,} edges. Headroom after spend: {report['headroom']:,}.",
        "",
        "## Score",
        "",
    ]
    for key, w in SCORE_WEIGHTS.items():
        part = (report.get("score_parts") or {}).get(key, 0)
        lines.append(f"- {key}: {part:.2f} x {w:.2f} = {part * w:.2f}")
    lines.extend(["", "## Observables", ""])
    for row in report.get("observable_deltas") or []:
        act = "actionable" if row.get("player_actionable") else "not actionable"
        lines.append(f"- {row['channel']}: {row['before']} becomes {row['after']} ({act})")
    lines.extend(["", "## Parity risk", ""])
    for row in report.get("parity_risk") or []:
        live = row.get("live_green")
        lines.append(f"- {row['tape']}: {row['why']} (live green: {live}, listed: {row.get('listed')})")
    lines.extend(["", "## Reasons", ""])
    for r in report.get("reasons") or []:
        lines.append(f"- {r}")
    gates = report.get("gates_failed") or []
    lines.extend(["", "## Gates failed", ""])
    if gates:
        for g in gates:
            lines.append(f"- {g}")
    else:
        lines.append("- none")
    alt = report.get("cheaper_alternative")
    lines.extend(["", "## Cheaper alternative", ""])
    if alt:
        lines.append(f"- {alt.get('text')} ({alt.get('neurons')} neurons). {alt.get('reason')}")
    else:
        lines.append("- none parsed")
    lines.extend(
        [
            "",
            f"Ablation contract: {report.get('ablation_contract')}",
            f"Teacher specifiable: {(report.get('teacher_specifiable') or {}).get('reason')}",
            f"Bake-off need: {report.get('bakeoff_need')}",
            f"Fly-scale refused: {report.get('fly_scale_refused')}",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def render_screen(report: dict[str, Any]) -> str:
    name = (report.get("proposal") or {}).get("name") or "proposal"
    alt = report.get("cheaper_alternative") or {}
    act = sum(1 for o in report.get("observable_deltas") or [] if o.get("player_actionable"))
    gates = ", ".join(report.get("gates_failed") or []) or "none"
    return "\n".join(
        [
            f"QoL {name}",
            f"verdict {report['verdict']}  score {report['score']:.2f}",
            f"baseline {report['baseline_neurons']:,}  ask {report['estimated_new_neurons']:,}  headroom {report['headroom']:,}",
            f"actionable deltas {act}  cost/observable {report.get('cost_per_observable')}",
            f"cheaper {alt.get('text', 'none')} ({alt.get('neurons')})",
            f"gates {gates}",
            f"job {(report.get('named_job_ok') or {}).get('reason')}",
        ]
    )


def write_report(report: dict[str, Any], dest_dir: Path | None = None) -> tuple[Path, Path]:
    dest = dest_dir or (LOGS / "qol_audit")
    dest.mkdir(parents=True, exist_ok=True)
    name = str((report.get("proposal") or {}).get("name") or "proposal")
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    js = dest / f"{safe}.json"
    md = dest / f"{safe}.md"
    js.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md.write_text(render_md(report), encoding="utf-8")
    return js, md


def scan_dir(
    folder: Path, *, compare: Path | None = None, cap: int | None = None
) -> list[dict[str, Any]]:
    paths = sorted(list(folder.glob("*.yaml")) + list(folder.glob("*.yml")) + list(folder.glob("*.json")))
    reports = []
    for path in paths:
        reports.append(audit_proposal(load_proposal(path), compare=compare, cap=cap))
    return reports
