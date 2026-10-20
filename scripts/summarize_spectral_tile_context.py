"""Independent array arithmetic and an ADC phase-DC mechanism check."""

import argparse
import os
import shutil
from pathlib import Path

import numpy as np
import torch
from probe_spectral_tile_context import digest, scene
from train_directional_bank_trial import read, ref, save

from demosaic.cfa import color_indices, malvar, mosaic
from demosaic.noise import add_noise
from demosaic.prior import box_mean
from demosaic.raw_spectral import spectral_innovation


def main(root, training_path):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    receipt = read(root / "receipt.json")
    assert ref(receipt["driver"]["path"]) == receipt["driver"]
    for item in receipt["sources"]:
        assert ref(item["path"]) == item
    archived = Path(read(training_path)["work"]) / "src/demosaic"
    assert all(
        ref(archived / Path(i["path"]).name)["sha256"] == i["sha256"] for i in receipt["sources"]
    )
    rows, cases = read(root / "per-context.json"), read(root / "per-case.json")
    assert len(rows) == 576 and len(cases) == 32
    kinds = ["flat", "oblique-carrier", "step-carrier", "thin-grid"]
    groups = []
    for kind in kinds:
        for condition in ["ADC-only", "high-noise"]:
            group = {"fixture": kind, "condition": condition}
            for tile in [256, 512]:
                selected = [
                    r
                    for r in rows
                    if r["case"].startswith(kind + "/" + condition + "/")
                    and r["tile_native"] == tile
                ]
                assert len(selected) == 36
                values = [r["core_difference_to_full_context_RMS_DN16"] for r in selected]
                group[str(tile)] = {
                    "RMS_min_DN16": min(values),
                    "RMS_median_DN16": float(np.median(values)),
                    "RMS_max_DN16": max(values),
                    "worst_abs_DN16": max(
                        r["core_difference_to_full_context_max_DN16"] for r in selected
                    ),
                }
            groups.append(group)
    maximum = 0.0
    with np.load(root / "example-corrections.npz", allow_pickle=False) as data:
        assert len(data.files) == 12
        for kind in kinds:
            for tile in [256, 512]:
                difference = data[f"{kind}-{tile}"].astype(np.float64) - data[
                    f"{kind}-full"
                ].astype(np.float64)
                row = next(
                    r
                    for r in rows
                    if r["case"] == kind + "/high-noise/RGGB"
                    and r["tile_native"] == tile
                    and r["offset_yx"] == [0, 0]
                )
                actual = [
                    float(np.sqrt(np.mean(difference**2)) * 65535),
                    float(np.abs(difference).max() * 65535),
                    *(difference.mean(axis=(-2, -1)) * 65535).ravel().tolist(),
                ]
                recorded = [
                    row["core_difference_to_full_context_RMS_DN16"],
                    row["core_difference_to_full_context_max_DN16"],
                    *row["core_difference_mean_RGB_DN16"],
                ]
                error = max(abs(a - b) for a, b in zip(actual, recorded, strict=True))
                assert error < 1e-10
                maximum = max(maximum, error)
    rng = torch.get_rng_state().clone()
    wb = torch.tensor([receipt["WB"]])
    mechanism = []
    with torch.inference_mode():
        for case in [c for c in cases if "/ADC-only/" in c["case"]]:
            kind, _, pattern = case["case"].split("/")
            colors = color_indices(pattern)
            packed = add_noise(
                mosaic(scene(kind, 768), colors),
                0.0,
                0.0,
                black_level=0.03,
                generator=torch.Generator().manual_seed(case["seed"]),
            )
            assert digest(packed) == case["raw_sha256"]
            base = box_mean(malvar(packed, colors, wb), 17)
            assert digest(base) == case["fixed_base_sha256"]
            residual = packed - mosaic(base, colors)
            full_mean = residual.mean((-2, -1), keepdim=True)
            full_core = spectral_innovation(base, packed, torch.zeros_like(packed), colors, wb)[
                ..., 304:464, 304:464
            ]
            assert digest(full_core) == case["full_context_correction_sha256"]
            for row in [r for r in rows if r["case"] == case["case"]]:
                x, y, tile, _ = row["context_native_xywh"]
                raw, coarse = (
                    packed[..., y // 2 : (y + tile) // 2, x // 2 : (x + tile) // 2],
                    base[..., y : y + tile, x : x + tile],
                )
                local_mean = (raw - mosaic(coarse, colors)).mean((-2, -1), keepdim=True)
                # Without shrinkage of non-DC modes, core differences equal
                # the response to this constant per-phase mean difference.
                phase = (full_mean - local_mean).expand(-1, -1, 6, 6)
                prediction_cell = malvar(phase, colors, wb)[..., 6:8, 6:8]
                prediction = prediction_cell.repeat(1, 1, 80, 80).double()
                correction = spectral_innovation(coarse, raw, torch.zeros_like(raw), colors, wb)[
                    ..., 304 - y : 464 - y, 304 - x : 464 - x
                ]
                assert digest(correction) == row["correction_sha256"]
                difference = correction.double() - full_core.double()
                remaining = difference - prediction
                mechanism.append(
                    {
                        "case": case["case"],
                        "tile_native": tile,
                        "offset_yx": row["offset_yx"],
                        "actual_difference_RMS_DN16": float(
                            difference.square().mean().sqrt() * 65535
                        ),
                        "phase_DC_prediction_RMS_DN16": float(
                            prediction.square().mean().sqrt() * 65535
                        ),
                        "remaining_RMS_DN16": float(remaining.square().mean().sqrt() * 65535),
                    }
                )
    assert (
        len(mechanism) == 288
        and torch.equal(rng, torch.get_rng_state())
        and not torch.cuda.is_initialized()
    )
    dc_groups = []
    for kind in kinds:
        for tile in [256, 512]:
            selected = [
                r
                for r in mechanism
                if r["case"].startswith(kind + "/") and r["tile_native"] == tile
            ]
            dc_groups.append(
                {
                    "fixture": kind,
                    "tile_native": tile,
                    "remaining_RMS_min_DN16": min(r["remaining_RMS_DN16"] for r in selected),
                    "remaining_RMS_max_DN16": max(r["remaining_RMS_DN16"] for r in selected),
                }
            )
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.1), layout="constrained")
    for ax, condition in zip(axes, ["ADC-only", "high-noise"], strict=True):
        for tile, offset in [(256, -0.1), (512, 0.1)]:
            values = [
                next(
                    g[str(tile)]
                    for g in groups
                    if g["fixture"] == kind and g["condition"] == condition
                )
                for kind in kinds
            ]
            median = np.array([v["RMS_median_DN16"] for v in values])
            errors = np.array(
                [[v["RMS_min_DN16"] for v in values], [v["RMS_max_DN16"] for v in values]]
            )
            errors = np.vstack((median - errors[0], errors[1] - median))
            ax.errorbar(
                np.arange(4) + offset,
                median,
                yerr=errors,
                fmt="o",
                capsize=4,
                label=f"{tile}px context",
            )
        ax.set_yscale("symlog", linthresh=0.1)
        ax.set(
            xticks=range(4),
            xticklabels=["flat", "oblique\ncarrier", "step +\ncarrier", "thin\ngrid"],
            title=condition,
            ylabel="Unit-gate correction difference RMS (DN16)",
        )
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.2)
    figure.suptitle(
        "Context sensitivity versus full768 operator; ranges over4 CFAs ×9 shifts\nGenerated fields, fixed observation-only base, gate1; no learned model or GT score",
        fontsize=10,
    )
    figure.savefig(root / "context-summary.png", dpi=160)
    figure.savefig(root / "context-summary.pdf")
    plt.close(figure)
    save(root / "phase-DC-mechanism.json", mechanism)
    shutil.copyfile(receipt["driver"]["path"], root / "executed-driver.py")
    result = {
        "status": "verified-generated-context-arithmetic-and-ADC-phase-DC-mechanism",
        "driver": ref(__file__),
        "study": ref(root / "receipt.json"),
        "training_plan": ref(training_path),
        "executed_probe_archive": ref(root / "executed-driver.py"),
        "groups": groups,
        "all32_cases_and576_contexts_covered": True,
        "all8_saved_array_pairs_reduced_independently": True,
        "maximum_numpy_vs_recorded_DN16_arithmetic_error": maximum,
        "all288_ADC_context_corrections_replayed_byte_exact": True,
        "phase_DC_mechanism": ref(root / "phase-DC-mechanism.json"),
        "phase_DC_summary": dc_groups,
        "all_four_operator_modules_exact_actual_training_source": True,
        "plot": ref(root / "context-summary.png"),
        "plot_PDF": ref(root / "context-summary.pdf"),
        "Torch_CPU_RNG_unchanged": True,
        "CUDA_initialized": False,
        "scope": "Generated unit-gate operator only. Phase-DC prediction is an ideal non-DC identity-mask approximation; remaining error includes real shrinkage/rounding. No learned quality, visibility, fullframe, checkpoint eligibility or new threshold claim.",
    }
    save(root / "summary-audit-v2.json", result)
    print({"audit": ref(root / "summary-audit-v2.json"), "phase_DC_groups": dc_groups})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--training-plan", type=Path, required=True)
    args = parser.parse_args()
    main(args.root.resolve(), args.training_plan.resolve())
