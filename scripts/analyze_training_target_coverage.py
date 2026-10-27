"""Measure fine-band contrast in retained prepared targets, without neural calls."""

import argparse
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from report_conditional_noise_response import EDGES, dct_band
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import linear_rgb

FAMILIES = (
    "commons-photographic",
    "commons-reviewed-photo",
    "commons-weak-texture",
    "commons-procedural",
    "commons-smooth-field",
    "native",
    "paired",
)


def checked(binding):
    if ref(binding["path"]) != binding:
        raise ValueError("Retained training-target input changed")
    return Path(binding["path"])


def commons_identity(recipe, index, reference_ids, eligible_ids, regions):
    """Replay only source-choice RNG; never open or augment source pixels."""
    rng = random.Random(recipe["seed"] + index)
    draw = rng.random()
    flat = recipe["flat_fraction"]
    if draw < flat:
        return "commons-smooth-field", None
    if draw < flat + recipe["synthetic_fraction"]:
        weak = recipe["weak_texture_fraction"]
        fine = recipe.get("fine_weak_texture_fraction", 0)
        if fine:
            raise ValueError("This coverage plan requires the declared legacy weak profile")
        return ("commons-weak-texture" if draw < flat + weak else "commons-procedural"), None
    identity = reference_ids[rng.randrange(len(reference_ids))]
    digest = hashlib.sha256(f"reviewed-photo-roi-v1:{recipe['seed']}:{index}".encode()).digest()
    chooser = random.Random(int.from_bytes(digest[:8], "little"))
    if chooser.random() < recipe["reviewed_roi_fraction"]:
        identity = regions[chooser.randrange(len(regions))]["id"]
        if identity not in eligible_ids:
            raise ValueError("Reviewed ROI lies outside the training cohort")
        return "commons-reviewed-photo", identity
    while identity not in eligible_ids:
        identity = reference_ids[rng.randrange(len(reference_ids))]
    return "commons-photographic", identity


def block_statistics(rgb, measured_mask=None):
    """Use the same native160/DCT16/band definition as conditional response."""
    rgb = np.asarray(rgb, dtype=np.float64)
    if rgb.ndim != 4 or rgb.shape[1:] != (3, 256, 256) or not np.isfinite(rgb).all():
        raise ValueError("Need finite Bx3x256x256 linear display-RGB targets")
    band, means = dct_band(rgb)
    rms = np.sqrt(np.sum(band**2, axis=-1) / 256)
    central = rgb[..., 48:208, 48:208]
    in_gamut = ((central >= 0) & (central <= 1)).all(axis=1)
    valid = in_gamut.reshape(len(rgb), 10, 16, 10, 16).transpose(0, 1, 3, 2, 4)
    valid = valid.reshape(len(rgb), 100, 256).all(axis=-1)
    if measured_mask is not None:
        mask = np.asarray(measured_mask)
        if mask.shape != rgb.shape or mask.dtype != np.bool_:
            raise ValueError("Measured CFA support must be a matching Boolean RGB mask")
        # Dense paired references are estimates. Exclude blocks with any hole in
        # their measured-CFA support, without pretending all RGB sites are known.
        support = mask[:, :, 48:208, 48:208].sum(axis=1) == 1
        support = support.reshape(len(rgb), 10, 16, 10, 16).transpose(0, 1, 3, 2, 4)
        valid &= support.reshape(len(rgb), 100, 256).all(axis=-1)
    valid &= (means >= 0.02) & (means <= 0.9) & (rms >= 1e-5)
    contrast = rms / np.maximum(means, 1e-12)
    bins = np.searchsorted(np.asarray(EDGES[1:-1]), contrast, side="right")
    return {
        "mean_luma": means,
        "band_RMS": rms,
        "relative_band_RMS": contrast,
        "valid": valid,
        "contrast_bin": bins,
    }


def statistics_row(values, index):
    valid = values["valid"][index]
    bins = values["contrast_bin"][index]
    counts = np.bincount(bins[valid], minlength=5)
    return {
        "total_blocks": 100,
        "valid_blocks": int(valid.sum()),
        "counts": counts.tolist(),
        "blocks_below_2_percent": int(counts[0]),
        "blocks_below_5_percent": int(counts[:2].sum()),
    }


def summarize(rows):
    result = []
    for family in FAMILIES:
        selected = [row for row in rows if row["family"] == family]
        if not selected:
            continue
        counts = np.sum([row["counts"] for row in selected], axis=0)
        valid = int(counts.sum())
        result.append(
            {
                "family": family,
                "context_slots": len(selected),
                "total_blocks": len(selected) * 100,
                "valid_blocks": valid,
                "counts": counts.tolist(),
                "valid_block_fractions": (counts / valid).tolist() if valid else None,
                "contexts_with_below_2_percent_blocks": sum(
                    row["blocks_below_2_percent"] > 0 for row in selected
                ),
                "contexts_with_below_5_percent_blocks": sum(
                    row["blocks_below_5_percent"] > 0 for row in selected
                ),
                "distinct_source_IDs": len(
                    {row["source_id"] for row in selected if row["source_id"] is not None}
                ),
            }
        )
    return result


