# Copyright (c) 2026 Martial Systems LLC
"""Host-side clicks. Hide the tick rate. Not the engine."""
from __future__ import annotations

import math
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

_CACHE: dict[str, Path] = {}


def _tone(path: Path, freq: float, ms: int, vol: float = 0.25, decay: bool = True) -> None:
    sr = 22050
    n = max(int(sr * ms / 1000), 1)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            env = math.exp(-8.0 * t) if decay else 1.0
            s = int(max(-1.0, min(1.0, vol * env * math.sin(2 * math.pi * freq * t))) * 32767)
            frames += struct.pack("<h", s)
        w.writeframes(bytes(frames))


def _noise(path: Path, ms: int, vol: float = 0.2) -> None:
    sr = 22050
    n = max(int(sr * ms / 1000), 1)
    seed = 12345
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
            noise = (seed / 0x7FFFFFFF) * 2.0 - 1.0
            env = math.exp(-12.0 * i / sr)
            s = int(max(-1.0, min(1.0, vol * env * noise)) * 32767)
            frames += struct.pack("<h", s)
        w.writeframes(bytes(frames))


def _ensure() -> dict[str, Path]:
    if _CACHE:
        return _CACHE
    d = Path(tempfile.gettempdir()) / "snn_doom_sfx"
    d.mkdir(parents=True, exist_ok=True)
    fire = d / "fire.wav"
    wall = d / "wall.wav"
    kill = d / "kill.wav"
    door = d / "door.wav"
    if not fire.is_file():
        _tone(fire, 880, 40, vol=0.3)
    if not wall.is_file():
        _noise(wall, 50, vol=0.25)
    if not kill.is_file():
        _tone(kill, 1320, 80, vol=0.28)
    if not door.is_file():
        _tone(door, 220, 70, vol=0.22, decay=True)
    _CACHE.update(fire=fire, wall=wall, kill=kill, door=door)
    return _CACHE


def play(name: str) -> None:
    paths = _ensure()
    path = paths.get(name)
    if path is None:
        return
    cmd = ["afplay", str(path)] if sys.platform == "darwin" else ["aplay", "-q", str(path)]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return
