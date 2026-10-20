"""CPU-only GAT moments and interior MHC noise covariance, without a learned model."""

import argparse
import hashlib
import math
import os
from pathlib import Path

import numpy as np
import torch
from train_directional_bank_trial import ref, save

from demosaic.cfa import PATTERNS, color_indices, malvar
from demosaic.pretrained_rgb import physical_rgb_features
from demosaic.safety import writable_path
from demosaic.vst import GeneralizedAnscombe, expectation_table


def conditional_moments(read_e, order):
    """Uncentered 2sqrt(max(N+Gaussian+q,0)) moments conditional on N.

    Integrate its first moment after a square-root substitution over +/-12
    Gaussian standard deviations. Its second moment uses the normal positive
    part formula. Centering does not change variance. This has no ADC clipping
    or quantization; convergence and Monte Carlo are checked separately.
    """
    counts = np.arange(321, dtype=np.float64)
    q = 3 / 8 + read_e**2
    if not read_e:
        return 2 * np.sqrt(counts + q), 4 * (counts + q)
    nodes, weights = np.polynomial.legendre.leggauss(order)
    lower = np.sqrt(np.maximum(counts + q - 12 * read_e, 0))
    upper = np.sqrt(counts + q + 12 * read_e)
    radius = (upper - lower) / 2
    u = (upper + lower)[:, None] / 2 + radius[:, None] * nodes
    normal = u**2 - counts[:, None] - q
    normal /= read_e
    density = np.exp(-(normal**2) / 2) / math.sqrt(2 * math.pi)
    first = (4 * u**2 / read_e * density * weights).sum(1) * radius
    location = counts + q
    standardized = location / read_e
    cdf = np.array([math.erfc(-v / math.sqrt(2)) / 2 for v in standardized])
    pdf = np.exp(-(standardized**2) / 2) / math.sqrt(2 * math.pi)
    second = 4 * (location * cdf + read_e * pdf)
    return first, second


def poisson_moments(mean, read_e, conditional):
    probability = np.empty(321, dtype=np.float64)
    probability[0] = math.exp(-mean)
    for count in range(1, len(probability)):
        probability[count] = probability[count - 1] * mean / count
    assert abs(probability.sum() - 1) < 5e-14
    first, second = conditional
    uncentered = probability @ first
    centered = uncentered - 2 * math.sqrt(3 / 8 + read_e**2)
    variance = max(0.0, float(probability @ second - uncentered**2))
    return float(centered), variance


def sample_gat(mean, read_e, count, seed):
    generator = torch.Generator().manual_seed(seed)
    raw = torch.poisson(torch.full((count,), mean, dtype=torch.float64), generator=generator)
    raw += read_e * torch.randn(raw.shape, dtype=torch.float64, generator=generator)
    transformed = GeneralizedAnscombe(1.0, read_e**2, inverse="algebraic")(raw).double()
    center = transformed - transformed.mean()
    variance = center.square().mean()
    se = ((center.pow(4).mean() - variance.square()).clamp_min(0) / count).sqrt()
    return float(transformed.mean()), float(variance), float(se)


def coefficients(pattern):
    impulses = torch.eye(144).reshape(144, 4, 6, 6)
    # The selected native2x2 cell has complete filter support in this12x12
    # field, so reflected borders do not enter these interior coefficients.
    matrix = malvar(impulses, color_indices(pattern))[..., 6:8, 6:8].flatten(1).T.double()
    assert torch.equal(matrix.sum(1), torch.ones(12, dtype=torch.float64))
    covariance = matrix @ matrix.T
    expected = []
    for rgb in range(3):
        for measured in PATTERNS[pattern]:
            expected.append(
                1.0
                if rgb == measured
                else 9 / 16
                if rgb == 1
                else 61 / 64
                if measured != 1
                else 127 / 128
            )
    assert torch.equal(covariance.diag(), torch.tensor(expected, dtype=torch.float64))
    assert float(covariance.trace()) == 11.0
    return matrix, covariance


