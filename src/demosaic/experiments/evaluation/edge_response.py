"""Exact conditional increments and absolute quiet/edge errors; GT scoring only."""

import numpy as np


def measure(arrays, value):
    target = arrays["target"].astype(np.float64)
    value = np.asarray(value, dtype=np.float64)
    if value.shape != target.shape or value.shape[:2] != (3, 3) or not np.isfinite(value).all():
        raise ValueError("Expected finite zero/one/two-direction RGB predictions")
    error = value - target
    result = {}
    for name, mask in (("quiet", arrays["quiet"]), ("edge", arrays["edge_band"])):
        if not mask.any():
            raise ValueError("Evaluation region must not be empty")
        e = error[..., mask]
        mean = e.mean(-1, keepdims=True)
        result[name + "_error_RMS_DN16"] = float(np.sqrt(np.mean(e**2)) * 65535)
        result[name + "_DC_RMS_DN16"] = float(np.sqrt(np.mean(mean**2)) * 65535)
        result[name + "_spatial_RMS_DN16"] = float(np.sqrt(np.mean((e - mean) ** 2)) * 65535)
    result["full_error_RMS_DN16"] = float(np.sqrt(np.mean(error**2)) * 65535)
    for name, first, second in (("strong", 0, 1), ("weak", 1, 2)):
        truth = target[second] - target[first]
        predicted = value[second] - value[first]
        energy = float(np.sum(truth**2))
        if energy <= 0:
            raise ValueError("A nonzero actual target increment is required")
        gain = float(np.sum(predicted * truth) / energy)
        result[name + "_gain"] = gain
        result[name + "_increment_error_RMS_DN16"] = float(
            np.sqrt(np.mean((predicted - truth) ** 2)) * 65535
        )
        result[name + "_orthogonal_RMS_DN16"] = float(
            np.sqrt(np.mean((predicted - gain * truth) ** 2)) * 65535
        )
    return result
