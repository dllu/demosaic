"""Dense local spectral residual above frozen V183 matching.

Every principal-band frequency is measured in overlapping windows. Three local
scales condition a shared 508-parameter mixer. Powers reuse input noise and are
not confidence; principal aliases remain unresolved. No target enters inference.
"""

import math

import torch
from torch.nn import functional as F

from .late_local_noise_matching import local_noise_features
from .late_local_phase_evidence_matching import local_phase_evidence_maps
from .late_pooled_phase_wave import _green_layout
from .late_phase_wave_readout import LatePhaseWaveReadoutDetail
from .late_spatial_context_wave import SpatialContextWaveReadout
from .precision import ieee_fp32


def _validate_dense_config(window, stride, support_windows):
    if (
        type(window) is not int
        or not 9 <= window <= 129
        or window % 2 != 1
        or type(stride) is not int
        or not 1 <= stride <= window // 2
    ):
        raise ValueError("Expected odd window9..129 and stride1..halfwindow")
    if (
        len(support_windows) != 2
        or len(set(support_windows)) != 2
        or any(type(s) is not int or s < 5 or s % 2 != 1 or s >= window for s in support_windows)
    ):
        raise ValueError("Expected two distinct smaller odd support windows>=5")


def _dense_geometry(height, width, window, stride, device):
    radius = window // 2
    axes = [list(range(0, n, stride)) for n in [height, width]]
    for axis, n in zip(axes, [height, width], strict=True):
        if axis[-1] != n - 1:
            axis.append(n - 1)
    ay, ax = [torch.tensor(a, device=device) for a in axes]
    cy, cx = torch.meshgrid(ay, ax, indexing="ij")
    centers = torch.stack([cy.flatten(), cx.flatten()], -1)
    y, x = torch.meshgrid(
        torch.arange(window, device=device), torch.arange(window, device=device), indexing="ij"
    )
    iy = centers[:, 0, None, None] + y
    ix = centers[:, 1, None, None] + x
    indices = iy * (width + 2 * radius) + ix
    valid = (iy >= radius) & (iy < height + radius) & (ix >= radius) & (ix < width + radius)
    q = torch.stack([torch.ones_like(x), x / radius - 1, y / radius - 1], -1).double()
    fy = torch.fft.fftfreq(window, device=device, dtype=torch.float64) / 2
    fy, fx = torch.meshgrid(fy, fy, indexing="ij")
    frequency_radius = torch.hypot(fy, fx)
    eligible = (frequency_radius >= 1 / 16) & (frequency_radius <= 1 / 3)
    offsets = fy.new_tensor([[0, 0], [0, 1], [1, 0], [1, 1]])
    angle = 2 * math.pi * (offsets[:, 0, None, None] * fy + offsets[:, 1, None, None] * fx)
    phase = torch.polar(torch.ones_like(angle), angle)
    hann = torch.hann_window(window, periodic=False, device=device, dtype=torch.float64)
    synthesis = hann[:, None] * hann[None, :]
    denominator = torch.zeros(
        (height + 2 * radius) * (width + 2 * radius), device=device, dtype=torch.float64
    )
    denominator.scatter_add_(
        0, indices.flatten(), synthesis.square().expand(len(centers), -1, -1).flatten()
    )
    denominator = denominator.reshape(height + 2 * radius, width + 2 * radius)[
        radius : radius + height, radius : radius + width
    ]
    if not bool((denominator > 0).all()):
        raise ArithmeticError("Dense overlap-add geometry leaves uncovered pixels")
    return {
        "centers_y": ay,
        "centers_x": ax,
        "centers_yx": centers,
        "linear_indices": indices,
        "valid": valid,
        "affine_basis": q,
        "native_fy": fy,
        "native_fx": fx,
        "eligible": eligible,
        "subpixel_phase": phase,
        "synthesis_window": synthesis,
        "normalization": denominator,
        "image_shape": torch.tensor([height, width], device=device),
    }


