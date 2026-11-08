"""Native carrier footprints for fixed packed bins; never recovery bounds.

Sampling every second pixel identifies a frequency modulo one half cycle per
native pixel. Four native lifts share each packed bin. Two green phases alone
do not distinguish all four lifts. These masks describe geometry, not a learned
head's attainable output: spatial coefficient modulation has other frequencies.
"""

import numpy as np


def signed_bins(shape, bins):
    if len(shape) != 2 or any(type(n) is not int or n < 8 for n in shape):
        raise ValueError("Expected two packed integer axes >=8")
    bins = np.asarray(bins)
    if (
        bins.ndim != 2
        or bins.shape[1] != 2
        or not np.issubdtype(bins.dtype, np.integer)
        or not ((bins >= 0) & (bins < shape)).all()
    ):
        raise ValueError("Expected in-range integer Nx2 packed bins")
    size = np.asarray(shape)
    return np.where(bins <= (size - 1) // 2, bins, bins - size)


def carrier_footprints(shape, bins, radius):
    """Conjugate-closed native masks around principal or all four lifts.

    Lift the signed CENTER before expanding each square neighborhood on the
    native torus. Folding the neighborhood first would silently wrap it at the
    packed Nyquist boundary. Four-lift overlap is counted once in the union.
    """
    centers = signed_bins(shape, bins)
    if type(radius) is not int or radius < 0 or radius >= min(shape) // 2:
        raise ValueError("Expected nonnegative radius below half a packed axis")
    native = tuple(2 * n for n in shape)
    masks = np.zeros((4, *native), dtype=bool)
    for index, (ay, ax) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
        for cy, cx in centers + np.asarray([ay * shape[0], ax * shape[1]]):
            for sign in [-1, 1]:
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        masks[index, (sign * cy + dy) % native[0], (sign * cx + dx) % native[1]] = (
                            True
                        )
    return masks[0], masks.any(0)


def native_regions(shape):
    if len(shape) != 2 or any(type(n) is not int or n < 16 or n % 2 for n in shape):
        raise ValueError("Expected even native integer axes >=16")
    fy, fx = [np.fft.fftfreq(n) for n in shape]
    ay, ax = abs(fy[:, None]), abs(fx[None, :])
    strict = (ay < 0.25) & (ax < 0.25)
    closed = (ay <= 0.25) & (ax <= 0.25)
    boundary = closed & ~strict
    return {
        "strict_principal_square": strict,
        "quarter_cycle_boundary": boundary,
        "outside_closed_principal_square": ~closed,
        "native_radial_1over16_to_1over3": (np.hypot(ay, ax) >= 1 / 16)
        & (np.hypot(ay, ax) <= 1 / 3),
    }


def power_summary(power, packed_shape, bins, radius):
    power = np.asarray(power)
    if (
        power.shape != tuple(2 * n for n in packed_shape)
        or not np.isfinite(power).all()
        or (power < 0).any()
        or not power.sum() > 0
    ):
        raise ValueError("Expected positive finite native template power")
    principal, all_lifts = carrier_footprints(packed_shape, bins, radius)
    total = power.sum(dtype=np.float64)
    result = {
        key: float(power[mask].sum(dtype=np.float64) / total)
        for key, mask in native_regions(power.shape).items()
    }
    result.update(
        principal_carrier_proximity=float(power[principal].sum(dtype=np.float64) / total),
        four_lift_carrier_proximity=float(power[all_lifts].sum(dtype=np.float64) / total),
        added_alias_proximity=float(power[all_lifts & ~principal].sum(dtype=np.float64) / total),
        principal_footprint_cells=int(principal.sum()),
        four_lift_footprint_cells=int(all_lifts.sum()),
    )
    return result
