"""Explicit training scope for the optional global RAW branch."""


def validate_raw_global_only(config):
    value = config.get("raw_global_only", False)
    if type(value) is not bool:
        raise ValueError("RAW global-only training must be a boolean")
    if value and any(
        config.get(key, False)
        for key in (
            "raw_kernel_only",
            "refiner_only",
            "coarse_refiner_only",
            "pyramid_refiner_only",
            "late_rgb_only",
            "raw_frequency_only",
        )
    ):
        raise ValueError("RAW global-only training cannot combine with another head-only mode")
    if value and config.get("model", {}).get("raw_global_features") is not True:
        raise ValueError("RAW global-only training requires RAW global features")
    return value


def require_resume_raw_global_scope(previous, current):
    if validate_raw_global_only(previous) != validate_raw_global_only(current):
        raise ValueError("Resume RAW global training scope differs; initialize a new run")
