#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Headless 16x18 play GIF plus a TTY still. No window."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.const import CENTER_COL
from snn_doom.demo.console import render_tty
from snn_doom.demo.tapes import save_run
from snn_doom.demo.view import frame_rgb, host_frame
from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.state import pack_input


def main() -> None:
    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    m = build_doom_snn()
    m.reset(spawn())
    bits = pack_input(0, 0, 1, 0)
    frames = []
    poses = []
    tape = []
    n = 32
    last = host_frame(m, 0, raster=False)
    rgb0 = frame_rgb(last["pixels"], scale=32, heading_col=CENTER_COL, dist=m.read_dists())
    frames.append(rgb0)
    poses.append(dict(last["state"]))
    tape.append(0)
    for _ in range(n - 1):
        last = host_frame(m, bits, raster=False)
        frames.append(frame_rgb(last["pixels"], scale=32, heading_col=CENTER_COL, dist=m.read_dists()))
        poses.append(dict(last["state"]))
        tape.append(bits)
    save_run(tape, poses, ROOT / "logs" / "runs" / "held_fwd.bits")
    gif = docs / "play.gif"
    try:
        from PIL import Image

        imgs = [Image.fromarray(f) for f in frames]
        # 32 frames * 625 ms ~ 20 s
        imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=625, loop=0)
    except ImportError:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.imsave(docs / "play.gif", frames[-1])
    tty = render_tty(
        last["pixels"],
        last["state"],
        last["map_bits"],
        pressed={"up"},
        tps=0.0,
        n_neurons=last["n_neurons"],
        spikes_per_step=last["spikes_per_step"],
        door=last["door"],
        shot=last["shot"],
        hitscan=last["hitscan"],
    )
    (docs / "tty.txt").write_text(tty + "\n", encoding="utf-8")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 10), facecolor="#111111")
    ax.set_facecolor("#111111")
    ax.axis("off")
    ax.text(0.02, 0.98, tty, family="monospace", fontsize=8, color="#c8d0c8", va="top", transform=ax.transAxes)
    fig.savefig(docs / "tty.png", dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(json_dumps({"gif": str(gif), "frames": len(frames), "n_neurons": last["n_neurons"]}))


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj)


if __name__ == "__main__":
    main()
