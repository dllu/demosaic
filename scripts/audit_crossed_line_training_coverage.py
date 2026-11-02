"""Replay only scheduled V142 procedural reads and their empty counterfactuals."""

import argparse
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
import yaml
from train_directional_bank_trial import guard, read, ref, save

from demosaic import data
from demosaic.train import domain_indices


def audit(training_path, output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    torch.set_num_threads(2)
    os.nice(10)
    training = read(training_path)
    guard(training)
    config_path = Path(training["arms"]["V142"]["train"])
    config = yaml.safe_load(config_path.read_text())
    assert config["steps"] == 1000 and config["mesh_texture_fraction"] == 0.1
    assert config["patch_size"] == 256 and config["batch_size"] == 16
    output.mkdir(parents=True, exist_ok=False)
    kwargs = {
        name: config[name]
        for name in (
            "patch_size",
            "seed",
            "synthetic_fraction",
            "flat_fraction",
            "augmentation_downsample",
            "weak_texture_fraction",
            "fine_weak_texture_fraction",
            "mesh_texture_fraction",
            "flat_chroma_stops",
            "optical_blur_probability",
            "photographic_low_contrast_fraction",
            "reviewed_roi_catalogue",
            "reviewed_roi_fraction",
            "photo_sampling_reference_manifest",
            "photo_sampling_reference_sha256",
        )
    }
    reader = data.CleanDataset(config["manifest"], trace_sources=True, **kwargs)
    source_path = Path(config["run"]) / "source-loss.jsonl"
    source_bytes = source_path.read_bytes()
    trace_copy = output / "source-loss-prefix.jsonl"
    trace_copy.write_bytes(source_bytes)
    traces = {
        row["source"]["draw_index"]: row["source"]
        for row in map(json.loads, source_bytes.splitlines())
        if row.get("source", {}).get("kind") == "crossed-lines"
    }
    scheduled = list(domain_indices("commons", 0, 1000, 16, 70, 0.25, 0.25))
    selected = [i for i in scheduled if 0.1 <= random.Random(70 + i).random() < 0.2]
    original = data.crossed_line_texture
    captured = {}

    def paired(size, rng, **options):
        before = rng.getstate()
        target, recipe = original(size, rng, **options)
        alternate = random.Random()
        alternate.setstate(before)
        empty, _ = original(size, alternate, **options, present=False)
        assert alternate.getstate() == rng.getstate()
        captured["empty"] = data.augment_before_downsample(
            empty, 256, alternate, optical_blur_probability=0
        )
        captured["recipe"] = recipe
        return target, recipe

    data.crossed_line_texture = paired
    rows, checked_traces = [], 0
    try:
        for index in selected:
            actual = reader[index]
            source = json.loads(actual["source"])
            assert source["kind"] == "crossed-lines"
            recipe = source["texture_recipe"]
            assert recipe == captured["recipe"]
            if index in traces:
                assert traces[index] == source
                checked_traces += 1
            p = actual["rgb"].numpy().astype(np.float64)
            e = captured["empty"].numpy().astype(np.float64)
            delta = p - e
            if not recipe["present"]:
                np.testing.assert_array_equal(p, e)
            assert np.isfinite(p).all() and (p >= 0).all() and (p < 1).all()
            core = delta[:, 48:208, 48:208]
            rows.append(
                {
                    "draw_index": index,
                    "scheduled_step": index // 16 + 1,
                    "recipe": recipe,
                    "post_geometry_RGB_min_max": [float(p.min()), float(p.max())],
                    "post_geometry_detail_RMS": float(np.sqrt(np.mean(delta**2))),
                    "post_geometry_detail_RMS_over_sampled_level": float(
                        np.sqrt(np.mean(delta**2)) / recipe["level"]
                    ),
                    "post_geometry_core160_detail_RMS": float(np.sqrt(np.mean(core**2))),
                    "post_geometry_exact_empty_pixel_fraction": float(
                        np.all(delta == 0, axis=0).mean()
                    ),
                    "post_geometry_peak_detail_DN16": float(np.max(np.abs(delta)) * 65535),
                }
            )
    finally:
        data.crossed_line_texture = original
    assert checked_traces == len(traces)
    assert not torch.cuda.is_initialized()
    present = [r for r in rows if r["recipe"]["present"]]
    summary = {
        "total_scheduled_target_slots": 16000,
        "scheduled_Commons_slots": len(scheduled),
        "crossed_line_source_slots": len(rows),
        "line_present_slots": len(present),
        "line_absent_slots": len(rows) - len(present),
        "logged_actual_reader_sources_exact": checked_traces,
    }
    for name, values in {
        "present_generated_level": [r["recipe"]["level"] for r in present],
        "present_requested_relative_peak": [
            r["recipe"]["requested_peak_relative_contrast"] for r in present
        ],
        "present_post_geometry_RMS_over_level": [
            r["post_geometry_detail_RMS_over_sampled_level"] for r in present
        ],
        "present_post_geometry_exact_empty_pixel_fraction": [
            r["post_geometry_exact_empty_pixel_fraction"] for r in present
        ],
        "present_post_geometry_peak_DN16": [r["post_geometry_peak_detail_DN16"] for r in present],
    }.items():
        summary[name + "_min_q25_median_q75_max"] = np.quantile(
            values, [0, 0.25, 0.5, 0.75, 1]
        ).tolist()
    summary["present_peak_below_half_DN16_before_training_exposure"] = sum(
        r["post_geometry_peak_detail_DN16"] < 0.5 for r in present
    )
    save(
        output / "result-v1.json",
        {
            "status": "completed-source-schedule-and-actual-reader-counterfactual-audit",
            "training_plan": ref(training_path),
            "recipe": ref(config_path),
            "actual_trace_prefix": ref(trace_copy),
            "operator": ref(__file__),
            "summary": summary,
            "rows": rows,
            "new_model_forwards": 0,
            "noise_observations": 0,
            "RAW_decodes": 0,
            "scope": "Replay only all scheduled procedural mesh reads from frozen V142 source; exact empty counterfactual uses identical RNG/geometry. Counts describe original1k schedule, not proof every update has executed. Logged actual source recipes match the saved trace prefix. Levels/contrasts are pre-camera/pre-training-exposure; source-level DN16 does not establish sensor visibility. No model quality or hallucination conclusion.",
        },
    )
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit(args.training_plan.resolve(), args.output.resolve())
