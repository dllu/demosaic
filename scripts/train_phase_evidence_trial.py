"""Matched warm-start control/evidence trial;CPU draft precedes CUDA admission.

One additional cached pass compares the phase evidence path at equal budget.
Existing V172 raw weights,Adam history and EMA initialize both arms. The new
parameter starts with an empty Adam history;both endpoints are reviewed in full.
"""

import argparse
import gc
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V178-phase-evidence-trial-v1"
ADMISSION = REPO / ".cache/quality-20261107/V178-phase-evidence-admission-v1"
V175 = REPO / ".cache/quality-20261107/V175-fresh-noise-matching-v2"
ARMS = ["control", "evidence"]
METHODS = {arm: {endpoint: f"V178-{arm}-{endpoint}" for endpoint in ["raw", "EMA"]} for arm in ARMS}


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def progress(name, value):
    path = ROOT / f"{name}-status-v1.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(path)


def own():
    return {"pid": os.getpid(), "created": psutil.Process().create_time()}


def guard(plan):
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def prerequisites(plan, name):
    admission = read(plan["admission"]["path"])
    assert admission["status"].startswith("pass-V178-native-CUDA") and not owner_live(
        admission["owner"]
    )
    required = (
        [] if name == "control-train" else (["control"] if name == "evidence-train" else ARMS)
    )
    for arm in required:
        assert not (ROOT / f"{arm}-train-failure-v1.json").exists()
        result = read(ROOT / f"{arm}-train-result-v1.json")
        assert result["status"].startswith("completed") and not owner_live(result["owner"])


def require_worker_launch(plan, name, owner):
    assert Path(__file__).is_relative_to(Path(plan["work"]))
    prerequisites(plan, name)
    for _ in range(60):
        try:
            if read(ROOT / f"{name}-launch-v1.json")["owner"] == owner:
                return
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(1)
    raise RuntimeError("Worker launch identity is not observable;no CUDA initialized")


def factory(arm, config):
    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail
    from demosaic.late_phase_evidence_matching import LatePhaseEvidenceMatchingDetail

    if arm == "control":
        return LateLocalNoiseMatchingDetail(
            **{k: v for k, v in config.items() if k != "evidence_peaks"}
        )
    if arm == "evidence":
        return LatePhaseEvidenceMatchingDetail(**config)
    raise ValueError(arm)


