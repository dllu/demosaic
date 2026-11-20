"""Opt-in restoration for repeating mesh supported by nearby Bayer RAW."""

import numpy as np

from .cfa import PATTERNS

_ROI_SIZE = 160
_WINDOW = 64
_POOLED_HALO = 16
_POOLED_FOOTPRINT = _ROI_SIZE + 2 * _POOLED_HALO
_DONOR = 128
_FFT_SIZE = 256
_FREQUENCIES = np.fft.fftfreq(_FFT_SIZE, d=2)
_FY, _FX = np.meshgrid(_FREQUENCIES, _FREQUENCIES, indexing="ij")
_RADIUS = np.hypot(_FX, _FY)
_SEARCH = (_FX >= 0.021) & (abs(_FY) >= 0.012) & (_RADIUS >= 0.041) & (_RADIUS <= 0.22)
_SECTORS = (_SEARCH & (_FY > 0), _SEARCH & (_FY < 0))
_DONOR_TAPER = np.sin(np.pi * (np.arange(_DONOR // 2) + 0.5) / (_DONOR // 2))
_DONOR_TAPER = np.outer(_DONOR_TAPER, _DONOR_TAPER).astype(np.float32)
_OVERLAP = np.sin(np.pi * (np.arange(_WINDOW) + 0.5) / _WINDOW) ** 2
_OVERLAP = np.outer(_OVERLAP, _OVERLAP)
_X, _Y = np.meshgrid(np.arange(_WINDOW, dtype=np.float64), np.arange(_WINDOW, dtype=np.float64))


def _cosine_background(size):
    y, x = (np.indices((size, size), dtype=np.float64) + 0.5) / size
    order = int(np.ceil(0.066 * size))
    return np.stack(
        [
            np.cos(np.pi * i * x) * np.cos(np.pi * j * y)
            for i in range(order + 1)
            for j in range(order + 1)
            if np.hypot(i, j) <= order
        ],
        axis=-1,
    )


_SMOOTH = _cosine_background(_WINDOW)
_EDGE = np.minimum(
    1.0, np.minimum(np.arange(_ROI_SIZE) + 0.5, np.arange(_ROI_SIZE)[::-1] + 0.5) / 12
)


def _positions(colors, x, y):
    return tuple(
        (row, column)
        for row in range(2)
        for column in range(2)
        if colors[2 * ((y + row) % 2) + (x + column) % 2] == 1
    )


def _sites(scene, x, y, size, row, column):
    xx, yy = x + column, y + row
    plane = 2 * (yy % 2) + (xx % 2)
    return scene[plane, yy // 2 : yy // 2 + size // 2, xx // 2 : xx // 2 + size // 2]


def _peaks(power):
    coords = [
        np.unravel_index(np.where(mask, power, -np.inf).argmax(), power.shape) for mask in _SECTORS
    ]
    return np.asarray([(_FX[c], _FY[c]) for c in coords])


def _spacing(scene, colors, x, y, *, clearance=0):
    from scipy.fft import fft2

    # A verifier may sample beyond the delivery ROI. Keep its entire footprint
    # clear of the frequency donors when running a held-sample experiment.
    boxes = (
        (x - _DONOR - clearance, y + 16),
        (x + _ROI_SIZE + clearance, y + 16),
        (x + 16, y - _DONOR - clearance),
        (x + 16, y + _ROI_SIZE + clearance),
    )
    if any(
        a < 0 or b < 0 or a + _DONOR > 2 * scene.shape[2] or b + _DONOR > 2 * scene.shape[1]
        for a, b in boxes
    ):
        return None
    powers = []
    for dx, dy in boxes:
        channels = []
        for row, column in _positions(colors, dx, dy):
            green = _sites(scene, dx, dy, _DONOR, row, column)
            weighted = (green - (_DONOR_TAPER * green).sum() / _DONOR_TAPER.sum()) * _DONOR_TAPER
            response = fft2(weighted, s=(_FFT_SIZE, _FFT_SIZE))
            response *= np.exp(-2j * np.pi * (_FY * row + _FX * column)).astype(np.complex64)
            channels.append(response / np.sqrt((_DONOR_TAPER**2).sum()))
        powers.append(abs(np.stack(channels).mean(axis=0)) ** 2)
    banks = np.stack(powers)
    banks /= np.maximum(banks[:, _SEARCH].mean(axis=1)[:, None, None], 1e-10)
    pair = _peaks(banks.mean(axis=0))
    counts = (np.linalg.norm(np.stack([_peaks(p) for p in banks]) - pair, axis=-1) <= 0.009).all(
        axis=1
    )
    radial, angle = np.linalg.norm(pair, axis=-1), abs(pair[:, 1] / pair[:, 0])
    if counts.any() and np.all(
        (radial >= 0.077) & (radial <= 0.195) & (angle >= 0.26) & (angle <= 3.8)
    ):
        return pair
    return None


def _fold(design, measurements, positions, shot, read):
    A, B = [design[y::2, x::2].reshape(-1, design.shape[-1]) for y, x in positions]
    u, v = measurements
    gram = A.T @ A
    moment = A.T @ u
    coefficients = np.linalg.solve(gram, moment)
    residual = v - B @ coefficients
    fit_error = residual @ residual
    variance = max(2e-11, shot * max(0.0, float(u.mean())) + read)
    support = []
    for family in range(2):
        keep = np.ones(len(moment), dtype=bool)
        keep[len(moment) - 4 + family :: 2] = False
        holdout = v - B[:, keep] @ np.linalg.solve(gram[keep][:, keep], moment[keep])
        support.append((holdout @ holdout - fit_error) / variance)
    return coefficients[-4:].reshape(2, 2).T, support


def _patch(scene, parent, xy, colors, design, carriers, shot, read):
    x, y = xy
    sites = _positions(colors, x, y)
    measures = [_sites(scene, x, y, _WINDOW, r, c).astype(np.float64).ravel() for r, c in sites]
    first, second = (
        _fold(design, order, phase, shot, read)
        for order, phase in ((measures, sites), (measures[::-1], sites[::-1]))
    )
    support = np.maximum(0, np.minimum(first[1], second[1]) - 6.0)
    if not support.any():
        return None
    measured = (first[0] + second[0]) * 0.5
    flattened = design.reshape(-1, design.shape[-1])
    existing = (
        np.linalg.solve(flattened.T @ flattened, flattened.T @ parent.ravel())[-4:].reshape(2, 2).T
    )
    correction = (measured - existing) * (support / (support + 6))[:, None]
    extent = np.linalg.norm(measured, axis=-1)
    correction *= np.minimum(1, extent / np.linalg.norm(correction, axis=-1).clip(min=1e-10))[
        :, None
    ]
    return (carriers @ correction.T.ravel()).astype(np.float32)


def refine_raw_mesh_carriers(
    parent,
    scene,
    colors,
    roi,
    *,
    shot,
    read,
    white_balance,
    camera_to_srgb,
    method="local64",
    parent_context=None,
    donor_clearance=None,
):
    """Refine a co-registered 160×160 linear camera RGB crop using noisy RAW.

    Parent contains restored RGB in the native ROI. Scene contains the
    surrounding Bayer data as four packed spatial phases. The rectangle
    uses native (x, y, width, height) coordinates, and colors indexes RGB
    for each phase. Supply the input shot/read prior, camera gains and
    camera-to-sRGB matrix. The fit uses four nearby 128-pixel RAW patches
    and may return the parent when support is weak.

    The default method is `"local64"`. The experimental `"pooled"` method
    accepts a 192×192 RGB `parent_context` with the exact parent crop centered
    inside it. It pools the weaker carrier's phase across this footprint
    and validates it on held Bayer samples inside each delivery window.
    It retains the planar fit where the direction ranking or evidence is
    ambiguous. The experimental `"pooled-color"` method also uses nearby red
    and blue phase evidence and lets each direction qualify when the rank
    is ambiguous. The final fit still requires reciprocal green support.
    The experimental `"ring-posterior"` method uses an exterior Bayer
    prior and averages the no-wire, one-wire and two-wire models in each
    delivery window. It estimates the inherited correction on the parent
    crop itself. The experimental `"weak-posterior"` method requires a
    192×192 parent context and uses the ring prior only in the weaker
    direction when both green lattices agree on the ranking. It preserves
    the stronger correction from the combined broad and central check.
    Donor clearance defaults to zero for `"local64"` and 16 pixels for
    the other methods.

    Requires the eval extra. Calibrated for a repeating two-family mesh.
    """
    if scene.ndim != 3 or scene.shape[0] != 4 or not np.issubdtype(scene.dtype, np.floating):
        raise ValueError("scene must contain four packed floating-point Bayer phases")
    if (
        parent.shape != (3, _ROI_SIZE, _ROI_SIZE)
        or not np.issubdtype(parent.dtype, np.floating)
        or not np.isfinite(parent).all()
    ):
        raise ValueError("parent must be a finite floating-point RGB crop with shape (3, 160, 160)")
    colors = tuple(colors)
    if colors not in PATTERNS.values():
        raise ValueError("colors must describe a Bayer CFA pattern")
    if not np.isfinite((shot, read)).all() or min(shot, read) < 0 or shot + read == 0:
        raise ValueError("shot and read must describe positive RAW noise variance")
    wb, matrix = np.asarray(white_balance), np.asarray(camera_to_srgb)
    if (
        wb.shape != (3,)
        or matrix.shape != (3, 3)
        or np.any(wb <= 0)
        or not np.isfinite(wb).all()
        or not np.isfinite(matrix).all()
    ):
        raise ValueError("white_balance and camera_to_srgb must describe valid camera color")
    x, y, w, h = roi
    if not all(isinstance(v, (int, np.integer)) for v in (x, y, w, h)) or (w, h) != (
        _ROI_SIZE,
        _ROI_SIZE,
    ):
        raise ValueError("roi must be a 160×160 native integer rectangle")
    x, y, w, h = map(int, (x, y, w, h))
    if min(x, y) < 0 or x + w > 2 * scene.shape[2] or y + h > 2 * scene.shape[1]:
        raise ValueError("roi must be contained in the Bayer scene")
    methods = ("local64", "pooled", "pooled-color", "ring-posterior", "weak-posterior")
    if method not in methods:
        raise ValueError(f"method must be one of {methods}")
    pooled = method in ("pooled", "pooled-color")
    needs_context = pooled or method == "weak-posterior"
    minimum_clearance = 0 if method == "local64" else _POOLED_HALO
    clearance = minimum_clearance if donor_clearance is None else donor_clearance
    if (
        isinstance(clearance, (bool, np.bool_))
        or not isinstance(clearance, (int, np.integer))
        or clearance < minimum_clearance
    ):
        raise ValueError(f"donor_clearance must be an integer of at least {minimum_clearance}")
    if needs_context:
        if parent_context is None:
            raise ValueError(f"{method} method requires a 192×192 parent_context")
        parent_context = np.asarray(parent_context)
        interior = np.s_[:, _POOLED_HALO:-_POOLED_HALO, _POOLED_HALO:-_POOLED_HALO]
        if (
            parent_context.shape != (3, _POOLED_FOOTPRINT, _POOLED_FOOTPRINT)
            or parent_context.dtype != parent.dtype
            or not np.isfinite(parent_context).all()
            or not np.array_equal(parent_context[interior], parent)
        ):
            raise ValueError(
                "parent_context must contain the exact RGB parent and its 16-pixel halo"
            )
    elif parent_context is not None:
        raise ValueError("parent_context is used by the pooled and weak-posterior methods")
    frequencies = _spacing(scene, colors, x, y, clearance=int(clearance))
    if frequencies is None:
        return parent
    try:
        neutral = np.linalg.solve(matrix, np.ones(3)) / wb
        if neutral[1] == 0:
            return parent
        if method == "ring-posterior":
            from ._mesh_presence import _refine

            return _refine(
                parent, scene, colors, (x, y), frequencies, shot, read, neutral / neutral[1]
            )
        if method == "weak-posterior":
            from ._mesh_weak_posterior import _refine

            return _refine(
                parent,
                parent_context,
                scene,
                colors,
                (x, y),
                frequencies,
                shot,
                read,
                neutral / neutral[1],
            )
        if pooled:
            from ._mesh_pooled import _refine

            return _refine(
                parent,
                parent_context[1],
                scene,
                colors,
                (x, y),
                frequencies,
                shot,
                read,
                neutral / neutral[1],
                regional_color=method == "pooled-color",
            )
        angle = (
            2
            * np.pi
            * (
                (_X[..., None] - (_WINDOW - 1) / 2) * frequencies[:, 0]
                + (_Y[..., None] - (_WINDOW - 1) / 2) * frequencies[:, 1]
            )
        )
        carriers = np.concatenate((np.cos(angle), np.sin(angle)), axis=-1)
        design = np.concatenate((_SMOOTH, carriers), axis=-1)
        signal = np.zeros((h, w))
        mass = np.zeros_like(signal)
        for dy in range(0, h - _WINDOW + 1, _WINDOW // 2):
            for dx in range(0, w - _WINDOW + 1, _WINDOW // 2):
                tile = np.s_[dy : dy + _WINDOW, dx : dx + _WINDOW]
                delta = _patch(
                    scene, parent[1][tile], (x + dx, y + dy), colors, design, carriers, shot, read
                )
                if delta is not None:
                    signal[tile] += delta * _OVERLAP
                mass[tile] += _OVERLAP
    except np.linalg.LinAlgError:
        return parent
    if not np.any(signal):
        return parent
    delta = (signal / np.maximum(0.02, mass)) * _EDGE[:, None] * _EDGE[None, :]
    rgb = ((neutral / neutral[1])[:, None, None] * delta).astype(parent.dtype)
    if not np.isfinite(rgb).all():
        return parent
    return parent + np.asarray(0.73, dtype=parent.dtype) * rgb
