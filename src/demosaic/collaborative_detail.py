"""Research-only cross-phase patch grouping with noise-scaled DCT rejection.

Matching keys omit the value phase. Candidate value patches do not overlap,
so their supplied independent pixel variances add without duplicate samples.
Observed Poisson variance, adaptive matching and parent subtraction still mean
the threshold is not calibrated camera confidence. No target enters this code.
"""

import math

import torch
from torch.nn import functional as F

from .cfa import malvar, mosaic
from .precision import ieee_fp32


def dct8(device, dtype=torch.float32):
    index = torch.arange(8, device=device, dtype=dtype)
    basis = torch.cos(math.pi / 8 * index[:, None] * (index[None] + 0.5)) * 0.5
    basis[0] /= math.sqrt(2)
    return basis


def patch_spectra(patches, basis):
    """Orthonormal coefficients and variance propagation are separate operations."""
    return basis @ patches @ basis.T


def _center(patches):
    # Subtraction first preserves exact cancellation of arbitrary FP32 constants.
    delta = patches - patches[..., :1]
    return delta - delta.mean(-1, keepdim=True)


@torch.inference_mode()
def collaborative_detail(base, packed, variance, colors, *, neighbors=64, alpha=0.01):
    """Return a physical RGB correction and diagnostics for one native context.

    Eight-by-eight packed values at stride8 are matched to stride4 query patches.
    All other-phase centered samples form cosine keys. Each query uniformly
    averages up to64 value patches. An orthonormal DCT of that mean is shrunk by
    max(1-T*variance/coefficient²,0), T=2log(4*Nquery*63/alpha). The same weights
    filter the observed-minus-grouped-parent coefficients. DC is always zero.
    Positive Hann overlap aggregation and fixed Malvar map it to physical RGB.

    The Gaussian union-bound motivation assumes independent known variances and
    keys independent of the value phase. Neither those assumptions nor spatial
    constancy hold generally for real captures. Report actual noisy-flat costs.
    This bounded research operator is not wired into ordinary inference.
    """
    if packed.ndim != 4 or packed.shape[:2] != (1, 4) or variance.shape != packed.shape:
        raise ValueError("Require one four-phase packed RAW and matching variance")
    h, w = packed.shape[-2:]
    if min(h, w) < 16 or h % 8 or w % 8 or h * w > 512**2:
        raise ValueError("Research contexts need packed sizes divisible by8, area<=512²")
    if base.shape != (1, 3, 2 * h, 2 * w):
        raise ValueError("Require matching physical camera-RGB parent")
    if type(neighbors) is not int or not 1 <= neighbors <= 256:
        raise ValueError("Neighbor count must be an integer in[1,256]")
    if isinstance(alpha, bool) or not isinstance(alpha, (float, int)) or not 0 < alpha < 1:
        raise ValueError("Require alpha in(0,1)")
    if colors.shape == (4,):
        colors = colors[None]
    if colors.shape != (1, 4) or colors.dtype != torch.long:
        raise ValueError("Require integer standard Bayer colors")
    allowed = torch.tensor(
        [[0, 1, 1, 2], [1, 0, 2, 1], [1, 2, 0, 1], [2, 1, 1, 0]], device=colors.device
    )
    if not bool((colors[:, None] == allowed).all(-1).any()):
        raise ValueError("Require a standard Bayer color layout")
    if any(v.device != packed.device for v in (base, variance, colors)):
        raise ValueError("All inputs must share one device")
    if any(
        not v.is_floating_point() or not bool(torch.isfinite(v).all())
        for v in (base, packed, variance)
    ) or bool((variance < 0).any()):
        raise ValueError("Require finite floating inputs and nonnegative variance")
    if not bool((variance > 0).any()):
        return torch.zeros_like(base, dtype=torch.float32), {
            "ADC_only_bypass": True,
            "active_coefficients": 0,
        }
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        packed, variance, base = packed.float(), variance.float(), base.float()
        basis = dct8(packed.device)
        padded = F.pad(packed, (4, 4, 4, 4), mode="replicate")
        queries = F.unfold(padded, 8, stride=4).reshape(1, 4, 64, -1).transpose(-1, -2)
        queries = _center(queries)
        nq = queries.shape[-2]
        threshold = 2 * math.log(4 * nq * 63 / alpha)
        returned = torch.zeros((1, 4, nq, 64), device=packed.device)
        active, max_stat, peak_weights = 0, 0.0, 0
        grid_info = []
        qy, qx = torch.meshgrid(
            torch.arange(h // 4 + 1, device=packed.device),
            torch.arange(w // 4 + 1, device=packed.device),
            indexing="ij",
        )
        parent_packed = mosaic(base, colors)
        # Query parity chooses one nonoverlapping candidate grid. Keeping four
        # origins avoids forcing every returned periodic patch to one phase.
        for oy, ox in ((0, 0), (0, 4), (4, 0), (4, 4)):
            qindex = torch.nonzero(
                (((qy * 4 - 4) % 8 == oy) & ((qx * 4 - 4) % 8 == ox)).flatten()
            ).flatten()

            def unfold(value, oy=oy, ox=ox):
                return (
                    F.unfold(value[..., oy:, ox:], 8, stride=8)
                    .reshape(1, 4, 64, -1)
                    .transpose(-1, -2)
                )

            candidates, parent, candidate_vars = map(unfold, (packed, parent_packed, variance))
            n = candidates.shape[-2]
            k = min(neighbors, n)
            grid_info.append(
                {
                    "origin_packed_yx": [oy, ox],
                    "candidates": n,
                    "queries": len(qindex),
                    "neighbors": k,
                }
            )
            centered = _center(candidates)
            raw_dct = patch_spectra(centered.reshape(1, 4, n, 8, 8), basis).flatten(-2)
            parent_dct = patch_spectra(_center(parent).reshape(1, 4, n, 8, 8), basis).flatten(-2)
            # Removing the patch mean changes only DC in this basis.
            noise_dct = patch_spectra(
                candidate_vars.reshape(1, 4, n, 8, 8), basis.square()
            ).flatten(-2)
            for phase in range(4):
                other = [v for v in range(4) if v != phase]
                keys = centered[:, other].transpose(1, 2).reshape(1, n, 192)
                query_keys = (
                    queries[:, other][:, :, qindex].transpose(1, 2).reshape(1, len(qindex), 192)
                )
                keys = F.normalize(keys, dim=-1, eps=1e-12)
                query_keys = F.normalize(query_keys, dim=-1, eps=1e-12)
                for start in range(0, len(qindex), 128):
                    end = min(start + 128, len(qindex))
                    scores = query_keys[:, start:end] @ keys.transpose(-1, -2)
                    indices = scores.topk(k, dim=-1, sorted=False).indices[0]
                    observed = raw_dct[0, phase][indices].mean(-2)
                    predicted = parent_dct[0, phase][indices].mean(-2)
                    coefficient_variance = noise_dct[0, phase][indices].sum(-2) / (k * k)
                    statistic = observed.square() / coefficient_variance.clamp_min(1e-20)
                    weight = (1 - threshold / statistic.clamp_min(1e-20)).clamp_min(0)
                    weight[:, 0] = 0
                    residual = weight * (observed - predicted)
                    returned[0, phase, qindex[start:end]] = (
                        basis.T @ residual.reshape(-1, 8, 8) @ basis
                    ).flatten(-2)
                    active += int((weight > 0).sum())
                    max_stat = max(max_stat, float(statistic[:, 1:].max()))
                    peak_weights = max(peak_weights, scores.numel())
        axis = 0.5 - 0.5 * torch.cos(
            2 * math.pi * (torch.arange(8, device=packed.device) + 0.5) / 8
        )
        window = (axis[:, None] * axis[None]).reshape(1, 1, 1, 64)
        values = (returned * window).transpose(-1, -2).reshape(1, 256, nq)
        norm = F.fold(window.reshape(1, 64, 1).expand(1, -1, nq), (h + 8, w + 8), 8, stride=4)
        field = F.fold(values, (h + 8, w + 8), 8, stride=4) / norm.clamp_min(1e-20)
        field = field[..., 4 : 4 + h, 4 : 4 + w]
        correction = malvar(field, colors)
        info = {
            "ADC_only_bypass": False,
            "candidate_grids": grid_info,
            "queries": nq,
            "requested_neighbors": neighbors,
            "threshold": threshold,
            "alpha": alpha,
            "active_coefficients": active,
            "tested_coefficients": 4 * nq * 63,
            "maximum_statistic": max_stat,
            "peak_similarity_numel": peak_weights,
        }
        return correction, info
