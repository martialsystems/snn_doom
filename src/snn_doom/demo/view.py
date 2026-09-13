# Copyright (c) 2026 Martial Systems LLC
"""Host display: compose RAM, FRAME_READOUT, raster, HUD from decoded bits.

Host loop: inject key bits, step the SNN a fixed LIF budget, argmax pixels, draw.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from snn_doom.const import (
    CELL,
    COS,
    DOOR_IDX,
    DOOR_X,
    DOOR_Y,
    MAP_H,
    MAP_W,
    SIN,
    STEPS_PER_TICK,
)
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

COLOR_WALL = (40, 40, 40)
COLOR_FLOOR = (20, 20, 20)
COLOR_DOOR_CLOSED = (160, 110, 50)
COLOR_DOOR_OPEN = (40, 70, 80)
COLOR_PLAYER = (80, 200, 80)
COLOR_FACE = (200, 255, 180)
COLOR_E1 = (200, 80, 80)
COLOR_E2 = (220, 150, 40)

RASTER_MODULES = (
    "CLOCK",
    "BIT_LATCH",
    "REGISTER_FILE",
    "ADDER_COMPARE",
    "RAM",
    "DOOR",
    "SEQUENCER",
    "RAY_COLUMN",
    "FRAME_READOUT",
)

_MOVE = {
    "left": "left",
    "a": "left",
    "right": "right",
    "d": "right",
    "up": "up",
    "w": "up",
    "down": "down",
    "s": "down",
}
_FIRE = frozenset({" ", "space", "f", "control", "ctrl"})
_DOOR = frozenset({"e", "q"})
QUIT_KEYS = frozenset({"escape", "esc"})
CANON_KEYS = frozenset({"left", "right", "up", "down", "space", "e"})


def frame_rgb(pixels: np.ndarray, scale: int = 16) -> np.ndarray:
    rgb = PALETTE[pixels.clip(0, 3)]
    return np.repeat(np.repeat(rgb, scale, axis=0), scale, axis=1)


def _stamp(img: np.ndarray, wx: int, wy: int, color: tuple[int, int, int], scale: int, r: int) -> None:
    h, w = img.shape[:2]
    x = int(wx * scale / CELL)
    y = int(wy * scale / CELL)
    img[max(0, y - r) : min(h, y + r + 1), max(0, x - r) : min(w, x + r + 1)] = color


def map_rgb(
    map_bits: int,
    px: int,
    py: int,
    ex: int,
    ey: int,
    *,
    ang: int = 0,
    enemy_alive: int = 1,
    ex2: int = 0,
    ey2: int = 0,
    enemy2_alive: int = 0,
    scale: int = 16,
) -> np.ndarray:
    rows = rows_of(map_bits)
    img = np.zeros((MAP_H * scale, MAP_W * scale, 3), dtype=np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = COLOR_WALL if ch == "#" else COLOR_FLOOR
            img[y * scale : (y + 1) * scale, x * scale : (x + 1) * scale] = color
    y0, x0 = DOOR_Y * scale, DOOR_X * scale
    door_color = COLOR_DOOR_CLOSED if (map_bits >> DOOR_IDX) & 1 else COLOR_DOOR_OPEN
    img[y0 : y0 + scale, x0 : x0 + scale] = door_color
    if enemy2_alive:
        _stamp(img, ex2, ey2, COLOR_E2, scale, r=2)
    if enemy_alive:
        _stamp(img, ex, ey, COLOR_E1, scale, r=2)
    _stamp(img, px, py, COLOR_PLAYER, scale, r=2)
    face_x = px + COS[ang % len(COS)]
    face_y = py + SIN[ang % len(SIN)]
    _stamp(img, face_x, face_y, COLOR_FACE, scale, r=1)
    return img


def raster_image(raster: dict[str, np.ndarray], width: int = 320) -> np.ndarray:
    rows = []
    for name in RASTER_MODULES:
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


def ingest_key(key: str | None) -> tuple[str, ...]:
    """Map a matplotlib or tty key name to tokens stored in the pressed set."""
    if not key:
        return ()
    k = str(key).lower()
    if k.startswith("ctrl+") or k.startswith("control+"):
        return ("space",)
    if k in _MOVE:
        return (_MOVE[k],)
    if k in _FIRE:
        return ("space",)
    if k in _DOOR:
        return ("e",)
    if k in QUIT_KEYS:
        return ("escape",)
    return (k,)


def keys_to_bits(pressed: set[str]) -> int:
    return pack_input(
        int("left" in pressed or "a" in pressed),
        int("right" in pressed or "d" in pressed),
        int("up" in pressed or "w" in pressed),
        int("down" in pressed or "s" in pressed),
        int("space" in pressed or "ctrl" in pressed or "f" in pressed),
        int("e" in pressed or "q" in pressed),
    )


def hud_text(
    st: dict[str, int],
    *,
    tps: float,
    n_neurons: int,
    spikes_per_step: float,
    pressed: set[str],
    door: int = 0,
    shot: int = 0,
    hitscan: int = 0,
    lif_step: int = 0,
    lif_total: int = 0,
) -> str:
    keys = ",".join(sorted(pressed)) if pressed else "(none)"
    lif = f"LIF {lif_step}/{lif_total}\n" if lif_total else ""
    return (
        f"snn_doom console\n"
        f"{lif}ticks/sec {tps:.3f}\n"
        f"neurons {n_neurons}\n"
        f"spikes/step {spikes_per_step:.1f}\n"
        f"px {st['px']} py {st['py']} ang {st['ang']}\n"
        f"e1 {st['ex']},{st['ey']} alive {st['enemy_alive']}\n"
        f"e2 {st['ex2']},{st['ey2']} alive {st['enemy2_alive']}\n"
        f"ammo {st['ammo']} hit {st['player_hit']} door {door} shot {shot} hs {hitscan}\n"
        f"keys {keys}\n"
        f"WASD/arrows move  space/f fire  e/q door  Esc quit\n"
        f"this is the ALU / this is RAM"
    )


def map_from_state(map_bits: int, st: dict[str, int], scale: int = 16) -> np.ndarray:
    return map_rgb(
        map_bits,
        st["px"],
        st["py"],
        st["ex"],
        st["ey"],
        ang=st["ang"],
        enemy_alive=st["enemy_alive"],
        ex2=st["ex2"],
        ey2=st["ey2"],
        enemy2_alive=st["enemy2_alive"],
        scale=scale,
    )


def make_console_figure():
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.patch.set_facecolor("#111111")
    try:
        fig.canvas.manager.set_window_title("snn_doom console")
    except (AttributeError, TypeError):
        pass
    titles = (
        "this is RAM (map) + REGISTER_FILE (pose)",
        "this is FRAME_READOUT (decoded pixels)",
        "spike raster by module",
        "",
    )
    for ax, title in zip(axes.flat, titles):
        ax.set_facecolor("#111111")
        ax.set_title(title, color="#c8d0c8", fontsize=10, fontfamily="monospace")
        ax.axis("off")
        for spine in ax.spines.values():
            spine.set_color("#333333")
    hud = axes[1, 1].text(
        0.05,
        0.95,
        "",
        family="monospace",
        fontsize=10,
        color="#c8d0c8",
        transform=axes[1, 1].transAxes,
        va="top",
    )
    fig.tight_layout()
    return fig, {
        "ax_map": axes[0, 0],
        "ax_frame": axes[0, 1],
        "ax_ras": axes[1, 0],
        "ax_hud": axes[1, 1],
        "hud": hud,
        "im_map": None,
        "im_frame": None,
        "im_ras": None,
    }


def update_console_figure(
    fig,
    artists: dict[str, Any],
    *,
    pixels: np.ndarray,
    map_bits: int,
    st: dict[str, int],
    raster: dict[str, np.ndarray],
    text: str,
) -> None:
    rgb_frame = frame_rgb(pixels)
    rgb_map = map_from_state(map_bits, st)
    rgb_ras = raster_image(raster)
    if artists["im_frame"] is None:
        artists["im_map"] = artists["ax_map"].imshow(rgb_map)
        artists["im_frame"] = artists["ax_frame"].imshow(rgb_frame)
        artists["im_ras"] = artists["ax_ras"].imshow(rgb_ras)
    else:
        artists["im_map"].set_data(rgb_map)
        artists["im_frame"].set_data(rgb_frame)
        artists["im_ras"].set_data(rgb_ras)
    artists["hud"].set_text(text)
    fig.canvas.draw_idle()


def host_frame(
    machine: DoomSNN,
    bits: int,
    on_chunk=None,
    chunk: int = 512,
) -> dict[str, Any]:
    """One game tick on the host path: inject, step LIF, decode."""
    pixels = machine.tick(bits, on_chunk=on_chunk, chunk=chunk)
    st = machine.read_state()
    return {
        "pixels": pixels,
        "state": st,
        "map_bits": machine.read_map_bits(),
        "raster": machine.raster(),
        "shot": machine.read_shot(),
        "door": machine.read_door(),
        "hitscan": machine.read_hitscan(),
        "spikes_per_step": machine.last_spikes_per_step,
        "n_neurons": machine.net.n,
        "steps_per_tick": machine.steps_per_tick,
    }


def run_demo(
    frames: int = 1,
    out: Path | None = None,
    inputs: list[int] | None = None,
    machine: DoomSNN | None = None,
) -> dict:
    """Headless host: recorded bits, no window. Live play is run_console."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if frames <= 0:
        raise ValueError("run_demo is headless; pass frames>=1 or use run_console")
    m = machine or build_doom_snn()
    state0 = spawn()
    m.reset(state0)
    n_run = frames
    t0 = time.perf_counter()
    last = {
        "pixels": m.decode_pixels(),
        "state": m.read_state(),
        "map_bits": m.read_map_bits(),
        "raster": m.raster(),
        "shot": 0,
        "door": m.read_door(),
        "hitscan": 0,
        "spikes_per_step": 0.0,
        "n_neurons": m.net.n,
        "steps_per_tick": m.steps_per_tick,
    }
    history_inputs = inputs or []
    for i in range(n_run):
        bits = history_inputs[i] if i < len(history_inputs) else 0
        last = host_frame(m, bits)
    elapsed = time.perf_counter() - t0
    tps = n_run / max(elapsed, 1e-6)
    st = last["state"]
    fig, artists = make_console_figure()
    update_console_figure(
        fig,
        artists,
        pixels=last["pixels"],
        map_bits=last["map_bits"],
        st=st,
        raster=last["raster"],
        text=hud_text(
            st,
            tps=tps,
            n_neurons=last["n_neurons"],
            spikes_per_step=last["spikes_per_step"],
            pressed=set(),
            door=last["door"],
            shot=last["shot"],
            hitscan=last["hitscan"],
            lif_step=STEPS_PER_TICK,
            lif_total=STEPS_PER_TICK,
        ),
    )
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=100)
    plt.close(fig)
    return {
        "ticks_per_sec": tps,
        "n_neurons": last["n_neurons"],
        "spikes_per_step": last["spikes_per_step"],
        "state": st,
        "pixels": last["pixels"],
        "map_bits": last["map_bits"],
        "door": last["door"],
        "shot": last["shot"],
        "hitscan": last["hitscan"],
    }
