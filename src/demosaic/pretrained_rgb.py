"""Pretrained RGB restoration trunk adapted to spatially conditioned Bayer data.

The weight-compatible DRUNet topology is adapted from Noise2VST's implementation
at 02b839dae08e6304441ef9e5b3452262c36c4550, inspired by KAIR/DPIR.
Copyright (c) 2025 Sebastien Herbreteau; copyright (c) 2019 Kai Zhang.
MIT notices: third_party/gaussian/{Noise2VST-LICENSE,KAIR-LICENSE}.

The physical feature construction, per-image normalization, measurement/camera
adapter and DINO fusion are this project's experimental joint reconstruction.
This is a single-pass trainable model, not the frozen GAT/HQS comparator.
"""

import hashlib
import math
from functools import lru_cache
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import PATTERNS, adc_cfa_projection, bilinear, color_indices, malvar
from .color import render
from .precision import ieee_fp32
from .prior import box_mean
from .vst import GeneralizedAnscombe


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.res = nn.Sequential(
            nn.Conv2d(channels, channels, 3, padding=1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels, channels, 3, padding=1, bias=False),
        )

    def forward(self, x):
        return x + self.res(x)


class RgbRestorationTrunk(nn.Module):
    """Original RGB DRUNet tensor names/topology for strict pretrained loading.

    Inputs are already normalized and padded to multiples of eight. Noise can
    vary spatially. Optional offsets start at zero in the joint model.
    """

    def __init__(self, *, hidden_autocast=False, middle_skip_fp32=False):
        super().__init__()
        self.hidden_autocast = hidden_autocast
        self.middle_skip_fp32 = middle_skip_fp32
        self.m_head = nn.Conv2d(4, 64, 3, padding=1, bias=False)
        for level, (a, b) in enumerate(zip((64, 128, 256), (128, 256, 512)), 1):
            setattr(
                self,
                f"m_down{level}",
                nn.Sequential(
                    *(ResidualBlock(a) for _ in range(4)),
                    nn.Conv2d(a, b, 2, stride=2, bias=False),
                ),
            )
            setattr(
                self,
                f"m_up{level}",
                nn.Sequential(
                    nn.ConvTranspose2d(b, a, 2, stride=2, bias=False),
                    *(ResidualBlock(a) for _ in range(4)),
                ),
            )
        self.m_body = nn.Sequential(*(ResidualBlock(512) for _ in range(4)))
        self.m_tail = nn.Conv2d(64, 3, 3, padding=1, bias=False)

    def forward(
        self,
        rgb,
        noise,
        *,
        head_offset=None,
        middle_offset=None,
        encoder_offsets=None,
        return_features=False,
    ):
        # Preserve weak native RGB variations through the first skip even when
        # deep features use BF16/FP16. Absolute RGB is projected in IEEE FP32.
        with torch.autocast(rgb.device.type, enabled=False), ieee_fp32():
            x1 = self.m_head(torch.cat((rgb.float(), noise.float()), dim=1))
            if head_offset is not None:
                x1 = x1 + head_offset.float()
        hidden = x1
        if self.hidden_autocast and torch.is_autocast_enabled(x1.device.type):
            # Keep the original FP32 head for the final native skip. Only the
            # hidden encoder branch follows the active CNN autocast dtype.
            hidden = hidden.to(torch.get_autocast_dtype(x1.device.type))
        x2 = self.m_down1(hidden)
        if encoder_offsets is not None:
            # Keep the same hidden/skip dtype as the no-context control. In
            # particular, zero feature gates must not introduce FP32 promotion.
            x2 = x2 + encoder_offsets[0].to(x2.dtype)
        x3 = self.m_down2(x2)
        if encoder_offsets is not None:
            x3 = x3 + encoder_offsets[1].to(x3.dtype)
        x4 = self.m_down3(x3)
        if self.middle_skip_fp32:
            # Match the FP32 promotion supplied by a DINO offset, even when
            # that branch is absent. Convolutions still follow the outer AMP.
            x4 = x4.float()
        if middle_offset is not None:
            x4 = x4 + middle_offset
        x = self.m_up3(self.m_body(x4) + x4)
        x = self.m_up2(x + x3)
        x = self.m_up1(x + x2)
        with torch.autocast(rgb.device.type, enabled=False), ieee_fp32():
            features = x.float() + x1
            prediction = self.m_tail(features)
            return (prediction, features) if return_features else prediction


