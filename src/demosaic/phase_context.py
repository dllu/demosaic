"""Larger measured-RAW contexts propose additional local periodic detail.

Selection and fitting reuse noisy input. Coherence, covariance and support are
heuristics, not calibrated confidence. Small images use the existing sparse fit.
"""

import time

import numpy as np

from .phase_context_frequency import frequency_fit
from .phase_frequency import fit_refined
from .phase_harmonic import _fit_selected_harmonics, _origins, green_pair
from .phase_noise_floor import estimate_variance_floor
from .phase_tv import _correct_fitted_patch


def _band_peaks(pair, low, high):
    fx, fy = pair["native_fx"], pair["native_fy"]
    radius = np.hypot(fx, fy)
    valid = (
        (radius >= low)
        & (radius <= high)
        & (np.abs(fx) < 0.25)
        & (np.abs(fy) < 0.25)
        & (fy > 0)
        & (pair["signed_coherence"] > 0.8)
    )
    score = np.where(valid, pair["noise_units_signed_cross"], -np.inf).copy()
    peaks = []
    for _ in range(4):
        p = np.unravel_index(np.argmax(score), score.shape)
        if score[p] < 5:
            break
        px, py = float(fx[p]), float(fy[p])
        peaks.append((px, py, float(score[p])))
        dx = np.abs(fx - px)
        dx = np.minimum(dx, 0.5 - dx)
        dy = np.abs(fy - py)
        score[dx * dx + dy * dy <= (4 / 256) ** 2] = -np.inf
    return peaks


def context_frequencies(packed, variance, colors, *, return_noise_floor=False):
    """Up to four candidates per band, using actual physical Bayer samples."""
    if not np.any(np.asarray(variance) > 0):
        result = ([], [], {"added_pixel_variance": 0.0, "ADC_only_bypass": True})
        return result if return_noise_floor else result[:2]
    pair = green_pair(packed, variance, colors)
    if pair["noise_units_signed_cross"] is None:
        result = ([], [], {"added_pixel_variance": 0.0, "variance_unavailable": True})
        return result if return_noise_floor else result[:2]
    floor = estimate_variance_floor(pair)
    added = floor["added_pixel_variance"]
    if added > 0:
        pair = green_pair(packed, np.asarray(variance, np.float64) + added, colors)
    candidates = _band_peaks(pair, 0.03, 0.22) + _band_peaks(pair, 0.22, 0.34)
    refined, searches = [], []
    for k, (fx, fy, score) in enumerate(candidates):
        radius = 0.22 if np.hypot(fx, fy) <= 0.22 else 0.34
        (nx, ny), info = frequency_fit(packed, colors, (fx, fy), max_radius=radius)
        others = [p for j, p in enumerate(candidates) if j != k] + refined
        if any(np.hypot(nx - p[0], ny - p[1]) < 2 / 256 for p in others):
            info["collision_fallback"] = True
        else:
            fx, fy = nx, ny
        refined.append((fx, fy, score))
        searches.append(info)
    result = (refined, searches, floor)
    return result if return_noise_floor else result[:2]


