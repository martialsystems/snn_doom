# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

import numpy as np

from snn_doom.const import FRAME_H, N_COLS, N_COLORS
from snn_doom.snn.encodings import build_readout
from snn_doom.snn.io import drive_bit, drive_int, zeros
from snn_doom.teacher.render import Column, paint_column, paint_frame


def _decode(enc, last) -> np.ndarray:
    frame = np.zeros((FRAME_H, N_COLS), dtype=np.uint8)
    for c in range(N_COLS):
        for r in range(FRAME_H):
            vals = [float(last[enc.extra["pixels"][c][r][k]]) for k in range(N_COLORS)]
            frame[r, c] = int(np.argmax(vals))
    return frame


def _drive(enc, dist: int, sprite: int, settle: int = 12):
    last = None
    for _ in range(settle):
        cur = zeros(enc.net)
        for c in range(N_COLS):
            drive_int(cur, enc.extra["dist_bits"][c], dist)
            drive_bit(cur, enc.extra["sprite_bits"][c], sprite)
        last = enc.net.step(cur)
    return last


def test_readout_sprite_blob_matches_paint_column() -> None:
    enc = build_readout("wta")
    # dist=10 sprite=1 is the held-fwd step-6 miss: wall-overwrite L1 was 2.
    for dist, sprite in ((4, 0), (10, 1), (12, 1), (0, 1), (8, 1)):
        enc.reset()
        last = _drive(enc, dist, sprite)
        want = paint_frame(tuple(Column(dist=dist, side=0, sprite=sprite) for _ in range(N_COLS)))
        got = _decode(enc, last)
        assert np.array_equal(got, want), (dist, sprite, int(np.abs(got.astype(int) - want.astype(int)).sum()))
        if sprite:
            col = paint_column(Column(dist=dist, side=0, sprite=1))
            assert (got[:, 0] == col).all()
