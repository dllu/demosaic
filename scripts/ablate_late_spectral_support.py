"""Post-hoc raw-endpoint diagnostic: remove local support, keep frequency gains."""

import argparse
import os
import shutil
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save


def prepare(root):
    training = read(root / "plan-v1.json")
    guard(training)
    assert (
        read(root / "postprocess-status-v1.json")["status"]
        == "completed-audited-arrays-awaiting-human-native-viewing"
    )
    assert read(root / "native-viewing-v1.json")["figures_represented"] == 50
    point = root / "support-ablation-v1"
    point.mkdir(exist_ok=False)
    runner = point / "operator-v1.py"
    shutil.copyfile(__file__, runner)
    collection = read(root / "review-result-v1.json")["collections"]["raw-step1000"]
    export = read(collection["path"])["export"]
    save(
        point / "plan-v1.json",
        {
            "root": str(root),
            "runner": ref(runner),
            "training_plan": ref(root / "plan-v1.json"),
            "design": ref(root / "quality-design-v1.json"),
            "collection": collection,
            "export": export,
            "new_component_forwards": 766,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Post-hoc diagnostic of final raw endpoint on all766 existing cases. Replace only local support with1 after the original forward. Learned frequency gains/weights unchanged. Not a selected checkpoint, fresh validation or new trained model. Compare learned-path replay with its archived prediction; preserve exact same parent and RAW. No target/reference in forward.",
        },
    )


def worker(root):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.cfa import malvar
    from demosaic.late_spectral_detail import LateSpectralDetail
    from demosaic.prediction_archive import fingerprint

    point = root / "support-ablation-v1"
    path = point / "plan-v1.json"
    plan = read(path)
    assert ref(__file__) == plan["runner"]
    for key in ("training_plan", "design", "collection", "export"):
        assert ref(plan[key]["path"]) == plan[key]
    training = read(plan["training_plan"]["path"])
    guard(training)
    assert (
        Path(LateSpectralDetail.forward.__code__.co_filename)
        .resolve()
        .is_relative_to(Path(training["work"]) / "src")
    )
    (point / "worker.claim").open("x").close()
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
    state = torch.load(plan["export"]["path"], map_location="cpu", weights_only=True)
    assert (
        state["endpoint"] == "model"
        and state["step"] == 1000
        and state["parent"] == training["parent"]
    )
    before_cpu, before_cuda = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    module = LateSpectralDetail(**state["module_config"]).cuda().eval()
    module.load_state_dict(state["state_dict"], strict=True)
    before = model_hash(module)
    archived = read(plan["collection"]["path"])
    assert archived["module_before"] == before
    by_id = {o["id"]: o for o in archived["observations"]}
    counts = [0]
    module.register_forward_hook(lambda *args: counts.__setitem__(0, counts[0] + 1))
    outputs = []
    predictions = point / "predictions"
    predictions.mkdir(exist_ok=False)
    for index, case in enumerate(read(plan["design"]["path"])["observations"]):
        assert (
            psutil.virtual_memory().available > 32 * 2**30
            and shutil.disk_usage(root).free > 96 * 2**30
        )
        assert (
            ref(case["arrays"]["path"]) == case["arrays"]
            and ref(case["parent"]["path"]) == case["parent"]
        )
        arrays = dict(np.load(case["arrays"]["path"]))
        base = torch.from_numpy(np.load(case["parent"]["path"])).cuda()
        batch = {
            k: torch.from_numpy(arrays[k]).cuda() for k in ("packed", "variance", "colors", "wb")
        }
        with torch.inference_mode():
            control, aux = module(base, **batch, return_aux=True)
            proposal = module.synthesis(aux["spectral_delta"], aux["geometry"])
            full = (base + malvar(proposal, batch["colors"], batch["wb"])).cpu().numpy()
        assert full.dtype == np.float32 and np.isfinite(full).all()
        old = by_id[case["id"]]["prediction"]
        assert ref(old["path"]) == old
        cached = np.load(old["path"])
        control = control.cpu().numpy()
        difference = float(np.max(np.abs(control.astype(np.float64) - cached.astype(np.float64))))
        assert difference <= 1e-7, (case["id"], difference)
        dest = predictions / f"prediction-{index:03d}.npy"
        np.save(dest, full)
        outputs.append(
            {
                "id": case["id"],
                "prediction": ref(dest),
                "values": fingerprint(full),
                "archived_control": old,
                "control_bit_exact": bool(np.array_equal(control, cached)),
                "control_maximum_difference_DN16": difference * 65535,
                "learned_support_mean": float(aux["support"].mean()),
                "module_forwards": 1,
            }
        )
        if index % 64 == 0:
            print("full-support cases", index + 1, flush=True)
        del arrays, base, batch, aux, proposal, full, control, cached
    assert counts[0] == 766 and model_hash(module) == before
    assert torch.equal(before_cpu, torch.get_rng_state()) and torch.equal(
        before_cuda, torch.cuda.get_rng_state()
    )
    guard(training)
    save(
        point / "collection-v1.json",
        {
            "status": "completed-posthoc-local-support-ablation",
            "plan": ref(path),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "observations": outputs,
            "new_component_forwards": counts[0],
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "module_before": before,
            "module_after": model_hash(module),
            "RNG_unchanged": True,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": plan["scope"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else worker)(args.root.resolve())
