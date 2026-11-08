"""Real CUDA parity and two restored readout updates above frozen V183 EMA."""

import argparse
import copy
import gc
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref
from profile_spaced_pooled_wave import completed_base

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V189-spaced-pooled-admission-v1"
ARTIFACTS = ROOT / "artifacts"
CPU = ROOT.parent / "V189-spaced-pooled-preparation-v1"


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def guard(plan):
    assert ref(__file__) == plan["runner"], "Use the sealed worker"
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def prepare():
    dependency = completed_base()
    tests = REPO / ".cache/v189-spaced-model-CPU-tests-v3.log"
    assert "30 passed" in tests.read_text()
    cpu = read(CPU / "result-v1.json")
    assert cpu["status"].startswith("pass-native-CPU-pooled-bins") and not owner_live(cpu["owner"])
    assert cpu["native_values_checked"] == 12779520 and cpu["inherited_tensors_exact"] == 189
    assert not ROOT.exists() and not ARTIFACTS.exists()
    assert shutil.disk_usage(REPO).free > (40 + 0.025) * 2**30
    assert psutil.virtual_memory().available > 52 * 2**30
    baseline = read(ROOT.parent / "V183-coherent-pair-evidence-trial-v1/plan-v1.json")
    old = read(ROOT.parent / "V180-local-phase-admission-v1/plan-v1.json")
    ROOT.mkdir()
    ARTIFACTS.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    (work / "tests").mkdir()
    for name in ["test_late_spaced_pooled_wave.py", "test_phase_wave_training_state.py"]:
        shutil.copyfile(REPO / "tests" / name, work / "tests" / name)
    plan = {
        "status": "prepared-seven-native-parities-and-two-isolated-readout-updates-not-quality",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "artifacts": str(ARTIFACTS),
        "work": str(work),
        "runner": ref(work / "scripts/admit_spaced_pooled_wave.py"),
        "dependency": dependency,
        "CPU_result": ref(CPU / "result-v1.json"),
        "CPU_state_tests": dict(ref(tests), text=tests.read_text()),
        "module_config": dict(
            baseline["module_config"], support_windows=[33, 17], support_stride=8
        ),
        "initializer": dependency["initializer"],
        "sampling_library": baseline["sampling_library"],
        "pair_units": baseline["pair_units"],
        "domain_weights": baseline["domain_weights"],
        "cases": old["cases"],
        "probe_domains": ["mesh", "mixed"],
        "lr": 0.001,
        "weight_decay": 0.01,
        "gradient_tolerance": {"rtol": 5e-5, "atol": 2e-5},
        "readout_tolerance": {"rtol": 1e-5, "atol": 3e-6},
        "scope": "One new102nd neural source:508parameter shared phase-aware readout with18 context inputs (large6 plus33/17packed-window6each atstride8, samepooledfixedbins); all189 V183 EMA tensors frozen. Seven baseline/new native initial parities, six standalone nonzero head CPU/GPU checks, two real four-image head-only AdamW updates(mesh,mixed), genuine model/Adam/EMA/CPU-CUDA RNG restoration between them with zero prefix replay. All nine V183 losses/mask retained. New head starts Adam/EMA at0, no old moments are loaded because inherited189 tensors never train. Only training mesh/mixed can optimize; protected sky/cab are parity-only. No quality claim, new source/noise,parent/DINO,RAW decode,original/dataz access. Probe checkpoints never initialize a future trial; local outputs forecast.025GiB above40GiB buffer; external inputs read-only. Pooled2green9neighbor ranking picks2Kunique suppressed bins with alternate-rank phase ordering, not selection holdouts. Same508parameters/193state/initialhash as V187; all101 older neural sources unchanged. V189 changes only suppression radius toceil(maxpackedaxis/65), other pooled ranking/waves/support unchanged. Paired CPU/GPU checks use these actual spaced bins.",
    }
    plan["inputs"] = [
        plan["CPU_result"],
        plan["sampling_library"],
        plan["pair_units"],
        dependency["publication"],
        dependency["verification"],
        plan["initializer"]["export"],
    ]
    for case in plan["cases"]:
        plan["inputs"] += [case["arrays"], case["parent"]]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "plan-v1.json", plan)
    print("Prepared7nativeparities/2head-onlyupdates/508parameters;no Torch imported")


