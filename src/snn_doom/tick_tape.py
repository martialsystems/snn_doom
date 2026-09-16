# Copyright (c) 2026 Martial Systems LLC
"""Multi-tick teacher vs net tape. One-frame fixtures can hide sequencer drift."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from snn_doom.const import CENTER_COL, DOOR_X, N_COLS
from snn_doom.ray_parity import CASES, LOGS
from snn_doom.snn.io import read_bit, read_int
from snn_doom.teacher.engine import tick, tick_v2
from snn_doom.teacher.maps import door_closed, spawn, with_door
from snn_doom.teacher.state import GameState, pack_input

TAPE_N = 4
HELD_N = 32
HELD_BITS = pack_input(0, 0, 1, 0)
FIRE_BITS = pack_input(0, 0, 0, 0, 1)
HELD_FIRE_BITS = pack_input(0, 0, 1, 0, 1)
DOOR_BITS = pack_input(0, 0, 0, 0, 0, 1)
TAPE_BITS = (
    0,
    pack_input(0, 0, 1, 0),
    pack_input(0, 1, 0, 0),
    pack_input(0, 0, 0, 1),
)
# Posed heading-on-enemy. Spawn looking east is the miss. Do not rotate spawn into a hit.
LOOK = spawn(px=104, py=88, ang=48, ex=104, ey=40)
LOOK2 = spawn(px=40, py=88, ang=48)
OVERLAP = spawn(px=24, py=24, ex=24, ey=24)
DRY = spawn(px=104, py=88, ang=48, ammo=0)


def _pose_dict(state: GameState) -> dict[str, int]:
    return {
        "px": state.px,
        "py": state.py,
        "ang": state.ang,
        "ex": state.ex,
        "ey": state.ey,
        "enemy_alive": state.enemy_alive,
        "player_hit": state.player_hit,
        "ex2": state.ex2,
        "ey2": state.ey2,
        "enemy2_alive": state.enemy2_alive,
        "ammo": state.ammo,
        "hp": state.hp,
        "pickup_alive": state.pickup_alive,
    }


def _snn_dists(machine) -> list[int]:
    s = machine.net.spikes
    return [read_int(s, machine.dist_cols[c]) for c in range(N_COLS)]


def _snn_hitscan(machine) -> int:
    return read_bit(machine.net.spikes, machine.sprite_cols[CENTER_COL])


def _step(i: int, bits: int, teacher: GameState, machine, pix, tr) -> dict[str, Any]:
    st = machine.read_state()
    dists = _snn_dists(machine)
    want_pose = _pose_dict(teacher)
    want_d = [c.dist for c in tr.columns]
    want_hs = tr.columns[CENTER_COL].sprite
    got_hs = _snn_hitscan(machine)
    want_shot = tr.shot
    got_shot = machine.read_shot()
    want_door = door_closed(teacher)
    got_door = machine.read_door()
    pose_ok = st == want_pose
    dist_ok = dists == want_d
    frame_ok = bool(np.array_equal(pix, tr.pixels))
    hitscan_ok = got_hs == want_hs
    shot_ok = got_shot == want_shot
    door_ok = got_door == want_door
    ok = pose_ok and dist_ok and frame_ok and hitscan_ok and shot_ok and door_ok
    return {
        "i": i,
        "bits": bits,
        "pose_ok": pose_ok,
        "dist_ok": dist_ok,
        "frame_ok": frame_ok,
        "hitscan_ok": hitscan_ok,
        "shot_ok": shot_ok,
        "door_ok": door_ok,
        "match": ok,
        "teacher_pose": want_pose,
        "snn_pose": st,
        "teacher_dist": want_d,
        "snn_dist": dists,
        "teacher_hitscan": want_hs,
        "snn_hitscan": got_hs,
        "teacher_shot": want_shot,
        "snn_shot": got_shot,
        "teacher_door": want_door,
        "snn_door": got_door,
        "l1": int(np.abs(pix.astype(int) - tr.pixels.astype(int)).sum()),
    }


def _run_bits(
    machine,
    start: GameState,
    bits_seq: list[int],
    tick_fn=tick,
) -> list[dict[str, Any]]:
    teacher = start
    machine.reset(start)
    steps = []
    for i, bits in enumerate(bits_seq):
        tr = tick_fn(teacher, bits)
        teacher = tr.state
        pix = machine.tick(bits)
        steps.append(_step(i, bits, teacher, machine, pix, tr))
    return steps


def run_tick_tape(
    machine=None,
    extra_ticks: int = TAPE_N,
    held_ticks: int = HELD_N,
    *,
    tick_fn=None,
    walk_e2: bool = False,
    out_name: str = "tick_tape.json",
    require_held_clear_heading: bool = True,
) -> dict[str, Any]:
    from snn_doom.modules.pipeline import build_doom_snn

    teacher_tick = tick_fn or tick
    m = machine or build_doom_snn(walk_e2=walk_e2)
    tapes = []
    all_match = True
    cycle = list(TAPE_BITS)
    for name, start, first_bits in CASES:
        bits_seq = [first_bits] + [cycle[i % len(cycle)] for i in range(extra_ticks)]
        steps = _run_bits(m, start, bits_seq, tick_fn=teacher_tick)
        ok = all(s["match"] for s in steps)
        all_match = all_match and ok
        tapes.append({"name": name, "match": ok, "steps": steps})
    held_steps = _run_bits(m, spawn(), [HELD_BITS] * held_ticks, tick_fn=teacher_tick)
    held_ok = all(s["match"] for s in held_steps)
    if require_held_clear_heading:
        held_ok = held_ok and all(s["teacher_hitscan"] == 0 and s["teacher_shot"] == 0 for s in held_steps)
    all_match = all_match and held_ok
    miss_steps = _run_bits(m, spawn(), [FIRE_BITS], tick_fn=teacher_tick)
    kill_steps = _run_bits(m, LOOK, [FIRE_BITS], tick_fn=teacher_tick)
    miss = miss_steps[0]
    kill = kill_steps[0]
    miss_ok = (
        miss["match"]
        and miss["teacher_hitscan"] == 0
        and miss["teacher_shot"] == 0
        and miss["teacher_pose"]["enemy_alive"] == 1
    )
    kill_ok = (
        kill["match"]
        and kill["teacher_hitscan"] == 1
        and kill["teacher_shot"] == 1
        and kill["teacher_pose"]["enemy_alive"] == 0
    )
    trigger_ok = miss_ok and kill_ok
    all_match = all_match and trigger_ok
    held_fire_steps = _run_bits(m, spawn(), [HELD_FIRE_BITS] * held_ticks, tick_fn=teacher_tick)
    if require_held_clear_heading:
        held_fire_ok = all(
            s["match"] and s["teacher_shot"] == 0 and s["teacher_hitscan"] == 0 and s["teacher_pose"]["enemy_alive"] == 1
            for s in held_fire_steps
        )
    else:
        held_fire_ok = all(s["match"] for s in held_fire_steps)
    all_match = all_match and held_fire_ok
    hurt_start = spawn(px=24, py=24, ex=24, ey=24, hp=3)
    hurt_steps = _run_bits(m, hurt_start, [0, HELD_BITS], tick_fn=teacher_tick)
    hurt_ok = (
        all(s["match"] for s in hurt_steps)
        and hurt_steps[0]["teacher_pose"]["hp"] == 2
        and hurt_steps[0]["teacher_pose"]["player_hit"] == 0
        and hurt_steps[0]["teacher_pose"]["enemy_alive"] == 0
        and hurt_steps[1]["teacher_pose"]["px"] > hurt_steps[0]["teacher_pose"]["px"]
    )
    dead_start = spawn(px=24, py=24, ex=24, ey=24, hp=1)
    dead_steps = _run_bits(m, dead_start, [0, HELD_BITS], tick_fn=teacher_tick)
    death_ok = (
        hurt_ok
        and all(s["match"] for s in dead_steps)
        and dead_steps[0]["teacher_pose"]["hp"] == 0
        and dead_steps[0]["teacher_pose"]["player_hit"] == 1
        and dead_steps[1]["teacher_pose"]["px"] == dead_steps[0]["teacher_pose"]["px"]
        and dead_steps[1]["teacher_pose"]["player_hit"] == 1
    )
    all_match = all_match and death_ok
    closed_start = with_door(spawn(), 1)
    block_steps = _run_bits(m, closed_start, [HELD_BITS] * 12, tick_fn=teacher_tick)
    pxs = [s["teacher_pose"]["px"] for s in block_steps]
    door_block_ok = (
        all(s["match"] for s in block_steps)
        and all(s["teacher_door"] == 1 for s in block_steps)
        and any(pxs[i] == pxs[i - 1] for i in range(1, len(pxs)))
        and block_steps[-1]["teacher_pose"]["px"] < DOOR_X * 16
    )
    open_steps = _run_bits(m, closed_start, [DOOR_BITS] + [HELD_BITS] * 12, tick_fn=teacher_tick)
    door_open_ok = (
        all(s["match"] for s in open_steps)
        and open_steps[0]["teacher_door"] == 0
        and any(s["teacher_pose"]["px"] >> 4 >= DOOR_X for s in open_steps)
    )
    approach = spawn()
    n_front = 0
    while (approach.px + 4) >> 4 < DOOR_X:
        approach = teacher_tick(approach, HELD_BITS).state
        n_front += 1
    close_steps = _run_bits(m, spawn(), [HELD_BITS] * n_front + [DOOR_BITS, HELD_BITS], tick_fn=teacher_tick)
    door_close_ok = (
        all(s["match"] for s in close_steps)
        and close_steps[-2]["teacher_door"] == 1
        and close_steps[-1]["teacher_pose"]["px"] == close_steps[-2]["teacher_pose"]["px"]
    )
    door_ok = door_block_ok and door_open_ok and door_close_ok
    all_match = all_match and door_ok
    e2_steps = _run_bits(m, LOOK2, [FIRE_BITS], tick_fn=teacher_tick)
    e2_ok = (
        e2_steps[0]["match"]
        and e2_steps[0]["teacher_shot"] == 1
        and e2_steps[0]["teacher_pose"]["enemy2_alive"] == 0
        and e2_steps[0]["teacher_pose"]["enemy_alive"] == 1
    )
    dry_steps = _run_bits(m, DRY, [FIRE_BITS], tick_fn=teacher_tick)
    dry_ok = (
        dry_steps[0]["match"]
        and dry_steps[0]["teacher_shot"] == 0
        and dry_steps[0]["teacher_pose"]["enemy_alive"] == 1
        and dry_steps[0]["teacher_pose"]["ammo"] == 0
    )
    all_match = all_match and e2_ok and dry_ok
    from snn_doom.const import PICKUP_X, PICKUP_Y

    pk_start = spawn(px=PICKUP_X * 16 + 8, py=PICKUP_Y * 16 + 8, ammo=1)
    pk_steps = _run_bits(m, pk_start, [0], tick_fn=teacher_tick)
    pickup_ok = (
        pk_steps[0]["match"]
        and pk_steps[0]["teacher_pose"]["ammo"] == 7
        and pk_steps[0]["teacher_pose"]["pickup_alive"] == 0
    )
    all_match = all_match and pickup_ok
    chase_n = 8
    chase_steps = _run_bits(m, spawn(), [0] * chase_n, tick_fn=teacher_tick)
    e1_moved = any(
        s["teacher_pose"]["ex"] != spawn().ex or s["teacher_pose"]["ey"] != spawn().ey for s in chase_steps
    )
    e2_moved = any(
        s["teacher_pose"]["ex2"] != spawn().ex2 or s["teacher_pose"]["ey2"] != spawn().ey2 for s in chase_steps
    )
    two_ok = all(s["match"] for s in chase_steps) and e1_moved and (e2_moved if walk_e2 else not e2_moved)
    if walk_e2:
        all_match = all_match and two_ok
    payload = {
        "all_match": all_match,
        "machine": "v2" if walk_e2 else "v1",
        "extra_ticks": extra_ticks,
        "held_ticks": held_ticks,
        "held_key": "fwd",
        "tapes": tapes,
        "held": {"name": "held_fwd", "match": held_ok, "steps": held_steps},
        "trigger": {
            "match": trigger_ok,
            "miss": {"name": "trigger_miss", "match": miss_ok, "steps": miss_steps},
            "kill": {"name": "trigger_kill", "match": kill_ok, "steps": kill_steps},
        },
        "held_fire": {"name": "held_fire_corridor", "match": held_fire_ok, "steps": held_fire_steps},
        "death": {
            "match": death_ok,
            "hurt": {"name": "hp_hurt_move", "match": hurt_ok, "steps": hurt_steps},
            "dead": {"name": "hp_zero_dead", "match": death_ok and dead_steps[0]["match"], "steps": dead_steps},
        },
        "door": {
            "match": door_ok,
            "block": {"name": "door_closed_block", "match": door_block_ok, "steps": block_steps},
            "open": {"name": "door_toggle_open_pass", "match": door_open_ok, "steps": open_steps},
            "close": {"name": "door_toggle_close_block", "match": door_close_ok, "steps": close_steps},
        },
        "second": {"name": "second_sprite_kill", "match": e2_ok, "steps": e2_steps},
        "ammo_dry": {"name": "ammo_zero_no_kill", "match": dry_ok, "steps": dry_steps},
        "pickup": {"name": "pickup_fill_ammo", "match": pickup_ok, "steps": pk_steps},
        "two_chaser": {
            "name": "two_chaser_idle",
            "match": two_ok,
            "e1_moved": e1_moved,
            "e2_moved": e2_moved,
            "steps": chase_steps,
        },
    }
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / out_name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def run_tick_tape_v2(machine=None, extra_ticks: int = TAPE_N, held_ticks: int = HELD_N) -> dict[str, Any]:
    """Held-fwd plus two-chaser play against tick_v2. Heading may see walking e2."""
    return run_tick_tape(
        machine,
        extra_ticks=extra_ticks,
        held_ticks=held_ticks,
        tick_fn=tick_v2,
        walk_e2=True,
        out_name="tick_tape_v2.json",
        require_held_clear_heading=False,
    )

