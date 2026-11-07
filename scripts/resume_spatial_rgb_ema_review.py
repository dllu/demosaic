"""Finish V157 EMA review after an explicit user pause and vanished process handles."""

import argparse
import os
import shutil
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_spatial_rgb_trial import classes


def collect(root):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    plan = read(root / "plan-v1.json")
    recovery = read(root / "review-recovery-plan-v2.json")
    guard(plan)
    guard(recovery)
    assert ref(__file__) == recovery["reviewer"]
    ready = read(root / "review-checkpoint-readiness-v1.json")
    training = read(root / "train-result-v1.json")
    assert ready["control_raw_EMA_Adam_exact"] and ready["finite_Adam_states_at1000"] == 58
    assert ready["checkpoint"] == training["checkpoint"] == ref(training["checkpoint"]["path"])
    assert not (root / "review-result-v1.json").exists()
    (root / "recovery-EMA-review.claim").open("x").close()
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
    assert psutil.virtual_memory().available > 52 * 2**30
    state = torch.load(training["checkpoint"]["path"], map_location="cpu", weights_only=True)
    design = read(root / "quality-design-v1.json")
    partial = read(recovery["partial_inventory"]["path"])
    assert len(partial["predictions"]) == 194
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    collections = dict(recovery["completed_collections"])
    assert len(collections) == 3
    calls = reused = saved = 0
    for endpoint, key in [("EMA", "emas")]:
        label = f"spatial-rgb-{endpoint}-step1000"
        point = Path(recovery["output_root"]) / label
        point.mkdir(parents=True, exist_ok=False)
        module = classes()["spatial-rgb"](**state["module_config"]).cuda().eval()
        module.load_state_dict(state[key]["spatial-rgb"], strict=True)
        before = model_hash(module)
        exported = point / "module.pt"
        assert ref(partial["export"]["path"]) == partial["export"]
        old = torch.load(partial["export"]["path"], map_location="cpu", weights_only=True)
        assert all(
            torch.equal(v.cpu(), old["state_dict"][k]) for k, v in module.state_dict().items()
        )
        shutil.copyfile(partial["export"]["path"], exported)
        count = [0]
        module.register_forward_hook(lambda *args, count=count: count.__setitem__(0, count[0] + 1))
        rows = []
        journal = point / "observations-v1.jsonl"
        with journal.open("x") as stream:
            for index, case in enumerate(design["observations"]):
                assert psutil.virtual_memory().available > 32 * 2**30
                assert shutil.disk_usage(root).free > 60 * 2**30
                assert shutil.disk_usage("/mnt/external").free > 196 * 2**30
                assert ref(case["arrays"]["path"]) == case["arrays"]
                assert ref(case["parent"]["path"]) == case["parent"]
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
                replay = index < 194
                if replay:
                    prediction = partial["predictions"][index]["prediction"]
                    assert partial["predictions"][index]["id"] == case["id"]
                    assert ref(prediction["path"]) == prediction
                    np.testing.assert_array_equal(value, np.load(prediction["path"]))
                    reused += 1
                else:
                    path = point / f"prediction-{index:03d}.npy"
                    assert not path.exists()
                    np.save(path, value, allow_pickle=False)
                    prediction = ref(path)
                    saved += 1
                row = {
                    "id": case["id"],
                    "prediction": prediction,
                    "values": fingerprint(value),
                    "parent": case["parent"],
                    "inputs": {k: fingerprint(arrays[k]) for k in batch},
                    "support_mean": float(aux["support"].mean()),
                    "coefficient_correction_RMS": float(
                        aux["spectral_delta"].abs().square().mean().sqrt()
                    ),
                    "spatial_correction_RMS_DN16": float(
                        aux["spatial_correction"].square().mean().sqrt()
                    )
                    * 65535,
                    "module_forwards": 1,
                    "archive_replayed_bit_exact": False,
                    "partial_prediction_replayed_bit_exact": replay,
                }
                rows.append(row)
                import json

                stream.write(json.dumps(row, allow_nan=False) + "\n")
                stream.flush()
                calls += 1
                if index % 64 == 0:
                    print(
                        json.dumps(
                            {"endpoint": label, "done": index + 1, "recovery_head_calls": calls}
                        ),
                        flush=True,
                    )
                del arrays, base, batch, output, aux, value
        assert count[0] == 822 and before == model_hash(module)
        assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
            cuda_rng, torch.cuda.get_rng_state()
        )
        path = point / "collection-v1.json"
        save(
            path,
            {
                "status": "completed-fixed-endpoint-after-exact-partial-replay",
                "arm": "spatial-rgb",
                "endpoint": endpoint,
                "export": ref(exported),
                "module_before": before,
                "module_after": model_hash(module),
                "observations": rows,
                "component_forwards": 822,
                "RNG_unchanged": True,
                "new_parent_DINO_forwards": 0,
                "new_noise_draws": 0,
                "adopted_array_storage_after_actual_replay": True,
                "original_partial_inventory": recovery["partial_inventory"],
                "observation_journal": ref(journal),
            },
        )
        collections[label] = ref(path)
        del module
    assert calls == 822 and reused == 194 and saved == 628
    guard(plan)
    guard(recovery)
    save(
        root / "review-result-v1.json",
        {
            "status": "completed-four-fixed-endpoints-after-storage-guard-and-exact-partial-replay",
            "plan": ref(root / "postprocess-plan-v3.json"),
            "collections": collections,
            "component_forwards": 3288,
            "actual_component_forwards_including_preserved_partial": 4036,
            "preserved_initial_review_calls": 2198,
            "first_recovery_component_forwards": 1016,
            "post_pause_component_forwards": calls,
            "recovery_component_forwards": 1016 + calls,
            "MSE_control_replayed_exact": 1644,
            "new_prediction_arrays": 1644,
            "partial_prediction_replays_exact": 554 + reused,
            "EMA_partial_prediction_replays_exact": reused,
            "newly_written_arrays_in_recovery": saved,
            "retained_unique_arrays_from_prior_stages": 1016,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "recovery_plan": ref(root / "review-recovery-plan-v2.json"),
            "scope": "3288 selected evaluations plus554 original raw and194 pre-pause EMA partial evaluations=4036 actual review calls. Original controls and completed raw collection reused;194 EMA partial outputs replayed bit-exact,628 remaining arrays external. Explicit user pause preserved;old handles verified absent before recovery. No training restart,source/noise/parent changes or old evidence deletion.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    collect(parser.parse_args().root.absolute())
