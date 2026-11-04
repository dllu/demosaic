"""Compare two fresh parent evaluations under one uniform deterministic policy."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path("/home/dllu/proj/demosaic")


def resources(root, launch=False):
    assert psutil.virtual_memory().available > (52 if launch else 32) * 2**30
    assert shutil.disk_usage(root).free > 96 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 208 * 2**30


def prepare(root):
    import numpy as np

    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    resources(REPO, launch=True)
    previous = REPO / ".cache/quality-20261103/V154-robust-spectral-v1"
    design = previous / "quality-design-v1.json"
    cases = read(design)["observations"]
    assert len(cases) == 822 and len({c["id"] for c in cases}) == 822
    expected_bytes = sum(np.load(c["parent"]["path"], mmap_mode="r").nbytes + 128 for c in cases)
    assert shutil.disk_usage("/mnt/external").free > 210 * 2**30 + expected_bytes
    assert shutil.disk_usage(REPO).free > 98 * 2**30 + expected_bytes
    external = Path("/mnt/external/demosaic/quality-20261103") / root.name
    assert not external.exists()
    root.mkdir()
    external.mkdir()
    work = root / "work"
    for source in list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / "scripts" / name
        for name in [
            Path(__file__).name,
            "train_directional_bank_trial.py",
            "profile_raw_kernel_inference.py",
        ]
    ]:
        dest = work / source.relative_to(REPO)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    assert len(list((work / "src/demosaic").glob("*.py"))) == 86
    for case in cases:
        for key in ["arrays", "parent"]:
            p = Path(case[key]["path"])
            assert p.is_relative_to(REPO) or p.is_relative_to(Path("/mnt/external"))
            assert ref(p) == case[key]
    models = {
        "V143": {
            "path": "/mnt/external/demosaic/models/v143-final5000.pt",
            "sha256": "96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4",
        },
        "V120": {
            "path": "/mnt/external/demosaic/models/v120-final20000.pt",
            "sha256": "a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb",
        },
    }
    assert all(ref(item["path"]) == item for item in models.values())
    plan = {
        "root": str(root),
        "work": str(work),
        "external": str(external),
        "design": ref(design),
        "models": models,
        "expected_DINO_sha256": "691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14",
        "expected_prediction_bytes": expected_bytes,
        "cases": 822,
        "inputs": [ref(design)] + list(models.values()),
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "No training. Fresh V143 and V120 evaluations onall822 identical immutable cached RAW inputs under one deterministic FP32/channels-last/no-AMP/no-TF32 policy. Old V143 collection used cuDNN benchmarkTrue; v1 exact-replay assumption failed by0.001709DN16 and is preserved. Neither parent output is adopted from that archive. V143 outputs local,V120 external,2.211GiB each with96/208GiB runtime reserves.1644 new parent/DINO calls,zero noise draws/RAW decodes/original lookup/dataz. Targets/reference never enter forward. Both real scenes retained and never scored as exactGT. Same adaptive cohort,not blind validation.",
    }
    save(root / "plan-v1.json", plan)
    guard(plan)
    print(
        json.dumps({"prepared": str(root), "cases": 822, "external_GiB": expected_bytes / 2**30}),
        flush=True,
    )


def worker(root, phase):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.prediction_archive import fingerprint

    plan = read(root / "plan-v1.json")
    guard(plan)
    assert Path(__file__).is_relative_to(Path(plan["work"]))
    assert Path(load_checkpoint.__code__.co_filename).is_relative_to(Path(plan["work"]))
    (root / (phase + ".claim")).open("x").close()
    resources(root, launch=True)
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.set_per_process_memory_fraction(
        12 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    assert phase in ["V143", "V120"]
    label = phase
    binding = plan["models"][label]
    with torch.random.fork_rng(devices=[0]):
        model, state = load_checkpoint(binding["path"], "cuda")
    assert state["loaded_sha256"] == binding["sha256"]
    del state
    model.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before = model_hash(model)
    backbone = model_hash(model.context.backbone)
    assert backbone == plan["expected_DINO_sha256"]
    CPU_RNG = torch.get_rng_state().clone()
    CUDA_RNG = torch.cuda.get_rng_state().clone()
    counts = {"parent": 0, "DINO": 0}
    model.register_forward_hook(lambda *args: counts.__setitem__("parent", counts["parent"] + 1))
    model.context.backbone.register_forward_hook(
        lambda *args: counts.__setitem__("DINO", counts["DINO"] + 1)
    )
    cases = read(plan["design"]["path"])["observations"]
    destination = (root if label == "V143" else Path(plan["external"])) / label
    destination.mkdir(exist_ok=False)
    save(
        root / (phase + "-loaded-v1.json"),
        {
            "model": binding,
            "model_hash": before,
            "DINO_hash": backbone,
            "counts": counts,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "precision": "IEEE-FP32",
            "channels_last": True,
            "cudnn_benchmark": False,
            "deterministic": True,
        },
    )
    rows = []
    started = time.time()
    with (root / (phase + "-trace-v1.jsonl")).open("x") as trace:
        for i, case in enumerate(cases):
            resources(root)
            assert ref(case["arrays"]["path"]) == case["arrays"]
            arrays = dict(np.load(case["arrays"]["path"]))
            args = [
                torch.from_numpy(arrays[k]).cuda()
                for k in ["packed", "variance", "colors", "wb", "matrix"]
            ]
            model.set_noise(case["noise"]["shot"], case["noise"]["read"])
            with torch.inference_mode():
                value = model(*args).cpu().numpy()
            assert value.dtype == np.float32 and np.isfinite(value).all()
            row = {
                "id": case["id"],
                "arrays": case["arrays"],
                "noise": case["noise"],
                "inputs": {
                    k: fingerprint(arrays[k])
                    for k in ["packed", "variance", "colors", "wb", "matrix"]
                },
                "output": fingerprint(value),
                "counts": dict(counts),
            }
            assert value.shape == np.load(case["parent"]["path"], mmap_mode="r").shape
            path = destination / f"prediction-{i:03d}.npy"
            assert not path.exists()
            np.save(path, value, allow_pickle=False)
            row["prediction"] = ref(path)
            row["archived_V143"] = case["parent"]
            if phase == "V143":
                old = np.load(case["parent"]["path"]).astype(np.float64)
                delta = value.astype(np.float64) - old
                row["archived_V143_bit_exact"] = bool(np.array_equal(value, old))
                row["archived_V143_maximum_difference_DN16"] = float(np.max(np.abs(delta)) * 65535)
                row["archived_V143_difference_RMS_DN16"] = float(np.sqrt(np.mean(delta**2)) * 65535)
            trace.write(json.dumps(row) + "\n")
            trace.flush()
            rows.append(row)
            if i % 32 == 0 or i + 1 == len(cases):
                print(
                    json.dumps(
                        {
                            "phase": phase,
                            "done": i + 1,
                            "total": len(cases),
                            "counts": counts,
                            "elapsed_seconds": time.time() - started,
                        }
                    ),
                    flush=True,
                )
            del args, arrays, value
    after = model_hash(model)
    assert after == before and model_hash(model.context.backbone) == backbone
    assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
        CUDA_RNG, torch.cuda.get_rng_state()
    )
    assert counts == {"parent": len(cases), "DINO": len(cases)}
    guard(plan)
    save(
        root / (phase + "-result-v1.json"),
        {
            "status": "completed-all822-fresh-parents-awaiting-quality-audit-and-native-viewing",
            "plan": ref(root / "plan-v1.json"),
            "model": binding,
            "model_before": before,
            "model_after": after,
            "DINO_before": backbone,
            "DINO_after": backbone,
            "RNG_unchanged": True,
            "counts": counts,
            "observations": rows,
            "trace": ref(root / (phase + "-trace-v1.jsonl")),
            "new_noise_draws": 0,
            "new_training_updates": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "elapsed_seconds": time.time() - started,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": plan["scope"],
        },
    )


def controller(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    assert Path(__file__).is_relative_to(Path(plan["work"]))
    (root / "controller.claim").open("x").close()
    status = {
        "status": "running-fresh-V143-then-fresh-V120",
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    save(root / "status-v1.json", status)
    for phase in ["V143", "V120"]:
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            str(Path(plan["work"]) / "src") + ":" + str(Path(plan["work"]) / "scripts")
        )
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        with (root / (phase + "-log-v1.txt")).open("x") as log:
            child = subprocess.Popen(
                [str(REPO / ".venv/bin/python"), str(Path(__file__)), str(root), "--phase", phase],
                cwd=REPO,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            status.update(phase=phase, child_owner=owner)
            save(root / "status-v1.json", status)
            code = child.wait()
        status["completed"][phase] = {"owner": owner, "returncode": code}
        if code:
            status["status"] = "failed-" + phase + "-preserve-receipts-no-restart"
            save(root / "status-v1.json", status)
            raise RuntimeError(status["status"])
        assert (root / (phase + "-result-v1.json")).exists()
    status["status"] = "completed-parent-arrays-awaiting-quality-audit-and-native-viewing"
    save(root / "status-v1.json", status)
    print(status["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--phase", choices=["prepare", "controller", "V143", "V120"], required=True)
    args = parser.parse_args()
    root = args.root.absolute()
    if args.phase == "prepare":
        prepare(root)
    elif args.phase == "controller":
        controller(root)
    else:
        worker(root, args.phase)