def correct_context_patch(
    packed,
    variance,
    colors,
    base,
    peaks,
    *,
    device="cpu",
    variance_floor=0.0,
    cross_phase_support=False,
):
    """Use effective local variances and add separated measured frequencies."""
    packed, variance, base = [np.asarray(v, np.float64) for v in (packed, variance, base)]
    if not np.isfinite(variance_floor) or variance_floor < 0:
        raise ValueError("Variance floor must be finite and nonnegative")
    clipped = bool(np.any(packed >= 1 - 1e-7))
    if not clipped and variance_floor > 0:
        variance = variance + variance_floor
    original = fit_refined(packed, variance, colors, base)
    if clipped or not peaks:
        value, info = _correct_fitted_patch(
            original,
            device=device,
            refine_frequency=True,
            sparse_support=True,
            cross_phase_support=cross_phase_support,
        )
        info["context_clipped_local_fallback"] = clipped
        info["context_variance_floor"] = 0.0 if clipped else float(variance_floor)
        return value, info
    selected = list(original["peaks"])
    count = len(selected)
    for p in peaks:
        if all(np.hypot(p[0] - q[0], p[1] - q[1]) >= 2 / 256 for q in selected):
            selected.append(p)
    if len(selected) == count:
        return _correct_fitted_patch(
            original,
            device=device,
            refine_frequency=True,
            sparse_support=True,
            cross_phase_support=cross_phase_support,
        )
    fitted = _fit_selected_harmonics(packed, variance, colors, base, selected)
    limits, searches, refined = [], [], []
    for k, (fx, fy, score) in enumerate(selected):
        ids = [12 + 6 * k + 2, 12 + 6 * k + 3]
        g = fitted["beta"][ids]
        power = float(g @ np.linalg.solve(fitted["covariance"][np.ix_(ids, ids)], g))
        limits.append(original["gate_limits"][k] if k < count else float(power > 9))
        if k >= count and power > 9:
            radius = 0.34 if np.hypot(fx, fy) > 0.22 else 0.22
            (nx, ny), info = frequency_fit(packed, colors, (fx, fy), max_radius=radius)
            others = [p for j, p in enumerate(selected) if j != k] + refined
            if all(np.hypot(nx - p[0], ny - p[1]) >= 2 / 256 for p in others):
                fx, fy = nx, ny
            else:
                info["collision_fallback"] = True
            searches.append(info)
        else:
            searches.append({"fixed_context_frequency": True})
        refined.append((fx, fy, score))
    fitted = _fit_selected_harmonics(packed, variance, colors, base, refined)
    fitted["gate_limits"], fitted["searches"] = limits, searches
    value, info = _correct_fitted_patch(
        fitted,
        device=device,
        refine_frequency=True,
        sparse_support=True,
        cross_phase_support=cross_phase_support,
    )
    info["context_added_frequencies"] = len(selected) - count
    info["original_frequency_searches"] = original.get("searches", [])
    return value, info


