"""Fixed V89 zero/unit spectral interventions on two photos and cached GFX."""

import argparse
import copy
import gc
import json
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from diagnose_spectral_gate_components import components, fingerprint, guard, resources
from PIL import Image
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import read, ref, save

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import _number, observation


def photo_inputs(plan):
    result, tensors = [], []
    for crop in plan["photo_crops"]:
        source = crop["source"]
        path = Path(source["cache"])
        if not path.is_absolute():
            path = Path(plan["photo_manifest"]).parent / path
        assert ref(path)["sha256"] == source["cache_sha256"]
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        assert list(array.shape) == source["shape"] and array.dtype == np.uint16
        x, y, width, height = crop["cache_context_xywh"]
        rgb = (
            torch.from_numpy(
                array[y : y + height, x : x + width].copy().astype(np.float32)
            ).permute(2, 0, 1)
            / 65535
        )
        assert rgb.shape == (3, 256, 256)
        tensors.append(rgb)
        result.append(
            {
                "source": source,
                "cache": ref(path),
                "context_xywh": crop["cache_context_xywh"],
                "ROI_xywh": crop["displayed_cache_ROI_xywh"],
            }
        )
    return torch.stack(tensors), result


def gfx_inputs(plan):
    fixture = read(plan["gfx_fixture"]["path"])
    original = fixture["serving_probes"][0]["observation"]
    assert ref(original["path"]) == original
    with np.load(original["path"], allow_pickle=False) as arrays:
        values = {k: torch.from_numpy(arrays[k].copy()) for k in arrays.files}
    assert values["packed"].shape == (4, 4, 256, 256)
    for i, region in enumerate(fixture["gfx_regions"]):
        for item in [region["noisy_packed"], region["reference_RGB"]]:
            assert ref(item["path"]) == item
        assert np.array_equal(
            values["packed"][i : i + 1].numpy(),
            np.load(region["noisy_packed"]["path"], allow_pickle=False),
        )
    return values, fixture


def panel(path, crop, index):
    assert ref(path)["sha256"] == crop["png_sha256"]
    with Image.open(path) as image:
        pixels = np.asarray(image).copy()
    x, y, w, h = crop["panels"][index]["png_xywh"]
    assert w == h == 160
    return pixels[y : y + h, x : x + w].astype(np.float64) / 255


