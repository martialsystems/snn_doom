# Agent notes: snn_doom

MIT. No GraphForge pin unless the operator says yes to the named laws (phase order, module freeze, host-must-not-tick claim-ban, no 166k until ablations pass).

The teacher is the spec. The demo path must not call `teacher.tick`, `cast_ray`, `apply_move`, `apply_enemy`, or `paint_frame`. Host: inject bits, step LIF, decode pixels, display, log.

Do not train a ViZDoom agent. Do not preserve fly cell types as features. MaleCNS is Phase 4 sparse init only. Do not grow to 166,700 neurons until the tiny net matches the teacher and `logs/ablation.json` shows each module death.

Verify:

```
python3 ~/agent_laws_verify_before_done/vbd_gate.py check --app-root . --claim-done
```
