"""Apply fixed ADC policies and score the complete matched faint-photo collection."""

import argparse
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from diagnose_local_material_detail import basis, fft_dct
from report_scene_wave_guides import native_board

from demosaic.adc_bins import adc_bin_projection
from demosaic.archive_metrics import linear_rgb, noisy_malvar, photometry
from demosaic.cfa import adc_cfa_projection, mosaic
from demosaic.experiments.artifacts import checked, read_json, reference, write_json

POLICIES = ("raw", "existing-exact-Malvar", "existing-exact-sites", "ADC-bins-Malvar")
ADC = {
    "bit_depth": 16,
    "black_level": 0.03,
    "quantizer_precision": "float64",
    "shot": 0.0,
    "read": 0.0,
}
DN16 = 65535
EDGES = np.array([0.0, 0.02, 0.05, 0.1, 0.2])
PATTERNS = {"RGGB", "BGGR", "GRBG", "GBRG"}
LUMA = np.array([0.2126, 0.7152, 0.0722])
COEFFICIENTS = basis(16)
FREQUENCIES = np.arange(16) / 32
RADIUS = np.hypot(FREQUENCIES[:, None], FREQUENCIES[None, :])
BAND = (RADIUS >= 1 / 8) & (RADIUS < 1 / 3)


def blocks(values):
    """225 non-overlapping native 16-pixel blocks per image or channel."""
    assert values.shape[-2:] == (256, 256)
    batch = values.shape[:-2]
    return (
        values[..., 8:248, 8:248]
        .reshape(*batch, 15, 16, 15, 16)
        .swapaxes(-3, -2)
        .reshape(*batch, 225, 16, 16)
    )


def band(values):
    tiled = blocks(values)
    direct = (COEFFICIENTS @ tiled @ COEFFICIENTS.T)[..., BAND]
    check = fft_dct(fft_dct(tiled, -1), -2)[..., BAND]
    np.testing.assert_allclose(direct, check, rtol=0.0, atol=4e-14)
    return direct


def original_masks(target, arrays):
    original_rgb = linear_rgb(target, arrays)
    luma = np.einsum("c,bchw->bhw", LUMA, original_rgb)
    mean = blocks(luma).mean((-2, -1))
    original_rms = np.linalg.norm(band(luma), axis=-1) / 16
    rgb_blocks = blocks(original_rgb)
    valid = ((rgb_blocks >= 0) & (rgb_blocks <= 1)).all((1, 3, 4))
    eligible = valid & (mean >= 0.02) & (mean <= 0.9)
    bins = np.searchsorted(EDGES, original_rms / np.maximum(mean, 1e-30), side="right") - 1
    return {str(i): eligible & (original_rms >= 1e-5) & (bins == i) for i in range(len(EDGES))} | {
        "quiet": eligible & (original_rms < 1e-5)
    }


def band_sums(prediction, target, masks):
    """Keep sufficient statistics in FP64 for exact paired source pooling."""
    result = []
    for p, t, sample in zip(prediction, target, range(len(prediction)), strict=True):
        rows = {}
        for name, mask in masks.items():
            select = mask[sample]
            if not select.any():
                continue
            expected, actual = t[select], p[select]
            difference = actual - expected
            rows[name] = {
                "blocks": int(select.sum()),
                "target": float(np.sum(expected**2)),
                "cross": float(np.sum(expected * actual)),
                "prediction": float(np.sum(actual**2)),
                "error": float(np.sum(difference**2)),
            }
        result.append(rows)
    return result


def physical_outputs(value, arrays, *, lift_modes=(), calibration=ADC):
    packed, colors, wb = [torch.from_numpy(arrays[k]) for k in ("packed", "colors", "wb")]
    prediction = torch.from_numpy(value)
    outputs = {
        "raw": value,
        "existing-exact-Malvar": adc_cfa_projection(
            prediction, packed, colors, wb, mode="malvar"
        ).numpy(),
        "existing-exact-sites": adc_cfa_projection(
            prediction, packed, colors, wb, mode="sites"
        ).numpy(),
        "ADC-bins-Malvar": adc_bin_projection(
            prediction, packed, colors, wb, **calibration
        ).numpy(),
    }
    for mode in lift_modes:
        corrected = adc_bin_projection(prediction, packed, colors, wb, **calibration, mode=mode)
        torch.testing.assert_close(
            mosaic(corrected, colors),
            mosaic(torch.from_numpy(outputs["ADC-bins-Malvar"]), colors),
            rtol=0.0,
            atol=0.0,
        )
        outputs[f"ADC-bins-{mode}"] = corrected.numpy()
    return outputs


