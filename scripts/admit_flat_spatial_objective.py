"""Two real warm-start updates test the new loss; no architecture is changed."""

import argparse
import gc
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V181-flat-spatial-admission-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V181-flat-spatial-admission-v1")
BASE = ROOT.parent / "V180-local-phase-trial-v1"


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def guard(plan):
    assert ref(__file__) == plan["runner"]
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def completed_base():
    source = BASE / "publication-work-v1/scripts/publish_local_phase_evidence_trial.py"
    assert ref(source) == read(BASE / "publication-source-v1.json")["publisher"]
    env = dict(
        os.environ,
        CUDA_VISIBLE_DEVICES="",
        OPENBLAS_NUM_THREADS="1",
        PYTHONPATH=":".join(
            str(BASE / name)
            for name in [
                "publication-work-v1/scripts",
                "reduction-work-v1/scripts",
                "audit-work-v1/scripts",
                "work/src",
                "work/scripts",
            ]
        ),
    )
    code = "import sys;import publish_local_phase_evidence_trial as p;p.completed_context(p.ROOT,viewed=True);assert 'torch' not in sys.modules"
    check = subprocess.run(
        [str(REPO / ".venv/bin/python"), "-c", code],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode:
        raise RuntimeError("Frozen completed-local dependency check failed: " + check.stderr)
    index = REPO / "docs/results/v180-local-phase-evidence-final-v1.json"
    verification = REPO / "docs/results/v180-local-phase-evidence-publication-verification-v1.json"
    assert read(verification)["publication"] == ref(index)
    return {"publication": ref(index), "verification": ref(verification), "gate": ref(source)}


def prepare():
    dependency = completed_base()
    assert not ROOT.exists() and not EXTERNAL.exists()
    baseline = read(BASE / "plan-v1.json")
    assert len(list((REPO / "src/demosaic").glob("*.py"))) == 98
    for path, digest in baseline["frozen_files"].items():
        if "/src/demosaic/" in path:
            assert ref(REPO / "src/demosaic" / Path(path).name)["sha256"] == digest
    tests = REPO / ".cache/v181-flat-spatial-CPU-tests-v2.log"
    assert "55 passed" in tests.read_text()
    assert psutil.virtual_memory().available > 52 * 2**30
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.2) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 0.15) * 2**30
    ROOT.mkdir()
    EXTERNAL.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    test = work / "tests/test_flat_spatial_objective.py"
    test.parent.mkdir()
    shutil.copyfile(REPO / "tests/test_flat_spatial_objective.py", test)
    admission = read(ROOT.parent / "V180-local-phase-admission-v1/plan-v1.json")
    plan = {
        "status": "prepared-loss-only-two-update-probe-not-quality",
        "created_unix_UTC": time.time(),
        "runner": ref(work / "scripts" / Path(__file__).name),
        "work": str(work),
        "root": str(ROOT),
        "external": str(EXTERNAL),
        "baseline": ref(BASE / "plan-v1.json"),
        "completed_dependency": dependency,
        "initial_checkpoint": baseline["initial_checkpoint"],
        "module_config": baseline["module_config"],
        "frozen_component": baseline["frozen_component"],
        "sampling_library": baseline["sampling_library"],
        "pair_units": baseline["pair_units"],
        "domain_weights": baseline["domain_weights"],
        "cases": [
            next(c for c in admission["cases"] if c["domain"] == d) for d in ["mesh", "mixed"]
        ],
        "loss": {
            "window": 17,
            "unit_DN16": 4,
            "weight": 0.25,
            "target_mask": "unchanged17px/1DN16range",
        },
        "CPU_GPU_tolerance": {"rtol": 1e-5, "atol": 1e-7},
        "CPU_tests": dict(ref(tests), text=tests.read_text()),
        "preserved_first_test": {
            "source": ref(REPO / ".cache/v181-flat-spatial-first-tests-v1.py"),
            "log": ref(REPO / ".cache/v181-flat-spatial-CPU-tests-v1.log"),
            "correction": "24passed/1failed:pytest attempted NumPy conversion of requires-grad tensor. Scalar .item comparison fixed; loss implementation/tolerances unchanged.",
        },
        "scope": "Loss-only implementation probe on unchanged admitted V180 architecture/98neuralfiles. Two real native4image updates,mesh then mixed,from V172 real141Adam900 plus zero local adapter/noAdam. Genuine checkpoint/Adam/EMA/CPU-CUDA RNG restoration between. Compare new native loss and output gradients with CPU;check independent FP32 total. No protected optimizer use,quality claim,new source/noise,parent/DINO or RAWdecode. Probe checkpoints are not training initializers.",
    }
    plan["inputs"] = [
        plan[k] for k in ["baseline", "initial_checkpoint", "sampling_library", "pair_units"]
    ]
    plan["inputs"] += list(dependency.values())
    for case in plan["cases"]:
        plan["inputs"] += [case["arrays"], case["parent"]]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "plan-v1.json", plan)
    print("Prepared unchanged98neuralfiles/newloss/2nativeupdates;zeroTorch/forward")


