"""Training-only spectral error before support or on delivered camera RGB."""

from noisy_objective import coefficient_loss


def spectral_loss(module, output, target, colors, aux, floor, site):
    """Keep the old coefficient loss exact, or score actual delivered error.

    Delivered mosaic uses the four observed CFA samples. Delivered RGB packs
    all three camera-RGB channels into twelve C-major spatial phases, so errors
    at unsampled colors also contribute. Both reuse the original analysis size
    and smooth band. Repeating the four-phase frame-noise proxy for RGB sets
    training units; it is not a calibrated post-demosaic covariance or SNR.
    Target/reference access is confined to training, never module forward.
    """
    if site == "pre-support":
        return coefficient_loss(module, target, colors, aux, floor)
    if site not in ("delivered-mosaic", "delivered-RGB"):
        raise ValueError("Unknown spectral supervision site")
    if output.shape != target.shape or output.ndim != 4 or output.shape[1] != 3:
        raise ValueError("Expected matching N x 3 x H x W delivered RGB and target")
    import torch
    from torch.nn import functional as F

    from demosaic.cfa import mosaic
    from demosaic.precision import ieee_fp32

    with torch.autocast(output.device.type, enabled=False), ieee_fp32():
        error = output.float() - target.float()
        packed = (
            mosaic(error, colors) if site == "delivered-mosaic" else F.pixel_unshuffle(error, 2)
        )
        spectrum, _ = module.analysis(packed, aux["geometry"][4])
        noise = aux["noise_power"]
        if site == "delivered-RGB":
            noise = noise.repeat(1, 3)
        assert noise.shape == spectrum.shape[:2]
        variance = noise[:, :, None, None].clamp_min((floor / 65535) ** 2)
        band = getattr(module, f"band_{aux['geometry'][4]}")
        return (spectrum.abs().square() / variance * band).sum() / (
            band.sum().clamp_min(1) * spectrum.shape[0] * spectrum.shape[1]
        )
