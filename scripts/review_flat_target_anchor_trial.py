"""Four fixed V162 endpoints with exact V161 harmonic control and durable journals."""

import argparse
import json
import os
import shutil
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_flat_target_anchor_trial import classes


def equal_tree(first, second):
    import torch

    if isinstance(first, torch.Tensor):
        return isinstance(second, torch.Tensor) and torch.equal(first.cpu(), second.cpu())
    if isinstance(first, dict):
        return first.keys() == second.keys() and all(
            equal_tree(v, second[k]) for k, v in first.items()
        )
    if isinstance(first, (list, tuple)):
        return (
            type(first) is type(second)
            and len(first) == len(second)
            and all(equal_tree(a, b) for a, b in zip(first, second, strict=True))
        )
    return first == second


def validate(root):
    import torch

    plan = read(root / "plan-v1.json")
    guard(plan)
    assert (
        read(root / "status-v1.json")["status"]
        == "completed-matched-training-awaiting-fixed-quality-review"
    )
    result = read(root / "train-result-v1.json")
    assert result["counts"] == result["updates"] == {"harmonic-control": 1000, "flat-anchor": 1000}
    assert result["steps"] == 1000 and result["initial_outputs_exact_parent"]
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000 and state["parent"] == plan["parent"]
    assert (
        set(state["arms"])
        == set(state["models"])
        == set(state["emas"])
        == {"harmonic-control", "flat-anchor"}
    )
    for arm in state["arms"]:
        assert (
            len(state["models"][arm])
            == len(state["emas"][arm])
            == len(state["optimizers"][arm]["state"])
            == state["arms"][arm]["parameter_tensors"]
        )
        assert all(float(v["step"]) == 1000 for v in state["optimizers"][arm]["state"].values())
        assert all(
            torch.isfinite(v).all() for key in ["models", "emas"] for v in state[key][arm].values()
        )
        assert all(
            torch.isfinite(v).all()
            for s in state["optimizers"][arm]["state"].values()
            for v in s.values()
        )
        for key in ["models", "emas"]:
            model = classes()[arm](**state["module_config"])
            model.load_state_dict(state[key][arm], strict=True)
            assert sum(p.numel() for p in model.parameters()) == state["arms"][arm]["parameters"]
    previous = read(plan["baseline_training"]["path"])
    assert ref(previous["checkpoint"]["path"]) == previous["checkpoint"]
    old = torch.load(previous["checkpoint"]["path"], map_location="cpu", weights_only=True)
    for key in ["models", "emas", "optimizers"]:
        assert equal_tree(state[key]["harmonic-control"], old[key]["harmonic-context"]), key
    assert len(result["trace"]) == len(previous["trace"]) == 1000
    for row, prior in zip(result["trace"], previous["trace"], strict=True):
        assert (
            row["step"] == prior["step"]
            and row["batch"] == prior["batch"]
            and row["domain"] == prior["domain"]
        )
        expected = prior["arms"]["harmonic-context"]
        assert {k: row["arms"]["harmonic-control"][k] for k in expected} == expected

    smoke = read(root / "smoke-result-v1.json")
    assert smoke["exact_V161_control_trace_rows"] == 10
    assert result["trace"][:10] == smoke["trace"]
    assert result["supervised_batches"] == {"harmonic-control": 900, "flat-anchor": 900}
    assert result["zero_ADC_gradient_batches"] == {"harmonic-control": 100, "flat-anchor": 100}
    assert not torch.cuda.is_initialized()
    save(
        root / "review-checkpoint-readiness-v1.json",
        {
            "status": "pass-actual-final-state-and-exact-control-before-review-claim",
            "checkpoint": result["checkpoint"],
            "baseline_checkpoint": previous["checkpoint"],
            "finite_Adam_states_at1000": sum(
                v["parameter_tensors"] for v in state["arms"].values()
            ),
            "strict_raw_EMA_loads": 4,
            "exact_control_trace_rows": 1000,
            "control_raw_EMA_Adam_exact": True,
            "new_neural_forwards": 0,
            "CUDA_initialized": False,
            "validator": ref(__file__),
        },
    )


