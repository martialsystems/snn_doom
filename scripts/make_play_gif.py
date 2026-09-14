#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Headless FRAME_READOUT + HOST_RADAR GIF, HOST_DEAD GIF, TTY still. No window."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.const import CENTER_COL
from snn_doom.demo.console import render_tty
from snn_doom.demo.radar import radar_rgb
from snn_doom.demo.tapes import save_run
from snn_doom.demo.view import frame_rgb, host_frame
from snn_doom.modules.pipeline import build_doom_snn
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.state import pack_input


def _fonts():
    from PIL import ImageFont

    try:
        return (
            ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 16),
            ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 42),
            ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18),
        )
    except OSError:
        d = ImageFont.load_default()
        return d, d, d


def compose(view: np.ndarray, radar: np.ndarray, *, splash: bool = False) -> np.ndarray:
    from PIL import Image, ImageDraw

    title_h = 24
    vh, vw = int(view.shape[0]), int(view.shape[1])
    scale = max(vh // int(radar.shape[0]), 1)
    rad = np.repeat(np.repeat(radar, scale, axis=0), scale, axis=1)
    rh, rw = int(rad.shape[0]), int(rad.shape[1])
    canvas_h = max(vh, rh) + title_h
    canvas_w = vw + rw
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[title_h : title_h + vh, :vw] = view
    y0 = title_h + (max(vh, rh) - rh) // 2
    canvas[y0 : y0 + rh, vw : vw + rw] = rad
    img = Image.fromarray(canvas)
    draw = ImageDraw.Draw(img)
    small, big, mid = _fonts()
    draw.text((8, 4), "FRAME_READOUT", fill=(200, 208, 200), font=small)
    draw.text((vw + 8, 4), "HOST_RADAR", fill=(200, 208, 200), font=small)
    if splash:
        overlay = Image.new("RGB", img.size, (40, 0, 0))
        img = Image.blend(img, overlay, 0.55)
        draw = ImageDraw.Draw(img)
        cx, cy = img.size[0] // 2, img.size[1] // 2
        draw.rectangle((cx - 180, cy - 70, cx + 180, cy + 70), fill=(64, 0, 0), outline=(255, 180, 180))
        draw.text((cx, cy - 28), "YOU DIED", fill=(255, 232, 232), font=big, anchor="mm")
        draw.text((cx, cy + 28), "HOST_DEAD   R restart", fill=(224, 192, 192), font=mid, anchor="mm")
    return np.asarray(img)


def _save_gif(path: Path, frames: list[np.ndarray], duration: int | list[int]) -> None:
    from PIL import Image

    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=duration, loop=0, disposal=2)


def _panel(m, last: dict) -> np.ndarray:
    view = frame_rgb(last["pixels"], scale=32, heading_col=CENTER_COL, dist=m.read_dists())
    radar = radar_rgb(last["map_bits"], last["state"], door=last["door"])
    return compose(view, radar)


def main() -> None:
    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    m = build_doom_snn()
    m.reset(spawn())
    bits = pack_input(0, 0, 1, 0)
    frames = []
    poses = []
    tape = []
    n = 16
    last = host_frame(m, 0, raster=False)
    frames.append(_panel(m, last))
    poses.append(dict(last["state"]))
    tape.append(0)
    for _ in range(n - 1):
        last = host_frame(m, bits, raster=False)
        frames.append(_panel(m, last))
        poses.append(dict(last["state"]))
        tape.append(bits)
    save_run(tape, poses, ROOT / "logs" / "runs" / "held_fwd.bits")
    _save_gif(docs / "play.gif", frames, duration=280)

    m.reset(spawn(px=24, py=24, ex=24, ey=24, hp=1))
    alive = {
        "pixels": m.decode_pixels(),
        "state": m.read_state(),
        "map_bits": m.read_map_bits(),
        "door": m.read_door(),
    }
    dead_frames = [_panel(m, alive)]
    last = host_frame(m, 0, raster=False)
    body = compose(
        frame_rgb(last["pixels"], scale=32, heading_col=CENTER_COL, dist=m.read_dists()),
        radar_rgb(last["map_bits"], last["state"], door=last["door"]),
        splash=True,
    )
    dead_frames.append(body)
    _save_gif(docs / "dead.gif", dead_frames, duration=[400, 2200])

    tty = render_tty(
        last["pixels"],
        last["state"],
        last["map_bits"],
        pressed=set(),
        tps=0.0,
        n_neurons=last["n_neurons"],
        spikes_per_step=last["spikes_per_step"],
        door=last["door"],
        shot=last["shot"],
        hitscan=last["hitscan"],
        dead=True,
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
    print(
        json_dumps(
            {
                "play": str(docs / "play.gif"),
                "dead": str(docs / "dead.gif"),
                "play_frames": len(frames),
                "dead_frames": len(dead_frames),
                "n_neurons": last["n_neurons"],
            }
        )
    )


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj)


if __name__ == "__main__":
    main()
