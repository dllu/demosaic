"""Physical cross-scale CFA wave support, not calibrated signal confidence.

Fixed-bin local affine+sinusoid fits provide amplitudes in camera-RGB units.
Nominal independent-RAW covariance describes the linear fit at grid centers.
Overlapping windows, data-dependent selection and a RAW-dependent anchor make
the actual innovation errors correlated. No target/reference is an input.
"""

import math

import torch

from .late_cfa_innovation_wave import _carrier, _wave_inverse
from .late_local_phase_evidence_matching import (
    _box_sums,
    _geometry,
    _interpolate_grid,
    local_projection_grid,
)
from .late_pooled_phase_wave import _green_layout
from .precision import ieee_fp32

AMPLITUDE_FLOOR_SQUARED = (1 / 65535) ** 2


def _validate_grid(values, variance, bins_yx, boxes):
    if (
        values.ndim != 4
        or values.shape[0] < 1
        or values.shape[1] < 1
        or min(values.shape[-2:]) < 8
        or max(values.shape[-2:]) > 512
        or values.dtype not in (torch.float32, torch.float64)
        or variance.shape != values.shape
        or variance.dtype != values.dtype
        or variance.device != values.device
        or not bool(torch.isfinite(values).all() & torch.isfinite(variance).all())
        or bool((variance < 0).any())
    ):
        raise ValueError(
            "Expected finite matching NxPxHxW FP32/FP64 values and nonnegative variance"
        )
    n, _, h, w = values.shape
    if (
        bins_yx.shape != (n, 2)
        or bins_yx.dtype != torch.int64
        or bins_yx.device != values.device
        or not bool(((bins_yx >= 0) & (bins_yx < bins_yx.new_tensor([h, w]))).all())
        or boxes.ndim != 2
        or boxes.shape[0] < 1
        or boxes.shape[1] != 4
        or boxes.dtype != torch.int64
        or boxes.device != values.device
    ):
        raise ValueError("Expected valid Nx2 int64 FFT bins and Lx4 int64 xywh boxes")
    x, y, nx, ny = boxes.unbind(1)
    if not bool(
        ((x >= 0) & (y >= 0) & (nx >= 2) & (ny >= 2) & (x + nx <= w) & (y + ny <= h)).all()
    ):
        raise ValueError("Boxes must fit inside the field with at least two rows and columns")


@torch.no_grad()
def local_amplitude_grid(values, variance, bins_yx, boxes):
    """FP64 complex amplitudes and 2x2 nominal covariance at each box.

    Let Q be the two real columns of exp(-i theta) after affine projection,
    G=Q^T Q and H=Q^T diag(v_RAW) Q. The fitted amplitude is G^dagger Q^T y;
    its nominal covariance is G^dagger H G^dagger. Basis order is cos,-sin.
    No isotropic/trace-only approximation is used for the LS covariance.
    Rank uses V198's numerical cutoff, 1e-10*box area, not an SNR threshold.

    Q's complex pseudo-variance sum(v*q*q), together with its trace variance,
    gives every entry of H by integral moments without materializing patches.
    """
    _validate_grid(values, variance, bins_yx, boxes)
    _, _, height, width = values.shape
    with torch.autocast(values.device.type, enabled=False), ieee_fp32():
        coefficient, projected_trace = local_projection_grid(values, variance, bins_yx, boxes)
        inverse, rank = _wave_inverse(height, width, bins_yx, boxes)
        rhs = torch.stack((coefficient.real, coefficient.imag), -1)
        amplitude = (inverse[:, None] @ rhs[..., None]).squeeze(-1)
        amplitude = torch.complex(amplitude[..., 0], amplitude[..., 1])
        carrier, _, _, yy, xx = _carrier(height, width, bins_yx)
        carrier = carrier.conj()[:, None]
        x, y, noise = xx.double(), yy.double(), variance.double()
        x0, y0, nx, ny = boxes.double().unbind(1)
        cx, cy, area = x0 + (nx - 1) / 2, y0 + (ny - 1) / 2, nx * ny

        def total(a):
            return _box_sums(a, boxes)

        moment = total(carrier)
        k0 = moment / area
        kx = (total(carrier * x) - cx * moment) / (ny * nx * (nx.square() - 1) / 12)
        ky = (total(carrier * y) - cy * moment) / (nx * ny * (ny.square() - 1) / 12)
        v0 = total(noise)
        vx0, vy0 = total(noise * x), total(noise * y)
        vx, vy = vx0 - cx * v0, vy0 - cy * v0
        vxx = total(noise * x.square()) - 2 * cx * vx0 + cx.square() * v0
        vyy = total(noise * y.square()) - 2 * cy * vy0 + cy.square() * v0
        vxy = total(noise * x * y) - cx * vy0 - cy * vx0 + cx * cy * v0
        vc = total(noise * carrier)
        vxc = total(noise * carrier * x) - cx * vc
        vyc = total(noise * carrier * y) - cy * vc
        pseudo = total(noise * carrier.square()) - 2 * (k0 * vc + kx * vxc + ky * vyc)
        pseudo += k0.square() * v0 + kx.square() * vxx + ky.square() * vyy
        pseudo += 2 * (k0 * kx * vx + k0 * ky * vy + kx * ky * vxy)
        rr, ii, ri = (
            (projected_trace + pseudo.real) / 2,
            (projected_trace - pseudo.real) / 2,
            pseudo.imag / 2,
        )
        h = torch.stack((rr, ri, ri, ii), -1).reshape(*rr.shape, 2, 2)
        # Moment subtraction can produce tiny negative eigenvalues at singular
        # bins. Reject material negatives; remove only floating-point residue.
        eigenvalues, vectors = torch.linalg.eigh(h)
        if bool(
            (eigenvalues < -2e-8 * v0[..., None].clamp_min(torch.finfo(torch.float64).tiny)).any()
        ):
            raise ArithmeticError("Projected nominal covariance is not positive semidefinite")
        h = (vectors * eigenvalues.clamp_min(0)[..., None, :]) @ vectors.transpose(-2, -1)
        covariance = inverse[:, None] @ h @ inverse[:, None]
        covariance = (covariance + covariance.transpose(-2, -1)) / 2
        return amplitude, covariance, rank


