# Copyright (c) 2026 Martial Systems LLC
"""Playable host console: inject keys, step LIF, decode pixels, blit.

Windowed matplotlib is --play. Terminal is --tty. CI does not import this for a window.
"""
from __future__ import annotations

import os
import select
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from snn_doom.const import CENTER_COL, DOOR_X, DOOR_Y, FRAME_H, N_COLS, STEPS_PER_TICK
from snn_doom.demo.radar import facing_char
from snn_doom.demo.audio import play as play_sfx
from snn_doom.demo.latch import InputLatch
from snn_doom.demo.round import ROUND_TICKS, RoundState
from snn_doom.demo.tapes import load_ghost, save_run
from snn_doom.demo.view import (
    CANON_KEYS,
    PALETTE,
    QUIT_KEYS,
    host_frame,
    hud_text,
    ingest_key,
    keys_to_bits,
    make_console_figure,
    make_play_figure,
    update_console_figure,
)
from snn_doom.modules.pipeline import DoomSNN, build_doom_snn
from snn_doom.teacher.maps import MAPS, rows_of, spawn


def render_tty(
    pixels: np.ndarray,
    st: dict[str, int],
    map_bits: int,
    *,
    pressed: set[str],
    tps: float,
    n_neurons: int,
    spikes_per_step: float,
    door: int = 0,
    shot: int = 0,
    hitscan: int = 0,
    color: bool = False,
    lif_step: int = 0,
    lif_total: int = 0,
) -> str:
    """Text console of the decoded frame plus RAM map. No second renderer."""
    lines: list[str] = ["snn_doom console  inject / LIF / decode"]
    h = int(pixels.shape[0]) if pixels.size else FRAME_H
    w = int(pixels.shape[1]) if pixels.size else N_COLS
    glyphs = ".#W@"
    for r in range(h):
        row = []
        for c in range(w):
            idx = int(pixels[r, c]) if pixels.size else 0
            idx = max(0, min(3, idx))
            if color:
                rgb = PALETTE[idx]
                row.append(f"\x1b[38;2;{int(rgb[0])};{int(rgb[1])};{int(rgb[2])}m██\x1b[0m")
            else:
                row.append(glyphs[idx])
        lines.append("".join(row))
    lines.append("")
    pcx, pcy = st["px"] >> 4, st["py"] >> 4
    e1x, e1y = st["ex"] >> 4, st["ey"] >> 4
    e2x, e2y = st["ex2"] >> 4, st["ey2"] >> 4

    grid = [list(row) for row in rows_of(map_bits)]
    if 0 <= DOOR_Y < len(grid) and 0 <= DOOR_X < len(grid[0]):
        grid[DOOR_Y][DOOR_X] = "D"
    if st["enemy2_alive"] and 0 <= e2y < len(grid) and 0 <= e2x < len(grid[0]):
        grid[e2y][e2x] = "2"
    if st["enemy_alive"] and 0 <= e1y < len(grid) and 0 <= e1x < len(grid[0]):
        grid[e1y][e1x] = "1"
    if 0 <= pcy < len(grid) and 0 <= pcx < len(grid[0]):
        grid[pcy][pcx] = "P"
        face = facing_char(int(st.get("ang") or 0))
        fx, fy = pcx, pcy
        if face == ">":
            fx += 1
        elif face == "<":
            fx -= 1
        elif face == "v":
            fy += 1
        else:
            fy -= 1
        if 0 <= fy < len(grid) and 0 <= fx < len(grid[0]) and grid[fy][fx] in {".", "#"}:
            grid[fy][fx] = face
    lines.extend("".join(row) for row in grid)
    lines.append("")
    lines.append(
        hud_text(
            st,
            tps=tps,
            n_neurons=n_neurons,
            spikes_per_step=spikes_per_step,
            pressed=pressed,
            door=door,
            shot=shot,
            hitscan=hitscan,
            lif_step=lif_step,
            lif_total=lif_total,
        )
    )
    return "\n".join(lines)


def _silence_mpl_keys() -> None:
    """Drop matplotlib's default keymap. q/s/f are door, back, and fire here."""
    import matplotlib as mpl

    for key in (
        "keymap.quit",
        "keymap.quit_all",
        "keymap.save",
        "keymap.fullscreen",
        "keymap.home",
        "keymap.back",
        "keymap.forward",
        "keymap.pan",
        "keymap.zoom",
        "keymap.grid",
        "keymap.yscale",
        "keymap.xscale",
    ):
        if key in mpl.rcParams:
            mpl.rcParams[key] = []


