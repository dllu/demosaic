"""Reciprocal green-phase prediction selects support for fixed measured waves.

The frequencies, variance floor and initial waves reuse both greens. Reciprocal
prediction is additional evidence, not independent validation or calibrated
uncertainty. This stage can remove weak real texture as well as false structure.
"""

from functools import lru_cache
from threading import Lock

import numpy as np
import torch

from .phase_envelope import local_green_phasor
from .phase_harmonic import native_envelope


def interpolation_weights(fine, coarse):
    """Clamped bilinear knots at the centers of equal-width native cells."""
    locations = (np.arange(fine) + 0.5) / (fine / coarse) - 0.5
    low = np.floor(locations).astype(int)
    mix = locations - low
    weights = np.zeros((fine, coarse))
    np.add.at(weights, (np.arange(fine), low.clip(0, coarse - 1)), 1 - mix)
    np.add.at(weights, (np.arange(fine), (low + 1).clip(0, coarse - 1)), mix)
    return weights


class _MaskSolver:
    """Diagonal primal-dual updates with a feasible dual lower bound."""

    def __init__(self, shape, coarse, device):
        self.lock = Lock()
        self.device = torch.device(device)
        kw = {"device": self.device, "dtype": torch.float64}
        self.t = torch.zeros(shape, **kw)
        self.r = torch.zeros(shape[-2:], **kw)
        self.u = torch.ones((shape[0], coarse, coarse), **kw)
        self.v = self.u.clone()
        self.p = torch.zeros((2, *self.u.shape), **kw)
        self.q = torch.zeros_like(self.r)
        self.w = torch.tensor(interpolation_weights(shape[-1], coarse), **kw)
        self.weight = torch.tensor(0.1, **kw)
        self.area = torch.ones_like(self.u) * 0.001
        self.tau = torch.ones_like(self.u)
        self.sigma = torch.ones_like(self.r)
        self.sigma_gradient = torch.tensor(1.0, **kw)
        if self.device.type == "cuda":
            self.stream = torch.cuda.Stream(device=self.device)
            self.stream.wait_stream(torch.cuda.current_stream(self.device))
            with torch.cuda.stream(self.stream):
                for _ in range(3):
                    self.steps(32)
            self.stream.synchronize()
            self.graph = torch.cuda.CUDAGraph()
            with torch.cuda.graph(self.graph, stream=self.stream):
                self.steps(32)
            torch.cuda.current_stream(self.device).wait_stream(self.stream)
        else:
            self.graph = None

    def expand(self, values):
        return self.w @ values @ self.w.T

    def transpose(self, values):
        return self.w.T @ (self.t * values[None]) @ self.w

    def gradient(self, values):
        result = torch.zeros_like(self.p)
        result[0, :, :-1] = values[:, 1:] - values[:, :-1]
        result[1, :, :, :-1] = values[:, :, 1:] - values[:, :, :-1]
        return result

    def divergence(self, values):
        result = torch.zeros_like(self.u)
        result[:, :-1] += values[0, :, :-1]
        result[:, 1:] -= values[0, :, :-1]
        result[:, :, :-1] += values[1, :, :, :-1]
        result[:, :, 1:] -= values[1, :, :, :-1]
        return result

    def steps(self, count):
        for _ in range(count):
            self.q.copy_(
                (self.q + self.sigma * (torch.sum(self.t * self.expand(self.v), 0) - self.r))
                / (1 + self.sigma)
            )
            dual = self.p + self.sigma_gradient * self.weight * self.gradient(self.v)
            self.p.copy_(
                dual
                / torch.maximum(torch.ones_like(self.u), torch.sqrt(torch.sum(dual * dual, 0)))[
                    None
                ]
            )
            old = self.u.clone()
            self.u.copy_(
                torch.clamp(
                    self.u
                    - self.tau
                    * (self.transpose(self.q) - self.weight * self.divergence(self.p) + self.area),
                    0,
                    1,
                )
            )
            self.v.copy_(2 * self.u - old)

    def bounds(self):
        residual = torch.sum(self.t * self.expand(self.u), 0) - self.r
        primal = (
            0.5 * torch.sum(residual**2)
            + self.weight * torch.sqrt(torch.sum(self.gradient(self.u) ** 2, 0)).sum()
            + (self.area * self.u).sum()
        )
        stationary = self.transpose(self.q) - self.weight * self.divergence(self.p) + self.area
        lower = (
            -0.5 * torch.sum(self.q * self.q)
            - torch.sum(self.q * self.r)
            + torch.minimum(stationary, torch.zeros_like(stationary)).sum()
        )
        scale = max(float(0.5 * torch.sum(self.t**2)), 1.0)
        gap = float(primal - lower)
        if gap < -1e-8 * scale:
            raise ArithmeticError("Invalid cross-phase mask dual bound")
        return {
            "primal": float(primal),
            "lower": float(lower),
            "absolute_gap": max(gap, 0),
            "relative_gap": max(gap, 0) / scale,
            "gap_scale": scale,
        }

    def solve(self, templates, target, weight, area, iterations):
        with self.lock, torch.inference_mode():
            self.t.copy_(torch.from_numpy(np.ascontiguousarray(templates)))
            self.r.copy_(torch.from_numpy(np.ascontiguousarray(target)))
            self.u.fill_(1)
            self.v.fill_(1)
            self.p.zero_()
            self.q.zero_()
            self.weight.fill_(weight)
            pixel_area = self.w.T @ torch.ones_like(self.r) @ self.w
            self.area.copy_(area * pixel_area[None])
            h, w = self.u.shape[-2:]
            degree = torch.full((h, w), 4.0, device=self.device, dtype=torch.float64)
            degree[0] -= 1
            degree[-1] -= 1
            degree[:, 0] -= 1
            degree[:, -1] -= 1
            column = self.w.T @ torch.abs(self.t) @ self.w
            self.tau.copy_(0.99 / (column + weight * degree[None]).clamp_min(1e-12))
            self.sigma.copy_(0.99 / torch.sum(torch.abs(self.t), 0).clamp_min(1e-12))
            self.sigma_gradient.fill_(0.99 / (2 * weight))
            for n in range(0, iterations, 32):
                if self.graph is not None:
                    self.graph.replay()
                else:
                    self.steps(32)
                info = self.bounds()
                if info["relative_gap"] < 1e-6:
                    break
            info.update(iterations=n + 32, converged=info["relative_gap"] < 1e-6)
            return self.expand(self.u).cpu().numpy().copy(), info


