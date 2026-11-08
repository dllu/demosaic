"""Admit V180 local phase evidence on CUDA after completed V178 publication.

Separate immutable worker; old admission/trial/model sources remain unchanged.
Two fresh-Adam probe updates are not training or a restored-quality result.
"""

import argparse
import gc
import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V180-local-phase-admission-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V180-local-phase-admission-v1")
DEPENDENCY = REPO / ".cache/quality-20261107/V178-phase-evidence-trial-v1"


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
    assert ref(__file__) == plan["runner"], "Use the sealed admission entry"
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def dependency_readiness(root):
    """Use the actual sealed V178 publication gate before importing Torch."""
    root = Path(root)
    if root != DEPENDENCY:
        raise ValueError("Expected the actual completed matched trial")
    source = root / "publication-work-v1/scripts/publish_phase_evidence_trial.py"
    seal = read(root / "publication-source-v1.json")
    assert ref(source) == seal["publisher"]
    spec = importlib.util.spec_from_file_location("completed_v178_publication_gate", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.completed_context(root, viewed=True)
    index_path = REPO / "docs/results/v178-phase-evidence-final-v1.json"
    verification_path = REPO / "docs/results/v178-phase-evidence-publication-verification-v1.json"
    final, verification = read(index_path), read(verification_path)
    assert (
        verification["status"]
        == "pass-exact-evidence-four-exports-matched-tables-native-and-browser-pixels"
    )
    assert verification["publication"] == ref(index_path)
    for key in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[key]["path"]) == final[key]
    return {
        "ready": True,
        "reason": "actual-V178-terminal-audited-viewed-and-published",
        "publication": ref(index_path),
        "verification": ref(verification_path),
        "matched_gate": ref(source),
        "scope": "Checks the actual completed V178 publication; historical guide hashes may evolve. No Torch/CUDA initialization or checkpoint load.",
    }