def main(plan_path, output, preflight):
    plan = read(plan_path)
    guard(plan)
    resources(plan)
    assert ref(__file__) == plan["worker"]
    root = writable_path(output)
    assert root.is_relative_to(Path(plan["root"]))
    root.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2 if preflight else 4)
    rgb, photo_meta = photo_inputs(plan)
    gfx, fixture = gfx_inputs(plan)
    if preflight:
        assert not torch.cuda.is_initialized()
        save(
            root / "summary.json",
            {
                "status": "completed-photo-GFX-input-preflight-without-new-neural-inference",
                "driver": ref(__file__),
                "plan": ref(plan_path),
                "photos": photo_meta,
                "photo_tensor_sha256": fingerprint({"rgb": rgb}),
                "GFX_input_sha256": fingerprint(gfx),
                "native_contexts": [256, 512],
                "original_RAFs_opened": False,
            },
        )
        print({"status": "completed-input-preflight", "photo_sources": 2, "GFX_regions": 4})
        return
    prior = read(Path(plan["root"]) / "cpu-preflight/summary.json")
    assert (
        prior["driver"] == plan["worker"]
        and prior["status"] == "completed-photo-GFX-input-preflight-without-new-neural-inference"
    )
    assert psutil.virtual_memory().available > 40 * 2**30
    device = torch.device("cuda", torch.cuda.current_device())
    torch.cuda.set_per_process_memory_fraction(
        16 * 2**30 / torch.cuda.get_device_properties(device).total_memory, device
    )
    torch.backends.cudnn.benchmark = False
    protocol = plan["photo_protocol"]
    roi = [48, 48, 160, 160]
    started = time.monotonic()
    source_ids = [c["source_id"] for c in plan["photo_crops"]]
    witnesses = {}
    with Path(plan["original_photo_cases"]["path"]).open() as stream:
        for line in stream:
            if not any(identity in line for identity in source_ids):
                continue
            row = json.loads(line)
            if (
                row["model"] == "Malvar2004:WB"
                and row["pattern"] == "RGGB"
                and row["id"] in source_ids
            ):
                witnesses[(row["id"], row["condition"])] = row["metrics"]
    assert len(witnesses) == 14
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state(device).clone()
    results = []
    reports = []
    with torch.random.fork_rng(devices=[device.index]), torch.inference_mode():
        model, state = load_checkpoint(plan["checkpoint"]["path"], device)
        assert state["loaded_sha256"] == plan["checkpoint"]["sha256"]
        del state
        model.eval().requires_grad_(False).to(memory_format=torch.channels_last)
        state_before = model_hash(model)
        dino_before = model_hash(model.context.backbone)
        assert dino_before == plan["DINO_sha256"]
        for condition in protocol["conditions"]:
            resources(plan)
            assert time.monotonic() - started < plan["timeout_seconds"]
            out = root / ("photo-" + condition["name"])
            out.mkdir()
            with amp_context(device, dtype="float32"):
                batch = observation(
                    rgb.to(device),
                    [c["source_id"] for c in plan["photo_crops"]],
                    condition,
                    "RGGB",
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    protocol["seed"],
                )
                for name in ["packed", "variance"]:
                    batch[name] = batch[name].contiguous(memory_format=torch.channels_last)
                noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
            model.set_noise(condition["shot"], condition["read"])
            values = components(model, batch, device)
            cpu = {k: v.cpu() for k, v in batch.items()}
            np.savez_compressed(
                out / "arrays.npz",
                **{k: v.numpy() for k, v in cpu.items()},
                **{k: v.numpy() for k, v in values.items()},
                noisy=noisy.cpu().numpy(),
            )
            crop_rows = []
            case_rows = []
            trim = (slice(None), slice(None), slice(8, -8), slice(8, -8))
            with amp_context(device, dtype="float32"):
                noisy_scores = quality_metrics(
                    noisy[trim], batch["target"][trim], batch["wb"], batch["matrix"]
                )
            max_ulp = 0.0
            nullable_fields = 0
            for i, crop in enumerate(plan["photo_crops"]):
                expected = witnesses[(crop["source_id"], condition["name"])]
                for name, tensor in noisy_scores.items():
                    value = _number(tensor[i])
                    old = expected[name]
                    if old is None:
                        assert value is None, (condition["name"], name, value)
                        nullable_fields += 1
                        continue
                    assert value is not None, (condition["name"], name, old)
                    spacing = abs(float(np.spacing(np.float32(old))))
                    ulp = abs(value - old) / spacing
                    assert ulp <= plan["classical_metric_ULP_bound"], (condition["name"], name, ulp)
                    max_ulp = max(max_ulp, ulp)
            for mode in ["full", "base", "unit"]:
                prediction = values[mode].to(device)
                with amp_context(device, dtype="float32"):
                    scores = quality_metrics(
                        prediction[trim], batch["target"][trim], batch["wb"], batch["matrix"]
                    )
                for i, crop in enumerate(plan["photo_crops"]):
                    label = "V89/" + mode
                    entry = save_triplet(
                        out,
                        crop["source_id"] + ":" + mode,
                        [
                            (
                                name,
                                display_crop(
                                    v[i : i + 1],
                                    batch["wb"][i : i + 1],
                                    batch["matrix"][i : i + 1],
                                    roi,
                                ),
                            )
                            for name, v in [
                                ("Noisy (Malvar)", noisy),
                                (mode, prediction),
                                ("GT (synthetic)", batch["target"]),
                            ]
                        ],
                        caption=crop["source_id"] + " / " + condition["name"] + " / " + label,
                        metadata={
                            "source_id": crop["source_id"],
                            "source": crop["source"],
                            "validation_index": crop["validation_index"],
                            "validation_seed": crop["validation_seed"],
                            "cache_context_xywh": crop["cache_context_xywh"],
                            "displayed_cache_ROI_xywh": crop["displayed_cache_ROI_xywh"],
                            "evaluation_tile_xywh": roi,
                            "condition": condition,
                            "pattern": "RGGB",
                            "white_balance": protocol["white_balance"],
                            "camera_to_srgb": protocol["camera_to_srgb"],
                            "model_label": label,
                            "checkpoint_sha256": plan["checkpoint"]["sha256"],
                            "display_exposure": 1,
                            "reference": "Exact synthetic clean target; base/unit are fixed interventions, not separately trained models.",
                        },
                    )
                    crop_rows.append(entry)
                    case_rows.append(
                        {
                            "source_id": crop["source_id"],
                            "condition": condition["name"],
                            "mode": mode,
                            "metrics": {k: _number(v[i]) for k, v in scores.items()},
                        }
                    )
                    if condition["name"] == "iso12800-prior":
                        # Match actual original noisy/GT viewing pixels, without
                        # claiming exact neural-output replay across algorithms.
                        current = out / entry["image"]
                        original = (
                            Path(plan["original_photo_report"]["path"]).parent / crop["image"]
                        )
                        for part in [0, 2]:
                            assert np.array_equal(
                                np.rint(panel(current, entry, part) * 255).astype(np.uint8),
                                np.rint(panel(original, crop, part) * 255).astype(np.uint8),
                            )
            report = out / "report.json"
            save(
                report,
                {
                    "native_crops": crop_rows,
                    "scope": "Fixed V89 full/base/unit on the same original photo/condition. Exact synthetic target; no new training or promoted policy.",
                },
            )
            reports.append(
                {"panel": "photo-" + condition["name"], "kind": "synthetic", "report": ref(report)}
            )
            results.append(
                {
                    "kind": "photo",
                    "condition": condition,
                    "inputs_sha256": fingerprint(cpu),
                    "classical_max_ULPs_to_original": max_ulp,
                    "classical_nullable_fields_support_exact": nullable_fields,
                    "cases": case_rows,
                    "gate": values["gate"].flatten().tolist(),
                    "upper_censored_fraction_by_image": (cpu["packed"] >= 1 - 0.5 / 65535)
                    .float()
                    .mean((1, 2, 3))
                    .tolist(),
                    "arrays": ref(out / "arrays.npz"),
                }
            )
            print(
                {"event": "completed-photo-condition", "condition": condition["name"]}, flush=True
            )
        out = root / "gfx"
        out.mkdir()
        model.set_noise(fixture["conditioning"]["shot"], fixture["conditioning"]["read"])
        batch = {k: v.to(device) for k, v in gfx.items()}
        values = components(model, batch, device)
        old = np.load(plan["original_gfx_RGB"]["path"], allow_pickle=False)
        replay_error = float(
            np.max(np.abs(old.astype(np.float64) - values["full"].numpy().astype(np.float64)))
        )
        assert replay_error <= plan["GFX_full_replay_atol"], replay_error
        np.savez_compressed(
            out / "arrays.npz",
            **{k: v.numpy() for k, v in gfx.items()},
            **{k: v.numpy() for k, v in values.items()},
        )
        crops = []
        for i, template in enumerate(plan["gfx_crops"]):
            region = fixture["gfx_regions"][i]
            assert template["region"] == region["region"]
            x, y = region["region"]["noisy_xy"]
            cx, cy, _w, _h = region["context_xywh"]
            view = [x - cx, y - cy, 160, 160]
            original = Path(plan["original_gfx_report"]["path"]).parent / template["image"]
            for mode in ["full", "base", "unit"]:
                metadata = {
                    k: copy.deepcopy(v)
                    for k, v in template.items()
                    if k
                    not in [
                        "image",
                        "caption",
                        "pixel_scale",
                        "display_encoding",
                        "panels",
                        "png_sha256",
                        "model",
                        "model_label",
                        "checkpoint_sha256",
                        "runtime",
                    ]
                }
                metadata.update(
                    model_label="V89/" + mode, checkpoint_sha256=plan["checkpoint"]["sha256"]
                )
                restored = display_crop(
                    values[mode][i : i + 1],
                    gfx["wb"][i : i + 1],
                    gfx["matrix"][i : i + 1],
                    view,
                    exposure=4,
                )
                crops.append(
                    save_triplet(
                        out,
                        region["region"]["name"] + ":" + mode,
                        [
                            ("Noisy (Malvar)", panel(original, template, 0)),
                            (mode, restored),
                            ("ISO100 ref (not GT)", panel(original, template, 2)),
                        ],
                        caption=region["region"]["name"] + " / V89/" + mode,
                        metadata=metadata,
                    )
                )
        report = out / "report.json"
        save(
            report,
            {
                "native_crops": crops,
                "scope": "Cached original native512/B4 observations. Independent ISO100 f/5.6 reference is not GT; no GFX reference scores, RAW decoding or full-frame inference.",
            },
        )
        reports.append({"panel": "gfx", "kind": "gfx", "report": ref(report)})
        results.append(
            {
                "kind": "gfx",
                "inputs_sha256": fingerprint(gfx),
                "full_RGB_replay_max_abs_error": replay_error,
                "gate": values["gate"].flatten().tolist(),
                "upper_censored_fraction_by_image": (gfx["packed"] >= 1 - 0.5 / 65535)
                .float()
                .mean((1, 2, 3))
                .tolist(),
                "arrays": ref(out / "arrays.npz"),
            }
        )
        assert (
            model_hash(model) == state_before and model_hash(model.context.backbone) == dino_before
        )
        del model
        gc.collect()
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state(device)
    )
    guard(plan)
    resources(plan)
    save(
        root / "summary.json",
        {
            "status": "completed-fixed-spectral-photo-GFX-component-pilot-awaiting-native-review",
            "plan": ref(plan_path),
            "driver": ref(__file__),
            "checkpoint": plan["checkpoint"],
            "model_state_sha256_unchanged": state_before,
            "DINO_sha256_unchanged": dino_before,
            "CPU_CUDA_RNG_unchanged": True,
            "results": results,
            "native_reports": reports,
            "new_training_updates": 0,
            "production_or_policy_changed": False,
            "scope": "Two fixed original development photos under all7 original conditions plus4 standing cached GFX native512 regions. Full/base/unit conditional interventions on the same V89 model, with no gate sweep/calibration. Exact synthetic GT for photos; independent ISO100 reference for GFX, not GT. No real-reference scores, independent generalization/SOTA claim, training extension or promotion. Actual native viewing and numerical interpretation remain required.",
        },
    )
    print(
        {
            "status": "completed-fixed-photo-GFX-component-pilot",
            "photo_case_slots": 14,
            "GFX_regions": 4,
            "native_triplets": 54,
        },
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--preflight", action="store_true")
    a = p.parse_args()
    main(a.plan, a.output, a.preflight)