@lru_cache(maxsize=16)
def _solver(shape, coarse, device):
    return _MaskSolver(shape, coarse, device)


def fit_masks(
    templates, target, *, weight=0.5, area=1 / 1610, coarse=32, iterations=8192, device="cpu"
):
    """Fit bounded masks jointly against fixed whitened reciprocal templates.

    Minimize .5||sum(t*P(m))-target||² + weight*sum(norm(grad(m)))
    + area*sum(P(m)), with 0<=m<=1. P is clamped bilinear interpolation.
    The numerical gap conditions on these fixed data, not their noisy selection.
    """
    templates, target = [np.asarray(a, np.float64) for a in (templates, target)]
    if (
        templates.ndim != 3
        or templates.shape[0] < 1
        or templates.shape[1] != templates.shape[2]
        or min(templates.shape[1:]) < 2
        or target.shape != templates.shape[1:]
        or not np.isfinite(templates).all()
        or not np.isfinite(target).all()
    ):
        raise ValueError("Require finite KxNxN templates and matching NxN target")
    if (
        not np.isfinite([weight, area]).all()
        or weight <= 0
        or area < 0
        or not isinstance(coarse, (int, np.integer))
        or isinstance(coarse, bool)
        or not 1 <= coarse <= templates.shape[-1]
        or not isinstance(iterations, (int, np.integer))
        or isinstance(iterations, bool)
        or iterations < 32
        or iterations % 32
    ):
        raise ValueError(
            "Require positive TV, nonnegative area, valid grid and 32-step iteration cap"
        )
    device = torch.device(device)
    if device.type not in ("cpu", "cuda"):
        raise ValueError("Mask device must be cpu or cuda")
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise ValueError("CUDA mask fitting requires an available CUDA device")
        if device.index is None:
            device = torch.device("cuda", torch.cuda.current_device())
        with torch.cuda.device(device):
            return _solver(templates.shape, coarse, str(device)).solve(
                templates, target, weight, area, iterations
            )
    return _solver(templates.shape, coarse, str(device)).solve(
        templates, target, weight, area, iterations
    )