def prepare():
    assert not ROOT.exists() and not EXTERNAL.exists()
    proof = dependency_readiness(DEPENDENCY)
    prior_path = REPO / ".cache/quality-20261107/V180-local-phase-preparation-v1/result-v1.json"
    prior = read(prior_path)
    assert (
        prior["status"]
        == "completed-native-CPU-local-feature-and-strict-state-preparation-not-quality"
    )
    cpu_plan = read(prior["plan"]["path"])
    for binding in cpu_plan["sources"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
    for name, digest in cpu_plan["prior97_neural_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    local_source = next(
        b
        for b in cpu_plan["sources"]
        if b["path"].endswith("/src/demosaic/late_local_phase_evidence_matching.py")
    )
    assert (
        ref(REPO / "src/demosaic/late_local_phase_evidence_matching.py")["sha256"]
        == local_source["sha256"]
    )
    assert len(list((REPO / "src/demosaic").glob("*.py"))) == 98
    old_path = ROOT.parent / "V178-phase-evidence-admission-v1/plan-v1.json"
    old = read(old_path)
    tests = REPO / ".cache/v180-local-phase-CPU-tests-v2.log"
    assert "112 passed" in tests.read_text()
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.2) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 0.2) * 2**30
    assert psutil.virtual_memory().available > 52 * 2**30
    ROOT.mkdir()
    EXTERNAL.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    (work / "tests").mkdir()
    for name in ["test_phase_admission_protocol.py", "test_late_local_phase_evidence_matching.py"]:
        shutil.copyfile(REPO / "tests" / name, work / "tests" / name)
    plan = {
        k: v for k, v in old.items() if k not in ["frozen_files", "inputs", "protocol_CPU_tests"]
    }
    plan.update(
        created_unix_UTC=time.time(),
        dependency_root=str(DEPENDENCY),
        root=str(ROOT),
        external=str(EXTERNAL),
        work=str(work),
        runner=ref(work / "scripts" / Path(__file__).name),
        CPU_preparation=ref(prior_path),
        module_config=cpu_plan["config"],
        component="LateLocalPhaseEvidenceMatchingDetail",
        operator_source=ref(work / "src/demosaic/late_local_phase_evidence_matching.py"),
        prior_admission_protocol=ref(REPO / "scripts/admit_phase_evidence_matching.py"),
        prior_admission_plan=ref(old_path),
        completed_V178_dependency=proof,
        protocol_CPU_tests=dict(ref(tests), text=tests.read_text()),
        new_local_projection_GiB=0.2,
        new_external_projection_GiB=0.2,
        local_center_power_tolerance={"rtol": 1e-8, "atol": 1e-8},
        scope="V180 local phase CUDA implementation probe only,after V178 terminal/audited/actually viewed/publication verification. Same seven cached cases and zero-adapter V172 compatibility controls;four training domains plus ADC,protected sky/cab evaluation only.32 component/frozen,27 matching,135 sampler,15 new projections;CPU/GPU features and local center power/geometry checked;two fresh-Adam updates mesh then mixed with genuine model/Adam/CPU-CUDA RNG restoration between. No repeated prefix,no fresh sensor/source,parent/DINO or RAW decode. No quality claim or automatic training launch. Protected captures/JPEGs/siblings remain excluded from optimizer updates. Local interpolation changes covariance and may spread support or create seams.",
    )
    plan["inputs"] = [
        ref(DEPENDENCY / "plan-v1.json"),
        plan["checkpoint"],
        plan["sampling_library"],
        plan["pair_units"],
        plan["CPU_preparation"],
        ref(prior["plan"]["path"]),
        ref(old_path),
        proof["publication"],
        proof["verification"],
    ]
    for case in plan["cases"]:
        plan["inputs"].extend([case["arrays"], case["parent"]])
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "plan-v1.json", plan)
    print(
        "PreparedV18032calls27matching135samplers2probeupdates;actualV178dependencyverified",
        flush=True,
    )


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
        from demosaic.late_local_phase_evidence_matching import (
            LateLocalPhaseEvidenceMatchingDetail,
            local_phase_evidence_maps,
        )

        def phase_evidence_maps(*args):
            return local_phase_evidence_maps(
                *args,
                peaks=plan["module_config"]["evidence_peaks"],
                window=plan["module_config"]["evidence_window"],
                stride=plan["module_config"]["evidence_stride"],
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
                **{k: v for k, v in plan["module_config"].items() if k in ["width", "max_search"]}
            )
            .cuda()
            .eval()
        )
        new = LateLocalPhaseEvidenceMatchingDetail(**plan["module_config"]).cuda().eval()
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
                        gpu_metadata = aux["phase_evidence"]
                        for key in [
                            "centers_y",
                            "centers_x",
                            "boxes_xywh",
                            "green_phase_indices",
                            "valid",
                        ]:
                            assert torch.equal(gpu_metadata[key].cpu(), reference_aux[key]), key
                        center_delta = (
                            gpu_metadata["local_center_power"].cpu()
                            - reference_aux["local_center_power"]
                        )
                        torch.testing.assert_close(
                            gpu_metadata["local_center_power"].cpu(),
                            reference_aux["local_center_power"],
                            **plan["local_center_power_tolerance"],
                        )
                        row["local_center_powers_checked"] = center_delta.numel()
                        row["local_center_power_maximum_difference"] = float(
                            center_delta.abs().max()
                        )
                        row["local_geometry_exact_CPU_GPU"] = True
                        del center_delta, gpu_metadata
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
                "component": "LateLocalPhaseEvidenceMatchingDetail",
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
                new = LateLocalPhaseEvidenceMatchingDetail(**plan["module_config"]).cuda().train()
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
                before["global_nominal_power"][:, 0, :, 0],
                after["global_nominal_power"][:, 0, :, 0],
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
            "status": "pass-V180-native-CUDA-initial-parity-real-gradients-restoration-and-local-ADC-invariants",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "component": plan["component"],
            "module_config": plan["module_config"],
            "operator_source": plan["operator_source"],
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
        print("PASSV180CUDAadmission;noqualityortraininglaunch", flush=True)
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