def draft():
    import torch
    from phase_evidence_training_state import warm_start_matching
    from profile_raw_kernel_inference import model_hash
    from train_local_noise_matching_trial import tree_equal

    assert not ROOT.exists() and not torch.cuda.is_initialized()
    tests = REPO / ".cache/v178-training-state-CPU-tests-v2.log"
    assert "13 passed" in tests.read_text()
    admission_plan = read(ADMISSION / "plan-v1.json")
    baseline = read(V175 / "plan-v1.json")
    for name, digest in baseline["prior_neural_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.4 + 0.2 + 2) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 1.25 + 0.2) * 2**30
    assert psutil.virtual_memory().available > 40 * 2**30
    assert ref(baseline["initial_checkpoint"]["path"]) == baseline["initial_checkpoint"]
    checkpoint = torch.load(
        baseline["initial_checkpoint"]["path"], map_location="cpu", weights_only=True
    )
    proofs = {}
    models = {}
    moments = {}
    emas = {}
    for arm in ARMS:
        model = factory(arm, admission_plan["module_config"])
        optimizer, ema, proof = warm_start_matching(model, checkpoint, lr=1e-4, weight_decay=0.01)
        assert proof["initial_updates"] == 900 and proof["Adam_clocks"]["network"]["steps"] == [
            900.0
        ]
        assert proof["Adam_clocks"]["adapter"]["states"] == 0
        if arm == "evidence":
            assert proof["Adam_clocks"]["adapter"]["tensors"] == 1
        proofs[arm] = dict(
            proof,
            module_hash=model_hash(model),
            trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
            trainable_tensors=sum(p.requires_grad for p in model.parameters()),
            EMA_tensors=len(ema),
        )
        models[arm] = model.state_dict()
        moments[arm] = optimizer.state_dict()["state"]
        emas[arm] = ema
    assert all(
        torch.equal(value, models["evidence"][name]) for name, value in models["control"].items()
    )
    assert tree_equal(moments["control"], moments["evidence"]) and tree_equal(
        moments["control"], checkpoint["optimizer"]["state"]
    )
    assert all(
        torch.equal(value, emas["evidence"][name]) for name, value in emas["control"].items()
    )
    assert proofs["control"]["module_hash"] == baseline["initial_module_hashes"]["raw"]
    assert not torch.cuda.is_initialized()
    ROOT.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    (work / "tests").mkdir()
    for name in ["test_phase_evidence_training_state.py", "test_late_phase_evidence_matching.py"]:
        shutil.copyfile(REPO / "tests" / name, work / "tests" / name)
    artifacts = ROOT / "artifacts"
    artifacts.mkdir()
    for name in ["checkpoints", "native"]:
        (artifacts / name).mkdir()
    plan = {
        "status": "CPU-draft-actual-warmstart-verified-awaiting-CUDA-admission",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "work": str(work),
        "artifacts": str(artifacts),
        "runner": ref(work / "scripts" / Path(__file__).name),
        "renderer": ref(work / "scripts/render_phase_evidence_trial.py"),
        "initial_checkpoint": baseline["initial_checkpoint"],
        "cache": baseline["cache"],
        "pair_units": baseline["pair_units"],
        "training_provenance": baseline["training_provenance"],
        "frozen_component": baseline["frozen_component"],
        "design": baseline["design"],
        "prior_scores": baseline["prior_scores"],
        "metrics_sources": baseline["metrics_sources"],
        "native_cases": baseline["native_cases"],
        "processing_order": baseline["processing_order"],
        "module_config": admission_plan["module_config"],
        "sampling_library": baseline["sampling_library"],
        "steps": 1000,
        "initial_updates": 900,
        "new_updates_per_arm": 900,
        "new_images_per_arm": 3600,
        "ADC_skips_per_arm": 100,
        "lr": 1e-4,
        "warmup": 50,
        "weight_decay": 0.01,
        "gradient_clip": 1.0,
        "EMA_decay": 0.999,
        "domain_weights": baseline["domain_weights"],
        "methods": METHODS,
        "minimum_GiB": {"RAM": 32, "local": 48, "external": 111},
        "launch_RAM_GiB": 52,
        "CUDA_quota_GiB": 24,
        "projected_new_local_GiB": 2.0,
        "projected_new_external_GiB": 0.0,
        "projection_margin_GiB": 0.5,
        "CPU_warmstart_proof": proofs,
        "both_arms_original_moments_and_EMA_exact": True,
        "state_CPU_tests": dict(ref(tests), text=tests.read_text()),
        "admission_expected_root": str(ADMISSION),
        "admission_plan_at_draft": ref(ADMISSION / "plan-v1.json"),
        "expected_quality_counts": {
            "wrapper": 3288,
            "frozen": 3288,
            "network": 3000,
            "sampler": 15000,
            "projection": 1500,
        },
        "scope": "Matched one-pass continuation from actual V172 raw/Adam/EMA at900 updates. Each arm adds900updates/3600images on the same1000 scene/calibration/target/noisy-parent rows;100ADC skips. Control is unchanged local-noise matching;evidence adds80 measured-wave coordinates via3120zero adapter weights. Same seven-term objective,domain weights,row LR schedule and existing141-tensor Adam history. Evidence adapter starts at Adam step0;its EMA starts zero and follows the same whole-model EMA decay. Existing network clocks end1800,newadapter900. No fresh sensor/source/geometry,parent/DINO or RAWdecode work. Atomic sampler backward retains warn-only nondeterminism;not bit-exact retraining or blind validation. All4endpoints/all822quality cases,V169 exact replays,288ADC identities,36full-array native cases,72figures/24triplets and protected GFX scenes/priors/JPEGs. Native pixels/coordinates/displays fixed;ISO100references qualitative,notGT. Actual CUDA admission and plan preparation required before any training. No quality gain claimed by this draft;V175 remains a separate larger fresh-noise recipe.",
    }
    plan["inputs"] = [
        plan[k]
        for k in [
            "initial_checkpoint",
            "cache",
            "pair_units",
            "training_provenance",
            "design",
            "prior_scores",
            "sampling_library",
        ]
    ] + plan["metrics_sources"]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "draft-v1.json", plan)
    print("CPUdraftverified141Adam900plusnew0;all4endpointsplanned;noGPU", flush=True)