@lru_cache(maxsize=1)
def pooled_malvar_kernels():
    """Linear coefficients for a 2x2 RGB mean, expressed in packed CFA cells.

    Basis impulses derive these small physical kernels from our MHC operator,
    without any image/reference fitting. The central 2x2 output has full 5x5
    support inside a 6x6 Bayer field, so no boundary extension enters the result.
    """
    impulses = torch.eye(36, dtype=torch.float32).reshape(36, 4, 3, 3)
    kernels = []
    for pattern in PATTERNS:
        rgb = malvar(impulses, color_indices(pattern))
        kernels.append(rgb[..., 2:4, 2:4].mean((-2, -1)).T.reshape(3, 4, 3, 3))
    return torch.stack(kernels)


@lru_cache(maxsize=1)
def detail_malvar_energy():
    """Interior MHC-minus-expanded-area2 noise energy per RGB/output/input phase.

    Independent unit CFA noise gives variance equal to squared coefficient
    sums. Keeping input phases separate permits actual Gaussian WB ratios.
    The central 2x2 output has complete support inside the 12x12 sensor field.
    """
    impulses = torch.eye(144, dtype=torch.float32).reshape(144, 4, 6, 6)
    result = []
    for pattern in PATTERNS:
        rgb = malvar(impulses, color_indices(pattern))
        low = F.avg_pool2d(rgb, 2)
        expanded = F.interpolate(low, scale_factor=2, mode="bilinear", align_corners=False)
        coefficients = (rgb - expanded)[..., 6:8, 6:8].flatten(1).T.reshape(12, 4, 6, 6)
        result.append(coefficients.square().sum((-2, -1)))
    return torch.stack(result)


