# Methodology (2026-09-12)

v1 is a discrete LIF circuit that implements a toy Doom tick. The joke is in the README. This file is the machine.

## Contract

Teacher in `src/snn_doom/teacher/` is the spec: 127-bit state, integer march, two enemies, 16×18 paint.
Stitched net in `src/snn_doom/modules/pipeline.py` is the engine.
Host injects 6 key bits, runs 7,598 LIF updates, argmaxes 16×18×4 color lines, draws, logs.
Same discrete update everywhere:

```
v ← τ v + I
s ← [v ≥ θ]
v ← v (1 − s)
```

Digital gates use τ = 0. Analog BPTT experiments use τ = 0.8 in PyTorch (`snn_doom.snn.train_analog`) and are not on the demo path.

Running machine: 7,973 LIF neurons. v1 budget cap is 8,000. Museum label (Phase 3 stitch, not the running machine): 7,217 LIF neurons. Sprite latches were added after that stitch so multi-tick enemy columns hold. Readout paints the teacher sprite blob, not the whole wall slab. Fire is four extra cells. HP is a 2-bit register (contact decrements). Door is a 2-step `we_ram` pulse on cell (4,5) after last march. VIEW is 16×18. Second sprite is a stationary enemy at (2,2). Ammo is a 3-bit register. Pickup at (3,6) fills it. SETTLE is 29.

Host vs neuron split: [how_this_runs_doom.md](how_this_runs_doom.md). Bit layout and graph: [architecture.md](architecture.md).

## Current results

| Thing | Status |
|-------|--------|
| Pose vs teacher (idle / forward / turn) | match |
| Enemy step vs teacher | match |
| Walls in the decoded frame | yes |
| 16 column distances bit-exact | yes (five poses in `logs/ray_parity.json`) |
| VIEW | 16×18 paint; same 16-column march |
| Second sprite | stationary enemy (2,2); heading hitscan only |
| Ammo | 3-bit; fire consumes; 0 cannot kill |
| Center-column hitscan | heading ray sprite bit; teacher and net match |
| 32-tick held-fwd tape | pose, dists, hitscan, frames (`logs/tick_tape.json`) |
| Fire | fifth bit AND heading sprite; spawn miss, posed kill |
| Held-fire corridor | 32 ticks fwd+fire from spawn: no shot, heading sprite 0 |
| Death | 2-bit HP; contact decrements; HP 0 sets sticky `player_hit` |
| Pickup | cell (3,6) fills ammo to 7 |
| Play maps | `corridor`, `arena`, `door` (RAM init only) |
| Isolated RAY bake-off winner | none; stitch freeze is dual-rail after parity |
| Host calling `teacher.tick` / `cast_ray` in the demo path | forbidden, tested |
| SETTLE | 29; isolated 127+1 fails at 23; held-fwd chase fails at 28; SETTLE 24 held-fwd still fails (`logs/settle_probe.json`) |
| Door | cell (4,5); sixth bit toggles occupancy after paint |
| 166k scale-up | refused until extra units have a named job |

Ablations (`logs/ablation.json`): zero CLOCK, LATCH, REG, ALU, or SEQUENCER and motion dies. Zero RAY or READOUT and pixels die. Zero RAM and the frame changes. LATCH ablation is silent if no key is held.

## State (127 bits)

| Field | Bits | Offset |
|-------|-----:|-------:|
| map | 64 | 0 |
| px, py | 8, 8 | 64, 72 |
| ang | 6 | 80 |
| ex, ey | 8, 8 | 86, 94 |
| enemy_alive | 1 | 102 |
| player_hit | 1 | 103 |
| ex2, ey2 | 8, 8 | 104, 112 |
| enemy2_alive | 1 | 120 |
| ammo | 3 | 121 |
| hp | 2 | 124 |
| pickup_alive | 1 | 126 |

World: 8×8 cells, 16 subcells/cell (4.4 fixed point). Angle: 64 ticks = 360°. Map bit 1 is wall. Frame: 16×18, 2-bit color {sky, floor, wall, enemy}. Rays: 16 columns, angles ang-8 to ang+7, march 8 units/step, max 15. Height: 18 - dist.

Inputs per LIF step: turn_left, turn_right, fwd, back, fire, door.

