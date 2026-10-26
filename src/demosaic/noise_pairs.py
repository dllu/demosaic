"""Independent simulated-noise views and a convex conditional-mean objective."""

import hashlib
import math

import torch

from .cfa import mosaic
from .losses import reconstruction_loss
from .noise import add_noise, variance_map
from .precision import ieee_fp32

POLICY = "independent-sensor-noise-v1"


def noise_pair_options(config):
    draws = config.get("noise_pair_draws", 1)
    weight = config.get("conditional_mean_weight", 0.0)
    if type(draws) is not int or draws not in (1, 2):
        raise ValueError("noise_pair_draws must be one or two")
    if (
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not math.isfinite(weight)
        or not 0 <= weight <= 1
    ):
        raise ValueError("Conditional mean weight must be finite and in [0,1]")
    if draws == 1 and weight:
        raise ValueError("Conditional mean loss requires two independent noise views")
    expected = POLICY if draws == 2 else None
    if config.get("noise_pair_policy", expected) != expected:
        raise ValueError("Unknown independent-noise policy")
    return draws, float(weight)


def require_resume_noise_pairs(previous, current):
    if noise_pair_options(previous) != noise_pair_options(current):
        raise ValueError(
            "Resume independent-noise policy or mean weight differs; initialize a new run"
        )


def independent_noise_view(batch, *, seed, step, domain):
    """Reuse clean geometry/camera/profile, drawing only a new sensor observation.

    Layout is [all original views, all second views]. A local generator leaves
    model/data RNG unchanged. Real paired observations must never enter here.
    """
    if domain not in ("commons", "native"):
        raise ValueError("Independent noise views require simulated-noise targets")
    required = {
        "packed",
        "variance",
        "sensor_target",
        "colors",
        "wb",
        "matrix",
        "shot",
        "read",
        "adc_black_level",
        "adc_bit_depth",
        "target",
    }
    if not required <= batch.keys() or {"sensor_reference", "sensor_mask"} & batch.keys():
        raise ValueError("Independent noise requires retained clean sensor and ADC metadata")
    size = len(batch["packed"])
    if size < 1 or any(not isinstance(v, torch.Tensor) or len(v) != size for v in batch.values()):
        raise ValueError("Independent noise fields need matching example axes")
    if not torch.all(batch["adc_bit_depth"] == 16):
        raise ValueError("Independent noise policy requires the recorded 16-bit ADC")
    device = batch["packed"].device
    value = int.from_bytes(
        hashlib.sha256(f"{POLICY}:{seed}:{step}:{domain}:view1".encode()).digest()[:8], "little"
    ) % (2**63)
    generator = torch.Generator(device=device).manual_seed(value)
    with torch.autocast(device.type, enabled=False), ieee_fp32():
        second = add_noise(
            mosaic(batch["sensor_target"].float(), batch["colors"]),
            batch["shot"],
            batch["read"],
            black_level=batch["adc_black_level"],
            bit_depth=16,
            generator=generator,
        )
        second_variance = variance_map(second, batch["shot"], batch["read"])
    result = {
        key: torch.cat(
            (v, second if key == "packed" else second_variance if key == "variance" else v)
        )
        for key, v in batch.items()
    }
    result["noise_pair_id"] = torch.arange(size, device=device).repeat(2)
    result["noise_view"] = torch.cat(
        (
            torch.zeros(size, dtype=torch.long, device=device),
            torch.ones(size, dtype=torch.long, device=device),
        )
    )
    return result


def validate_noise_pair_batch(batch):
    size = len(batch["target"])
    if size < 2 or size % 2:
        raise ValueError("Expected two equally sized independent-noise views")
    half = size // 2
    device = batch["target"].device
    if (
        "noise_pair_id" not in batch
        or "noise_view" not in batch
        or not torch.equal(batch["noise_pair_id"], torch.arange(half, device=device).repeat(2))
        or not torch.equal(
            batch["noise_view"], torch.arange(2, device=device).repeat_interleave(half)
        )
    ):
        raise ValueError("Independent-noise pair identity/layout differs")
    for key in (
        "target",
        "sensor_target",
        "colors",
        "wb",
        "matrix",
        "shot",
        "read",
        "adc_black_level",
        "adc_bit_depth",
    ):
        if (
            key not in batch
            or len(batch[key]) != size
            or not torch.equal(batch[key][:half], batch[key][half:])
        ):
            raise ValueError(f"Independent-noise pair {key} differs")
    if "sensor_reference" in batch or "sensor_mask" in batch:
        raise ValueError("Real paired observations cannot use conditional-mean supervision")
    return half


def conditional_mean_reconstruction_loss(
    prediction, batch, auxiliary=None, *, weight=0.0, **options
):
    """Convex mixture of per-view and mean-prediction reconstruction losses.

    Mean predictions are camera-linear outputs, not changed input noise
    conditioning. The original loss and its weights/masks remain unchanged.
    """
    noise_pair_options({"noise_pair_draws": 2, "conditional_mean_weight": weight})
    if weight:
        half = validate_noise_pair_batch(batch)
        if len(prediction) != 2 * half or (auxiliary is not None and len(auxiliary) != 2 * half):
            raise ValueError("Predictions and independent noise pairs differ")
    ordinary, terms = reconstruction_loss(prediction, batch, auxiliary, **options)
    if weight == 0:
        return ordinary, terms
    # Packed observations/variance are not a fictitious averaged sensor input.
    supervision = {
        key: value[:half]
        for key, value in batch.items()
        if key not in {"packed", "variance", "noise_pair_id", "noise_view"}
    }
    with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
        mean = (prediction[:half].float() + prediction[half:].float()) * 0.5
        mean_aux = (
            None
            if auxiliary is None
            else (auxiliary[:half].float() + auxiliary[half:].float()) * 0.5
        )
        averaged, mean_terms = reconstruction_loss(mean, supervision, mean_aux, **options)
        loss = (1 - weight) * ordinary + weight * averaged
        mixed = {
            key: (1 - weight) * value + weight * mean_terms[key] for key, value in terms.items()
        }
    return loss, {**mixed, "per_view_loss": ordinary, "conditional_mean_loss": averaged}
