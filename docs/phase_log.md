# Phase log

## Phase 0: teacher (2026-09-12)

Passed: 104-bit packed state, 8x8 map, integer ray march, turn/move/enemy/collide, 16x16 framebuffer, deterministic `tick`, unit tests.

Failed: none in the teacher.

Next: encoding bake-off on 50-2000 neuron nets.

## Phase 1: encodings (2026-09-12)

Passed: dual-rail/bistable/oscillator win CLOCK, LATCH, REG, ALU, RAM, SEQUENCER. FRAME_READOUT fixed WTA/population/dual_rail at accuracy 1.0. Table: `docs/bakeoff.md`.

Failed: RAY_COLUMN isolated bake-off, all encodings under the 0.70 gate (winner `none`). Analog rate/population bags lost the digital roles.

Next: freeze digital priors; keep RAY as a stitched march, not a 200-neuron bag.

## Phase 2: module freeze (2026-09-12)

Passed: hand-wired dual-rail frozen for CLOCK, LATCH, REG, ALU, RAM, SEQUENCER. FRAME_READOUT frozen as population (tied with dual_rail/wta). Analog 4-bit adder BPTT smoke ran (`train_analog`, 20 steps, loss 0.20) and was not selected.

Failed: RAY_COLUMN has no freeze (`none`).

Next: stitch with the frozen priors plus a shared ray unit.

## Phase 3: stitch (2026-09-12)

Passed: 7,217 LIF neurons, 38,722 edges, under the 8,000 cap. Pose/enemy match the teacher on idle, forward, and turn. Walls appear in the decoded frame. Ablation: zero CLOCK/LATCH/REG/ALU/SEQUENCER kills motion; zero RAY kills pixels and leaves pose; zero READOUT kills pixels and leaves pose; zero RAM changes the frame.

Failed: isolated RAY bake-off still `none`. Stitch distances now match the teacher on five poses (`logs/ray_parity.json` all_match). Miss was carry-chain starve at SETTLE=12 plus capture one one-hot late, not the angle table.

Next: readout freeze is a separate train edge. Do not start 166k because someone is curious.

## GraphForge pin (2026-09-12)

Four refuse laws in `doomforge/`: teacher_green, module_freeze, demo_path, scale_166k. VBD is evidence (`logs/teacher_green.json`, `logs/demo_surface.json`, `logs/ray_parity.json`, `logs/ablation.json`, `checkpoints/freeze_manifest.json`). Sanity: train_readout blocked, scale_166k blocked, bake-off and train_ray allowed, demo surface clean. LATCH held-key ablation now sets `latch_held_key_dies`.

## Phase 4: scale

Refused. `scripts/scale_166k.py` raises LawBlockedError until `logs/ray_parity.json` all_match, RAY freeze, ablations isolate, and LATCH dies on a held key.

## Phase 5: demo (2026-09-12)

Passed: `scripts/run_demo.py --frames 1` writes `logs/demo_frame.png` (~1.6 ticks/sec on this host). Host path does not call `tick`/`cast_ray`.
