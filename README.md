# snn_doom

A fruit fly was mapped. People taught that map to play DOOM...but this is not that. This is *farrr* more cursed. 

This repo doesn't showcase the fly brain playing DOOM. The fly brain *is* a DOOM engine, each neuron is remapped with a sole function, to run DOOM. Python only injects four keys, steps the circuit, and decodes the color lines. That's it. It does none of the heavy lifting, even thought it CAN technically run DOOM by itself without a fly.

All the technical bits: [docs/methodology.md](docs/methodology.md).

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python scripts/run_teacher.py --steps 4
.venv/bin/python scripts/run_demo.py --frames 1
.venv/bin/python scripts/ablate.py
```

`--fwd` holds forward in the recorded path. CI does not open a window.