def prepare():
    plan = read(ROOT / "draft-v1.json")
    guard(plan)
    assert not (ROOT / "plan-v1.json").exists()
    result_path = ADMISSION / "admission-result-v1.json"
    admission = read(result_path)
    assert admission["status"].startswith("pass-V178-native-CUDA") and not owner_live(
        admission["owner"]
    )
    assert admission["totals"] == {
        "wrapper": 32,
        "frozen": 32,
        "network": 27,
        "sampler": 135,
        "projection": 15,
    }
    assert admission["actual_optimizer_updates"] == 2
    admitted_plan = read(admission["plan"]["path"])
    for path, digest in plan["frozen_files"].items():
        if "/src/demosaic/" in path:
            other = Path(admitted_plan["work"]) / "src/demosaic" / Path(path).name
            assert ref(other)["sha256"] == digest
    # V175 render/quality exists before the separate admission is allowed.
    plan["V175_scores"] = ref(V175 / "scores-v1.json")
    plan["prior_figures"] = ref(V175 / "figures-v1.json")
    plan["admission"] = ref(result_path)
    plan["inputs"] += [
        plan["V175_scores"],
        plan["prior_figures"],
        plan["admission"],
        ref(ROOT / "draft-v1.json"),
    ]
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 2) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5) * 2**30
    assert psutil.virtual_memory().available > 52 * 2**30
    plan["status"] = "prepared-matched-control-evidence-native-trial-after-actual-CUDA-admission"
    save(ROOT / "plan-v1.json", plan)
    print("Prepared900additionalupdatesperarm;all4endpoints822cases", flush=True)


def resources(plan, name, owner):
    while True:
        available = {
            "RAM": psutil.virtual_memory().available,
            "local": shutil.disk_usage(REPO).free,
            "external": shutil.disk_usage("/mnt/external").free,
        }
        if all(available[k] > v * 2**30 for k, v in plan["minimum_GiB"].items()):
            return
        progress(
            name,
            {"status": "waiting-before-next-forward", "owner": owner, "available_bytes": available},
        )
        time.sleep(2)


def runtime(plan):
    import torch

    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
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


def instrument(module, counts):
    for name, child in [
        ("wrapper", module),
        ("frozen", module.frozen),
        ("network", module.network),
    ]:
        child.register_forward_pre_hook(
            lambda *args, name=name: counts.__setitem__(name, counts[name] + 1)
        )
    for child in module.network.modules():
        if type(child).__name__ == "NonlocalBlock":
            child.register_forward_pre_hook(
                lambda *args: counts.__setitem__("sampler", counts["sampler"] + 1)
            )
    if hasattr(module, "phase_evidence_in"):
        module.phase_evidence_in.register_forward_pre_hook(
            lambda *args: counts.__setitem__("projection", counts["projection"] + 1)
        )
    return module


