"""Audit completed corrected-grid exports and fixed-photo predictions on CPU."""

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import tifffile
import torch
from benchmark_packed_compilation import batch, difference, read, ref, sha
from evaluate_packed_grid import export_difference, scores
from review_packed_isotropic_quarter import completed

from demosaic.cfa import color_indices, malvar
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path

METRIC_REPLAY_ATOL = 1e-4


def legacy_frame(report, checkpoint):
    models = [m for m in report["models"] if m.get("sha256") == checkpoint["sha256"]]
    assert len(models) == 1, "Ambiguous or missing legacy checkpoint"
    model = models[0]
    assert model["precision"] == "float16" and model["device"] == "cuda"
    assert model["model_config"]["restoration_backbone"] == "packed-isotropic"
    frames = [f for f in report["full_frames"] if f["model_label"] == model["label"]]
    assert len(frames) == 1, "Ambiguous or missing legacy full-frame method"
    frame = frames[0]
    timing = frame["timing"]
    assert all(timing[k] == v for k, v in {"tile": 512, "overlap": 64, "batch_size": 4}.items())
    assert timing["compute_precision"] == "float16"
    assert timing.get("tile_grid_alignment", 2) == 2
    assert frame["display_exposure"] == 4
    files = [f for f in frame["files"] if f["path"].endswith("-linear16.tiff")]
    assert len(files) == 1
    return model, frame, files[0]


def audit_photos(directory, checkpoint, fixture):
    directory = Path(directory)
    report = read(directory / "receipt.json")
    assert report["checkpoint"]["sha256"] == checkpoint["sha256"]
    assert report["checkpoint"]["step"] == 40000
    assert report["device"] == "cuda" and report["precision"] == "float16"
    assert (
        report["CUDA_initialized"]
        and report["all_tensor_bytes_parameter_identities_and_keys_unchanged"]
    )
    assert len(report["cases"]) == 2 and len(report["native_crops"]) == 6
    audit = []
    for case, entry in zip(report["cases"], fixture["photos"], strict=True):
        assert case["source_id"] == entry["metadata"]["source"]["id"]
        assert case["observation"] == entry["observation"]
        values = batch(entry["observation"]["path"], torch.device("cpu"))
        predictions, maximum = {}, 0.0
        for policy in ["Whole", "Legacy", "Corrected"]:
            artifact = case["arrays"][policy]
            assert ref(artifact["path"]) == artifact
            prediction = np.load(artifact["path"], allow_pickle=False)
            assert prediction.shape == (3, 510, 510) and prediction.dtype == np.float32
            assert np.isfinite(prediction).all()
            predictions[policy] = prediction
            actual = scores(torch.from_numpy(prediction), values)
            expected = case["exact_synthetic_GT_metrics_border8"][policy]
            assert actual.keys() == expected.keys()
            for metric, value in actual.items():
                if value is None or expected[metric] is None:
                    assert value is expected[metric]
                else:
                    error = abs(value - expected[metric])
                    maximum = max(maximum, error)
                    assert error <= METRIC_REPLAY_ATOL, (policy, metric, error)
        for policy in ["Legacy", "Corrected"]:
            error = difference(
                predictions[policy][:, 128:-128, 128:-128],
                predictions["Whole"][:, 128:-128, 128:-128],
            )
            assert error == case["interior_exclude128_errors_against_whole"][policy]
        audit.append({"source_id": case["source_id"], "max_metric_replay_error": maximum})
    for crop in report["native_crops"]:
        assert sha(directory / crop["image"]) == crop["png_sha256"]
        assert crop["checkpoint"]["sha256"] == checkpoint["sha256"]
        assert crop["evaluation_tile_xywh"] == [176, 176, 160, 160]
        assert crop["display_exposure"] == 1
    return {"receipt": ref(directory / "receipt.json"), "metric_and_all_array_audit": audit}


