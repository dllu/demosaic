"""Replace a subset of simulated ADC-only training inputs with faint sensor noise."""

import hashlib
import math

import torch

from .cfa import mosaic
from .noise import add_noise, variance_map
from .precision import ieee_fp32


def bridge_fraction(config):
    value = config.get("near_adc_bridge_fraction", 0.0)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise ValueError("Near-ADC bridge fraction must be finite and in [0,1]")
    return float(value)


def require_resume_near_adc_bridge(previous, current):
    if bridge_fraction(previous) != bridge_fraction(current):
        raise ValueError("Resume near-ADC bridge fraction differs; initialize a new run")


def _seed(seed, step, domain, stream):
    message = f"near-adc-training-v1:{seed}:{step}:{domain}:{stream}".encode()
    return int.from_bytes(hashlib.sha256(message).digest()[:8], "little") % (2**63)


@torch.no_grad()
def bridge_noise_batch(batch, fraction, *, seed, step, domain):
    """Keep targets, camera transforms, and all original positive-noise samples.

    Within the ADC-only subset, draw full-signal sigma log-uniformly across
    4–160 ADC codes and read noise across 0.7–1500 electrons. The shot term
    is the positive root of shot + (read_e * shot)**2 = full-signal variance.
    Stateless generators keep the original data and model RNG streams intact.
    """
    if not fraction:
        return batch
    if domain not in ("commons", "native"):
        raise ValueError("Near-ADC training requires simulated-noise inputs")
    packed = batch["packed"]
    device = packed.device
    profile_rng = torch.Generator().manual_seed(_seed(seed, step, domain, "profile"))
    draws = torch.rand(len(packed), 3, dtype=torch.float64, generator=profile_rng).to(device)
    adc_only = (batch["shot"].reshape(-1) == 0) & (batch["read"].reshape(-1) == 0)
    selected = torch.where(adc_only & (draws[:, 0] < fraction))[0]
    if selected.numel() == 0:
        return batch
    if not torch.all(batch["adc_bit_depth"][selected] == 16):
        raise ValueError("Near-ADC training requires the recorded 16-bit ADC")
    black = batch["adc_black_level"][selected]
    sigma_codes = 4 * (40 ** draws[selected, 1, None, None, None])
    read_e = 0.7 * ((1500 / 0.7) ** draws[selected, 2, None, None, None])
    full_variance = (sigma_codes / (65535 * (1 - black.double()))).square()
    shot = 2 * full_variance / (1 + (1 + 4 * read_e.square() * full_variance).sqrt())
    read = (read_e * shot).square().float()
    shot = shot.float()

    sensor_rng = torch.Generator(device=device).manual_seed(_seed(seed, step, domain, "sensor"))
    with torch.autocast(device.type, enabled=False), ieee_fp32():
        clean = mosaic(batch["sensor_target"][selected].float(), batch["colors"][selected])
        raw = add_noise(clean, shot, read, black_level=black, generator=sensor_rng)
        variance = variance_map(raw, shot, read)
    changed = {"packed": raw, "variance": variance, "shot": shot, "read": read}
    return batch | {
        key: batch[key].index_copy(0, selected, value) for key, value in changed.items()
    }