## Modules

| Module | Job | Notes |
|--------|-----|-------|
| CLOCK | SETTLE-period ring | a 6-step kick filled a packet; that was a bug once |
| BIT_LATCH | held keys | ablation must be tested with a held key |
| REGISTER_FILE | pose + enemy bits | |
| ADDER_COMPARE | turn, move, enemy step, ray step | 8-bit add/compare |
| RAM | 64 map cells | extra read ports |
| SEQUENCER | pose / column / march rings | 5 / 16 / 15 plus death chain and door window |
| DOOR | `we_ram` pulse on cell (4,5) | after last march, before next pose |
| RAY_COLUMN | one marching ray, 16 dist latches | frozen dual-rail after five-pose 16-int match |
| FRAME_READOUT | 16×18×4 color lines | frozen wta after five-pose argmax match |

Encodings that won the digital bake-off for CLOCK / LATCH / REG / ALU / RAM / SEQ: dual-rail, bistable, oscillator. RAY_COLUMN missed the 0.70 gate in every encoding. Shared LUT tagging once marked move COS ROM as RAY, so RAY ablation killed pose. Fixed. Do not do that again.

Full table: [bakeoff.md](bakeoff.md), `logs/bakeoff.json`.

## Phase rules

Stage 0 teacher tests pass before bake-off.
A module freezes before the next one trains. RAY freeze is `checkpoints/ray_column.json` after the 16-int fixture matches.
Demo path must not call `teacher.tick` or `cast_ray`.
166,700 neurons are refused until column distances match the teacher march and ablations stay green.

Those four are GraphForge laws in `doomforge/`. Pytest and the JSON under `logs/` are evidence the graph reads. Do not report done on a scale-up that skips RAY lock. Phase log: [phase_log.md](phase_log.md).

Do not pin idle pixel L1 as a law. Pin the 16 column distances. L1 can still move after RAY is exact.

## Library split

**NumPy LIF**, sparse CSR (`I = W @ s`): the machine that runs. Optional Numba kernel, same discrete equation.
**PyTorch** analog BPTT: encoding experiments only.
One discrete equation. Two autodiff stories. Do not mix them in `run_demo.py`.

## Commands

```bash
.venv/bin/python scripts/run_bakeoff.py
.venv/bin/python scripts/train_all.py
.venv/bin/python scripts/run_demo.py --frames 1 --fwd
.venv/bin/python -m snn_doom.play
.venv/bin/python scripts/run_demo.py --play --lab
.venv/bin/python scripts/ablate.py
```

## Layout

| Path | Role |
|------|------|
| `src/snn_doom/teacher/` | integer spec tick |
| `src/snn_doom/snn/` | LIF, encodings, bake-off, analog train |
| `src/snn_doom/modules/` | frozen modules + stitch |
| `src/snn_doom/demo/` | host display: headless PNG, `--play` window, `--tty` |
| `checkpoints/` | frozen winners |
| `logs/bakeoff.json` | encoding table |
| `logs/ablation.json` | lesion results |
| `docs/architecture.md` | bits and graph |
| `docs/how_this_runs_doom.md` | host vs neuron split |
| `docs/phase_log.md` | what passed |
| `docs/bakeoff.md` | encoding bake-off |
| `vbd.runtime.json` | verify-before-done checks |
| `doomforge/` | GraphForge pin and the four refuse laws |

## v1

7,973 LIF units. SETTLE 29 (7,598 LIF steps/tick). 16×18 VIEW, stationary second sprite at (2,2), 3-bit ammo, 2-bit HP, pickup at (3,6). Teacher-matched pose, enemy, distances, frames, and center-column hitscan on the five-pose tape plus four extra ticks, and on 32 held-fwd ticks. Fire: spawn miss, posed kill. Held-fire corridor does not leak a kill. Contact decrements HP; HP 0 is sticky dead. Door: closed blocks, toggle opens a pass, toggle closes a block (`logs/tick_tape.json`). SETTLE 24 stays off until that held-fwd tape is green. Every named module has a freeze hash in `checkpoints/freeze_manifest.json`. Pixel L1 stays a metric. `scale_166k.py` still dies unless extra units have a named job. That file does not exist.
