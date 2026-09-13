# Architecture (2026-09-12)

A tiny Doom-like engine as a synchronous LIF circuit. The teacher in Python is the distillation target. The stitched net is the engine.

## Library

PyTorch is the training library for analog encodings (surrogate-gradient BPTT). The running engine is a NumPy LIF with the same discrete-time equation:

```
v <- tau * v + I
s <- [v >= thresh]
v <- v * (1 - s)
```

Digital modules use `tau=0` (v=I, a McCulloch-Pitts gate on LIF hardware). Analog bake-off nets use `tau=0.8`. JAX is unused: one autodiff stack, and this house already pins torch on sibling products.

## State bits (124)

| Field | Width | Offset |
|-------|------:|-------:|
| map_bits | 64 | 0 |
| px | 8 | 64 |
| py | 8 | 72 |
| ang | 6 | 80 |
| ex | 8 | 86 |
| ey | 8 | 94 |
| enemy_alive | 1 | 102 |
| player_hit | 1 | 103 |
| ex2 | 8 | 104 |
| ey2 | 8 | 112 |
| enemy2_alive | 1 | 120 |
| ammo | 3 | 121 |

World is 8x8 cells, 16 subcells per cell (4.4 fixed point). Angle is 64 ticks of 5.625 degrees. Map bit=1 is wall. Sequencer and clock are network-internal, not packed state.

Input bits (host injects every LIF step of a game tick): turn_left, turn_right, fwd, back, fire, door.

## Teacher tick

1. Turn: ±2 angle units, cancel if both or neither.
2. Move: add `COS[ang]//2` (or minus if back). Stay if the destination cell is wall or out of world.
3. Enemy: e1, if alive, steps 2 units on x toward the player, else on y. Stay if wall. e2 is stationary at cell (2,2).
4. Collide: same cell as e1 or e2 sets `player_hit`, clears that enemy, and starts `DEATH_TICKS` freeze ticks (pose held, dead frame, then re-arm).
5. Ray: 16 columns, angles `ang-8 .. ang+7`. March 8 world units per step, up to 15. Record dist, side, sprite.
6. Paint: 16x18 pixels, 2-bit color (sky, floor, wall, enemy). Height = `18-dist`.
7. Fire: if ammo is greater than 0, consume one. Kill whoever the heading ray visited (e1 and/or e2). Sprite AND is the shot flag. Ammo 0 cannot kill.
8. Door: after paint, the sixth key toggles occupancy of cell (4,5) through `we_ram`. Next pose sees the new bit.

## Module graph

```
CLOCK (SETTLE=29 ring)
  -> SEQUENCER (pose ring 5, march ring 16, column ring 16, door window 1)
       -> BIT_LATCH (held keys, including door)
       -> REGISTER_FILE (px,py,ang,ex,ey,ex2,ey2,flags,ammo)
       -> ADDER_COMPARE (turn, move, enemy, ray step)
       -> RAM (64 map cells, extra read ports)
       -> DOOR (2-step we_ram pulse on cell (4,5) after last march)
       -> RAY_COLUMN (rx,ry,dx,dy, per-column dist)
       -> FRAME_READOUT (fixed 16x18x4 WTA)
```

Host: inject 6 key bits, step `STEPS_PER_TICK` LIF updates, argmax 4 color lines per pixel, draw, log.

## Encodings

Bake-off roles and encodings live in `src/snn_doom/snn/bakeoff.py`. Rubric:

- 0.35 accuracy
- 0.20 hold over extra time
- 0.15 accuracy under p=0.05 spike flips
- 0.15 neuron frugality vs 2000
- 0.15 spike frugality vs n

Accuracy gates: CLOCK 0.90, BIT_LATCH 0.95, REGISTER_FILE 0.90, ADDER_COMPARE 0.85, RAM 0.90, SEQUENCER 0.90, RAY_COLUMN 0.70, FRAME_READOUT 0.85.

Fly cell-type names are not features. MaleCNS is a Phase 4 sparse init, not v1 topology.

## Neuron budget

v1 cap: 8,000. Measured stitch (`checkpoints/snn_doom_v1.json`): 7,958 neurons, 41,779 edges, SETTLE 29, 7,598 LIF steps per tick. Fly-scale 166,700 stays refused until leftover units have a named job and column distances stay teacher-exact under ablation.

## Curriculum (stitch)

1. Static frame (keys=0)
2. Player turn/move
3. Enemy + collide
4. Full tick

## Ablation law

Zeroing a module's edges must kill that function: CLOCK stops the rings, RAM drops walls, ALU freezes pose, RAY blanks columns, READOUT drops wall pixels, DOOR leaves occupancy unflipped.
