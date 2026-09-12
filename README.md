# snn_doom

A fruit fly was mapped. People taught the map to play Doom...but this is not that. 

This repo doesn't showcase the fly brain playing doom. The fly brain *is* a Doom engine. Python injects four keys, steps the circuit, and decodes the color lines. That's it. Python does none of the heavy lifting, even thought it CAN run DOOM by itself. 

All the technical bits: [docs/methodology.md](docs/methodology.md).

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python scripts/run_teacher.py --steps 4
.venv/bin/python scripts/run_demo.py --frames 1
.venv/bin/python scripts/ablate.py
```

`--fwd` holds forward in the recorded path. CI does not open a window.


