#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.const import STEPS_PER_TICK, V1_NEURON_CAP
from snn_doom.modules.pipeline import build_doom_snn


def main() -> None:
    m = build_doom_snn()
    out = ROOT / "checkpoints" / "snn_doom_v1.json"
    payload = {
        "n_neurons": m.net.n,
        "n_edges": int(m.net.src.size),
        "steps_per_tick": STEPS_PER_TICK,
        "cap": V1_NEURON_CAP,
        "modules": sorted(set(m.net.module)),
        "counts": {name: m.net.module.count(name) for name in sorted(set(m.net.module))},
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
