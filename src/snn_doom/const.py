# Copyright (c) 2026 Martial Systems LLC
"""Shared geometry and bit-layout constants for the teacher and the SNN."""
from __future__ import annotations

import math
from typing import Final

MAP_W: Final[int] = 8
MAP_H: Final[int] = 8
MAP_CELLS: Final[int] = MAP_W * MAP_H
CELL: Final[int] = 16
WORLD: Final[int] = MAP_W * CELL
N_ANG: Final[int] = 64
N_COLS: Final[int] = 16
FRAME_H: Final[int] = 16
MAX_DIST: Final[int] = 15
RAY_SCALE: Final[int] = 8
MOVE_DIV: Final[int] = 2
TURN_STEP: Final[int] = 2
ENEMY_STEP: Final[int] = 2
FOV_HALF: Final[int] = 8
CENTER_COL: Final[int] = FOV_HALF  # column_angle(ang, CENTER_COL) == ang; hitscan uses this ray

COLOR_SKY: Final[int] = 0
COLOR_FLOOR: Final[int] = 1
COLOR_WALL: Final[int] = 2
COLOR_ENEMY: Final[int] = 3
N_COLORS: Final[int] = 4

IN_TURN_L: Final[int] = 0
IN_TURN_R: Final[int] = 1
IN_FWD: Final[int] = 2
IN_BACK: Final[int] = 3
IN_FIRE: Final[int] = 4
N_INPUT_BITS: Final[int] = 5
INPUT_NAMES: Final[tuple[str, ...]] = ("turn_left", "turn_right", "fwd", "back", "fire")

# Persistent game state (sequencer/clock live in the net, not here).
STATE_FIELDS: Final[tuple[tuple[str, int], ...]] = (
    ("map_bits", MAP_CELLS),
    ("px", 8),
    ("py", 8),
    ("ang", 6),
    ("ex", 8),
    ("ey", 8),
    ("enemy_alive", 1),
    ("player_hit", 1),
)


def _offsets(fields: tuple[tuple[str, int], ...]) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    off = 0
    for name, width in fields:
        out[name] = (off, width)
        off += width
    return out


STATE_LAYOUT: Final[dict[str, tuple[int, int]]] = _offsets(STATE_FIELDS)
STATE_BITS: Final[int] = sum(w for _, w in STATE_FIELDS)

# Direction LUTs: Q0.3-ish world units (RAY_SCALE = 8 at unit heading).
COS: Final[tuple[int, ...]] = tuple(
    int(round(math.cos(2.0 * math.pi * a / N_ANG) * RAY_SCALE)) for a in range(N_ANG)
)
SIN: Final[tuple[int, ...]] = tuple(
    int(round(math.sin(2.0 * math.pi * a / N_ANG) * RAY_SCALE)) for a in range(N_ANG)
)

# Default spawn: cell (1,5) looking east; enemy cell (6,2).
DEFAULT_PX: Final[int] = 1 * CELL + CELL // 2
DEFAULT_PY: Final[int] = 5 * CELL + CELL // 2
DEFAULT_ANG: Final[int] = 0
DEFAULT_EX: Final[int] = 6 * CELL + CELL // 2
DEFAULT_EY: Final[int] = 2 * CELL + CELL // 2

SEED: Final[int] = 0
FLIES_BUDGET: Final[int] = 166_700
V1_NEURON_CAP: Final[int] = 8_000

# LIF digital subset: tau=0 makes v=I, a McCulloch-Pitts gate on LIF hardware.
DIGITAL_TAU: Final[float] = 0.0
DIGITAL_THRESH: Final[float] = 1.0
ANALOG_TAU: Final[float] = 0.8
ANALOG_THRESH: Final[float] = 1.0
# 8-bit ripple 127+1 first matches at LIF 24. COS/SIN adds plus dir mux need headroom.
SETTLE_STEPS: Final[int] = 32
POSE_WINDOWS: Final[int] = 5
MARCH_LEN: Final[int] = MAX_DIST + 1  # beat 0 loads; beats 1..15 add like the teacher
STEPS_PER_TICK: Final[int] = SETTLE_STEPS * (POSE_WINDOWS + N_COLS * MARCH_LEN)

# Bake-off scoring (architecture.md).
SCORE_W_ACC: Final[float] = 0.35
SCORE_W_STAB: Final[float] = 0.20
SCORE_W_NOISE: Final[float] = 0.15
SCORE_W_NEUR: Final[float] = 0.15
SCORE_W_SPIK: Final[float] = 0.15
NEURON_REF: Final[int] = 2000
NOISE_P: Final[float] = 0.05

ACC_GATE: Final[dict[str, float]] = {
    "CLOCK": 0.90,
    "BIT_LATCH": 0.95,
    "REGISTER_FILE": 0.90,
    "ADDER_COMPARE": 0.85,
    "RAM": 0.90,
    "SEQUENCER": 0.90,
    "RAY_COLUMN": 0.70,
    "FRAME_READOUT": 0.85,
}

ROLES: Final[tuple[str, ...]] = tuple(ACC_GATE.keys())
ENCODINGS: Final[tuple[str, ...]] = (
    "rate",
    "population",
    "dual_rail",
    "bistable",
    "wta",
    "oscillator",
)
