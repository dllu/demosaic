"""Experimental correction for one isolated straight guide outside a native query."""

from dataclasses import dataclass

import numpy as np

from .cfa import PATTERNS


@dataclass(frozen=True)
class Guide:
    normal: tuple[float, float]  # (x, y), signed normal to the distant line
    offset: float
    color: tuple[float, float, float]  # signed camera-RGB unit vector
    strength: float
    samples: int


def coordinates(height, width, *, phase=False, origin=(0, 0)):
    step = 2 if phase else 1
    x = origin[0] + step * np.arange(width, dtype=np.float64)
    y = origin[1] + step * np.arange(height, dtype=np.float64)
    return np.meshgrid(x, y)


def native_sites(shape, origin):
    height, width = shape
    x, y = coordinates(height, width, phase=True, origin=origin)
    return np.stack([x, x + 1, x, x + 1]), np.stack([y, y, y + 1, y + 1])


def fit(design, values, variance):
    base = np.maximum(variance, 1e-12) ** -1
    weights = base
    for iteration in range(3):
        normal = design.T @ (weights[:, None] * design)
        right = design.T @ (weights * values)
        value = np.linalg.solve(normal, right)
        if iteration < 2:
            normalized = np.abs(design @ value - values) * np.sqrt(base)
            weights = base * np.minimum(1, 3 / np.maximum(normalized, 1e-12))
    errors = np.sqrt(np.diag(np.linalg.inv(normal)))
    return value, errors


def gaussian_profile(offset, width):
    taper = np.clip(4 - np.abs(offset) / width, 0, 1)
    return np.exp(-0.5 * (offset / width) ** 2) * taper**2 * (3 - 2 * taper)


def external_guide(scene, variance, colors, box, *, min_z=5.5):
    """Use exterior RAW only. A diffuse or unsupported line yields no guide."""
    from scipy.ndimage import gaussian_filter

    x, y = coordinates(*scene.shape[-2:], phase=True)
    x += 0.5
    y += 0.5
    left, top, width, height = box
    distance = np.maximum.reduce([left - x, x - left - width + 1, top - y, y - top - height + 1])
    exterior = distance >= 32
    if not exterior.any():
        return None
    baseline = np.where(exterior, scene, 0.0)

    # Normalize filtered values by visible weights to protect the excluded core.
    def smooth(radius):
        weights = gaussian_filter(exterior.astype(float), radius)
        return gaussian_filter(baseline, (0, radius, radius)) / np.maximum(weights, 1e-9)

    band = smooth(0.82) - smooth(3.25)
    scatter = np.sqrt(np.maximum(variance, 1e-12)) * 0.32
    score = (np.abs(band) / scatter).max(0)
    level = max(min_z, 0.60 * float(score[exterior].max()))
    active = (score >= level) & exterior
    if active.sum() < 36:
        return None
    points = np.stack([x[active], y[active]], axis=-1)
    weights = (score[active] - level + 1).clip(max=12)
    center = np.average(points, axis=0, weights=weights)
    centered = points - center
    covariance = centered.T @ (weights[:, None] * centered) / weights.sum()
    eigenvalues, axes = np.linalg.eigh(covariance)
    if eigenvalues[1] < 2500 or eigenvalues[0] > 12:
        return None
    tangent = axes[:, 1]
    side = (points - np.array([left + (width - 1) / 2, top + (height - 1) / 2])) @ tangent
    if min((side < -64).sum(), (side > 64).sum()) < 16:
        return None
    normal = axes[:, 0]
    offset = center @ normal
    # Estimate the signed color vector from its native exterior sensor sites.
    xn, yn = native_sites(scene.shape[-2:], (0, 0))
    d = normal[0] * xn + normal[1] * yn - offset
    amplitude = []
    errors = []
    for c in range(3):
        selected = (np.asarray(colors)[:, None, None] == c) & exterior[None] & (np.abs(d) <= 13)
        if selected.sum() < 36:
            return None
        coefficients, std = fit(
            np.column_stack(
                [
                    np.ones(selected.sum()),
                    (xn[selected] - center[0]) / 256,
                    (yn[selected] - center[1]) / 256,
                    gaussian_profile(d[selected], 2.6),
                ]
            ),
            scene[selected],
            variance[selected],
        )
        amplitude.append(coefficients[-1])
        errors.append(std[-1])
    strength = np.linalg.norm(np.asarray(amplitude) / errors)
    if strength < 12:
        return None
    signed = np.asarray(amplitude) / np.linalg.norm(amplitude)
    return Guide(tuple(normal), float(offset), tuple(signed), float(strength), int(active.sum()))


