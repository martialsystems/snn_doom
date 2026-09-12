# snn_doom

A fruit fly was mapped. People taught the map to play Doom.

This repo skipped the fly and the playing. It is a box of leaky integrate-and-fire neurons that *is* a tiny Doom engine. The map sits in RAM cells. Pose and the one guy who keeps walking toward you sit in latches. A little marching ray is supposed to paint the corridor. Python injects four keys, steps the circuit, and decodes the color lines. If Python starts raycasting, the whole thing is a costume.

7,217 neurons. About 1.6 ticks a second. The walls come up, which is the part I still do not quite believe. Distances drink on the job: idle frame vs teacher is pixel L1 54. Pose and the enemy match. Every encoding we tried for the ray failed the 0.70 gate. 166,700 is the fly budget and a dare we have not earned.

Lesion CLOCK, the latch, the registers, the ALU, or the sequencer and it stops walking. Lesion the ray or the readout and the screen goes blank. Lesion RAM and the picture changes. The latch still looks innocent if you never hold a key, which is a coward's test.

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python scripts/run_teacher.py --steps 4
.venv/bin/python scripts/run_demo.py --frames 1
.venv/bin/python scripts/ablate.py
```

`--fwd` holds forward in the recorded path. CI does not open a window.

The machine, the encodings, and the rules about not scaling yet: [docs/methodology.md](docs/methodology.md).
