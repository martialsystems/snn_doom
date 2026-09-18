# Copyright (c) 2026 Martial Systems LLC
"""Fixed column-to-pixel decoder. Host only argmaxes color lines per pixel."""
from __future__ import annotations

from snn_doom.const import COLOR_ENEMY, COLOR_FLOOR, COLOR_SKY, COLOR_WALL, FRAME_H, N_COLS
from snn_doom.snn.digital import Rail, and2, decoder_bits, or_n
from snn_doom.snn.lif import NetBuilder
from snn_doom.teacher.render import is_enemy_row, is_wall_row


def build_fixed_readout(b: NetBuilder, encoding: str = "wta", *, n_cols: int | None = None) -> dict:
    del encoding
    cols = N_COLS if n_cols is None else int(n_cols)
    module = "FRAME_READOUT"
    dist_bits: list[list[Rail]] = []
    sprite_bits: list[Rail] = []
    pixels = []
    mid = FRAME_H // 2
    for c in range(cols):
        bits = [Rail(*b.alloc_pair(f"d{c}_{k}", module)) for k in range(4)]
        dist_bits.append(bits)
        sprite_bits.append(Rail(*b.alloc_pair(f"sp{c}", module)))
        onehot = decoder_bits(b, bits, f"doh_{c}", module)
        col_pix = []
        for row in range(FRAME_H):
            color = [b.alloc(f"p_{row}_{c}_{k}", module) for k in range(4)]
            sky_src = []
            floor_src = []
            wall_src = []
            enemy_src = []
            for dist, line in enumerate(onehot):
                if is_wall_row(row, dist):
                    wall_src.append(line)
                elif row < mid:
                    sky_src.append(line)
                else:
                    floor_src.append(line)
                if is_enemy_row(row, dist):
                    enemy_src.append(line)
            for src in sky_src:
                b.wire(src, color[COLOR_SKY], 1.2)
            for src in floor_src:
                b.wire(src, color[COLOR_FLOOR], 1.2)
            for src in wall_src:
                b.wire(src, color[COLOR_WALL], 1.2)
            if enemy_src:
                geom = or_n(b, enemy_src, f"eg_{row}_{c}", module)
                en = and2(b, sprite_bits[c].t, geom, f"en_{row}_{c}", module)
                b.wire(en, color[COLOR_ENEMY], 2.4)
                b.wire(en, color[COLOR_WALL], -2.4)
                b.wire(en, color[COLOR_SKY], -2.4)
                b.wire(en, color[COLOR_FLOOR], -2.4)
            col_pix.append(color)
        pixels.append(col_pix)
    return {
        "dist_bits": dist_bits,
        "sprite_bits": sprite_bits,
        "pixels": pixels,
        "n_in": cols * 5,
        "n_out": cols * FRAME_H * 4,
    }