def physical_rgb_features(
    packed,
    variance,
    colors,
    wb=None,
    matrix=None,
    *,
    rgb=None,
    stabilized=False,
    normalization_mask=None,
    photometry_profiles=None,
):
    """Build normalized camera RGB and actual CFA/camera metadata in IEEE FP32.

    No input fitting, reference or learned denoiser is used here. The spatial
    noise map is a marginal measurement-noise proxy, not an assertion that
    demosaiced RGB noise is independent. Affine scales are per image so batches
    cannot change an image's normalization. An explicit training mask chooses
    central-half statistics for selected images, with the same raw measurements
    and feature canvas. Physical anchors use the resulting coordinates.
    """
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        packed, variance = packed.float(), variance.float()
        batch, _, h, w = packed.shape
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        rgb = malvar(packed, colors, wb) if rgb is None else rgb.float()
        offset = rgb.amin((1, 2, 3), keepdim=True)
        rgb_variance = bilinear(box_mean(variance.clamp_min(0), 7), colors)
        sigma = rgb_variance.mean(1, keepdim=True).clamp_min(0).sqrt()
        image_range = rgb.amax((1, 2, 3), keepdim=True) - offset
        # A quantized/clipped flat does not provide a useful contrast scale.
        # Preserve the original prior's unit fallback for constant RGB. For
        # nearly flat tiles, a conservative eight-sigma floor avoids feeding
        # an arbitrarily large normalized noise level to the pretrained trunk.
        span = torch.maximum(image_range, 8 * sigma.amax((1, 2, 3), keepdim=True))
        flat_span = torch.ones_like(span)
        if stabilized:
            flat_span = torch.maximum(flat_span, 8 * sigma.amax((1, 2, 3), keepdim=True))
        span = torch.where(image_range <= 1e-6, flat_span, span.clamp_min(1e-4))
        if normalization_mask is not None:
            if (
                not isinstance(normalization_mask, torch.Tensor)
                or normalization_mask.dtype != torch.bool
                or normalization_mask.shape != (batch,)
                or normalization_mask.device != packed.device
            ):
                raise ValueError("Normalization mask must be one device-local boolean per image")
            height, width = rgb.shape[-2:]
            y, x = height // 4, width // 4
            center_rgb = rgb[..., y : height - y, x : width - x]
            center_sigma = sigma[..., y : height - y, x : width - x]
            center_offset = center_rgb.amin((1, 2, 3), keepdim=True)
            center_range = center_rgb.amax((1, 2, 3), keepdim=True) - center_offset
            center_floor = 8 * center_sigma.amax((1, 2, 3), keepdim=True)
            center_flat = (
                torch.maximum(torch.ones_like(center_floor), center_floor)
                if stabilized
                else torch.ones_like(center_floor)
            )
            center_span = torch.where(
                center_range <= 1e-6,
                center_flat,
                torch.maximum(center_range, center_floor).clamp_min(1e-4),
            )
            select = normalization_mask[:, None, None, None]
            offset = torch.where(select, center_offset, offset)
            span = torch.where(select, center_span, span)
        normalized = (rgb - offset) / span
        noise = sigma / span
        phase_masks = F.one_hot(colors, 3).transpose(1, 2)[..., None, None].float()
        mask = F.pixel_shuffle(phase_masks.expand(-1, -1, -1, h, w).reshape(batch, 12, h, w), 2)
        measured = F.pixel_shuffle((phase_masks * packed[:, None]).reshape(batch, 12, h, w), 2)
        measured = (measured - offset * mask) / span
        balance = packed.new_ones(batch, 3) if wb is None else wb.float()
        transform = (
            torch.eye(3, device=packed.device)[None].expand(batch, -1, -1)
            if matrix is None
            else matrix.float()
        )
        camera = torch.cat((balance.clamp_min(1e-6).log2(), transform.flatten(1)), dim=1)
        if photometry_profiles is None:
            noise_condition = (rgb_variance.clamp_min(1e-12).log() + 12) / 6
        else:
            noise_condition = stabilized_photometry(photometry_profiles, offset, span).expand(
                -1, -1, *rgb.shape[-2:]
            )
        condition = torch.cat(
            (
                measured,
                mask,
                noise_condition,
                camera[:, :, None, None].expand(-1, -1, 2 * h, 2 * w),
            ),
            dim=1,
        )
        return rgb, normalized, noise, condition, offset, span


def stabilized_photometry(profiles, offset, span):
    """Encode physical black/white coordinates and the noise-family/read ratio.

    Sensor-measurement black/white anchors preserve clipping photometry across ISO,
    including constant tiles whose normalized RGB/noise alone are ambiguous.
    They replace the three constant unit-variance log channels, adding no
    parameters. These are measurement coordinates, not expectations of noisy
    transformed observations. asinh compresses them without clipping.
    """
    with torch.autocast(offset.device.type, enabled=False), ieee_fp32():
        values = []
        for b, (transform, scale, stochastic) in enumerate(profiles):
            white = torch.ones_like(offset[b : b + 1])
            white = transform(white) if transform is not None else white / scale
            black_coordinate = -offset[b : b + 1] / span[b : b + 1]
            white_coordinate = (white - offset[b : b + 1]) / span[b : b + 1]
            family = (
                math.log1p(transform.read_e) / 3
                if transform is not None
                else -1.0
                if stochastic
                else -2.0
            )
            values.append(
                torch.cat(
                    (
                        black_coordinate.asinh(),
                        white_coordinate.asinh(),
                        torch.full_like(black_coordinate, family),
                    ),
                    dim=1,
                )
            )
        return torch.cat(values)


