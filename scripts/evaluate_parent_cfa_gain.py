"""Paired full development-photo test with one mature-model forward per batch."""

import argparse
import copy
import hashlib
import json
import math
import os
import random
import time
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml
from probe_saved_cfa_gain_grid import channel_gain, read, ref

from demosaic.cfa import bilinear, malvar
from demosaic.data import CleanDataset, synthetic
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import amp_context
from demosaic.prior import wiener_packed
from demosaic.reporting import display_crop, save_triplet
from demosaic.suite import observation, summarize


def paired_predictions(model, batch, condition):
    """One shared FP32 forward; the correction never receives a target."""
    model.set_noise(condition["shot"], condition["read"])
    with amp_context(batch["packed"].device, dtype="float32"):
        original = model(*(batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"]))
    corrected, gains = channel_gain(original, batch["packed"], batch["colors"])
    return original, corrected, gains


def model_hash(model):
    result = hashlib.sha256()
    for name, value in model.state_dict().items():
        value = value.detach().cpu().contiguous()
        result.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        flat = value.reshape(-1).clone(memory_format=torch.contiguous_format)
        result.update(flat.view(torch.uint8).numpy().tobytes())
    return result.hexdigest()


@torch.inference_mode()
def main(plan_path):
    from audit_fresh_dino_statistics import audit_photo

    os.nice(5)
    torch.set_num_threads(4)
    plan = read(plan_path)
    root, output = Path(plan["root"]), Path(plan["output"])
    assert ref(__file__) == plan["worker"]
    for item in [*plan["source_files"], plan["checkpoint"], plan["manifest"], plan["protocol"]]:
        assert ref(item["path"]) == item
    assert psutil.virtual_memory().available > 32 * 2**30
    assert psutil.disk_usage(root).free > 128 * 2**30
    assert not torch.cuda.is_initialized() and torch.cuda.is_available()
    torch.cuda.set_per_process_memory_fraction(
        24 * 2**30 / torch.cuda.get_device_properties(0).total_memory, 0
    )
    torch.backends.cudnn.benchmark = False
    with (root / "claim").open("x") as stream:
        stream.write(str(os.getpid()))
    started = time.monotonic()
    status = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "sources_done": 0,
        "actual_network_forwards": 0,
    }

    def record(state, **values):
        status.update(status=state, updated_unix=time.time(), **values)
        temporary = root / "status.tmp"
        temporary.write_text(json.dumps(status, indent=2, allow_nan=False) + "\n")
        temporary.replace(root / "status.json")
        print(
            json.dumps(
                {k: status[k] for k in ["status", "sources_done", "actual_network_forwards"]}
            ),
            flush=True,
        )

    try:
        record("loading-genuine-parent-for-shared-forward-photo-comparison")
        output.mkdir(parents=True, exist_ok=False)
        protocol = yaml.safe_load(Path(plan["protocol"]["path"]).read_text())
        data = CleanDataset(plan["manifest"]["path"], split="val", patch_size=256, native_crop=True)
        assert len(data) == 427 and len(protocol["conditions"]) == 7
        assert protocol["patterns"] == ["RGGB", "BGGR", "GRBG", "GBRG"]
        model, state = load_checkpoint(plan["checkpoint"]["path"], "cuda")
        assert state["step"] == 20000
        assert state["model_config"]["dino_model"] == plan["dino_model"]
        original_record = {
            **plan["checkpoint"],
            "label": "V63-parent-fresh-FP32",
            "step": 20000,
            "model_config": state["model_config"],
            "compute_precision": "float32",
            "memory_format": "channels_last",
            "training_run": state["config"]["run"],
        }
        del state
        model.eval().to(memory_format=torch.channels_last)
        initial_model_hash = model_hash(model)
        corrected_record = {
            **copy.deepcopy(original_record),
            "label": "V63-input-CFA-channel-gain",
            "correction": plan["algorithm"],
            "fit": "all native256 pixels; input only",
        }
        models = [original_record, corrected_record]
        metadata = {
            "format_version": 1,
            "protocol": protocol,
            "models": models,
            "manifest": plan["manifest"]["path"],
            "manifest_sha256": plan["manifest"]["sha256"],
            "split": "val",
            "sources": 427,
            "synthetic_sources": 16,
            "patch_size": 256,
            "native_crop": True,
            "batch_size": 4,
            "adc_bits": 16,
            "adc_black": 0.03,
            "torch": str(torch.__version__),
            "execution_plan": ref(plan_path),
            "observation_and_metrics_precision": "IEEE FP32",
            "noise_pairing": "per-source/condition/CFA seed; identical observation for both outputs",
            "reference_target": "Existing exact simulated target and common clipping/rendering",
            "classical_baselines": [
                "Bilinear:IEEE-FP32",
                "Malvar2004:white-balanced:IEEE-FP32",
                "Wiener7+Malvar2004:white-balanced:IEEE-FP32",
            ],
        }
        (output / "protocol.json").write_text(json.dumps(metadata, indent=2) + "\n")
        entries = [("photo", row["id"], i) for i, row in enumerate(data.rows)] + [
            ("synthetic", f"synthetic-{i}", i) for i in range(16)
        ]
        rows, fits, crops = [], [], []
        border = protocol["border"]
        trim = (slice(None), slice(None), slice(border, -border), slice(border, -border))
        with (
            (output / "per-image.jsonl").open("w") as stream,
            (output / "input-only-fits.jsonl").open("w") as fit_stream,
        ):
            for first in range(0, len(entries), 4):
                assert time.monotonic() - started < 7200
                assert psutil.virtual_memory().available > 24 * 2**30
                current = entries[first : first + 4]
                rgb = torch.stack(
                    [
                        data[i]["rgb"]
                        if kind == "photo"
                        else synthetic(256, random.Random(1_000_000 + i))
                        for kind, _, i in current
                    ]
                ).cuda()
                ids = [identity for _, identity, _ in current]
                for condition in protocol["conditions"]:
                    for pattern in protocol["patterns"]:
                        batch = observation(
                            rgb,
                            ids,
                            condition,
                            pattern,
                            protocol["white_balance"],
                            protocol["camera_to_srgb"],
                            protocol["seed"],
                        )
                        for key in ["packed", "variance"]:
                            batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
                        original, corrected, gains = paired_predictions(model, batch, condition)
                        status["actual_network_forwards"] += 1
                        for prediction in [original, corrected]:
                            assert (
                                prediction.dtype == torch.float32
                                and torch.isfinite(prediction).all()
                            )
                        noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
                        predictions = [
                            (models[0]["label"], original),
                            (models[1]["label"], corrected),
                            ("Bilinear", bilinear(batch["packed"], batch["colors"])),
                            ("Malvar2004:WB", noisy),
                            (
                                "Wiener7+Malvar2004:WB",
                                malvar(
                                    wiener_packed(batch["packed"], batch["variance"]),
                                    batch["colors"],
                                    batch["wb"],
                                ),
                            ),
                        ]
                        for i, (kind, identity, _) in enumerate(current):
                            fit = {
                                "id": identity,
                                "kind": kind,
                                "condition": condition["name"],
                                "pattern": pattern,
                                "gains": gains[i].cpu().tolist(),
                            }
                            fit_stream.write(json.dumps(fit, allow_nan=False) + "\n")
                            fits.append(fit)
                        for label, prediction in predictions:
                            scores = quality_metrics(
                                prediction[trim],
                                batch["target"][trim],
                                batch["wb"],
                                batch["matrix"],
                            )
                            values = {k: v.cpu().tolist() for k, v in scores.items()}
                            for i, (kind, identity, source_index) in enumerate(current):
                                row = {
                                    "id": identity,
                                    "kind": kind,
                                    "condition": condition["name"],
                                    "pattern": pattern,
                                    "model": label,
                                    "metrics": {
                                        k: (v[i] if math.isfinite(v[i]) else None)
                                        for k, v in values.items()
                                    },
                                }
                                stream.write(json.dumps(row, allow_nan=False) + "\n")
                                rows.append(row)
                                if (
                                    first == 0
                                    and i < 2
                                    and label in [m["label"] for m in models]
                                    and condition["name"] == "iso12800-prior"
                                    and pattern == "RGGB"
                                ):
                                    record_model = copy.deepcopy(
                                        next(m for m in models if m["label"] == label)
                                    )
                                    record_model["gains"] = (
                                        gains[i].cpu().tolist()
                                        if label == models[1]["label"]
                                        else [1, 1, 1]
                                    )
                                    record_model["snapshot"] = str(plan_path)
                                    source = data.rows[source_index]
                                    cache = Path(plan["manifest"]["path"]).parent / source["cache"]
                                    shape = np.load(cache, mmap_mode="r").shape
                                    rng = random.Random(data.seed + source_index)
                                    rng.random()
                                    y, x = (
                                        rng.randrange(shape[0] - 255),
                                        rng.randrange(shape[1] - 255),
                                    )
                                    crop = save_triplet(
                                        output,
                                        f"{identity}:{label}",
                                        [
                                            (
                                                name,
                                                display_crop(
                                                    value[i : i + 1],
                                                    batch["wb"][i : i + 1],
                                                    batch["matrix"][i : i + 1],
                                                    [48, 48, 160, 160],
                                                ),
                                            )
                                            for name, value in [
                                                ("Noisy (Malvar)", noisy),
                                                ("Denoised", prediction),
                                                ("GT (synthetic)", batch["target"]),
                                            ]
                                        ],
                                        caption=f"{identity} / {condition['name']} / {label}",
                                        metadata={
                                            "source_id": identity,
                                            "source": source,
                                            "model": record_model,
                                            "checkpoint_sha256": plan["checkpoint"]["sha256"],
                                            "validation_index": source_index,
                                            "validation_seed": data.seed,
                                            "evaluation_tile_xywh": [48, 48, 160, 160],
                                            "cache_context_xywh": [x, y, 256, 256],
                                            "cache_display_ROI_xywh": [x + 48, y + 48, 160, 160],
                                            "cache": ref(cache),
                                            "condition": condition,
                                            "pattern": pattern,
                                            "white_balance": protocol["white_balance"],
                                            "camera_to_srgb": protocol["camera_to_srgb"],
                                            "display_exposure": 1.0,
                                            "reference": "Exact synthetic clean target",
                                        },
                                    )
                                    crops.append(crop)
                stream.flush()
                fit_stream.flush()
                record(
                    "running-full427-shared-forward-FP32-photo-test",
                    sources_done=first + len(current),
                    case_rows=len(rows),
                    native_triplets=len(crops),
                )
                if first == 0:
                    (output / "early-native.json").write_text(
                        json.dumps({"native_crops": crops}, indent=2) + "\n"
                    )
        assert len(rows) == 62020 and len(fits) == 12404 and len(crops) == 4
        assert status["actual_network_forwards"] == 3108 and model_hash(model) == initial_model_hash
        for item in plan["source_files"]:
            assert ref(item["path"]) == item
        result = {
            **metadata,
            **summarize(rows),
            "native_crops": crops,
            "actual_network_forwards": status["actual_network_forwards"],
            "input_only_fits": ref(output / "input-only-fits.jsonl"),
            "model_state_unchanged": True,
            "scope": plan["scope"],
        }
        (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        audit = audit_photo(output, expected_methods=5)
        (output / "independent-summary-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        record(
            "completed-shared-forward-photo-test-awaiting-native-camera-and-decision-review",
            result=ref(output / "summary.json"),
            audit=ref(output / "independent-summary-audit.json"),
        )
    except BaseException as error:
        record("failed-shared-forward-photo-test-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