def train(arm):
    import numpy as np
    import torch
    from nonlocal_residual_objective import objective
    from phase_evidence_training_state import (
        adam_clocks,
        matching_parameters,
        restore_matching_state,
        update_matching_ema,
        warm_start_matching,
    )
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    name = arm + "-train"
    owner = own()
    require_worker_launch(plan, name, owner)
    (ROOT / f"{name}.claim").open("x").close()
    runtime(plan)
    counts = {k: 0 for k in ["wrapper", "frozen", "network", "sampler", "projection"]}
    initial = torch.load(plan["initial_checkpoint"]["path"], map_location="cpu", weights_only=True)
    module = instrument(factory(arm, plan["module_config"]).cuda(), counts)
    optimizer, ema, warmstart = warm_start_matching(
        module, initial, lr=plan["lr"], weight_decay=plan["weight_decay"]
    )
    del initial
    save(ROOT / f"{arm}-warmstart-v1.json", warmstart)
    frozen = model_hash(module.frozen)
    assert frozen == plan["frozen_component"]["module_hash"]
    CPU_RNG, CUDA_RNG = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    rows = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    updates = skipped = images = 0
    trace = []
    checkpoints = []
    restoration = None
    maximum = {name: 0.0 for name in matching_parameters(module)}
    with (ROOT / f"{arm}-train-trace-v1.jsonl").open("x") as journal:
        for step, item in enumerate(rows, 1):
            resources(plan, name, owner)
            assert (
                ref(item["arrays"]["path"]) == item["arrays"]
                and ref(item["parent"]["path"]) == item["parent"]
            )
            arrays = dict(np.load(item["arrays"]["path"], allow_pickle=False))
            parent = np.load(item["parent"]["path"], allow_pickle=False)
            assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"] and fingerprint(
                parent
            ) == item["parent_values"]
            assert units[step - 1]["step"] == step and units[step - 1]["batch"] == item["arrays"]
            p = max(0, step - plan["warmup"]) / (plan["steps"] - plan["warmup"])
            lr = (
                plan["lr"]
                * min(1, step / plan["warmup"])
                * (0.1 + 0.9 * (1 + math.cos(math.pi * p)) / 2)
            )
            row = {
                "step": step,
                "batch": item["arrays"],
                "parent": item["parent"],
                "domain": item["metadata"]["domain"],
                "noisy": bool(np.any(arrays["variance"] > 0)),
                "lr": lr,
            }
            if row["noisy"]:
                batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
                base = torch.from_numpy(parent).cuda()
                pair_units = torch.tensor(
                    units[step - 1]["candidate_units_FP32"], device="cuda", dtype=torch.float32
                ).reshape(-1, 1, 1, 1)
                optimizer.zero_grad(set_to_none=True)
                for group in optimizer.param_groups:
                    group["lr"] = lr
                output, aux = module(
                    base,
                    *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                    return_aux=True,
                )
                loss, terms, mask = objective(
                    output,
                    aux["frozen_output"],
                    batch,
                    pair_units,
                    plan["domain_weights"][row["domain"]],
                )
                assert torch.isfinite(loss)
                loss.backward()
                zero = []
                for key, parameter in matching_parameters(module).items():
                    assert parameter.grad is not None and torch.isfinite(parameter.grad).all(), key
                    maximum[key] = max(maximum[key], float(parameter.grad.abs().max()))
                    if parameter.grad.count_nonzero() == 0:
                        zero.append(key)
                assert not any(p.grad is not None for p in module.frozen.parameters())
                norm = torch.nn.utils.clip_grad_norm_(
                    matching_parameters(module).values(),
                    plan["gradient_clip"],
                    error_if_nonfinite=True,
                )
                optimizer.step()
                updates += 1
                images += len(base)
                decay = update_matching_ema(
                    module,
                    ema,
                    total_updates=plan["initial_updates"] + updates,
                    maximum_decay=plan["EMA_decay"],
                )
                row.update(
                    loss=float(loss.detach()),
                    terms={k: float(v.detach()) for k, v in terms.items()},
                    gradient_norm=float(norm),
                    zero_gradient_tensors=zero,
                    flat_mask=fingerprint(mask.cpu().numpy()),
                    flat_eligible_pixels=int(mask.sum()),
                    correction_RMS_DN16=float(aux["correction"].detach().square().mean().sqrt())
                    * 65535,
                    EMA_decay=decay,
                )
                del batch, base, pair_units, output, aux, loss, terms, mask
            else:
                skipped += 1
                row["skipped"] = "zero variance;no matching,projection or optimizer call"
            assert model_hash(module.frozen) == frozen
            row.update(
                updates=updates,
                total_network_updates=plan["initial_updates"] + updates,
                counts=dict(counts),
            )
            trace.append(row)
            journal.write(json.dumps(row, allow_nan=False) + "\n")
            journal.flush()
            if step == 1 or step % 10 == 0:
                progress(
                    name,
                    {
                        "status": "training",
                        "owner": owner,
                        "arm": arm,
                        "step": step,
                        "updates": updates,
                        "counts": counts,
                        "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                    },
                )
            if step in [8, 250, 500, 750, 1000]:
                clocks = adam_clocks(module, optimizer)
                assert clocks["network"]["steps"] == [float(plan["initial_updates"] + updates)]
                assert clocks["adapter"]["steps"] == ([float(updates)] if arm == "evidence" else [])
                checkpoint = Path(plan["artifacts"]) / "checkpoints" / f"{arm}-step{step:04d}.pt"
                payload = {
                    "models": module.state_dict(),
                    "ema": ema,
                    "optimizer": optimizer.state_dict(),
                    "arm": arm,
                    "module_config": plan["module_config"],
                    "step": step,
                    "updates": updates,
                    "initial_updates": plan["initial_updates"],
                    "CPU_RNG": torch.get_rng_state(),
                    "CUDA_RNG": torch.cuda.get_rng_state(),
                    "counts": dict(counts),
                    "plan": ref(ROOT / "plan-v1.json"),
                }
                with checkpoint.open("xb") as stream:
                    torch.save(payload, stream)
                checkpoints.append(ref(checkpoint))
                del payload
                if step == 8:
                    before = model_hash(module)
                    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
                    del module, optimizer
                    gc.collect()
                    module = instrument(factory(arm, plan["module_config"]).cuda(), counts)
                    optimizer, ema, restoration = restore_matching_state(
                        module, saved, lr=plan["lr"], weight_decay=plan["weight_decay"]
                    )
                    assert model_hash(module) == before
                    restoration.update(
                        checkpoint=ref(checkpoint), continued_at_row=9, repeated_prefix_forwards=0
                    )
                    save(ROOT / f"{arm}-restoration-v1.json", restoration)
                    del saved
            del arrays, parent
    assert len(trace) == 1000 and updates == 900 and skipped == 100 and images == 3600
    assert counts == {
        "wrapper": 900,
        "frozen": 900,
        "network": 900,
        "sampler": 4500,
        "projection": 900 if arm == "evidence" else 0,
    }
    assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
        CUDA_RNG, torch.cuda.get_rng_state()
    )
    if arm == "evidence":
        assert maximum["phase_evidence_in.weight"] > 0
    assert any(value > 0 for key, value in maximum.items() if key.startswith("network."))
    guard(plan)
    save(
        ROOT / f"{arm}-train-result-v1.json",
        {
            "status": "completed-matched-warmstart-one-pass",
            "owner": owner,
            "arm": arm,
            "plan": ref(ROOT / "plan-v1.json"),
            "trace": trace,
            "checkpoints": checkpoints,
            "final_checkpoint": checkpoints[-1],
            "updates": updates,
            "skipped_ADC": skipped,
            "training_images": images,
            "counts": counts,
            "initial_updates": 900,
            "final_Adam_clocks": adam_clocks(module, optimizer),
            "restoration": restoration,
            "frozen_module_hash": frozen,
            "frozen_unchanged": True,
            "RNG_unchanged": True,
            "parameter_maximum_gradients": maximum,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "new_parent_DINO_forwards": 0,
            "new_noise_source_draws": 0,
            "scope": plan["scope"],
        },
    )
    progress(
        name,
        {
            "status": "completed-training",
            "owner": owner,
            "arm": arm,
            "step": 1000,
            "updates": 900,
            "counts": counts,
        },
    )


