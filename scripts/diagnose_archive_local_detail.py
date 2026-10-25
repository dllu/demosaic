"""Compare local fine-band response in matched saved photographic archives."""

import hashlib
import json
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
from diagnose_local_material_detail import basis, binding, blocks, fft_dct, luminance, reduce_sums

CONDITIONS = {"adc-only", "iso100-prior", "iso12800-prior"}
PATTERNS = {"RGGB", "BGGR", "GRBG", "GBRG"}
EDGES = np.array([0, 0.02, 0.05, 0.10, 0.20])


def fingerprint(value):
    return {
        "dtype": value.dtype.str,
        "shape": list(value.shape),
        "sha256": hashlib.sha256(value.tobytes()).hexdigest(),
    }


def read_records(path, sha256):
    rows = {}
    for index, line in enumerate(Path(path).read_text().splitlines()):
        row = json.loads(line)
        if row["schema"] != "demosaic-predictions-v1" or row["index"] != index:
            raise ValueError("Archive schema or sequential index differs")
        if row["model"]["sha256"] != sha256:
            continue
        if row["model"].get("self_ensemble", "none") != "none" or row["model"]["step"] != 20000:
            raise ValueError("Expected final20k single-view predictions")
        context = row["context"]
        if context["condition"]["name"] not in CONDITIONS:
            continue
        if context["pattern"] not in PATTERNS or context["condition"]["exposure"] != 1:
            raise ValueError("Unexpected phase or exposure")
        key = (tuple(context["ids"]), context["condition"]["name"], context["pattern"])
        if key in rows:
            raise ValueError("Duplicate photographic batch")
        rows[key] = row
    if not rows:
        raise ValueError("No declared endpoint observations")
    return rows


def matched(a, b):
    if a["context"] != b["context"]:
        raise ValueError("Noisy input or observation context differs")
    if a["supervision_values"] != b["supervision_values"]:
        raise ValueError("Target, WB or matrix values differ")
    if not {"packed", "variance", "colors", "wb", "matrix"} <= set(
        a["context"]["input_fingerprints"]
    ):
        raise ValueError("Missing physical-input fingerprints")


