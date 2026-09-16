#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from doomforge.gate import require_settle_floor, require_v1_cap, require_v2_cap
from snn_doom.const import STEPS_PER_TICK, V1_NEURON_CAP, V2_NEURON_CAP
from snn_doom.modules.pipeline import build_doom_snn


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--machine", choices=("v1", "v2"), default="v1")
    args = p.parse_args()
    walk_e2 = args.machine == "v2"
    m = build_doom_snn(walk_e2=walk_e2)
    require_settle_floor(intent="export")
    if walk_e2:
        require_v2_cap(n_neurons=m.net.n, intent="export")
        out = ROOT / "checkpoints" / "snn_doom_v2.json"
        cap = V2_NEURON_CAP
    else:
        require_v1_cap(n_neurons=m.net.n, intent="export")
        out = ROOT / "checkpoints" / "snn_doom_v1.json"
        cap = V1_NEURON_CAP
    payload = {
        "n_neurons": m.net.n,
        "n_edges": int(m.net.src.size),
        "steps_per_tick": STEPS_PER_TICK,
        "cap": cap,
        "machine": args.machine,
        "modules": sorted(set(m.net.module)),
        "counts": {name: m.net.module.count(name) for name in sorted(set(m.net.module))},
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
