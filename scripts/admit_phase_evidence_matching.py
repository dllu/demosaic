"""Prepare/wait/run one V178 CUDA admission after the complete V175 GPU pipeline.

Admission uses existing cached parents,never new V143/DINO or sensor renders.
Two optimizer updates are an implementation probe,not a model-quality result.
"""

import argparse
import gc
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import dependency_readiness, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V178-phase-evidence-admission-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V178-phase-evidence-admission-v1")
DEPENDENCY = REPO / ".cache/quality-20261107/V175-fresh-noise-matching-v2"


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def status(phase, owner, *, watch=False, **fields):
    path = ROOT / ("watch-status-v1.json" if watch else "admission-status-v1.json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            dict(status=phase, owner=owner, observed_unix_UTC=time.time(), **fields), indent=2
        )
        + "\n"
    )
    temporary.replace(path)


def own():
    return {"pid": os.getpid(), "created": psutil.Process().create_time()}


def guard(plan):
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def prepare():
    assert not ROOT.exists() and not EXTERNAL.exists()
    prior_path = REPO / ".cache/quality-20261107/V178-phase-evidence-preparation-v1/result-v1.json"
    prior = read(prior_path)
    assert prior["status"].startswith("completed-CPU")
    prior_plan = read(prior["plan"]["path"])
    for binding in prior_plan["sources"]:
        assert ref(binding["path"])["sha256"] == binding["sha256"]
    tests = REPO / ".cache/v178-admission-protocol-CPU-tests-v2.log"
    assert "18 passed" in tests.read_text()
    v175 = read(DEPENDENCY / "plan-v1.json")
    cache = read(v175["cache"]["path"])
    design = read(v175["design"]["path"])
    cases = []
    for domain in ["mesh", "photo", "mixed", "flat"]:
        row = next(
            r
            for r in cache["batches"]
            if r["metadata"]["domain"] == domain
            and any(r["metadata"]["noise"][k] > 0 for k in ["shot", "read"])
        )
        cases.append(
            {
                "id": f"training-{domain}-step{row['step']}",
                "arrays": row["arrays"],
                "parent": row["parent"],
                "training_step": row["step"],
                "domain": domain,
                "noisy": True,
            }
        )
    row = next(
        r
        for r in cache["batches"]
        if not any(r["metadata"]["noise"][k] > 0 for k in ["shot", "read"])
    )
    cases.append(
        {
            "id": f"training-ADC-step{row['step']}",
            "arrays": row["arrays"],
            "parent": row["parent"],
            "training_step": row["step"],
            "domain": row["metadata"]["domain"],
            "noisy": False,
        }
    )
    for name in ["main-overcast-sky", "mesh-nominal"]:
        row = next(r for r in design["observations"] if r["id"] == name)
        cases.append(
            {
                "id": name,
                "arrays": row["arrays"],
                "parent": row["parent"],
                "domain": "protected-real",
                "training_step": None,
                "noisy": True,
            }
        )
    for path, digest in v175["prior_neural_hashes"].items():
        assert ref(REPO / "src/demosaic" / path)["sha256"] == digest
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.4 + 0.2) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 1.25 + 0.2) * 2**30
    assert psutil.virtual_memory().available > 40 * 2**30
    ROOT.mkdir()
    EXTERNAL.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    (work / "tests").mkdir()
    for name in ["test_phase_admission_protocol.py", "test_late_phase_evidence_matching.py"]:
        shutil.copyfile(REPO / "tests" / name, work / "tests" / name)
    plan = {
        "status": "fixed-native-CUDA-parity-gradient-restore-and-resource-admission",
        "created_unix_UTC": time.time(),
        "dependency_root": str(DEPENDENCY),
        "root": str(ROOT),
        "external": str(EXTERNAL),
        "work": str(work),
        "runner": ref(work / "scripts" / Path(__file__).name),
        "cases": cases,
        "checkpoint": v175["initial_checkpoint"],
        "sampling_library": v175["sampling_library"],
        "pair_units": v175["pair_units"],
        "CPU_preparation": ref(prior_path),
        "module_config": dict(v175["module_config"], evidence_peaks=4),
        "domain_weights": v175["domain_weights"],
        "gradient_clip": v175["gradient_clip"],
        "lr": 1e-4,
        "weight_decay": v175["weight_decay"],
        "minimum_GiB": {"RAM": 32, "local": 48, "external": 111},
        "launch_RAM_GiB": 52,
        "CUDA_quota_GiB": 24,
        "new_local_projection_GiB": 0.2,
        "new_external_projection_GiB": 0.2,
        "projection_margin_GiB": 0.5,
        "CPU_GPU_feature_tolerance": {"rtol": 1e-4, "atol": 1e-4},
        "protocol_CPU_tests": dict(ref(tests), text=tests.read_text()),
        "expected": {
            "parity_rows": 14,
            "all_component_calls": 32,
            "frozen_calls": 32,
            "matching_calls": 27,
            "sampler_calls": 135,
            "new_projection_calls": 15,
            "CPU_feature_calls": 6,
            "direct_GPU_feature_calls": 3,
            "optimizer_updates": 2,
            "Adam_tensors": 142,
            "restored_checkpoint_step": 1,
        },
        "scope": "Run once only after original V175 train,review,completion-watch owners are terminal and completed audits/render receipts exist.7 native cached cases xraw/EMA xold/new;no new parent/DINO,sensor/source or RAWdecode. Two fresh-Adam updates are an admission probe:mesh step1,save/genuinely restore model/Adam/CPU+CUDA RNG,mixed step4. No prefix replay. Post-update ADC/mixed-zero-cell invariants and direct constant/phase-selection feature checks. This is not a trained-quality report or a choice of future training initializer;V172 raw/EMA are compatibility controls. Protected captures never enter optimizer updates. No automatic retry on failure,no model promotion or image-quality claim.",
    }
    plan["inputs"] = [
        ref(DEPENDENCY / "plan-v1.json"),
        plan["checkpoint"],
        plan["sampling_library"],
        plan["pair_units"],
        plan["CPU_preparation"],
    ]
    for case in cases:
        plan["inputs"].extend([case["arrays"], case["parent"]])
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "plan-v1.json", plan)
    print("Prepared32componentcalls27matching135samplers2updates;GPUdependencyrequired", flush=True)