@torch.no_grad()
def dense_local_spectrum(
    packed, variance, colors, *, window=65, stride=32, support_windows=(33, 17)
):
    """Zero-pad clipped patches, remove weighted affine planes and propagate noise.

    A padding value is never counted as an observed sample. Each scale's design
    includes only the valid Hann-weighted samples. No reflected duplicate noise
    is treated as independent. All scales use the same window-size FFT grid.
    """
    green = _green_layout(packed, variance, colors)
    if bool((variance < 0).any()):
        raise ValueError("Expected nonnegative supplied variance")
    _validate_dense_config(window, stride, support_windows)
    batch, _, height, width = packed.shape
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        geometry = _dense_geometry(height, width, window, stride, packed.device)
        radius = window // 2
        gather = green[:, :, None, None].expand(-1, -1, height, width)
        raw, noise = packed.gather(1, gather).double(), variance.gather(1, gather).double()
        index = geometry["linear_indices"]
        patches = []
        for value in [raw, noise]:
            padded = F.pad(value, (radius, radius, radius, radius))
            patches.append(
                padded.flatten(-2)
                .index_select(-1, index.flatten())
                .reshape(batch, 2, len(index), window, window)
                .transpose(1, 2)
            )
        raw, noise = patches
        q = geometry["affine_basis"]
        features, spectra, variances = [], [], []
        green_y, green_x = green // 2, green % 2
        offset = (
            -2
            * math.pi
            * (
                geometry["native_fy"][None, None] * green_y[..., None, None]
                + geometry["native_fx"][None, None] * green_x[..., None, None]
            )
        )
        transport = torch.polar(torch.ones_like(offset), offset)[:, None]
        for scale in [window, *support_windows]:
            taper = torch.hann_window(
                scale, periodic=False, device=packed.device, dtype=torch.float64
            )
            taper = F.pad(taper, ((window - scale) // 2,) * 2)
            weight = (taper[:, None] * taper[None, :])[None] * geometry["valid"]
            gram = torch.einsum("phw,hwi,hwj->pij", weight.square(), q, q)
            inverse = torch.linalg.inv(gram)
            beta = torch.einsum(
                "pij,npchwi->npcj",
                inverse,
                raw[..., None] * (weight.square()[None, :, None, :, :, None] * q),
            )
            residual = weight[None, :, None] * (raw - torch.einsum("npcj,hwj->npchw", beta, q))
            coefficient = torch.fft.fft2(residual, norm="ortho")
            transformed_basis = torch.fft.fft2(weight[..., None] * q, dim=(1, 2), norm="ortho")
            h = torch.einsum(
                "phwi,pij->phwj", transformed_basis, inverse.to(transformed_basis.dtype)
            )
            cross = torch.fft.fft2(
                (noise * weight[None, :, None].pow(3))[..., None] * q, dim=(3, 4), norm="ortho"
            )
            covariance = torch.einsum(
                "npchw,hwi,hwj->npcij", noise * weight[None, :, None].pow(4), q, q
            )
            base = (noise * weight[None, :, None].square()).mean((-2, -1))[..., None, None]
            propagated = base - 2 * (h[None, :, None].conj() * cross).sum(-1).real
            propagated = (
                propagated
                + torch.einsum("phwi,npcij,phwj->npchw", h, covariance.to(h.dtype), h.conj()).real
            )
            if bool((propagated < -1e-10 * base.clamp_min(torch.finfo(torch.float64).tiny)).any()):
                raise ArithmeticError("Dense propagated spectral variance became negative")
            propagated = propagated.clamp_min(0)
            aligned = coefficient * transport
            z = aligned / propagated.clamp_min((1 / 65535) ** 2).sqrt()
            pa, pb = z.abs().square().unbind(2)
            a, b = z.unbind(2)
            cross_power = a * b.conj() / ((1 + pa) * (1 + pb)).sqrt()
            strength = (pa + pb) / (1 + pa + pb)
            fields = torch.stack(
                [
                    pa.log1p(),
                    pb.log1p(),
                    cross_power.real,
                    cross_power.imag,
                    geometry["native_fx"] * strength,
                    geometry["native_fy"] * strength,
                ],
                2,
            )
            features.append(fields)
            spectra.append(aligned)
            variances.append(propagated)
        context = (
            torch.cat(features, 2).reshape(batch * len(index), 18, window, window).to(packed.dtype)
        )
        coefficient = spectra[0].to(
            torch.complex64 if packed.dtype == torch.float32 else torch.complex128
        )
        if not bool(torch.isfinite(context).all() & torch.isfinite(coefficient).all()):
            raise ArithmeticError("Dense local spectral measurements are nonfinite")
        geometry.update(
            green_phase_indices=green,
            windows=torch.tensor([window, *support_windows], device=packed.device),
            stride=torch.tensor(stride, device=packed.device),
            propagated_variance=torch.stack(variances, 2),
            aligned_spectra=torch.stack(spectra, 2),
        )
        return context, coefficient, geometry


class DenseLocalSpectrumReadout(SpatialContextWaveReadout):
    """Dimensionless spectral mixing and native-subpixel weighted overlap-add.

    Raw coefficients retain camera-RGB units. Noise-normalized powers condition
    the weights; output amplitude is not multiplied by a second noise RMS. Both
    sides of each conjugate pair are averaged to ensure real synthesis.
    """

    def forward(self, context, coefficient, geometry):
        if (
            context.ndim != 4
            or context.shape[1] != 18
            or coefficient.ndim != 5
            or coefficient.shape[2] != 2
        ):
            raise ValueError("Expected dense patch context and two complex phase spectra")
        batch, patches, _, length, width = coefficient.shape
        if (
            length != width
            or context.shape != (batch * patches, 18, length, length)
            or context.dtype not in [torch.float32, torch.float64]
            or not coefficient.is_complex()
        ):
            raise ValueError("Dense context/spectrum shapes or dtypes do not match")
        height, image_width = [int(v) for v in geometry["image_shape"]]
        with torch.autocast(context.device.type, enabled=False), ieee_fp32():
            weights = self.mixing(F.silu(self.context(context))).reshape(
                batch, patches, 3, 4, length, length
            )
            a = torch.complex(weights[:, :, :, 0], weights[:, :, :, 1])
            b = torch.complex(weights[:, :, :, 2], weights[:, :, :, 3])
            spectrum = (a * coefficient[:, :, 0, None] + b * coefficient[:, :, 1, None]) * geometry[
                "eligible"
            ]
            conjugate = (-torch.arange(length, device=context.device)) % length
            spectrum = (
                spectrum + spectrum.index_select(-2, conjugate).index_select(-1, conjugate).conj()
            ) / 2
            phase = geometry["subpixel_phase"].to(coefficient.dtype)
            native = torch.fft.ifft2(spectrum[:, :, :, None] * phase, norm="ortho").real
            native = native * geometry["synthesis_window"].to(context.dtype)
            values = native.permute(0, 2, 3, 1, 4, 5).reshape(batch, 12, -1)
            padding = length // 2
            target_size = (height + 2 * padding) * (image_width + 2 * padding)
            index = geometry["linear_indices"].flatten()[None, None].expand(batch, 12, -1)
            summed = context.new_zeros(batch, 12, target_size).scatter_add(2, index, values)
            summed = summed.reshape(batch, 12, height + 2 * padding, image_width + 2 * padding)
            packed = summed[
                :, :, padding : padding + height, padding : padding + image_width
            ] / geometry["normalization"].to(context.dtype)
            output = F.pixel_shuffle(packed, 2)
            if not bool(torch.isfinite(output).all()):
                raise ArithmeticError("Dense overlap-add output is nonfinite")
            return output


class LateDenseLocalSpectrumDetail(LatePhaseWaveReadoutDetail):
    """Freeze V183 matching; replace sparse waves with a dense local readout."""

    def __init__(
        self,
        width=16,
        max_search=9.0,
        evidence_peaks=4,
        evidence_window=65,
        evidence_stride=32,
        dense_window=65,
        dense_stride=32,
        dense_support_windows=(33, 17),
    ):
        _validate_dense_config(dense_window, dense_stride, dense_support_windows)
        super().__init__(width, max_search, evidence_peaks, evidence_window, evidence_stride)
        self.wave_readout = DenseLocalSpectrumReadout()
        self.dense_window, self.dense_stride, self.dense_support_windows = (
            dense_window,
            dense_stride,
            tuple(dense_support_windows),
        )
        self.train()

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                restored = self.frozen(base, packed, variance, colors, wb)
                features, sigma = local_noise_features(restored, packed, variance, colors, wb)
                evaluated = bool(torch.any(sigma > 0))
                evidence_aux = dense_aux = None
                context = coefficient = None
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
                    context, coefficient, dense_aux = dense_local_spectrum(
                        packed.float(),
                        variance.float(),
                        colors,
                        window=self.dense_window,
                        stride=self.dense_stride,
                        support_windows=self.dense_support_windows,
                    )
                else:
                    inherited_correction, inherited = torch.zeros_like(restored), restored
            if evaluated:
                wave = self.wave_readout(context, coefficient, dense_aux)
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
                    "dense_spectrum": dense_aux,
                    "dense_context": context,
                    "dense_coefficient": coefficient,
                }
            return output
