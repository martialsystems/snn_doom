<p align="right">
  <a href="https://ko-fi.com/martialgames"><img src="https://img.shields.io/badge/Donate-Ko--fi-ff5e5b?style=flat-square&logo=ko-fi&logoColor=white" alt="Donate on Ko-fi" /></a>
</p>

# snn_doom

A fruit fly was mapped. People taught that map to play DOOM...but this is not that. This is *farrr* more cursed. 

This repo doesn't showcase the fly brain playing DOOM. The fly brain *is* a DOOM engine, each neuron is remapped with a sole function, to run DOOM. Python only injects six keys, steps the circuit, and decodes the color lines. That's it. It does none of the heavy lifting, even thought it CAN technically run DOOM by itself without a fly.

[Play online now](https://martialgames.net/snn-doom/)

The page steps the exported v1 LIF. `python -m snn_doom.play` is the same stitch locally.

## Research notes

- [Full Methodology](docs/methodology.md)
- [V1 - closed machine, 8,000 neurons](docs/v1.md)
- [v2 - walking e2, 12,000 neuron cap](docs/v2.md)
- [v2.32 - 32-column VIEW](docs/v2_32.md)

or you can download this git and test yourself.

## Play

*Note: Current playtest is v1 only. v2 is the walking-e2 16×18 machine (`--machine v2`). 32-col VIEW is `--machine v2_32`.*

```bash
python -m venv .venv && .venv/bin/pip install -e ".[play]"
.venv/bin/python -m snn_doom.play
# WASD / arrows    move
# space / f        fire
# e / q            door
# R                restart after YOU DIED
# Esc              quit
```

Same loop: `scripts/run_demo.py --play`.

What you should see: a chunky 16×18 first-person slab (FRAME_READOUT) and a top-down radar (HOST_RADAR) so you can tell where you are versus red and orange. Red chases. Orange is a statue at cell (2,2). Kill red and it comes back on a free cell that is not on your nose. The window does not close. Die (hp == 0) and you get HOST_DEAD: YOU DIED plus Restart. Esc is the other way out.

FRAME_READOUT plus HOST_RADAR:

![FRAME_READOUT plus HOST_RADAR](docs/play.gif)

YOU DIED:

![YOU DIED](docs/dead.gif)

TTY:

![tty](docs/tty.png)

Useful flags:

```text
--lab              spike raster
--fast             skip the raster
--scale 32         chunky pixels
--map corridor|arena|door
--tty              terminal view
--fwd              hold forward
--ghost logs/runs/held_fwd.bits
--no-radar         hide the map
--no-dead          old behavior: death closes the window
--no-waves         red stays dead; still does not quit
--wave-e2          also loop the orange body (v1: statue; v2: walker)
--machine v2       walking e2 stitch; fail-closes if the v2 tape or checkpoint is missing
--machine v2_32    32-col VIEW; fail-closes if that stitch or tape is missing
```

Hold-turn is 11.25° per tick (`TURN_STEP=2` on a 64-step circle). The host cannot spin you faster than that. Speeding it up is an ALU change, not a key repeat.

CI does not open a window.

## What this is

An 8×8 map. Sixteen rays. Eighteen rows of four colors: sky, floor, wall, sprite. One chasing enemy, one statue, 3-bit ammo, 2-bit HP, one door cell at (4,5), one ammo pack. Hitscan is the yellow center column. Fire is that column plus a fifth latched key, and you need ammo.

The teacher in `src/snn_doom/teacher/` is the spec. The stitched net in `src/snn_doom/modules/pipeline.py` is the engine. A tick is thousands of discrete LIF updates:

```text
v ← τv + I
s ← [v ≥ θ]
v ← v (1 − s)
```

Digital gates use τ = 0. That is a McCulloch-Pitts gate sitting on LIF hardware. Analog bake-off nets exist and are not on the demo path.

v1 budget is 8,000 neurons. The running stitch is 7,973. The leftover 27 cells do not buy a second chase ALU. Fly-scale 166,700 is refused until every extra unit has a named job and the 16 column distances stay teacher-exact under ablation.

How the host and the net split the tick: [docs/how_this_runs_doom.md](docs/how_this_runs_doom.md).

## What Python is allowed to do

Host:

- Inject six bits: turn left, turn right, forward, back, fire, door.
- Step the net `STEPS_PER_TICK` times.
- Argmax four color lines per pixel.
- Draw, log, overlay a radar, splash YOU DIED, respawn red on a free cell.

Host is not allowed to call `teacher.tick`, `cast_ray`, `apply_move`, `apply_enemy`, or `paint_frame` on the play path. Those functions are the spec the net has to match, not a hidden renderer.

Radar, death splash, and enemy waves are console. They cost zero neurons. The QoL auditor will mark them REJECT_WASTE if you file them as engine work. That is correct.

## What it is not

It is not ViZDoom. The net does not pick keys. You do, or a recorded bit tape does.

It is not 1993 Doom. No BSP, no sound engine in the stitch, no 320×200.

It is not "we mapped a fly and it learned to play." Cell types are not features. MaleCNS is a Phase 4 sparse init that is not allowed to start yet.

## Check the machine

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python scripts/run_teacher.py --steps 4
.venv/bin/python scripts/run_demo.py --frames 1
.venv/bin/python -m snn_doom.play
.venv/bin/python scripts/ablate.py
.venv/bin/python scripts/audit_qol.py --scan proposals/
```

Zero CLOCK, LATCH, REG, ALU, or SEQUENCER and motion dies. Zero RAY or READOUT and pixels die. Zero RAM and the frame changes. That is the point of the stitch.

[Fly Research Index](https://gist.github.com/martialsystems/12835f747d6360781f3cc7f91f243178)

## Methods card

Copied from `METHODS.yaml`.

| Field | Value |
|-------|-------|
| Object | remap / stitch |
| Status | Closed |
| Falsifier | teacher-exact pose fails or neuron count exceeds 8000 |
| n / seeds | 1 frozen play |
| Science lock | `889524b` |
| Pre-specified | false |

