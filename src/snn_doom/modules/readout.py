# Copyright (c) 2026 Martial Systems LLC
"""Fixed column-to-pixel decoder. Host only argmaxes color lines per pixel."""
from __future__ import annotations

from snn_doom.const import COLOR_ENEMY, COLOR_FLOOR, COLOR_SKY, COLOR_WALL, FRAME_H, N_COLS
from snn_doom.snn.digital import Rail, and2, decoder_bits
from snn_doom.snn.lif import NetBuilder


def column_height(dist: int) -> int:
    if dist <= 0:
        return 0
    return max(1, FRAME_H - dist)


def build_fixed_readout(b: NetBuilder, encoding: str = "wta") -> dict:
    del encoding
    module = "FRAME_READOUT"
    dist_bits: list[list[Rail]] = []
    sprite_bits: list[Rail] = []
    pixels = []
    for c in range(N_COLS):
        bits = [Rail(*b.alloc_pair(f"d{c}_{k}", module)) for k in range(4)]
        dist_bits.append(bits)
        sprite_bits.append(Rail(*b.alloc_pair(f"sp{c}", module)))
        onehot = decoder_bits(b, bits, f"doh_{c}", module)
        col_pix = []
        for row in range(FRAME_H):
            color = [b.alloc(f"p_{row}_{c}_{k}", module) for k in range(4)]
            mid = FRAME_H // 2
            sky_src = []
            floor_src = []
            wall_src = []
            for dist, line in enumerate(onehot):
                h = column_height(dist)
                half = max(1, h // 2) if h else 0
                is_wall = h and abs(row - mid) < half
                if dist == 0 or not is_wall:
                    if row < mid:
                        sky_src.append(line)
                    else:
                        floor_src.append(line)
                else:
                    wall_src.append(line)
            for src in sky_src:
                b.wire(src, color[COLOR_SKY], 1.2)
            for src in floor_src:
                b.wire(src, color[COLOR_FLOOR], 1.2)
            for src in wall_src:
                b.wire(src, color[COLOR_WALL], 1.2)
            en = and2(b, sprite_bits[c].t, color[COLOR_WALL], f"en_{row}_{c}", module)
            b.wire(en, color[COLOR_ENEMY], 2.4)
            b.wire(en, color[COLOR_WALL], -2.4)
            col_pix.append(color)
        pixels.append(col_pix)
    return {
        "dist_bits": dist_bits,
        "sprite_bits": sprite_bits,
        "pixels": pixels,
        "n_in": N_COLS * 5,
        "n_out": N_COLS * FRAME_H * 4,
    }
