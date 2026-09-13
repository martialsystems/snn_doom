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

_NUMBA_KERNEL = None
_NUMBA_TRIED = False
_SCIPY_CSR = None
_SCIPY_TRIED = False


def _numba_step_n():
    """Optional compiled n-step kernel. Same discrete LIF. CSR sparse I = W @ s."""
    global _NUMBA_KERNEL, _NUMBA_TRIED
    if _NUMBA_TRIED:
        return _NUMBA_KERNEL
    _NUMBA_TRIED = True
    try:
        import numba
    except ImportError:
        _NUMBA_KERNEL = None
        return None

    @numba.njit(cache=True)
    def kernel(n_steps, v0, spikes0, tau, thresh, indptr, indices, csr_w, current):
        n = v0.shape[0]
        v = v0.copy()
        spikes = spikes0.copy()
        i = np.empty(n, dtype=np.float32)
        acc = 0.0
        for _ in range(n_steps):
            for j in range(n):
                i[j] = current[j]
            for src in range(n):
                s = spikes[src]
                if s > 0.0:
                    start = indptr[src]
                    end = indptr[src + 1]
                    for e in range(start, end):
                        i[indices[e]] += csr_w[e] * s
            for j in range(n):
                v[j] = tau[j] * v[j] + i[j]
                if v[j] >= thresh[j]:
                    spikes[j] = 1.0
                    v[j] = 0.0
                    acc += 1.0
                else:
                    spikes[j] = 0.0
        return v, spikes, acc

    @numba.njit(cache=True, fastmath=True)
    def kernel_tau0(n_steps, v0, spikes0, thresh, indptr, indices, csr_w, current):
        n = v0.shape[0]
        v = v0.copy()
        spikes = spikes0.copy()
        i = np.empty(n, dtype=np.float32)
        acc = 0.0
        for _ in range(n_steps):
            for j in range(n):
                i[j] = current[j]
            for src in range(n):
                s = spikes[src]
                if s > 0.0:
                    start = indptr[src]
                    end = indptr[src + 1]
                    for e in range(start, end):
                        i[indices[e]] += csr_w[e] * s
            for j in range(n):
                vj = i[j]
                if vj >= thresh[j]:
                    spikes[j] = 1.0
                    v[j] = 0.0
                    acc += 1.0
                else:
                    spikes[j] = 0.0
                    v[j] = vj
        return v, spikes, acc

    try:
        tiny = np.zeros(1, dtype=np.float32)
        ip = np.zeros(2, dtype=np.int32)
        kernel(1, tiny, tiny, tiny, tiny + 1.0, ip, np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.float32), tiny)
        kernel_tau0(1, tiny, tiny, tiny + 1.0, ip, np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.float32), tiny)
    except Exception:
        _NUMBA_KERNEL = None
        return None
    _NUMBA_KERNEL = (kernel, kernel_tau0)
    return _NUMBA_KERNEL


def _scipy_csr():
    global _SCIPY_CSR, _SCIPY_TRIED
    if _SCIPY_TRIED:
        return _SCIPY_CSR
    _SCIPY_TRIED = True
    try:
        from scipy.sparse import csr_matrix
    except ImportError:
        _SCIPY_CSR = None
        return None
    _SCIPY_CSR = csr_matrix
    return csr_matrix


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
    indptr: np.ndarray = field(init=False)
    indices: np.ndarray = field(init=False)
    csr_w: np.ndarray = field(init=False)
    _scipy_w: object = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self.v = np.zeros(self.n, dtype=np.float32)
        self.spikes = np.zeros(self.n, dtype=np.float32)
        self._rebuild_csr()

    def _rebuild_csr(self) -> None:
        n = self.n
        if self.src.size == 0:
            self.indptr = np.zeros(n + 1, dtype=np.int32)
            self.indices = np.zeros(0, dtype=np.int32)
            self.csr_w = np.zeros(0, dtype=np.float32)
            self._scipy_w = None
            return
        order = np.argsort(self.src, kind="mergesort")
        src = self.src[order]
        self.indices = self.dst[order].astype(np.int32, copy=False)
        self.csr_w = self.w_e[order].astype(np.float32, copy=False)
        counts = np.bincount(src, minlength=n).astype(np.int32)
        self.indptr = np.zeros(n + 1, dtype=np.int32)
        np.cumsum(counts, out=self.indptr[1:])
        factory = _scipy_csr()
        if factory is not None:
            self._scipy_w = factory(
                (self.csr_w, self.indices, self.indptr),
                shape=(n, n),
            )
        else:
            self._scipy_w = None

    def reset(self) -> None:
        self.v.fill(0.0)
        self.spikes.fill(0.0)

    def _inject(self, current: np.ndarray | None) -> np.ndarray:
        if current is None:
            i = np.zeros(self.n, dtype=np.float32)
        else:
            i = np.array(current, dtype=np.float32, copy=True)
        if self.src.size and self.spikes.any():
            mask = self.spikes[self.src] > 0.0
            if mask.any():
                i += np.bincount(
                    self.dst[mask],
                    weights=self.w_e[mask] * self.spikes[self.src[mask]],
                    minlength=self.n,
                ).astype(np.float32)
        return i

    def step(self, current: np.ndarray | None = None) -> np.ndarray:
        i = self._inject(current)
        self.v = self.tau * self.v + i
        self.spikes = (self.v >= self.thresh).astype(np.float32)
        self.v = self.v * (1.0 - self.spikes)
        return self.spikes

    def step_n(self, n: int, current: np.ndarray | None = None) -> float:
        """n LIF steps. Same equation as step. Returns mean spikes/step."""
        if n <= 0:
            return 0.0
        cur = np.zeros(self.n, dtype=np.float32) if current is None else np.asarray(current, dtype=np.float32)
        kernels = _numba_step_n()
        if kernels is not None:
            kernel, kernel_tau0 = kernels
            if np.all(self.tau == 0.0):
                v, spikes, acc = kernel_tau0(
                    int(n),
                    self.v,
                    self.spikes,
                    self.thresh,
                    self.indptr,
                    self.indices,
                    self.csr_w,
                    cur,
                )
            else:
                v, spikes, acc = kernel(
                    int(n),
                    self.v,
                    self.spikes,
                    self.tau,
                    self.thresh,
                    self.indptr,
                    self.indices,
                    self.csr_w,
                    cur,
                )
            self.v = v
            self.spikes = spikes
            return float(acc) / float(n)
        if self._scipy_w is not None:
            v = self.v
            spikes = self.spikes
            tau = self.tau
            thresh = self.thresh
            w = self._scipy_w
            acc = 0.0
            for _ in range(n):
                i = cur + w.dot(spikes)
                v = tau * v + i
                spikes = (v >= thresh).astype(np.float32)
                v = v * (1.0 - spikes)
                acc += float(spikes.sum())
            self.v = v
            self.spikes = spikes
            return acc / float(n)
        acc = 0.0
        for _ in range(n):
            s = self.step(cur)
            acc += float(s.sum())
        return acc / float(n)

    def zero_module(self, name: str) -> None:
        """Ablation: drop edges into or out of that module."""
        dead = {i for i, m in enumerate(self.module) if m == name}
        if not dead:
            return
        keep = [k for k in range(self.src.size) if int(self.src[k]) not in dead and int(self.dst[k]) not in dead]
        self.src = self.src[keep]
        self.dst = self.dst[keep]
        self.w_e = self.w_e[keep]
        self._rebuild_csr()

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
