"""Collect six fixed raw/EMA endpoints from the delivered-objective trial."""

import argparse
import os
import shutil
from pathlib import Path

import psutil
from train_delivered_objective_trial import classes
from train_directional_bank_trial import guard, read, ref, save


def prepare(root, revision=1):
    plan = read(root / "plan-v1.json")
    guard(plan)
    target = root / f"review-source-v{revision}.py"
    assert not target.exists()
    shutil.copyfile(__file__, target)
    save(
        root / f"review-plan-v{revision}.json",
        {
            "training_plan": ref(root / "plan-v1.json"),
            "design": ref(root / "quality-design-v1.json"),
            "runner": ref(target),
            "scope": "Six fixed raw/EMA step1000 endpoints on822 cases:retained798 plus24 ADC controls. Adopt exact cached parent arrays. No source/target/reference in forward except original RAW conditions and supplied parent. No fresh noise,parent or DINO calls during endpoint review.",
        },
    )


def worker(root, revision=1, validate_only=False):
    import json

    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    path = root / f"review-plan-v{revision}.json"
    review_plan = read(path)
    assert ref(__file__) == review_plan["runner"]
    assert ref(review_plan["training_plan"]["path"]) == review_plan["training_plan"]
    training = read(review_plan["training_plan"]["path"])
    guard(training)
    assert ref(review_plan["design"]["path"]) == review_plan["design"]
    design = read(review_plan["design"]["path"])
    assert (
        read(root / "status-v1.json")["status"]
        == "completed-matched-training-awaiting-fixed-quality-review"
    )
    result = read(root / "train-result-v1.json")
    assert result["steps"] == 1000 and result["initial_outputs_exact_parent"]
    assert (
        result["counts"]
        == result["updates"]
        == {"pre-control": 1000, "delivered-mosaic": 1000, "delivered-RGB": 1000}
    )
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000 and state["parent"] == training["parent"]
    assert (
        set(state["models"])
        == set(state["emas"])
        == set(state["arms"])
        == {"pre-control", "delivered-mosaic", "delivered-RGB"}
    )
    for arm in state["arms"]:
        assert (
            len(state["optimizers"][arm]["state"])
            == len(state["models"][arm])
            == len(state["emas"][arm])
            == state["arms"][arm]["parameter_tensors"]
        )
        assert all(float(v["step"]) == 1000 for v in state["optimizers"][arm]["state"].values())
        assert all(
            torch.isfinite(v).all() for key in ("models", "emas") for v in state[key][arm].values()
        )
    cache = read(training["cache"]["path"])
    assert cache["all1000_input_target_fingerprints_exact_V147"]
    assert (
        cache["parent_before"] == cache["parent_after"]
        and cache["DINO_before"] == cache["DINO_after"]
    )
    if validate_only:
        for arm in state["arms"]:
            module = classes()[arm](**state["module_config"])
            module.load_state_dict(state["models"][arm], strict=True)
            assert sum(p.numel() for p in module.parameters()) == state["arms"][arm]["parameters"]
        assert not torch.cuda.is_initialized()
        save(
            root / f"review-checkpoint-readiness-v{revision}.json",
            {
                "status": "pass-actual-final-checkpoint-before-review-claim",
                "review_plan": ref(path),
                "checkpoint": result["checkpoint"],
                "parameter_tensors_per_arm": {
                    arm: len(state["models"][arm]) for arm in state["arms"]
                },
                "new_neural_forwards": 0,
                "CUDA_initialized": False,
                "scope": "Validates all actual final model/EMA/Adam tensor counts and strict CPU model loading before any endpoint claim or CUDA setup.",
            },
        )
        return
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
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    collections = {}
    total = 0
    for arm in state["arms"]:
        for endpoint, key in (("raw", "models"), ("EMA", "emas")):
            label = f"{arm}-{endpoint}-step1000"
            point = root / "review-v1" / label
            point.mkdir(parents=True, exist_ok=False)
            module = classes()[arm](**state["module_config"]).cuda().eval()
            assert (
                Path(module.forward.__code__.co_filename)
                .resolve()
                .is_relative_to(Path(training["work"]) / "src")
            )
            module.load_state_dict(state[key][arm], strict=True)
            assert sum(p.numel() for p in module.parameters()) == state["arms"][arm]["parameters"]
            initial = model_hash(module)
            dest = point / "module.pt"
            with dest.open("xb") as stream:
                torch.save(
                    {
                        "component": state["arms"][arm]["class"],
                        "module_config": state["module_config"],
                        "state_dict": state[key][arm],
                        "parent": state["parent"],
                        "paired_training_checkpoint": result["checkpoint"],
                        "arm": arm,
                        "endpoint": endpoint,
                        "step": 1000,
                    },
                    stream,
                )
            count = [0]
            module.register_forward_hook(
                lambda *args, count=count: count.__setitem__(0, count[0] + 1)
            )
            observations = []
            for index, case in enumerate(design["observations"]):
                assert (
                    psutil.virtual_memory().available > 32 * 2**30
                    and shutil.disk_usage(root).free > 96 * 2**30
                    and shutil.disk_usage("/mnt/external").free > 208 * 2**30
                )
                assert (
                    ref(case["arrays"]["path"]) == case["arrays"]
                    and ref(case["parent"]["path"]) == case["parent"]
                )
                arrays = dict(np.load(case["arrays"]["path"]))
                base = np.load(case["parent"]["path"])
                batch = {
                    k: torch.from_numpy(arrays[k]).cuda()
                    for k in ("packed", "variance", "colors", "wb")
                }
                with torch.inference_mode():
                    output, aux = module(torch.from_numpy(base).cuda(), **batch, return_aux=True)
                value = output.cpu().numpy()
                assert (
                    value.dtype == np.float32
                    and value.shape == base.shape
                    and np.isfinite(value).all()
                )
                dest = point / f"prediction-{index:03d}.npy"
                np.save(dest, value)
                observations.append(
                    {
                        "id": case["id"],
                        "prediction": ref(dest),
                        "values": fingerprint(value),
                        "parent": case["parent"],
                        "inputs": {k: fingerprint(arrays[k]) for k in batch},
                        "support_mean": float(aux["support"].mean()),
                        "coefficient_correction_RMS": float(
                            aux["spectral_delta"].abs().square().mean().sqrt()
                        ),
                        "module_forwards": 1,
                    }
                )
                total += 1
                if index % 64 == 0:
                    print(
                        json.dumps(
                            {
                                "endpoint": label,
                                "done": index + 1,
                                "total_component_forwards": total,
                            }
                        ),
                        flush=True,
                    )
                del batch, output, aux, value, arrays, base
            assert count[0] == 822 and model_hash(module) == initial
            assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
                cuda_rng, torch.cuda.get_rng_state()
            )
            dest = point / "collection-v1.json"
            save(
                dest,
                {
                    "status": "completed-fixed-paired-endpoint",
                    "plan": ref(path),
                    "arm": arm,
                    "endpoint": endpoint,
                    "export": ref(point / "module.pt"),
                    "module_before": initial,
                    "module_after": model_hash(module),
                    "observations": observations,
                    "component_forwards": count[0],
                    "new_parent_DINO_forwards": 0,
                    "new_noise_draws": 0,
                    "RNG_unchanged": True,
                },
            )
            collections[label] = ref(dest)
            del module
    assert total == design["new_component_forwards"] == 4932
    guard(training)
    save(
        root / "review-result-v1.json",
        {
            "status": "completed-six-fixed-endpoints-awaiting-audit-native-viewing",
            "plan": ref(path),
            "collections": collections,
            "component_forwards": total,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "validate", "worker"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--revision", type=int, default=1)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root.resolve(), args.revision)
    else:
        worker(args.root.resolve(), args.revision, validate_only=args.mode == "validate")
