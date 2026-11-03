"""Review both fixed late-spectral endpoints using archived parent predictions."""

import argparse
import os
import shutil
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save


def prepare(root):
    training = read(root / "plan-v1.json")
    guard(training)
    target = root / "review-source-v1.py"
    assert not target.exists()
    shutil.copyfile(__file__, target)
    save(
        root / "review-plan-v1.json",
        {
            "training_plan": ref(root / "plan-v1.json"),
            "design": ref(root / "quality-design-v1.json"),
            "runner": ref(target),
            "scope": "Both raw/EMA step1000; 766 exact cached observations each. Only the new component executes; cached V143/DINO output adopted with its hash. No noise draws or target in forward.",
        },
    )


def worker(root):
    import json

    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_spectral_detail import LateSpectralDetail
    from demosaic.prediction_archive import fingerprint

    plan_path = root / "review-plan-v1.json"
    plan = read(plan_path)
    assert ref(__file__) == plan["runner"]
    assert ref(plan["training_plan"]["path"]) == plan["training_plan"]
    training = read(plan["training_plan"]["path"])
    guard(training)
    assert (
        Path(LateSpectralDetail.forward.__code__.co_filename)
        .resolve()
        .is_relative_to(Path(training["work"]) / "src")
    )
    assert ref(plan["design"]["path"]) == plan["design"]
    design = read(plan["design"]["path"])
    assert read(root / "status-v1.json")["status"] == "completed-training-awaiting-quality-review"
    result = read(root / "train-result-v1.json")
    assert result["steps"] == 1000 and result["initial_output_exact_parent"]
    assert result["parent_model_before"] == result["parent_model_after"]
    assert result["DINO_before"] == result["DINO_after"]
    assert result["counts"] == {
        "parent_root": 990,
        "DINO": 990,
        "module_training": 1000,
        "optimizer_updates": 1000,
        "adopted_parent_batches": 10,
    }
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000 and state["parent"] == training["parent"]
    assert len(state["optimizer"]["state"]) == 12
    assert all(float(v["step"]) == 1000 for v in state["optimizer"]["state"].values())
    assert len(state["model"]) == len(state["ema"]) == 12
    assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in state[key].values())
    (root / "review.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[2:4])
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
    before_cpu, before_cuda = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    collections = {}
    total = 0
    for label, key in (("raw-step1000", "model"), ("EMA-step1000", "ema")):
        point = root / "review-v1" / label
        point.mkdir(parents=True, exist_ok=False)
        module = LateSpectralDetail(**state["module_config"]).cuda().eval()
        module.load_state_dict(state[key], strict=True)
        initial = model_hash(module)
        exported = point / "module.pt"
        with exported.open("xb") as stream:
            torch.save(
                {
                    "component": "LateSpectralDetail",
                    "module_config": state["module_config"],
                    "state_dict": state[key],
                    "parent": state["parent"],
                    "training_checkpoint": result["checkpoint"],
                    "endpoint": key,
                    "step": 1000,
                },
                stream,
            )
        export = ref(exported)
        count = [0]
        module.register_forward_hook(lambda *args, count=count: count.__setitem__(0, count[0] + 1))
        observations = []
        for index, case in enumerate(design["observations"]):
            assert psutil.virtual_memory().available > 32 * 2**30
            assert shutil.disk_usage(root).free > 96 * 2**30
            assert ref(case["arrays"]["path"]) == case["arrays"]
            assert ref(case["parent"]["path"]) == case["parent"]
            arrays = dict(np.load(case["arrays"]["path"]))
            base = np.load(case["parent"]["path"])
            assert base.dtype == np.float32 and np.isfinite(base).all()
            batch = {
                k: torch.from_numpy(arrays[k]).cuda()
                for k in ("packed", "variance", "colors", "wb")
            }
            with torch.inference_mode():
                value, aux = module(torch.from_numpy(base).cuda(), **batch, return_aux=True)
            value = value.cpu().numpy()
            assert (
                value.shape == base.shape and value.dtype == np.float32 and np.isfinite(value).all()
            )
            dest = point / f"prediction-{index:03d}.npy"
            assert not dest.exists()
            np.save(dest, value)
            observations.append(
                {
                    "id": case["id"],
                    "prediction": ref(dest),
                    "values": fingerprint(value),
                    "parent": case["parent"],
                    "inputs": {k: fingerprint(arrays[k]) for k in batch},
                    "gain_abs_mean": float(aux["gain"].abs().mean()),
                    "support_mean": float(aux["support"].mean()),
                    "module_forwards": 1,
                }
            )
            total += 1
            if index % 64 == 0:
                print(
                    json.dumps(
                        {"endpoint": label, "done": index + 1, "total_module_forwards": total}
                    ),
                    flush=True,
                )
            del batch, value, aux, arrays, base
        assert count[0] == 766 and model_hash(module) == initial
        assert torch.equal(before_cpu, torch.get_rng_state()) and torch.equal(
            before_cuda, torch.cuda.get_rng_state()
        )
        path = point / "collection-v1.json"
        save(
            path,
            {
                "status": "completed-fixed-endpoint",
                "plan": ref(plan_path),
                "endpoint": label,
                "export": export,
                "module_before": initial,
                "module_after": model_hash(module),
                "observations": observations,
                "module_forwards": count[0],
                "new_parent_or_DINO_forwards": 0,
                "new_noise_draws": 0,
                "RNG_unchanged": True,
            },
        )
        collections[label] = ref(path)
        del module
    assert total == design["module_forwards"] == 1532
    guard(training)
    save(
        root / "review-result-v1.json",
        {
            "status": "completed-both-fixed-endpoints-awaiting-array-audit-and-native-viewing",
            "plan": ref(plan_path),
            "collections": collections,
            "module_forwards": total,
            "new_parent_or_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else worker)(args.root.resolve())
