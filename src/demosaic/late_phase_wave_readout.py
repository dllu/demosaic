"""Direct phase-aware readout of input-only local RAW wave measurements.

The completed matching component is frozen. A small shared readout learns only
an added RGB wave residual. This is an experimental architecture, not evidence
of trained quality or noisy-flat safety. Principal-band aliases remain unresolved.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .late_local_noise_matching import local_noise_features
from .late_local_phase_evidence_matching import (
    LateLocalPhaseEvidenceMatchingDetail,
    local_phase_evidence_maps,
)
from .precision import ieee_fp32


class PhaseWaveReadout(nn.Module):
    """Shared contextual mixing of two measured complex waves into camera RGB.

    Six nonoscillating coordinates condition a 6->16->12 pointwise MLP. Its
    twelve outputs are complex mixing weights for two measurements and three
    colors. Mixing precedes explicit native-subpixel phase transport. Every
    selected direction/rank uses the same weights and contributes equally.
    There is no constant RGB output: zero wave coordinates give zero residual,
    even after contextual biases change. No noisy-input safety follows from that
    identity. Coefficients retain V180's interpolated Fourier-noise units.
    """

    def __init__(self):
        super().__init__()
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(18401).get_state())
            self.context = nn.Conv2d(6, 16, 1, device="cpu")
            self.mixing = nn.Conv2d(16, 12, 1, device="cpu")
        nn.init.zeros_(self.mixing.weight)
        nn.init.zeros_(self.mixing.bias)

    def forward(self, evidence, bins_yx):
        if (
            evidence.ndim != 4
            or evidence.shape[0] < 1
            or evidence.shape[1] % 20
            or not 20 <= evidence.shape[1] <= 160
            or min(evidence.shape[-2:]) < 8
            or max(evidence.shape[-2:]) > 512
            or evidence.dtype not in (torch.float32, torch.float64)
            or not bool(torch.isfinite(evidence).all())
        ):
            raise ValueError("Expected finite FP32/FP64 Nx(20*peaks)xHxW,peaks1..8,axes8..512")
        batch, channels, height, width = evidence.shape
        peaks = channels // 20
        if (
            bins_yx.shape != (batch, 2, peaks, 2)
            or bins_yx.dtype != torch.int64
            or bins_yx.device != evidence.device
            or not bool(((bins_yx >= 0) & (bins_yx < bins_yx.new_tensor([height, width]))).all())
        ):
            raise ValueError("Expected same-device integer bins Nx2xpeaksx2 in the packed FFT")
        with torch.autocast(evidence.device.type, enabled=False), ieee_fp32():
            count = 2 * peaks
            fields = evidence.reshape(batch * count, 10, height, width)
            weights = self.mixing(F.silu(self.context(fields[:, 4:])))
            weights = weights.reshape(batch, count, 3, 4, height, width)
            waves = fields[:, :4].sinh().reshape(batch, count, 4, height, width)
            if not bool(torch.isfinite(waves).all()):
                raise ArithmeticError("Inverse-asinh measured wave is not finite")
            ar, ai, br, bi = [v[:, :, None] for v in waves.unbind(2)]
            cr = weights[:, :, :, 0] * ar - weights[:, :, :, 1] * ai
            cr = cr + weights[:, :, :, 2] * br - weights[:, :, :, 3] * bi
            ci = weights[:, :, :, 0] * ai + weights[:, :, :, 1] * ar
            ci = ci + weights[:, :, :, 2] * bi + weights[:, :, :, 3] * br
            bins = bins_yx.reshape(batch, count, 2)
            y, x = bins.unbind(-1)
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


class LatePhaseWaveReadoutDetail(LateLocalPhaseEvidenceMatchingDetail):
    """Frozen local matching plus 316 trainable phase-aware readout parameters.

    Loading a completed local-evidence export preserves all its tensors. Only
    the new readout trains; its final layer starts at zero. Native local noise
    RMS scales the new residual, with the inherited exact zero-variance routing.
    """

    def __init__(
        self, width=16, max_search=9.0, evidence_peaks=4, evidence_window=65, evidence_stride=32
    ):
        super().__init__(width, max_search, evidence_peaks, evidence_window, evidence_stride)
        self.requires_grad_(False)
        self.wave_readout = PhaseWaveReadout()
        self.train()

    def train(self, mode=True):
        super().train(mode)
        self.network.eval()
        self.phase_evidence_in.eval()
        return self

    def initialize_from_evidence(self, state):
        expected = {name for name in self.state_dict() if not name.startswith("wave_readout.")}
        if set(state) != expected:
            raise ValueError("Expected exactly the completed local-evidence component state")
        if (
            self.wave_readout.mixing.weight.count_nonzero()
            or self.wave_readout.mixing.bias.count_nonzero()
        ):
            raise ValueError("Evidence initializer requires a zero readout final layer")
        self.load_state_dict(dict(self.state_dict(), **state), strict=True)
        return self

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
                    inherited_correction = F.pixel_shuffle(self.network(features), 2) * sigma
                    inherited = torch.where(sigma > 0, restored + inherited_correction, restored)
                else:
                    inherited_correction, inherited = torch.zeros_like(restored), restored
            if evaluated:
                wave = self.wave_readout(evidence, evidence_aux["bin_yx"]) * sigma
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, inherited + wave, inherited)
            else:
                wave, output = torch.zeros_like(restored), inherited
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
                }
            return output
