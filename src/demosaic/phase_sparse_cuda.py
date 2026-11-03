"""Float64 CUDA-graph ADMM for group-sparse or fixed-support complex fields."""

from functools import lru_cache
from threading import Lock

import numpy as np
import torch


class _CoefficientTV:
    def __init__(self, shape, mode, device):
        self.device = torch.device(device)
        self.shape = shape
        self.mode = mode
        self.lock = Lock()
        h, w = shape
        kw = {"device": self.device, "dtype": torch.float64}
        self.z = torch.zeros((2, h, w), **kw)
        self.weight = torch.ones((h, w), **kw)
        self.extra = torch.ones_like(self.weight)
        self.u = torch.zeros_like(self.z)
        self.v = torch.zeros_like(self.z)
        self.c = torch.zeros_like(self.z)
        self.d = torch.zeros((2, 2, h, w), **kw)
        self.b = torch.zeros_like(self.d)
        self.scale = torch.ones((), **kw)
        self.gap = torch.zeros((), **kw)
        fy = 2 - 2 * np.cos(2 * np.pi * np.arange(2 * h) / (2 * h))
        fx = 2 - 2 * np.cos(2 * np.pi * np.arange(2 * w) / (2 * w))
        self.den = torch.from_numpy(2 + 16 * (fy[:, None] + fx[None, :])).to(self.device)
        self.stream = torch.cuda.Stream(device=self.device)
        self.stream.wait_stream(torch.cuda.current_stream(self.device))
        with torch.cuda.stream(self.stream):
            for _ in range(3):
                self.steps(8)
        self.stream.synchronize()
        self.graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(self.graph, stream=self.stream):
            self.steps(8)
        torch.cuda.current_stream(self.device).wait_stream(self.stream)

    def grad(self, u):
        g = torch.zeros((2, *u.shape), device=u.device, dtype=u.dtype)
        g[0, :, :-1, :] = u[:, 1:, :] - u[:, :-1, :]
        g[1, :, :, :-1] = u[:, :, 1:] - u[:, :, :-1]
        return g

    def div(self, g):
        out = torch.zeros_like(g[0])
        out[:, :-1, :] += g[0, :, :-1, :]
        out[:, 1:, :] -= g[0, :, :-1, :]
        out[:, :, :-1] += g[1, :, :, :-1]
        out[:, :, 1:] -= g[1, :, :, :-1]
        return out

    def solve(self, rhs):
        h, w = self.shape
        even = torch.cat([rhs, rhs.flip((1,))], dim=1)
        even = torch.cat([even, even.flip((2,))], dim=2)
        return torch.fft.ifft2(torch.fft.fft2(even) / self.den).real[:, :h, :w]

    def steps(self, count):
        for _ in range(count):
            self.u.copy_(self.solve(self.z - 16 * self.div(self.d - self.b) + self.v - self.c))
            g = self.grad(self.u)
            q = g + self.b
            length = torch.sqrt(torch.sum(q * q, dim=(0, 1)))
            self.d.copy_(
                q * torch.clamp(1 - self.weight / (16 * length.clamp_min(1e-32)), min=0)[None, None]
            )
            q0 = self.u + self.c
            if self.mode == "group":
                l0 = torch.sqrt(torch.sum(q0 * q0, dim=0))
                self.v.copy_(q0 * torch.clamp(1 - self.extra / l0.clamp_min(1e-32), min=0)[None])
            else:
                self.v.copy_(q0 * self.extra[None])
            self.b.add_(g - self.d)
            self.c.add_(self.u - self.v)
            if self.mode == "mask":
                self.c.mul_(1 - self.extra[None])
        grad = self.grad(self.v)
        a = -self.div(16 * self.b) + self.c
        primal = 0.5 * torch.sum((self.v - self.z) ** 2) + torch.sum(
            self.weight * torch.sqrt(torch.sum(grad * grad, dim=(0, 1)))
        )
        if self.mode == "group":
            primal += torch.sum(self.extra * torch.sqrt(torch.sum(self.v * self.v, dim=0)))
        lower = -0.5 * torch.sum(a * a) + torch.sum(self.z * a)
        self.gap.copy_((primal - lower) / self.scale)

    def __call__(self, z, weight, extra, iterations):
        with self.lock, torch.inference_mode(), torch.cuda.device(self.device):
            self.z.copy_(torch.from_numpy(np.array(z, np.float64, order="C", copy=True)))
            self.weight.copy_(torch.from_numpy(np.array(weight, np.float64, order="C", copy=True)))
            self.extra.copy_(torch.from_numpy(np.array(extra, np.float64, order="C", copy=True)))
            self.v.copy_(self.z)
            self.c.zero_()
            self.d.copy_(self.grad(self.z))
            self.b.zero_()
            scale = max(float(np.sum(np.asarray(z) ** 2)) * 0.5, 1e-32)
            self.scale.fill_(scale)
            n = 0
            while n < iterations:
                count = min(8, iterations - n)
                if count == 8:
                    self.graph.replay()
                else:
                    self.steps(count)
                n += count
                gap = float(self.gap)
                if gap < -1e-9:
                    raise ArithmeticError("Invalid coefficient-TV CUDA dual bound")
                gap = max(gap, 0)
                if gap < 1e-5:
                    break
            value = self.v.cpu().numpy().copy()
            return value, {
                "iterations": n,
                "relative_primal_dual_gap": gap,
                "absolute_primal_dual_gap": gap * scale,
                "gap_scale": scale,
                "converged": gap < 1e-5,
                "zero_coefficients_fraction": float(np.mean(np.all(value == 0, axis=0))),
                "backend": "cuda-float64-graph8",
            }


@lru_cache(maxsize=4)
def _solver(shape, mode, device):
    return _CoefficientTV(shape, mode, device)


def coefficient_tv_cuda(values, weight, extra, mode, iterations, device):
    device = torch.device(device)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise ValueError("CUDA coefficient TV requires an available CUDA device")
    if device.index is None:
        device = torch.device("cuda", torch.cuda.current_device())
    return _solver(tuple(values.shape[-2:]), mode, str(device))(values, weight, extra, iterations)


def prepare_sparse_cuda(device="cuda"):
    """Warm both native128 coefficient solvers before concurrent frame jobs."""
    device = torch.device(device)
    if device.index is None:
        device = torch.device("cuda", torch.cuda.current_device())
    return [_solver((128, 128), mode, str(device)) for mode in ["group", "mask"]]