def review():
    import numpy as np
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from phase_evidence_training_state import load_matching_ema
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    owner = own()
    require_worker_launch(plan, "review", owner)
    (ROOT / "review.claim").open("x").close()
    runtime(plan)
    expected = {
        r["id"]: r
        for r in read(plan["prior_scores"]["path"])["rows"]
        if r["method"] == "balanced-EMA"
    }
    assert len(expected) == 822
    metric = DetailMetrics(plan["metrics_sources"])
    design = read(plan["design"]["path"])["observations"]
    counts = {k: 0 for k in ["wrapper", "frozen", "network", "sampler", "projection"]}
    rows = []
    native = {}
    weights = {}
    checkpoints = {}
    replays = ADC_exact = closure_channels = 0
    CPU_RNG, CUDA_RNG = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    with (
        (ROOT / "quality-events-v1.jsonl").open("x") as events,
        (ROOT / "quality-observations-v1.jsonl").open("x") as journal,
    ):
        for arm in ARMS:
            training = read(ROOT / f"{arm}-train-result-v1.json")
            assert training["frozen_unchanged"] and training["RNG_unchanged"]
            checkpoints[arm] = training["final_checkpoint"]
            assert ref(checkpoints[arm]["path"]) == checkpoints[arm]
            state = torch.load(checkpoints[arm]["path"], map_location="cpu", weights_only=True)
            for endpoint in ["raw", "EMA"]:
                method = METHODS[arm][endpoint]
                module = instrument(factory(arm, plan["module_config"]).cuda(), counts).eval()
                module.load_state_dict(state["models"], strict=True)
                if endpoint == "EMA":
                    load_matching_ema(module, state["ema"])
                before = model_hash(module)
                weights[method] = {"before": before, "frozen": model_hash(module.frozen)}
                assert weights[method]["frozen"] == plan["frozen_component"]["module_hash"]
                for ordinal, index in enumerate(plan["processing_order"]):
                    resources(plan, "review", owner)
                    case = design[index]
                    assert (
                        ref(case["arrays"]["path"]) == case["arrays"]
                        and ref(case["parent"]["path"]) == case["parent"]
                    )
                    arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
                    base = np.load(case["parent"]["path"], allow_pickle=False)
                    batch = {
                        k: torch.from_numpy(arrays[k]).cuda()
                        for k in ["packed", "variance", "colors", "wb"]
                    }
                    with torch.inference_mode():
                        output, aux = module(
                            torch.from_numpy(base).cuda(),
                            *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                            return_aux=True,
                        )
                    torch.cuda.synchronize()
                    value = output.cpu().numpy()
                    frozen = aux["frozen_output"].cpu().numpy()
                    correction = aux["correction"].cpu().numpy()
                    assert fingerprint(frozen) == expected[case["id"]]["values"]
                    replays += 1
                    np.testing.assert_array_equal(value, frozen + correction)
                    closure_channels += value.size
                    if not aux["matching_evaluated"]:
                        assert np.array_equal(value, frozen) and not np.any(arrays["variance"])
                        ADC_exact += 1
                    row = metric.measure(case, arrays, base, value)
                    row.update(
                        method=method,
                        index=index,
                        values=fingerprint(value),
                        frozen_values=fingerprint(frozen),
                        frozen_replay_exact=True,
                        ADC_exact=not aux["matching_evaluated"],
                        nonlocal_correction_values=fingerprint(correction),
                        nonlocal_correction_RMS_DN16=float(
                            np.sqrt(np.mean(correction.astype(np.float64) ** 2))
                        )
                        * 65535,
                    )
                    if case["id"] in plan["native_cases"]:
                        for label, array in [(method, value), (method + "-correction", correction)]:
                            path = Path(plan["artifacts"]) / "native" / f"{label}-{index:03d}.npy"
                            assert not path.exists()
                            np.save(path, array, allow_pickle=False)
                            native.setdefault(case["id"], {})[label] = ref(path)
                        row["prediction"] = native[case["id"]][method]
                    rows.append(row)
                    evidence = None
                    if arm == "evidence" and aux["phase_evidence"] is not None:
                        evidence = {
                            k: v.detach().cpu().tolist() for k, v in aux["phase_evidence"].items()
                        }
                    record = {
                        "method": method,
                        "index": index,
                        "id": case["id"],
                        "arrays": case["arrays"],
                        "parent": case["parent"],
                        "inputs": {k: fingerprint(arrays[k]) for k in batch},
                        "row": row,
                        "evidence": evidence,
                        "frozen_replay_exact": True,
                        "closure_exact": True,
                    }
                    journal.write(json.dumps(record, allow_nan=False) + "\n")
                    journal.flush()
                    events.write(
                        json.dumps(
                            {
                                "method": method,
                                "index": index,
                                "ordinal": ordinal,
                                "id": case["id"],
                                "counts": dict(counts),
                                "matching_evaluated": aux["matching_evaluated"],
                            }
                        )
                        + "\n"
                    )
                    events.flush()
                    if ordinal % 16 == 0:
                        progress(
                            "review",
                            {
                                "status": "reviewing",
                                "owner": owner,
                                "method": method,
                                "index": index,
                                "counts": counts,
                                "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                            },
                        )
                    del arrays, base, batch, output, aux, value, frozen, correction, evidence
                assert model_hash(module) == before
                weights[method]["after"] = model_hash(module)
                del module
            del state
    assert (
        counts == plan["expected_quality_counts"]
        and len(rows) == 3288
        and len(native) == 36
        and replays == 3288
        and ADC_exact == 288
    )
    assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
        CUDA_RNG, torch.cuda.get_rng_state()
    )
    rows.sort(key=lambda r: (r["index"], r["method"]))
    guard(plan)
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-four-endpoint-fixed-quality-awaiting-native-viewing",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "checkpoints": checkpoints,
            "rows": rows,
            "summary": summarize(rows),
            "counts": counts,
            "native_predictions": native,
            "module_hashes": weights,
            "weights_unchanged": True,
            "RNG_unchanged": True,
            "exact_V169_replays": replays,
            "ADC_outputs_exact_V169": ADC_exact,
            "independent_inprocess_addition_channels": closure_channels,
            "new_parent_DINO_forwards": 0,
            "new_source_noise_draws": 0,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": plan["scope"],
        },
    )
    progress(
        "review",
        {
            "status": "completed-quality-awaiting-render-and-viewing",
            "owner": owner,
            "counts": counts,
        },
    )


