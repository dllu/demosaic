"""Compare fixed, input-selected held-out detail with shared cached observations."""

import argparse
import hashlib
import math
import shutil
from pathlib import Path

import numpy as np
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def tensor_hash(values):
    return {
        k: hashlib.sha256(v.detach().cpu().numpy().tobytes()).hexdigest() for k, v in values.items()
    }


def prepare(selection_path, root):
    import json

    import torch
    import yaml

    from demosaic.data import CleanDataset
    from demosaic.suite import observation

    selection = read(selection_path)
    assert selection["source_split"] == "val" and selection["source_bin_factor"] == 8
    assert selection["native_context_size"] == 256 and selection["native_ROI_size"] == 160
    inputs = [
        ref(selection_path),
        selection["source_manifest"],
        selection["protocol"],
        selection["training_manifest_exclusion_check"],
    ]
    for item in inputs:
        assert ref(item["path"]) == item
    training = {
        r["id"]
        for r in (json.loads(x) for x in Path(inputs[-1]["path"]).read_text().splitlines())
        if r["split"] == "train"
    }
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for source in [
        *REPO.glob("src/demosaic/*.py"),
        *[
            REPO / p
            for p in (
                "scripts/report_heldout_detail.py",
                "scripts/train_directional_bank_trial.py",
                "scripts/profile_raw_kernel_inference.py",
                "configs/evaluation.yaml",
                "pyproject.toml",
                "uv.lock",
                "LICENSE",
                "third_party/dinov3/LICENSE.md",
                "third_party/gaussian/Noise2VST-LICENSE",
                "third_party/gaussian/KAIR-LICENSE",
            )
        ],
    ]:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    save(root / "selection.json", selection)
    inputs.append(ref(root / "selection.json"))
    data = CleanDataset(
        inputs[1]["path"],
        split="val",
        patch_size=256,
        native_crop=True,
        seed=selection["dataset_seed"],
    )
    protocol = yaml.safe_load(Path(selection["protocol"]["path"]).read_text())
    conditions = {c["name"]: c for c in protocol["conditions"]}
    torch.set_num_threads(2)
    observations = []
    for case in selection["examples"]:
        i, source = case["index"], case["source"]
        assert source == data.rows[i] and source["id"] not in training
        assert ref(case["cache"]["path"]) == case["cache"]
        inputs.append(case["cache"])
        rgb = data[i]["rgb"][None]
        actual = rgb[0].permute(1, 2, 0).numpy()
        assert hashlib.sha256(actual.tobytes()).hexdigest() == case["clean256_RGB_float32_sha256"]
        for name in selection["conditions"]:
            condition = conditions[name]
            for pattern in selection["patterns"]:
                batch = observation(
                    rgb,
                    [source["id"]],
                    condition,
                    pattern,
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    protocol["seed"],
                )
                path = root / f"{source['id']}-{name}-{pattern}.npz"
                np.savez(path, **{k: v.numpy() for k, v in batch.items()})
                observations.append(
                    {
                        "case": case,
                        "condition": condition,
                        "pattern": pattern,
                        "arrays": ref(path),
                        "tensor_sha256": tensor_hash(batch),
                    }
                )
                inputs.append(ref(path))
    assert len(observations) == 12
    assert not torch.cuda.is_initialized()
    plan = {
        "root": str(root),
        "work": str(work),
        "selection": ref(root / "selection.json"),
        "observations": observations,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": selection["scope"],
    }
    save(root / "plan.json", plan)
    guard(plan)
    return root / "plan.json"


