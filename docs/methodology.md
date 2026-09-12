# Methodology (2026-09-12)

v1 is a discrete LIF circuit that implements a toy Doom tick. The joke is in the README. This file is the machine.

## Contract

Teacher in `src/snn_doom/teacher/` is the spec: 104-bit state, integer march, one enemy, 16×16 paint.
Stitched net in `src/snn_doom/modules/pipeline.py` is the engine.
Host injects 4 key bits, runs 2,940 LIF updates, argmaxes 16×16×4 color lines, draws, logs.
Same discrete update everywhere:

```
v ← τ v + I
s ← [v ≥ θ]
v ← v (1 − s)
```

Digital gates use τ = 0. Analog BPTT experiments use τ = 0.8 in PyTorch (`snn_doom.snn.train_analog`) and are not on the demo path.

Running machine: 7,217 LIF neurons, 38,722 edges. v1 budget cap is 8,000.

Host vs neuron split: [how_this_runs_doom.md](how_this_runs_doom.md). Bit layout and graph: [architecture.md](architecture.md).

## Current results

| Thing | Status |
|-------|--------|
| Pose vs teacher (idle / forward / turn) | match |
| Enemy step vs teacher | match |
| Walls in the decoded frame | yes |
| 16 column distances bit-exact | no (idle pixel L1 = 54) |
| Isolated RAY bake-off winner | none |
| Host calling `teacher.tick` / `cast_ray` in the demo path | forbidden, tested |
| 166k scale-up | refused until RAY locks |

Ablations (`logs/ablation.json`): zero CLOCK, LATCH, REG, ALU, or SEQUENCER and motion dies. Zero RAY or READOUT and pixels die. Zero RAM and the frame changes. LATCH ablation is silent if no key is held.

## State (104 bits)

| Field | Bits | Offset |
|-------|-----:|-------:|
| map | 64 | 0 |
| px, py | 8, 8 | 64, 72 |
| ang | 6 | 80 |
| ex, ey | 8, 8 | 86, 94 |
| enemy_alive | 1 | 102 |
| player_hit | 1 | 103 |

World: 8×8 cells, 16 subcells/cell (4.4 fixed point). Angle: 64 ticks = 360°. Map bit 1 is wall. Frame: 16×16, 2-bit color {sky, floor, wall, enemy}. Rays: 16 columns, angles ang-8 to ang+7, march 8 units/step, max 15. Height: 16 - dist.

Inputs per LIF step: turn_left, turn_right, fwd, back.

## Modules

| Module | Job | Notes |
|--------|-----|-------|
| CLOCK | SETTLE-period ring | a 6-step kick filled a packet; that was a bug once |
| BIT_LATCH | held keys | ablation must be tested with a held key |
| REGISTER_FILE | pose + enemy bits | |
| ADDER_COMPARE | turn, move, enemy step, ray step | 8-bit add/compare |
| RAM | 64 map cells | extra read ports |
| SEQUENCER | pose / column / march rings | 5 / 16 / 15 |
| RAY_COLUMN | one marching ray, 16 dist latches | not frozen; distances not bit-exact |
| FRAME_READOUT | 16×16×4 color lines | WTA / pop / dual-rail all hit 1.0 in bake-off |

Encodings that won the digital bake-off for CLOCK / LATCH / REG / ALU / RAM / SEQ: dual-rail, bistable, oscillator. RAY_COLUMN missed the 0.70 gate in every encoding. Shared LUT tagging once marked move COS ROM as RAY, so RAY ablation killed pose. Fixed. Do not do that again.

Full table: [bakeoff.md](bakeoff.md), `logs/bakeoff.json`.

## Phase rules

Stage 0 teacher tests pass before bake-off.
A module freezes before the next one trains. RAY has no freeze.
Demo path must not call `teacher.tick` or `cast_ray`.
166,700 neurons are refused until column distances match the teacher march and ablations stay green.

Those four are process laws. Pytest is evidence. Do not report done on a scale-up that skips RAY lock. Phase log: [phase_log.md](phase_log.md).

## Library split

**NumPy LIF**, sparse COO: the machine that runs.
**PyTorch** analog BPTT: encoding experiments only.
One discrete equation. Two autodiff stories. Do not mix them in `run_demo.py`.

## Commands

```bash
.venv/bin/python scripts/run_bakeoff.py
.venv/bin/python scripts/train_all.py
.venv/bin/python scripts/run_demo.py --frames 1 --fwd
.venv/bin/python scripts/ablate.py
```

## Layout

| Path | Role |
|------|------|
| `src/snn_doom/teacher/` | integer spec tick |
| `src/snn_doom/snn/` | LIF, encodings, bake-off, analog train |
| `src/snn_doom/modules/` | frozen modules + stitch |
| `src/snn_doom/demo/` | host display |
| `checkpoints/` | frozen winners |
| `logs/bakeoff.json` | encoding table |
| `logs/ablation.json` | lesion results |
| `docs/architecture.md` | bits and graph |
| `docs/how_this_runs_doom.md` | host vs neuron split |
| `docs/phase_log.md` | what passed |
| `docs/bakeoff.md` | encoding bake-off |
| `vbd.runtime.json` | verify-before-done checks |

## Next experiment

Train or repair the shared ray unit so the 16 column distances match the teacher march on idle, forward, turn, and one wall-graze. Re-run ablations with a held key. Then freeze RAY. Then talk about 166k.