def features(x, y, band, colors, origin, shape):
    left, top = origin
    height, width = shape
    u, v = (
        (x - left - (width - 1) / 2) / max(width, 1),
        (y - top - (height - 1) / 2) / max(height, 1),
    )
    one = np.eye(3)[colors]
    return np.concatenate((one, one * u[:, None], one * v[:, None], band[:, None]), axis=-1)


def supported_correction(
    base,
    packed,
    variance,
    colors,
    origin,
    guide,
    *,
    segment=None,
    threshold=2.5,
    width=1.2,
    evidence_only=False,
):
    """Use a common section for both independently fitted CFA halves."""
    if guide is None:
        return base, []
    height, query_width = base.shape[-2:]
    xn, yn = native_sites(packed.shape[-2:], origin)
    x, y = coordinates(height, query_width, origin=origin)
    n0, n1 = guide.normal
    d = n0 * xn + n1 * yn - guide.offset
    t = -n1 * (xn - origin[0] - (query_width - 1) / 2) + n0 * (yn - origin[1] - (height - 1) / 2)
    rgb_d = n0 * x + n1 * y - guide.offset
    rgb_t = -n1 * (x - origin[0] - (query_width - 1) / 2) + n0 * (y - origin[1] - (height - 1) / 2)
    chroma = np.asarray(guide.color)
    c = np.broadcast_to(np.asarray(colors)[:, None, None], packed.shape)
    chosen = (np.abs(d) < 9) & (packed > -0.029) & (packed < 0.985)
    folds = (xn // 2 + yn // 2).astype(int) % 2
    evidence = []
    amplitude = np.zeros((height, query_width), dtype=np.float64)
    support = np.zeros_like(amplitude)
    centers = [0.0] if segment is None else np.arange(-192, 193, segment / 2)
    for center in centers:
        if segment is None:
            local = chosen
            delivery = np.ones_like(amplitude)
        else:
            local = chosen & (np.abs(t - center) <= segment / 2)
            delivery = np.maximum(1 - np.abs(rgb_t - center) / (segment / 2), 0)
        if local.sum() < 180 or np.count_nonzero(delivery * (np.abs(rgb_d) <= 4 * width)) < 40:
            continue
        out = []
        for side in (0, 1):
            pick = local & (folds == side)
            if pick.sum() < 80 or np.unique(c[pick]).size != 3:
                break
            design = features(
                xn[pick],
                yn[pick],
                gaussian_profile(d[pick], width) * chroma[c[pick]],
                c[pick],
                origin,
                (height, query_width),
            )
            value, sigma = fit(design, packed[pick], variance[pick])
            out.append((value[-1], sigma[-1]))
        if len(out) != 2:
            continue
        snr = min(v / s for v, s in out)
        evidence.append(
            {
                "tangent": float(center),
                "minimum_snr": float(snr),
                "pooled_signed_score": float(sum(v / s for v, s in out) / np.sqrt(2)),
            }
        )
        support += delivery
        if evidence_only or snr <= threshold:
            continue
        at = (yn[local] - origin[1]).astype(int)
        across = (xn[local] - origin[0]).astype(int)
        rows = features(
            xn[local],
            yn[local],
            gaussian_profile(d[local], width) * chroma[c[local]],
            c[local],
            origin,
            (height, query_width),
        )
        physical, _ = fit(rows, packed[local], variance[local])
        parent, _ = fit(rows, base[c[local], at, across], variance[local])
        blend = min(1.0, max(0.0, (snr - threshold) / 2))
        amplitude += delivery * blend * (physical[-1] - parent[-1])
    if not np.any(amplitude):
        return base, evidence
    section = gaussian_profile(rgb_d, width) * (amplitude / np.maximum(support, 1e-9))
    return (base + chroma[:, None, None] * section).astype(base.dtype), evidence


def keep_local_support(parent, correction, packed, variance, colors, origin, guide):
    """Keep the long-window amplitude where narrow windows still support a line."""
    if guide is None or correction is parent or np.array_equal(parent, correction):
        return parent, []
    _, evidence = supported_correction(
        parent, packed, variance, colors, origin, guide, segment=24, evidence_only=True
    )
    height, width = parent.shape[-2:]
    x, y = coordinates(height, width, origin=origin)
    n0, n1 = guide.normal
    tangent = -n1 * (x - origin[0] - (width - 1) / 2) + n0 * (y - origin[1] - (height - 1) / 2)
    positions = np.arange(-192, 193, 12, dtype=float)
    values = {r["tangent"]: r["pooled_signed_score"] for r in evidence}
    z = np.array([values.get(p, 0) for p in positions])
    strength = np.clip(z - 2, 0, 1)
    strength = strength**2 * (3 - 2 * strength)
    taper = np.interp(tangent, positions, strength, left=0, right=0)
    result = parent.astype(float) + taper[None] * (correction.astype(float) - parent)
    return result.astype(parent.dtype), evidence


def refine_isolated_raw_line(parent, scene, variance, colors, box):
    """Return the optional correction for a phase-aligned native 256×256 query.

    ``scene`` and ``variance`` are NumPy arrays in four packed Bayer phases.
    ``parent`` is camera-linear RGB for the same 256×256 box in native scene
    coordinates, before WB. The fixed experimental policy uses 64-pixel
    amplitude estimates with a 24-pixel support check. A missing or
    numerically unsupported proposal preserves the parent. Requires the
    evaluation extra for SciPy.
    """
    if (
        not all(isinstance(v, np.ndarray) for v in (scene, variance, parent))
        or scene.ndim != 3
        or scene.shape[0] != 4
        or variance.shape != scene.shape
        or parent.shape != (3, 256, 256)
        or not all(np.issubdtype(v.dtype, np.floating) for v in (scene, variance, parent))
        or not all(np.isfinite(v).all() for v in (scene, variance, parent))
        or (variance < 0).any()
    ):
        raise ValueError("Require finite floating Bayer, variance and native camera-RGB arrays")
    if np.shape(colors) != (4,) or tuple(colors) not in PATTERNS.values():
        raise ValueError("Require the actual Bayer phase colors")
    colors = tuple(int(value) for value in colors)
    if (
        len(box) != 4
        or any(not isinstance(v, (int, np.integer)) for v in box)
        or tuple(box[2:]) != (256, 256)
        or min(box[:2]) < 0
        or any(v % 2 for v in box[:2])
        or box[0] + 256 > scene.shape[2] * 2
        or box[1] + 256 > scene.shape[1] * 2
    ):
        raise ValueError("Require an even-origin 256×256 box inside the Bayer scene")
    if not np.any(variance):
        return parent
    x, y = box[0] // 2, box[1] // 2
    query = np.s_[:, y : y + 128, x : x + 128]
    args = (scene[query], variance[query], colors, box[:2])
    try:
        guide = external_guide(scene, variance, colors, box)
        candidate, _ = supported_correction(parent, *args, guide, segment=64)
        result, _ = keep_local_support(parent, candidate, *args, guide)
    except np.linalg.LinAlgError:
        return parent
    return result if np.isfinite(result).all() else parent