def probe():
    plan = read(ROOT / "plan-v1.json")
    completed_base()
    guard(plan)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        if (ROOT / "admission-launch-v1.json").exists() and read(ROOT / "admission-launch-v1.json")[
            "owner"
        ] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing actual launch identity; no Torch import")
    (ROOT / "admission.claim").open("x").close()
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    records = []
    try:
        import numpy as np
        import torch
        from audit_phase_evidence_trial import loss_from_terms
        from flat_spatial_objective import flat_spatial_error_loss, objective
        from phase_evidence_training_state import (
            adam_clocks,
            restore_matching_state,
            update_matching_ema,
            warm_start_matching,
        )
        from profile_raw_kernel_inference import model_hash
        from train_local_phase_evidence_trial import factory
        from train_phase_evidence_trial import instrument

        assert not torch.cuda.is_initialized()
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.set_float32_matmul_precision("highest")
        torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.cuda.set_per_process_memory_fraction(
            24 * 2**30 / torch.cuda.get_device_properties(0).total_memory
        )
        torch.ops.load_library(plan["sampling_library"]["path"])
        save(
            ROOT / "runtime-v1.json",
            {
                "Torch": torch.__version__,
                "CUDA": torch.version.cuda,
                "device": torch.cuda.get_device_name(),
                "sampling_library": plan["sampling_library"],
                "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            },
        )
        initial = torch.load(
            plan["initial_checkpoint"]["path"], map_location="cpu", weights_only=True
        )
        model = instrument(factory("evidence", plan["module_config"]).cuda(), counts).train()
        optimizer, ema, proof = warm_start_matching(model, initial, lr=1e-4, weight_decay=0.01)
        save(ROOT / "warmstart-v1.json", proof)
        assert proof["original_moments_exact"] and proof["Adam_clocks"]["network"]["steps"] == [
            900.0
        ]
        assert proof["Adam_clocks"]["adapter"]["states"] == 0
        frozen = model_hash(model.frozen)
        assert frozen == plan["frozen_component"]["module_hash"]
        units = read(plan["pair_units"]["path"])["rows"]
        checkpoints = []
        for update, case in enumerate(plan["cases"], 1):
            assert psutil.virtual_memory().available > 32 * 2**30
            assert shutil.disk_usage(REPO).free > 48 * 2**30
            assert shutil.disk_usage("/mnt/external").free > 111 * 2**30
            arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
            batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
            base = torch.from_numpy(np.load(case["parent"]["path"], allow_pickle=False)).cuda()
            pair_units = torch.tensor(
                units[case["training_step"] - 1]["candidate_units_FP32"],
                device="cuda",
                dtype=torch.float32,
            ).reshape(-1, 1, 1, 1)
            optimizer.zero_grad(set_to_none=True)
            output, aux = model(
                base, *(batch[k] for k in ["packed", "variance", "colors", "wb"]), return_aux=True
            )
            loss, terms, mask = objective(
                output,
                aux["frozen_output"],
                batch,
                pair_units,
                plan["domain_weights"][case["domain"]],
            )
            reference = output.detach().cpu().requires_grad_()
            cpu_loss = flat_spatial_error_loss(reference, batch["target"].cpu(), mask.cpu())
            cpu_grad = torch.autograd.grad(cpu_loss, reference)[0]
            gpu_grad = torch.autograd.grad(terms["flat_spatial"], output, retain_graph=True)[
                0
            ].cpu()
            torch.testing.assert_close(
                terms["flat_spatial"].cpu(), cpu_loss, **plan["CPU_GPU_tolerance"]
            )
            torch.testing.assert_close(gpu_grad, cpu_grad, **plan["CPU_GPU_tolerance"])
            old = loss_from_terms(
                {k: float(v.detach()) for k, v in terms.items() if k != "flat_spatial"},
                plan["domain_weights"][case["domain"]],
            )
            expected = np.float32(
                np.float32(old)
                + np.float32(0.25 * plan["domain_weights"][case["domain"]])
                * np.float32(float(terms["flat_spatial"].detach()))
            )
            assert (
                float(loss.detach()) == float(expected) and terms["flat_spatial"] > 0 and mask.any()
            )
            loss.backward()
            gradients = {
                n: int(p.grad.count_nonzero())
                for n, p in model.named_parameters()
                if p.requires_grad and p.grad is not None and torch.isfinite(p.grad).all()
            }
            assert len(gradients) == 142 and all(v > 0 for v in gradients.values())
            assert all(p.grad is None for p in model.frozen.parameters())
            norm = torch.nn.utils.clip_grad_norm_(
                (p for p in model.parameters() if p.requires_grad), 1, error_if_nonfinite=True
            )
            optimizer.step()
            decay = update_matching_ema(model, ema, total_updates=900 + update, maximum_decay=0.999)
            clocks = adam_clocks(model, optimizer)
            assert clocks["network"]["steps"] == [float(900 + update)] and clocks["adapter"][
                "steps"
            ] == [float(update)]
            assert model_hash(model.frozen) == frozen
            record = {
                "update": update,
                "case": case["id"],
                "arrays": case["arrays"],
                "parent": case["parent"],
                "loss": float(loss.detach()),
                "terms": {k: float(v.detach()) for k, v in terms.items()},
                "mask_pixels": int(mask.sum()),
                "gradient_norm": float(norm),
                "nonzero_gradients": gradients,
                "EMA_decay": decay,
                "Adam_clocks": clocks,
                "model_hash": model_hash(model),
                "CPU_GPU_loss_difference": abs(
                    float(terms["flat_spatial"].detach()) - float(cpu_loss.detach())
                ),
                "CPU_GPU_gradient_maximum_difference": float((gpu_grad - cpu_grad).abs().max()),
                "native_gradient_coordinates": cpu_grad.numel(),
                "counts": dict(counts),
            }
            records.append(record)
            save(ROOT / f"update-{update}-v1.json", record)
            path = EXTERNAL / f"probe-step{update}.pt"
            payload = {
                "models": model.state_dict(),
                "ema": ema,
                "optimizer": optimizer.state_dict(),
                "initial_updates": 900,
                "updates": update,
                "CPU_RNG": torch.get_rng_state(),
                "CUDA_RNG": torch.cuda.get_rng_state(),
                "component": type(model).__name__,
                "module_config": plan["module_config"],
                "plan": ref(ROOT / "plan-v1.json"),
                "scope": "Loss probe only,not training initializer",
            }
            with path.open("xb") as stream:
                torch.save(payload, stream)
            checkpoints.append(ref(path))
            del (
                output,
                aux,
                loss,
                terms,
                mask,
                reference,
                cpu_loss,
                cpu_grad,
                gpu_grad,
                batch,
                base,
                pair_units,
                payload,
            )
            if update == 1:
                saved = torch.load(path, map_location="cpu", weights_only=True)
                del model, optimizer
                gc.collect()
                model = instrument(
                    factory("evidence", plan["module_config"]).cuda(), counts
                ).train()
                optimizer, ema, restored = restore_matching_state(
                    model, saved, lr=1e-4, weight_decay=0.01
                )
                assert model_hash(model) == record["model_hash"] and all(
                    restored[k]
                    for k in [
                        "model_loaded_strictly",
                        "Adam_exact",
                        "EMA_exact",
                        "CPU_RNG_exact",
                        "CUDA_RNG_exact",
                    ]
                )
                save(
                    ROOT / "restoration-v1.json",
                    dict(restored, checkpoint=ref(path), repeated_prefix_forwards=0),
                )
                del saved
        assert counts == {"wrapper": 2, "frozen": 2, "network": 2, "sampler": 10, "projection": 2}
        guard(plan)
        save(
            ROOT / "admission-result-v1.json",
            {
                "status": "pass-V181-flat-spatial-CUDA-native-gradients-FP32-total-and-restoration",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "records": records,
                "checkpoints": checkpoints,
                "counts": counts,
                "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
                "new_noise_draws": 0,
                "new_parent_DINO_forwards": 0,
                "protected_optimizer_inputs": 0,
                "source": dict(ref(__file__), text=Path(__file__).read_text()),
                "scope": plan["scope"],
            },
        )
        print(
            "PASS two real native updates/FP32 totals/CPU-GPU loss+gradients/genuine warm restoration;no quality claim"
        )
    except BaseException as error:
        save(
            ROOT / "admission-failure-v1.json",
            {
                "owner": owner,
                "error": repr(error),
                "counts": counts,
                "completed_updates": len(records),
                "scope": "Preserved failure,no automatic retry",
            },
        )
        raise


def inspect():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    result = read(ROOT / "admission-result-v1.json")
    assert (
        not owner_live(result["owner"])
        and result["owner"] == read(ROOT / "admission-launch-v1.json")["owner"]
    )
    assert (
        result["status"].startswith("pass-V181-flat-spatial-CUDA")
        and not (ROOT / "admission-failure-v1.json").exists()
    )
    import torch
    from phase_evidence_training_state import adam_clocks, load_matching_ema, restore_matching_state
    from profile_raw_kernel_inference import model_hash
    from train_local_phase_evidence_trial import factory

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    initial = torch.load(plan["initial_checkpoint"]["path"], map_location="cpu", weights_only=True)
    checked = []
    for u, binding in enumerate(result["checkpoints"], 1):
        assert ref(binding["path"]) == binding
        state = torch.load(binding["path"], map_location="cpu", weights_only=True)
        model = factory("evidence", plan["module_config"])
        optimizer, ema, restored = restore_matching_state(
            model, dict(state, CUDA_RNG=None), lr=1e-4, weight_decay=0.01
        )
        assert all(
            restored[k]
            for k in ["model_loaded_strictly", "Adam_exact", "EMA_exact", "CPU_RNG_exact"]
        )
        assert (
            restored["CUDA_RNG_exact"] is None
            and model_hash(model) == result["records"][u - 1]["model_hash"]
        )
        assert all(
            torch.equal(v, initial["models"][k])
            for k, v in state["models"].items()
            if k.startswith("frozen.")
        )
        clocks = adam_clocks(model, optimizer)
        assert clocks == result["records"][u - 1]["Adam_clocks"]
        load_matching_ema(model, ema)
        checked.append(
            {
                "checkpoint": binding,
                "Adam_clocks": clocks,
                "EMA_module_hash": model_hash(model),
                "strict_raw_EMA_frozen_restore": True,
            }
        )
    assert not torch.cuda.is_initialized()
    save(
        ROOT / "CPU-inspection-v1.json",
        {
            "status": "pass-V181-flat-spatial-CPU-checkpoints-and-warm-Adam-EMA",
            "admission": ref(ROOT / "admission-result-v1.json"),
            "checks": checked,
            "new_neural_forwards": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print(
        "PASS two actual loss-probe checkpoints/Adam901-902+adapter1-2/EMA/frozen;zero CUDA or forward"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "probe", "inspect"])
    args = parser.parse_args()
    {"prepare": prepare, "probe": probe, "inspect": inspect}[args.phase]()
