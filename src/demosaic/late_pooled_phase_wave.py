"""Pool green phases and neighboring frequencies for the V185-sized wave head.

Only the new readout uses pooled selection. Frozen V183 matching keeps its exact
old one-phase evidence. Pooling reuses samples: no phase is a selection holdout,
and nominal powers or selected scores are not calibrated confidence.
"""

import math

import torch
from torch.nn import functional as F

from .late_local_noise_matching import local_noise_features
from .late_local_phase_evidence_matching import (
    _geometry,
    _interpolate_grid,
    local_phase_evidence_maps,
    local_projection_grid,
)
from .late_phase_evidence_matching import _green_spectra
from .late_spatial_context_wave import LateSpatialContextWaveDetail, fixed_bin_support_context
from .precision import ieee_fp32


def _green_layout(packed, variance, colors):
    if (
        packed.ndim != 4
        or packed.shape[0] < 1
        or packed.shape[1] != 4
        or variance.shape != packed.shape
        or min(packed.shape[-2:]) < 8
        or max(packed.shape[-2:]) > 512
        or packed.dtype not in [torch.float32, torch.float64]
        or variance.dtype != packed.dtype
        or variance.device != packed.device
        or not bool(torch.isfinite(packed).all() & torch.isfinite(variance).all())
    ):
        raise ValueError("Expected finite matching FP32/FP64 Nx4xHxW, axes8..512")
    colors = torch.as_tensor(colors, device=packed.device)
    if colors.ndim == 1:
        colors = colors[None].expand(len(packed), -1)
    allowed = colors.new_tensor([[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
    if colors.shape != (len(packed), 4) or not bool(
        (colors[:, None] == allowed).all(-1).any(-1).all()
    ):
        raise ValueError("Expected standard Bayer layouts")
    return torch.where(colors == 1)[1].reshape(len(packed), 2)


@torch.no_grad()
def pooled_phase_bins(packed, variance, colors, *, peaks=4):
    """Choose 2K unique peaks from mean two-phase, 3x3-neighborhood power.

    Exact old Hann/affine spectra and full supplied-noise propagation are used.
    Each pixel's phase power is normalized before equal pooling over two greens
    and nine circular frequency neighbors. Retain old1/16..1/3 native band and
    conjugate3x3 suppression. Alternate ranks between the two phase-order groups
    to distribute strong/weak ranks; these groups are not independent selectors.
    """
    green = _green_layout(packed, variance, colors)
    if type(peaks) is not int or not 1 <= peaks <= 8:
        raise ValueError("Expected peaks1..8")
    batch, _, height, width = packed.shape
    device = packed.device
    with torch.autocast(device.type, enabled=False), ieee_fp32():
        spectrum, noise = _green_spectra(packed, variance, green)
        power = spectrum.abs().square() / noise.clamp_min((1 / 65535) ** 2)
        mean = power.mean(1)
        score = (
            sum(torch.roll(mean, (dy, dx), (-2, -1)) for dy in [-1, 0, 1] for dx in [-1, 0, 1]) / 9
        )
        if not bool(torch.isfinite(score).all()):
            raise ArithmeticError("Pooled spectral score is nonfinite")
        fy, fx = [
            torch.fft.fftfreq(n, device=device, dtype=torch.float64) / 2 for n in [height, width]
        ]
        radius = torch.hypot(fy[:, None], fx[None, :])
        eligible = (
            (radius >= 1 / 16)
            & (radius <= 1 / 3)
            & ((fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None, :] > 0)))
        )
        available = eligible[None].expand(batch, -1, -1).clone()
        item = torch.arange(batch, device=device)
        bins = []
        validity = []
        selected_scores = []
        for _ in range(2 * peaks):
            maximum, flat = score.masked_fill(~available, -torch.inf).flatten(1).max(1)
            valid = torch.isfinite(maximum)
            y, x = flat // width, flat % width
            bins.append(torch.stack((y, x), -1))
            validity.append(valid)
            selected_scores.append(torch.where(valid, maximum, torch.zeros_like(maximum)))
            for cy, cx in [(y, x), ((-y) % height, (-x) % width)]:
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        available[item, (cy + dy) % height, (cx + dx) % width] = False
        bins = torch.stack(bins, 1).reshape(batch, peaks, 2, 2).transpose(1, 2).contiguous()
        valid = torch.stack(validity, 1).reshape(batch, peaks, 2).transpose(1, 2).contiguous()
        scores = (
            torch.stack(selected_scores, 1).reshape(batch, peaks, 2).transpose(1, 2).contiguous()
        )
        phase_powers = []
        for direction, (a, b) in enumerate([(0, 1), (1, 0)]):
            y, x = bins[:, direction].unbind(-1)
            phase_powers.append(torch.stack([power[item[:, None], p, y, x] for p in [a, b]], -1))
        return (
            bins,
            valid,
            {
                "green_phase_indices": green,
                "bin_yx": bins,
                "valid": valid,
                "rank": torch.arange(2 * peaks, device=device)
                .reshape(peaks, 2)
                .T[None]
                .expand(batch, -1, -1),
                "pooled_score": scores,
                "global_nominal_power": torch.stack(phase_powers, 1),
            },
        )


@torch.no_grad()
def fixed_bin_wave_maps(packed, variance, colors, bins_yx, valid, *, window=65, stride=32):
    """The old ten local wave/context channels at supplied rather than selected bins."""
    green = _green_layout(packed, variance, colors)
    batch, _, height, width = packed.shape
    if (
        bins_yx.ndim != 4
        or bins_yx.shape[:2] != (batch, 2)
        or bins_yx.shape[-1] != 2
        or not 1 <= bins_yx.shape[2] <= 8
        or bins_yx.dtype != torch.int64
        or bins_yx.device != packed.device
        or valid.shape != bins_yx.shape[:-1]
        or valid.dtype != torch.bool
        or valid.device != packed.device
        or not bool(((bins_yx >= 0) & (bins_yx < bins_yx.new_tensor([height, width]))).all())
    ):
        raise ValueError("Expected fixed integer Nx2xpeaksx2 bins and boolean validity")
    if (
        type(window) is not int
        or window < 3
        or window % 2 != 1
        or type(stride) is not int
        or not 1 <= stride <= 512
    ):
        raise ValueError("Expected odd window>=3 and stride1..512")
    peaks = bins_yx.shape[2]
    index = green[:, :, None, None].expand(-1, -1, height, width)
    raw, noise = packed.gather(1, index), variance.gather(1, index)
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        ay, ax, boxes = _geometry(height, width, window, stride, packed.device)
        fy, fx = [
            torch.fft.fftfreq(n, device=packed.device, dtype=torch.float64) / 2
            for n in [height, width]
        ]
        yy, xx = torch.meshgrid(
            torch.arange(height, device=packed.device),
            torch.arange(width, device=packed.device),
            indexing="ij",
        )
        period = math.lcm(height, width)
        maps = []
        powers = []
        for direction, (a, b) in enumerate([(0, 1), (1, 0)]):
            for peak in range(peaks):
                chosen = bins_yx[:, direction, peak]
                y, x = chosen.unbind(1)
                coefficient, local_variance = local_projection_grid(raw, noise, chosen, boxes)
                z = coefficient / local_variance.clamp_min((1 / 65535) ** 2).sqrt()
                powers.append(z[:, [a, b]].abs().square().reshape(batch, 2, len(ay), len(ax)))
                z = _interpolate_grid(z.reshape(batch, 2, len(ay), len(ax)), ay, ax, height, width)
                transported = []
                for phase in [a, b]:
                    offset = (
                        2
                        * math.pi
                        * (fy[y] * (green[:, phase] // 2) + fx[x] * (green[:, phase] % 2))
                    )
                    transported.append(
                        z[:, phase] * torch.polar(torch.ones_like(offset), -offset)[:, None, None]
                    )
                first, second = transported
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
                fields = torch.stack(
                    (
                        wa.real.asinh(),
                        wa.imag.asinh(),
                        wb.real.asinh(),
                        wb.imag.asinh(),
                        pa.log1p(),
                        pb.log1p(),
                        cross.real,
                        cross.imag,
                        fx[x, None, None] * strength,
                        fy[y, None, None] * strength,
                    ),
                    1,
                ).to(packed.dtype)
                maps.append(
                    torch.where(
                        valid[:, direction, peak, None, None, None],
                        fields,
                        torch.zeros_like(fields),
                    )
                )
        return torch.cat(maps, 1), {
            "green_phase_indices": green,
            "bin_yx": bins_yx,
            "valid": valid,
            "local_center_power": torch.stack(powers, 1).reshape(
                batch, 2, peaks, 2, len(ay), len(ax)
            ),
            "centers_y": ay,
            "centers_x": ax,
            "boxes_xywh": boxes,
        }


class LatePooledPhaseWaveDetail(LateSpatialContextWaveDetail):
    """Same 508-parameter head and frozen189 state, with pooled head selection."""

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                restored = self.frozen(base, packed, variance, colors, wb)
                features, sigma = local_noise_features(restored, packed, variance, colors, wb)
                evaluated = bool(torch.any(sigma > 0))
                evidence_aux = wave_aux = pool_aux = support_aux = None
                if evaluated:
                    old, evidence_aux = local_phase_evidence_maps(
                        packed.float(),
                        variance.float(),
                        colors,
                        peaks=self.evidence_peaks,
                        window=self.evidence_window,
                        stride=self.evidence_stride,
                    )
                    features = features + self.phase_evidence_in(old)
                    inherited_correction = F.pixel_shuffle(self.network(features), 2) * sigma
                    inherited = torch.where(sigma > 0, restored + inherited_correction, restored)
                else:
                    inherited_correction, inherited = torch.zeros_like(restored), restored
            if evaluated:
                bins, valid, pool_aux = pooled_phase_bins(
                    packed.float(), variance.float(), colors, peaks=self.evidence_peaks
                )
                evidence, wave_aux = fixed_bin_wave_maps(
                    packed.float(),
                    variance.float(),
                    colors,
                    bins,
                    valid,
                    window=self.evidence_window,
                    stride=self.evidence_stride,
                )
                support, support_aux = fixed_bin_support_context(
                    packed.float(),
                    variance.float(),
                    colors,
                    bins,
                    valid,
                    windows=self.support_windows,
                    stride=self.support_stride,
                )
                wave = self.wave_readout(evidence, bins, support) * sigma
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, inherited + wave, inherited)
            else:
                wave, output = torch.zeros_like(restored), inherited
                support = evidence = None
            if return_aux:
                return output, {
                    "frozen_output": restored,
                    "inherited_output": inherited,
                    "inherited_correction": inherited_correction,
                    "wave_correction": wave,
                    "correction": inherited_correction + wave,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                    "phase_evidence": evidence_aux,
                    "wave_selection": pool_aux,
                    "wave_evidence": wave_aux,
                    "wave_evidence_features": evidence,
                    "wave_support": support_aux,
                    "wave_support_context": support,
                }
            return output
