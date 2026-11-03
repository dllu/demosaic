"""Group-sparse support selection followed by a masked phasor refit.

Support and power proxies reuse observed RAW. Neither the mask nor the Gaussian
covariance is calibrated uncertainty for this nonlinear estimator.
"""

import numpy as np

from .phase_tv import _divergence, _gradient, _poisson_neumann


def coefficient_tv(values, weight, extra, *, mode="group", iterations=1024, device="cpu"):
    """TV plus group L1, or TV constrained to a supplied Boolean support.

    The two phasor components share each norm. A second ADMM split implements
    the group proximal map or exact zero-outside-support constraint. Return its
    feasible primal field and a feasible-dual bound, including capped solves.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 3 or values.shape[0] != 2 or min(values.shape[-2:]) < 1:
        raise ValueError("Require two phasor components on a nonempty grid")
    weight = np.broadcast_to(np.asarray(weight, dtype=np.float64), values.shape[-2:])
    if not np.isfinite(values).all() or not np.isfinite(weight).all() or np.any(weight < 0):
        raise ValueError("Require finite coefficients and nonnegative finite TV weights")
    if mode not in ("group", "mask"):
        raise ValueError("Coefficient mode must be group or mask")
    extra = np.broadcast_to(np.asarray(extra), values.shape[-2:])
    if mode == "mask":
        if extra.dtype != np.bool_:
            raise ValueError("The refit support must be Boolean")
    else:
        extra = extra.astype(np.float64)
        if not np.isfinite(extra).all() or np.any(extra < 0):
            raise ValueError("Group weights must be finite and nonnegative")
    if (
        not isinstance(iterations, (int, np.integer))
        or isinstance(iterations, bool)
        or iterations < 1
    ):
        raise ValueError("Iteration cap must be a positive integer")
    if str(device) not in ("cpu",) and not str(device).startswith("cuda"):
        raise ValueError("Coefficient solver device must be cpu or cuda")
    if not np.any(weight):
        if mode == "mask":
            value = values * extra[None]
        else:
            length = np.sqrt(np.sum(values * values, axis=0))
            value = values * np.maximum(0, 1 - extra / np.maximum(length, 1e-32))[None]
        return value, {
            "iterations": 0,
            "relative_primal_dual_gap": 0.0,
            "absolute_primal_dual_gap": 0.0,
            "gap_scale": max(float(np.sum(values**2)) * 0.5, 1e-32),
            "converged": True,
            "zero_coefficients_fraction": float(np.mean(np.all(value == 0, axis=0))),
        }
    if str(device).startswith("cuda"):
        from .phase_sparse_cuda import coefficient_tv_cuda

        return coefficient_tv_cuda(values, weight, extra, mode, iterations, device)
    u = values.copy()
    v = values.copy()
    d = _gradient(u)
    b = np.zeros_like(d)
    c = np.zeros_like(values)
    scale = max(float(np.sum(values * values)) * 0.5, 1e-32)
    for n in range(iterations):
        u = _poisson_neumann((values - 16 * _divergence(d - b) + v - c) / 2, 8)
        g = _gradient(u)
        q = g + b
        length = np.sqrt(np.sum(q * q, axis=(0, 1)))
        d = q * np.maximum(0, 1 - weight / (16 * np.maximum(length, 1e-32)))[None, None]
        q0 = u + c
        if mode == "group":
            l0 = np.sqrt(np.sum(q0 * q0, axis=0))
            v = q0 * np.maximum(0, 1 - extra / np.maximum(l0, 1e-32))[None]
        else:
            v = q0 * extra[None]
        b += g - d
        c += u - v
        if mode == "mask":
            c *= ~extra[None]
        if (n + 1) % 8 == 0 or n + 1 == iterations:
            grad = _gradient(v)
            a = -_divergence(16 * b) + c
            primal = 0.5 * float(np.sum((v - values) ** 2)) + float(
                np.sum(weight * np.sqrt(np.sum(grad * grad, axis=(0, 1))))
            )
            if mode == "group":
                primal += float(np.sum(extra * np.sqrt(np.sum(v * v, axis=0))))
            lower = -0.5 * float(np.sum(a * a)) + float(np.sum(values * a))
            gap = (primal - lower) / scale
            if gap < -1e-9:
                raise ArithmeticError("Invalid coefficient-TV dual bound")
            gap = max(gap, 0)
            if gap < 1e-5:
                break
    return v, {
        "iterations": n + 1,
        "relative_primal_dual_gap": gap,
        "absolute_primal_dual_gap": gap * scale,
        "gap_scale": scale,
        "converged": gap < 1e-5,
        "zero_coefficients_fraction": float(np.mean(np.all(v == 0, axis=0))),
    }


def connected_support(mask, min_area=805):
    """Retain four-connected regions spanning a coefficient correlation area.

    The fixed default is ceil(4*pi*(sigma_native/2)^2), sigma_native=16. It is
    a spatial-support heuristic, not a calibrated confidence threshold.
    """
    mask = np.asarray(mask)
    if mask.ndim != 2 or mask.dtype != np.bool_:
        raise ValueError("Require a Boolean two-dimensional support mask")
    if not isinstance(min_area, (int, np.integer)) or isinstance(min_area, bool) or min_area < 1:
        raise ValueError("Minimum support area must be a positive integer")
    min_area = int(min_area)
    h, w = mask.shape
    seen = np.zeros_like(mask)
    out = np.zeros_like(mask)
    sizes = []
    kept = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        seen[y, x] = True
        stack = [(int(y), int(x))]
        points = []
        while stack:
            py, px = stack.pop()
            points.append((py, px))
            for ny, nx in [(py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)]:
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        sizes.append(len(points))
        if len(points) >= min_area:
            kept.append(len(points))
            yy, xx = zip(*points)
            out[yy, xx] = True
    return out, {
        "minimum_packed_area": min_area,
        "component_areas": sizes,
        "kept_component_areas": kept,
        "removed_pixels": int(np.count_nonzero(mask & ~out)),
    }


def sparse_support_refit(values, noise, covariance, *, device="cpu"):
    """TV16/group weight0.5 support, power9 mask, then TV4 on fixed support."""
    support, support_info = coefficient_tv(values, 16 * noise, 0.5 * noise, device=device)
    a, b, d = covariance
    power = np.maximum(
        0,
        (d * support[0] ** 2 - 2 * b * support[0] * support[1] + a * support[1] ** 2)
        / np.maximum(a * d - b * b, 1e-32),
    )
    mask, components = connected_support(power > 9)
    coeff, refit_info = coefficient_tv(values, 4 * noise, mask, mode="mask", device=device)
    support_info.update(
        mean_TV_weight=float(np.mean(16 * noise)),
        mean_group_weight=float(np.mean(0.5 * noise)),
        support_fraction=float(np.mean(mask)),
        component_filter=components,
        support_power_proxy="Gaussian32covariance,notnonlinearuncertainty",
    )
    return coeff, refit_info, support_info
