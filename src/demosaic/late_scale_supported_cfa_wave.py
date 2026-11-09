"""CFA waves conditioned on physical amplitude/phase agreement across scales.

Experimental head above the trained V195 anchor; no trained-quality claim.
Cross-scale support is descriptive input evidence, not a flat-safety gate.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import mosaic
from .cfa_scale_support import cfa_cross_scale_support
from .late_cfa_innovation_wave import (
    CFAInnovationWaveReadout,
    LateCFAInnovationWaveDetail,
    cfa_innovation_wave_maps,
)
from .late_innovation_wave import innovation_phase_bins
from .late_pooled_phase_wave import LatePooledPhaseWaveDetail
from .late_spatial_context_wave import fixed_bin_support_context
from .precision import ieee_fp32


class ScaleSupportedCFAReadout(CFAInnovationWaveReadout):
    """643 parameters: 36->16->3 real, bounded gates on measured RGB waves.

    V198's 24 old input columns and hidden biases keep the same initialization;
    twelve extra columns start at zero. Final gates also start at zero, so the
    exact anchor is retained. All four head tensors train; no inherited tensor
    does. Extra support inputs cannot synthesize a missing color's wave.
    """

    def __init__(self):
        super().__init__()
        previous = self.context
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(20001).get_state())
            self.context = nn.Conv2d(36, 16, 1, device="cpu")
        with torch.no_grad():
            self.context.weight.zero_()
            self.context.weight[:, :24].copy_(previous.weight)
            self.context.bias.copy_(previous.bias)

    def forward(self, context, waves, bins_yx):
        if (
            context.ndim != 5
            or context.shape[0] < 1
            or context.shape[1] not in range(2, 17, 2)
            or context.shape[2] != 36
            or min(context.shape[-2:]) < 8
            or max(context.shape[-2:]) > 512
            or context.dtype not in (torch.float32, torch.float64)
            or not bool(torch.isfinite(context).all())
        ):
            raise ValueError("Expected finite FP32/FP64 Nx(2*peaks)x36xHxW context, axes8..512")
        batch, count, _, height, width = context.shape
        if (
            waves.shape != (batch, count, 3, 2, height, width)
            or waves.dtype != context.dtype
            or waves.device != context.device
            or not bool(torch.isfinite(waves).all())
        ):
            raise ValueError("Expected matching finite Nx(2*peaks)x3x2xHxW physical RGB waves")
        if (
            bins_yx.shape != (batch, 2, count // 2, 2)
            or bins_yx.dtype != torch.int64
            or bins_yx.device != context.device
            or not bool(((bins_yx >= 0) & (bins_yx < bins_yx.new_tensor([height, width]))).all())
        ):
            raise ValueError("Expected matching integer Nx2xpeaksx2 FFT bins")
        with torch.autocast(context.device.type, enabled=False), ieee_fp32():
            gates = self.gates(F.silu(self.context(context.flatten(0, 1)))).tanh()
            gates = gates.reshape(batch, count, 3, height, width)
            real, imag = (v * gates for v in waves.unbind(3))
            y, x = bins_yx.reshape(batch, count, 2).unbind(-1)
            ky = torch.where(y <= (height - 1) // 2, y, y - height)
            kx = torch.where(x <= (width - 1) // 2, x, x - width)
            offsets = context.new_tensor([[0, 0], [0, 1], [1, 0], [1, 1]]).double()
            angle = math.pi * (
                ky.double()[..., None] * offsets[:, 0] / height
                + kx.double()[..., None] * offsets[:, 1] / width
            )
            cosine, sine = [
                f(angle).to(context.dtype)[:, :, None, :, None, None]
                for f in (torch.cos, torch.sin)
            ]
            native = (real[:, :, :, None] * cosine - imag[:, :, :, None] * sine).sum(1)
            return F.pixel_shuffle(native.flatten(1, 2), 2)


class LateScaleSupportedCFAWaveDetail(LateCFAInnovationWaveDetail):
    """193 frozen V195 tensors plus four fresh scale-supported head tensors.

    Selection, physical synthesis basis, within-scale contexts and the anchor
    match V198. Twelve cross-scale coordinates and 192 parameters are added.
    This combined change requires trained quality comparison; neither bounded
    gates nor nominal covariance establishes false-detail safety.
    """

    def __init__(self, **config):
        super().__init__(**config)
        if not self.evidence_window > self.support_windows[0] > self.support_windows[1]:
            raise ValueError("Scale support requires strictly decreasing large/small windows")
        self.cfa_readout = ScaleSupportedCFAReadout()
        self.train()

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                # Call the retained V195 anchor directly: no V198 head forward.
                anchor, anchor_aux = LatePooledPhaseWaveDetail.forward(
                    self, base, packed, variance, colors, wb, return_aux=True
                )
                sigma = anchor_aux["sigma"]
                evaluated = bool(torch.any(sigma > 0))
                field = selection = evidence = support = context = waves = scale_aux = None
                if evaluated:
                    field = packed.float() - mosaic(anchor.float(), colors)
                    bins, valid, selection = innovation_phase_bins(
                        field, variance.float(), colors, peaks=self.evidence_peaks, lower=self.lower
                    )
                    large, waves, evidence = cfa_innovation_wave_maps(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        window=self.evidence_window,
                        stride=self.evidence_stride,
                    )
                    small, support = fixed_bin_support_context(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        windows=self.support_windows,
                        stride=self.support_stride,
                    )
                    agreement, scale_aux = cfa_cross_scale_support(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        windows=(self.evidence_window, *self.support_windows),
                        strides=(self.evidence_stride, self.support_stride, self.support_stride),
                    )
                    context = torch.cat((large[:, :, :6], small, large[:, :, 6:], agreement), 2)
            if evaluated:
                wave = self.cfa_readout(context, waves, bins)
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, anchor + wave, anchor)
            else:
                wave, output = torch.zeros_like(anchor), anchor
            if return_aux:
                return output, {
                    "anchor_output": anchor,
                    "anchor_aux": anchor_aux,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                    "measurement_field": field,
                    "wave_selection": selection,
                    "cfa_evidence": evidence,
                    "wave_support": support,
                    "scale_support": scale_aux,
                    "cfa_context": context,
                    "cfa_waves": waves,
                    "wave_correction": wave,
                }
            return output
