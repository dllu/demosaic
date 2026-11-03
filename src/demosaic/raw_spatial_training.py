"""Learning-rate policy for a newly initialized local RAW attention branch."""

import math


def spatial_lr_multiplier(config):
    value = config.get("raw_spatial_lr_multiplier", 1.0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(  # noqa: TRY004 -- configuration errors use ValueError before model construction
            "Spatial learning-rate multiplier must be finite and positive"
        )
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Spatial learning-rate multiplier must be finite and positive")
    if value != 1:
        if config.get("model", {}).get("raw_spatial_features") is not True:
            raise ValueError("Spatial learning-rate multiplier requires RAW spatial features")
        if any(
            config.get(key, 1) != 1
            for key in (
                "phase_lr_multiplier",
                "raw_directional_lr_multiplier",
                "raw_spectral_lr_multiplier",
                "raw_frequency_lr_multiplier",
                "late_rgb_lr_multiplier",
            )
        ):
            raise ValueError(
                "Spatial learning-rate groups cannot combine with other RAW-head groups"
            )
    return value


def require_resume_spatial_lr(previous, current):
    if spatial_lr_multiplier(previous) != spatial_lr_multiplier(current):
        raise ValueError("Resume spatial learning rate differs; initialize a new run")
