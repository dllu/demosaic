"""Bounded complex CFA-phase mixing for a late spectral innovation operator."""

import torch
from torch import nn
from torch.nn import functional as F

from .late_spectral_detail import LateSpectralDetail
from .raw_frequency_features import frequency_descriptor


def bounded_real_image_mixing(matrix):
    """Conjugate frequency pairs and cap a computable induced2-norm bound.

    ||H||2 <= sqrt(||H||1*||H||inf). Shared scalar diagonals with |g|<=1
    are included. This is a per-bin coefficient bound, not a global RGB or
    data-dependent Lipschitz guarantee and not a flat-noise safety theorem.
    """
    size = matrix.shape[-1]
    reverse = (-torch.arange(size, device=matrix.device)) % size
    paired = matrix.index_select(-2, reverse).index_select(-1, reverse).conj()
    matrix = (matrix + paired) * 0.5
    absolute = matrix.abs()
    norm_one = absolute.sum(1).amax(1)
    norm_inf = absolute.sum(2).amax(1)
    # Clamp before sqrt: sqrt(0) followed by a clamp would have a nonfinite
    # derivative at the exact zero initialization, even with zero upstream.
    divisor = (norm_one * norm_inf).clamp_min(1).sqrt()
    return matrix / divisor[:, None, None]


class LateSpectralMatrixDetail(LateSpectralDetail):
    """Same analysis/support as V147;32 real outputs encode a complex4×4 mix.

    All ten common parameter tensors initialize identically to the scalar
    component. The replacement output starts exactly zero, and construction
    preserves global CPU/CUDA RNG state. No target/reference enters forward.
    """

    def __init__(self, max_window=256):
        super().__init__(max_window)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(14801).get_state())
            self.frequency_out = nn.Conv2d(32, 32, 1, bias=False, device="cpu")
            # A frequency-constant imaginary bias cancels under conjugate
            # projection, so only the16 identifiable real biases are stored.
            self.frequency_real_bias = nn.Parameter(torch.zeros(4, 4, device="cpu"))
        nn.init.zeros_(self.frequency_out.weight)

    def frequency_gain(self, observed, innovation, noise, colors):
        descriptor = frequency_descriptor(observed, noise, colors)
        innovation_descriptor = frequency_descriptor(innovation, noise, colors)
        features = torch.cat((descriptor, innovation_descriptor[:, :17]), 1)
        logits = self.frequency_out(F.silu(self.frequency_in(features)))
        values = logits.reshape(len(observed), 4, 4, 2, *observed.shape[-2:])
        real = (values[:, :, :, 0] + self.frequency_real_bias[None, :, :, None, None]).tanh()
        imaginary = values[:, :, :, 1].tanh()
        mixing = bounded_real_image_mixing(torch.complex(real, imaginary))
        observed_power = descriptor[:, :4].sum(1, keepdim=True)
        return mixing * observed_power[:, None] * getattr(self, f"band_{observed.shape[-1]}")

    def apply_frequency_gain(self, gain, innovation):
        return torch.einsum("noihw,nihw->nohw", gain, innovation)