def check_bin_projection(variants, inputs, target):
    cfa = torch.from_numpy(inputs["colors"])
    old, corrected, truth = (
        mosaic(torch.from_numpy(v), cfa).numpy().astype(np.float64)
        for v in (variants["raw"], variants["ADC-bins-Malvar"], target)
    )

    def encode(x):
        return np.rint(np.clip(x * 0.97 + 0.03, 0, 1) * DN16)

    codes = encode(inputs["packed"].astype(np.float64))
    np.testing.assert_array_equal(encode(truth), codes)
    np.testing.assert_array_equal(encode(corrected), codes)
    assert np.all((corrected - truth) ** 2 <= (old - truth) ** 2)


def score(batch, record, models, *, lift_modes=()):
    assert (
        batch["id"] == record["id"] and batch["input_fingerprints"] == record["input_fingerprints"]
    )
    with np.load(checked(batch["arrays"])) as data:
        inputs = dict(data)
    predictions = {}
    for variant in record["variants"]:
        model = variant["label"]
        assert variant["checkpoint"] == models[model]["checkpoint"]
        predictions[model] = physical_outputs(
            np.load(checked(variant["prediction"])), inputs, lift_modes=lift_modes
        )
    # All physical operators above receive only the observed packed codes,
    # Bayer indices, WB and the model output. Target opens start here.
    with np.load(checked(batch["target"])) as data:
        target, original = data["target"], data["original_target"]
    inputs["target"] = target
    masks = original_masks(original, inputs)
    target_band = band(np.einsum("c,bchw->bhw", LUMA, linear_rgb(target, inputs)))
    rows = []
    for model, variants in predictions.items():
        check_bin_projection(variants, inputs, target)
        for name, value in variants.items():
            assert (
                value.dtype == np.float32
                and value.shape == target.shape
                and np.isfinite(value).all()
            )
            photos = photometry(value, inputs, border=8)
            estimated = band(np.einsum("c,bchw->bhw", LUMA, linear_rgb(value, inputs)))
            for i, sums in enumerate(band_sums(estimated, target_band, masks)):
                rows.append(
                    {
                        "source": batch["source_ids"][i],
                        "CFA": batch["pattern"],
                        "model": model,
                        "policy": name,
                        "band_sums": sums,
                        "photometry": {key: float(value[i]) for key, value in photos.items()},
                    }
                )
    return rows, inputs, predictions


def source_balance(rows):
    per_source = defaultdict(list)
    for row in rows:
        per_source[row["model"], row["policy"], row["source"]].append(row)
    aggregate = defaultdict(list)
    for (model, policy, source), samples in per_source.items():
        assert len(samples) == 4 and {row["CFA"] for row in samples} == PATTERNS
        names = set(samples[0]["band_sums"])
        assert all(set(v["band_sums"]) == names for v in samples)
        for name in sorted(names):
            values = [v["band_sums"][name] for v in samples]
            sums = {key: sum(v[key] for v in values) for key in values[0]}
            assert all(v["blocks"] == values[0]["blocks"] for v in values)
            rms = np.sqrt(sums["error"] / (sums["blocks"] * 256)) * DN16
            gain = (
                sums["cross"] / sums["target"] if name != "quiet" and sums["target"] > 0 else None
            )
            aggregate[model, policy, name].append(
                {
                    "source": source,
                    "CFA_observations": 4,
                    "unique_blocks": values[0]["blocks"],
                    "gain": gain,
                    "error_RMS_DN16": float(rms),
                }
            )
    result = []
    for (model, policy, name), photo_rows in sorted(aggregate.items()):
        gains = [r["gain"] for r in photo_rows if r["gain"] is not None]
        result.append(
            {
                "model": model,
                "policy": policy,
                "band": name,
                "source_rows": photo_rows,
                "source_count": len(photo_rows),
                "unique_blocks": sum(r["unique_blocks"] for r in photo_rows),
                "equal_source_RMS_DN16": float(np.mean([r["error_RMS_DN16"] for r in photo_rows])),
                "equal_source_gain": float(np.mean(gains)) if gains else None,
            }
        )
    return result


