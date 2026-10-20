"""Rank training-only Commons sources with V43 for targeted visual curation."""

import argparse
import copy
import hashlib
import heapq
import json
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
MANIFEST = Path("/mnt/external/demosaic/commons-post4557-reviewed-20261020-v1/manifest4.jsonl")
CHECKPOINT = REPO / ".cache/benchmarks/mature-hidden-FP16-full-quality-v1/work/checkpoints/V43.pt"


def prepare(root):
    import yaml

    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for folder in ("src/demosaic", "scripts"):
        for source in (REPO / folder).glob("*.py"):
            target = work / folder / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    protocol = yaml.safe_load((REPO / "configs/evaluation.yaml").read_text())
    rows = [json.loads(line) for line in MANIFEST.read_text().splitlines()]
    counts = {s: sum(r["split"] == s for r in rows) for s in ("train", "val", "test")}
    assert counts == {"train": 88508, "val": 2303, "test": 2255}
    source = work / "manifest4.jsonl"
    shutil.copyfile(MANIFEST, source)
    plan = {
        "root": str(root),
        "work": str(work),
        "python": str(REPO / ".venv/bin/python3"),
        "HF_HOME": str(REPO / ".cache/huggingface"),
        "manifest": ref(source),
        "source_manifest": ref(MANIFEST),
        "checkpoint": ref(CHECKPOINT),
        "counts": counts,
        "size": 256,
        "batch_size": 8,
        "workers": 2,
        "conditions": [
            c for c in protocol["conditions"] if c["name"] in ("adc-only", "iso12800-prior")
        ],
        "wb": protocol["white_balance"],
        "matrix": protocol["camera_to_srgb"],
        "seed": protocol["seed"],
        "inputs": [ref(CHECKPOINT), ref(MANIFEST)],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "worker": ref(work / "scripts/score_commons_quality.py"),
        "scope": "Training-source difficulty/IQA screening only. Fixed center4x-cache crop followed by area2; no geometry or PSF augmentation. Original V43 FP32, RGGB, ADC/highest-noise; score each source once per condition using its original reconstruction objective. No holdout/GFX inputs, model training, automatic exclusions, model comparison or speed experiment. High loss is a review cue, not a bad-photo label. Declared whole-cache hashes are retained; actual loaded crops/observations are hashed, without claiming a fresh whole-cache audit of all88508 files.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def per_image_losses(prediction, batch):
    """Original reference-white Charbonnier objective, with per-image reduction."""
    import torch
    from torch.nn import functional as F

    from demosaic.cfa import mosaic
    from demosaic.color import render

    def penalty(error):
        return (error.square() + 1e-6).sqrt().flatten(1).mean(1)

    target = batch["target"]
    display = render(prediction, batch["wb"], batch["matrix"], fp32=True)
    truth = render(target, batch["wb"], batch["matrix"], fp32=True)
    linear = penalty(prediction - target)
    rendered = penalty(display - truth)
    gradient = (
        sum(penalty(torch.diff(display, dim=d) - torch.diff(truth, dim=d)) for d in (-1, -2)) / 2
    )
    boundary = F.max_pool2d((truth.amax(1, keepdim=True) > 0.98).float(), 7, 1, 3)
    chroma = (display - display.mean(1, keepdim=True)) - (truth - truth.mean(1, keepdim=True))
    highlight = (chroma.abs() * boundary).flatten(1).sum(1) / (
        boundary.flatten(1).sum(1) * 3
    ).clamp_min(1)
    sensor = penalty(mosaic(prediction - target, batch["colors"]))
    mse = (display - truth).square().flatten(1).mean(1)
    return {
        "loss": linear + 0.5 * rendered + 0.1 * gradient + 0.1 * highlight + 0.1 * sensor,
        "linear": linear,
        "rendered": rendered,
        "gradient": gradient,
        "highlight": highlight,
        "sensor": sensor,
        "linear_MSE": (prediction - target).square().flatten(1).mean(1),
        "srgb_MSE": mse,
        "srgb_PSNR": -10 * mse.clamp_min(1e-12).log10(),
    }


def worker(plan_path, cpu=False):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash
    from torch.nn import functional as F
    from torch.utils.data import DataLoader, Dataset

    from demosaic.inference import load_checkpoint
    from demosaic.precision import amp_context
    from demosaic.suite import observation
    from demosaic.train import batch_fingerprint

    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["worker"]
    if cpu:
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    device = torch.device("cpu" if cpu else "cuda")
    torch.set_num_threads(2 if cpu else 4)
    rows = [
        r
        for r in (
            json.loads(line) for line in Path(plan["manifest"]["path"]).read_text().splitlines()
        )
        if r["split"] == "train"
    ]
    if cpu:
        rows = rows[:4]
    size = 64 if cpu else plan["size"]

    class Sources(Dataset):
        def __len__(self):
            return len(rows)

        def __getitem__(self, index):
            row = rows[index]
            array = np.load(row["cache"], mmap_mode="r", allow_pickle=False)
            assert array.dtype == np.uint16 and list(array.shape) == row["shape"]
            assert row["bin_factor"] == 4 and row["color_space"] == "linear-sRGB"
            h, w = array.shape[:2]
            assert min(h, w) >= size * 2
            y, x = (h - size * 2) // 2, (w - size * 2) // 2
            crop = array[y : y + size * 2, x : x + size * 2].copy()
            rgb = F.avg_pool2d(
                torch.from_numpy(crop.astype(np.float32)).permute(2, 0, 1) / 65535, 2
            )
            luma = rgb.mean(0)
            gradient = (
                (luma[1:] - luma[:-1]).square().mean()
                + (luma[:, 1:] - luma[:, :-1]).square().mean()
            ) / 2
            laplacian = (
                4 * luma[1:-1, 1:-1]
                - luma[2:, 1:-1]
                - luma[:-2, 1:-1]
                - luma[1:-1, 2:]
                - luma[1:-1, :-2]
            )
            return {
                "rgb": rgb,
                "index": index,
                "roi": torch.tensor([x, y, size * 2, size * 2]),
                "crop_sha256": hashlib.sha256(crop.tobytes()).hexdigest(),
                "contrast": float(luma.std()),
                "gradient_RMS": float(gradient.sqrt()),
                "laplacian_RMS": float(laplacian.square().mean().sqrt()),
                "bright_fraction": float((rgb.amax(0) >= 0.999).float().mean()),
            }

    # Fork workers before CUDA/model loading: sources only read CPU arrays.
    loader = DataLoader(
        Sources(),
        batch_size=2 if cpu else plan["batch_size"],
        num_workers=0 if cpu else plan["workers"],
        generator=torch.Generator().manual_seed(plan["seed"]),
        **({"multiprocessing_context": "fork"} if not cpu else {}),
    )
    batches = iter(loader)
    if not cpu:
        assert not torch.cuda.is_initialized()
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            min(
                16 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
                torch.cuda.get_per_process_memory_fraction(device),
            ),
            device,
        )
    output = Path(plan["work"]) / ("CPU-source-proof" if cpu else "source-scores")
    output.mkdir(parents=True, exist_ok=False)
    model, state = load_checkpoint(plan["checkpoint"]["path"], device)
    assert state["loaded_sha256"] == plan["checkpoint"]["sha256"] and state["step"] == 2000
    del state
    model.eval()
    if not cpu:
        model.to(memory_format=torch.channels_last)
    before, dino = model_hash(model), model_hash(model.context.backbone)
    config, identities = copy.deepcopy(model.config.to_dict()), [id(p) for p in model.parameters()]
    cpu_rng, python_rng = torch.get_rng_state().clone(), random.getstate()
    cuda_rng = torch.cuda.get_rng_state_all() if not cpu else []
    calls, done, count = [], 0, 0
    hook = model.context.backbone.register_forward_hook(lambda *_: calls.append(1))
    tops = {c["name"]: [] for c in plan["conditions"]}
    proxies = {"low_gradient": [], "high_laplacian": [], "bright": []}

    def retain(heap, priority, index, row, limit):
        entry = (priority, index, row)
        if len(heap) < limit:
            heapq.heappush(heap, entry)
        elif entry[:2] > heap[0][:2]:
            heapq.heapreplace(heap, entry)

    with (output / "per-source.jsonl").open("x") as stream, torch.inference_mode():
        try:
            for data in batches:
                rgb = data["rgb"].to(device)
                indexes = data["index"].tolist()
                ids = [rows[i]["id"] for i in indexes]
                common = []
                for j, index in enumerate(indexes):
                    record = {
                        "id": ids[j],
                        "training_index": index,
                        "cache_sha256_declared": rows[index]["cache_sha256"],
                        "actual_bin4_crop_sha256": data["crop_sha256"][j],
                        "ROI_in_bin4_xywh": data["roi"][j].tolist(),
                        "contrast": float(data["contrast"][j]),
                        "gradient_RMS": float(data["gradient_RMS"][j]),
                        "laplacian_RMS": float(data["laplacian_RMS"][j]),
                        "bright_fraction": float(data["bright_fraction"][j]),
                    }
                    common.append(record)
                    if record["contrast"] > 0.025:
                        retain(proxies["low_gradient"], -record["gradient_RMS"], index, record, 64)
                        retain(
                            proxies["high_laplacian"],
                            record["laplacian_RMS"] / record["contrast"],
                            index,
                            record,
                            64,
                        )
                    retain(proxies["bright"], record["bright_fraction"], index, record, 32)
                for condition in plan["conditions"]:
                    host = observation(
                        rgb, ids, condition, "RGGB", plan["wb"], plan["matrix"], plan["seed"]
                    )
                    args = [host[k] for k in ("packed", "variance", "colors", "wb", "matrix")]
                    if not cpu:
                        args = [
                            a.contiguous(memory_format=torch.channels_last) if a.ndim == 4 else a
                            for a in args
                        ]
                    digest = batch_fingerprint(host)
                    model.set_noise(condition["shot"], condition["read"])
                    with amp_context(device, dtype="float32"):
                        prediction = model(*args)
                        assert (
                            prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
                        )
                        metrics = {
                            k: v.cpu().tolist()
                            for k, v in per_image_losses(prediction, host).items()
                        }
                    count += 1
                    assert batch_fingerprint(host) == digest
                    for j, record in enumerate(common):
                        record = {
                            **record,
                            "condition": condition,
                            "pattern": "RGGB",
                            "batch_measurement_and_target_sha256": digest,
                            "metrics": {k: v[j] for k, v in metrics.items()},
                        }
                        stream.write(json.dumps(record, allow_nan=False) + "\n")
                        retain(
                            tops[condition["name"]],
                            record["metrics"]["loss"],
                            indexes[j],
                            record,
                            128,
                        )
                    del host, prediction, args
                done += len(indexes)
                if done % 512 == 0 or done == len(rows):
                    stream.flush()
                    save(
                        output / "progress.json",
                        {
                            "sources_done": done,
                            "sources_total": len(rows),
                            "actual_forwards": count,
                            "owner": {
                                "pid": os.getpid(),
                                "created": psutil.Process().create_time(),
                            },
                        },
                    )
                    save(
                        output / "review-candidates.json",
                        {
                            "sources_scored": done,
                            "complete": done == len(rows),
                            "high_loss": {
                                k: [e[2] for e in sorted(v, reverse=True)] for k, v in tops.items()
                            },
                            "IQA_proxies_not_automatic_labels": {
                                k: [e[2] for e in sorted(v, reverse=True)]
                                for k, v in proxies.items()
                            },
                        },
                    )
                    print({"sources_done": done, "sources_total": len(rows)}, flush=True)
        finally:
            hook.remove()
    assert model_hash(model) == before and model_hash(model.context.backbone) == dino
    assert model.config.to_dict() == config and [id(p) for p in model.parameters()] == identities
    assert torch.equal(cpu_rng, torch.get_rng_state()) and random.getstate() == python_rng
    assert all(
        torch.equal(a, b)
        for a, b in zip(cuda_rng, torch.cuda.get_rng_state_all() if not cpu else [], strict=True)
    )
    assert done == len(rows) and len(calls) == count
    guard(plan)
    save(
        output / "receipt.json",
        {
            "status": "completed-source-difficulty-ranking-awaiting-visual-curation",
            "plan": ref(plan_path),
            "checkpoint": plan["checkpoint"],
            "model_sha256": before,
            "DINO_sha256": dino,
            "sources_scored": done,
            "cases": done * len(plan["conditions"]),
            "actual_forwards": count,
            "DINO_calls": len(calls),
            "state_config_parameters_RNG_inputs_preserved": True,
            "scores": ref(output / "per-source.jsonl"),
            "engineering_only": cpu,
            "CUDA_initialized": torch.cuda.is_initialized(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": plan["scope"],
        },
    )


def run(plan_path):
    from queue_tf32x3_cuda import stop_owned

    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": [],
    }
    child = None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "controller-status.json", state)

    def resources(gib):
        return (
            psutil.virtual_memory().available >= gib * 2**30
            and shutil.disk_usage(root).free >= 64 * 2**30
            and shutil.disk_usage("/mnt/external").free >= 500 * 2**30
        )

    try:
        for cpu in (True, False):
            name = "CPU" if cpu else "GPU"
            if not cpu:
                began, stable = time.monotonic(), None
                record("waiting-for-stable-source-screen-headroom")
                while True:
                    assert time.monotonic() - began < 3600
                    stable = (
                        (time.monotonic() if stable is None else stable) if resources(48) else None
                    )
                    if stable is not None and time.monotonic() - stable >= 60:
                        break
                    time.sleep(5)
            assert resources(48)
            guard(plan)
            env = dict(
                os.environ,
                CUDA_VISIBLE_DEVICES="" if cpu else "0",
                HF_HOME=plan["HF_HOME"],
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OMP_NUM_THREADS="2" if cpu else "4",
                OPENBLAS_NUM_THREADS="2",
                PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
            )
            with (root / (name + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [plan["python"], "-P", plan["worker"]["path"], "worker", str(plan_path)]
                    + (["--cpu"] if cpu else []),
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owned = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-source-screen-" + name, child=owned)
                deadline = time.monotonic() + (900 if cpu else 21600)
                while child.poll() is None:
                    if time.monotonic() > deadline or not resources(24):
                        raise RuntimeError("Owned source screen reached resource/runtime bound")
                    time.sleep(2)
                assert child.wait() == 0
            receipt = work / ("CPU-source-proof" if cpu else "source-scores") / "receipt.json"
            result = read(receipt)
            assert result["owner"] == owned and result["engineering_only"] == cpu
            if cpu:
                assert not result["CUDA_initialized"] and result["sources_scored"] == 4
            state["completed"].append(name)
            record("completed-source-screen-" + name, receipt=ref(receipt))
        record("completed-source-screen-awaiting-actual-visual-curation")
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned(child, state["child"])
        record("failed-source-screen-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker", "run"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.path)
    elif args.mode == "run":
        run(args.path.resolve())
    else:
        worker(args.path.resolve(), args.cpu)