def collect(root):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    plan = read(root / "plan-v1.json")
    guard(plan)
    ready = read(root / "review-checkpoint-readiness-v1.json")
    assert ready["status"] == "pass-actual-final-state-and-exact-control-before-review-claim"
    result = read(root / "train-result-v1.json")
    assert ready["checkpoint"] == result["checkpoint"] == ref(result["checkpoint"]["path"])
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    design = read(root / "quality-design-v1.json")
    assert len(design["observations"]) == 822 and design["new_component_forwards"] == 3288
    assert not (root / "review.claim").exists()
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
    total = controls_exact = saved_predictions = 0
    for arm in state["arms"]:
        for endpoint, key in [("raw", "models"), ("EMA", "emas")]:
            label = f"{arm}-{endpoint}-step1000"
            point = Path(plan["quality_output_roots"][label]) / label
            point.mkdir(parents=True, exist_ok=False)
            module = classes()[arm](**state["module_config"]).cuda().eval()
            assert Path(module.forward.__code__.co_filename).is_relative_to(
                Path(plan["work"]) / "src"
            )
            module.load_state_dict(state[key][arm], strict=True)
            before = model_hash(module)
            exported = point / "module.pt"
            with exported.open("xb") as stream:
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
            old_collection = (
                read(plan["control_collections"][label]["path"])
                if arm == "harmonic-control"
                else None
            )
            old = (
                {r["id"]: r["prediction"] for r in old_collection["observations"]}
                if old_collection
                else {}
            )
            if old_collection:
                assert before == old_collection["module_before"] == old_collection["module_after"]
            count = [0]
            module.register_forward_hook(
                lambda *args, count=count: count.__setitem__(0, count[0] + 1)
            )
            rows = []
            observation_stream = (point / "observations-v1.jsonl").open("x")
            forward_stream = (point / "forward-events-v1.jsonl").open("x")
            for index, case in enumerate(design["observations"]):
                assert psutil.virtual_memory().available > 32 * 2**30
                assert (
                    shutil.disk_usage(root).free > 60 * 2**30
                    and shutil.disk_usage("/mnt/external").free > 152 * 2**30
                )
                assert (
                    ref(case["arrays"]["path"]) == case["arrays"]
                    and ref(case["parent"]["path"]) == case["parent"]
                )
                arrays = dict(np.load(case["arrays"]["path"]))
                base = np.load(case["parent"]["path"])
                batch = {
                    k: torch.from_numpy(arrays[k]).cuda()
                    for k in ["packed", "variance", "colors", "wb"]
                }
                with torch.inference_mode():
                    output, aux = module(torch.from_numpy(base).cuda(), **batch, return_aux=True)
                value = output.cpu().numpy()
                assert (
                    value.dtype == np.float32
                    and value.shape == base.shape
                    and np.isfinite(value).all()
                )
                forward_stream.write(
                    json.dumps({"index": index, "id": case["id"], "returned_forwards": count[0]})
                    + "\n"
                )
                forward_stream.flush()
                if old_collection:
                    prediction = old[case["id"]]
                    assert ref(prediction["path"]) == prediction
                    archived_value = np.load(prediction["path"])
                    np.testing.assert_array_equal(value, archived_value)
                    assert fingerprint(value) == fingerprint(archived_value)
                    del archived_value
                    controls_exact += 1
                else:
                    path = point / f"prediction-{index:03d}.npy"
                    assert not path.exists()
                    np.save(path, value, allow_pickle=False)
                    prediction = ref(path)
                    saved_predictions += 1
                rows.append(
                    {
                        "id": case["id"],
                        "prediction": prediction,
                        "values": fingerprint(value),
                        "parent": case["parent"],
                        "inputs": {k: fingerprint(arrays[k]) for k in batch},
                        "support_mean": float(aux["support"].mean()),
                        "coefficient_correction_RMS": float(
                            aux["spectral_delta"].abs().square().mean().sqrt()
                        ),
                        "module_forwards": 1,
                        **(
                            {
                                "spatial_correction_RMS_DN16": float(
                                    aux["spatial_correction"].square().mean().sqrt()
                                )
                                * 65535
                            }
                            if "spatial_correction" in aux
                            else {}
                        ),
                        "archive_replayed_bit_exact": bool(old_collection),
                    }
                )
                observation_stream.write(json.dumps(rows[-1], allow_nan=False) + "\n")
                observation_stream.flush()
                total += 1
                if index % 64 == 0:
                    print(
                        json.dumps(
                            {"endpoint": label, "done": index + 1, "current_head_calls": total}
                        ),
                        flush=True,
                    )
                del batch, arrays, base, output, aux, value
            observation_stream.close()
            forward_stream.close()
            assert count[0] == 822 and before == model_hash(module)
            assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
                cuda_rng, torch.cuda.get_rng_state()
            )
            path = point / "collection-v1.json"
            save(
                path,
                {
                    "status": "completed-fixed-endpoint",
                    "arm": arm,
                    "endpoint": endpoint,
                    "export": ref(exported),
                    "module_before": before,
                    "module_after": model_hash(module),
                    "observations": rows,
                    "component_forwards": count[0],
                    "RNG_unchanged": True,
                    "observation_journal": ref(point / "observations-v1.jsonl"),
                    "forward_journal": ref(point / "forward-events-v1.jsonl"),
                    "new_parent_DINO_forwards": 0,
                    "new_noise_draws": 0,
                    "adopted_array_storage_after_actual_replay": bool(old_collection),
                    "original_control_collection": plan["control_collections"].get(label),
                },
            )
            collections[label] = ref(path)
            del module
    assert total == 3288 and controls_exact == saved_predictions == 1644
    guard(plan)
    save(
        root / "review-result-v1.json",
        {
            "status": "completed-four-fixed-endpoints-awaiting-independent-quality-and-native-viewing",
            "plan": ref(root / "plan-v1.json"),
            "collections": collections,
            "component_forwards": total,
            "control_replayed_exact": controls_exact,
            "new_prediction_arrays": saved_predictions,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    (validate if args.validate_only else collect)(args.root.absolute())
