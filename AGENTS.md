# Agent notes: snn_doom

MIT. GraphForge pin in `doomforge/`: teacher suite before bake-off; module i frozen before train i+1; demo host surface; 166k refused until RAY distances lock. Verify-before-done is the evidence backend and the finish gate, not the process. Call `doomforge.gate.require_*` on those edges. Do not bake-off before teacher tests. Do not train FRAME_READOUT before a RAY freeze. Do not start a 166k init to see.

The teacher is the spec. The demo path must not call `teacher.tick`, `cast_ray`, `apply_move`, `apply_enemy`, or `paint_frame`. Host: inject bits, step LIF, decode pixels, display, log.

Do not train a ViZDoom agent. Do not preserve fly cell types as features. MaleCNS is Phase 4 sparse init only. Do not grow to 166,700 neurons until `logs/ray_parity.json` `all_match` is true, ablations isolate, and LATCH dies on a held key. Do not spend leftover neurons unless `scripts/audit_qol.py` verdict is ACCEPT or ACCEPT_WITH_CAP.

Do not write a stitch over `V1_NEURON_CAP`. Call `doomforge.gate.require_v1_cap` from stitch export, not from the auditor. Do not drop SETTLE below the green floor in `logs/settle_probe.json`. Call `doomforge.gate.require_settle_floor` from CLOCK/SETTLE writers. Audit may emit ACCEPT_WITH_CAP. Stitch may not. Keep `apply_enemy2` out of `tick()` on v1. v1 is closed (7,973 LIF, cap 8,000). Do not edit `checkpoints/snn_doom_v1.json` to fit a walker. Walking e2 is v2: `tick_v2` calls `apply_enemy2`, cap 12,000, `doom.v2_cap`, stitch `checkpoints/snn_doom_v2.json` (9,077 LIF), `docs/v2.md`. `--play` stays v1. `--machine v2` fail-closes if that stitch or `logs/tick_tape_v2.json` is missing. Phase 4 is 166,700 and is not v2.

Verify:

```
python3 ~/agent_laws_verify_before_done/vbd_gate.py check --app-root . --claim-done
PYTHONPATH=~/graphforge/src:. .venv/bin/python doomforge/scripts/sanity_doomforge.py
```
