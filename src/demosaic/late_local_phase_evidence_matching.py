"""Local measured-wave features for matching; untrained experimental variant.

Global one-phase FFT selection is retained. Local FP64 affine projections and
coarse-grid interpolation supply features, not reconstructed wires/confidence.
No target or reference enters forward, and no trained-quality claim is made.
"""

import math

import torch
from torch.nn import functional as F

from .late_local_noise_matching import local_noise_features
from .late_phase_evidence_matching import LatePhaseEvidenceMatchingDetail, _green_spectra
from .nonlocal_autograd import enable_sampler_autograd
from .precision import ieee_fp32


def _axis_centers(length, stride, device):
    axis = torch.arange(0, length, stride, device=device)
    if (length - 1) % stride:
        axis = torch.cat((axis, axis.new_tensor([length - 1])))
    return axis


def _geometry(height, width, window, stride, device):
    ay, ax = [_axis_centers(length, stride, device) for length in [height, width]]
    cy, cx = torch.meshgrid(ay, ax, indexing="ij")
    centers = torch.stack((cy.flatten(), cx.flatten()), 1)
    start = (centers - window // 2).clamp_min(0)
    end = torch.minimum(centers + window // 2 + 1, centers.new_tensor([height, width]))
    boxes = torch.stack(
        (start[:, 1], start[:, 0], end[:, 1] - start[:, 1], end[:, 0] - start[:, 0]), 1
    )
    return ay, ax, boxes


def _box_sums(values, boxes):
    integral = F.pad(values.cumsum(-2).cumsum(-1), (1, 0, 1, 0))
    x, y, width, height = boxes.unbind(1)
    return (
        integral[..., y + height, x + width]
        - integral[..., y, x + width]
        - integral[..., y + height, x]
        + integral[..., y, x]
    )


def local_projection_grid(values, variance, bins_yx, boxes):
    """FP64 local coefficients and full trace variance for NxPxHxW planes.

    Each batch item has one selected frequency. All planes in it are measured
    at that fixed bin; no plane can alter the bin through this function.
    """
    values, variance = values.double(), variance.clamp_min(0).double()
    _, _, height, width = values.shape
    device = values.device
    yy, xx = torch.meshgrid(
        torch.arange(height, device=device), torch.arange(width, device=device), indexing="ij"
    )
    by, bx = bins_yx.unbind(1)
    ky = torch.where(by <= (height - 1) // 2, by, by - height)
    kx = torch.where(bx <= (width - 1) // 2, bx, bx - width)
    period = math.lcm(height, width)
    phase = (
        ky[:, None, None] * yy * (period // height) + kx[:, None, None] * xx * (period // width)
    ).remainder(period)
    phase = torch.where(phase > period // 2, phase - period, phase)
    angle = phase.double() * (-2 * math.pi / period)
    carrier = torch.polar(torch.ones_like(angle), angle)
    x, y = xx.double(), yy.double()
    x0, y0, nx, ny = boxes.double().unbind(1)
    cx, cy = x0 + (nx - 1) / 2, y0 + (ny - 1) / 2
    count = nx * ny
    sxx, syy = ny * nx * (nx.square() - 1) / 12, nx * ny * (ny.square() - 1) / 12

    def total(field):
        return _box_sums(field, boxes)

    m0 = total(carrier)
    mx, my = total(carrier * x) - cx * m0, total(carrier * y) - cy * m0
    k0, kx, ky = (v[:, None] for v in [m0 / count, mx / sxx, my / syy])
    centered = values - values[..., :1, :1]
    mean = total(centered)
    coefficient = total(centered * carrier[:, None]) - k0 * mean
    coefficient -= kx * (total(centered * x) - cx * mean)
    coefficient -= ky * (total(centered * y) - cy * mean)
    v0 = total(variance)
    vx0, vy0 = total(variance * x), total(variance * y)
    vx, vy = vx0 - cx * v0, vy0 - cy * v0
    vxx = total(variance * x.square()) - 2 * cx * vx0 + cx.square() * v0
    vyy = total(variance * y.square()) - 2 * cy * vy0 + cy.square() * v0
    vxy = total(variance * x * y) - cx * vy0 - cy * vx0 + cx * cy * v0
    vc = total(variance * carrier[:, None])
    vxc, vyc = (
        total(variance * x * carrier[:, None]) - cx * vc,
        total(variance * y * carrier[:, None]) - cy * vc,
    )
    noise = v0 - 2 * (k0.conj() * vc + kx.conj() * vxc + ky.conj() * vyc).real
    noise += k0.abs().square() * v0 + kx.abs().square() * vxx + ky.abs().square() * vyy
    noise += 2 * (k0.conj() * kx * vx + k0.conj() * ky * vy + kx.conj() * ky * vxy).real
    if bool((noise < -2e-9 * v0.clamp_min(torch.finfo(torch.float64).tiny)).any()):
        raise ArithmeticError("Local projected variance is negative beyond rounding")
    return coefficient, noise.clamp_min(0)


def _interpolate_grid(values, ay, ax, height, width):
    """Linear interpolation at actual integer centers, including the last gap."""

    def indices(axis, length):
        pixels = torch.arange(length, device=axis.device)
        lower = torch.searchsorted(axis, pixels, right=True).sub(1).clamp(0, len(axis) - 2)
        fraction = (pixels - axis[lower]).double() / (axis[lower + 1] - axis[lower])
        return lower, fraction

    ix, fx = indices(ax, width)
    iy, fy = indices(ay, height)
    horizontal = values[..., ix] * (1 - fx) + values[..., ix + 1] * fx
    return horizontal[..., iy, :] * (1 - fy[:, None]) + horizontal[..., iy + 1, :] * fy[:, None]


@torch.no_grad()
def local_phase_evidence_maps(packed, variance, colors, *, peaks=4, window=65, stride=32):
    """Same 10 channels/peak as global evidence, with local coefficient fields.

    At grid centers, coefficients use exact supplied trace-noise units after
    local plane removal. Interpolation of normalized complex coefficients adds
    correlation and changes marginal variance; interpolated powers are features,
    not calibrated SNR. Finite windows/interpolation still spread support.
    """
    if (
        type(window) is not int
        or window < 3
        or window % 2 != 1
        or type(stride) is not int
        or not 1 <= stride <= 512
    ):
        raise ValueError("Expected odd window>=3 and integer stride1..512")
    if (
        packed.ndim != 4
        or packed.shape[1] != 4
        or variance.shape != packed.shape
        or packed.shape[0] < 1
        or min(packed.shape[-2:]) < 8
        or max(packed.shape[-2:]) > 512
    ):
        raise ValueError("Expected matching Nx4xHxW with axes8..512")
    if (
        packed.dtype not in [torch.float32, torch.float64]
        or variance.dtype != packed.dtype
        or variance.device != packed.device
    ):
        raise ValueError("Expected matching FP32/FP64 RAW and variance")
    if (
        type(peaks) is not int
        or not 1 <= peaks <= 8
        or not bool(torch.isfinite(packed).all() & torch.isfinite(variance).all())
    ):
        raise ValueError("Expected finite inputs and peaks1..8")
    batch, _, height, width = packed.shape
    colors = torch.as_tensor(colors, device=packed.device)
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    allowed = torch.tensor(
        [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]], device=packed.device
    )
    if colors.shape != (batch, 4) or not bool((colors[:, None] == allowed).all(-1).any(-1).all()):
        raise ValueError("Expected standard Bayer layouts")
    green = torch.where(colors == 1)[1].reshape(batch, 2)
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        spectrum, global_variance = _green_spectra(packed, variance, green)
        global_variance = global_variance.clamp_min((1 / 65535) ** 2)
        fy = torch.fft.fftfreq(height, device=packed.device, dtype=packed.dtype) / 2
        fx = torch.fft.fftfreq(width, device=packed.device, dtype=packed.dtype) / 2
        native_fy = torch.fft.fftfreq(height, device=packed.device, dtype=torch.float64) / 2
        native_fx = torch.fft.fftfreq(width, device=packed.device, dtype=torch.float64) / 2
        radius = torch.hypot(fy[:, None], fx[None, :])
        eligible = (radius >= 1 / 16) & (radius <= 1 / 3)
        eligible &= (fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None, :] > 0))
        index = green[:, :, None, None].expand(-1, -1, height, width)
        raw, noise = packed.gather(1, index), variance.gather(1, index)
        ay, ax, boxes = _geometry(height, width, window, stride, packed.device)
        yy, xx = torch.meshgrid(
            torch.arange(height, device=packed.device),
            torch.arange(width, device=packed.device),
            indexing="ij",
        )
        period = math.lcm(height, width)
        item = torch.arange(batch, device=packed.device)
        maps, selected_bins, selected_valid, global_powers, local_powers = [], [], [], [], []
        for a, b in [(0, 1), (1, 0)]:
            available = eligible[None].expand(batch, -1, -1).clone()
            power = spectrum[:, a].abs().square() / global_variance[:, a]
            bins, validity, gp, lp = [], [], [], []
            for _ in range(peaks):
                maximum, flat = power.masked_fill(~available, -torch.inf).flatten(1).max(1)
                valid = torch.isfinite(maximum)
                y, x = flat // width, flat % width
                chosen = torch.stack((y, x), -1)
                coefficient, local_variance = local_projection_grid(raw, noise, chosen, boxes)
                z = coefficient / local_variance.clamp_min((1 / 65535) ** 2).sqrt()
                center_power = z.abs().square().reshape(batch, 2, len(ay), len(ax))
                z = _interpolate_grid(z.reshape(batch, 2, len(ay), len(ax)), ay, ax, height, width)
                coefficients = []
                for phase in [a, b]:
                    offset = (
                        2
                        * math.pi
                        * (
                            native_fy[y] * (green[:, phase] // 2)
                            + native_fx[x] * (green[:, phase] % 2)
                        )
                    )
                    coefficients.append(
                        z[:, phase] * torch.polar(torch.ones_like(offset), -offset)[:, None, None]
                    )
                first, second = coefficients
                pa, pb = first.abs().square(), second.abs().square()
                cross = first * second.conj() / ((1 + pa) * (1 + pb)).sqrt()
                ky, kx = (
                    torch.where(y <= (height - 1) // 2, y, y - height),
                    torch.where(x <= (width - 1) // 2, x, x - width),
                )
                phase = (
                    ky[:, None, None] * yy * (period // height)
                    + kx[:, None, None] * xx * (period // width)
                ).remainder(period)
                phase = torch.where(phase > period // 2, phase - period, phase)
                angle = phase.double() * (2 * math.pi / period)
                carrier = torch.polar(torch.ones_like(angle), angle)
                wa, wb = first * carrier, second * carrier
                strength = (pa + pb) / (1 + pa + pb)
                channels = torch.stack(
                    (
                        wa.real.asinh(),
                        wa.imag.asinh(),
                        wb.real.asinh(),
                        wb.imag.asinh(),
                        pa.log1p(),
                        pb.log1p(),
                        cross.real,
                        cross.imag,
                        native_fx[x, None, None] * strength,
                        native_fy[y, None, None] * strength,
                    ),
                    1,
                ).to(packed.dtype)
                maps.append(
                    torch.where(valid[:, None, None, None], channels, torch.zeros_like(channels))
                )
                bins.append(chosen)
                validity.append(valid)
                gp.append(
                    torch.stack(
                        [
                            spectrum[item, p, y, x].abs().square() / global_variance[item, p, y, x]
                            for p in [a, b]
                        ],
                        1,
                    )
                )
                lp.append(center_power[:, [a, b]])
                for cy, cx in [(y, x), ((-y) % height, (-x) % width)]:
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            available[item, (cy + dy) % height, (cx + dx) % width] = False
            selected_bins.append(torch.stack(bins, 1))
            selected_valid.append(torch.stack(validity, 1))
            global_powers.append(torch.stack(gp, 1))
            local_powers.append(torch.stack(lp, 1))
        return torch.cat(maps, 1), {
            "green_phase_indices": green,
            "bin_yx": torch.stack(selected_bins, 1),
            "valid": torch.stack(selected_valid, 1),
            "global_nominal_power": torch.stack(global_powers, 1),
            "local_center_power": torch.stack(local_powers, 1),
            "centers_y": ay,
            "centers_x": ax,
            "boxes_xywh": boxes,
        }


class LateLocalPhaseEvidenceMatchingDetail(LatePhaseEvidenceMatchingDetail):
    """V178's parameter layout with localized measured-wave coordinates.

    The default window/stride were chosen after the training-only support study,
    not blind validation. FP64 moments are a reference implementation; actual
    CUDA cost, training and image quality remain unmeasured.
    """

    def __init__(
        self, width=16, max_search=9.0, evidence_peaks=4, evidence_window=65, evidence_stride=32
    ):
        if (
            type(evidence_window) is not int
            or evidence_window < 3
            or evidence_window % 2 != 1
            or type(evidence_stride) is not int
            or not 1 <= evidence_stride <= 512
        ):
            raise ValueError("Expected odd evidence window>=3 and stride1..512")
        super().__init__(width, max_search, evidence_peaks)
        self.evidence_window, self.evidence_stride = evidence_window, evidence_stride

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                restored = self.frozen(base, packed, variance, colors, wb)
                features, sigma = local_noise_features(restored, packed, variance, colors, wb)
            evaluated = bool(torch.any(sigma > 0))
            evidence_aux = None
            if evaluated:
                evidence, evidence_aux = local_phase_evidence_maps(
                    packed.float(),
                    variance.float(),
                    colors,
                    peaks=self.evidence_peaks,
                    window=self.evidence_window,
                    stride=self.evidence_stride,
                )
                features = features + self.phase_evidence_in(evidence)
                if torch.is_grad_enabled():
                    enable_sampler_autograd()
                correction = F.pixel_shuffle(self.network(features), 2) * sigma
                output = torch.where(sigma > 0, restored + correction, restored)
            else:
                correction, output = torch.zeros_like(restored), restored
            if return_aux:
                return output, {
                    "frozen_output": restored,
                    "correction": correction,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                    "phase_evidence": evidence_aux,
                }
            return output
