"""Compare retained shadow targets and real-capture conditioning in sensor units."""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import linear_rgb

BRIGHTNESS_EDGES = (0, 2**-12, 2**-10, 2**-8, 2**-6, 2**-4, 2**-2, 1, np.inf)
NOISE_EDGES = (0, 0.125, 0.25, 0.5, 1, 2, 4, np.inf)


def blocks(values):
    """Native160 center split into100 native16 blocks; keep leading axes."""
    values = np.asarray(values)
    if values.shape[-2:] != (256, 256):
        raise ValueError("Expected a256px prepared context")
    values = values[..., 48:208, 48:208]
    shape = values.shape[:-2]
    values = values.reshape(*shape, 10, 16, 10, 16)
    order = tuple(range(len(shape))) + (len(shape), len(shape) + 2, len(shape) + 1, len(shape) + 3)
    return values.transpose(order).reshape(*shape, 100, 16, 16)


def green_sensor_blocks(clean, colors, shot, read_noise):
    """Mean clean measured-green intensity and pre-ADC pixel-noise RMS.

    Average both physical green planes, not all dense RGB green sites. This
    reports pixel-noise conditioning only, not luma-band SNR or output risk.
    """
    clean = np.asarray(clean, dtype=np.float64)
    colors = np.asarray(colors)
    shot, read_noise = np.asarray(shot).reshape(-1), np.asarray(read_noise).reshape(-1)
    if clean.ndim != 4 or clean.shape[1:] != (3, 256, 256):
        raise ValueError("Need Bx3x256x256 camera-linear clean targets")
    if colors.shape != (len(clean), 4) or any(sorted(c.tolist()) != [0, 1, 1, 2] for c in colors):
        raise ValueError("Need one valid Bayer layout per target")
    if (
        len(shot) != len(clean)
        or len(read_noise) != len(clean)
        or np.any(shot < 0)
        or np.any(read_noise < 0)
    ):
        raise ValueError("Need nonnegative per-target shot/read coefficients")
    if (
        not np.isfinite(clean).all()
        or not np.isfinite(shot).all()
        or not np.isfinite(read_noise).all()
    ):
        raise ValueError("Sensor inputs must be finite")
    dense = blocks(clean[:, 1])
    means, variances, valid = [], [], []
    for i, layout in enumerate(colors):
        phases = [
            dense[i, :, phase // 2 :: 2, phase % 2 :: 2].reshape(100, 64)
            for phase in np.flatnonzero(layout == 1)
        ]
        samples = np.concatenate(phases, axis=1)
        mean = samples.mean(axis=1)
        variance = (np.maximum(samples, 0) * shot[i] + read_noise[i]).mean(axis=1)
        means.append(mean)
        variances.append(variance)
        valid.append(((samples >= 0) & (samples < 0.98)).all(axis=1) & (mean > 0))
    means, variances = np.asarray(means), np.asarray(variances)
    return {
        "green_mean": means,
        "pre_ADC_pixel_variance": variances,
        "relative_pixel_noise_RMS": np.sqrt(variances) / np.maximum(means, 1e-12),
        "green_target_valid": np.asarray(valid),
    }


def cell_indices(green_mean, relative_noise):
    return (
        np.searchsorted(BRIGHTNESS_EDGES[1:-1], green_mean, side="right"),
        np.searchsorted(NOISE_EDGES[1:-1], relative_noise, side="right"),
    )


def checked(binding):
    if ref(binding["path"]) != binding:
        raise ValueError("Retained shadow-analysis input changed")
    return Path(binding["path"])


def analyze(plan_path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Shadow coverage requires NumPy-only CPU execution")
    plan = read(plan_path)
    for item in plan["inputs"] + plan["frozen_files"]:
        checked(item)
    original = read(checked(plan["original_coverage"]))
    contexts = read(checked(original["per_context"]))
    with np.load(checked(original["block_statistics"]), allow_pickle=False) as archive:
        previous = {key: archive[key] for key in archive.files}
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    values, row_ids, rows = [], [], []
    control = read(checked(plan["training_receipt"]))
    for step in control["observed_inputs"]:
        if step["domain"] == "paired":
            continue
        with np.load(checked(step["prepared_tensors"]), allow_pickle=False) as archive:
            target = archive["sensor_target"]
            assert len(target) == 32 and np.array_equal(target[:16], target[16:])
            data = {
                key: archive[key][:16]
                for key in ["colors", "shot", "read", "target", "wb", "matrix"]
            }
            sensor = green_sensor_blocks(target[:16], data["colors"], data["shot"], data["read"])
        rgb = linear_rgb(data["target"], data)
        support = blocks(((rgb >= 0) & (rgb <= 1)).all(axis=1)).all(axis=(-2, -1))
        sensor["rendered_in_gamut"] = support
        for i in range(16):
            old_index = (step["step"] - 1) * 16 + i
            context = contexts[old_index]
            assert context["step"] == step["step"] and context["example"] == i
            row = {
                "id": context["id"],
                "family": context["family"],
                "source_id": context["source_id"],
                "step": step["step"],
                "example": i,
                "shot": context["shot"],
                "read": context["read"],
                "prepared_tensors": step["prepared_tensors"],
                "prior_row": old_index,
            }
            rows.append(row)
            row_ids.append(context["id"])
        values.append(sensor)
    arrays = {key: np.concatenate([value[key] for value in values]) for key in values[0]}
    indices = [row["prior_row"] for row in rows]
    for key in ["mean_luma", "band_RMS", "relative_band_RMS"]:
        arrays[key] = previous[key][indices]
    assert len(rows) == 272
    arrays["valid"] = arrays["green_target_valid"] & arrays["rendered_in_gamut"]
    arrays["shadow"] = arrays["mean_luma"] < 0.02
    arrays["weak_band"] = (
        (arrays["relative_band_RMS"] < 0.05)
        & (arrays["mean_luma"] > 0)
        & (arrays["band_RMS"] >= 1e-5)
    )
    bx, by = cell_indices(arrays["green_mean"], arrays["relative_pixel_noise_RMS"])
    arrays["brightness_bin"], arrays["relative_noise_bin"] = bx, by
    with (output / "sensor-blocks.npz").open("xb") as stream:
        np.savez(stream, **arrays)
    summaries = []
    families = list(dict.fromkeys(row["family"] for row in rows))
    for family in families:
        selected = np.asarray([row["family"] == family for row in rows])
        valid = arrays["valid"][selected]
        shadow, weak = arrays["shadow"][selected], arrays["weak_band"][selected]
        summaries.append(
            {
                "family": family,
                "context_slots": int(selected.sum()),
                "total_blocks": int(valid.size),
                "valid_blocks": int(valid.sum()),
                "valid_shadow_blocks": int((valid & shadow).sum()),
                "valid_weak_shadow_blocks": int((valid & shadow & weak).sum()),
                "ADC_only_contexts": sum(
                    row["family"] == family and row["shot"] == row["read"] == 0 for row in rows
                ),
            }
        )
    gfx = []
    with np.load(checked(plan["GFX_inputs"]), allow_pickle=False) as archive:
        raw, colors = archive["raw_context"], archive["colors"][0]
    selection = read(checked(plan["GFX_selection"]))
    for region in selection["regions"]:
        x, y, w, h = region["ROI_xywh"]
        assert w == h == 160
        crop = raw[y : y + h, x : x + w].astype(np.float64)
        samples = np.concatenate(
            [
                crop[(phase // 2 - y) % 2 :: 2, (phase % 2 - x) % 2 :: 2].ravel()
                for phase in np.flatnonzero(colors == 1)
            ]
        )
        mean = float(samples.mean())
        assert mean > 0
        for name, profile in plan["GFX_profiles"].items():
            variance = float(np.mean(np.maximum(samples, 0) * profile["shot"] + profile["read"]))
            relative = np.sqrt(variance) / mean
            ix, iy = (int(v) for v in cell_indices(mean, relative))
            matches = arrays["valid"] & (bx == ix) & (by == iy)
            families_matches = []
            for family in families:
                selected = np.asarray([row["family"] == family for row in rows])
                count = matches[selected]
                families_matches.append(
                    {
                        "family": family,
                        "blocks_in_same_condition_cell": int(count.sum()),
                        "weak_blocks_in_cell": int((count & arrays["weak_band"][selected]).sum()),
                        "context_slots_in_cell": int(count.any(axis=1).sum()),
                    }
                )
            gfx.append(
                {
                    "region": region["name"],
                    "profile": name,
                    "nominal_profile": profile,
                    "source_sensor_ROI_xywh": region["noisy_raw_xywh"],
                    "observed_green_mean": mean,
                    "input_only_proxy_pixel_variance": variance,
                    "proxy_relative_pixel_noise_RMS": float(relative),
                    "brightness_bin": ix,
                    "relative_noise_bin": iy,
                    "training_matches": families_matches,
                    "scope": "Observed-green mean and existing supplied variance proxy, not clean brightness, calibrated noise, fine-band SNR, GT or a restoration-quality measurement.",
                }
            )
    save(output / "contexts.json", rows)
    result = {
        "status": "completed-retained-shadow-sensor-condition-coverage",
        "plan": ref(plan_path),
        "analysis_source": ref(__file__),
        "context_slots": 272,
        "excluded_real_paired_slots": 16,
        "families": summaries,
        "sensor_block_arrays": ref(output / "sensor-blocks.npz"),
        "contexts": ref(output / "contexts.json"),
        "GFX_condition_cells": gfx,
        "brightness_edges": [None if np.isinf(x) else x for x in BRIGHTNESS_EDGES],
        "relative_noise_edges": [None if np.isinf(x) else x for x in NOISE_EDGES],
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "Torch_imported": False,
        "scope": "Bounded retained18-step implementation prefix. Simulated-noise clean targets only; native references retain source noise/optics. Compare pre-ADC per-pixel green-noise conditioning, never luma-band SNR. No full-corpus or quality/admission-policy claim; real GFX proxy is uncalibrated.",
    }
    save(output / "analysis-v1.json", result)
    print(
        json.dumps(
            {
                "families": summaries,
                "GFX_cells": [
                    {
                        key: row[key]
                        for key in [
                            "region",
                            "profile",
                            "observed_green_mean",
                            "proxy_relative_pixel_noise_RMS",
                            "brightness_bin",
                            "relative_noise_bin",
                        ]
                    }
                    for row in gfx
                ],
            }
        )
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    analyze(args.plan.resolve())