def context_origin(start, length):
    """Clamp an even-origin 512-pixel window on a 256-pixel context grid."""
    if length < 512:
        raise ValueError("Actual context must span at least 512 native samples")
    return int(np.clip(256 * (start // 256) - 64, 0, 2 * ((length - 512) // 2)))


def _solver_stats(device):
    return {
        "device": str(device),
        "solves": 0,
        "iterations": 0,
        "capped": 0,
        "maximum_relative_primal_dual_gap": 0.0,
    }


def refine_context_harmonics(
    raw, colors, base, *, shot, read, stride=128, tv_device="cpu", cross_phase_support=False
):
    """Use cached actual 512-pixel contexts and the original 256-pixel fit/blend.

    Inputs shorter than 512 in either dimension retain the exact sparse stage.
    Only legacy local fitting extends odd CFA boundaries; frequency detection
    always uses actual observations. No neural calls, references or noise draws.
    """
    from .phase_harmonic import refine_phase_harmonics

    started = time.perf_counter()
    envelope = "cross" if cross_phase_support else "wide"
    method = "local-phase-harmonic-v8" if cross_phase_support else "local-phase-harmonic-v7"
    raw, base, colors = np.asarray(raw), np.asarray(base), np.asarray(colors)
    if raw.ndim != 2 or min(raw.shape) < 2 or base.shape != (3, *raw.shape):
        raise ValueError("Require a >=2x2 Bayer image and matching 3xHxW RGB")
    if not np.isfinite(raw).all() or not np.isfinite(base).all():
        raise ValueError("RAW and RGB must be finite")
    if not np.isfinite([shot, read]).all() or min(shot, read) < 0:
        raise ValueError("Require finite nonnegative shot/read variances")
    if not isinstance(stride, (int, np.integer)) or stride % 2 or not 2 <= stride <= 192:
        raise ValueError("Stride must be even and between 2 and 192")
    if (
        colors.shape != (4,)
        or not np.issubdtype(colors.dtype, np.integer)
        or tuple(colors) not in {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
    ):
        raise ValueError("Require a standard integer Bayer phase layout")
    context = {
        "native": 512,
        "grid_stride_native": 256,
        "grid_offset_native": -64,
        "annuli": [[0.03, 0.22], [0.22, 0.34]],
        "peaks_per_band": 4,
        "signed_coherence_threshold": 0.8,
        "signed_cross_noise_threshold": 5,
        "strict_abs_component_bound": 0.25,
        "physical_peak_suppression": 4 / 256,
        "maximum_local_peaks": 12,
        "windows": 0,
        "selected_windows": 0,
        "frequencies": 0,
        "frequency_evaluations": 0,
        "collision_fallbacks": 0,
        "maximum_abs_delta_bins": 0.0,
        "variance_floor_positive_windows": 0,
        "maximum_added_pixel_variance": 0.0,
        "variance_floor_windows": [],
        "variance_floor_probe_annulus": [0.1, 0.34],
        "variance_floor_rule": "max(0,max_green(median(PSD/unit)/ln2-median(declared_noise/unit)))",
        "confidence_calibrated": False,
    }
    if min(raw.shape) < 512:
        value, info = refine_phase_harmonics(
            raw,
            colors,
            base,
            shot=shot,
            read=read,
            stride=stride,
            envelope="sparse",
            tv_device=tv_device,
        )
        info.update(
            method=method,
            envelope=envelope,
            context=context,
            context_small_image_fallback=True,
            effective_envelope="sparse",
            seconds=time.perf_counter() - started,
        )
        if cross_phase_support:
            info["cross_phase_support"] = {"enabled": False, "small_image_fallback": True}
        return value, info
    result = np.array(base, dtype=np.float32, copy=True)
    info = {
        "method": method,
        "envelope": envelope,
        "enabled": True,
        "refine_frequency": True,
        "stride_native": int(stride),
        "tile_native": 256,
        "working_precision": "float64 fits;float32 full-image accumulation/output",
        "noise": "max(observed RAW,0)*shot+read;same convention as neural inference",
        "confidence_calibrated": False,
        "context": context,
        "patches": 0,
        "selected_patches": 0,
        "active_patches": 0,
        "selected_frequencies": 0,
        "context_added_frequencies": 0,
        "new_model_calls": 0,
        "TV": _solver_stats(tv_device),
        "support_TV": _solver_stats(tv_device),
        "sparse_support": {
            "support_TV_noise_multiplier": 16,
            "group_noise_multiplier": 0.5,
            "support_power_threshold": 9,
            "minimum_connected_packed_area": 805,
            "connectivity": 4,
            "masked_refit_TV_noise_multiplier": 4,
            "post_filter_power_shrink": 9,
            "magnitude_cap": 3,
            "global_gate": 9,
            "apron_native": 32,
            "confidence_calibrated": False,
        },
        "frequency_search": {
            "solves": 0,
            "evaluations": 0,
            "collision_fallbacks": 0,
            "clipped_windows": 0,
            "maximum_abs_delta_bins": 0.0,
            "confidence_calibrated": False,
        },
    }
    if cross_phase_support:
        info["cross_phase_support"] = {
            "enabled": True,
            "mask_grid": [32, 32],
            "mask_node_spacing_native": 8,
            "raw_phasor_sigma_native": 32,
            "TV_weight_coarse": 0.5,
            "area_weight_native": 1 / 1610,
            "support_threshold": 0.5,
            "solves": 0,
            "capped": 0,
            "iterations": 0,
            "maximum_relative_gap": 0.0,
            "maximum_absolute_gap": 0.0,
            "confidence_calibrated": False,
        }
    if shot == read == 0:
        info.update(ADC_only_bypass=True, seconds=time.perf_counter() - started)
        return result, info
    height, width = raw.shape
    rows, cols = np.arange(height + height % 2), np.arange(width + width % 2)
    rows = np.where(rows < height, rows, 2 * ((height - 2) // 2) + rows % 2)
    cols = np.where(cols < width, cols, 2 * ((width - 2) // 2) + cols % 2)
    add = np.zeros((3, height, width), dtype=np.float32)
    weights = np.zeros((height, width), dtype=np.float32)
    apron = np.sin(np.pi * np.arange(32) / 64) ** 2
    one = np.ones(256)
    one[:32], one[-32:] = apron, apron[::-1]
    taper = one[:, None] * one[None, :]
    cache = {}
    for y in _origins(len(rows), stride):
        cy = context_origin(y, height)
        for x in _origins(len(cols), stride):
            cx = context_origin(x, width)
            if (cy, cx) not in cache:
                q = np.asarray(raw[cy : cy + 512, cx : cx + 512], dtype=np.float32)
                p = np.stack([q[i // 2 :: 2, i % 2 :: 2] for i in range(4)])
                peaks, searches, floor = context_frequencies(
                    p, np.maximum(p, 0) * shot + read, colors, return_noise_floor=True
                )
                cache[cy, cx] = peaks, floor["added_pixel_variance"]
                context["variance_floor_positive_windows"] += floor["added_pixel_variance"] > 0
                context["maximum_added_pixel_variance"] = max(
                    context["maximum_added_pixel_variance"], floor["added_pixel_variance"]
                )
                context["variance_floor_windows"].append(
                    {"native_xywh": [cx, cy, 512, 512], **floor}
                )
                context["windows"] += 1
                context["selected_windows"] += bool(peaks)
                context["frequencies"] += len(peaks)
                for search in searches:
                    context["frequency_evaluations"] += search["evaluations"]
                    context["collision_fallbacks"] += bool(search.get("collision_fallback"))
                    context["maximum_abs_delta_bins"] = max(
                        context["maximum_abs_delta_bins"],
                        float(np.max(np.abs(search["delta_bins_xy"]))),
                    )
            ry, rx = rows[y : y + 256], cols[x : x + 256]
            q = np.asarray(raw[np.ix_(ry, rx)], dtype=np.float32)
            packed = np.stack([q[i // 2 :: 2, i % 2 :: 2] for i in range(4)])
            parent = base[:, ry[:, None], rx]
            value, diagnostic = correct_context_patch(
                packed,
                np.maximum(packed, 0) * shot + read,
                colors,
                parent,
                cache[cy, cx][0],
                device=tv_device,
                variance_floor=cache[cy, cx][1],
                cross_phase_support=cross_phase_support,
            )
            delta = value - parent
            h, w = min(256, height - y), min(256, width - x)
            add[:, y : y + h, x : x + w] += delta[:, :h, :w]
            weights[y : y + h, x : x + w] += taper[:h, :w]
            info["patches"] += 1
            info["selected_patches"] += bool(diagnostic.get("peaks"))
            info["selected_frequencies"] += len(diagnostic.get("peaks", []))
            info["active_patches"] += bool(np.any(delta))
            info["context_added_frequencies"] += diagnostic.get("context_added_frequencies", 0)
            cross = diagnostic.get("cross_phase_support", {})
            if cross.get("applied"):
                solver = cross["solver"]
                stats = info["cross_phase_support"]
                stats["solves"] += 1
                stats["capped"] += not solver["converged"]
                stats["iterations"] += solver["iterations"]
                for key in ("relative_gap", "absolute_gap"):
                    stats["maximum_" + key] = max(stats["maximum_" + key], solver[key])
            searches = diagnostic.get("frequency_searches", []) + diagnostic.get(
                "original_frequency_searches", []
            )
            info["frequency_search"]["clipped_windows"] += bool(
                diagnostic.get("context_clipped_local_fallback")
            ) or any(s.get("clipped_window_fallback") for s in searches)
            for search in searches:
                if "evaluations" not in search:
                    continue
                stats = info["frequency_search"]
                stats["solves"] += 1
                stats["evaluations"] += search["evaluations"]
                stats["collision_fallbacks"] += bool(search.get("collision_fallback"))
                stats["maximum_abs_delta_bins"] = max(
                    stats["maximum_abs_delta_bins"], float(np.max(np.abs(search["delta_bins_xy"])))
                )
            for part in diagnostic.get("local", []):
                for key, block in [("edge", "TV"), ("support", "support_TV")]:
                    solver = part.get("solver", {}).get(key)
                    if solver:
                        stats = info[block]
                        stats["solves"] += 1
                        stats["iterations"] += solver["iterations"]
                        stats["capped"] += not solver["converged"]
                        stats["maximum_relative_primal_dual_gap"] = max(
                            stats["maximum_relative_primal_dual_gap"],
                            solver["relative_primal_dual_gap"],
                        )
    np.maximum(weights, 1, out=weights)
    np.divide(add, weights[None], out=add)
    result += add
    energy = sum(
        float(np.sum(add[:, y : y + 256].astype(np.float64) ** 2)) for y in range(0, height, 256)
    )
    info.update(
        seconds=time.perf_counter() - started,
        extension="Actual512 contexts;repeat complete Bayer cells only for legacy odd local boundaries",
        blend="sum tapered deltas/max(sum tapers,1),including inactive patches",
        added_field_rms_DN16=float(np.sqrt(energy / add.size) * 65535),
        max_abs_added_field_DN16=float(np.max(np.abs(add)) * 65535),
    )
    return result, info