def analyze(
    first_manifest,
    first_sha,
    second_manifest,
    second_sha,
    output,
    *,
    expected_images=427,
    source_ids=None,
    maximum_seconds=600,
):
    """Pool four CFAs per source/condition, then report equal-source summaries."""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Explicit CPU-only environment required")
    sources = None if source_ids is None else set(source_ids)
    first, second = (
        read_records(first_manifest, first_sha),
        read_records(second_manifest, second_sha),
    )
    if first.keys() != second.keys():
        raise ValueError("Matched photographic coverage differs")
    for key in first:
        matched(first[key], second[key])
    output = Path(output)
    output.mkdir(exist_ok=False)
    began = time.monotonic()
    c = basis(16)
    frequencies = np.arange(16) / 32
    radius = np.hypot(frequencies[:, None], frequencies[None, :])
    band = (radius >= 1 / 8) & (radius < 1 / 3)
    maximum_error, transforms = 0.0, 0
    checked, supervision_cache = set(), {}

    def guard():
        if time.monotonic() - began > maximum_seconds:
            raise TimeoutError("Declared CPU analysis deadline")
        if psutil.virtual_memory().available < 8 * 2**30:
            raise RuntimeError("Less than8GiB available RAM")

    def load(item, *, supervision=False):
        key = (item["path"], item["sha256"])
        if key not in checked:
            if binding(item["path"]) != item:
                raise ValueError("Changed retained array")
            checked.add(key)
        if supervision:
            if key not in supervision_cache:
                with np.load(item["path"], allow_pickle=False) as archive:
                    values = {k: archive[k] for k in archive.files}
                if len(supervision_cache) >= 4:
                    supervision_cache.pop(next(iter(supervision_cache)))
                supervision_cache[key] = values
            return supervision_cache[key]
        return np.load(item["path"], allow_pickle=False)

    def transform(value):
        nonlocal maximum_error, transforms
        coefficients = c @ value @ c.T
        independent = fft_dct(fft_dct(value, -1), -2)
        np.testing.assert_allclose(coefficients, independent, rtol=1e-11, atol=1e-13)
        maximum_error = max(maximum_error, float(np.max(np.abs(coefficients - independent))))
        transforms += len(value)
        return coefficients[..., band]

    sums = defaultdict(
        lambda: {"GT_energy": 0.0, "cross": 0.0, "prediction_energy": 0.0, "blocks": 0}
    )
    coverage, gt, input_rows = set(), {}, []
    for key, a in first.items():
        guard()
        b = second[key]
        ids, condition, pattern = key
        indices = [
            i
            for i, source in enumerate(ids)
            if len(source) == 40
            and all(ch in "0123456789abcdef" for ch in source)
            and (sources is None or source in sources)
        ]
        if not indices:
            continue
        left, right = (load(r["supervision"], supervision=True) for r in (a, b))
        for row, values in ((a, left), (b, right)):
            if any(
                fingerprint(values[k]) != value for k, value in row["supervision_values"].items()
            ):
                raise ValueError("Supervision fingerprint differs")
        if any(not np.array_equal(left[k], right[k]) for k in ("target", "wb", "matrix")):
            raise ValueError("Retained supervision differs")
        predictions = [load(row["prediction"]) for row in (a, b)]
        for value, row in zip(predictions, (a, b), strict=True):
            if (
                value.shape != left["target"].shape
                or value.dtype != np.float32
                or not np.isfinite(value).all()
                or fingerprint(value) != row["prediction_values"]
            ):
                raise ValueError("Prediction values differ from native FP32 record")
        input_rows.append(
            {
                "context": a["context"],
                "first": {k: a[k] for k in ("prediction", "supervision")},
                "second": {k: b[k] for k in ("prediction", "supervision")},
            }
        )
        for i in indices:
            source = ids[i]
            observation = (source, condition, pattern)
            if observation in coverage:
                raise ValueError("Duplicated source/noise/CFA observation")
            coverage.add(observation)
            data = {k: left[k][i : i + 1] for k in ("target", "wb", "matrix")}
            identity = {k: fingerprint(v) for k, v in data.items()}
            if source not in gt:
                rgb, y = luminance(data["target"], data)
                tb = blocks(y)
                t = transform(tb)
                energy = np.sum(t * t, axis=1)
                mean = tb.mean(axis=(1, 2))
                rms = np.sqrt(energy / 256)
                valid = (mean >= 0.02) & (mean <= 0.9) & (rms >= 1e-5)
                for channel in rgb[0]:
                    tile = blocks(channel)
                    valid &= np.all((tile >= 0) & (tile <= 1), axis=(1, 2))
                bins = np.searchsorted(EDGES, rms / np.maximum(mean, 1e-30), side="right") - 1
                gt[source] = {
                    "identity": identity,
                    "coefficients": t,
                    "energy": energy,
                    "mean": mean,
                    "rms": rms,
                    "valid": valid,
                    "bins": bins,
                }
            reference = gt[source]
            if identity != reference["identity"]:
                raise ValueError("GT/WB/matrix changes across noise conditions or CFAs")
            for label, value in zip(("first", "second"), predictions, strict=True):
                p = transform(blocks(luminance(value[i : i + 1], data)[1]))
                cross = np.sum(p * reference["coefficients"], axis=1)
                power = np.sum(p * p, axis=1)
                for index in range(5):
                    selected = reference["valid"] & (reference["bins"] == index)
                    if not selected.any():
                        continue
                    item = sums[(source, condition, index, label)]
                    item["GT_energy"] += float(reference["energy"][selected].sum())
                    item["cross"] += float(cross[selected].sum())
                    item["prediction_energy"] += float(power[selected].sum())
                    item["blocks"] += int(selected.sum())
    if len(gt) != expected_images or len(coverage) != expected_images * 12:
        raise ValueError("Incomplete declared photographic cohort")
    if sources is not None and set(gt) != sources:
        raise ValueError("Declared source selection differs")
    per_source = [
        {
            "source_id": source,
            "condition": condition,
            "bin": index,
            "method": label,
            "sums": values,
            **reduce_sums(values),
        }
        for (source, condition, index, label), values in sorted(sums.items())
    ]
    summaries = []
    for condition in sorted(CONDITIONS):
        for index in range(5):
            row = {
                "condition": condition,
                "bin": index,
                "relative_GT_band_RMS_lower": float(EDGES[index]),
                "relative_GT_band_RMS_upper": float(EDGES[index + 1]) if index < 4 else None,
            }
            grouped = {
                label: [
                    r
                    for r in per_source
                    if r["condition"] == condition and r["bin"] == index and r["method"] == label
                ]
                for label in ("first", "second")
            }
            if not grouped["first"]:
                continue
            for label, values in grouped.items():
                pooled = {k: sum(r["sums"][k] for r in values) for k in values[0]["sums"]}
                row[label] = {
                    "contributing_sources": len(values),
                    "pooled": reduce_sums(pooled),
                    "source_balanced": {
                        k: float(np.mean([r[k] for r in values]))
                        for k in (
                            "GT_projected_gain",
                            "GT_band_RMS",
                            "band_error_RMS",
                            "orthogonal_band_RMS",
                        )
                    },
                }
            if [r["source_id"] for r in grouped["first"]] != [
                r["source_id"] for r in grouped["second"]
            ]:
                raise ValueError("Contrast-stratum source coverage differs")
            row["second_minus_first"] = {
                metric: row["second"]["source_balanced"][metric]
                - row["first"]["source_balanced"][metric]
                for metric in row["first"]["source_balanced"]
            }
            summaries.append(row)

    def save(name, value):
        with (output / name).open("x") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
        return binding(output / name)

    source_rows = save("per-source-v1.json", per_source)
    inputs = save("selected-inputs-v1.json", input_rows)
    ids = sorted(gt)
    np.savez(
        output / "GT-strata-v1.npz",
        source_ids=np.array(ids),
        eligible=np.stack([gt[s]["valid"] for s in ids]),
        bins=np.stack([gt[s]["bins"] for s in ids]),
        GT_band_RMS=np.stack([gt[s]["rms"] for s in ids]),
        GT_mean_luminance=np.stack([gt[s]["mean"] for s in ids]),
    )
    result = {
        "first_manifest": binding(first_manifest),
        "second_manifest": binding(second_manifest),
        "first_checkpoint_sha256": first_sha,
        "second_checkpoint_sha256": second_sha,
        "photographic_sources": len(gt),
        "paired_source_noise_CFA_observations": len(coverage),
        "unique_source_blocks": len(gt) * 225,
        "block_observations_per_method": len(coverage) * 225,
        "summaries": summaries,
        "per_source": source_rows,
        "retained_inputs": inputs,
        "GT_strata": binding(output / "GT-strata-v1.npz"),
        "native16_blocks_transformed": transforms,
        "maximum_explicit_cosine_vs_even_FFT_absolute_error": maximum_error,
        "array_files_checked": len(checked),
        "seconds": time.monotonic() - began,
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "scope": "Descriptive local linear-luminance detail audit of matched final20k single-view saved outputs. Three fixed noise priors/four CFAs; GT-only native16 DCT radial[1/8,1/3), RMS/mean bins0/.02/.05/.10/.20, mean .02-.9, band RMS>=1e-5, GT RGB inside[0,1]. Equal source weight after pooling four CFAs within source/condition. Unique block counts do not multiply independent material coverage by noise/CFA count. Coarse-boundary leakage and chance noise/GT correlation remain; no debiasing, SOTA, uncertainty or carrier-recovery claim.",
    }
    save("result-v1.json", result)
    return result
