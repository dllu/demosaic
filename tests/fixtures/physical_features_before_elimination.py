"""Original physical-feature construction, before unused anchor-channel work removal."""

import torch
from torch.nn import functional as F

from demosaic.cfa import bilinear, malvar
from demosaic.precision import ieee_fp32
from demosaic.pretrained_rgb import stabilized_photometry
from demosaic.prior import box_mean

SOURCE_SHA256 = "9018feb07b37c7f1431e9c23af85a049f83dee9ed70747b8681a4cb3e0f7035a"


def physical_rgb_features_before_elimination(
    packed,
    variance,
    colors,
    wb=None,
    matrix=None,
    *,
    rgb=None,
    stabilized=False,
    normalization_mask=None,
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
        log_noise = (rgb_variance.clamp_min(1e-12).log() + 12) / 6
        condition = torch.cat(
            (
                measured,
                mask,
                log_noise,
                camera[:, :, None, None].expand(-1, -1, 2 * h, 2 * w),
            ),
            dim=1,
        )
        return rgb, normalized, noise, condition, offset, span


def original_anchored_features(*args, photometry_profiles=None, **kwargs):
    result = physical_rgb_features_before_elimination(*args, **kwargs)
    if photometry_profiles is None:
        return result
    rgb, normalized, noise, condition, offset, span = result
    anchors = stabilized_photometry(photometry_profiles, offset, span)
    condition = torch.cat(
        (condition[:, :6], anchors.expand(-1, -1, *rgb.shape[-2:]), condition[:, 9:]), dim=1
    )
    return rgb, normalized, noise, condition, offset, span