def run(source, output, qualification):
    producer_plan = source / "plan.json"
    plan = read_json(producer_plan)
    cohort = read_json(source / "cohort.json")
    assert plan["analysis_protocol"]["policies"] == list(POLICIES)
    assert len(cohort["source_ids"]) == 427
    chosen = sorted(cohort["source_ids"])[:2]
    if qualification:
        batches = plan["observations"][:4]
        bindings = [reference(source / "collection" / f"case-{i:03d}.json") for i in range(4)]
        assert {b["pattern"] for b in batches} == PATTERNS
        collection_binding = None
    else:
        collection_binding = reference(source / "collection/result.json")
        collection = read_json(checked(collection_binding))
        assert collection["plan"] == reference(producer_plan)
        assert collection["local_DINO"] == {"requests": 856, "executions": 428, "replays": 428}
        assert collection["models"] == plan["models"]
        assert collection["CPU_rng_unchanged"]
        batches, bindings = plan["observations"], collection["records"]
        assert len(batches) == len(bindings) == 428
    output.mkdir()
    rows, images = [], []
    started = time.monotonic()
    for i, (batch, binding) in enumerate(zip(batches, bindings, strict=True)):
        metrics, arrays, predictions = score(batch, read_json(checked(binding)), plan["models"])
        rows.extend(metrics)
        if batch["pattern"] == "RGGB":
            for index, identity in enumerate(batch["source_ids"]):
                if identity not in chosen:
                    continue
                one = {k: v[index : index + 1] for k, v in arrays.items()}
                target = one["target"][0]
                variants = [
                    predictions[model][policy][index]
                    for model, policy in [
                        ("V120", "raw"),
                        ("scale-control20k", "raw"),
                        ("scale-control20k", "ADC-bins-Malvar"),
                    ]
                ]
                values = [noisy_malvar(one)[0], *variants, target]
                images.append(
                    native_board(
                        output,
                        identity,
                        values,
                        one,
                        {
                            "observation": batch,
                            "models": plan["models"],
                            "ROI_xywh": [48, 48, 160, 160],
                            "reference_role": "Exact simulated faint target",
                        },
                        labels=(
                            "Noisy Malvar",
                            "V120",
                            "Corpus20k",
                            "Corpus20k with ADC bins",
                            "Exact GT",
                        ),
                        triplet_indices=(0, 3, 4),
                        exposure=1,
                        roi=(48, 48, 160, 160),
                        contrast=20,
                    )
                )
        if (i + 1) % 16 == 0:
            write_json(
                output / "progress.json",
                {
                    "completed_batches": i + 1,
                    "planned_batches": len(batches),
                    "score_rows": len(rows),
                },
                replace=True,
            )
            print(i + 1, "of", len(batches), flush=True)
    if not qualification:
        assert len(rows) == 13664 and len(images) == 2
        assert {r["source"] for r in rows} == set(cohort["source_ids"])
    else:
        assert len(images) == 2
    balance = source_balance(rows)
    write_json(
        output / "result.json",
        {
            "producer": reference(__file__),
            "input_plan": reference(producer_plan),
            "collection": collection_binding,
            "source_cohort": reference(source / "cohort.json"),
            "qualification_only": qualification,
            "rows": rows,
            "source_balanced_bands": balance,
            "native_images": images,
            "seconds": time.monotonic() - started,
            "counts": {"batches": len(batches), "score_rows": len(rows)},
            "scope": "Fixed two-model/four-policy faint ADC comparison. FP64 alternate DCT checks"
            " all coefficient arrays. Original target controls contrast masks, faint target"
            " controls reconstruction scores. Four CFA cases pooled before equal source means."
            " Exact independent re-encoding checks every corrected ADC sample. No neural calls.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--qualification", action="store_true")
    arguments = parser.parse_args()
    os.sched_setaffinity(0, [2, 3] if not arguments.qualification else [6, 7])
    torch.set_num_threads(2)
    os.nice(10)
    with torch.inference_mode():
        run(arguments.source.resolve(), arguments.output.resolve(), arguments.qualification)
