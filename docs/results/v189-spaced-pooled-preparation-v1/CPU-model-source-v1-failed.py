"""Wider pooled spectral suppression at V187's unchanged head/state budget.

Frozen V183 matching retains its original one-phase bins. Only the new wave
readout uses spaced pooled bins; no target or reference enters inference.
"""

import math

import torch
from torch.nn import functional as F

from .late_local_noise_matching import local_noise_features
from .late_local_phase_evidence_matching import local_phase_evidence_maps
from .late_phase_evidence_matching import _green_spectra
from .late_pooled_phase_wave import LatePooledPhaseWaveDetail, _green_layout, fixed_bin_wave_maps
from .late_spatial_context_wave import fixed_bin_support_context
from .precision import ieee_fp32


@torch.no_grad()
def spaced_pooled_phase_bins(packed, variance, colors, *, peaks=4, window=65):
    """Same pooled ranking as V187, with wider conjugate suppression.

    Radius ceil(max packed axis/window) tracks the wave-window frequency scale.
    It changes allocation, not calibrated confidence; both greens affect picks.
    """
    green = _green_layout(packed, variance, colors)
    if type(peaks) is not int or not 1 <= peaks <= 8:
        raise ValueError("Expected peaks1..8")
    batch, _, height, width = packed.shape
    if type(window) is not int or window < 3 or window % 2 != 1:
        raise ValueError("Expected odd wave window>=3")
    radius = math.ceil(max(height, width) / window)
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
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
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
                "suppression_radius": torch.tensor(radius, device=device, dtype=torch.int64),
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


class LateSpacedPooledPhaseWaveDetail(LatePooledPhaseWaveDetail):
    """Same508parameter/193state constructor; only sparse selection radius changes."""

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
                bins, valid, pool_aux = spaced_pooled_phase_bins(
                    packed.float(),
                    variance.float(),
                    colors,
                    peaks=self.evidence_peaks,
                    window=self.evidence_window,
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