def launch(phase):
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert phase in ["train-control", "train-evidence", "review"]
    name = phase.removeprefix("train-") + "-train" if phase.startswith("train-") else phase
    prerequisites(plan, name)
    assert not (ROOT / f"{name}-launch-v1.json").exists() and not (ROOT / f"{name}.claim").exists()
    if phase == "train-evidence":
        result = read(ROOT / "control-train-result-v1.json")
        assert result["status"].startswith("completed") and not owner_live(result["owner"])
    if phase == "review":
        for arm in ARMS:
            result = read(ROOT / f"{arm}-train-result-v1.json")
            assert result["status"].startswith("completed") and not owner_live(result["owner"])
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"] * 2**30
    env = dict(
        os.environ,
        PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    command = [str(REPO / ".venv/bin/python"), plan["runner"]["path"], phase]
    with (ROOT / f"{name}-v1.log").open("xb") as log:
        child = subprocess.Popen(
            command,
            cwd=REPO,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        save(
            ROOT / f"{name}-launch-v1.json",
            {
                "owner": {"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
                "command": command,
                "plan": ref(ROOT / "plan-v1.json"),
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=[
            "draft",
            "prepare",
            "train-control",
            "train-evidence",
            "review",
            "launch-control",
            "launch-evidence",
            "launch-review",
        ],
    )
    phase = parser.parse_args().phase
    try:
        if phase == "draft":
            draft()
        elif phase == "prepare":
            prepare()
        elif phase.startswith("launch-"):
            launch(
                "train-" + phase.removeprefix("launch-") if phase != "launch-review" else "review"
            )
        elif phase == "review":
            review()
        else:
            train(phase.removeprefix("train-"))
    except BaseException as error:
        if phase in ["train-control", "train-evidence", "review"] and ROOT.exists():
            name = phase.removeprefix("train-") + "-train" if phase.startswith("train-") else phase
            path = ROOT / f"{name}-failure-v1.json"
            if not path.exists():
                save(
                    path,
                    {
                        "status": "failed-preserved-no-automatic-retry",
                        "owner": own(),
                        "error": repr(error),
                        "source": ref(__file__),
                    },
                )
        raise


if __name__ == "__main__":
    main()
