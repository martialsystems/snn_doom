# Copyright (c) 2026 Martial Systems LLC
"""VBD writes these artifacts. GraphForge reads them fail-closed if missing."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
CKPT = REPO / "checkpoints"
MANIFEST = CKPT / "freeze_manifest.json"

ROLE_FILES = {
    "CLOCK": "clock.json",
    "BIT_LATCH": "bit_latch.json",
    "REGISTER_FILE": "register_file.json",
    "ADDER_COMPARE": "adder_compare.json",
    "RAM": "ram.json",
    "SEQUENCER": "sequencer.json",
    "RAY_COLUMN": "ray_column.json",
    "FRAME_READOUT": "frame_readout.json",
    "DOOR": "door.json",
}

BANNED_DEMO_TOKENS = (
    "teacher.tick",
    "cast_ray(",
    "apply_enemy",
    "apply_move",
    "paint_frame",
)

DEMO_SCAN_PATHS = (
    REPO / "scripts" / "run_demo.py",
    REPO / "src" / "snn_doom" / "play.py",
    *(REPO / "src" / "snn_doom" / "demo").rglob("*.py"),
    REPO / "src" / "snn_doom" / "modules" / "pipeline.py",
)

ISOLATE_MOTION = ("CLOCK", "BIT_LATCH", "REGISTER_FILE", "ADDER_COMPARE", "SEQUENCER")
ISOLATE_PIXELS = ("RAY_COLUMN", "FRAME_READOUT")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_frozen_payload(data: dict[str, Any]) -> bool:
    return bool(data.get("frozen")) and str(data.get("encoding") or "none") != "none"


def frozen_map() -> dict[str, bool]:
    out = {role: False for role in ROLE_FILES}
    manifest = {}
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8")).get("sha256") or {}
    for role, name in ROLE_FILES.items():
        path = CKPT / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not is_frozen_payload(data):
            continue
        digest = sha256_file(path)
        expected = manifest.get(role)
        if expected is None or expected == digest:
            out[role] = True
    return out


def write_freeze_manifest() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for role, name in ROLE_FILES.items():
        path = CKPT / name
        if path.is_file():
            hashes[role] = sha256_file(path)
    payload = {"sha256": hashes, "files": ROLE_FILES}
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return hashes


def teacher_green_live() -> bool:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_teacher.py", "-q"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    ok = r.returncode == 0
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "teacher_green.json").write_text(
        json.dumps({"ok": ok, "returncode": r.returncode}, indent=2) + "\n",
        encoding="utf-8",
    )
    return ok


def teacher_green() -> bool:
    path = LOGS / "teacher_green.json"
    if path.is_file():
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("ok") is True:
                return True
        except json.JSONDecodeError:
            return False
    return teacher_green_live()


def scan_demo_banned_hits() -> list[str]:
    hits: list[str] = []
    for path in DEMO_SCAN_PATHS:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in BANNED_DEMO_TOKENS:
            if tok in text:
                hits.append(f"{path.relative_to(REPO)}:{tok}")
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "demo_surface.json").write_text(
        json.dumps({"hits": hits, "ok": not hits}, indent=2) + "\n",
        encoding="utf-8",
    )
    return hits


def ray_parity() -> dict[str, Any]:
    path = LOGS / "ray_parity.json"
    if not path.is_file():
        return {"ok": False, "all_match": False, "missing": True}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def ray_distances_exact() -> bool:
    data = ray_parity()
    return bool(data.get("all_match")) and not data.get("missing")


def ablation_report() -> dict[str, Any]:
    path = LOGS / "ablation.json"
    if not path.is_file():
        return {"ok": False, "missing": True}
    return json.loads(path.read_text(encoding="utf-8"))


def ablations_isolate(report: dict[str, Any] | None = None) -> bool:
    report = report if report is not None else ablation_report()
    if report.get("missing"):
        return False
    rows = {r["module"]: r for r in report.get("rows") or []}
    for name in ISOLATE_MOTION:
        row = rows.get(name)
        if row is None:
            return False
        if not (row.get("state_delta") or {}).get("px"):
            return False
    for name in ISOLATE_PIXELS:
        row = rows.get(name)
        if row is None or int(row.get("pixel_l1") or 0) <= 0:
            return False
    ram = rows.get("RAM")
    if ram is None or int(ram.get("pixel_l1") or 0) <= 0:
        return False
    return True


def all_modules_frozen() -> bool:
    frozen = frozen_map()
    return bool(frozen) and all(frozen.get(role) for role in ROLE_FILES)


def multi_tick_parity() -> bool:
    path = LOGS / "tick_tape.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(data.get("all_match"))


_BANNED_EXTRA = (
    "budget leftover",
    "leftover from a fly",
    "fly budget",
    "malecns leftover",
)


def extra_units_declared() -> bool:
    path = REPO / "config" / "scale_extra_units.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    role = str(data.get("extra_units") or "").strip()
    if not role:
        return False
    low = role.lower()
    if any(b in low for b in _BANNED_EXTRA):
        return False
    return True


def v1_cap() -> int:
    from snn_doom.const import V1_NEURON_CAP

    return int(V1_NEURON_CAP)


def v1_neurons() -> int:
    path = CKPT / "snn_doom_v1.json"
    if not path.is_file():
        return -1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return -1
    try:
        return int(data.get("n_neurons"))
    except (TypeError, ValueError):
        return -1


def settle_live() -> int:
    from snn_doom.const import SETTLE_STEPS

    return int(SETTLE_STEPS)


def settle_floor() -> int:
    """Last green held-fwd SETTLE. Red probe keeps baseline. Missing probe cannot drop."""
    path = LOGS / "settle_probe.json"
    live = settle_live()
    if not path.is_file():
        return live
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return live
    if bool(data.get("match")):
        try:
            return int(data.get("candidate") or live)
        except (TypeError, ValueError):
            return live
    try:
        return int(data.get("baseline") or live)
    except (TypeError, ValueError):
        return live


def latch_held_key_dies(report: dict[str, Any] | None = None) -> bool:
    report = report if report is not None else ablation_report()
    if report.get("missing"):
        return False
    if "latch_held_key_dies" in report:
        return bool(report["latch_held_key_dies"])
    rows = {r["module"]: r for r in report.get("rows") or []}
    latch = rows.get("BIT_LATCH")
    if latch is None:
        return False
    return bool((latch.get("state_delta") or {}).get("px"))