def _bind_keys(fig, latch: InputLatch, stop: dict[str, bool]) -> None:
    def on_press(event) -> None:
        tokens = ingest_key(getattr(event, "key", None))
        if any(t in QUIT_KEYS for t in tokens):
            stop["q"] = True
            return
        if "c" in tokens:
            latch.held.clear()
            return
        latch.press(tokens)

    def on_release(event) -> None:
        latch.release(ingest_key(getattr(event, "key", None)))

    fig.canvas.mpl_connect("key_press_event", on_press)
    fig.canvas.mpl_connect("key_release_event", on_release)
    fig.canvas.mpl_connect("close_event", lambda _evt: stop.__setitem__("q", True))


def _save_last(out: Path | None, fig) -> None:
    if out is None or fig is None:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100)


def run_console(
    *,
    machine: DoomSNN | None = None,
    ticks: int = 0,
    display: bool = True,
    tty: bool = False,
    pressed: set[str] | None = None,
    out: Path | None = None,
    lab: bool = False,
    scale: int = 32,
    map_name: str = "default",
    door_closed: bool = False,
    fwd_lock: bool = False,
    record: bool = True,
    ghost: list[int] | Path | None = None,
    round_limit: int = ROUND_TICKS,
    sound: bool = True,
    radar: bool = True,
) -> dict[str, Any]:
    """Live host. ticks=0 runs until quit when a surface is open; headless defaults to 1."""
    if tty:
        display = False
    if ticks <= 0 and not display and not tty:
        ticks = 1
    m = machine or build_doom_snn()
    rows = MAPS.get(map_name, MAPS["default"])
    state0 = spawn(rows=rows, door_closed=1 if (door_closed or map_name == "door") else 0)
    m.reset(state0)
    latch = InputLatch(fwd_lock=fwd_lock)
    if pressed:
        latch.held |= set(pressed)
    stop = {"q": False}
    fig = None
    artists: dict[str, Any] | None = None
    color_tty = bool(tty and sys.stdout.isatty())
    rnd = RoundState(limit=round_limit if round_limit else 10**9)
    tape: list[int] = []
    poses: list[dict[str, int]] = []
    ghost_poses: list[dict[str, int]] = []
    if ghost:
        if isinstance(ghost, (str, Path)):
            _, ghost_poses = load_ghost(Path(ghost))
        else:
            from snn_doom.demo.tapes import replay_poses

            ghost_poses = replay_poses(list(ghost))

    if display:
        import matplotlib.pyplot as plt

        _silence_mpl_keys()
        fig, artists = make_console_figure() if lab else make_play_figure(scale=scale, radar=radar)
        _bind_keys(fig, latch, stop)
        plt.show(block=False)

    t0 = time.perf_counter()
    n = 0
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
    if artists is not None and fig is not None:
        update_console_figure(
            fig,
            artists,
            pixels=last["pixels"],
            map_bits=last["map_bits"],
            st=last["state"],
            raster=last["raster"],
            text=hud_text(
                last["state"],
                tps=0.0,
                n_neurons=last["n_neurons"],
                spikes_per_step=0.0,
                pressed=latch.held,
                door=last["door"],
                lif_total=STEPS_PER_TICK,
            ),
            door=last["door"],
        )
        fig.canvas.flush_events()

    fd = None
    old_term = None
    if tty and sys.stdin.isatty():
        import termios
        import tty as tty_mod

        fd = sys.stdin.fileno()
        old_term = termios.tcgetattr(fd)
        tty_mod.setcbreak(fd)

    try:
        while True:
            if ticks > 0 and n >= ticks:
                break
            if stop["q"]:
                break
            if display and fig is not None:
                import matplotlib.pyplot as plt

                if not plt.fignum_exists(fig.number):
                    break
                fig.canvas.flush_events()
            if tty and fd is not None:
                if not _poll_tty(latch, stop, fd):
                    break
            bits, flash, shown = latch.consume()
            tape.append(bits)
            prev = last["state"]
            ghost_st = ghost_poses[n] if ghost_poses and n < len(ghost_poses) else None
            if sound:
                if flash.get("muzzle"):
                    play_sfx("fire")
                if flash.get("door"):
                    play_sfx("door")
            if artists is not None and fig is not None and flash:
                update_console_figure(
                    fig,
                    artists,
                    pixels=last["pixels"],
                    map_bits=last["map_bits"],
                    st=last["state"],
                    raster=last["raster"] if lab else {},
                    text=hud_text(
                        last["state"],
                        tps=n / max(time.perf_counter() - t0, 1e-6),
                        n_neurons=last["n_neurons"],
                        spikes_per_step=last["spikes_per_step"],
                        pressed=shown,
                        door=last["door"],
                        shot=last["shot"],
                        hitscan=last["hitscan"],
                        lif_total=STEPS_PER_TICK,
                    ),
                    flash=flash,
                    dist=m.read_dists(),
                    heading_col=CENTER_COL,
                    ghost=ghost_st,
                    door=last["door"],
                )
                fig.canvas.flush_events()
            last = host_frame(m, bits, raster=lab)
            last["state"]["score"] = rnd.score
            poses.append(dict(last["state"]))
            n += 1
            if sound:
                if last["shot"]:
                    play_sfx("kill")
                moved = last["state"]["px"] != prev["px"] or last["state"]["py"] != prev["py"]
                if (bits & 12) in (4, 8) and not moved:
                    play_sfx("wall")
            outcome = rnd.observe(last["state"])
            elapsed = time.perf_counter() - t0
            tps = n / max(elapsed, 1e-6)
            text = hud_text(
                last["state"],
                tps=tps,
                n_neurons=last["n_neurons"],
                spikes_per_step=last["spikes_per_step"],
                pressed=shown,
                door=last["door"],
                shot=last["shot"],
                hitscan=last["hitscan"],
                lif_step=last["steps_per_tick"],
                lif_total=last["steps_per_tick"],
            )
            if outcome != "play":
                text += f"\n{outcome.upper()}  score {rnd.score}"
            if artists is not None and fig is not None:
                dists = m.read_dists()
                update_console_figure(
                    fig,
                    artists,
                    pixels=last["pixels"],
                    map_bits=last["map_bits"],
                    st=last["state"],
                    raster=last["raster"] if lab else {},
                    text=text,
                    flash=None,
                    dist=dists,
                    heading_col=CENTER_COL,
                    ghost=ghost_st,
                    door=last["door"],
                )
                fig.canvas.flush_events()
            if tty:
                body = render_tty(
                    last["pixels"],
                    last["state"],
                    last["map_bits"],
                    pressed=shown,
                    tps=tps,
                    n_neurons=last["n_neurons"],
                    spikes_per_step=last["spikes_per_step"],
                    door=last["door"],
                    shot=last["shot"],
                    hitscan=last["hitscan"],
                    color=color_tty,
                    lif_step=last["steps_per_tick"],
                    lif_total=last["steps_per_tick"],
                )
                if color_tty:
                    sys.stdout.write("\x1b[2J\x1b[H")
                sys.stdout.write(body + "\n")
                sys.stdout.flush()
            if outcome != "play":
                break
    finally:
        if fd is not None and old_term is not None:
            import termios

            termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
        _save_last(out, fig)
        if fig is not None:
            import matplotlib.pyplot as plt

            plt.close(fig)
        if record and tape:
            save_run(tape, poses)

    elapsed = time.perf_counter() - t0
    tps = max(n, 1) / max(elapsed, 1e-6)
    return {
        "ticks_per_sec": tps,
        "n_neurons": last["n_neurons"],
        "spikes_per_step": last["spikes_per_step"],
        "state": last["state"],
        "pixels": last["pixels"],
        "map_bits": last["map_bits"],
        "door": last["door"],
        "shot": last["shot"],
        "hitscan": last["hitscan"],
        "ticks": n,
        "score": rnd.score,
        "outcome": rnd.outcome,
        "tape": tape,
    }


def _poll_tty(latch: InputLatch, stop: dict[str, bool], fd: int) -> bool:
    while True:
        ready, _, _ = select.select([fd], [], [], 0)
        if not ready:
            return True
        ch = os.read(fd, 1).decode("utf-8", errors="ignore")
        if ch in ("\x1b", "Q"):
            # Esc or lone Q quits. Arrow keys arrive as Esc [ A etc.
            more, _, _ = select.select([fd], [], [], 0.01)
            if ch == "\x1b" and more:
                rest = os.read(fd, 2).decode("utf-8", errors="ignore")
                arrows = {"[A": "up", "[B": "down", "[C": "right", "[D": "left"}
                token = arrows.get(rest)
                if token:
                    for k in ("up", "down", "left", "right"):
                        latch.held.discard(k)
                    latch.press((token,))
                    continue
            stop["q"] = True
            return False
        if ch in ("x", "X"):
            latch.held.clear()
            continue
        tokens = ingest_key(ch)
        if any(t in QUIT_KEYS for t in tokens):
            stop["q"] = True
            return False
        if ch in ("w", "a", "s", "d"):
            for k in ("up", "down", "left", "right"):
                latch.held.discard(k)
        latch.press(tokens)
