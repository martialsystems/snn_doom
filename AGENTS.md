# Agent notes: snn_doom

MIT. GraphForge pin in `doomforge/`: teacher suite before bake-off; module i frozen before train i+1; demo host surface; 166k refused until RAY distances lock. Verify-before-done is the evidence backend and the finish gate, not the process. Call `doomforge.gate.require_*` on those edges. Do not bake-off before teacher tests. Do not train FRAME_READOUT before a RAY freeze. Do not start a 166k init to see.

The teacher is the spec. The demo path must not call `teacher.tick`, `cast_ray`, `apply_move`, `apply_enemy`, or `paint_frame`. Host: inject bits, step LIF, decode pixels, display, log.

Do not train a ViZDoom agent. Do not preserve fly cell types as features. MaleCNS is Phase 4 sparse init only. Do not grow to 166,700 neurons until `logs/ray_parity.json` `all_match` is true, ablations isolate, and LATCH dies on a held key. Do not spend leftover neurons unless `scripts/audit_qol.py` verdict is ACCEPT or ACCEPT_WITH_CAP.

Verify:

```
python3 ~/agent_laws_verify_before_done/vbd_gate.py check --app-root . --claim-done
PYTHONPATH=~/graphforge/src:. .venv/bin/python doomforge/scripts/sanity_doomforge.py
```
