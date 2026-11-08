"""A new RAW/innovation wave head above an unchanged trained pooled-wave anchor.

Input residuals are correlated with RAW. Supplied RAW Fourier variances provide
units, not innovation-noise calibration. This prototype establishes no quality
or flat-safety gain; training and native photographic comparisons are required.
"""

import math

import torch

from .cfa import mosaic
from .late_phase_evidence_matching import _green_spectra
from .late_pooled_phase_wave import LatePooledPhaseWaveDetail, _green_layout, fixed_bin_wave_maps
from .late_spatial_context_wave import SpatialContextWaveReadout, fixed_bin_support_context
from .precision import ieee_fp32


@torch.no_grad()
def innovation_phase_bins(field, variance, colors, *, peaks=4, lower=1 / 64):
    """Eight default pooled bins in a configurable native band; no detection gate.

    Same two-green,3x3-power average and conjugate3x3 NMS as V187. Alternate
    ranks go to phase-order groups; neither group is an independent holdout.
    At lower1/16 this preserves the earlier selector's FP32/FP64 arithmetic.
    """
    green = _green_layout(field, variance, colors)
    if type(peaks) is not int or not 1 <= peaks <= 8:
        raise ValueError("Expected peaks1..8")
    if not isinstance(lower, (int, float)) or not math.isfinite(lower) or not 0 < lower < 1 / 3:
        raise ValueError("Expected finite lower native frequency between0 and1/3")
    batch, _, height, width = field.shape
    with torch.autocast(field.device.type, enabled=False), ieee_fp32():
        spectrum, noise = _green_spectra(field, variance, green)
        power = spectrum.abs().square() / noise.clamp_min((1 / 65535) ** 2)
        mean = power.mean(1)
        score = (
            sum(torch.roll(mean, (dy, dx), (-2, -1)) for dy in [-1, 0, 1] for dx in [-1, 0, 1]) / 9
        )
        if not bool(torch.isfinite(score).all()):
            raise ArithmeticError("Nonfinite nominal spectral score")
        fy, fx = [
            torch.fft.fftfreq(n, device=field.device, dtype=torch.float64) / 2
            for n in [height, width]
        ]
        radius = torch.hypot(fy[:, None], fx[None])
        eligible = (
            (radius >= lower)
            & (radius <= 1 / 3)
            & ((fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None] > 0)))
        )
        available = eligible[None].expand(batch, -1, -1).clone()
        item = torch.arange(batch, device=field.device)
        bins, validity, selected_scores = [], [], []
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
        powers = []
        for direction, (a, b) in enumerate([(0, 1), (1, 0)]):
            y, x = bins[:, direction].unbind(-1)
            powers.append(torch.stack([power[item[:, None], p, y, x] for p in [a, b]], -1))
        return (
            bins,
            valid,
            {
                "green_phase_indices": green,
                "bin_yx": bins,
                "valid": valid,
                "rank": torch.arange(2 * peaks, device=field.device)
                .reshape(peaks, 2)
                .T[None]
                .expand(batch, -1, -1),
                "pooled_score": scores,
                "global_nominal_power": torch.stack(powers, 1),
            },
        )


class LateInnovationWaveDetail(LatePooledPhaseWaveDetail):
    """508 fresh parameters above all193 frozen trained-anchor state tensors.

    RAW control and innovation variant share a new zero-output head and band.
    The field changes selection AND measured local wave/support coordinates
    together. Signed innovation can represent missing signal or parent error;
    signal selectivity and flat error must still be measured after training.
    """

    def __init__(self, *, measurement="innovation", lower=1 / 64, **anchor_config):
        if measurement not in ["RAW", "innovation"]:
            raise ValueError("Expected RAW or innovation measurement")
        if not isinstance(lower, (int, float)) or not math.isfinite(lower) or not 0 < lower < 1 / 3:
            raise ValueError("Expected a finite positive lower band below1/3")
        super().__init__(**anchor_config)
        self.requires_grad_(False)
        self.innovation_readout = SpatialContextWaveReadout()
        self.measurement, self.lower = measurement, float(lower)
        self.train()

    def train(self, mode=True):
        # Ancestor constructors call train before the extra head exists.
        super().train(False)
        if hasattr(self, "innovation_readout"):
            self.innovation_readout.train(mode)
        self.training = mode
        return self

    def initialize_anchor(self, state):
        expected = {n for n in self.state_dict() if not n.startswith("innovation_readout.")}
        if set(state) != expected or len(expected) != 193:
            raise ValueError("Expected exact193-tensor trained pooled-wave anchor")
        if (
            self.innovation_readout.mixing.weight.count_nonzero()
            or self.innovation_readout.mixing.bias.count_nonzero()
        ):
            raise ValueError("Anchor initialization requires an unused zero-output new head")
        self.load_state_dict(dict(self.state_dict(), **state), strict=True)
        return self

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                anchor, anchor_aux = super().forward(
                    base, packed, variance, colors, wb, return_aux=True
                )
                sigma = anchor_aux["sigma"]
                evaluated = bool(torch.any(sigma > 0))
                evidence = support = selection = wave_aux = support_aux = field = None
                if evaluated:
                    field = packed.float()
                    if self.measurement == "innovation":
                        field = field - mosaic(anchor.float(), colors)
                    bins, valid, selection = innovation_phase_bins(
                        field, variance.float(), colors, peaks=self.evidence_peaks, lower=self.lower
                    )
                    evidence, wave_aux = fixed_bin_wave_maps(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        window=self.evidence_window,
                        stride=self.evidence_stride,
                    )
                    support, support_aux = fixed_bin_support_context(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        windows=self.support_windows,
                        stride=self.support_stride,
                    )
            if evaluated:
                wave = self.innovation_readout(evidence, bins, support) * sigma
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, anchor + wave, anchor)
            else:
                wave, output = torch.zeros_like(anchor), anchor
            if return_aux:
                return output, {
                    "anchor_output": anchor,
                    "anchor_aux": anchor_aux,
                    "wave_correction": wave,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                    "measurement_field": field,
                    "wave_selection": selection,
                    "wave_evidence": wave_aux,
                    "wave_evidence_features": evidence,
                    "wave_support": support_aux,
                    "wave_support_context": support,
                }
            return output
