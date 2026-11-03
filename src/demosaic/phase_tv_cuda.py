"""Bounded CUDA-graph ADMM in float64, matching the NumPy reference.

Only a local two-component phasor and its weights persist on CUDA. The scalar
check every eight steps uses the same objective and stopping rule as the CPU.
"""

from functools import lru_cache
from threading import Lock

import numpy as np
import torch


class _CudaTV:
    def __init__(self, shape, device="cuda"):
        self.device = torch.device(device)
        self.shape = shape
        self.lock = Lock()
        h, w = shape
        kw = {"device": self.device, "dtype": torch.float64}
        self.values = torch.zeros((2, h, w), **kw)
        self.weight = torch.ones((h, w), **kw)
        self.u = torch.zeros_like(self.values)
        self.d = torch.zeros((2, 2, h, w), **kw)
        self.b = torch.zeros_like(self.d)
        self.scale = torch.ones((), **kw)
        self.gap = torch.zeros((), **kw)
        fy = 2 - 2 * np.cos(2 * np.pi * np.arange(2 * h) / (2 * h))
        fx = 2 - 2 * np.cos(2 * np.pi * np.arange(2 * w) / (2 * w))
        self.den = torch.from_numpy(1 + 16 * (fy[:, None] + fx[None, :])).to(self.device)
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
            self.u.copy_(self.solve(self.values - 16 * self.div(self.d - self.b)))
            g = self.grad(self.u)
            q = g + self.b
            length = torch.sqrt(torch.sum(q * q, dim=(0, 1)))
            self.d.copy_(
                q * torch.clamp(1 - self.weight / (16 * length.clamp_min(1e-32)), min=0)[None, None]
            )
            self.b.add_(g - self.d)
        dual = 16 * self.b
        div = self.div(dual)
        primal = 0.5 * torch.sum((self.u - self.values) ** 2) + torch.sum(
            self.weight * torch.sqrt(torch.sum(g * g, dim=(0, 1)))
        )
        lower = -0.5 * torch.sum(div**2) - torch.sum(self.values * div)
        self.gap.copy_((primal - lower) / self.scale)

    def __call__(self, values, weight, iterations=1024):
        with self.lock, torch.inference_mode(), torch.cuda.device(self.device):
            self.values.copy_(
                torch.from_numpy(np.array(values, dtype=np.float64, order="C", copy=True))
            )
            self.weight.copy_(
                torch.from_numpy(np.array(weight, dtype=np.float64, order="C", copy=True))
            )
            self.d.copy_(self.grad(self.values))
            self.b.zero_()
            scale = max(float(np.sum(values**2)) * 0.5, 1e-32)
            self.scale.fill_(scale)
            n = 0
            gap = None
            while n < iterations:
                count = min(8, iterations - n)
                if count == 8:
                    self.graph.replay()
                else:
                    self.steps(count)
                n += count
                gap = float(self.gap)
                if gap < -1e-9:
                    raise ArithmeticError("InvalidCUDAdualbound")
                gap = max(0, gap)
                if gap < 1e-5:
                    break
            return self.u.cpu().numpy().copy(), {
                "iterations": n,
                "relative_primal_dual_gap": gap,
                "gap_scale": scale,
                "absolute_primal_dual_gap": gap * scale,
                "converged": gap < 1e-5,
                "backend": "cuda-float64-graph8",
            }


@lru_cache(maxsize=2)
def _solver(shape, device):
    return _CudaTV(shape, device)


def denoise_tv_cuda(values, weight, iterations=1024, device="cuda"):
    device = torch.device(device)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise ValueError("CUDA TV requires an available CUDA device")
    if device.index is None:
        device = torch.device("cuda", torch.cuda.current_device())
    return _solver(tuple(values.shape[-2:]), str(device))(values, weight, iterations)


def prepare_tv_cuda(device="cuda"):
    """Warm the fixed packed128 solver before concurrent callers use it."""
    device = torch.device(device)
    if device.index is None:
        device = torch.device("cuda", torch.cuda.current_device())
    return _solver((128, 128), str(device))
