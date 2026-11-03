"""Edge-preserving smoothing of local complex harmonic coefficients.

The post-filter threshold uses the earlier Gaussian32 noise proxy, not a
calibrated covariance of the nonlinear TV estimate. No reference or RNG is used.
"""

import numpy as np

from .phase_envelope import local_green_phasor
from .phase_harmonic import fit_patch_harmonics, native_envelope


def _gradient(u):
    g = np.zeros((2, *u.shape))
    g[0, :, :-1, :] = u[:, 1:, :] - u[:, :-1, :]
    g[1, :, :, :-1] = u[:, :, 1:] - u[:, :, :-1]
    return g


def _divergence(g):
    out = np.zeros_like(g[0])
    out[:, :-1, :] += g[0, :, :-1, :]
    out[:, 1:, :] -= g[0, :, :-1, :]
    out[:, :, :-1] += g[1, :, :, :-1]
    out[:, :, 1:] -= g[1, :, :, :-1]
    return out


def _poisson_neumann(rhs, rho):
    """Solve(I-rho*div*grad)u=rhs with whole-field Neumann boundaries.

    The even extension is of the coefficient field, never of Bayer samples.
    """
    h, w = rhs.shape[-2:]
    even = np.concatenate([rhs, rhs[:, ::-1, :]], axis=1)
    even = np.concatenate([even, even[:, :, ::-1]], axis=2)
    fy = 2 - 2 * np.cos(2 * np.pi * np.arange(2 * h) / (2 * h))
    fx = 2 - 2 * np.cos(2 * np.pi * np.arange(2 * w) / (2 * w))
    den = 1 + rho * (fy[:, None] + fx[None, :])
    return np.fft.ifft2(np.fft.fft2(even) / den).real[:, :h, :w]