def run(plan_path, checkpoint_paths, labels, output, *, rawnind=None):
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.cfa import malvar
    from demosaic.inference import load_checkpoint
    from demosaic.metrics import quality_metrics
    from demosaic.reference import load_rawnind
    from demosaic.reporting import display_crop, save_triplet
    from demosaic.safety import writable_path
    from demosaic.suite import freeze_checkpoint

    assert len(checkpoint_paths) == len(labels) and len(set(labels)) == len(labels)
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    plan = read(plan_path)
    guard(plan)
    assert ref(plan["selection"]["path"]) == plan["selection"]
    selection = read(plan["selection"]["path"])
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    models, records, before = [], [], []
    for checkpoint, label in zip(checkpoint_paths, labels, strict=True):
        frozen, digest = freeze_checkpoint(checkpoint, output / "weights")
        model, state = load_checkpoint(frozen, "cpu")
        assert state["loaded_sha256"] == digest
        models.append(model.eval())
        records.append(
            {
                "label": label,
                "sha256": digest,
                "source": str(checkpoint),
                "snapshot": str(frozen),
                "step": state["step"],
                "effective_model_config": model.config.to_dict(),
                "compute_precision": "float32",
                "device": "cpu",
            }
        )
        before.append(model_hash(model))
        del state
    if rawnind:
        models.append(load_rawnind(rawnind, gain_mode="cfa-channel", device="cpu").eval())
        records.append(
            {
                "label": "RawNIND:CFA-channel",
                "weight_sha256": ref(rawnind / "utnet2-bayer.pt")["sha256"],
                "gain": "per-channel observed-CFA least-squares, input-only",
                "compute_precision": "float32",
                "device": "cpu",
            }
        )
        before.append(model_hash(models[-1]))
    crops, scores = [], []
    with torch.inference_mode():
        for item in plan["observations"]:
            with np.load(item["arrays"]["path"], allow_pickle=False) as archive:
                batch = {k: torch.from_numpy(archive[k].copy()) for k in archive.files}
            assert tensor_hash(batch) == item["tensor_sha256"]
            condition, case = item["condition"], item["case"]
            roi = case["center_ROI_xywh"]
            noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
            for model, record in zip(models, records, strict=True):
                if hasattr(model, "set_noise"):
                    model.set_noise(condition["shot"], condition["read"])
                prediction = model(
                    *(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix"))
                )
                assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
                assert tensor_hash(batch) == item["tensor_sha256"]
                metrics = quality_metrics(
                    prediction[..., 8:-8, 8:-8],
                    batch["target"][..., 8:-8, 8:-8],
                    batch["wb"],
                    batch["matrix"],
                )
                values = {
                    k: float(v[0]) if math.isfinite(float(v[0])) else None
                    for k, v in metrics.items()
                }
                scores.append(
                    {
                        "source_id": case["source"]["id"],
                        "model": record["label"],
                        "condition": condition["name"],
                        "pattern": item["pattern"],
                        "metrics": values,
                    }
                )
                panels = [
                    (
                        name,
                        display_crop(
                            rgb,
                            batch["wb"],
                            batch["matrix"],
                            roi,
                            exposure=selection["display_exposure"],
                        ),
                    )
                    for name, rgb in [
                        ("Noisy (Malvar)", noisy),
                        ("Denoised", prediction),
                        ("GT (synthetic)", batch["target"]),
                    ]
                ]
                crops.append(
                    save_triplet(
                        output,
                        f"{case['source']['id']}:{condition['name']}:{record['label']}",
                        panels,
                        caption=f"{case['detail']} / {condition['name']} / {record['label']}",
                        metadata={
                            "source_id": case["source"]["id"],
                            "source": case["source"],
                            "validation_index": case["index"],
                            "validation_seed": selection["dataset_seed"],
                            "evaluation_tile_xywh": roi,
                            "source_cache_context_xywh": case["cache_xywh"],
                            "condition": condition,
                            "pattern": item["pattern"],
                            "model": record,
                            "display_exposure": selection["display_exposure"],
                            "reference": "Exact synthetic clean target",
                            "observation": item["arrays"],
                            "detail": case["detail"],
                            "selection": selection["selection"],
                        },
                    )
                )
    assert all(model_hash(m) == digest for m, digest in zip(models, before, strict=True))
    assert not torch.cuda.is_initialized()
    guard(plan)
    save(
        output / "report.json",
        {
            "status": "completed-fixed-heldout-detail-awaiting-native-viewing",
            "plan": ref(plan_path),
            "driver": ref(__file__),
            "models": records,
            "per_case_scores": scores,
            "native_crops": crops,
            "model_weights_and_cached_inputs_unchanged": True,
            "scope": "Supplementary four-source/RGGB/three-condition material diagnosis with cached shared CPU observations. Not the full photographic/camera benchmark; no model-selection threshold. All crops native160, exact synthetic GT, fixed shared display and source coordinates.",
        },
    )
    print(ref(output / "report.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--checkpoint", type=Path, nargs="+")
    parser.add_argument("--labels", nargs="+")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rawnind", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.selection, args.path))
    else:
        run(args.path.resolve(), args.checkpoint, args.labels, args.output, rawnind=args.rawnind)