class PretrainedRgbDemosaic(nn.Module):
    """One trainable RGB pass with CFA/noise/camera input and frozen DINO context."""

    def __init__(
        self,
        *,
        stabilized=False,
        physical_anchors=False,
        processing_scale=1,
        detail_prior=False,
        hidden_autocast=False,
        center_camera_matrix=False,
        middle_skip_fp32=False,
        adc_projection=False,
        adc_projection_mode="malvar",
        raw_kernel=False,
        raw_kernel_windows=(1, 5, 17),
        raw_kernel_phase_conditioning=False,
        raw_directional_residual=False,
        raw_directional_bank_context=False,
        raw_directional_bank_detach_input=False,
        raw_spectral_residual=False,
        raw_frequency_features=False,
        raw_spatial_features=False,
    ):
        super().__init__()
        if raw_directional_bank_context and not raw_directional_residual:
            raise ValueError("Directional bank context requires the directional branch")
        if raw_directional_bank_detach_input and not raw_directional_bank_context:
            raise ValueError("Directional bank input detachment requires bank context")
        if physical_anchors and not stabilized:
            raise ValueError("Physical anchors require variance stabilization")
        if adc_projection and not stabilized:
            raise ValueError(
                "ADC CFA projection requires explicit stabilized RGB noise conditioning"
            )
        if adc_projection_mode not in ("malvar", "sites"):
            raise ValueError("ADC CFA projection mode must be malvar or sites")
        if processing_scale not in (1, 2) or processing_scale == 2 and not stabilized:
            raise ValueError("Packed processing requires variance stabilization and scale 2")
        if detail_prior and processing_scale != 2:
            raise ValueError("The detail prior requires packed processing")
        if raw_kernel and (processing_scale != 1 or adc_projection):
            raise ValueError(
                "RAW kernel reconstruction requires native processing and no ADC projection"
            )
        if raw_kernel_phase_conditioning and not raw_kernel:
            raise ValueError("RAW kernel phase conditioning requires RAW kernel reconstruction")
        if raw_directional_residual and (
            not stabilized
            or not physical_anchors
            or processing_scale != 1
            or raw_kernel
            or adc_projection
        ):
            raise ValueError(
                "Directional residual requires native stabilized anchored RGB without other RAW heads"
            )
        if raw_spectral_residual and (
            not stabilized
            or not physical_anchors
            or processing_scale != 1
            or raw_kernel
            or raw_directional_residual
            or adc_projection
        ):
            raise ValueError(
                "Spectral residual requires native stabilized anchored RGB without other RAW heads"
            )
        if raw_frequency_features and (
            not stabilized
            or not physical_anchors
            or processing_scale != 1
            or raw_kernel
            or raw_directional_residual
            or raw_spectral_residual
            or adc_projection
        ):
            raise ValueError(
                "RAW frequency features require native anchored RGB without other RAW heads"
            )
        if raw_spatial_features and (
            not stabilized
            or not physical_anchors
            or processing_scale != 1
            or raw_kernel
            or raw_directional_residual
            or raw_spectral_residual
            or raw_frequency_features
            or adc_projection
        ):
            raise ValueError(
                "RAW spatial features require native anchored RGB without other RAW heads"
            )
        self.network = RgbRestorationTrunk(
            hidden_autocast=hidden_autocast, middle_skip_fp32=middle_skip_fp32
        )
        self.measurement_adapter = nn.Conv2d(21, 64, 1)
        nn.init.zeros_(self.measurement_adapter.weight)
        nn.init.zeros_(self.measurement_adapter.bias)
        self.center_camera_matrix = center_camera_matrix
        self.register_buffer(
            "camera_matrix_reference",
            torch.zeros(64, 3) if center_camera_matrix else None,
        )
        self.stabilized = stabilized
        self.adc_projection = adc_projection
        self.adc_projection_mode = adc_projection_mode
        self.physical_anchors = physical_anchors
        self.processing_scale = processing_scale
        self.detail_prior = detail_prior
        if processing_scale == 2:
            self.phase_adapter = nn.Conv2d(16, 64, 1)
            self.phase_head = nn.Conv2d(80, 12, 3, padding=1)
            for module in [self.phase_adapter, self.phase_head]:
                nn.init.zeros_(module.weight)
                nn.init.zeros_(module.bias)
            # Store support flattened: Module.to(channels_last) treats 5D
            # buffers as volumes and rejects this training memory format.
            self.register_buffer(
                "pooled_kernels", pooled_malvar_kernels().flatten(2).clone(), persistent=False
            )
            self.register_buffer(
                "phase_patterns", torch.tensor(list(PATTERNS.values())), persistent=False
            )
            if detail_prior:
                self.register_buffer(
                    "detail_energy", detail_malvar_energy().clone(), persistent=False
                )
        self._noise_key = None
        self._noise_profiles = None
        self.raw_kernel = None
        self.raw_directional = None
        self.raw_spectral = None
        self.raw_frequency = None
        self.raw_spatial = None
        self.rgb_refinement = None
        if raw_frequency_features:
            from .raw_frequency_features import RawFrequencyFeatures

            self.raw_frequency = RawFrequencyFeatures()
        if raw_spatial_features:
            from .raw_spatial_features import RawSpatialFeatures

            self.raw_spatial = RawSpatialFeatures()
        if raw_spectral_residual:
            from .raw_spectral import RawSpectralResidual

            self.raw_spectral = RawSpectralResidual()
        if raw_directional_residual:
            from .raw_directional import RawDirectionalResidual

            self.raw_directional = RawDirectionalResidual(
                bank_context=raw_directional_bank_context,
                bank_detach_input=raw_directional_bank_detach_input,
            )
        if raw_kernel:
            from .raw_kernel import AdaptiveRawKernel

            # Keep the existing RGB tail in the trainable feature path. Its
            # free RGB prediction conditions kernels, never enters output RGB.
            self.raw_kernel = AdaptiveRawKernel(
                67, raw_kernel_windows, phase_conditioning=raw_kernel_phase_conditioning
            )

    @torch.no_grad()
    def initialize_camera_matrix_reference(self):
        """Preserve a parent's exact forward while centering matrix gradients.

        Store the three individual diagonal columns so equal weights subtract
        exactly after device moves; a pre-summed CPU reference can round
        differently from the CUDA reduction.
        """
        if not self.center_camera_matrix:
            raise ValueError("Camera matrix centering is disabled")
        self.camera_matrix_reference.copy_(self.measurement_adapter.weight[:, [12, 16, 20], 0, 0])

    def project_measurements(self, condition):
        if not self.center_camera_matrix:
            return self.measurement_adapter(condition)
        weight = self.measurement_adapter.weight
        correction = (weight[:, [12, 16, 20], 0, 0] - self.camera_matrix_reference).sum(1)
        # W M + b - (W - W_reference) I has derivative M-I with respect
        # to matrix weights. Camera information and representational capacity
        # remain intact, and the reference makes the parent's initial forward
        # exact without rebasing its trainable bias.
        return F.conv2d(condition, weight, self.measurement_adapter.bias - correction)

    def set_noise(self, shot, read):
        """Condition explicitly on supplied scalar/per-image physical priors.

        Tables depend only on shot/read, never observations or reference data.
        These transient, nonlearned profiles are excluded from checkpoints/EMA.
        """
        if not self.stabilized:
            return self
        shot = torch.as_tensor(shot, dtype=torch.float64).detach().flatten().cpu()
        read = torch.as_tensor(read, dtype=torch.float64).detach().flatten().cpu()
        count = max(len(shot), len(read))
        if count == 0 or len(shot) not in (1, count) or len(read) not in (1, count):
            raise ValueError("Shot/read require compatible scalar or per-image profiles")
        shot, read = shot.expand(count), read.expand(count)
        if not (torch.isfinite(shot).all() and torch.isfinite(read).all()):
            raise ValueError("Shot/read must be finite nonnegative priors")
        if (shot < 0).any() or (read < 0).any():
            raise ValueError("Shot/read must be finite nonnegative priors")
        device = self.measurement_adapter.weight.device
        key = (tuple(zip(shot.tolist(), read.tolist())), device)
        if key != self._noise_key:
            self._noise_profiles = [
                (
                    GeneralizedAnscombe(a, r).to(device) if a else None,
                    math.sqrt(r) if r else 1.0,
                    bool(a or r),
                )
                for a, r in key[0]
            ]
            self._noise_key = key
        return self

    def _phase_indices(self, colors):
        matches = (colors[:, None] == self.phase_patterns[None]).all(-1)
        if not matches.any(-1).all():
            raise ValueError("Expected an ordinary Bayer phase pattern")
        return matches.long().argmax(-1)

    def pooled_noise_gain(self, colors, balance, *, indices=None):
        """RMS marginal gain of MHC+area2 for independent unit CFA noise.

        RGB/spatial covariance remains; this does not whiten the observation.
        GAT's unit variance is itself approximate at low photon counts.
        """
        if indices is None:
            indices = self._phase_indices(colors)
        kernel = self.pooled_kernels[indices].reshape(-1, 3, 4, 3, 3)
        balance = balance.float().clamp_min(1e-6)
        ratio = balance.gather(1, colors)[:, None, :, None, None] / balance[:, :, None, None, None]
        return ((kernel * ratio).square().sum((1, 2, 3, 4)) / 3).sqrt()[:, None, None, None]

    def detail_noise_variance(self, colors, balance, *, indices=None):
        """Periodic RGB marginal variance, not a covariance-whitening transform."""
        if indices is None:
            indices = self._phase_indices(colors)
        energy = self.detail_energy[indices]
        balance = balance.float().clamp_min(1e-6)
        ratio = balance.gather(1, colors)[:, None, :] / balance.repeat_interleave(4, 1)[..., None]
        variance = (energy * ratio.square()).sum(-1)
        return F.pixel_shuffle(variance[..., None, None], 2)

    def filter_detail(self, detail, variance):
        """Local Wiener prior in normalized physical units; preserve zero-noise detail.

        Variance is an interior Gaussian marginal proxy; GAT variance and tile
        boundaries are approximate. No reference image or fitted transform enters.
        """
        energy = box_mean(detail.square(), 7)
        signal = (energy - box_mean(variance, 7)).clamp_min(0)
        gain = signal / (signal + variance).clamp_min(1e-12)
        gain = torch.where(variance > 0, gain, torch.ones_like(gain))
        return detail * gain

    def forward_packed(
        self,
        normalized,
        noise,
        condition,
        packed,
        colors,
        wb,
        matrix,
        profiles,
        offset,
        span,
        preview,
        context,
    ):
        """Run the pretrained CNN on packed resolution; predict every output phase.

        All four CFA values and their color identities remain available to the
        trunk. A full-resolution physical bypass keeps detail at initialization;
        a zero-initialized phase head learns 12 outputs per packed cell.
        """
        h, w = normalized.shape[-2:]
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            low_rgb = F.avg_pool2d(normalized, 2)
            balance = packed.new_ones(len(packed), 3)
            if wb is not None:
                use_wb = packed.new_tensor([p[0] is None for p in profiles], dtype=torch.bool)
                balance = torch.where(use_wb[:, None], wb.float(), balance)
            phase_indices = self._phase_indices(colors)
            low_noise = F.avg_pool2d(noise, 2) * self.pooled_noise_gain(
                colors, balance, indices=phase_indices
            )
            # Validate metadata once, before the deep CNN. Rechecking a CUDA
            # boolean afterwards would introduce a needless host synchronization.
            native_variance = None
            if self.detail_prior:
                native_variance = noise.square() * self.detail_noise_variance(
                    colors, balance, indices=phase_indices
                ).repeat(1, 1, h // 2, w // 2)
            low_condition = F.avg_pool2d(condition, 2)
            labels = F.one_hot(colors, 3).transpose(1, 2).reshape(len(packed), 12, 1, 1)
            phase = torch.cat(
                ((packed.float() - offset) / span, labels.expand(-1, -1, *packed.shape[-2:])),
                dim=1,
            )
            pad = (0, -low_rgb.shape[-1] % 8, 0, -low_rgb.shape[-2] % 8)
            low_rgb, low_noise, low_condition, phase = (
                F.pad(value, pad, mode="replicate")
                for value in (low_rgb, low_noise, low_condition, phase)
            )
            head_offset = self.project_measurements(low_condition) + self.phase_adapter(phase)
        middle_offset = None
        if context is not None:
            middle_offset = context(
                render(preview, wb, matrix), (low_rgb.shape[-2] // 8, low_rgb.shape[-1] // 8)
            )
        coarse, features = self.network(
            low_rgb,
            low_noise,
            head_offset=head_offset,
            middle_offset=middle_offset,
            return_features=True,
        )
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            correction = F.interpolate(
                coarse.float() - low_rgb, scale_factor=2, mode="bilinear", align_corners=False
            )[..., :h, :w]
            phase_features = torch.cat((features.float(), phase), dim=1)
            phase_correction = F.pixel_shuffle(self.phase_head(phase_features), 2)[..., :h, :w]
            prediction = normalized + correction + phase_correction
            if self.detail_prior:
                expanded = F.interpolate(
                    low_rgb, scale_factor=2, mode="bilinear", align_corners=False
                )[..., :h, :w]
                detail = normalized - expanded
                prediction = prediction + (self.filter_detail(detail, native_variance) - detail)
            return prediction

    def forward(
        self,
        packed,
        variance,
        colors,
        wb=None,
        matrix=None,
        context=None,
        *,
        normalization_mask=None,
    ):
        if normalization_mask is not None and (
            not self.training
            or not self.stabilized
            or not self.physical_anchors
            or self.processing_scale != 1
            or self.raw_kernel is not None
            or self.raw_directional is not None
            or self.raw_spectral is not None
            or self.raw_frequency is not None
            or self.rgb_refinement is not None
        ):
            raise ValueError(
                "Normalization augmentation requires full-resolution anchored RGB training"
            )
        original_packed = packed
        original_variance = variance
        directional_features = None
        profiles, preview, base_rgb = None, None, None
        if self.stabilized:
            if self._noise_profiles is None:
                raise ValueError(
                    "Supply explicit shot/read conditioning before stabilized inference"
                )
            if len(self._noise_profiles) not in (1, len(packed)):
                raise ValueError("Noise profiles must be scalar or match the image batch")
            profiles = (
                self._noise_profiles * len(packed)
                if len(self._noise_profiles) == 1
                else self._noise_profiles
            )
            if colors.ndim == 1:
                colors = colors[None].expand(len(packed), -1)
            if context is not None:
                # Foundation features retain the ordinary camera/WB rendering;
                # stabilized coordinates are only for the restoration trunk.
                preview = malvar(packed, colors, wb)
            transformed, proxies, interpolated = [], [], []
            for b, (transform, scale, stochastic) in enumerate(profiles):
                raw = packed[b : b + 1]
                with torch.autocast(raw.device.type, enabled=False), ieee_fp32():
                    z = transform(raw) if transform is not None else (raw.double() / scale).float()
                transformed.append(z)
                proxies.append(torch.ones_like(z) if stochastic else torch.zeros_like(z))
                balance = None if transform is not None or wb is None else wb[b : b + 1]
                interpolated.append(malvar(z, colors[b : b + 1], balance))
            packed, variance = torch.cat(transformed), torch.cat(proxies)
            base_rgb = torch.cat(interpolated)
        rgb, normalized, noise, condition, offset, span = physical_rgb_features(
            packed,
            variance,
            colors,
            wb,
            matrix,
            rgb=base_rgb,
            stabilized=self.stabilized,
            normalization_mask=normalization_mask,
            photometry_profiles=profiles if self.physical_anchors else None,
        )
        if self.processing_scale == 2:
            prediction = self.forward_packed(
                normalized,
                noise,
                condition,
                packed,
                colors,
                wb,
                matrix,
                profiles,
                offset,
                span,
                rgb if preview is None else preview,
                context,
            )
        else:
            h, w = rgb.shape[-2:]
            pad = (0, -w % 8, 0, -h % 8)
            normalized, noise, condition = (
                F.pad(value, pad, mode="replicate") for value in (normalized, noise, condition)
            )
            with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
                head_offset = self.project_measurements(condition)
                if self.raw_frequency is not None:
                    frequency_offset = self.raw_frequency(packed, variance, colors, span)
                    head_offset = head_offset + F.pad(frequency_offset, pad, mode="replicate")
                if self.raw_spatial is not None:
                    spatial_offset = self.raw_spatial(packed, variance, colors, span)
                    head_offset = head_offset + F.pad(spatial_offset, pad, mode="replicate")
            middle_offset, encoder_kwargs = None, {}
            late_features = None
            if context is not None:
                preview_rgb = render(rgb if preview is None else preview, wb, matrix)
                context_size = (normalized.shape[-2] // 8, normalized.shape[-1] // 8)
                if self.rgb_refinement is None:
                    middle_offset = context(preview_rgb, context_size)
                else:
                    middle_offset, late_features = context(
                        preview_rgb, context_size, return_features=True
                    )
                if isinstance(middle_offset, tuple):
                    encoder_kwargs = {"encoder_offsets": middle_offset[:2]}
                    middle_offset = middle_offset[2]
            if (
                self.raw_kernel is not None
                or self.raw_directional is not None
                or self.raw_spectral is not None
                or self.rgb_refinement is not None
            ):
                prediction, features = self.network(
                    normalized,
                    noise,
                    head_offset=head_offset,
                    middle_offset=middle_offset,
                    return_features=True,
                    **encoder_kwargs,
                )
                directional_features = torch.cat((features.float(), prediction.float()), 1)[
                    ..., :h, :w
                ]
                if self.raw_kernel is not None:
                    return self.raw_kernel(original_packed, colors, directional_features)
                prediction = prediction[..., :h, :w]
            else:
                prediction = self.network(
                    normalized,
                    noise,
                    head_offset=head_offset,
                    middle_offset=middle_offset,
                    **encoder_kwargs,
                )[..., :h, :w]
            if self.rgb_refinement is not None:
                prediction = self.rgb_refinement(
                    prediction,
                    directional_features,
                    condition[..., :h, :w],
                    late_features,
                )
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            output = prediction.float() * span + offset
            if profiles is not None:
                output = torch.cat(
                    [
                        transform.inverse(output[b : b + 1])
                        if transform is not None
                        else (output[b : b + 1].double() * scale).float()
                        for b, (transform, scale, _) in enumerate(profiles)
                    ]
                )
            if self.adc_projection:
                # Explicit shot/read profiles alone choose the policy, never
                # an observed variance map or a fitted residual threshold.
                selected = [b for b, (_, _, stochastic) in enumerate(profiles) if not stochastic]
                if selected:
                    if len(selected) == len(output):
                        output = adc_cfa_projection(
                            output, original_packed, colors, wb, mode=self.adc_projection_mode
                        )
                    else:
                        indices = torch.tensor(selected, device=output.device)
                        balance = (
                            None
                            if wb is None
                            else wb.reshape(-1, 3).expand(len(output), -1)[indices]
                        )
                        corrected = adc_cfa_projection(
                            output[indices],
                            original_packed[indices],
                            colors[indices],
                            balance,
                            mode=self.adc_projection_mode,
                        )
                        output = output.index_copy(0, indices, corrected)
            if self.raw_directional is not None:
                output = self.raw_directional(
                    output, original_packed, original_variance, colors, directional_features
                )
            if self.raw_spectral is not None:
                output = self.raw_spectral(
                    output, original_packed, original_variance, colors, directional_features, wb
                )
            return output


def initialize_rgb_prior(model, receipt, *, archive=None):
    """Strictly transfer verified original RGB weights, retaining trainability."""
    from .gaussian import load_gaussian_prior

    if model.config.restoration_backbone != "pretrained-rgb":
        raise ValueError("Gaussian initialization requires the pretrained-rgb backbone")
    prior = load_gaussian_prior(receipt, archive=archive)
    model.pretrained_rgb.network.load_state_dict(prior.network.state_dict(), strict=True)
    return {
        "type": "verified RGB Gaussian restoration pretraining",
        "path": str(Path(receipt).resolve()),
        "sha256": hashlib.sha256(Path(receipt).read_bytes()).hexdigest(),
        "prior": prior.receipt,
        "new_adapters": (
            "Zero measurement/camera projection and zero DINO fusion gate"
            + (
                "; zero packed phase projection and output head"
                if model.config.rgb_processing_scale == 2
                else ""
            )
        ),
        "rgb_processing_scale": model.config.rgb_processing_scale,
        "physical_representation": (
            "Centered GAT / expectation inverse with explicit shot/read; unit-noise CFA"
            if model.config.variance_stabilization
            else "Affine-normalized linear camera RGB; spatial noise proxy; no GAT"
        ),
    }