def scale_agreement(large, small, large_trace, small_trace):
    """Bounded complex amplitude/phase agreement in physical units.

    2*A_L*conj(A_S) / (|A_L|^2+|A_S|^2+nu_L+nu_S+floor).
    Equal strong waves approach +1; opposite phases approach -1. Noise powers
    attenuate vanishing/weak amplitudes. This is not a probability, independent
    holdout test or estimated covariance of the difference between scales.
    """
    if (
        large.shape != small.shape
        or large.dtype not in (torch.complex64, torch.complex128)
        or small.dtype != large.dtype
        or large.device != small.device
        or large_trace.shape != large.shape
        or small_trace.shape != large.shape
        or large_trace.device != large.device
        or small_trace.device != large.device
        or large_trace.dtype != large.real.dtype
        or small_trace.dtype != large.real.dtype
        or not bool(torch.isfinite(large).all() & torch.isfinite(small).all())
        or not bool(torch.isfinite(large_trace).all() & torch.isfinite(small_trace).all())
        or bool((large_trace < 0).any() | (small_trace < 0).any())
    ):
        raise ValueError("Expected matching finite complex amplitudes and nonnegative real traces")
    denominator = large.abs().square() + small.abs().square()
    denominator = denominator + large_trace + small_trace + AMPLITUDE_FLOOR_SQUARED
    return 2 * large * small.conj() / denominator


