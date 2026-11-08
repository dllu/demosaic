"""Smaller fixed-bin RAW measurements condition the unchanged large wave basis.

Experimental spatial-support context, not calibrated confidence. No target or
reference enters inference, and all inherited V183 matching tensors stay frozen.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .late_local_noise_matching import local_noise_features
from .late_local_phase_evidence_matching import (
    _geometry,
    _interpolate_grid,
    local_phase_evidence_maps,
    local_projection_grid,
)
from .late_phase_wave_readout import LatePhaseWaveReadoutDetail, PhaseWaveReadout
from .precision import ieee_fp32


@torch.no_grad()
def fixed_bin_support_context(
    packed, variance, colors, bins_yx, valid, *, windows=(33, 17), stride=8
):
    """Six nonoscillating coordinates/scale at the supplied one-phase bins.

    This function never selects a frequency. Each clipped box removes its own
    affine plane, normalizes by propagated trace variance, then interpolates
    complex coefficients at actual centers. Per scale, channels are log1p power
    A/B, bounded signed complex cross evidence, and native fx/fy times strength.
    Windows overlap and reuse the same noise; none is an independent test.
    """
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
        raise ValueError("Expected finite matching FP32/FP64 Nx4xHxW,axes8..512")
    if (
        len(windows) != 2
        or len(set(windows)) != 2
        or any(type(w) is not int or w < 3 or w % 2 != 1 for w in windows)
        or type(stride) is not int
        or not 1 <= stride <= 512
    ):
        raise ValueError("Expected two distinct odd windows>=3 and stride1..512")
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
        raise ValueError(
            "Expected fixed integer Nx2xpeaksx2 FFT bins and matching boolean validity"
        )
    colors = torch.as_tensor(colors, device=packed.device)
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    allowed = torch.tensor(
        [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]], device=packed.device
    )
    if colors.shape != (batch, 4) or not bool((colors[:, None] == allowed).all(-1).any(-1).all()):
        raise ValueError("Expected a standard Bayer layout per image")
    peaks = bins_yx.shape[2]
    green = torch.where(colors == 1)[1].reshape(batch, 2)
    index = green[:, :, None, None].expand(-1, -1, height, width)
    raw, noise = packed.gather(1, index), variance.gather(1, index)
    scales = []
    powers = []
    boxes_by_scale = []
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        native_fy = torch.fft.fftfreq(height, device=packed.device, dtype=torch.float64) / 2
        native_fx = torch.fft.fftfreq(width, device=packed.device, dtype=torch.float64) / 2
        for window in windows:
            ay, ax, boxes = _geometry(height, width, window, stride, packed.device)
            fields = []
            center_powers = []
            for direction, (a, b) in enumerate([(0, 1), (1, 0)]):
                for peak in range(peaks):
                    chosen = bins_yx[:, direction, peak]
                    y, x = chosen.unbind(1)
                    coefficient, local_variance = local_projection_grid(raw, noise, chosen, boxes)
                    z = coefficient / local_variance.clamp_min((1 / 65535) ** 2).sqrt()
                    center_powers.append(
                        z[:, [a, b]].abs().square().reshape(batch, 2, len(ay), len(ax))
                    )
                    z = _interpolate_grid(
                        z.reshape(batch, 2, len(ay), len(ax)), ay, ax, height, width
                    )
                    transported = []
                    for phase in [a, b]:
                        angle = (
                            2
                            * math.pi
                            * (
                                native_fy[y] * (green[:, phase] // 2)
                                + native_fx[x] * (green[:, phase] % 2)
                            )
                        )
                        transported.append(
                            z[:, phase] * torch.polar(torch.ones_like(angle), -angle)[:, None, None]
                        )
                    first, second = transported
                    pa, pb = first.abs().square(), second.abs().square()
                    cross = first * second.conj() / ((1 + pa) * (1 + pb)).sqrt()
                    strength = (pa + pb) / (1 + pa + pb)
                    channels = torch.stack(
                        (
                            pa.log1p(),
                            pb.log1p(),
                            cross.real,
                            cross.imag,
                            native_fx[x, None, None] * strength,
                            native_fy[y, None, None] * strength,
                        ),
                        1,
                    ).to(packed.dtype)
                    fields.append(
                        torch.where(
                            valid[:, direction, peak, None, None, None],
                            channels,
                            torch.zeros_like(channels),
                        )
                    )
            scales.append(torch.stack(fields, 1))
            powers.append(
                torch.stack(center_powers, 1).reshape(batch, 2, peaks, 2, len(ay), len(ax))
            )
            boxes_by_scale.append(boxes)
    return torch.cat(scales, 2), {
        "windows": torch.tensor(windows, device=packed.device),
        "stride": torch.tensor(stride, device=packed.device),
        "bin_yx": bins_yx,
        "valid": valid,
        "green_phase_indices": green,
        "centers_y": ay,
        "centers_x": ax,
        "boxes_xywh": torch.stack(boxes_by_scale),
        "center_power": torch.stack(powers, 1),
    }


class SpatialContextWaveReadout(PhaseWaveReadout):
    """508-parameter readout: old six context weights plus twelve zero inputs.

    Large-window wave synthesis is unchanged. The two smaller scales condition
    mixing only. At construction, the old hidden mapping is preserved exactly
    in parameter space, while all new input weights and the final layer are zero.
    """

    def __init__(self):
        super().__init__()
        old_weight, old_bias = (
            self.context.weight.detach().clone(),
            self.context.bias.detach().clone(),
        )
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(18501).get_state())
            self.context = nn.Conv2d(18, 16, 1, device="cpu")
        with torch.no_grad():
            self.context.weight.zero_()
            self.context.weight[:, :6].copy_(old_weight)
            self.context.bias.copy_(old_bias)

    def forward(self, evidence, bins_yx, support):
        if (
            evidence.ndim != 4
            or evidence.shape[0] < 1
            or evidence.shape[1] % 20
            or not 20 <= evidence.shape[1] <= 160
            or min(evidence.shape[-2:]) < 8
            or max(evidence.shape[-2:]) > 512
            or evidence.dtype not in [torch.float32, torch.float64]
            or not bool(torch.isfinite(evidence).all())
        ):
            raise ValueError("Expected finite FP32/FP64 Nx(20*peaks)xHxW,peaks1..8,axes8..512")
        batch, channels, height, width = evidence.shape
        peaks = channels // 20
        count = 2 * peaks
        if (
            bins_yx.shape != (batch, 2, peaks, 2)
            or bins_yx.dtype != torch.int64
            or bins_yx.device != evidence.device
            or not bool(((bins_yx >= 0) & (bins_yx < bins_yx.new_tensor([height, width]))).all())
        ):
            raise ValueError("Expected same-device integer bins Nx2xpeaksx2 in the packed FFT")
        if (
            support.shape != (batch, count, 12, height, width)
            or support.dtype != evidence.dtype
            or support.device != evidence.device
            or not bool(torch.isfinite(support).all())
        ):
            raise ValueError("Expected finite matching Nx(2*peaks)x12xHxW support context")
        with torch.autocast(evidence.device.type, enabled=False), ieee_fp32():
            fields = evidence.reshape(batch * count, 10, height, width)
            contextual = torch.cat(
                (fields[:, 4:], support.reshape(batch * count, 12, height, width)), 1
            )
            weights = self.mixing(F.silu(self.context(contextual))).reshape(
                batch, count, 3, 4, height, width
            )
            waves = fields[:, :4].sinh().reshape(batch, count, 4, height, width)
            if not bool(torch.isfinite(waves).all()):
                raise ArithmeticError("Inverse-asinh measured wave is not finite")
            ar, ai, br, bi = [v[:, :, None] for v in waves.unbind(2)]
            cr = weights[:, :, :, 0] * ar - weights[:, :, :, 1] * ai
            cr = cr + weights[:, :, :, 2] * br - weights[:, :, :, 3] * bi
            ci = weights[:, :, :, 0] * ai + weights[:, :, :, 1] * ar
            ci = ci + weights[:, :, :, 2] * bi + weights[:, :, :, 3] * br
            y, x = bins_yx.reshape(batch, count, 2).unbind(-1)
            ky = torch.where(y <= (height - 1) // 2, y, y - height)
            kx = torch.where(x <= (width - 1) // 2, x, x - width)
            offsets = evidence.new_tensor([[0, 0], [0, 1], [1, 0], [1, 1]]).double()
            angle = math.pi * (
                ky.double()[..., None] * offsets[:, 0] / height
                + kx.double()[..., None] * offsets[:, 1] / width
            )
            cosine, sine = [
                f(angle).to(evidence.dtype)[:, :, None, :, None, None]
                for f in [torch.cos, torch.sin]
            ]
            native = (cr[:, :, :, None] * cosine - ci[:, :, :, None] * sine).mean(1)
            return F.pixel_shuffle(native.flatten(1, 2), 2)


class LateSpatialContextWaveDetail(LatePhaseWaveReadoutDetail):
    """Frozen V183 matching with a spatially conditioned large-wave readout."""

    def __init__(
        self,
        width=16,
        max_search=9.0,
        evidence_peaks=4,
        evidence_window=65,
        evidence_stride=32,
        support_windows=(33, 17),
        support_stride=8,
    ):
        if (
            len(support_windows) != 2
            or len(set(support_windows)) != 2
            or any(
                type(w) is not int or w < 3 or w % 2 != 1 or w >= evidence_window
                for w in support_windows
            )
            or type(support_stride) is not int
            or not 1 <= support_stride <= 512
        ):
            raise ValueError("Expected two distinct smaller odd support windows and stride1..512")
        super().__init__(width, max_search, evidence_peaks, evidence_window, evidence_stride)
        self.wave_readout = SpatialContextWaveReadout()
        self.support_windows, self.support_stride = tuple(support_windows), support_stride
        self.train()

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                restored = self.frozen(base, packed, variance, colors, wb)
                features, sigma = local_noise_features(restored, packed, variance, colors, wb)
                evaluated = bool(torch.any(sigma > 0))
                evidence_aux = support_aux = None
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
                    inherited_correction = F.pixel_shuffle(self.network(features), 2) * sigma
                    inherited = torch.where(sigma > 0, restored + inherited_correction, restored)
                else:
                    inherited_correction, inherited = torch.zeros_like(restored), restored
            if evaluated:
                support, support_aux = fixed_bin_support_context(
                    packed.float(),
                    variance.float(),
                    colors,
                    evidence_aux["bin_yx"],
                    evidence_aux["valid"],
                    windows=self.support_windows,
                    stride=self.support_stride,
                )
                wave = self.wave_readout(evidence, evidence_aux["bin_yx"], support) * sigma
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, inherited + wave, inherited)
            else:
                wave, output = torch.zeros_like(restored), inherited
                support = None
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
                    "wave_support": support_aux,
                    "wave_support_context": support,
                }
            return output
