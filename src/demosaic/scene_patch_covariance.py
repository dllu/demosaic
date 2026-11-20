"""Use disjoint scene patches to condition a query's own Bayer innovation."""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.spatial.distance import cdist

SIZE = 16
STRIDE = 8
NEIGHBORS = 32
MODES = ("matched", "diagonal", "transposed", "nearby", "confirmed", "confirmed_diagonal")
VALIDATED_MODES = (
    "donor_validated",
    "validated_diagonal",
    "validated_transposed",
    "donor_and_query",
    "diagonal_and_query",
)


@dataclass(frozen=True)
class PatchBasis:
    green: np.ndarray
    projection: np.ndarray
    image: np.ndarray
    transpose: np.ndarray


@lru_cache(maxsize=4)
def patch_basis(colors):
    """Fit smooth nuisance terms and the same continuous modes on both greens."""
    green = np.flatnonzero(np.asarray(colors) == 1)
    if (len(colors), len(green)) != (4, 2):
        raise ValueError("Expected a Bayer layout with two green planes")
    # Coefficients are orthonormal on the delivered native grid. Exclude the
    # per-plane Nyquist limits and the low modes used for patch matching.
    frequency = np.arange(8) / (2 * SIZE)
    radius = np.hypot(frequency[:, None], frequency[None, :])
    smooth = np.argwhere(radius < 0.08)
    active = np.argwhere((radius >= 0.08) & (radius <= 0.224))
    pairs = np.concatenate((smooth, active))
    locations = (np.arange(SIZE) + 0.5) / SIZE
    basis = np.sqrt(2 / SIZE) * np.cos(np.pi * np.arange(8)[:, None] * locations)
    basis[0] = 1 / np.sqrt(SIZE)
    image = basis[pairs[:, 0], :, None] * basis[pairs[:, 1], None, :]
    sampled = np.stack([image[:, g // 2 :: 2, g % 2 :: 2] for g in green])
    design = sampled.reshape(2, len(pairs), -1).transpose(0, 2, 1)
    if not np.all(np.linalg.cond(design) < 8):
        raise ValueError("The selected detail modes are ill-conditioned on Bayer")
    projection = np.linalg.pinv(design)[:, len(smooth) :]
    lookup = {tuple(pair): i for i, pair in enumerate(active)}
    transpose = np.array([lookup[(x, y)] for y, x in active])
    return PatchBasis(green, projection, image[len(smooth) :], transpose)


def sample_windows(raw, coords):
    """Extract even-origin windows directly from physical CFA planes."""
    y, x = (coords.T // 2)[..., None, None]
    offsets = np.arange(SIZE // 2)
    return raw[:, y + offsets[:, None], x + offsets].transpose(1, 0, 2, 3)


def encode(windows, basis, shot, read):
    means = windows.mean(axis=(-1, -2), dtype=np.float64)
    green = windows[:, basis.green]
    quadrants = green.reshape(len(windows), 2, 2, SIZE // 4, 2, SIZE // 4)
    quadrants = quadrants.mean(axis=(1, 3, 5), dtype=np.float64).reshape(len(windows), 4)
    signal = means[:, basis.green].mean(axis=1)
    noise = np.sqrt(np.maximum(shot * signal + read, 1e-12))
    light = np.log(0.015 + np.maximum(means, 0))
    shape = (quadrants - signal[:, None]) / (0.02 + noise[:, None])
    descriptor = np.concatenate((light, np.clip(shape, -8, 8)), axis=1)
    coefficients = np.einsum("gkf,ngf->ngk", basis.projection, green.reshape(len(windows), 2, -1))
    valid = np.mean((windows < -0.02) | (windows > 0.96), axis=(1, 2, 3)) < 0.025
    return descriptor, coefficients, noise, valid


@dataclass(frozen=True)
class ExteriorPatches:
    coords: np.ndarray
    features: np.ndarray
    normalized: np.ndarray


def build_exterior(raw, colors, box, shot, read, *, max_windows=4800, halo=16):
    """Read only exterior CFA sites. Coordinates and thinning precede image reads."""
    x, y, w, h = box
    height, width = (2 * n for n in raw.shape[-2:])
    stride = max(SIZE, 2 * int(np.ceil(np.sqrt(height * width / max_windows) / 2)))
    yy, xx = np.meshgrid(
        np.arange(0, height - SIZE + 1, stride),
        np.arange(0, width - SIZE + 1, stride),
        indexing="ij",
    )
    safe = (yy + SIZE <= y - halo) | (yy >= y + h + halo)
    safe |= (xx + SIZE <= x - halo) | (xx >= x + w + halo)
    coords = np.column_stack((yy[safe], xx[safe]))
    if not len(coords):
        return None
    basis = patch_basis(tuple(colors))
    features, coefficients, noise, valid = encode(sample_windows(raw, coords), basis, shot, read)
    # Divide by the typical standard deviation of the average green fit.
    # Limit the leverage of a single high-contrast donor.
    normalized = coefficients / (np.sqrt(2) * noise[:, None, None])
    return ExteriorPatches(coords[valid], features[valid], np.clip(normalized[valid], -10, 10))


def choose_exterior(features, coords, exterior, *, nearby=False, ranked=False):
    feature_cost = cdist(features, exterior.features, metric="sqeuclidean")
    spatial = cdist(coords, exterior.coords, metric="sqeuclidean")
    spatial /= (4 * SIZE) ** 2
    distance = feature_cost + (spatial if nearby else 0.25 * np.log1p(spatial))
    count = min(NEIGHBORS, len(exterior.coords))
    index = np.argpartition(distance, count - 1, axis=1)[:, :count]
    if ranked:
        order = np.argsort(np.take_along_axis(distance, index, axis=1), axis=1, kind="stable")
        index = np.take_along_axis(index, order, axis=1)
    selected = np.take_along_axis(feature_cost, index, axis=1)
    weights = np.exp(-0.5 * selected)
    # A poor match shrinks the second moments toward zero.
    weights /= np.maximum(8, weights.sum(axis=1, keepdims=True))
    return exterior.normalized[index], weights


def covariance(donors, weights):
    """Estimate an uncentered, sign-invariant second moment with disjoint greens."""
    first, second = donors.transpose(2, 0, 1, 3)
    cross = np.einsum("bni,bnj->bij", weights[..., None] * first, second)
    return 0.375 * (cross + cross.swapaxes(-1, -2)) + (
        0.25 * cross.diagonal(axis1=-1, axis2=-2)[..., None, :] * np.eye(cross.shape[-1])
    )


def filter_innovation(moment, innovation, floor):
    gain, vectors = eigenfilter(moment, floor)
    projected = np.einsum("bik,bi->bk", vectors, innovation)
    return np.einsum("bik,bk->bi", vectors, gain * projected)


def eigenfilter(moment, floor):
    eigenvalues, vectors = np.linalg.eigh(moment)
    signal = np.maximum(eigenvalues - floor[:, None], 0)
    return signal / (1 + signal), vectors


def signed_support(observations, projected, sigma):
    """Require both physical greens to support the signed proposal."""
    scores = observations * np.sign(projected)[:, None, :] / sigma
    return np.clip((scores.min(axis=1) - 0.5) / 2, 0, 1)


def folded_weights(weights):
    """Normalize disjoint halves while retaining the reliability of the donor match."""
    totals = weights.sum(axis=-1, keepdims=True)
    proba = weights / np.maximum(totals, 1e-30)
    square_sum = np.sum(proba**2, axis=-1, keepdims=True)
    supported = (square_sum <= 0.25) & (totals > 0)
    return proba, square_sum, supported


def confirmed_power(products, weights, noise_power):
    """Lower signed cross-power estimate from held-out pairs of physical greens."""
    p, square_sum, supported = folded_weights(weights)
    mean = np.einsum("bn,bnk->bk", p, products)
    squared_error = (products - mean[:, None]) ** 2
    variance = np.einsum("bn,bnk->bk", p**2, squared_error) / np.maximum(1 - square_sum, 1e-6)
    standard_error = np.sqrt(np.maximum(variance, noise_power * square_sum))
    return np.maximum(mean - 2 * standard_error, 0) * supported


def donor_validated_fields(donors, weights, innovation, coefficients, noise, basis):
    """Fit directions in one donor half and estimate their power in the other."""
    result = {key: np.zeros_like(innovation) for key in VALIDATED_MODES}
    if donors.shape[1] < 8:
        return result
    gram = basis.projection @ basis.projection.swapaxes(-1, -2)
    coefficient_var = gram.diagonal(axis1=-1, axis2=-2)
    match_strength = np.minimum(weights.sum(axis=1, keepdims=True), 1)
    diagonal_support = signed_support(
        coefficients, innovation, noise[:, None, None] * np.sqrt(coefficient_var)
    )
    for start in (0, 1):
        discover, validate = donors[:, start::2], donors[:, 1 - start :: 2]
        p, _, eligible = folded_weights(weights[:, start::2])
        held = weights[:, 1 - start :: 2]
        moment = covariance(discover, p)
        diagonal_only = np.maximum(moment.diagonal(axis1=-1, axis2=-2), 0)
        checked = confirmed_power(
            validate[:, :, 0] * validate[:, :, 1], held, np.prod(coefficient_var, axis=0) / 4
        )
        signal = np.minimum(checked, diagonal_only) * match_strength * eligible
        update = innovation * signal / (1 + signal) * 0.5
        result["validated_diagonal"] += update
        result["diagonal_and_query"] += update * diagonal_support

        eig, vectors = np.linalg.eigh(moment)
        observations = np.einsum("bik,bngi->bngk", vectors, validate)
        variances = np.einsum("bik,gij,bjk->bgk", vectors, gram, vectors, optimize=True)
        checking_noise = np.prod(variances, axis=1) / 4
        powers = confirmed_power(
            observations[:, :, 0] * observations[:, :, 1], held, checking_noise
        )
        signal = np.minimum(powers, np.maximum(eig, 0)) * match_strength * eligible
        gain = 0.5 * signal / (1 + signal)
        projected = np.einsum("bik,bi->bk", vectors, innovation)
        result["donor_validated"] += np.einsum("bik,bk->bi", vectors, gain * projected)
        observed = np.einsum("bik,bgi->bgk", vectors, coefficients)
        support = signed_support(observed, projected, noise[:, None, None] * np.sqrt(variances))
        result["donor_and_query"] += np.einsum("bik,bk->bi", vectors, gain * projected * support)

        wrong = vectors[:, basis.transpose]
        wrong_projection = np.einsum("bik,bi->bk", wrong, innovation)
        result["validated_transposed"] += np.einsum("bik,bk->bi", wrong, gain * wrong_projection)
    return result


def single_donor_fit(
    donors, weights, innovation, coefficients, noise, basis, neighbors, nearby_weights
):
    """Previous single estimate of covariance and its original controls."""
    matched = covariance(donors, weights)
    # Finite sample noise alone yields positive eigenvalues after PSD
    # projection. Use the same dimension-dependent empirical allowance
    # for the full moment and its diagonal control.
    floor = np.sqrt(len(basis.image) * np.sum(weights**2, axis=1))
    rotated = matched[:, basis.transpose][:, :, basis.transpose]
    diagonal = np.maximum(matched.diagonal(axis1=-1, axis2=-2) - floor[:, None], 0)
    local = covariance(neighbors, nearby_weights)
    local_floor = np.sqrt(len(basis.image) * np.sum(nearby_weights**2, axis=1))
    gain, vectors = eigenfilter(matched, floor)
    projected = np.einsum("bik,bi->bk", vectors, innovation)
    observed = np.einsum("bik,bgi->bgk", vectors, coefficients)
    exact_projection = np.einsum("bik,gip->bgkp", vectors, basis.projection)
    sigma = noise[:, None, None] * np.linalg.norm(exact_projection, axis=-1)
    support = signed_support(observed, projected, sigma)
    diagonal_sigma = noise[:, None, None] * np.linalg.norm(basis.projection, axis=-1)
    diagonal_gain = innovation * (diagonal / (1 + diagonal))
    return {
        "matched": np.einsum("bik,bk->bi", vectors, gain * projected),
        "diagonal": diagonal_gain,
        "transposed": filter_innovation(rotated, innovation, floor),
        "nearby": filter_innovation(local, innovation, local_floor),
        "confirmed": np.einsum("bik,bk->bi", vectors, gain * projected * support),
        "confirmed_diagonal": diagonal_gain
        * signed_support(coefficients, innovation, diagonal_sigma),
    }


def corrections(raw, parent_green, colors, shot, read, box, exterior, *, validate_donors=False):
    """Return fixed-basis luminance corrections from the query measurements."""
    height, width = parent_green.shape
    modes = VALIDATED_MODES if validate_donors else MODES
    results = {key: np.zeros_like(parent_green) for key in modes}
    if exterior is None or not len(exterior.coords) or min(height, width) < SIZE:
        return results

    basis = patch_basis(tuple(colors))
    yy, xx = np.meshgrid(
        np.arange(0, height - SIZE + 1, STRIDE),
        np.arange(0, width - SIZE + 1, STRIDE),
        indexing="ij",
    )
    coords = np.column_stack((yy.ravel(), xx.ravel()))
    windows = sample_windows(raw, coords)
    features, coefficients, noise, valid = encode(windows, basis, shot, read)
    offsets = np.arange(SIZE)
    grid_y = coords[:, 0, None, None] + offsets[:, None]
    grid_x = coords[:, 1, None, None] + offsets
    parent_windows = parent_green[grid_y, grid_x]
    parent_fits = np.einsum(
        "gkf,ngf->ngk",
        basis.projection,
        np.stack([parent_windows[:, g // 2 :: 2, g % 2 :: 2] for g in basis.green], axis=1).reshape(
            len(coords), 2, -1
        ),
    )
    innovation = (coefficients - parent_fits).mean(axis=1) * valid[:, None]
    global_coords = coords + np.asarray(box)[[1, 0]]
    donors, weights = choose_exterior(features, global_coords, exterior, ranked=validate_donors)
    if validate_donors:
        values = donor_validated_fields(donors, weights, innovation, coefficients, noise, basis)
    else:
        neighbors, nearby_weights = choose_exterior(features, global_coords, exterior, nearby=True)
        values = single_donor_fit(
            donors, weights, innovation, coefficients, noise, basis, neighbors, nearby_weights
        )
    taper = np.sin((offsets + 0.5) * np.pi / SIZE) ** 2
    window = taper[:, None] * taper[None, :]
    normal = np.zeros_like(parent_green)
    np.add.at(normal, (grid_y, grid_x), np.broadcast_to(window, parent_windows.shape))
    for key, value in values.items():
        delta = np.einsum("nk,kyx->nyx", value, basis.image)
        np.add.at(results[key], (grid_y, grid_x), delta * window)
        # In a tile interior the windows sum to one. Keep the outer taper.
        results[key] /= np.maximum(1, normal)
    return results
