# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "web" / "pack"


def test_browser_lif_pose_matches_python_tick0() -> None:
    if shutil.which("node") is None:
        return
    assert (PACK / "net.bin").is_file()
    assert (PACK / "net.json").is_file()
    meta = json.loads((PACK / "net.json").read_text(encoding="utf-8"))
    assert meta["n"] == 7973
    assert meta["steps_per_tick"] == 7598
    out = subprocess.check_output(["node", str(REPO / "web" / "compare.mjs")], cwd=REPO, text=True)
    data = json.loads(out)
    assert data["poseOk"] is True
    assert data["js"]["px"] == data["py"]["px"]
    assert data["js"]["hp"] == 3
