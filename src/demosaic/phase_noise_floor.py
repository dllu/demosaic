"""Nonnegative additive variance floor from a robust spectral proxy.

For circular Gaussian Fourier noise, median(power)/ln2 estimates its mean.
The fixed affine/Hann operator propagates unit pixel variance exactly. Texture
can inflate this proxy. This is a conservative floor, not calibrated uncertainty.
"""

from functools import lru_cache

import numpy as np

from .phase_harmonic import tapered_spectrum


@lru_cache(maxsize=8)
def unit_noise(shape):
    value = tapered_spectrum(np.zeros(shape), np.ones(shape))["noise_variance"]
    value.setflags(write=False)
    return value


def estimate_variance_floor(pair):
    radius = np.hypot(pair["native_fx"], pair["native_fy"])
    mask = (
        (radius >= 0.1)
        & (radius <= 0.34)
        & (pair["native_fy"] > 0)
        & (np.abs(pair["native_fx"]) < 0.25)
    )
    unit = unit_noise(radius.shape)[mask]
    empirical = np.median(pair["power"][:, mask] / unit[None], axis=1) / np.log(2)
    declared = np.median(pair["noise_variance"][:, mask] / unit[None], axis=1)
    added = max(0.0, float(np.max(empirical - declared)))
    return {
        "added_pixel_variance": added,
        "empirical_spectral_proxy_per_green": empirical.tolist(),
        "declared_noise_proxy_per_green": declared.tolist(),
        "probe_bins_per_green": int(mask.sum()),
        "probe_annulus": [0.1, 0.34],
        "positive_fy_only": True,
        "confidence_calibrated": False,
    }
