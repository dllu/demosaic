"""Known CFA transport and local green evidence for late spectral estimation."""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .late_spectral_matrix import LateSpectralMatrixDetail, bounded_real_image_mixing
from .raw_frequency_features import frequency_descriptor, hermitian_projection


def phase_transport(size):
    """Align packed Fourier coefficients to native pixel origin, on CPU.

    Native site positions are(0,0),(0,1),(1,0),(1,1). Packed frequency is twice
    native frequency, hence the pi phase ramp. Fractional shifts at packed
    Nyquist need not preserve real-image symmetry; the existing output band
    is zero there and native matrix conjugate projection remains explicit.
    """
    f = torch.fft.fftfreq(size, device="cpu", dtype=torch.float32)
    dy = torch.tensor([0, 0, 1, 1], device="cpu")[:, None, None]
    dx = torch.tensor([0, 1, 0, 1], device="cpu")[:, None, None]
    angle = -math.pi * (dy * f[None, :, None] + dx * f[None, None, :])
    return torch.polar(torch.ones_like(angle), angle)[None]


def basis_rotation(colors, dtype):
    """Real orthogonal rotation from physical slots to R,Gsum,Gdiff,B."""
    green = colors == 1
    position = green.cumsum(1)
    first, second = green & (position == 1), green & (position == 2)
    return torch.stack(
        (
            colors == 0,
            green / math.sqrt(2),
            (first.float() - second.float()) / math.sqrt(2),
            colors == 2,
        ),
        1,
    ).to(dtype)


def to_coherent(values, colors, transport):
    rotation = basis_rotation(colors, values.dtype)
    return torch.einsum("nbp,nphw->nbhw", rotation, values * transport)


def matrix_to_native(matrix, colors, transport):
    rotation = basis_rotation(colors, matrix.dtype)
    value = torch.einsum("nbchw,ncp->nbphw", matrix, rotation)
    value = torch.einsum("nbq,nbphw->nqphw", rotation, value)
    return value * transport.conj()[:, :, None] * transport[:, None]


def separable_box(values, size):
    pad = size // 2
    value = F.avg_pool2d(F.pad(values, (0, 0, pad, pad), mode="replicate"), (size, 1), stride=1)
    return F.avg_pool2d(F.pad(value, (pad, pad, 0, 0), mode="replicate"), (1, size), stride=1)


class LateSpectralAlignedMatrixDetail(LateSpectralMatrixDetail):
    """V148 parameter count/family; estimate the matrix in coherent coordinates.

    The final conjugate/norm projection is in physical CFA coordinates. This
    keeps the native per-bin bound rather than assuming its1/inf gauge is
    invariant to a basis rotation. All12 initial tensors match V148 exactly.
    """

    def __init__(self, max_window=256):
        super().__init__(max_window)
        size = 4
        while size <= max_window:
            self.register_buffer(f"transport_{size}", phase_transport(size), persistent=False)
            size *= 2

    def frequency_gain(self, observed, innovation, noise, colors):
        size = observed.shape[-1]
        transport = getattr(self, f"transport_{size}")
        basis_observed = to_coherent(observed, colors, transport)
        basis_innovation = to_coherent(innovation, colors, transport)
        rotation = basis_rotation(colors, noise.dtype)
        basis_noise = torch.einsum("nbp,np->nb", rotation.square(), noise)
        canonical = colors.new_tensor([0, 1, 1, 2])[None].expand(len(colors), -1)
        descriptor = frequency_descriptor(basis_observed, basis_noise, canonical)
        innovation_descriptor = frequency_descriptor(basis_innovation, basis_noise, canonical)
        features = torch.cat((descriptor, innovation_descriptor[:, :17]), 1)
        logits = self.frequency_out(F.silu(self.frequency_in(features)))
        values = logits.reshape(len(observed), 4, 4, 2, size, size)
        real = (values[:, :, :, 0] + self.frequency_real_bias[None, :, :, None, None]).tanh()
        imaginary = values[:, :, :, 1].tanh()
        native = matrix_to_native(torch.complex(real, imaginary), colors, transport)
        mixing = bounded_real_image_mixing(native)
        # Preserve the exact original observed-power calculation/units.
        observed_power = frequency_descriptor(observed, noise, colors)[:, :4].sum(1, keepdim=True)
        return mixing * observed_power[:, None] * getattr(self, f"band_{size}")


class LateSpectralCoherentDetail(LateSpectralAlignedMatrixDetail):
    """Append9 target-free common/difference energy features to local support.

    Three packed scales9/33/129 provide local and wider evidence. The signed
    common-minus-difference contrast is a feature, not a calibrated signal
    probability or a guarantee on noisy flats. The same measured-RAW band and
    fixed STFT geometry construct both fields. Parent/target pixels never enter
    these additional features. All existing weights are preserved initially;
    appended local-input weights are zero. Both estimator and support train.
    """

    def __init__(self, max_window=256):
        super().__init__(max_window)
        previous = self.local_in
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(14901).get_state())
            self.local_in = nn.Conv2d(37, 24, 3, padding=1, device="cpu")
        with torch.no_grad():
            self.local_in.weight.zero_()
            self.local_in.weight[:, :28].copy_(previous.weight)
            self.local_in.bias.copy_(previous.bias)

    def local_features(self, packed, parent, variance, proposal, colors, observed, noise, geometry):
        original = super().local_features(
            packed, parent, variance, proposal, colors, observed, noise, geometry
        )
        batch, _, height, width = packed.shape
        size, count = geometry[4:6]
        layouts = colors[:, None].expand(-1, count, -1).reshape(-1, 4)
        coherent = to_coherent(observed, layouts, getattr(self, f"transport_{size}"))[:, 1:3]
        green_geometry = (batch, 2, height, width, *geometry[4:])
        green = self.synthesis(
            hermitian_projection(coherent * getattr(self, f"band_{size}")), green_geometry
        )
        variance_mean = variance.clamp_min(0).mean(1, keepdim=True)
        features = []
        for scale in (9, 33, 129):
            energy = separable_box(green.square(), scale)
            reference = separable_box(variance_mean, scale).clamp_min((1 / 65535) ** 2)
            common, difference = energy[:, :1], energy[:, 1:]
            features.extend(
                (
                    torch.log1p(common / reference),
                    torch.log1p(difference / reference),
                    (common - difference) / (common + difference + reference),
                )
            )
        return torch.cat((original, *features), 1)
