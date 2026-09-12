# Copyright (c) 2026 Martial Systems LLC
"""Live view: map, decoded frame, per-module raster, ticks/sec.

Host loop: inject key bits, step the SNN a fixed LIF budget, argmax pixels, draw.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from snn_doom.const import MAP_H, MAP_W
from snn_doom.modules.pipeline import DoomSNN, build_doom_snn
from snn_doom.teacher.maps import rows_of, spawn
from snn_doom.teacher.state import pack_input

PALETTE = np.array(
    [
        [80, 140, 200],  # sky
        [90, 80, 60],  # floor
        [180, 180, 180],  # wall
        [200, 40, 40],  # enemy
    ],
    dtype=np.uint8,
)


def frame_rgb(pixels: np.ndarray, scale: int = 16) -> np.ndarray:
    rgb = PALETTE[pixels.clip(0, 3)]
    return np.repeat(np.repeat(rgb, scale, axis=0), scale, axis=1)


def map_rgb(state_map: int, px: int, py: int, ex: int, ey: int, scale: int = 16) -> np.ndarray:
    rows = rows_of(state_map)
    img = np.zeros((MAP_H * scale, MAP_W * scale, 3), dtype=np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = (40, 40, 40) if ch == "#" else (20, 20, 20)
            img[y * scale : (y + 1) * scale, x * scale : (x + 1) * scale] = color
    img[(py >> 4) * scale : (py >> 4) * scale + scale, (px >> 4) * scale : (px >> 4) * scale + scale] = (80, 200, 80)
    img[(ey >> 4) * scale : (ey >> 4) * scale + scale, (ex >> 4) * scale : (ex >> 4) * scale + scale] = (200, 80, 80)
    return img


def raster_image(raster: dict[str, np.ndarray], width: int = 320) -> np.ndarray:
    names = [
        "CLOCK",
        "BIT_LATCH",
        "REGISTER_FILE",
        "ADDER_COMPARE",
        "RAM",
        "SEQUENCER",
        "RAY_COLUMN",
        "FRAME_READOUT",
    ]
    rows = []
    for name in names:
        v = raster.get(name)
        if v is None or v.size == 0:
            band = np.zeros((12, width), dtype=np.uint8)
        else:
            x = (v[:width] * 255).astype(np.uint8)
            if x.size < width:
                x = np.pad(x, (0, width - x.size))
            band = np.repeat(x[None, :], 12, axis=0)
        rows.append(band)
    stacked = np.vstack(rows)
    return np.stack([stacked, stacked, stacked], axis=-1)


def keys_to_bits(pressed: set[str]) -> int:
    return pack_input(
        int("left" in pressed or "a" in pressed),
        int("right" in pressed or "d" in pressed),
        int("up" in pressed or "w" in pressed),
        int("down" in pressed or "s" in pressed),
        int("space" in pressed or "ctrl" in pressed or "f" in pressed),
    )


def run_demo(
    frames: int = 0,
    out: Path | None = None,
    inputs: list[int] | None = None,
    machine: DoomSNN | None = None,
) -> dict:
    """If frames>0, run headless and optionally save a PNG. frames=0 is interactive."""
    import matplotlib

    if frames > 0:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = machine or build_doom_snn()
    state0 = spawn()
    m.reset(state0)
    pressed: set[str] = set()
    n_run = frames if frames > 0 else 10**9
    t0 = time.perf_counter()
    last_pixels = m.decode_pixels()
    history_inputs = inputs or []
    for i in range(n_run):
        bits = history_inputs[i] if i < len(history_inputs) else (0 if frames > 0 else keys_to_bits(pressed))
        last_pixels = m.tick(bits)
        st = m.read_state()
        if frames > 0 and i + 1 >= frames:
            break
    elapsed = time.perf_counter() - t0
    tps = (min(n_run, max(frames, 1))) / max(elapsed, 1e-6)
    rgb_frame = frame_rgb(last_pixels)
    rgb_map = map_rgb(state0.map_bits, st["px"], st["py"], st["ex"], st["ey"])
    rgb_ras = raster_image(m.raster())
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    axes[0, 0].imshow(rgb_map)
    axes[0, 0].set_title("this is RAM (map) + REGISTER_FILE (pose)")
    axes[0, 0].axis("off")
    axes[0, 1].imshow(rgb_frame)
    axes[0, 1].set_title("this is FRAME_READOUT (decoded pixels)")
    axes[0, 1].axis("off")
    axes[1, 0].imshow(rgb_ras)
    axes[1, 0].set_title("spike raster by module")
    axes[1, 0].axis("off")
    axes[1, 1].axis("off")
    axes[1, 1].text(
        0.05,
        0.6,
        f"ticks/sec {tps:.3f}\nneurons {m.net.n}\nspikes/step {m.last_spikes_per_step:.1f}\n"
        f"px {st['px']} py {st['py']} ang {st['ang']}\nex {st['ex']} ey {st['ey']} hit {st['player_hit']}\n"
        f"this is the ALU / this is RAM",
        family="monospace",
        fontsize=10,
        transform=axes[1, 1].transAxes,
        va="top",
    )
    fig.tight_layout()
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=100)
    plt.close(fig)
    return {
        "ticks_per_sec": tps,
        "n_neurons": m.net.n,
        "spikes_per_step": m.last_spikes_per_step,
        "state": st,
        "pixels": last_pixels,
    }
