# snn_doom

A spiking net that **is** a tiny Doom engine: 8x8 map, player pose, 16 ray columns, one enemy, 16x16 framebuffer from spikes.

v1 machine: 7,217 LIF neurons, 38,722 edges, 2,940 LIF steps per game tick. Pose and the enemy match the teacher on idle, forward, and turn. Columns are neural; distances are not yet bit-exact (idle pixel L1 54). Isolated RAY bake-off is still `none`.

The teacher in `src/snn_doom/teacher/` is the spec (104-bit state, integer tick). The stitched LIF machine in `src/snn_doom/modules/pipeline.py` is the engine. Host Python injects four key bits, steps the net, decodes pixels by argmax on color lines, and draws.

Write-up: [docs/how_this_runs_doom.md](docs/how_this_runs_doom.md). Architecture: [docs/architecture.md](docs/architecture.md). Phase log: [docs/phase_log.md](docs/phase_log.md).

## Library

NumPy LIF for the running machine. PyTorch for analog-encoding training (surrogate gradient). Digital modules use `tau=0` on that same LIF.

## How to run

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python scripts/run_teacher.py --steps 4
.venv/bin/python scripts/run_bakeoff.py
.venv/bin/python scripts/train_all.py
.venv/bin/python scripts/run_demo.py --frames 1
.venv/bin/python scripts/ablate.py
```

Keys in the recorded demo path: `--fwd` sets the forward input bit. Interactive GUI is not the CI path.

## What neurons compute

| Module | Job |
|--------|-----|
| CLOCK | SETTLE-period ring |
| BIT_LATCH | held keys |
| REGISTER_FILE | pose and enemy bits |
| ADDER_COMPARE | turn, move, enemy step, ray step |
| RAM | 64 map cells |
| SEQUENCER | pose / column / march rings |
| RAY_COLUMN | one marching ray, 16 column dist latches |
| FRAME_READOUT | fixed 16x16x4 color lines |

## File table

| Path | Role |
|------|------|
| `src/snn_doom/teacher/` | spec tick |
| `src/snn_doom/snn/` | LIF, encodings, bake-off |
| `src/snn_doom/modules/` | frozen modules + stitch |
| `src/snn_doom/demo/` | host display |
| `docs/architecture.md` | state bits and graph |
| `logs/bakeoff.json` | encoding table |
| `checkpoints/` | frozen winners |
