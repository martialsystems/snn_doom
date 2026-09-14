# Phase log

## v1 closed / v2 spec (2026-09-14)

v1 is the museum machine: 7,973 LIF, cap 8,000, leftover 27, e2 statue, `--play` default. Do not restamp `checkpoints/snn_doom_v1.json` for a walker. v2 is a new teacher, cap 12,000 (`doom.v2_cap`), and a later stitch. First v2 sentence: `apply_enemy2` in `tick()`. Phase 4 remains 166,700 and is refused. Notes: [v1.md](v1.md), [v2.md](v2.md).

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

FRAME_READOUT frozen wta (`checkpoints/frame_readout.json`) after five-pose frames matched under argmax (`logs/frame_parity.json`, L1 0 as metric). RAY and READOUT ablations still split pixels vs pose. Idle LATCH stayed quiet. `--fwd` remains the LATCH witness.

Multi-tick tape (`logs/tick_tape.json`): five poses, then idle/fwd/turn/back. Sequencer re-arms pose at frame_end. Sprite latches hold enemy columns. `all_match` true. Scale law now also requires every module hashed, the tape, and a named extra-units job. Extra units undeclared. `scale_166k.py` still blocked.

Hitscan and held-fwd (2026-09-12): `CENTER_COL` is the heading ray. Teacher `hitscan` and `DoomSNN.read_hitscan` match on spawn-east (0) and facing the enemy (1). 32 held-fwd ticks match pose, 16 distances, hitscan, and frames. Step 6 was L1 2 with those three already matching: column 0 sprite at dist 10. Readout had been sprite AND wall. Teacher paints `is_enemy_row` (abs from mid ≤ max(1, half//2)). Isolated WTA readout now matches `paint_column`. v1 is 7,160 neurons.

Trigger (2026-09-12): fifth latched bit AND heading sprite. Kill writes `enemy_alive=0` on the last column's last march window. Tape is spawn+fire miss, then posed look-north+fire kill. Spawn held-fwd still never lights heading sprite. No extra march. Four extra cells (7,164). Extra units still undeclared.

Death and held-fire (2026-09-12): contact drops `enemy_alive` before the ray, holds pose for `DEATH_TICKS` freeze ticks, then re-arms `player_hit` on the last freeze. Held-fire is 32 ticks of fwd+fire down the spawn-east corridor: shot 0, heading sprite 0, then the posed look still kills. Headless `--frames` injects fire=0. Interactive space/ctrl/f is a host key. Scale still blocked. Extra units undeclared.

SPEED (2026-09-12): SETTLE 29. Isolated 127+1 is 0 at 23, exact at 24. 30+6 exact at 12. Stitched one-tick fwd is green at 24, but 32-tick held-fwd skips one enemy step at SETTLE 28 (px=64, snn ex=86 vs teacher 84). 29 is one notch above that break. CLOCK ring 29 (7,177 cells, minus 3 vs 32). STEPS_PER_TICK 7,569. RAY/READOUT freeze hashes unchanged. Scale still blocked: leftover cells have no named extra-units job.

Door (2026-09-12): cell (4,5), sixth host bit. Default map open so held-fwd still passes. Write is a 2-step `we_ram` pulse on that RAM bistable after last march (`door_busy` window, `clk[2]|clk[3]`). Pose re-arm is `door_end` on the door-window beat. Teacher tests first. Isolated RAM set-bit reads back at SETTLE 29. Toggle data is the opposite rail; pulse width 2 so it does not oscillate. Headless `--frames` injects door=0. Interactive e/q is host-only. Scale still blocked. Extra units undeclared.

VIEW, second sprite, ammo (2026-09-13): 16×18 paint (32 columns would miss the 8,000 cap). Stationary second enemy at cell (2,2), off spawn-east heading. Hitscan remains the heading column. Fire consumes 3-bit ammo; ammo 0 cannot kill; posed look with ammo 1 kills. Refused sizes, not live counts: 18 columns alone 7,631 before e2; 16×20 plus e2 compares 8,086 (over cap). SETTLE 29. Scale still blocked.

## GraphForge pin (2026-09-12)

Four refuse laws in `doomforge/`: teacher_green, module_freeze, demo_path, scale_166k. VBD is evidence (`logs/teacher_green.json`, `logs/demo_surface.json`, `logs/ray_parity.json`, `logs/ablation.json`, `checkpoints/freeze_manifest.json`). Sanity: train_readout blocked, scale_166k blocked, bake-off and train_ray allowed, demo surface clean. LATCH held-key ablation now sets `latch_held_key_dies`.

## Phase 4: scale

Refused. `scripts/scale_166k.py` raises LawBlockedError until `logs/ray_parity.json` all_match, RAY freeze, ablations isolate, and LATCH dies on a held key.

## GraphForge v1 cap and SETTLE floor (2026-09-14)

Pinned `doom.v1_cap` on stitch export (`scripts/export_checkpoint.py`) and `doom.settle_floor` on CLOCK/SETTLE writers. Live checkpoint 7,973 is under 8,000. SETTLE 29 is the green held-fwd floor; 24 stays refused while `logs/settle_probe.json` `match` is false. Auditor verdicts unchanged: walking e2 is still ACCEPT_WITH_CAP. `apply_enemy2` stays out of `tick()`.

## Phase 5: demo (2026-09-12)

Passed: `scripts/run_demo.py --frames 1` writes `logs/demo_frame.png` (~1.6 ticks/sec on this host). Host path does not call `tick`/`cast_ray`.

Live console (2026-09-13): `python -m snn_doom.play` is the front door. Default `--play` fullscreen VIEW, raster hidden unless `--lab`. Input latch one-shots fire/door. HUD flash on keydown. Host clicks for fire/wall/kill/door. Round: score is kills, survive 64 ticks or clear both sprites, HP 0 loses. `--map corridor|arena|door`. `--scale 32`. `--fast`. Tapes: `logs/runs/*.bits` plus ghost overlay. Held-fwd fixture map stays open so the 32-tick tape still passes; play spawn closes door (4,5).

HP / pickup (2026-09-13): contact decrements 2-bit HP instead of a 4-tick freeze. Pickup cell (3,6) fills ammo to 7. e2 stays a statue: a second chase ALU does not fit the 8,000 cap. SETTLE stays 29: the 32-tick held-fwd tape fails at 24 (`logs/settle_probe.json`). CSR Numba LIF on this host is about 6 to 8 game ticks/sec for the 7,973-unit net (was ~1.6 before vectorization). Target 10 to 20 is still open.