def denoise_complex_tv(values, weight, iterations=1024, *, device="cpu"):
    """Bounded ADMM for vectorial ROF on two real phasor components.

    Minimize .5*sum((u-values)^2)+sum(weight*norm(grad(u))), sharing the norm
    across sine/cosine and both spatial axes. Every8 iterations measure a
    feasible-dual lower bound; stop at gap/(.5*sum(values²))<1e-5 or the cap.
    Returned diagnostics disclose capped/nonconverged estimates.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 3 or values.shape[0] != 2 or min(values.shape[-2:]) < 1:
        raise ValueError("Require two finite phasor components on a nonempty grid")
    weight = np.broadcast_to(np.asarray(weight, dtype=np.float64), values.shape[-2:])
    if not np.isfinite(values).all() or not np.isfinite(weight).all() or np.any(weight < 0):
        raise ValueError("Require finite coefficients and nonnegative finite TV weights")
    if (
        not isinstance(iterations, (int, np.integer))
        or isinstance(iterations, bool)
        or iterations < 1
    ):
        raise ValueError("TV iteration cap must be a positive integer")
    if not np.any(weight) or np.all(values == values[:, :1, :1]):
        return values.copy(), {
            "iterations": 0,
            "relative_primal_dual_gap": 0.0,
            "gap_scale": float(np.sum(values**2)) * 0.5,
            "absolute_primal_dual_gap": 0.0,
            "converged": True,
        }
    if str(device).startswith("cuda"):
        from .phase_tv_cuda import denoise_tv_cuda

        return denoise_tv_cuda(values, weight, iterations, device)
    if str(device) != "cpu":
        raise ValueError("TV solver device must be cpu or cuda")
    u = values.copy()
    d = _gradient(u)
    b = np.zeros_like(d)
    rho = 16.0
    scale = max(float(np.sum(values**2)) * 0.5, 1e-32)
    gap = None
    for n in range(iterations):
        u = _poisson_neumann(values - rho * _divergence(d - b), rho)
        g = _gradient(u)
        q = g + b
        length = np.sqrt(np.sum(q * q, axis=(0, 1)))
        d = q * np.maximum(0, 1 - weight / (rho * np.maximum(length, 1e-32)))[None, None]
        b += g - d
        if (n + 1) % 8 == 0 or n + 1 == iterations:
            dual = rho * b
            div = _divergence(dual)
            primal = 0.5 * float(np.sum((u - values) ** 2)) + float(
                np.sum(weight * np.sqrt(np.sum(g * g, axis=(0, 1))))
            )
            lower = -0.5 * float(np.sum(div**2)) - float(np.sum(values * div))
            if primal - lower < -1e-9 * scale:
                raise ArithmeticError("TV dual bound exceeded the primal objective")
            gap = max(0, primal - lower) / scale
            if gap < 1e-5:
                break
    return u, {
        "iterations": n + 1,
        "relative_primal_dual_gap": gap,
        "gap_scale": scale,
        "absolute_primal_dual_gap": gap * scale,
        "converged": gap < 1e-5,
    }


def correct_edge_phase_patch(
    packed, variance, colors, base, *, device="cpu", refine_frequency=False, sparse_support=False
):
    """Fixed sigma16 phasors, noise-scaled vectorial TV, and the original gates.

    The Gaussian32 covariance sets a heuristic post-filter power threshold.
    It is not the covariance/confidence of the nonlinear TV result.
    """
    refine_frequency = refine_frequency or sparse_support
    if refine_frequency:
        from .phase_frequency import fit_refined

        fitted = fit_refined(packed, variance, colors, base)
    else:
        fitted = fit_patch_harmonics(packed, variance, colors, base)
    return _correct_fitted_patch(
        fitted, device=device, refine_frequency=refine_frequency, sparse_support=sparse_support
    )


def _correct_fitted_patch(
    fitted, *, device="cpu", refine_frequency=False, sparse_support=False, cross_phase_support=False
):
    """Synthesize a validated joint fit with the original local TV policy."""
    base = fitted["base"]
    peaks = fitted["peaks"]
    if not peaks:
        return base.copy(), {"peaks": []}
    use_sparse = sparse_support and not any(
        s.get("clipped_window_fallback") for s in fitted.get("searches", [])
    )
    beta, cov = fitted["beta"], fitted["covariance"]
    planes = np.stack(
        [(fitted["plane"] @ beta[3 * p : 3 * p + 3]).reshape(128, 128) for p in range(4)]
    )
    fields = {"edge": np.zeros_like(base)}
    yy, xx = np.mgrid[:256, :256]
    detail = []
    waves, wave_frequencies = [], []
    for k, (fx, fy, score) in enumerate(peaks):
        ids = [12 + 6 * k + 2, 12 + 6 * k + 3]
        g = beta[ids]
        power = float(g @ np.linalg.solve(cov[np.ix_(ids, ids)], g))
        gate = max(0, 1 - 9 / max(power, 1e-12))
        if refine_frequency:
            gate = min(fitted["gate_limits"][k], gate)
        if gate == 0:
            detail.append({"gate": 0})
            continue
        small, _, local = local_green_phasor(
            fitted["residual"], fitted["variance"], fitted["colors"], planes, (fx, fy), 16
        )
        _, _, coarse = local_green_phasor(
            fitted["residual"], fitted["variance"], fitted["colors"], planes, (fx, fy), 32
        )
        a, b, d = coarse["covariance"]
        det = np.maximum(a * d - b * b, 1e-32)
        noise = np.sqrt((local["covariance"][0] + local["covariance"][2]) / 2)
        item = {"gate": gate, "solver": {}}
        for key, multiplier in {"edge": 16}.items():
            if use_sparse:
                from .phase_sparse import sparse_support_refit

                coeff, solver, support_solver = sparse_support_refit(
                    small, noise, coarse["covariance"], device=device
                )
                multiplier = 4
                item["solver"]["support"] = support_solver
            else:
                coeff, solver = denoise_complex_tv(small, noise * multiplier, device=device)
            lp = np.maximum(
                0, (d * coeff[0] ** 2 - 2 * b * coeff[0] * coeff[1] + a * coeff[1] ** 2) / det
            )
            scale = np.maximum(0, 1 - 9 / np.maximum(lp, 1e-16))
            re = (g[0] * coeff[0] + g[1] * coeff[1]) / float(g @ g)
            im = (g[1] * coeff[0] - g[0] * coeff[1]) / float(g @ g)
            amplitude = np.hypot(re, im)
            scale *= np.minimum(1, 3 / np.maximum(amplitude, 1e-16))
            r = native_envelope(re * scale)
            i = native_envelope(im * scale)
            angle = 2 * np.pi * (fx * xx + fy * yy)
            wave = np.zeros_like(base) if cross_phase_support else None
            for c in range(3):
                j = 12 + 6 * k + 2 * c
                component = gate * (
                    (beta[j] * r + beta[j + 1] * i) * np.cos(angle)
                    + (beta[j + 1] * r - beta[j] * i) * np.sin(angle)
                )
                fields[key][c] += component
                if wave is not None:
                    wave[c] = component
            if wave is not None:
                waves.append(wave)
                wave_frequencies.append((fx, fy))
            item["solver"][key] = {
                "mean_weight": float(np.mean(noise * multiplier)),
                "mean_active": float(np.mean(scale > 0)),
                **solver,
            }
        detail.append(item)
    apron = np.sin(np.pi * np.arange(32) / 64) ** 2
    one = np.ones(256)
    one[:32], one[-32:] = apron, apron[::-1]
    taper = one[:, None] * one[None, :]
    diagnostic = {
        "peaks": peaks,
        "local": detail,
        "local_sigma_native": 16,
        "TV_noise_multiplier": 4 if use_sparse else 16,
        "post_filter_power_shrink": 9,
        "post_filter_noise_proxy": "FixedGaussian32covariance,notTVuncertainty",
    }
    if refine_frequency:
        diagnostic["frequency_searches"] = fitted["searches"]
    if sparse_support:
        diagnostic["sparse_support"] = {
            "enabled": use_sparse,
            "clipped_window_grid_TV_fallback": not use_sparse,
            "support_TV_noise_multiplier": 16,
            "support_group_noise_multiplier": 0.5,
            "support_power_threshold": 9,
            "minimum_connected_packed_area": 805,
            "connectivity": 4,
            "masked_refit_TV_noise_multiplier": 4,
        }
    if cross_phase_support:
        if waves and use_sparse:
            from .phase_cross import cross_phase_masks

            masks, cross_info = cross_phase_masks(fitted, wave_frequencies, device=device)
            fields["edge"].fill(0)
            for wave, mask in zip(waves, masks):
                fields["edge"] += wave * mask[None]
            diagnostic["cross_phase_support"] = {"applied": True, **cross_info}
        else:
            diagnostic["cross_phase_support"] = {
                "applied": False,
                "clipped_window_fallback": not use_sparse,
            }
    return base + fields["edge"] * taper[None], diagnostic
