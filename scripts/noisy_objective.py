"""Training-only ADC routing and bounded clean-spectrum emphasis for V151."""


def ADC_only(noise):
    return noise["shot"] == noise["read"] == 0


def apply_ADC_weight(loss, noise, weight):
    """Keep the loss graph on zero-weight steps; Adam/EMA clocks still advance."""
    assert weight in (0, 1)
    return loss * 0 if weight == 0 and ADC_only(noise) else loss


def peak_weights(clean, variance, bonus):
    """Common phase weight in[1,1+bonus]; variance is already floored.

    This training-target power/noise proxy is not calibrated SNR/probability.
    No renormalization lowers the baseline penalty on signal-free targets.
    """
    assert bonus >= 0
    ratio = clean.abs().square().sum(1, keepdim=True) / variance.sum(1, keepdim=True)
    return 1 + bonus * ratio / (1 + ratio)


def coefficient_loss(module, target, colors, aux, floor, peak_bonus=0):
    import torch

    from demosaic.cfa import mosaic
    from demosaic.precision import ieee_fp32

    with torch.autocast(target.device.type, enabled=False), ieee_fp32():
        clean, _ = module.analysis(mosaic(target.float(), colors), aux["geometry"][4])
        desired = clean - aux["parent_spectrum"]
        band = getattr(module, f"band_{aux['geometry'][4]}")
        variance = aux["noise_power"][:, :, None, None].clamp_min((floor / 65535) ** 2)
        error = (aux["spectral_delta"] - desired).abs().square() / variance * band
        if peak_bonus:
            error = error * peak_weights(clean, variance, peak_bonus)
        return error.sum() / (band.sum().clamp_min(1) * clean.shape[0] * 4)