def analyze(plan_path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Coverage analysis requires a NumPy-only CPU process")
    plan = read(plan_path)
    for binding in plan["inputs"] + plan["frozen_files"]:
        checked(binding)
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    recipe = read(plan["recipe"])
    control = read(checked(plan["training_receipt"]))
    reference_ids = tuple(
        row["id"]
        for row in map(json.loads, checked(plan["sampling_reference"]).read_text().splitlines())
        if row["split"] == "train"
    )
    eligible_ids = {
        row["id"]
        for row in map(json.loads, checked(plan["source_manifest"]).read_text().splitlines())
        if row["split"] == "train"
    }
    regions = read(checked(plan["ROI_catalogue"]))["examples"]
    assert len(eligible_ids) == 90784 and len(regions) == 20
    trace = list(map(json.loads, checked(plan["source_trace"]).read_text().splitlines()))
    traces = {(row["step"], row["example_in_source_batch"]): row for row in trace}
    rows, blocks, identities = [], defaultdict(list), []
    trace_checks, unique_contexts, duplicates_removed = 0, 0, 0
    for step in control["observed_inputs"]:
        path = checked(step["prepared_tensors"])
        with np.load(path, allow_pickle=False) as archive:
            target = archive["target"]
            size = len(target)
            if step["domain"] == "paired":
                assert size == 16 and "noise_pair_id" not in archive.files
                half = size
            else:
                half = size // 2
                assert half == 16 and size == 2 * half
                assert np.array_equal(archive["noise_view"], np.repeat([0, 1], half))
                assert np.array_equal(archive["noise_pair_id"], np.tile(np.arange(half), 2))
                assert np.array_equal(target[:half], target[half:])
                for key in ["wb", "matrix", "shot", "read"]:
                    assert np.array_equal(archive[key][:half], archive[key][half:])
                duplicates_removed += half
            data = {key: archive[key][:half] for key in ["wb", "matrix", "shot", "read"]}
            mask = archive["sensor_mask"][:half] if step["domain"] == "paired" else None
            rgb = linear_rgb(target[:half], data)
            values = block_statistics(rgb, mask)
            for key, value in values.items():
                blocks[key].append(value)
            for example in range(half):
                index = (step["step"] - 1) * 16 + example
                family, identity = step["domain"], None
                if family == "commons":
                    family, identity = commons_identity(
                        recipe, index, reference_ids, eligible_ids, regions
                    )
                observed = traces.get((step["step"], example))
                if observed is not None:
                    source = observed["source"]
                    assert (
                        source["draw_index"] == index
                        and source["draw_seed"] == recipe["seed"] + index
                    )
                    expected_kind = {
                        "commons-smooth-field": "smooth-field",
                        "commons-weak-texture": "weak-texture",
                        "commons-procedural": "procedural",
                    }.get(family, "photographic")
                    assert source["kind"] == expected_kind
                    if identity is not None:
                        assert source["source_id"] == identity
                        assert (source["reviewed_roi_xywh"] is not None) == (
                            family == "commons-reviewed-photo"
                        )
                    trace_checks += 1
                shot, read_noise = (
                    float(data["shot"][example].reshape(-1)[0]),
                    float(data["read"][example].reshape(-1)[0]),
                )
                row_id = f"step{step['step']:02d}-example{example:02d}"
                rows.append(
                    {
                        "id": row_id,
                        "step": step["step"],
                        "example": example,
                        "domain": step["domain"],
                        "family": family,
                        "source_id": identity,
                        "global_source_draw_index": index,
                        "shot": shot,
                        "read": read_noise,
                        "sigma18": math.sqrt(0.18 * shot + read_noise),
                        "prepared_tensors": step["prepared_tensors"],
                        **statistics_row(values, example),
                    }
                )
                identities.append(row_id)
            unique_contexts += half
    assert len(rows) == unique_contexts == 288 and duplicates_removed == 272
    assert trace_checks == len(trace) == 16
    with (output / "block-statistics.npz").open("xb") as stream:
        np.savez(stream, **{key: np.concatenate(values) for key, values in blocks.items()})
    references = []
    for case in plan["diagnostic_references"]:
        with np.load(checked(case["target"]), allow_pickle=False) as archive:
            data = {key: archive[key] for key in archive.files}
        values = block_statistics(linear_rgb(data["target"], data))
        references.append(
            {
                "id": case["id"],
                "reference_role": case["reference_role"],
                "target": case["target"],
                **statistics_row(values, 0),
            }
        )
    save(output / "per-context.json", rows)
    result = {
        "status": "completed-retained-training-target-contrast-coverage",
        "plan": ref(plan_path),
        "analysis_source": ref(__file__),
        "context_slots": unique_contexts,
        "duplicate_noise_views_removed": duplicates_removed,
        "domain_counts": dict(Counter(row["domain"] for row in rows)),
        "source_choice_metadata_trace_matches": trace_checks,
        "native_blocks": unique_contexts * 100,
        "per_context": ref(output / "per-context.json"),
        "block_statistics": ref(output / "block-statistics.npz"),
        "block_row_IDs": identities,
        "family_summaries": summarize(rows),
        "diagnostic_references": references,
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "Torch_imported": False,
        "scope": "First18 discarded CUDA training-check steps only, not a uniform corpus audit or full training distribution. Context slots can reuse a source. Photographic family labels come from deterministic source-choice metadata, checked against all16 actual trace rows. Paired/native targets retain reference/source noise and optics. DCT support does not prove useful or noiseless texture. No quality or policy-change conclusion by itself.",
    }
    save(output / "analysis-v1.json", result)
    print(
        json.dumps(
            {
                "contexts": unique_contexts,
                "domain_counts": result["domain_counts"],
                "families": result["family_summaries"],
            }
        )
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    analyze(args.plan.resolve())