@torch.no_grad()
def cfa_scale_amplitudes(field, variance, colors, bins_yx, valid, *, window=65, stride=8):
    """Canonical physical RGB amplitudes plus an interpolated nominal bound.

    Each phase is fitted independently and transported to canonical native
    phase. Green averages its two amplitudes; under the nominal independent-RAW
    model its center covariance trace is (trace_G1+trace_G2)/4. At pixels between
    centers, (sum_i w_i sqrt(trace_i))^2 bounds the linear interpolation's trace
    by Cauchy-Schwarz even for overlapping windows. It is deliberately not the
    exact interpolated variance. This bound concerns the fixed linear RAW-noise
    model only, and does not account for the correlated anchor or selection.
    """
    green = _green_layout(field, variance, colors)
    n, _, height, width = field.shape
    if (
        bins_yx.ndim != 4
        or bins_yx.shape[:2] != (n, 2)
        or bins_yx.shape[-1] != 2
        or not 1 <= bins_yx.shape[2] <= 8
        or valid.shape != bins_yx.shape[:-1]
        or valid.dtype != torch.bool
        or valid.device != field.device
        or type(window) is not int
        or window < 3
        or window % 2 != 1
        or type(stride) is not int
        or not 1 <= stride <= 512
    ):
        raise ValueError(
            "Expected fixed Nx2xpeaksx2 bins, boolean validity, odd window and stride1..512"
        )
    colors = torch.as_tensor(colors, device=field.device)
    if colors.ndim == 1:
        colors = colors[None].expand(n, -1)
    order = torch.cat(
        (
            torch.where(colors == 0)[1].reshape(n, 1),
            green,
            torch.where(colors == 2)[1].reshape(n, 1),
        ),
        1,
    )
    index = order[:, :, None, None].expand(-1, -1, height, width)
    samples, noise = field.gather(1, index), variance.gather(1, index)
    amplitudes, bounds, center_amplitudes, center_covariances, ranks = [], [], [], [], []
    with torch.autocast(field.device.type, enabled=False), ieee_fp32():
        ay, ax, boxes = _geometry(height, width, window, stride, field.device)
        for chosen, usable in zip(
            bins_yx.flatten(1, 2).unbind(1), valid.flatten(1, 2).unbind(1), strict=True
        ):
            amplitude, covariance, rank = local_amplitude_grid(samples, noise, chosen, boxes)
            _, ky, kx, _, _ = _carrier(height, width, chosen)
            angle = math.pi * (
                ky[:, None].double() * (order // 2) / height
                + kx[:, None].double() * (order % 2) / width
            )
            transport = torch.polar(torch.ones_like(angle), -angle)[:, :, None]
            canonical = amplitude * transport
            rgb = torch.stack(
                (canonical[:, 0], (canonical[:, 1] + canonical[:, 2]) / 2, canonical[:, 3]), 1
            )
            trace = covariance.diagonal(dim1=-2, dim2=-1).sum(-1).clamp_min(0)
            rgb_trace = torch.stack((trace[:, 0], (trace[:, 1] + trace[:, 2]) / 4, trace[:, 3]), 1)
            rgb = _interpolate_grid(rgb.reshape(n, 3, len(ay), len(ax)), ay, ax, height, width)
            bound = _interpolate_grid(
                rgb_trace.sqrt().reshape(n, 3, len(ay), len(ax)), ay, ax, height, width
            ).square()
            mask = usable[:, None, None, None]
            amplitudes.append(torch.where(mask, rgb, 0))
            bounds.append(torch.where(mask, bound, 0))
            center_amplitudes.append(canonical)
            center_covariances.append(covariance)
            ranks.append(rank)
        return (
            torch.stack(amplitudes, 1),
            torch.stack(bounds, 1),
            {
                "canonical_phase_indices": order,
                "centers_y": ay,
                "centers_x": ax,
                "boxes_xywh": boxes,
                "canonical_center_amplitudes": torch.stack(center_amplitudes, 1),
                "nominal_untransported_center_covariance": torch.stack(center_covariances, 1),
                "wave_gram_rank": torch.stack(ranks, 1),
                "bin_yx": bins_yx,
                "valid": valid,
            },
        )


@torch.no_grad()
def cfa_cross_scale_support(
    field, variance, colors, bins_yx, valid, *, windows=(65, 33, 17), strides=(32, 8, 8)
):
    """Twelve coordinates/bin: real/imag RGB agreement of 65 with 33 and 17.

    Geometry is configurable for tests; windows must be strictly decreasing.
    No output image is synthesized and no frequencies are selected here.
    """
    if (
        len(windows) != 3
        or len(strides) != 3
        or any(type(w) is not int or w < 3 or w % 2 != 1 for w in windows)
        or not windows[0] > windows[1] > windows[2]
    ):
        raise ValueError("Expected three strictly decreasing odd support windows")
    measured = [
        cfa_scale_amplitudes(field, variance, colors, bins_yx, valid, window=w, stride=s)
        for w, s in zip(windows, strides, strict=True)
    ]
    large, large_trace, _ = measured[0]
    channels = []
    for small, small_trace, _ in measured[1:]:
        agreement = scale_agreement(large, small, large_trace, small_trace)
        channels.extend((agreement.real, agreement.imag))
    # Each pair contributes RGB real then RGB imaginary coordinates.
    return torch.cat(channels, 2).to(field.dtype), {
        "windows": tuple(windows),
        "strides": tuple(strides),
        "scale_geometry": [m[2] for m in measured],
        "nominal_interpolated_trace_bound": torch.stack([m[1] for m in measured], 2),
    }