def covariance_mc(pattern, samples, seed, *, mean=None, read_e=None):
    generator = torch.Generator().manual_seed(seed)
    chunks = []
    digest = hashlib.sha256()
    transform = None if mean is None else GeneralizedAnscombe(1.0, read_e**2, inverse="algebraic")
    for start in range(0, samples, 2048):
        size = min(2048, samples - start)
        shape = (size, 4, 6, 6)
        if transform is None:
            raw = torch.randn(shape, generator=generator)
        else:
            raw = torch.poisson(torch.full(shape, mean, dtype=torch.float64), generator=generator)
            raw += read_e * torch.randn(shape, dtype=torch.float64, generator=generator)
            raw = transform(raw)
        values = malvar(raw, color_indices(pattern))[..., 6:8, 6:8].flatten(1).contiguous()
        digest.update(values.numpy().tobytes(order="C"))
        chunks.append(values)
    values = torch.cat(chunks).double()
    center = values - values.mean(0)
    covariance = center.T @ center / (samples - 1)
    product_second = center.square().T @ center.square() / samples
    se = ((product_second - covariance.square()).clamp_min(0) / samples).sqrt()
    return values.mean(0), covariance, se, digest.hexdigest()


def main(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    rng = torch.get_rng_state().clone()
    reads, means = [0.0, 0.5, 2.0, 8.0], [0.0, 0.25, 1.0, 4.0, 16.0, 64.0]
    rows, arrays = [], {}
    conditional = {r: conditional_moments(r, 256) for r in reads}
    for read_e in reads:
        low = conditional_moments(read_e, 128)
        expected, grid = expectation_table(read_e)
        for mean in means:
            first, variance = poisson_moments(mean, read_e, conditional[read_e])
            earlier = poisson_moments(mean, read_e, low)
            assert max(abs(first - earlier[0]), abs(variance - earlier[1])) < 2e-10
            assert abs(first - float(np.interp(mean, grid, expected))) < 2e-6
            sampled_mean, sampled_variance, se = sample_gat(
                mean, read_e, 262144, 20261020 + len(rows)
            )
            assert abs(sampled_variance - variance) <= 6 * se + 5e-6
            assert abs(sampled_mean - first) <= 6 * math.sqrt(variance / 262144) + 5e-6
            rows.append(
                {
                    "read_e": read_e,
                    "Poisson_mean": mean,
                    "quadrature_centered_mean": first,
                    "quadrature_variance": variance,
                    "MC_samples": 262144,
                    "MC_mean": sampled_mean,
                    "MC_variance": sampled_variance,
                    "MC_variance_SE": se,
                }
            )
    matrices = []
    for index, pattern in enumerate(PATTERNS):
        operator, covariance = coefficients(pattern)
        sampled_mean, empirical, se, digest = covariance_mc(pattern, 32768, 20261120 + index)
        assert ((empirical - covariance).abs() <= 6 * se + 5e-5).all()
        assert (sampled_mean.abs() <= 6 * (covariance.diag() / 32768).sqrt() + 5e-5).all()
        colors = color_indices(pattern)
        fields = physical_rgb_features(
            torch.zeros(1, 4, 6, 6), torch.ones(1, 4, 6, 6), colors, stabilized=True
        )
        assert torch.equal(fields[2] * fields[5], torch.ones_like(fields[2]))
        arrays[pattern + "_coefficients"] = operator.numpy()
        arrays[pattern + "_covariance"] = covariance.numpy()
        arrays[pattern + "_MC_covariance"] = empirical.numpy()
        matrices.append(
            {
                "CFA": pattern,
                "unit_CFA_RGB_phase_variance": covariance.diag().reshape(3, 4).tolist(),
                "mean_RGB_variance": float(covariance.trace() / 12),
                "eigenvalues": torch.linalg.eigvalsh(covariance).tolist(),
                "MC_fields": 32768,
                "MC_covariance_max_absolute_difference": float(
                    (empirical - covariance).abs().max()
                ),
                "MC_covariance_max_error_in_SE": float(
                    ((empirical - covariance).abs() / se.clamp_min(1e-12)).max()
                ),
                "MC_sample_SHA256": digest,
                "production_pre_normalization_sigma": 1.0,
            }
        )
    special = []
    _, covariance = coefficients("RGGB")
    for level in [0.01, 0.18]:
        mean = level / 0.00256
        first, variance = poisson_moments(mean, 2.0, conditional[2.0])
        observed_mean, empirical, se, digest = covariance_mc(
            "RGGB", 32768, 20261220 + len(special), mean=mean, read_e=2.0
        )
        predicted = covariance * variance
        assert ((empirical - predicted).abs() <= 6 * se + 5e-5).all()
        assert ((observed_mean - first).abs() <= 6 * (predicted.diag() / 32768).sqrt() + 5e-5).all()
        special.append(
            {
                "signal_level": level,
                "shot": 0.00256,
                "read_variance": 0.0000262144,
                "Poisson_mean": mean,
                "read_e": 2.0,
                "GAT_variance": variance,
                "predicted_mean_RGB_phase_variance": float(predicted.trace() / 12),
                "MC_fields": 32768,
                "MC_covariance_max_absolute_difference": float((empirical - predicted).abs().max()),
                "MC_sample_SHA256": digest,
            }
        )
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.1), layout="constrained")
    dense = np.r_[0.0, np.geomspace(0.025, 80, 240)]
    for read_e in reads:
        curve = [poisson_moments(float(mean), read_e, conditional[read_e])[1] for mean in dense]
        axes[0].plot(dense, curve, label=f"read noise {read_e:g} e−")
        chosen = [r for r in rows if r["read_e"] == read_e]
        axes[0].errorbar(
            [r["Poisson_mean"] for r in chosen],
            [r["MC_variance"] for r in chosen],
            yerr=[1.96 * r["MC_variance_SE"] for r in chosen],
            fmt=".",
            capsize=2,
            color=axes[0].lines[-1].get_color(),
        )
    axes[0].axhline(1, color="black", ls="--", lw=1, label="unit proxy")
    axes[0].set(
        xlabel="Poisson mean (electrons)",
        ylabel="Stabilized variance",
        title="GAT: quadrature and independent Monte Carlo",
    )
    axes[0].set_xscale("symlog", linthresh=0.25)
    axes[0].set_xlim(0, 80)
    axes[0].legend(fontsize=8, loc="lower right")
    heat = axes[1].imshow(arrays["RGGB_covariance"], vmin=-1, vmax=1, cmap="RdBu_r")
    labels = [f"{c}{p}" for c in "RGB" for p in range(4)]
    axes[1].set(
        xticks=range(12),
        xticklabels=labels,
        yticks=range(12),
        yticklabels=labels,
        title="Interior MHC covariance, unit independent CFA noise",
    )
    axes[1].tick_params(axis="x", labelrotation=90)
    figure.colorbar(heat, ax=axes[1], label="Covariance (RGB/2×2 phases)")
    figure.savefig(root / "noise-proxy-summary.png", dpi=160)
    figure.savefig(root / "noise-proxy-summary.pdf")
    plt.close(figure)
    np.savez(root / "covariance-arrays.npz", **arrays)
    save(root / "moments.json", rows)
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    result = {
        "status": "completed-CPU-stabilized-noise-proxy-moment-and-covariance-diagnostic",
        "driver": ref(__file__),
        "sources": [
            ref(Path("src/demosaic") / n) for n in ["vst.py", "cfa.py", "pretrained_rgb.py"]
        ],
        "moment_rows": ref(root / "moments.json"),
        "moment_cases": len(rows),
        "moment_MC_samples_per_case": 262144,
        "conditional_quadrature_orders": [128, 256],
        "Gaussian_integration_range_sigma": 12,
        "Poisson_count_support": [0, 320],
        "all_moment_and_covariance_checks_passed": True,
        "unit_Gaussian_CFA_covariance": matrices,
        "protocol_level_flat_unclipped_checks": special,
        "covariance_arrays": ref(root / "covariance-arrays.npz"),
        "plot": ref(root / "noise-proxy-summary.png"),
        "plot_PDF": ref(root / "noise-proxy-summary.pdf"),
        "CPU_RNG_unchanged": True,
        "CUDA_initialized": False,
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "scope": "Independent generated CPU fields, no learned model or photograph. Stochastic unclipped/unquantized Poisson-Gaussian measurements; actual production GAT/MHC plus separate moment quadrature and published-filter energy constants. Interior covariance only, excluding reflected boundaries. Real sensor calibration, ADC/clipping effects and quality/causality are unproven. No condition, model, data, training, threshold or inference default changes.",
    }
    save(root / "receipt.json", result)
    print(
        {
            "receipt": ref(root / "receipt.json"),
            "moment_cases": len(rows),
            "unit_MHC_mean_variance": matrices[0]["mean_RGB_variance"],
            "protocol_checks": special,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.output)