def reciprocal_templates(fitted, frequencies):
    """Each green is predicted from the other, using physical CFA positions.

    Per-phase affine RAW backgrounds and sigma32 phasors use only that phase.
    Frequencies, variance floor and wave selection already reused both phases.
    """
    colors = fitted["colors"]
    greens = np.flatnonzero(colors == 1)
    plane = fitted["plane"]
    packed, variance = fitted["packed"], fitted["variance"]
    raw_planes = np.zeros_like(packed)
    window = np.hanning(128)[:, None] * np.hanning(128)[None, :]
    white = np.zeros((256, 256))
    target = np.zeros_like(white)
    for phase in greens:
        weights = window.ravel() / np.sqrt(np.maximum(variance[phase].ravel(), 1e-10))
        design = plane * weights[:, None]
        values = packed[phase].ravel() * weights
        beta = np.linalg.lstsq(design, values, rcond=None)[0]
        raw_planes[phase] = (plane @ beta).reshape(128, 128)
        oy, ox = divmod(int(phase), 2)
        white[oy::2, ox::2] = 1 / np.sqrt(np.maximum(variance[phase], 1e-10))
    yy, xx = np.mgrid[:256, :256]
    templates = np.zeros((len(frequencies), 256, 256))
    for k, (fx, fy) in enumerate(frequencies):
        angle = 2 * np.pi * (fx * xx + fy * yy)
        for phase, other in [tuple(greens), tuple(greens[::-1])]:
            selected = np.zeros(4, int)
            selected[other] = 1
            phasor, _, _ = local_green_phasor(packed, variance, selected, raw_planes, (fx, fy), 32)
            real, imaginary = [native_envelope(v) for v in phasor]
            wave = real * np.cos(angle) + imaginary * np.sin(angle)
            oy, ox = divmod(int(phase), 2)
            templates[k, oy::2, ox::2] = wave[oy::2, ox::2] * white[oy::2, ox::2]
    for phase in greens:
        oy, ox = divmod(int(phase), 2)
        target[oy::2, ox::2] = (packed[phase] - raw_planes[phase]) * white[oy::2, ox::2]
    return templates, target


def cross_phase_masks(fitted, frequencies, *, device="cpu"):
    """Select support at mask>=.5, preserving original RGB wave amplitudes."""
    templates, target = reciprocal_templates(fitted, frequencies)
    masks, solver = fit_masks(templates, target, device=device)
    support = masks >= 0.5
    return support, {
        "method": "reciprocal-green-support-v1",
        "mask_grid": [32, 32],
        "mask_node_spacing_native": 8,
        "interpolation": "Clamped bilinear;actual RAW samples are never enlarged",
        "raw_phasor_sigma_native": 32,
        "TV_weight_coarse": 0.5,
        "area_weight_native": 1 / 1610,
        "support_threshold": 0.5,
        "support_fraction": float(support.mean()),
        "confidence_calibrated": False,
        "solver": solver,
    }


def prepare_cross_cuda(device="cuda", wave_counts=range(1, 13)):
    """Warm graph shapes before concurrent complete-frame jobs."""
    device = torch.device(device)
    if device.index is None:
        device = torch.device("cuda", torch.cuda.current_device())
    with torch.cuda.device(device):
        return [_solver((k, 256, 256), 32, str(device)) for k in wave_counts]