def resources(plan, owner):
    while True:
        available = {
            "RAM": psutil.virtual_memory().available,
            "local": shutil.disk_usage(REPO).free,
            "external": shutil.disk_usage("/mnt/external").free,
        }
        if all(available[k] > v * 2**30 for k, v in plan["minimum_GiB"].items()):
            return
        status("waiting-before-next-forward", owner, available_bytes=available)
        time.sleep(2)


def worker():
    plan = read(ROOT / "plan-v1.json")
    owner = own()
    # No Torch/CUDA import or scientific claim before completed dependency proof.
    proof = dependency_readiness(plan["dependency_root"])
    assert proof["ready"], proof
    guard(plan)
    for _ in range(60):
        try:
            launch = read(ROOT / "admission-launch-v1.json")
            if launch["owner"] == owner:
                break
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(1)
    else:
        raise RuntimeError("Admission launch ownership not observable;no CUDA initialized")
    (ROOT / "admission.claim").open("x").close()
    save(ROOT / "dependency-proof-v1.json", proof)
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    counts = {
        name: {"wrapper": 0, "frozen": 0, "network": 0, "sampler": 0, "projection": 0}
        for name in ["old", "new"]
    }
    feature_calls = {"CPU": 0, "direct_GPU": 0}
    phase = "startup"
    parity = []
    updates = []
    try:
        import numpy as np
        import torch
        from nonlocal_residual_objective import objective
        from profile_raw_kernel_inference import model_hash
        from train_local_noise_matching_trial import tree_equal

        from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail
        from demosaic.late_phase_evidence_matching import (
            LatePhaseEvidenceMatchingDetail,
            phase_evidence_maps,
        )
        from demosaic.prediction_archive import fingerprint

        assert not torch.cuda.is_initialized()
        resources(plan, owner)
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.set_float32_matmul_precision("highest")
        torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.cuda.set_per_process_memory_fraction(
            plan["CUDA_quota_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory
        )
        torch.ops.load_library(plan["sampling_library"]["path"])
        torch.cuda.reset_peak_memory_stats()
        save(
            ROOT / "runtime-v1.json",
            {
                "owner": owner,
                "Torch": torch.__version__,
                "CUDA": torch.version.cuda,
                "device": torch.cuda.get_device_name(0),
                "native_library": plan["sampling_library"],
                "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
                "CUDA_quota_GiB": 24,
            },
        )
        state = torch.load(plan["checkpoint"]["path"], map_location="cpu", weights_only=True)
        old = (
            LateLocalNoiseMatchingDetail(
                **{k: v for k, v in plan["module_config"].items() if k != "evidence_peaks"}
            )
            .cuda()
            .eval()
        )
        new = LatePhaseEvidenceMatchingDetail(**plan["module_config"]).cuda().eval()
        captured = {}
        event_stream = (ROOT / "forward-events-v1.jsonl").open("x")

        def event(name, kind):
            counts[name][kind] += 1
            event_stream.write(
                json.dumps({"phase": phase, "component": name, "kind": kind, "counts": counts})
                + "\n"
            )
            event_stream.flush()

        def instrument(model, name):
            for kind, child in [
                ("wrapper", model),
                ("frozen", model.frozen),
                ("network", model.network),
            ]:
                child.register_forward_pre_hook(
                    lambda *args, name=name, kind=kind: event(name, kind)
                )
            for child in model.network.modules():
                if type(child).__name__ == "NonlocalBlock":
                    child.register_forward_pre_hook(lambda *args, name=name: event(name, "sampler"))
            if name == "new":

                def projection_hook(_, args):
                    event("new", "projection")
                    captured["features"] = args[0].detach()

                model.phase_evidence_in.register_forward_pre_hook(projection_hook)

        instrument(old, "old")
        instrument(new, "new")

        def load_case(case, *, targets=False):
            assert (
                ref(case["arrays"]["path"]) == case["arrays"]
                and ref(case["parent"]["path"]) == case["parent"]
            )
            with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
                keys = ["packed", "variance", "colors", "wb"] + (
                    ["target", "pair_indices"] if targets else []
                )
                cpu = {key: torch.from_numpy(arrays[key].copy()) for key in keys}
            base = torch.from_numpy(np.load(case["parent"]["path"], allow_pickle=False)).cuda()
            return cpu, {k: v.cuda() for k, v in cpu.items()}, base

        def invoke(model, batch, base, *, aux=True):
            resources(plan, owner)
            return model(
                base, *(batch[k] for k in ["packed", "variance", "colors", "wb"]), return_aux=aux
            )

        frozen_hash = None
        with (ROOT / "parity-rows-v1.jsonl").open("x") as journal:
            for case in plan["cases"]:
                cpu, batch, base = load_case(case)
                reference = reference_aux = None
                if case["noisy"]:
                    with torch.no_grad():
                        reference, reference_aux = phase_evidence_maps(
                            *(cpu[k] for k in ["packed", "variance", "colors"])
                        )
                    feature_calls["CPU"] += 1
                for endpoint in ["raw", "EMA"]:
                    phase = f"parity:{case['id']}:{endpoint}"
                    status(phase, owner, counts=counts)
                    old.load_state_dict(state["models"], strict=True)
                    if endpoint == "EMA":
                        old.network.load_state_dict(state["ema"], strict=True)
                    new.initialize_from_local_matching(old.state_dict())
                    if frozen_hash is None:
                        frozen_hash = model_hash(new.frozen)
                    with torch.no_grad():
                        torch.cuda.synchronize()
                        started = time.perf_counter()
                        baseline, baseline_aux = invoke(old, batch, base)
                        torch.cuda.synchronize()
                        seconds_old = time.perf_counter() - started
                        started = time.perf_counter()
                        output, aux = invoke(new, batch, base)
                        torch.cuda.synchronize()
                        seconds_new = time.perf_counter() - started
                    row = {
                        "id": case["id"],
                        "endpoint": endpoint,
                        "source": case["arrays"],
                        "parent": case["parent"],
                        "baseline": fingerprint(baseline.cpu().numpy()),
                        "candidate": fingerprint(output.cpu().numpy()),
                        "old_seconds": seconds_old,
                        "new_seconds": seconds_new,
                        "matching_evaluated": aux["matching_evaluated"],
                        "counts": json.loads(json.dumps(counts)),
                    }
                    exact = torch.equal(baseline.view(torch.int32), output.view(torch.int32))
                    row["initial_output_bit_exact"] = exact
                    if not exact:
                        np.savez(
                            ROOT / "initial-parity-failure-arrays-v1.npz",
                            baseline=baseline.cpu().numpy(),
                            candidate=output.cpu().numpy(),
                        )
                    assert exact, row
                    assert (
                        aux["matching_evaluated"]
                        == baseline_aux["matching_evaluated"]
                        == case["noisy"]
                    )
                    if case["noisy"]:
                        observed = captured.pop("features").cpu()
                        assert torch.equal(
                            aux["phase_evidence"]["bin_yx"].cpu(), reference_aux["bin_yx"]
                        )
                        torch.testing.assert_close(
                            observed, reference, **plan["CPU_GPU_feature_tolerance"]
                        )
                        delta = observed.double() - reference.double()
                        row["CPU_GPU_feature_RMS_difference"] = float(delta.square().mean().sqrt())
                        row["CPU_GPU_feature_maximum_difference"] = float(delta.abs().max())
                        row["feature_coordinates_checked"] = observed.numel()
                        del observed, delta
                    else:
                        assert aux["phase_evidence"] is None and torch.equal(
                            output.view(torch.int32), aux["frozen_output"].view(torch.int32)
                        )
                    parity.append(row)
                    journal.write(json.dumps(row) + "\n")
                    journal.flush()
                    os.fsync(journal.fileno())
                    del baseline, baseline_aux, output, aux
                del cpu, batch, base, reference, reference_aux
        del old
        gc.collect()
        new.initialize_from_local_matching(state["models"])
        new.train()
        optimizer = torch.optim.AdamW(
            (p for p in new.parameters() if p.requires_grad),
            lr=plan["lr"],
            weight_decay=plan["weight_decay"],
        )
        units = read(plan["pair_units"]["path"])["rows"]
        for update, domain in [(1, "mesh"), (2, "mixed")]:
            case = next(c for c in plan["cases"] if c["domain"] == domain)
            phase = f"optimizer-update:{update}:{domain}"
            status(phase, owner, counts=counts)
            cpu, batch, base = load_case(case, targets=True)
            pair_units = torch.tensor(
                units[case["training_step"] - 1]["candidate_units_FP32"],
                device="cuda",
                dtype=torch.float32,
            ).reshape(-1, 1, 1, 1)
            optimizer.zero_grad(set_to_none=True)
            output, aux = invoke(new, batch, base)
            loss, terms, mask = objective(
                output, aux["frozen_output"], batch, pair_units, plan["domain_weights"][domain]
            )
            assert torch.isfinite(loss)
            loss.backward()
            gradients = {}
            for name, parameter in new.named_parameters():
                if not parameter.requires_grad:
                    assert parameter.grad is None
                    continue
                assert parameter.grad is not None and torch.isfinite(parameter.grad).all(), name
                gradients[name] = {
                    "maximum": float(parameter.grad.abs().max()),
                    "nonzero": int(parameter.grad.count_nonzero()),
                }
            assert len(gradients) == 142 and gradients["phase_evidence_in.weight"]["nonzero"] > 0
            assert any(v["nonzero"] > 0 for k, v in gradients.items() if k.startswith("network."))
            norm = torch.nn.utils.clip_grad_norm_(
                (p for p in new.parameters() if p.requires_grad),
                plan["gradient_clip"],
                error_if_nonfinite=True,
            )
            optimizer.step()
            torch.cuda.synchronize()
            assert len(optimizer.state) == 142 and all(
                float(v["step"]) == update for v in optimizer.state.values()
            )
            assert model_hash(new.frozen) == frozen_hash
            record = {
                "update": update,
                "case": case["id"],
                "loss": float(loss.detach()),
                "terms": {k: float(v.detach()) for k, v in terms.items()},
                "gradient_norm_before_clip": float(norm),
                "gradients": gradients,
                "mask_pixels": int(mask.sum()),
                "mask": fingerprint(mask.cpu().numpy()),
                "model_hash": model_hash(new),
                "counts": json.loads(json.dumps(counts)),
            }
            updates.append(record)
            save(ROOT / f"update-{update}-v1.json", record)
            checkpoint = EXTERNAL / f"admission-step{update}.pt"
            payload = {
                "component": "LatePhaseEvidenceMatchingDetail",
                "module_config": plan["module_config"],
                "plan": ref(ROOT / "plan-v1.json"),
                "models": new.state_dict(),
                "optimizer": optimizer.state_dict(),
                "updates": update,
                "CPU_RNG": torch.get_rng_state(),
                "CUDA_RNG": torch.cuda.get_rng_state(),
                "scope": "Admission probe only,not a quality checkpoint",
            }
            with checkpoint.open("xb") as stream:
                torch.save(payload, stream)
            captured.clear()
            del output, aux, loss, terms, mask, batch, cpu, base, pair_units, payload
            if update == 1:
                saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
                del new, optimizer
                gc.collect()
                new = LatePhaseEvidenceMatchingDetail(**plan["module_config"]).cuda().train()
                new.load_state_dict(saved["models"], strict=True)
                optimizer = torch.optim.AdamW(
                    (p for p in new.parameters() if p.requires_grad),
                    lr=plan["lr"],
                    weight_decay=plan["weight_decay"],
                )
                optimizer.load_state_dict(saved["optimizer"])
                assert tree_equal(optimizer.state_dict(), saved["optimizer"])
                torch.set_rng_state(saved["CPU_RNG"])
                torch.cuda.set_rng_state(saved["CUDA_RNG"])
                assert model_hash(new) == record["model_hash"]
                assert torch.equal(torch.get_rng_state(), saved["CPU_RNG"]) and torch.equal(
                    torch.cuda.get_rng_state().cpu(), saved["CUDA_RNG"]
                )
                assert len(optimizer.state) == 142 and all(
                    float(v["step"]) == 1 for v in optimizer.state.values()
                )
                instrument(new, "new")
                save(
                    ROOT / "restoration-v1.json",
                    {
                        "status": "pass-genuine-step1-model-Adam-and-CPU-CUDA-RNG-restoration",
                        "checkpoint": ref(checkpoint),
                        "model_hash": model_hash(new),
                        "Adam_states": 142,
                        "Adam_step": 1,
                        "Adam_moments_exact": True,
                        "CPU_CUDA_RNG_exact": True,
                        "replayed_updates": 0,
                    },
                )
                del saved
        new.eval()
        invariants = []
        with torch.no_grad():
            for label in ["ADC", "mixed-zero"]:
                phase = f"post-update:{label}"
                status(phase, owner, counts=counts)
                case = (
                    next(c for c in plan["cases"] if not c["noisy"])
                    if label == "ADC"
                    else next(c for c in plan["cases"] if c["domain"] == "mesh")
                )
                cpu, batch, base = load_case(case)
                if label == "mixed-zero":
                    batch["variance"][..., : batch["variance"].shape[-1] // 4] = 0
                output, aux = invoke(new, batch, base)
                width = output.shape[-1] if label == "ADC" else output.shape[-1] // 4
                assert torch.equal(
                    output[..., :width].view(torch.int32),
                    aux["frozen_output"][..., :width].view(torch.int32),
                )
                assert aux["matching_evaluated"] == (label != "ADC")
                invariants.append(
                    {
                        "case": label,
                        "source": case["arrays"],
                        "native_zero_width": width,
                        "bit_exact_frozen_cells": True,
                        "scope": "Mixed-zero changes supplied variance only;conditioning fixture,not a physical capture or quality score.",
                    }
                )
                captured.clear()
                del cpu, batch, base, output, aux
            phase = "direct-CUDA-feature-invariants"
            constant = (
                torch.arange(4, device="cuda", dtype=torch.float32)[None, :, None, None].expand(
                    1, 4, 16, 16
                )
                / 1000
            )
            features, _ = phase_evidence_maps(
                constant, torch.full_like(constant, 1e-5), torch.tensor([0, 1, 1, 2], device="cuda")
            )
            feature_calls["direct_GPU"] += 1
            assert features.count_nonzero() == 0
            cpu, batch, base = load_case(next(c for c in plan["cases"] if c["domain"] == "mesh"))
            del cpu, base
            raw, variance, colors = [batch[k][:1].clone() for k in ["packed", "variance", "colors"]]
            _, before = phase_evidence_maps(raw, variance, colors)
            feature_calls["direct_GPU"] += 1
            green = torch.where(colors[0] == 1)[0]
            index = int(green[1])
            raw[:, index] = raw[:, index].flip(-1) * 1.01
            variance[:, index] *= 1.1
            _, after = phase_evidence_maps(raw, variance, colors)
            feature_calls["direct_GPU"] += 1
            assert torch.equal(before["bin_yx"][:, 0], after["bin_yx"][:, 0])
            assert torch.equal(
                before["nominal_power"][:, 0, :, 0], after["nominal_power"][:, 0, :, 0]
            )
        assert model_hash(new.frozen) == frozen_hash
        totals = {
            k: sum(v[k] for v in counts.values())
            for k in ["wrapper", "frozen", "network", "sampler", "projection"]
        }
        expected = plan["expected"]
        assert totals == dict(
            zip(
                ["wrapper", "frozen", "network", "sampler", "projection"],
                [32, 32, 27, 135, 15],
                strict=True,
            )
        ), totals
        assert (
            len(parity) == expected["parity_rows"] == 14
            and len(updates) == expected["optimizer_updates"] == 2
        )
        assert feature_calls == {"CPU": 6, "direct_GPU": 3}
        event_stream.close()
        result = {
            "status": "pass-V178-native-CUDA-initial-parity-real-gradients-restoration-and-local-ADC-invariants",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "parity": parity,
            "updates": updates,
            "invariants": invariants,
            "counts": counts,
            "totals": totals,
            "feature_calls": feature_calls,
            "frozen_module_hash": frozen_hash,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "post_update_checkpoints": [ref(EXTERNAL / f"admission-step{i}.pt") for i in [1, 2]],
            "actual_optimizer_updates": 2,
            "new_V143_DINO_forwards": 0,
            "new_noise_source_draws": 0,
            "RAW_decodes": 0,
            "direct_constant_feature_maps_zero": True,
            "measured_phase_cannot_change_selecting_phase_bins_or_power": True,
            "scope": plan["scope"],
        }
        save(ROOT / "admission-result-v1.json", result)
        status("completed-admission-awaiting-inspection-no-training-launched", owner, counts=counts)
        print("PASSV178CUDAadmission;noqualityortraininglaunch", flush=True)
    except BaseException as error:
        save(
            ROOT / "admission-failure-v1.json",
            {
                "status": "failed-preserved-no-retry",
                "owner": owner,
                "phase": phase,
                "error": repr(error),
                "counts": counts,
                "completed_parity_rows": len(parity),
                "completed_optimizer_updates": len(updates),
                "feature_calls": feature_calls,
            },
        )
        status("failed-preserved-no-retry", owner, error=repr(error), counts=counts)
        raise


def watch():
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    (ROOT / "watch.claim").open("x").close()
    owner = own()
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    save(ROOT / "watch-owner-v1.json", owner)
    try:
        while True:
            try:
                proof = dependency_readiness(plan["dependency_root"])
            except (psutil.AccessDenied, OSError, json.JSONDecodeError) as error:
                status("waiting-for-dependency-observation", owner, watch=True, error=repr(error))
                time.sleep(15)
                continue
            if not proof["ready"]:
                status(proof["reason"], owner, watch=True, dependency=proof)
                time.sleep(15)
                continue
            free = {
                "RAM": psutil.virtual_memory().available,
                "local": shutil.disk_usage(REPO).free,
                "external": shutil.disk_usage("/mnt/external").free,
            }
            if (
                free["RAM"] <= 52 * 2**30
                or free["local"] <= (48 + 0.5 + 0.2) * 2**30
                or free["external"] <= (111 + 0.5 + 0.2) * 2**30
            ):
                status(
                    "waiting-for-admission-launch-resources",
                    owner,
                    watch=True,
                    available_bytes=free,
                )
                time.sleep(15)
                continue
            break
        assert not any(
            (ROOT / name).exists()
            for name in [
                "admission.claim",
                "admission-launch-v1.json",
                "admission-result-v1.json",
                "admission-failure-v1.json",
            ]
        )
        guard(plan)
        save(ROOT / "watch-ready-dependency-v1.json", proof)
        env = dict(
            os.environ,
            PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="2",
            MKL_NUM_THREADS="1",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
        )
        command = [str(REPO / ".venv/bin/python"), plan["runner"]["path"], "worker"]
        with (ROOT / "admission-v1.log").open("xb") as log:
            child = subprocess.Popen(
                command,
                cwd=REPO,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            save(
                ROOT / "admission-launch-v1.json",
                {
                    "owner": child_owner,
                    "watcher": owner,
                    "command": command,
                    "plan": ref(ROOT / "plan-v1.json"),
                    "dependency_proof": ref(ROOT / "watch-ready-dependency-v1.json"),
                },
            )
            status("running-CUDA-admission", owner, watch=True, worker_owner=child_owner)
            code = child.wait()
        assert code == 0, f"Admission exited{code};no retry"
        result = read(ROOT / "admission-result-v1.json")
        assert result["owner"] == child_owner and result["status"].startswith("pass-")
        save(
            ROOT / "watch-result-v1.json",
            {
                "status": "completed-one-CUDA-admission-awaiting-inspection",
                "owner": owner,
                "admission": ref(ROOT / "admission-result-v1.json"),
                "launched_training": False,
            },
        )
        status("completed-admission-awaiting-inspection-no-training-launched", owner, watch=True)
    except BaseException as error:
        save(
            ROOT / "watch-failure-v1.json",
            {"status": "failed-preserved-no-retry", "owner": owner, "error": repr(error)},
        )
        status("failed-preserved-no-retry", owner, watch=True, error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "watch", "worker"])
    phase = parser.parse_args().phase
    {"prepare": prepare, "watch": watch, "worker": worker}[phase]()
