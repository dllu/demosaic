"""Replay completed fresh S/B arms on the fixed, already-cached CPU inputs.

Compute only the new arm: reuse noisy/reference/previous no-context pixels and
the two serialized CPU synthetic observations. No GPU or source RAW decoding.
This is a small qualitative development check, not the full matched suite.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from demosaic.cfa import color_indices
from demosaic.inference import load_checkpoint
from demosaic.model import ModelConfig
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read_panels(root, crop):
    path = root / crop["image"]
    assert sha(path) == crop["png_sha256"]
    with Image.open(path) as image:
        assert image.mode == "RGB" and image.size == (512, 192)
        values = np.asarray(image)
        return [
            values[y : y + h, x : x + w].copy()
            for x, y, w, h in [p["png_xywh"] for p in crop["panels"]]
        ]


def array(root, record):
    path = root / record["image"]
    assert sha(path) == record["sha256"]
    values = np.load(path, allow_pickle=False)
    assert values.dtype == np.float32 and list(values.shape) == record["shape"]
    assert np.isfinite(values).all()
    return torch.from_numpy(values)


@torch.inference_mode()
def main(checkpoint, output):
    torch.set_num_threads(4)
    assert not torch.cuda.is_initialized()
    base_dir = Path("/mnt/external/demosaic/evaluation/gfx-3879-3880-v43-none10k-cpu-contexts-v1")
    base_path = base_dir / "report.json"
    base = json.loads(base_path.read_text())
    assert base["runtime"]["device"] == "cpu" and base["runtime"]["neural_precision"] == "float32"
    assert base["runtime"]["cuda_initialized"] is False and not base["full_frames"]
    baseline = base["models"][1]
    assert baseline["sha256"] == "0df4ff404c38b8f4b42f6451486e91c97631544b1c817c126f371195942f3af4"
    assert sha(baseline["snapshot"]) == baseline["sha256"]
    previous = torch.load(baseline["snapshot"], map_location="cpu", weights_only=True)
    incoming = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert previous["step"] == incoming["step"] == 10000
    assert previous["config"]["source_sha256"] == incoming["config"]["source_sha256"]
    assert (
        incoming["config"]["source_sha256"]
        == "2f1a2251d8141d335e99266343b46b61b8da3cb13012fc63d79ea5c3968ad01c"
    )
    assert not previous["model_config"]["dino"] and incoming["model_config"]["dino"]
    keys = [
        "seed",
        "batch_size",
        "lr",
        "steps",
        "warmup_steps",
        "manifest_sha256",
        "paired_manifest_sha256",
        "raw_clean_manifest_sha256",
        "validation_manifest_sha256",
        "paired_fraction",
        "raw_clean_fraction",
        "augmentation_downsample",
        "raw_clean_augmentation_downsample",
        "precision",
        "data_seed_per_step",
        "noise_free_fraction",
        "synthetic_fraction",
        "flat_fraction",
        "broad_camera",
        "reconstruct_highlights",
        "preserve_negative_read_noise",
        "channels_last",
        "normalized_sensor_weight",
        "multiscale_sensor_weight",
        "phase_lr_multiplier",
        "ema_decay",
    ]
    for key in keys:
        assert previous["config"].get(key) == incoming["config"].get(key), key
    common_model = ModelConfig.from_checkpoint(previous["model_config"]).to_dict()
    candidate_model = ModelConfig.from_checkpoint(incoming["model_config"]).to_dict()
    for key in common_model:
        if key not in ("dino", "dino_model", "dino_revision"):
            assert common_model[key] == candidate_model[key], key
    prior = "479abe3c5327dfd10ff54a80ec7d4098ca80752a5c9492cdff31cee430bec4b4"
    for state in [previous, incoming]:
        assert state["config"]["initialized_from"]["prior"]["weights_sha256"] == prior
    for source in Path("src/demosaic").glob("*.py"):
        assert source.read_bytes() == (base_dir / "source" / source.name).read_bytes(), source
    assert incoming["config"]["seed"] == 48 and incoming["config"]["steps"] == 10000
    assert (
        previous["model_config"]["rgb_middle_skip_fp32"]
        and incoming["model_config"]["rgb_middle_skip_fp32"]
    )
    assert {float(v["step"]) for v in incoming["optimizer"]["state"].values() if "step" in v} == {
        10000.0
    }
    assert all(v["lr"] == 1e-5 for v in incoming["optimizer"]["param_groups"])
    runs = [Path(state["config"]["run"]) for state in [previous, incoming]]
    observations = []
    for run in runs:
        rows = [json.loads(x) for x in (run / "metrics.jsonl").read_text().splitlines()]
        observations.append(
            [(x["step"], x["domain"], x["batch_sha256"]) for x in rows if x.get("event") == "train"]
        )
    assert observations[0] == observations[1] and len(observations[0]) == 403
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "source"
    archive.mkdir()
    for source in [*Path("src/demosaic").glob("*.py"), Path(__file__)]:
        (archive / source.name).write_bytes(source.read_bytes())
    frozen, digest = freeze_checkpoint(checkpoint, output / "weights")
    model, state = load_checkpoint(frozen, "cpu")
    label = f"{Path(state['config']['run']).name}:step10000"
    record = {
        "label": label,
        "sha256": digest,
        "snapshot": str(frozen),
        "device": "cpu",
        "precision": "float32",
        "model_config": model.config.to_dict(),
    }
    del previous, incoming, state
    model.eval().to(memory_format=torch.channels_last)
    colors = color_indices(base["sources"][0]["metadata"]["pattern"])
    meta = base["sources"][0]["metadata"]
    wb = torch.tensor(meta["white_balance"])[None]
    matrix = torch.tensor(meta["camera_to_srgb"])[None]
    model.set_noise(base["conditioning"]["shot"], base["conditioning"]["read"])
    crops, direct, floats = [], [], []
    for region in base["selection"]["regions"]:
        name = region["name"]
        parent = next(
            c
            for c in base["native_crops"]
            if c["region"]["name"] == name and c["model_label"] == baseline["label"]
        )
        original = read_panels(base_dir, parent)
        packed = array(
            base_dir,
            next(
                x
                for x in base["float_contexts"]
                if x["role"] == "noisy-packed" and x["region"]["name"] == name
            ),
        ).contiguous(memory_format=torch.channels_last)
        variance = packed.clamp_min(0) * base["conditioning"]["shot"] + base["conditioning"]["read"]
        with amp_context("cpu", dtype="float32"):
            prediction = model(packed, variance, colors, wb, matrix)
        assert prediction.shape == (1, 3, 512, 512) and torch.isfinite(prediction).all()
        target = output / f"{name}-rgb-f32.npy"
        np.save(target, prediction.numpy(), allow_pickle=False)
        floats.append(
            {
                "image": target.name,
                "sha256": sha(target),
                "shape": [1, 3, 512, 512],
                "dtype": "float32",
                "region": region,
                "model": record,
            }
        )
        tx, ty, _, _ = parent["context_xywh"]
        roi = [region["noisy_xy"][0] - tx, region["noisy_xy"][1] - ty, 160, 160]
        display = display_crop(prediction, wb, matrix, roi, exposure=4.0)
        info = {
            "region": region,
            "context_xywh": parent["context_xywh"],
            "model": record,
            "conditioning": base["conditioning"],
            "display_exposure": 4.0,
            "shared_wb": meta["white_balance"],
            "shared_matrix": meta["camera_to_srgb"],
            "base_report": str(base_path),
            "base_report_sha256": sha(base_path),
            "reference": "Independent ISO100 f/5.6 AHD reference, not exact GT; no quality score",
        }
        crop = save_triplet(
            output,
            name + label,
            [
                ("Noisy (Malvar)", original[0].astype(np.float32) / 255),
                ("DINO / CPU FP32", display),
                ("ISO100 ref (not GT)", original[2].astype(np.float32) / 255),
            ],
            caption=f"{name} / {label} / CPU FP32 / approximate ISO100 reference",
            metadata=info,
        )
        stored = read_panels(output, crop)
        assert np.array_equal(stored[0], original[0]) and np.array_equal(stored[2], original[2])
        crops.append(crop)
        direct.append(
            save_triplet(
                output,
                name + label + "direct",
                [
                    ("Noisy (Malvar)", original[0].astype(np.float32) / 255),
                    ("No context / 10k", original[1].astype(np.float32) / 255),
                    ("DINO / 10k", stored[1].astype(np.float32) / 255),
                ],
                caption=f"{name} / matched fresh none versus DINO / both10000 / CPU FP32",
                metadata={
                    **info,
                    "baseline": baseline,
                    "reference": "Two learned methods; neither panel is GT.",
                },
            )
        )
        print(json.dumps({"event": "gfx-context", "region": name, "model": label}), flush=True)
    model.to(memory_format=torch.contiguous_format)
    synthetic_receipt = Path("docs/results/cross-camera-none10k-cpu-review.json")
    synthetic = json.loads(synthetic_receipt.read_text())["exact_gt_examples"]
    exact = []
    model.set_noise(0.00256, 0.0000262144)
    for observation in synthetic["observations"]:
        path = Path(observation["arrays"])
        assert sha(path) == observation["arrays_sha256"]
        with np.load(path, allow_pickle=False) as data:
            batch = {k: torch.from_numpy(data[k].copy()) for k in data.files}
        with amp_context("cpu", dtype="float32"):
            prediction = model(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        parent = next(
            c
            for c in synthetic["native_crops"]
            if c["source_id"] == observation["source_id"]
            and c["model"].get("sha256") == baseline["sha256"]
        )
        panels = read_panels(Path(synthetic["execution_summary"]).parent, parent)
        display = display_crop(prediction, batch["wb"], batch["matrix"], [48, 48, 160, 160])
        crop = save_triplet(
            output,
            observation["source_id"] + label,
            [
                ("Noisy (Malvar)", panels[0].astype(np.float32) / 255),
                ("DINO / CPU FP32", display),
                ("GT (synthetic)", panels[2].astype(np.float32) / 255),
            ],
            caption=f"{observation['source_id']} / {label} / exact simulated GT / CPU FP32",
            metadata={
                "source_id": observation["source_id"],
                "source": parent["source"],
                "model": record,
                "observation": observation,
                "conditioning": {"shot": 0.00256, "read": 0.0000262144},
                "display_exposure": 1.0,
                "reference": "Exact simulated clean target; two illustrative cases, not full427 evaluation.",
            },
        )
        stored = read_panels(output, crop)
        assert np.array_equal(stored[0], panels[0]) and np.array_equal(stored[2], panels[2])
        exact.append(crop)
    assert not torch.cuda.is_initialized()
    result = {
        "status": "completed-matched-fresh-dino-cpu-qualitative-replay",
        "model": record,
        "baseline": baseline,
        "common_training_fields_verified": keys,
        "shared_logged_training_observations": 403,
        "base_report": {"path": str(base_path), "sha256": sha(base_path)},
        "native_crops": crops,
        "direct_learned_comparisons": direct,
        "exact_gt_examples": exact,
        "float_contexts": floats,
        "runtime": {
            "device": "cpu",
            "precision": "float32",
            "torch": str(torch.__version__),
            "cuda_initialized": False,
        },
        "source_files": {p.name: sha(p) for p in archive.glob("*.py")},
        "limitations": "Four512 GFX contexts and two fixed synthetic observations. Not full-frame or full-suite quality. One training seed; context adds trainable projection capacity and separate nondeterministic CUDA training. B/final GPU review remain.",
    }
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"status": result["status"], "output": str(output), "checkpoint_sha256": digest}
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.checkpoint, args.output)