def probe():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    completed_base()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        launch = ROOT / "admission-launch-v1.json"
        if launch.exists() and read(launch)["owner"] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing actual launch owner; no Torch initialized")
    (ROOT / "admission.claim").open("x").close()
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    try:
        import numpy as np
        import torch
        from audit_coherent_pair_evidence_trial import loss_from_terms
        from coherent_pair_objective import objective
        from phase_wave_training_state import (
            clocks,
            fresh_state,
            inherited_hash,
            update_ema,
        )
        from profile_raw_kernel_inference import model_hash
        from spatial_wave_training_state import pack_checkpoint, restore_factored
        from train_phase_evidence_trial import instrument

        from demosaic.late_local_phase_evidence_matching import LateLocalPhaseEvidenceMatchingDetail
        from demosaic.late_spaced_pooled_wave import (
            LateSpacedPooledPhaseWaveDetail,
            fixed_bin_support_context,
            fixed_bin_wave_maps,
            spaced_pooled_phase_bins,
        )

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
            plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
        )
        counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
        model = instrument(
            LateSpacedPooledPhaseWaveDetail(**plan["module_config"])
            .initialize_from_evidence(initial["state_dict"])
            .cuda(),
            counts,
        ).train()
        baseline = instrument(
            LateLocalPhaseEvidenceMatchingDetail(
                **{k: v for k, v in plan["module_config"].items() if not k.startswith("support_")}
            ).cuda(),
            counts,
        ).eval()
        baseline.load_state_dict(initial["state_dict"], strict=True)
        baseline.requires_grad_(False)
        inherited = plan["initializer"]["module_hash"]
        assert inherited_hash(model) == model_hash(baseline) == inherited
        assert all(
            n.startswith("wave_readout.") for n, p in model.named_parameters() if p.requires_grad
        )
        captured = {}

        def capture(module, args):
            captured.update(
                evidence=args[0].detach().cpu(),
                bins=args[1].detach().cpu(),
                support=args[2].detach().cpu(),
            )

        hook = model.wave_readout.register_forward_pre_hook(capture)
        parities = []
        for case in plan["cases"]:
            assert psutil.virtual_memory().available > 32 * 2**30
            with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                batch = {
                    k: torch.from_numpy(archive[k]).cuda()
                    for k in ["packed", "variance", "colors", "wb"]
                }
            base = torch.from_numpy(np.load(case["parent"]["path"], allow_pickle=False)).cuda()
            captured.clear()
            args = [batch[k] for k in ["packed", "variance", "colors", "wb"]]
            with torch.no_grad():
                old = baseline(base, *args)
                actual, aux = model(base, *args, return_aux=True)
            assert torch.equal(old.view(torch.int32), actual.view(torch.int32))
            assert (
                torch.equal(old, aux["inherited_output"])
                and aux["wave_correction"].count_nonzero() == 0
            )
            row = {
                "case": case["id"],
                "native_output_values": actual.numel(),
                "initial_output_bit_exact": True,
                "matching_evaluated": aux["matching_evaluated"],
            }
            if captured:
                cpu_bins, cpu_valid, _ = spaced_pooled_phase_bins(
                    batch["packed"].cpu(),
                    batch["variance"].cpu(),
                    batch["colors"].cpu(),
                    peaks=plan["module_config"]["evidence_peaks"],
                )
                assert torch.equal(cpu_bins, captured["bins"])
                cpu_waves, _ = fixed_bin_wave_maps(
                    batch["packed"].cpu(),
                    batch["variance"].cpu(),
                    batch["colors"].cpu(),
                    captured["bins"],
                    cpu_valid,
                    window=plan["module_config"]["evidence_window"],
                    stride=plan["module_config"]["evidence_stride"],
                )
                torch.testing.assert_close(captured["evidence"], cpu_waves, rtol=2e-5, atol=3e-6)
                row.update(
                    pooled_selection_CPU_GPU_bins_exact=True,
                    wave_feature_values_checked=cpu_waves.numel(),
                    wave_feature_maximum_CPU_GPU_difference=float(
                        (captured["evidence"] - cpu_waves).abs().max()
                    ),
                )
                del cpu_waves
                cpu_support, _ = fixed_bin_support_context(
                    batch["packed"].cpu(),
                    batch["variance"].cpu(),
                    batch["colors"].cpu(),
                    captured["bins"],
                    aux["wave_selection"]["valid"].cpu(),
                    windows=tuple(plan["module_config"]["support_windows"]),
                    stride=plan["module_config"]["support_stride"],
                )
                torch.testing.assert_close(captured["support"], cpu_support, rtol=2e-5, atol=3e-6)
                row.update(
                    support_values_checked=cpu_support.numel(),
                    support_maximum_CPU_GPU_difference=float(
                        (captured["support"] - cpu_support).abs().max()
                    ),
                )
                del cpu_support
                cpu_head = copy.deepcopy(model.wave_readout).cpu()
                cpu_head._forward_pre_hooks.clear()
                with torch.no_grad():
                    cpu_head.mixing.weight.copy_(
                        torch.linspace(-0.05, 0.07, cpu_head.mixing.weight.numel()).reshape_as(
                            cpu_head.mixing.weight
                        )
                    )
                    cpu_head.mixing.bias.copy_(torch.linspace(-0.02, 0.03, 12))
                    expected = cpu_head(captured["evidence"], captured["bins"], captured["support"])
                    gpu_head = copy.deepcopy(cpu_head).cuda()
                    actual_head = gpu_head(
                        captured["evidence"].cuda(),
                        captured["bins"].cuda(),
                        captured["support"].cuda(),
                    ).cpu()
                torch.testing.assert_close(actual_head, expected, **plan["readout_tolerance"])
                row.update(
                    nonzero_head_values=actual_head.numel(),
                    nonzero_head_maximum_CPU_GPU_difference=float(
                        (actual_head - expected).abs().max()
                    ),
                )
                del cpu_head, gpu_head, expected, actual_head
            parities.append(row)
            save(ROOT / f"parity-{len(parities)}-v1.json", row)
            print("parity", case["id"], actual.numel(), flush=True)
            del batch, base, args, old, actual, aux
            captured.clear()
            gc.collect()
        del baseline, initial
        optimizer, ema = fresh_state(model, lr=plan["lr"], weight_decay=plan["weight_decay"])
        assert clocks(model, optimizer) == {"tensors": 4, "states": 0, "steps": []}
        units = read(plan["pair_units"]["path"])["rows"]
        records = []
        checkpoints = []
        for update, domain in enumerate(plan["probe_domains"], 1):
            case = next(c for c in plan["cases"] if c["domain"] == domain)
            with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                batch = {k: torch.from_numpy(archive[k]).cuda() for k in archive.files}
            base = torch.from_numpy(np.load(case["parent"]["path"], allow_pickle=False)).cuda()
            pair_units = torch.tensor(
                units[case["training_step"] - 1]["candidate_units_FP32"],
                device="cuda",
                dtype=torch.float32,
            ).reshape(-1, 1, 1, 1)
            optimizer.zero_grad(set_to_none=True)
            captured.clear()
            output, aux = model(
                base, *(batch[k] for k in ["packed", "variance", "colors", "wb"]), return_aux=True
            )
            loss, terms, mask = objective(
                output, aux["frozen_output"], batch, pair_units, plan["domain_weights"][domain]
            )
            term_values = {k: float(v.detach()) for k, v in terms.items()}
            assert float(loss.detach()) == loss_from_terms(
                term_values, plan["domain_weights"][domain]
            )
            upstream = torch.autograd.grad(loss, output, retain_graph=True)[0].detach().cpu()
            cpu_head = copy.deepcopy(model.wave_readout).cpu()
            cpu_head._forward_pre_hooks.clear()
            cpu_output = (
                cpu_head(captured["evidence"], captured["bins"], captured["support"])
                * aux["sigma"].cpu()
            )
            cpu_gradients = torch.autograd.grad(
                (cpu_output * upstream).sum(), tuple(cpu_head.parameters())
            )
            loss.backward()
            differences = []
            gradients = {}
            for (name, p), expected in zip(
                model.wave_readout.named_parameters(), cpu_gradients, strict=True
            ):
                assert p.grad is not None and torch.isfinite(p.grad).all()
                torch.testing.assert_close(p.grad.cpu(), expected, **plan["gradient_tolerance"])
                gradients[name] = int(p.grad.count_nonzero())
                differences.append(float((p.grad.cpu() - expected).abs().max()))
                assert bool(p.grad.count_nonzero()) == (update > 1 or name.startswith("mixing."))
            assert all(
                p.grad is None
                for n, p in model.named_parameters()
                if not n.startswith("wave_readout.")
            )
            norm = torch.nn.utils.clip_grad_norm_(
                model.wave_readout.parameters(), 1, error_if_nonfinite=True
            )
            optimizer.step()
            decay = update_ema(model, ema, updates=update)
            assert inherited_hash(model) == inherited
            assert clocks(model, optimizer) == {"tensors": 4, "states": 4, "steps": [float(update)]}
            record = {
                "update": update,
                "domain": domain,
                "case": case["id"],
                "loss": float(loss.detach()),
                "terms": term_values,
                "independent_nine_term_FP32_total_exact": True,
                "mask_pixels": int(mask.sum()),
                "gradient_norm": float(norm),
                "nonzero_gradient_coordinates": gradients,
                "CPU_GPU_parameter_gradient_maximum_difference": max(differences),
                "parameter_gradient_coordinates": sum(
                    p.numel() for p in model.wave_readout.parameters()
                ),
                "EMA_decay": decay,
                "Adam_clocks": clocks(model, optimizer),
                "inherited_hash": inherited,
                "model_hash": model_hash(model),
                "counts": dict(counts),
            }
            records.append(record)
            save(ROOT / f"update-{update}-v1.json", record)
            path = ARTIFACTS / f"probe-step{update}.pt"
            payload = {
                "models": model.state_dict(),
                "ema": ema,
                "optimizer": optimizer.state_dict(),
                "updates": update,
                "inherited_hash": inherited,
                "CPU_RNG": torch.get_rng_state(),
                "CUDA_RNG": torch.cuda.get_rng_state(),
                "component": type(model).__name__,
                "module_config": plan["module_config"],
                "plan": ref(ROOT / "plan-v1.json"),
                "scope": "Admission only;never a training initializer",
            }
            with path.open("xb") as stream:
                torch.save(pack_checkpoint(payload, plan["initializer"]["export"]), stream)
            checkpoints.append(ref(path))
            del (
                output,
                aux,
                loss,
                terms,
                mask,
                batch,
                base,
                pair_units,
                payload,
                upstream,
                cpu_head,
                cpu_output,
                cpu_gradients,
            )
            captured.clear()
            if update == 1:
                saved = torch.load(path, map_location="cpu", weights_only=True)
                hook.remove()
                del model, optimizer
                gc.collect()
                model = instrument(
                    LateSpacedPooledPhaseWaveDetail(**plan["module_config"]).cuda(), counts
                ).train()
                optimizer, ema = restore_factored(
                    model, saved, lr=plan["lr"], weight_decay=plan["weight_decay"]
                )
                assert (
                    model_hash(model) == record["model_hash"] and inherited_hash(model) == inherited
                )
                hook = model.wave_readout.register_forward_pre_hook(capture)
                save(
                    ROOT / "restoration-v1.json",
                    {
                        "checkpoint": ref(path),
                        "model_Adam_EMA_CPU_CUDA_RNG_exact": True,
                        "repeated_prefix_forwards": 0,
                        "Adam_clocks": clocks(model, optimizer),
                    },
                )
                del saved
            print("update", update, "gradients", gradients, flush=True)
        assert counts == {
            "wrapper": 16,
            "frozen": 16,
            "network": 14,
            "sampler": 70,
            "projection": 14,
        }
        guard(plan)
        save(
            ROOT / "admission-result-v1.json",
            {
                "status": "pass-V189-frozen-baseline-native-CUDA-parity-head-gradients-and-restoration",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "parities": parities,
                "records": records,
                "checkpoints": checkpoints,
                "counts": counts,
                "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
                "inherited189_tensors_unchanged": True,
                "new_source_noise_draws": 0,
                "parent_DINO_calls": 0,
                "protected_optimizer_inputs": 0,
                "scope": plan["scope"],
            },
        )
        print(
            "PASS7initialparities/6nonzeroheadparities/2updates/508CPU-GPUgradients/restoration",
            flush=True,
        )
    except BaseException as exc:
        save(
            ROOT / "admission-failure-v1.json",
            {"owner": owner, "error": repr(exc), "time_UTC": time.time()},
        )
        raise


def launch():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "admission-launch-v1.json").exists()
    env = dict(
        os.environ,
        PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
        CUDA_VISIBLE_DEVICES="0",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    with (ROOT / "admission-v1.log").open("xb") as log:
        process = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), plan["runner"]["path"], "probe"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
    save(ROOT / "admission-launch-v1.json", {"owner": owner, "plan": ref(ROOT / "plan-v1.json")})
    print(json.dumps(owner))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "probe"])
    args = parser.parse_args()
    {"prepare": prepare, "launch": launch, "probe": probe}[args.phase]()
