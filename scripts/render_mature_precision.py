"""Render saved mature precision outputs at native scale, without model inference."""

import argparse
import copy
import json
import os
from pathlib import Path

import numpy as np
from build_native_crop_board import MODEL_FIELDS, build, read_crop
from train_directional_bank_trial import read, ref

POLICIES = ("fp32", "fp16", "fp16-hidden")
GPU_STATUS = "completed-mature-precision-GPU-arrays-awaiting-native-and-independent-scalar-review"


def checked(item):
    if ref(item["path"]) != {k: item[k] for k in ("path", "sha256")}:
        raise ValueError(f"Changed recorded input: {item['path']}")
    return Path(item["path"])


def save_new(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def arrays(item):
    with np.load(checked(item), allow_pickle=False) as data:
        return {k: data[k].copy() for k in data.files}


def prediction(item, shape):
    value = np.load(checked(item), allow_pickle=False)
    if value.dtype != np.float32 or value.shape != shape or not np.isfinite(value).all():
        raise ValueError("Expected finite saved native FP32 camera RGB")
    return value


def gpu_methods(plan_path, receipt_path):
    """Only a genuine completed pilot can supply the three new policy identities."""
    plan, receipt = read(plan_path), read(receipt_path)
    if receipt["status"] != GPU_STATUS or receipt["plan"] != ref(plan_path):
        raise ValueError("Missing successful GPU receipt for this exact plan")
    if not receipt["backend_settings_restored"]:
        raise ValueError("GPU backend restoration failed")
    if [m["model"] for m in receipt["models"]] != list(plan["models"]):
        raise ValueError("GPU model set/order differs from the frozen pilot")
    methods = []
    fixture_ids = [f["id"] for f in plan["fixtures"]]
    for model in receipt["models"]:
        if model["checkpoint"] != plan["models"][model["model"]]:
            raise ValueError("GPU checkpoint differs from the frozen pilot")
        captures = model["captures"]
        keys = [(c["policy"], c["fixture"]) for c in captures]
        if (
            len(keys) != len(set(keys))
            or set(keys) != {(p, f) for p in POLICIES for f in fixture_ids}
            or any(c["model"] != model["model"] for c in captures)
        ):
            raise ValueError("GPU capture rectangle is incomplete or duplicated")
        for policy in POLICIES:
            methods.append(
                {
                    "label": model["model"] + ":" + policy,
                    "model": model["model"],
                    "policy": policy,
                    "checkpoint": model["checkpoint"],
                    "RGB": {c["fixture"]: c["RGB"] for c in captures if c["policy"] == policy},
                }
            )
    return methods


def historical_methods(plan, gfx_registry):
    """Genuine old FP32 outputs preflight rendering; they never impersonate FP16."""
    methods, evidence = [], []
    photo_root = checked(plan["photo_registry"]).parent.parent
    gfx = read(checked(gfx_registry))
    for model, checkpoint in plan["models"].items():
        for policy in ("original", "autotuned"):
            path = photo_root / f"{model}-{policy}" / "result.json"
            report = read(path)
            if (report["arm"], report["policy"], report["checkpoint"]) != (
                model,
                policy,
                checkpoint,
            ):
                raise ValueError("Historical photo policy/checkpoint identity differs")
            label = f"{model}:{policy}-FP32"
            gfx_crops = [c for c in gfx["native_crops"] if c["model_label"] == label]
            if len(gfx_crops) != 4 or any(
                c["checkpoint_sha256"] != checkpoint["sha256"] for c in gfx_crops
            ):
                raise ValueError("Historical GFX method is missing or changed")
            gfx_array = gfx_crops[0]["model"]["RGB"]
            if any(c["model"]["RGB"] != gfx_array for c in gfx_crops):
                raise ValueError("Historical GFX crops use different predictions")
            rgb = {plan["fixtures"][0]["id"]: gfx_array}
            if len(report["predictions"]) != 2:
                raise ValueError("Historical photo predictions are incomplete")
            for index, row in enumerate(report["predictions"]):
                fixture = plan["fixtures"][index + 1]
                if row["index"] != index or row["observation"] != fixture["arrays"]:
                    raise ValueError("Historical photo observation differs")
                rgb[fixture["id"]] = row["RGB"]
            methods.append(
                {
                    "label": label,
                    "model": model,
                    "policy": policy + "-FP32",
                    "checkpoint": checkpoint,
                    "RGB": rgb,
                }
            )
            evidence.append(ref(path))
    return methods, evidence


def render(plan, gfx_registry, methods, output, *, evidence, scope):
    import torch

    from demosaic.reporting import display_crop, save_triplet

    if torch.cuda.is_initialized():
        raise ValueError("Saved-output renderer must remain CPU-only")
    if len({m["label"] for m in methods}) != len(methods):
        raise ValueError("Method labels must be unique")
    output = Path(output)
    if output.exists():
        raise ValueError("Choose a new render directory")
    photo_path = checked(plan["photo_registry"])
    gfx_path = checked(gfx_registry)
    photo_templates = read(photo_path)["native_crops"]
    gfx_templates = [
        c for c in read(gfx_path)["native_crops"] if c["model_label"] == "V43:original-FP32"
    ]
    gfx_fixture = read(checked(plan["gfx_fixture"]))
    if len(photo_templates) != 2 or len(gfx_templates) != 4:
        raise ValueError("Expected two photos and all four standing GFX regions")
    fixtures = plan["fixtures"][:3]
    if [f["kind"] for f in fixtures] != ["gfx", "photo", "photo"]:
        raise ValueError("Unexpected frozen fixture order")
    observations = {f["id"]: arrays(f["arrays"]) for f in fixtures}
    templates = []
    for index, template in enumerate(photo_templates):
        fixture = fixtures[index + 1]
        values = observations[fixture["id"]]
        if (
            template["observation"] != fixture["arrays"]
            or template["condition"] != fixture["condition"]
        ):
            raise ValueError("Photo template observation/noise differs from pilot")
        if (
            template["evaluation_tile_xywh"] != [48, 48, 160, 160]
            or template["display_exposure"] != 1
        ):
            raise ValueError("Photo display/ROI differs from the fixed pilot")
        for key, recorded in [
            ("wb", template["white_balance"]),
            ("matrix", template["camera_to_srgb"]),
        ]:
            np.testing.assert_array_equal(values[key][0], np.asarray(recorded, np.float32))
        parts, _, _ = read_crop(photo_path, template, "synthetic")
        templates.append(
            ("synthetic", fixture, 0, template, parts, template["evaluation_tile_xywh"])
        )
    for index, template in enumerate(gfx_templates):
        fixture = fixtures[0]
        values = observations[fixture["id"]]
        expected = gfx_fixture["gfx_regions"][index]
        if (
            template["source"]["fixture"] != plan["gfx_fixture"]
            or template["source"]["observation"] != fixture["arrays"]
            or template["region"] != expected["region"]
            or template["context_xywh"] != expected["context_xywh"]
        ):
            raise ValueError("GFX source, region or context differs from pilot")
        if (
            template["conditioning"] != {k: fixture["condition"][k] for k in ("shot", "read")}
            or template["display_exposure"] != 4
        ):
            raise ValueError("GFX noise/display differs from fixed pilot")
        for key, recorded in [("wb", template["shared_wb"]), ("matrix", template["shared_matrix"])]:
            np.testing.assert_array_equal(values[key][index], np.asarray(recorded, np.float32))
        x, y = template["region"]["noisy_xy"]
        cx, cy, _, _ = template["context_xywh"]
        roi = [x - cx, y - cy, 160, 160]
        if roi != [176, 176, 160, 160]:
            raise ValueError("Standing GFX ROI differs from native512 fixture")
        parts, _, _ = read_crop(gfx_path, template, "gfx")
        templates.append(("gfx", fixture, index, template, parts, roi))
    # Validate all RGB files before writing any artifacts. Targets never enter a model.
    for method in methods:
        if method["checkpoint"] != plan["models"][method["model"]]:
            raise ValueError("Rendering checkpoint differs from the frozen pilot")
        for fixture in fixtures:
            values = observations[fixture["id"]]
            shape = (
                len(values["packed"]),
                3,
                values["packed"].shape[-2] * 2,
                values["packed"].shape[-1] * 2,
            )
            prediction(method["RGB"][fixture["id"]], shape)
    output.mkdir(parents=True, exist_ok=False)
    crops = {"synthetic": [], "gfx": []}
    for method in methods:
        for kind, fixture, index, template, parts, roi in templates:
            values = observations[fixture["id"]]
            shape = (
                len(values["packed"]),
                3,
                values["packed"].shape[-2] * 2,
                values["packed"].shape[-1] * 2,
            )
            rgb_ref = method["RGB"][fixture["id"]]
            rgb = torch.from_numpy(prediction(rgb_ref, shape)[index : index + 1].copy())
            metadata = {k: copy.deepcopy(v) for k, v in template.items() if k not in MODEL_FIELDS}
            label = method["label"]
            metadata.update(
                model_label=label,
                checkpoint_sha256=method["checkpoint"]["sha256"],
                compute_precision=method["policy"],
                device="saved-CUDA-output/CPU-display",
                model={
                    "label": label,
                    "sha256": method["checkpoint"]["sha256"],
                    "policy": method["policy"],
                    "RGB": rgb_ref,
                },
            )
            case = template.get("source_id", template.get("region", {}).get("name"))
            crop = save_triplet(
                output / kind,
                label + ":" + case,
                [
                    ("Noisy (Malvar)", parts[0].astype(np.float64) / 255),
                    (
                        "Denoised",
                        display_crop(
                            rgb,
                            torch.from_numpy(values["wb"][index : index + 1]),
                            torch.from_numpy(values["matrix"][index : index + 1]),
                            roi,
                            exposure=template["display_exposure"],
                        ),
                    ),
                    (template["panels"][2]["label"], parts[2].astype(np.float64) / 255),
                ],
                caption=case + " / " + label,
                metadata=metadata,
            )
            crops[kind].append(crop)
    boards = []
    for kind in ("synthetic", "gfx"):
        report_path = output / kind / "report.json"
        save_new(report_path, {"native_crops": crops[kind], "scope": scope})
        board_path = output / (kind + "-native.png")
        build([report_path], board_path, kind)
        boards.append(ref(board_path.with_suffix(".json")))
    result = {
        "status": "rendered-native-crops-awaiting-actual-manual-review",
        "driver": ref(__file__),
        "photo_registry": plan["photo_registry"],
        "gfx_registry": gfx_registry,
        "evidence": evidence,
        "methods": methods,
        "boards": boards,
        "triplets": sum(map(len, crops.values())),
        "native_cells_exact": sum(read(b["path"])["native_cells_exact"] for b in boards),
        "CUDA_initialized": torch.cuda.is_initialized(),
        "new_network_forwards": 0,
        "scope": scope,
    }
    save_new(output / "index.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("gfx_registry", type=Path)
    parser.add_argument("output", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--GPU-receipt", type=Path)
    source.add_argument("--historical-FP32", action="store_true")
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("Run this CPU-only renderer with CUDA_VISIBLE_DEVICES=''")
    plan = read(args.plan)
    registry = ref(args.gfx_registry)
    if args.historical_FP32:
        methods, evidence = historical_methods(plan, registry)
        scope = "Historical original/autotuned FP32 rendering preflight only; no FP16 predictions, new inference, quality/timing result or pilot completion. Actual native viewing remains required."
    else:
        methods = gpu_methods(args.plan, args.GPU_receipt)
        evidence = [ref(args.GPU_receipt)]
        scope = "Saved mature FP32/FP16 policy outputs only; exact native pixels and common transforms. GFX ISO100 is a separate reference, not GT. No scalar interpretation, inference, training, default change or promotion. Actual native viewing remains required."
    evidence.append(ref(args.plan))
    result = render(plan, registry, methods, args.output, evidence=evidence, scope=scope)
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("status", "triplets", "native_cells_exact", "new_network_forwards")
            }
        )
    )


if __name__ == "__main__":
    main()
