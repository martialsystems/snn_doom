# Copyright (c) 2026 Martial Systems LLC
"""Vectorized LIF. Digital modules use tau=0; analog bake-off uses tau=0.8.

Library: PyTorch when training analog encodings (surrogate BPTT). NumPy for the
stitched digital machine and for evolutionary search. Same discrete-time equation:

    v <- tau * v + I
    s <- [v >= thresh]
    v <- v * (1 - s)     # hard reset

PyTorch is the training library because fly_pong already pins torch, surrogate
gradients are standard there, and we can freeze a module as a weight matrix.
JAX is not used: one autodiff stack, not two.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from snn_doom.const import DIGITAL_TAU, DIGITAL_THRESH


@dataclass
class LifNet:
    n: int
    tau: np.ndarray
    thresh: np.ndarray
    src: np.ndarray
    dst: np.ndarray
    w_e: np.ndarray
    names: list[str]
    module: list[str]
    v: np.ndarray = field(init=False)
    spikes: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        self.v = np.zeros(self.n, dtype=np.float32)
        self.spikes = np.zeros(self.n, dtype=np.float32)

    def reset(self) -> None:
        self.v.fill(0.0)
        self.spikes.fill(0.0)

    def step(self, current: np.ndarray | None = None) -> np.ndarray:
        i = np.zeros(self.n, dtype=np.float32)
        if self.src.size and self.spikes.any():
            mask = self.spikes[self.src] > 0.0
            if mask.any():
                np.add.at(i, self.dst[mask], self.w_e[mask] * self.spikes[self.src[mask]])
        if current is not None:
            i = i + current
        self.v = self.tau * self.v + i
        self.spikes = (self.v >= self.thresh).astype(np.float32)
        self.v = self.v * (1.0 - self.spikes)
        return self.spikes

    def zero_module(self, name: str) -> None:
        """Ablation: drop edges into or out of that module."""
        dead = {i for i, m in enumerate(self.module) if m == name}
        if not dead:
            return
        keep = [k for k in range(self.src.size) if int(self.src[k]) not in dead and int(self.dst[k]) not in dead]
        self.src = self.src[keep]
        self.dst = self.dst[keep]
        self.w_e = self.w_e[keep]

    def module_spikes(self, name: str) -> np.ndarray:
        idx = np.array([m == name for m in self.module], dtype=bool)
        return self.spikes[idx]

    def spikes_per_step(self) -> float:
        return float(self.spikes.sum())


class NetBuilder:
    def __init__(self) -> None:
        self.names: list[str] = []
        self.module: list[str] = []
        self.tau: list[float] = []
        self.thresh: list[float] = []
        self.edges: list[tuple[int, int, float]] = []

    @property
    def n(self) -> int:
        return len(self.names)

    def alloc(
        self,
        name: str,
        module: str,
        tau: float = DIGITAL_TAU,
        thresh: float = DIGITAL_THRESH,
    ) -> int:
        idx = self.n
        self.names.append(name)
        self.module.append(module)
        self.tau.append(tau)
        self.thresh.append(thresh)
        return idx

    def alloc_pair(self, name: str, module: str, **kwargs: float) -> tuple[int, int]:
        t = self.alloc(f"{name}_t", module, **kwargs)
        f = self.alloc(f"{name}_f", module, **kwargs)
        return t, f

    def wire(self, src: int, dst: int, weight: float) -> None:
        self.edges.append((src, dst, float(weight)))

    def compile(self) -> LifNet:
        if self.edges:
            src, dst, weight = zip(*self.edges)
            src_a = np.array(src, dtype=np.int32)
            dst_a = np.array(dst, dtype=np.int32)
            w_e = np.array(weight, dtype=np.float32)
        else:
            src_a = np.zeros(0, dtype=np.int32)
            dst_a = np.zeros(0, dtype=np.int32)
            w_e = np.zeros(0, dtype=np.float32)
        return LifNet(
            n=self.n,
            tau=np.array(self.tau, dtype=np.float32),
            thresh=np.array(self.thresh, dtype=np.float32),
            src=src_a,
            dst=dst_a,
            w_e=w_e,
            names=list(self.names),
            module=list(self.module),
        )


def heaviside_surrogate_fast_sigmoid(v, thresh, beta: float = 8.0):
    """Torch-only surrogate. Imported lazily so numpy tests do not need torch."""
    import torch

    class _Spike(torch.autograd.Function):
        @staticmethod
        def forward(ctx, membrane, th, b):
            ctx.save_for_backward(membrane, th, b)
            return (membrane >= th).to(membrane.dtype)

        @staticmethod
        def backward(ctx, grad_output):
            membrane, th, b = ctx.saved_tensors
            diff = b * (membrane - th)
            sig = torch.sigmoid(diff)
            return grad_output * b * sig * (1.0 - sig), None, None

    if not isinstance(v, __import__("torch").Tensor):
        raise TypeError("surrogate spike is torch-only")
    import torch as _torch

    th = v.new_tensor(thresh) if not isinstance(thresh, _torch.Tensor) else thresh
    b = v.new_tensor(beta)
    return _Spike.apply(v, th, b)
