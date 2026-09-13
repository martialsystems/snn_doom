# How this is running Doom (2026-09-12)

The network is the engine. A game tick is a fixed number of LIF steps. Pose, the enemy, the map lookup, the column march, and the pixel lines are neurons and weights.

The host does four things:

1. Inject six key bits as currents on input rails.
2. Call `net.step` `STEPS_PER_TICK` times.
3. Argmax four color lines per pixel.
4. Draw the 16x18 frame and log spikes/step.

`--play` is that loop with a window. `--tty` is the same loop in the terminal. Headless `--frames` writes a PNG and does not open a window.

Playing Doom would mean the net choosing keys to maximize a score in ViZDoom or a clone. This net does not choose keys. You, a recorded bit file, or the live console do. The net computes the next pose and the next frame from those bits.

A conventional renderer behind a neural readout would mean Python still doing DDA or blit, and neurons only decorating the pixels. The demo path does not call `tick`, `cast_ray`, `apply_move`, `apply_enemy`, or `paint_frame`. Those functions exist in `teacher/` as the spec the net is supposed to match.

v1 is an 8x8 map, 16 columns, 18-row paint, one chasing enemy and one stationary sprite, 3-bit ammo, 2-bit color. It is a Doom-like tick, not 1993 vanilla.
