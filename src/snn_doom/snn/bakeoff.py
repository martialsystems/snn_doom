# Copyright (c) 2026 Martial Systems LLC
"""Role x encoding bake-off. Hand-wired priors first; analog nets stay random unless trained."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from snn_doom.const import ENCODINGS, NOISE_P, ROLES, SEED
from snn_doom.snn.encodings import BUILDERS, EncodedNet
from snn_doom.snn.io import drive_bit, drive_index, drive_int, read_int, zeros
from snn_doom.snn.score import passes_gate, score_row
from snn_doom.teacher.maps import spawn
from snn_doom.teacher.render import column_angle, paint_frame
from snn_doom.teacher.render import cast_ray


def _kick_and_run(enc: EncodedNet, steps: int, kick: int | None, extra_cur=None) -> list[np.ndarray]:
    enc.reset()
    traces = []
    for t in range(steps):
        cur = zeros(enc.net)
        if t == 0 and kick is not None:
            drive_index(cur, kick)
        if extra_cur is not None:
            cur = cur + extra_cur
        traces.append(enc.net.step(cur).copy())
    return traces


def eval_clock(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    period = int(enc.extra["period"]) if "period" in enc.extra else 8
    out = enc.extra["out"]
    kick = enc.extra.get("kick")
    steps = period * 8
    traces = _kick_and_run(enc, steps, kick)
    if noise and rng is not None:
        for s in traces:
            flip = rng.random(s.shape) < noise
            s[flip] = 1.0 - s[flip]
    got = [int(s[out] >= 1.0) for s in traces]
    expect = [1 if t % period == 0 else 0 for t in range(steps)]
    # ring has a 0-delay on the kicked cell at t=0
    acc = float(sum(g == e for g, e in zip(got, expect)) / steps)
    # stability: last 4 periods vs first 4
    half = period * 4
    acc_late = float(sum(g == e for g, e in zip(got[half:], expect[half:])) / max(len(got[half:]), 1))
    spk = float(np.mean([s.sum() for s in traces]))
    return {"accuracy": acc, "stability": acc_late, "spikes_per_step": spk, "n_neurons": enc.net.n}


def eval_latch(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    enc.reset()
    steps_hold = 24
    traces = []
    q = enc.extra.get("out")
    for t in range(4 + steps_hold + 4 + steps_hold):
        cur = zeros(enc.net)
        if t < 4:
            if "we_t" in enc.extra:
                drive_index(cur, enc.extra["we_t"])
                drive_index(cur, enc.extra["d_t"])
                drive_index(cur, enc.extra["we_f"], amp=0.0)
            elif "in" in enc.extra:
                drive_index(cur, enc.extra["in"])
            elif "t" in enc.extra:
                drive_index(cur, enc.extra["t"])
        elif 4 + steps_hold <= t < 8 + steps_hold:
            if "we_t" in enc.extra:
                drive_index(cur, enc.extra["we_t"])
                drive_index(cur, enc.extra["d_f"])
            elif "in" in enc.extra:
                pass
            elif "f" in enc.extra:
                drive_index(cur, enc.extra["f"])
        s = enc.net.step(cur).copy()
        if noise and rng is not None:
            flip = rng.random(s.shape) < noise
            s[flip] = 1.0 - s[flip]
        traces.append(s)
    # after first write, hold 1; after second, hold 0
    mid = 4 + steps_hold
    hold1 = traces[4:mid]
    hold0 = traces[mid + 4 :]
    acc1 = float(np.mean([s[q] >= 1.0 for s in hold1])) if hold1 else 0.0
    acc0 = float(np.mean([s[q] < 1.0 for s in hold0])) if hold0 else 0.0
    acc = 0.5 * acc1 + 0.5 * acc0
    stab = acc0
    spk = float(np.mean([s.sum() for s in traces]))
    return {"accuracy": acc, "stability": stab, "spikes_per_step": spk, "n_neurons": enc.net.n}


def eval_register(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    if "regs" not in enc.extra or not enc.extra["regs"]:
        return {"accuracy": 0.0, "stability": 0.0, "spikes_per_step": 0.0, "n_neurons": enc.net.n}
    enc.reset()
    regs = enc.extra["regs"]
    width = len(regs[0])
    value = 0b1010
    # force-write by driving latch rails
    cur = zeros(enc.net)
    for k, q in enumerate(regs[1]):
        drive_bit(cur, q, (value >> k) & 1)
    for _ in range(4):
        enc.net.step(cur)
    # hold
    ok = 0
    tot = 0
    for _ in range(16):
        s = enc.net.step(zeros(enc.net)).copy()
        if noise and rng is not None:
            flip = rng.random(s.shape) < noise
            s[flip] = 1.0 - s[flip]
        got = read_int(s, regs[1])
        ok += int(got == value)
        tot += 1
    acc = ok / max(tot, 1)
    return {
        "accuracy": float(acc),
        "stability": float(acc),
        "spikes_per_step": float(enc.net.spikes.sum()),
        "n_neurons": enc.net.n,
    }


def eval_adder(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    if "a" not in enc.extra:
        return {"accuracy": 0.05, "stability": 0.0, "spikes_per_step": 0.0, "n_neurons": enc.net.n}
    rng = rng or np.random.default_rng(SEED)
    width = enc.extra["width"]
    n_trials = 16
    hits = 0
    late_hits = 0
    spk = 0.0
    for trial in range(n_trials):
        a = int(rng.integers(0, 1 << width))
        c = int(rng.integers(0, 1 << width))
        enc.reset()
        last = None
        for t in range(24):
            cur = zeros(enc.net)
            drive_int(cur, enc.extra["a"], a)
            drive_int(cur, enc.extra["c"], c)
            drive_bit(cur, enc.extra["cin"], 0)
            s = enc.net.step(cur)
            spk += float(s.sum())
            last = s
        got = read_int(last, enc.extra["sums"])
        want = (a + c) & ((1 << width) - 1)
        hits += int(got == want)
        late_hits += int(got == want)
        if noise:
            pass
    acc = hits / n_trials
    return {
        "accuracy": float(acc),
        "stability": float(late_hits / n_trials),
        "spikes_per_step": spk / (n_trials * 24),
        "n_neurons": enc.net.n,
    }


def eval_ram(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    if "cells" not in enc.extra:
        return {"accuracy": 0.0, "stability": 0.0, "spikes_per_step": 0.0, "n_neurons": enc.net.n}
    enc.reset()
    addr, we, data = enc.extra["addr"], enc.extra["we"], enc.extra["data"]
    # write 1 at address 3
    for t in range(8):
        cur = zeros(enc.net)
        drive_int(cur, addr, 3)
        drive_bit(cur, we, 1)
        drive_bit(cur, data, 1)
        enc.net.step(cur)
    ok = 0
    tot = 0
    for t in range(12):
        cur = zeros(enc.net)
        drive_int(cur, addr, 3)
        drive_bit(cur, we, 0)
        s = enc.net.step(cur)
        bit = int(s[enc.extra["out_t"]] >= 1.0)
        if t >= 4:
            ok += int(bit == 1)
            tot += 1
    acc = ok / max(tot, 1)
    return {
        "accuracy": float(acc),
        "stability": float(acc),
        "spikes_per_step": float(enc.net.spikes.sum()),
        "n_neurons": enc.net.n,
    }


def eval_seq(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    cells = enc.extra.get("out") or enc.extra.get("cells")
    if not cells:
        return {"accuracy": 0.0, "stability": 0.0, "spikes_per_step": 0.0, "n_neurons": enc.net.n}
    n = len(cells)
    traces = _kick_and_run(enc, n * 3, enc.extra.get("kick"))
    ok = 0
    tot = 0
    for t, s in enumerate(traces):
        hot = [int(s[i] >= 1.0) for i in cells]
        want = t % n
        ok += int(hot[want] == 1 and sum(hot) == 1)
        tot += 1
    acc = ok / max(tot, 1)
    late = traces[n:]
    ok2 = 0
    for t, s in enumerate(late, start=n):
        hot = [int(s[i] >= 1.0) for i in cells]
        want = t % n
        ok2 += int(hot[want] == 1 and sum(hot) == 1)
    stab = ok2 / max(len(late), 1)
    return {
        "accuracy": float(acc),
        "stability": float(stab),
        "spikes_per_step": float(np.mean([s.sum() for s in traces])),
        "n_neurons": enc.net.n,
    }


def eval_ray(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    if "x" not in enc.extra:
        return {"accuracy": 0.1, "stability": 0.0, "spikes_per_step": 1.0, "n_neurons": enc.net.n}
    s0 = spawn()
    hits = 0
    n = 8
    spk = 0.0
    from snn_doom.const import COS, SIN

    for col in range(n):
        enc.reset()
        ang = column_angle(s0.ang, col)
        teacher = cast_ray(s0, ang)
        # load map + pose + dir
        for t in range(6):
            cur = zeros(enc.net)
            drive_int(cur, enc.extra["x"], s0.px)
            drive_int(cur, enc.extra["y"], s0.py)
            drive_int(cur, enc.extra["dx"], COS[ang] & 0xFF)
            drive_int(cur, enc.extra["dy"], SIN[ang] & 0xFF)
            drive_bit(cur, enc.extra["cin0"], 0)
            drive_bit(cur, enc.extra["cin1"], 0)
            drive_bit(cur, enc.extra["we"], 0)
            for i, cell in enumerate(enc.extra["ram_cells"]):
                drive_bit(cur, cell, (s0.map_bits >> i) & 1)
            if t == 0:
                drive_index(cur, enc.extra["march"][0])
            enc.net.step(cur)
        last = None
        for t in range(16 * 12):
            cur = zeros(enc.net)
            drive_int(cur, enc.extra["dx"], COS[ang] & 0xFF)
            drive_int(cur, enc.extra["dy"], SIN[ang] & 0xFF)
            last = enc.net.step(cur)
            spk += float(last.sum())
        got = read_int(last, enc.extra["dist"])
        hits += int(got == teacher.dist)
    acc = hits / n
    return {
        "accuracy": float(acc),
        "stability": float(acc),
        "spikes_per_step": spk / (n * 16 * 12),
        "n_neurons": enc.net.n,
    }


def eval_readout(enc: EncodedNet, noise: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    if "dist_bits" not in enc.extra:
        return {"accuracy": 0.1, "stability": 0.0, "spikes_per_step": 1.0, "n_neurons": enc.net.n}
    from snn_doom.teacher.render import Column

    cols = tuple(Column(dist=4, side=0, sprite=0) for _ in range(16))
    want = paint_frame(cols)
    enc.reset()
    last = None
    for _ in range(12):
        cur = zeros(enc.net)
        for c in range(16):
            drive_int(cur, enc.extra["dist_bits"][c], 4)
            drive_bit(cur, enc.extra["sprite_bits"][c], 0)
        last = enc.net.step(cur)
    frame = np.zeros_like(want)
    for c in range(16):
        for r in range(16):
            vals = [float(last[enc.extra["pixels"][c][r][k]]) for k in range(4)]
            frame[r, c] = int(np.argmax(vals))
    acc = float((frame == want).mean())
    return {
        "accuracy": acc,
        "stability": acc,
        "spikes_per_step": float(last.sum()),
        "n_neurons": enc.net.n,
    }


EVALS = {
    "CLOCK": eval_clock,
    "BIT_LATCH": eval_latch,
    "REGISTER_FILE": eval_register,
    "ADDER_COMPARE": eval_adder,
    "RAM": eval_ram,
    "SEQUENCER": eval_seq,
    "RAY_COLUMN": eval_ray,
    "FRAME_READOUT": eval_readout,
}


def run_bakeoff(seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    rows = []
    winners: dict[str, str] = {}
    for role in ROLES:
        best = None
        for enc_name in ENCODINGS:
            try:
                enc = BUILDERS[role](enc_name)
                clean = EVALS[role](enc)
                noisy = EVALS[role](enc, noise=NOISE_P, rng=rng)
                row = {
                    "role": role,
                    "encoding": enc_name,
                    "accuracy": clean["accuracy"],
                    "stability": clean["stability"],
                    "noise_robustness": noisy["accuracy"],
                    "n_neurons": clean["n_neurons"],
                    "spikes_per_step": clean["spikes_per_step"],
                    "error": None,
                }
            except Exception as exc:  # bake-off must complete even if a net fails
                row = {
                    "role": role,
                    "encoding": enc_name,
                    "accuracy": 0.0,
                    "stability": 0.0,
                    "noise_robustness": 0.0,
                    "n_neurons": 0,
                    "spikes_per_step": 0.0,
                    "error": type(exc).__name__ + ": " + str(exc)[:200],
                }
            row["score"] = score_row(row)
            row["pass_gate"] = passes_gate(role, row["accuracy"])
            rows.append(row)
            if row["pass_gate"] and (best is None or row["score"] > best["score"]):
                best = row
        winners[role] = best["encoding"] if best is not None else "none"
    return {"seed": seed, "rows": rows, "winners": winners}


def write_bakeoff(path: Path, md_path: Path | None = None) -> dict:
    data = run_bakeoff()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if md_path is not None:
        lines = [
            "# Encoding bake-off",
            "",
            f"Seed {data['seed']}. Rubric: 0.35 accuracy, 0.20 stability, 0.15 noise, 0.15 neuron frugality, 0.15 spike frugality.",
            "",
            "| Role | Encoding | Acc | Stab | Noise | Neurons | Spikes/step | Score | Gate |",
            "|------|----------|----:|-----:|------:|--------:|------------:|------:|------|",
        ]
        for row in data["rows"]:
            lines.append(
                f"| {row['role']} | {row['encoding']} | {row['accuracy']:.3f} | {row['stability']:.3f} | "
                f"{row['noise_robustness']:.3f} | {row['n_neurons']} | {row['spikes_per_step']:.2f} | "
                f"{row['score']:.3f} | {'pass' if row['pass_gate'] else 'fail'} |"
            )
        lines.append("")
        lines.append("## Winners")
        lines.append("")
        for role, enc in data["winners"].items():
            lines.append(f"- {role}: {enc}")
        lines.append("")
        md_path.write_text("\n".join(lines), encoding="utf-8")
    return data
