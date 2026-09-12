# Copyright (c) 2026 Martial Systems LLC
"""Optional BPTT on a rate-coded 4-bit adder. Used when digital priors are not the point."""
from __future__ import annotations

from typing import Any


def train_rate_adder(steps: int = 200, seed: int = 0) -> dict[str, Any]:
    try:
        import torch
        from torch import nn
    except ImportError:
        return {"ok": False, "reason": "torch_missing"}

    from snn_doom.snn.lif import heaviside_surrogate_fast_sigmoid

    g = torch.Generator().manual_seed(seed)
    n_in, n_h, n_out, t_steps = 8, 64, 6, 16
    w_in = nn.Parameter(torch.randn(n_h, n_in, generator=g) * 0.1)
    w_rec = nn.Parameter(torch.randn(n_h, n_h, generator=g) * 0.05)
    w_out = nn.Parameter(torch.randn(n_out, n_h, generator=g) * 0.1)
    opt = torch.optim.Adam([w_in, w_rec, w_out], lr=1e-2)
    last = 0.0
    for _ in range(steps):
        a = torch.randint(0, 16, (8,), generator=g)
        b = torch.randint(0, 16, (8,), generator=g)
        bits_a = ((a[:, None] >> torch.arange(4)) & 1).float()
        bits_b = ((b[:, None] >> torch.arange(4)) & 1).float()
        x = torch.cat([bits_a, bits_b], dim=1)
        target = torch.cat(
            [
                (((a + b)[:, None] >> torch.arange(4)) & 1).float(),
                (a > b).float()[:, None],
                (a == b).float()[:, None],
            ],
            dim=1,
        )
        v = torch.zeros(8, n_h)
        acc = torch.zeros(8, n_out)
        for _t in range(t_steps):
            i = x @ w_in.T + v @ w_rec.T
            s = heaviside_surrogate_fast_sigmoid(v + i, 1.0)
            v = 0.8 * (v + i) * (1.0 - s.detach())
            acc = acc + s @ w_out.T
        pred = acc / t_steps
        loss = nn.functional.mse_loss(pred, target)
        opt.zero_grad()
        loss.backward()
        opt.step()
        last = float(loss.detach())
    return {"ok": True, "loss": last, "steps": steps, "seed": seed}