def export_auditor(receipt):
    assert ref(receipt["path"]) == receipt
    spec = importlib.util.spec_from_file_location("frozen_export_auditor", receipt["path"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_exports


@torch.inference_mode()
def review(manifest_path, output):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    output = writable_path(output)
    assert not output.exists()
    manifest = read(manifest_path)
    assert ref(manifest["review_plan"]["path"]) == manifest["review_plan"]
    _, _, checkpoints = completed(read(manifest["review_plan"]["path"]))
    assert checkpoints == manifest["checkpoints"]
    assert ref(manifest["fixture"]["path"]) == manifest["fixture"]
    fixture = read(manifest["fixture"]["path"])
    for path, expected in fixture["files"].items():
        assert sha(path) == expected, path
    assert ref(manifest["legacy_GFX_report"]["path"]) == manifest["legacy_GFX_report"]
    legacy_report = read(manifest["legacy_GFX_report"]["path"])
    assert legacy_report["sources"] == fixture["gfx_sources"]
    assert legacy_report["conditioning"] == fixture["conditioning"]
    legacy_folder = Path(manifest["legacy_GFX_report"]["path"]).parent
    audit_exports = export_auditor(manifest["export_auditor"])
    meta = fixture["gfx_metadata"]
    assert meta["flip"] == 0
    wb = torch.tensor(meta["white_balance"], dtype=torch.float32)[None]
    matrix = torch.tensor(meta["camera_to_srgb"], dtype=torch.float32)[None]
    output.mkdir(parents=True)
    comparisons, crops, timings, photographs = [], [], [], []
    for checkpoint in checkpoints:
        arm = checkpoint["arm"]
        photographs.append(audit_photos(manifest["photo_outputs"][arm], checkpoint, fixture))
        folder = Path(manifest["full_outputs"][arm])
        current = read(folder / "receipt.json")
        assert current["status"] == "completed-full-frame-compilation-timing-case"
        assert current["checkpoint"]["sha256"] == checkpoint["sha256"]
        assert current["checkpoint"]["step"] == 40000
        assert current["policy"] == "eager" and current["backend"] is None
        assert current["compiled_components"] == 0
        assert current["parameters_keys_and_tensor_bytes_unchanged"]
        assert current["CUDA_initialized"] and current["device"] == "cuda"
        grid = 32 if arm == "dino" else 4
        samples = current["full_frame_samples"]
        assert len(samples) == 3 and len(current["repeat_pixel_errors"]) == 2
        assert all(e["passes_predeclared_bound"] for e in current["repeat_pixel_errors"])
        for sample in [current["excluded_warmup"], *(s["timing"] for s in samples)]:
            assert sample["tile_grid_alignment"] == grid and sample["tile_stride"] == 448
            assert sample["tile"] == 512 and sample["overlap"] == 64
            assert sample["batch_size"] == 4 and sample["tiles"] == 520
            assert sample["megapixels"] == 101.995852 and sample["compute_precision"] == "float16"
        # This frozen auditor checks every RGB16 pixel against the saved F32.
        values = audit_exports(current)
        for start in range(0, values.shape[1], 128):
            assert np.isfinite(values[:, start : start + 128]).all()
        model, frame, encoded = legacy_frame(legacy_report, checkpoint)
        assert model["model_config"] == current["checkpoint"]["model_config"]
        old_path = legacy_folder / encoded["path"]
        assert sha(old_path) == encoded["sha256"] and old_path.stat().st_size == encoded["bytes"]
        with tifffile.TiffFile(old_path) as tif:
            page = tif.pages[0]
            assert page.shape == (8746, 11662, 3) and page.bitspersample == 16
            assert json.loads(page.description)["color_space"] == "linear-camera-RGB"
        exports = {
            "Legacy RGB16": tifffile.memmap(old_path, mode="r"),
            "Corrected RGB16": tifffile.memmap(current["RGB16"]["path"], mode="r"),
        }
        comparisons.append(
            {
                "checkpoint": checkpoint,
                "legacy_model_label": model["label"],
                "legacy_export": ref(old_path),
                "corrected_export": current["RGB16"],
                "all_RGB16_pixels": export_difference(
                    exports["Corrected RGB16"], exports["Legacy RGB16"]
                ),
            }
        )
        seconds = [s["timing"]["seconds"] for s in samples]
        timings.append(
            {
                "arm": arm,
                "corrected_seconds": seconds,
                "median_seconds": float(np.median(seconds)),
                "range_seconds": [min(seconds), max(seconds)],
                "legacy_historical_single_run_seconds": frame["timing"]["seconds"],
                "scope": "Three corrected restores after one excluded full warmup; historical legacy run is not a concurrent speed control",
                "repeat_pixel_errors": current["repeat_pixel_errors"],
                "full_receipt": ref(folder / "receipt.json"),
            }
        )
        for entry in fixture["gfx_regions"]:
            region = entry["region"]
            x, y = region["noisy_xy"]
            size = region["size"]
            tx, ty, _, _ = entry["context_xywh"]
            packed = torch.from_numpy(
                np.load(entry["noisy_packed"]["path"], allow_pickle=False).copy()
            )
            noisy = display_crop(
                malvar(packed, color_indices(meta["pattern"])[None], wb),
                wb,
                matrix,
                [x - tx, y - ty, size, size],
                exposure=4,
            )
            reference = torch.from_numpy(
                np.load(entry["reference_RGB"]["path"], allow_pickle=False).copy()
            )
            reference = display_crop(reference, wb, matrix, [0, 0, size, size], exposure=4)
            for policy, encoded_values in exports.items():
                rgb = encoded_values[y : y + size, x : x + size].astype(np.float32) / np.float32(
                    65535
                )
                display = display_crop(
                    torch.from_numpy(rgb.transpose(2, 0, 1).copy())[None],
                    wb,
                    matrix,
                    [0, 0, size, size],
                    exposure=4,
                )
                crops.append(
                    save_triplet(
                        output,
                        arm + ":" + region["name"] + ":" + policy,
                        [
                            ("Noisy (Malvar)", noisy),
                            (policy, display),
                            ("ISO100 ref (not GT)", reference),
                        ],
                        caption=arm + " / " + region["name"] + " / " + policy,
                        metadata={
                            "checkpoint": checkpoint,
                            "policy": policy,
                            "region": region,
                            "tile_grid_alignment": 2 if policy.startswith("Legacy") else grid,
                            "conditioning": fixture["conditioning"],
                            "shared_wb": meta["white_balance"],
                            "shared_matrix": meta["camera_to_srgb"],
                            "display_exposure": 4,
                            "sources": fixture["gfx_sources"],
                            "reference": entry["reference"],
                            "full_frame": True,
                            "display_encoding": "8-bit sRGB preview; both method panels decode the recorded RGB16 exports",
                            "output_sample_encoding": "Both method panels use decoded camera-linear RGB16 exports; not unquantized F32",
                        },
                    )
                )
    assert len(crops) == 4 * len(fixture["gfx_regions"]) and not torch.cuda.is_initialized()
    result = {
        "status": "completed-corrected-grid-CUDA-photos-and-full-RGB16-awaiting-native-visual-review",
        "checkpoints": checkpoints,
        "photo_audits": photographs,
        "all_export_pixel_comparisons": comparisons,
        "timings": timings,
        "native_GFX_triplets": crops,
        "GT_metric_replay_absolute_tolerance": METRIC_REPLAY_ATOL,
        "CPU_audit_CUDA_initialized": False,
        "no_automatic_model_or_compute_policy_promotion": True,
        "scope": "Supplement to the unchanged full40k quality review. All RGB16 export pixels "
        "are compared; clipping/quantization differs from unquantized-F32 equivalence. Both "
        "displayed method panels use the same RGB16 decoding, WB/matrix/exposure. Real ISO100 "
        "refs are not GT. No training, protected-final scoring, output correction, compilation "
        "or automatic promotion. Native visual review remains required.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    review(args.manifest, args.output)
