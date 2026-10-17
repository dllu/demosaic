"""Read-only whole-state, native-triplet and full RGB16 checks for the data trial.

This verifies artifact integrity, not restoration quality or actual visual review.
Historical replay helpers accept real older recipes/panels explicitly; the command
entry point requires the completed, exited V63/V64 owners and their frozen plan.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import tifffile
import torch
import yaml
from audit_fresh_dino_statistics import sha
from audit_sensor_mean_artifacts import FIELDS, exited, identity
from compare_long_commons_scores import historical_runs
from PIL import Image

from demosaic.reporting import display_crop
from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
TRAINING = BASE / "runs/long-commons-v63-v64-first4k-workflow-v1.json"
PARENT = "1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e"
SOURCE = "c9058d90d7d77e61ad7ec53293b805d8ea72da173318e38d1329e138215544c8"
RAWNIND = "c1f7de3de24cb12f4803ee65e11cfb467e9a5b80c3cb7126746ef026106c15e0"
OLD_REGISTRY = Path("docs/results/wide-flat-palette-full4k-review.json")
OLD_REGISTRY_SHA = "b65ab9cfa235f0684959861432a4093d4e99f397baf9117ecc22523c54d0d1c2"
PANELS = {"full427": 4, "known": 4, "unseen": 4, "analytic": 6, "gfx": 8, "three-camera": 12}
RECTANGLES = [[8, 24, 160, 160], [176, 24, 160, 160], [344, 24, 160, 160]]
# Fixed before V63/V64 output review. CPU/GPU FP32 display arithmetic can straddle
# an 8-bit rounding boundary; all mismatches are retained, never called exact.
DISPLAY_MAX_LSB = 1
DISPLAY_MAX_CHANGED_CHANNEL_VALUES = 16


def read(path):
    return json.loads(Path(path).read_text())


def audit_state(checkpoint, recipe, source_files, manifest_hashes, parent, log_path, steps):
    """Check an actual saved boundary against its actual original recipe."""
    assert sha(checkpoint["path"]) == checkpoint["sha256"] and checkpoint["step"] == steps
    state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
    cfg = state["config"]
    assert state["step"] == steps <= cfg["steps"] == recipe["steps"]
    assert cfg["initialized_from"]["sha256"] == parent
    for key, value in recipe.items():
        if key != "validation_protocol":
            assert cfg.get(key) == value, (checkpoint["arm"], key)
    assert cfg["source_sha256"] == SOURCE
    assert len(state["model"]) == len(state["ema"]) == 91
    assert state["model"].keys() == state["ema"].keys()
    assert len(state["optimizer"]["state"]) == 89
    for key in ["model", "ema"]:
        assert all(torch.isfinite(v).all() for v in state[key].values())
    assert all(
        torch.isfinite(v).all()
        for item in state["optimizer"]["state"].values()
        for v in item.values()
        if isinstance(v, torch.Tensor)
    )
    assert {int(v["step"]) for v in state["optimizer"]["state"].values()} == {steps}
    assert all(key in state for key in ["python_rng", "torch_rng", "cuda_rng"])
    assert len(state["cuda_rng"]) == 1
    assert math.isfinite(state["best"])
    snapshot = Path(cfg["source_snapshot"])
    assert {p.name for p in snapshot.glob("*.py")} == {Path(p).name for p in source_files}
    for path, digest in source_files.items():
        assert sha(snapshot / Path(path).name) == digest
    for key in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]:
        assert cfg[key + "_sha256"] == manifest_hashes[cfg[key]] == sha(cfg[key])
    assert sha(cfg["validation_protocol"]) == cfg["validation_protocol_sha256"]
    protocol_hashes = {
        digest
        for path, digest in manifest_hashes.items()
        if Path(path).name == Path(recipe["validation_protocol"]).name
    }
    assert protocol_hashes == {cfg["validation_protocol_sha256"]}
    records = [
        r
        for line in Path(log_path).read_text().splitlines()
        if (r := json.loads(line)).get("event") == "train"
    ]
    assert [r["step"] for r in records] == [1, *range(25, steps + 1, 25)]
    assert all(math.isfinite(v) for r in records for v in r.values() if isinstance(v, (float, int)))
    result = {
        "checkpoint": checkpoint,
        "step": steps,
        "original_planned_updates": cfg["steps"],
        "source_bundle_sha256": SOURCE,
        "seed": cfg["seed"],
        "model_tensors": 91,
        "EMA_tensors": 91,
        "AdamW_states": 89,
        "all_state_finite": True,
        "complete_RNG_present": True,
        "all_original_recipe_fields_exact_except_resolved_validation_protocol_path": True,
        "four_manifest_and_validation_protocol_hashes_verified": True,
        "source_snapshot_files_exact": True,
        "training_log": {
            "path": str(log_path),
            "sha256": sha(log_path),
            "train_rows": len(records),
        },
        "learning_rates": [g["lr"] for g in state["optimizer"]["param_groups"]],
    }
    return result, records


def crop_sha(crop):
    return crop.get("checkpoint_sha256", crop.get("model", {}).get("sha256"))


def pixels(path, crop):
    assert sha(path) == crop["png_sha256"]
    assert [p["png_xywh"] for p in crop["panels"]] == RECTANGLES
    assert crop["pixel_scale"] == "1 image pixel = 1 PNG pixel; open original at 100%"
    with Image.open(path) as im:
        assert im.mode == "RGB" and im.size == (512, 192)
        return np.array(im)


def preview_difference(expected, actual):
    difference = np.abs(expected.astype(np.int16) - actual.astype(np.int16))
    changed = int(np.count_nonzero(difference))
    maximum = int(difference.max())
    assert maximum <= DISPLAY_MAX_LSB and changed <= DISPLAY_MAX_CHANGED_CHANNEL_VALUES
    return {"changed_channel_values": changed, "maximum_8bit_code_difference": maximum}


def audit_panels(outputs, checkpoints, *, replay_extra_models=False):
    """Inspect actual selected artifacts; replay can retain extra historical models."""
    selected = {c["sha256"]: c["arm"] for c in checkpoints}
    assert len(selected) == 2
    old_runs = historical_runs(OLD_REGISTRY, OLD_REGISTRY_SHA)
    images, floats, files, runs, display_checks, tif_crops = [], [], [], {}, [], []
    for panel, count in PANELS.items():
        root = Path(outputs[panel])
        report = root / ("report.json" if panel in {"gfx", "three-camera"} else "summary.json")
        data = read(report)
        allowed = set(selected) | ({RAWNIND} if panel == "three-camera" else set())
        if not replay_extra_models:
            assert len(data["models"]) == (3 if panel == "three-camera" else 2)
            assert {m.get("sha256", m.get("weight_sha256")) for m in data["models"]} == allowed
            assert len(data["native_crops"]) == count
        candidate_labels = {m["label"] for m in data["models"] if m.get("sha256") in selected}
        assert len(candidate_labels) == 2
        crops = [
            c
            for c in data["native_crops"]
            if crop_sha(c) in selected
            and (panel != "three-camera" or c["baseline"]["gain_mode"] == "cfa-channel")
        ]
        assert len(crops) == count
        previous_report = Path(old_runs[panel]["report"])
        assert sha(previous_report) == old_runs[panel]["report_sha256"]
        previous = read(previous_report)
        old_crops = [c for c in previous["native_crops"] if crop_sha(c) == PARENT]
        float_lookup = {}
        for item in data.get("float_contexts", []):
            if panel == "three-camera" and item["model"] not in (
                candidate_labels
                | {"Bilinear", "Malvar 2004, WB", "Variance prior + Malvar", "RawNIND:CFA-channel"}
            ):
                assert replay_extra_models
                continue
            path = root / item["image"]
            assert sha(path) == item["sha256"] and item["dtype"] == "float32"
            value = np.load(path, mmap_mode="r", allow_pickle=False)
            assert value.dtype == np.float32 and list(value.shape) == item["shape"]
            assert np.isfinite(value).all()
            floats.append({"path": str(path), "sha256": sha(path), "shape": list(value.shape)})
            if panel == "gfx":
                matching = [
                    old
                    for old in previous["float_contexts"]
                    if old["region"] == item["region"] and old["role"] == item["role"]
                ]
                assert len(matching) == 1 and item["sha256"] == matching[0]["sha256"]
                assert sha(previous_report.parent / matching[0]["image"]) == item["sha256"]
            if panel == "three-camera":
                key = item["source"], item["model"]
                assert key not in float_lookup
                float_lookup[key] = (item, value)
        if panel == "three-camera":
            assert len(float_lookup) == 18
            sources = {key[0] for key in float_lookup}
            assert len(sources) == 3
            assert all(sum(key[0] == source for key in float_lookup) == 6 for source in sources)
        gfx_frames = {}
        if panel == "gfx":
            frames = [f for f in data["full_frames"] if f["model_label"] in candidate_labels]
            assert len(frames) == 2
            for frame in frames:
                assert len(frame["files"]) == 2 and frame["display_exposure"] == 4.0
                for item in frame["files"]:
                    path = root / item["path"]
                    assert sha(path) == item["sha256"] and path.stat().st_size == item["bytes"]
                    with tifffile.TiffFile(path) as tif:
                        page = tif.pages[0]
                        assert page.shape == (8746, 11662, 3)
                        assert page.bitspersample == 16 and page.samplesperpixel == 3
                        description = json.loads(page.description)
                        assert description["bits_per_sample"] == 16
                        if "srgb16" in path.name:
                            assert description["color_space"] == "sRGB" and 34675 in page.tags
                        else:
                            assert description["color_space"] == "linear-camera-RGB"
                    value = tifffile.memmap(path, mode="r")
                    codes = int(np.unique(value[::97, ::101]).size)
                    assert value.dtype == np.uint16 and codes > 256
                    files.append({**item, "path": str(path), "sampled_unique_codes": codes})
                    if "srgb16" in path.name:
                        gfx_frames[frame["model_label"]] = value
        seen = set()
        per_arm = {digest: set() for digest in selected}
        for crop in crops:
            digest, key = crop_sha(crop), identity(panel, crop)
            assert (digest, key) not in seen
            seen.add((digest, key))
            per_arm[digest].add(key)
            matching = [c for c in old_crops if identity(panel, c) == key]
            assert len(matching) == 1, (panel, key)
            old = matching[0]
            for field in [
                *FIELDS,
                "variance_multiplier",
                "validation_index",
                "validation_seed",
                "source_id",
                "noisy_sha256",
            ]:
                assert (field in crop) == (field in old) and crop.get(field) == old.get(field), (
                    panel,
                    field,
                )
            actual = pixels(root / crop["image"], crop)
            retained = pixels(previous_report.parent / old["image"], old)
            for x in [8, 344]:
                np.testing.assert_array_equal(
                    actual[24:184, x : x + 160], retained[24:184, x : x + 160]
                )
            assert crop["display_exposure"] > 0
            if panel in {"gfx", "three-camera"}:
                assert "not GT" in crop["panels"][2]["label"]
            if panel == "full427":
                assert crop["reference"] == "Exact synthetic clean target"
            if panel == "gfx":
                assert crop["full_frame"] and crop["display_exposure"] == 4.0
                x, y = crop["region"]["noisy_xy"]
                assert crop["region"]["size"] == 160
                codes = gfx_frames[crop["model_label"]][y : y + 160, x : x + 160].astype(np.uint32)
                # 65535 = 255 * 257: nearest 8-bit code from the full sRGB16 TIFF.
                preview = ((codes + 128) // 257).astype(np.uint8)
                np.testing.assert_array_equal(preview, actual[24:184, 176:336])
                tif_crops.append(
                    {
                        "png": str(root / crop["image"]),
                        "region": crop["region"]["name"],
                        "exact_full_sRGB16_native_ROI": True,
                    }
                )
            if panel == "three-camera":
                assert crop["baseline"]["sha256"] == RAWNIND
                assert crop["baseline"]["gain_mode"] == "cfa-channel"
                wb = torch.tensor(crop["white_balance"])[None]
                matrix = torch.tensor(crop["camera_to_srgb"])[None]
                for label, x in [
                    ("Malvar 2004, WB", 8),
                    (crop["model_label"], 176),
                    ("RawNIND:CFA-channel", 344),
                ]:
                    metadata, value = float_lookup[crop["source"], label]
                    assert metadata["context_xywh"] == crop["context_xywh"]
                    displayed = display_crop(
                        torch.from_numpy(np.array(value, copy=True)),
                        wb,
                        matrix,
                        crop["context_roi_xywh"],
                        exposure=crop["display_exposure"],
                    )
                    codes = np.rint(displayed.clip(0, 1) * 255).astype(np.uint8)
                    display_checks.append(
                        {
                            "png": str(root / crop["image"]),
                            "panel_x": x,
                            **preview_difference(codes, actual[24:184, x : x + 160]),
                        }
                    )
            images.append(
                {
                    "panel": panel,
                    "path": str(root / crop["image"]),
                    "sha256": crop["png_sha256"],
                    "arm": selected[digest],
                    "checkpoint_sha256": digest,
                    "metadata": crop,
                    "saved_V60_control": str(previous_report.parent / old["image"]),
                }
            )
        first, second = per_arm.values()
        assert len(first) == len(second) == count // 2 and first == second
        if panel == "gfx":
            assert {c["region"]["name"] for c in crops} == {
                "overcast-sky",
                "building-detail",
                "foliage",
                "chain-link-fence",
            }
        runs[panel] = {
            "report": str(report),
            "report_sha256": sha(report),
            "selected_native_PNGs": len(crops),
        }
    assert len(images) == 38 and len(floats) == 26 and len(files) == 4
    assert len(display_checks) == 36 and len(tif_crops) == 8
    return {
        "runs": runs,
        "images": images,
        "float_arrays": floats,
        "full_RGB16_files": files,
        "common_noisy_reference_pixels_and_transform_metadata_exact_to_V60": True,
        "three_camera_saved_F32_to_PNG_checks": display_checks,
        "three_camera_display_check_bounds": {
            "maximum_LSB": DISPLAY_MAX_LSB,
            "maximum_changed_channel_values_per_panel": DISPLAY_MAX_CHANGED_CHANNEL_VALUES,
            "scope": "8-bit preview rerender only; every mismatch retained. No bound on restoration/metric/color errors.",
        },
        "GFX_full_sRGB16_to_native_PNG_checks": tif_crops,
        "limitations": "Integrity and declared display-rounding checks, not actual visual inspection or quality. Real GFX/RawNIND references are not exact GT; photographic synthetic targets are exact for that synthetic observation only.",
    }


def main(workflow, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    output = writable_path(output)
    assert not output.exists()
    status, training = read(workflow), read(TRAINING)
    assert status["status"] == "completed-primary-panels-awaiting-hue-statistical-and-native-review"
    assert training["status"] == "trained-both-first4000-awaiting-controlled-quality-review"
    exited(status)
    exited(training)
    plan, train_plan = read(status["plan"]), read(training["plan"])
    assert plan["previous_owner"] == training["controller"]
    assert status["checkpoints"] == training["checkpoints"]
    assert train_plan["parent"]["sha256"] == PARENT and train_plan["planned_updates"] == 20000
    for guard in [plan, train_plan]:
        for path, digest in {
            **guard["inputs"],
            **guard["source_files"],
            **guard.get("tools", {}),
        }.items():
            assert sha(path) == digest, path
    checkpoints = sorted(training["checkpoints"], key=lambda c: c["arm"])
    assert [c["arm"] for c in checkpoints] == ["control", "expanded"]
    recipes = []
    for item in train_plan["configs"]:
        assert sha(item["path"]) == item["sha256"]
        recipes.append(yaml.safe_load(Path(item["path"]).read_text()))
    skip = {"manifest", "run", "experiment_notes"}
    assert {k: v for k, v in recipes[0].items() if k not in skip} == {
        k: v for k, v in recipes[1].items() if k not in skip
    }
    states, logs = {}, {}
    for checkpoint, recipe in zip(checkpoints, recipes, strict=True):
        arm = checkpoint["arm"]
        assert recipe["steps"] == 20000 and recipe["seed"] == 49
        log = Path(training["plan"]).parent / (arm + "-first4000-metrics.jsonl")
        states[arm], logs[arm] = audit_state(
            checkpoint, recipe, train_plan["source_files"], train_plan["inputs"], PARENT, log, 4000
        )
    observed = []
    for first, second in zip(logs["control"], logs["expanded"], strict=True):
        assert [first[k] for k in ["step", "domain", "lr"]] == [
            second[k] for k in ["step", "domain", "lr"]
        ]
        equal = first["batch_sha256"] == second["batch_sha256"]
        if first["domain"] != "synthetic":
            assert equal, first["step"]
        observed.append(
            {"step": first["step"], "domain": first["domain"], "batch_hash_exact": equal}
        )
    assert len(observed) == 161 and any(not r["batch_hash_exact"] for r in observed)
    result = {
        "status": "completed-independent-long-data-state-native-and-RGB16-integrity-audit",
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "training_workflow": str(TRAINING),
        "training_workflow_sha256": sha(TRAINING),
        "boundary": states,
        "logged_observations": observed,
        **audit_panels(status["outputs"], checkpoints),
        "driver_sha256": sha(__file__),
        "CUDA_initialized": torch.cuda.is_initialized(),
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for arm, item in states.items():
        (output / (arm + "-training-metrics.jsonl")).write_bytes(
            Path(item["training_log"]["path"]).read_bytes()
        )
    print(json.dumps({"output": str(output), "PNG": 38, "F32": 26, "RGB16": 4}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    main(**vars(parser.parse_args()))
