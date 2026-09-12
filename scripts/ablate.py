#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.state import pack_input

MODULES = (
    "CLOCK",
    "BIT_LATCH",
    "REGISTER_FILE",
    "ADDER_COMPARE",
    "RAM",
    "SEQUENCER",
    "RAY_COLUMN",
    "FRAME_READOUT",
)


def main() -> None:
    base = build_doom_snn()
    s0 = spawn()
    base.reset(s0)
    bits = pack_input(0, 0, 1, 0)
    pix0 = base.tick(bits)
    st0 = base.read_state()
    rows = []
    for name in MODULES:
        m = build_doom_snn()
        m.reset(s0)
        m.zero_module(name)
        pix = m.tick(bits)
        st = m.read_state()
        rows.append(
            {
                "module": name,
                "pixel_l1": int(abs(pix.astype(int) - pix0.astype(int)).sum()),
                "state_delta": {k: int(st[k] != st0[k]) for k in st0},
                "pixels_nonzero": int((pix != 0).sum()),
            }
        )
        print(name, rows[-1]["pixel_l1"], rows[-1]["state_delta"])
    out = ROOT / "logs" / "ablation.json"
    out.write_text(json.dumps({"baseline_state": st0, "rows": rows}, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
