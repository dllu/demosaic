"""Continue V172 with fresh physical noise and exact new frozen-parent outputs.

Nine further passes retain scene/calibration/target and seven-term supervision.
The 897 eligible noisy rows per pass get fresh coupled/ordinary sensor noise;
three clipped photo rows retain their exact cached inputs/parents. A longer,
reheated learning-rate schedule is a joint training-recipe test, not a claim
that budget and noise diversity have been independently isolated.
"""

import argparse
import copy
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V175-fresh-noise-matching-v2"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V175-fresh-noise-matching-v2")


def prepare():
    import ast

    import torch
    from balanced_spatial_metrics import DetailMetrics
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail

    assert not (ROOT / "plan-v1.json").exists() and not EXTERNAL.exists()
    prior_root = REPO / ".cache/quality-20261107/V174-spread-matching-v1"
    prior = read(prior_root / "plan-v1.json")
    guard(prior)
    reference_path = REPO / ".cache/quality-20261107/V172-local-noise-matching-v1/plan-v1.json"
    reference = read(reference_path)
    initial_training = read(reference_path.with_name("train-result-v1.json"))
    initial_checkpoint = initial_training["final_checkpoint"]
    assert ref(initial_checkpoint["path"]) == initial_checkpoint
    eligibility_path = ROOT / "clean-sensor-preflight-v2.json"
    eligibility = read(eligibility_path)
    assert (
        eligibility["cache"] == reference["cache"]
        and eligibility["pair_units"] == reference["pair_units"]
    )
    assert eligibility["fresh_noise_eligible_noisy_rows_per_pass"] == 897
    assert [r["step"] for r in eligibility["rows"] if not r["fresh_noise_eligible"]] == [
        65,
        358,
        543,
    ]
    assert "54 passed" in (REPO / ".cache/v175-renoise-CPU-tests-v2.log").read_text()
    initial = torch.load(initial_checkpoint["path"], map_location="cpu", weights_only=True)
    assert (
        initial["updates"] == 900
        and initial["skipped"] == 100
        and len(initial["optimizer"]["state"]) == 141
    )
    assert all(float(s["step"]) == 900 for s in initial["optimizer"]["state"].values())
    module = LateLocalNoiseMatchingDetail(**reference["module_config"])
    module.load_state_dict(initial["models"], strict=True)
    scores = read(reference_path.with_name("scores-v1.json"))
    assert model_hash(module) == scores["module_hashes"]["raw"]["before"]
    raw_hash = model_hash(module)
    module.network.load_state_dict(initial["ema"], strict=True)
    assert model_hash(module) == scores["module_hashes"]["EMA"]["before"]
    parent_data = read(reference["training_provenance"]["path"])
    assert ref(parent_data["parent"]["path"]) == {
        k: parent_data["parent"][k] for k in ["path", "sha256"]
    }
    assert shutil.disk_usage(REPO).free > (48 + 0.2 + 0.5) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 1.25 + 0.5) * 2**30
    protocol = ROOT / "original-protocol-v1.md"
    assert not protocol.exists()
    shutil.copyfile(REPO / "docs/fresh-noise-matching.md", protocol)
    work = ROOT / "work"
    assert not work.exists()
    shutil.copytree(prior["work"], work)
    names = [
        "train_fresh_noise_matching_trial.py",
        "render_fresh_noise_matching_trial.py",
        "renoise_cached_training.py",
        "preflight_renoise_training.py",
        "coupled_sensor_noise.py",
    ]
    for name in names:
        shutil.copyfile(REPO / "scripts" / name, work / "scripts" / name)
    shutil.copyfile(
        REPO / "tests/test_renoise_cached_training.py",
        work / "tests/test_renoise_cached_training.py",
    )
    prior_neural = prior["prior_neural_hashes"]
    assert len(prior_neural) == 96 and all(
        ref(REPO / "src/demosaic" / n)["sha256"] == h for n, h in prior_neural.items()
    )
    plan = copy.deepcopy(prior)
    for name in [
        "offset_initializer",
        "offset_grid_spacing",
        "baseline_offset_diagnostic",
        "matched_V172_recipe",
    ]:
        plan.pop(name, None)
    plan.update(
        root=str(ROOT),
        work=str(work),
        external=str(EXTERNAL),
        runner=ref(work / "scripts" / Path(__file__).name),
        renderer=ref(work / "scripts/render_fresh_noise_matching_trial.py"),
        steps=10000,
        continuation_rows=9000,
        initial_optimizer_updates=900,
        expected_new_updates=8100,
        expected_total_updates=9000,
        expected_new_ADC_skips=900,
        expected_new_training_images=32400,
        expected_fresh_noise_batches=8073,
        expected_retained_cached_noisy_batches=27,
        expected_new_training_parent_DINO_roots=8073,
        expected_parent_runtime_replays=2,
        lr=0.0001,
        warmup=100,
        EMA_decay=reference["EMA_decay"],
        domain_weights=reference["domain_weights"],
        minimum_GiB={"RAM": 32, "local": 48, "external": 111},
        launch_RAM_GiB=52,
        projected_remaining_external_GiB=1.25,
        projected_remaining_local_GiB=0.2,
        projection_margin_GiB=0.5,
        initial_checkpoint=initial_checkpoint,
        initial_module_hashes={"raw": raw_hash, "EMA": model_hash(module)},
        initial_training=ref(reference_path.with_name("train-result-v1.json")),
        reference_V172_plan=ref(reference_path),
        clean_sensor_preflight=ref(eligibility_path),
        failed_preflight=ref(ROOT / "failed-clean-sensor-preflight-v1.json"),
        failed_CPU_preparation=ref(ROOT / "failed-CPU-preparation-v1.json"),
        prior_worker_import_rejection=ref(ROOT / "prior-worker-import-rejection-v1.json"),
        full_parent=parent_data["parent"],
        expected_DINO_sha256=parent_data["expected_DINO_sha256"],
        expected_parent_module_hash=read(reference["cache"]["path"])["parent_before"],
        prior_figures=ref(prior_root / "figures-v1.json"),
        baseline_scores=ref(reference_path.with_name("scores-v1.json")),
        spread_scores=ref(prior_root / "scores-v1.json"),
        methods=["V175-raw", "V175-EMA"],
        CPU_tests=ref(REPO / ".cache/v175-renoise-CPU-tests-v2.log"),
        inherited_matching_admission=reference["admission"],
        original_protocol=ref(protocol),
        scope="V175 continuation from V172 raw model/Adam/EMA at900 updates;unchanged96 neural sources,2.09M network,local physical units,frozen V169/V143-DINO and exact seven-term objective. Nine further passes over1000 retained scene/calibration/target rows:897 fresh sensor realizations per pass,3 clipped photo rows retain exact cached noisy inputs/parents,100 ADC rows skip.8073 fresh batches recompute exact frozen V143/DINO parent;27 noisy cached batches reuse their own exact parents.8100 new optimizer updates/32400 images;total9000 updates/36000 images including V172. Learning rate reheats to1e-4 with100-row warmup/cosine to1e-5. This jointly changes training budget/noise realizations/LR,not an isolated mechanism proof. No new source/camera/geometry renders or original/dataz reads. All targets/pair information stay training-only. Global RNG unchanged through local stateless CPU noise seeds;real step1008 model/Adam/EMA/RNG restoration without prefix replay. Both endpoints/all822 fixed cached quality inputs/36 full-array cases/60 native figures/12 triplets,protected GFX scenes/priors/windows/JPEGs;real references qualitative,notGT. Six existing EMA quality forwards capture30 offset fields,not causal influence. No blind generalization,noisy-flat guarantee or full-frame timing claim.",
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    plan["inputs"] = [
        plan["original_protocol"],
        initial_checkpoint,
        plan["initial_training"],
        plan["reference_V172_plan"],
        plan["clean_sensor_preflight"],
        plan["failed_preflight"],
        plan["failed_CPU_preparation"],
        plan["prior_worker_import_rejection"],
        plan["full_parent"],
        plan["CPU_tests"],
        reference["cache"],
        reference["pair_units"],
        prior["design"],
        prior["prior_scores"],
        plan["prior_figures"],
        plan["baseline_scores"],
        plan["spread_scores"],
        reference["admission"],
        prior["sampling_library"],
    ]

    def functions(path):
        return {
            n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(Path(path).read_text()).body
            if isinstance(n, ast.FunctionDef)
        }

    old, new = functions(prior["runner"]["path"]), functions(plan["runner"]["path"])
    assert all(old[k] == new[k] for k in ["resources", "runtime", "tree_equal"])
    old_review = old["review"].replace("V174-", "V175-")
    assert old_review == new["review"]
    EXTERNAL.mkdir()
    for name in ["checkpoints", "native", "offsets", "training-prefix"]:
        (EXTERNAL / name).mkdir()
    save(ROOT / "plan-v1.json", plan)
    guard(plan)
    metric = DetailMetrics(plan["metrics_sources"])
    assert metric is not None and not torch.cuda.is_initialized()
    sources = [REPO / "scripts" / n for n in names] + [
        REPO / "tests/test_renoise_cached_training.py"
    ]
    save(
        REPO / "docs/results/v175-fresh-noise-matching-preparation-v2.json",
        {
            "status": "prepared-from-verified-V172-state-and-all1000-scene-bindings-quality-unmeasured",
            "plan": dict(ref(ROOT / "plan-v1.json"), contents=plan),
            "preflight": dict(ref(eligibility_path), contents=eligibility),
            "failed_preflight": dict(
                ref(ROOT / "failed-clean-sensor-preflight-v1.json"),
                contents=read(ROOT / "failed-clean-sensor-preflight-v1.json"),
            ),
            "failed_CPU_preparation": dict(
                ref(ROOT / "failed-CPU-preparation-v1.json"),
                contents=read(ROOT / "failed-CPU-preparation-v1.json"),
            ),
            "prior_worker_import_rejection": dict(
                ref(ROOT / "prior-worker-import-rejection-v1.json"),
                contents=read(ROOT / "prior-worker-import-rejection-v1.json"),
            ),
            "CPU_tests": dict(
                ref(plan["CPU_tests"]["path"]), text=Path(plan["CPU_tests"]["path"]).read_text()
            ),
            "source_texts": [dict(ref(p), text=p.read_text()) for p in sources],
            "unchanged_neural_files": 96,
            "new_matching_admission_forwards": 0,
            "scope": plan["scope"],
        },
    )
    save(
        ROOT / "metric-runtime-readiness-v1.json",
        {
            "status": "prepared-awaiting-frozen-worker-CPU-check",
            "scope": "Unchanged V174 quality function except explicit V175 method labels;unchanged metric sources and inherited native graph admission. Fresh-noise CPU and all-scene preflight pass;two actual parent replays still required before training.",
        },
    )
    assert not torch.cuda.is_initialized()
    print(
        "Prepared V175:8073 fresh batches+27 cached;8100 further updates;no new neural work",
        flush=True,
    )


def check(plan):
    """Execute actual frozen-worker imports and CPU checkpoint loads."""
    import torch
    from balanced_spatial_metrics import DetailMetrics
    from nonlocal_residual_objective import objective
    from profile_raw_kernel_inference import model_hash
    from renoise_cached_training import renoise

    from demosaic.inference import load_checkpoint
    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail

    assert objective is not None and renoise is not None
    metric = DetailMetrics(plan["metrics_sources"])
    assert metric is not None
    checkpoint = torch.load(
        plan["initial_checkpoint"]["path"], map_location="cpu", weights_only=True
    )
    module = LateLocalNoiseMatchingDetail(**plan["module_config"])
    module.load_state_dict(checkpoint["models"], strict=True)
    assert model_hash(module) == plan["initial_module_hashes"]["raw"]
    with torch.random.fork_rng(devices=[]):
        parent, loaded = load_checkpoint(plan["full_parent"]["path"], "cpu")
    assert loaded["loaded_sha256"] == plan["full_parent"]["sha256"]
    assert model_hash(parent) == plan["expected_parent_module_hash"]
    assert model_hash(parent.context.backbone) == plan["expected_DINO_sha256"]
    guard(plan)
    assert not torch.cuda.is_initialized()
    save(
        ROOT / "metric-runtime-readiness-v1.json",
        {
            "status": "pass-before-training-launch",
            "runner": ref(__file__),
            "parent_checkpoint": plan["full_parent"],
            "matching_checkpoint": plan["initial_checkpoint"],
            "parent_module_hash": model_hash(parent),
            "DINO_hash": model_hash(parent.context.backbone),
            "initial_matching_hash": model_hash(module),
            "objective_module": objective.__module__,
            "renoise_module": renoise.__module__,
            "CUDA_initialized": False,
            "new_neural_forwards": 0,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "Actual frozen-worker imports,metric constructor and strict matching/full-parent CPU state loads pass. Native graph admission inherited;two exact CUDA parent replays remain required before training.",
        },
    )
    print(
        "PASS actual frozen-worker imports,metric and matching/parent/DINO CPU loads;zero forwards",
        flush=True,
    )


def make_module(plan, counts, *, state=None):
    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail

    m = LateLocalNoiseMatchingDetail(**plan["module_config"])
    m.load_state_dict(state, strict=True)
    m.cuda()
    for name, child in [("wrapper", m), ("frozen", m.frozen), ("network", m.network)]:
        child.register_forward_hook(
            lambda *args, name=name: counts.__setitem__(name, counts[name] + 1)
        )
    for child in m.network.modules():
        if type(child).__name__ == "NonlocalBlock":
            child.register_forward_hook(
                lambda *args: counts.__setitem__("sampler", counts["sampler"] + 1)
            )
    return m


def train(plan):
    import numpy as np
    import torch
    from nonlocal_residual_objective import objective
    from profile_raw_kernel_inference import model_hash
    from renoise_cached_training import renoise

    from demosaic.inference import load_checkpoint
    from demosaic.precision import ieee_fp32
    from demosaic.prediction_archive import fingerprint

    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    (ROOT / "train.claim").open("x").close()
    runtime(plan)
    counts = {"wrapper": 0, "frozen": 0, "network": 0, "sampler": 0}
    initial = torch.load(plan["initial_checkpoint"]["path"], map_location="cpu", weights_only=True)
    module = make_module(plan, counts, state=initial["models"])
    assert model_hash(module) == plan["initial_module_hashes"]["raw"]
    frozen = model_hash(module.frozen)
    optimizer = torch.optim.AdamW(
        module.network.parameters(), lr=plan["lr"], weight_decay=plan["weight_decay"]
    )
    optimizer.load_state_dict(initial["optimizer"])
    assert tree_equal(optimizer.state_dict(), initial["optimizer"])
    ema = {k: v.cuda().clone() for k, v in initial["ema"].items()}
    assert tree_equal(ema, initial["ema"])
    del initial
    with torch.random.fork_rng(devices=[0]):
        parent, loaded = load_checkpoint(plan["full_parent"]["path"], "cuda")
    assert loaded["loaded_sha256"] == plan["full_parent"]["sha256"]
    del loaded
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    assert model_hash(parent) == plan["expected_parent_module_hash"]
    assert model_hash(parent.context.backbone) == plan["expected_DINO_sha256"]
    parent_counts = {"parent": 0, "DINO": 0}
    for name, child in [("parent", parent), ("DINO", parent.context.backbone)]:
        child.register_forward_hook(
            lambda *args, name=name: parent_counts.__setitem__(name, parent_counts[name] + 1)
        )
    active = {}

    def observe_parent(_module, args):
        assert len(args) == 5
        actual = {
            k: fingerprint(v.detach().cpu().numpy())
            for k, v in zip(["packed", "variance", "colors", "wb", "matrix"], args, strict=True)
        }
        assert actual == active["inputs"]
        active["observed_inputs"] = actual

    parent.register_forward_pre_hook(observe_parent)
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    rows = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    eligibility = read(plan["clean_sensor_preflight"]["path"])["rows"]
    replays = []
    for item in rows[:2]:
        resources(plan, "train", owner)
        arrays = dict(np.load(item["arrays"]["path"]))
        batch = {
            k: torch.from_numpy(arrays[k]).cuda()
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
        active["inputs"] = {k: fingerprint(arrays[k]) for k in batch}
        parent.set_noise(item["metadata"]["noise"]["shot"], item["metadata"]["noise"]["read"])
        with torch.inference_mode(), ieee_fp32():
            predicted = (
                parent(*(batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"]))
                .cpu()
                .numpy()
            )
        assert fingerprint(predicted) == item["parent_values"]
        replays.append(
            {
                "step": item["step"],
                "input": item["arrays"],
                "parent": item["parent"],
                "values": fingerprint(predicted),
                "actual_inputs": active["observed_inputs"],
                "counts": dict(parent_counts),
            }
        )
        del arrays, batch, predicted
    save(
        ROOT / "parent-runtime-replays-v1.json",
        {
            "status": "pass-two-native-size-parent-DINO-replays-before-training",
            "rows": replays,
            "counts": dict(parent_counts),
            "new_source_noise_draws": 0,
        },
    )
    trace, checkpoints, prefix = [], [], []
    updates = skipped = images = fresh = cached_noisy = poisson = gaussian = 0
    maximum = {n: 0.0 for n, p in module.network.named_parameters()}
    restoration = None
    journal = (ROOT / "train-trace-v1.jsonl").open("x")
    events = (ROOT / "train-forward-events-v1.jsonl").open("x")

    def checkpoint(step):
        path = EXTERNAL / f"checkpoints/step{step:05d}.pt"
        state = {
            "step": step,
            "models": module.state_dict(),
            "ema": ema,
            "optimizer": optimizer.state_dict(),
            "updates": updates,
            "total_updates": updates + 900,
            "skipped": skipped,
            "counts": dict(counts),
            "parent_counts": dict(parent_counts),
            "module_config": plan["module_config"],
            "plan": ref(ROOT / "plan-v1.json"),
            "CPU_RNG": torch.get_rng_state(),
            "CUDA_RNG": torch.cuda.get_rng_state(),
        }
        with path.open("xb") as stream:
            torch.save(state, stream)
        binding = ref(path)
        checkpoints.append(binding)
        return binding

    for continuation_row in range(1, 9001):
        resources(plan, "train", owner)
        cache_index = (continuation_row - 1) % 1000
        item, unit, eligible = rows[cache_index], units[cache_index], eligibility[cache_index]
        step = 1000 + continuation_row
        assert (
            ref(item["arrays"]["path"]) == item["arrays"]
            and ref(item["parent"]["path"]) == item["parent"]
        )
        arrays = dict(np.load(item["arrays"]["path"]))
        assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"]
        assert (
            eligible["arrays"] == item["arrays"]
            and unit["batch"] == item["arrays"]
            and unit["step"] == item["step"]
        )
        progress = max(0, continuation_row - plan["warmup"]) / (9000 - plan["warmup"])
        lr = (
            plan["lr"]
            * min(1, continuation_row / plan["warmup"])
            * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        )
        row = {
            "step": step,
            "continuation_row": continuation_row,
            "cache_step": item["step"],
            "scene_pass": 1 + (continuation_row - 1) // 1000,
            "original_batch": item["arrays"],
            "original_parent": item["parent"],
            "domain": item["metadata"]["domain"],
            "lr": lr,
            "noisy": eligible["noisy"],
            "fresh_noise_eligible": eligible["fresh_noise_eligible"],
        }
        if row["noisy"]:
            if eligible["fresh_noise_eligible"]:
                arrays, draw = renoise(arrays, item["metadata"], continuation_row, item["step"])
                fresh += 1
                poisson += draw["Poisson_calls"]
                gaussian += draw["Gaussian_calls"]
            else:
                draw = {
                    "seed": None,
                    "Poisson_calls": 0,
                    "Gaussian_calls": 0,
                    "reason": eligible["reason"],
                }
                cached_noisy += 1
            row["sensor_draw"] = draw
            row["inputs"] = {k: fingerprint(v) for k, v in arrays.items()}
            for key in arrays:
                if key not in ["packed", "variance"]:
                    assert row["inputs"][key] == item["inputs"][key]
            batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
            if eligible["fresh_noise_eligible"]:
                active["inputs"] = {
                    k: row["inputs"][k] for k in ["packed", "variance", "colors", "wb", "matrix"]
                }
                parent.set_noise(
                    item["metadata"]["noise"]["shot"], item["metadata"]["noise"]["read"]
                )
                events.write(
                    json.dumps(
                        {
                            "step": step,
                            "event": "before-parent",
                            "parent_counts": dict(parent_counts),
                        }
                    )
                    + "\n"
                )
                events.flush()
                with torch.inference_mode(), ieee_fp32():
                    prediction = parent(
                        *(batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"])
                    )
                base = prediction.clone()
                parent_values = prediction.cpu().numpy()
                row["actual_parent_inputs"] = active["observed_inputs"]
                events.write(
                    json.dumps(
                        {
                            "step": step,
                            "event": "returned-parent",
                            "parent_counts": dict(parent_counts),
                            "values": fingerprint(parent_values),
                        }
                    )
                    + "\n"
                )
                events.flush()
                del prediction
            else:
                parent_values = np.load(item["parent"]["path"])
                assert fingerprint(parent_values) == item["parent_values"]
                base = torch.from_numpy(parent_values).cuda()
            row["parent_values"] = fingerprint(parent_values)
            if continuation_row <= 8:
                input_path = EXTERNAL / f"training-prefix/row-{continuation_row:02d}-inputs.npz"
                parent_path = EXTERNAL / f"training-prefix/row-{continuation_row:02d}-parent.npy"
                with input_path.open("xb") as stream:
                    np.savez(stream, **arrays)
                with parent_path.open("xb") as stream:
                    np.save(stream, parent_values, allow_pickle=False)
                row["saved_inputs"], row["saved_parent"] = ref(input_path), ref(parent_path)
                prefix.append(
                    {
                        "row": continuation_row,
                        "inputs": row["saved_inputs"],
                        "parent": row["saved_parent"],
                    }
                )
            pair_units = torch.tensor(
                unit["candidate_units_FP32"], device="cuda", dtype=torch.float32
            ).reshape(-1, 1, 1, 1)
            optimizer.zero_grad(set_to_none=True)
            for group in optimizer.param_groups:
                group["lr"] = lr
            events.write(
                json.dumps({"step": step, "event": "before-matching", "counts": dict(counts)})
                + "\n"
            )
            events.flush()
            torch.cuda.synchronize()
            started = time.perf_counter()
            output, aux = module(
                base, *(batch[k] for k in ["packed", "variance", "colors", "wb"]), return_aux=True
            )
            events.write(
                json.dumps(
                    {
                        "step": step,
                        "event": "returned-matching",
                        "counts": dict(counts),
                        "frozen_values": fingerprint(aux["frozen_output"].detach().cpu().numpy()),
                    }
                )
                + "\n"
            )
            events.flush()
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
            for name, p in module.network.named_parameters():
                assert p.grad is not None and torch.isfinite(p.grad).all(), name
                maximum[name] = max(maximum[name], float(p.grad.abs().max()))
                if p.grad.count_nonzero() == 0:
                    zero.append(name)
            assert not any(
                p.grad is not None for p in [*module.frozen.parameters(), *parent.parameters()]
            )
            norm = torch.nn.utils.clip_grad_norm_(
                module.network.parameters(), plan["gradient_clip"], error_if_nonfinite=True
            )
            optimizer.step()
            updates += 1
            images += len(base)
            decay = min(plan["EMA_decay"], (1 + 900 + updates) / (10 + 900 + updates))
            with torch.no_grad():
                for k, v in module.network.state_dict().items():
                    ema[k].lerp_(v, 1 - decay)
            torch.cuda.synchronize()
            row.update(
                loss=float(loss.detach()),
                terms={k: float(v.detach()) for k, v in terms.items()},
                gradient_norm=float(norm),
                zero_gradient_tensors=zero,
                flat_eligible_pixels=int(mask.sum()),
                flat_mask=fingerprint(mask.cpu().numpy()),
                correction_RMS_DN16=float(aux["correction"].detach().square().mean().sqrt())
                * 65535,
                seconds=time.perf_counter() - started,
                counts=dict(counts),
                parent_counts=dict(parent_counts),
                updates=updates,
            )
            del output, aux, loss, terms, mask, batch, base, pair_units, parent_values
        else:
            skipped += 1
            row.update(
                skipped="ADC row retained;no sensor draw,parent,matching or optimizer evaluation",
                counts=dict(counts),
                parent_counts=dict(parent_counts),
                updates=updates,
            )
        assert model_hash(module.frozen) == frozen
        assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
            cuda_rng, torch.cuda.get_rng_state()
        )
        trace.append(row)
        journal.write(json.dumps(row, allow_nan=False) + "\n")
        journal.flush()
        if continuation_row == 1 or continuation_row % 10 == 0:
            status = {
                "status": "training",
                "owner": owner,
                "step": step,
                "continuation_row": continuation_row,
                "updates": updates,
                "total_updates": updates + 900,
                "skipped": skipped,
                "fresh_batches": fresh,
                "cached_noisy_batches": cached_noisy,
                "counts": dict(counts),
                "parent_counts": dict(parent_counts),
                "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
            }
            save(ROOT / "train-status-v1.json", status)
            print(json.dumps(status), flush=True)
        if step in [1008, 2000, 5000, 10000]:
            binding = checkpoint(step)
            if step == 1008:
                before_hash = model_hash(module)
                state = torch.load(binding["path"], map_location="cpu", weights_only=True)
                del optimizer, module
                module = make_module(plan, counts, state=state["models"])
                optimizer = torch.optim.AdamW(
                    module.network.parameters(), lr=plan["lr"], weight_decay=plan["weight_decay"]
                )
                optimizer.load_state_dict(state["optimizer"])
                assert model_hash(module) == before_hash and tree_equal(
                    optimizer.state_dict(), state["optimizer"]
                )
                assert tree_equal(ema, state["ema"]) and state["updates"] == updates
                torch.set_rng_state(state["CPU_RNG"])
                torch.cuda.set_rng_state(state["CUDA_RNG"])
                restoration = {
                    "checkpoint": binding,
                    "model_exact": True,
                    "optimizer_exact": True,
                    "EMA_exact": True,
                    "CPU_RNG_exact": torch.equal(torch.get_rng_state(), state["CPU_RNG"]),
                    "CUDA_RNG_exact": torch.equal(
                        torch.cuda.get_rng_state().cpu(), state["CUDA_RNG"]
                    ),
                    "continued_at_step": 1009,
                    "repeated_prefix_forwards": 0,
                }
                save(ROOT / "checkpoint-restoration-v1.json", restoration)
                del state
        del arrays
    journal.close()
    events.close()
    assert len(trace) == 9000 and updates == 8100 and skipped == 900 and images == 32400
    assert fresh == 8073 and cached_noisy == 27
    assert counts == {"wrapper": 8100, "frozen": 8100, "network": 8100, "sampler": 40500}
    assert parent_counts == {"parent": 8075, "DINO": 8075}
    assert min(maximum.values()) > 0 and len(optimizer.state) == 141
    assert all(
        float(s["step"]) == 9000 and all(torch.isfinite(v).all() for v in s.values())
        for s in optimizer.state.values()
    )
    assert all(torch.isfinite(v).all() for v in [*module.state_dict().values(), *ema.values()])
    assert (
        model_hash(parent) == plan["expected_parent_module_hash"]
        and model_hash(parent.context.backbone) == plan["expected_DINO_sha256"]
    )
    assert model_hash(module.frozen) == frozen
    guard(plan)
    save(
        ROOT / "train-result-v1.json",
        {
            "status": "completed9000-continuation-rows-with-fresh-noise-and-exact-parent",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "initial_checkpoint": plan["initial_checkpoint"],
            "checkpoints": checkpoints,
            "final_checkpoint": checkpoints[-1],
            "updates": updates,
            "total_optimizer_updates": 9000,
            "skipped_ADC_batches": skipped,
            "counts": counts,
            "parent_counts": parent_counts,
            "new_fresh_noise_batches": fresh,
            "retained_cached_noisy_batches": cached_noisy,
            "sensor_Poisson_calls": poisson,
            "sensor_Gaussian_calls": gaussian,
            "training_images": images,
            "total_training_images_including_V172": 36000,
            "trace": trace,
            "saved_prefix": prefix,
            "parameter_maximum_gradients": maximum,
            "final_Adam_states": 141,
            "checkpoint_restoration": restoration,
            "frozen_module_hash": frozen,
            "frozen_weights_unchanged": True,
            "RNG_unchanged": True,
            "new_parent_DINO_forwards": 8075,
            "new_scene_geometry_renders": 0,
            "new_original_dataz_reads": 0,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": plan["scope"],
        },
    )
    save(
        ROOT / "train-status-v1.json",
        {
            "status": "completed-training-awaiting-fixed-quality",
            "owner": owner,
            "step": 10000,
            "updates": updates,
            "counts": counts,
            "parent_counts": parent_counts,
        },
    )
    print("TRAIN COMPLETED8100 new updates/8073 fresh noise+parent batches", flush=True)


def resources(plan, phase, owner):
    while True:
        available = {
            "RAM": psutil.virtual_memory().available,
            "local": shutil.disk_usage(REPO).free,
            "external": shutil.disk_usage("/mnt/external").free,
        }
        if all(available[k] > v * 2**30 for k, v in plan["minimum_GiB"].items()):
            return available
        save(
            ROOT / f"{phase}-status-v1.json",
            {
                "status": "waiting-before-next-forward",
                "owner": owner,
                "available_bytes": available,
                "minimum_GiB": plan["minimum_GiB"],
            },
        )
        time.sleep(2)


def runtime(plan):
    import torch

    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
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


def tree_equal(a, b):
    import torch

    if isinstance(a, torch.Tensor):
        return isinstance(b, torch.Tensor) and torch.equal(a.cpu(), b.cpu())
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(tree_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return (
            type(a) is type(b)
            and len(a) == len(b)
            and all(tree_equal(x, y) for x, y in zip(a, b, strict=True))
        )
    return a == b


def review(plan):
    import numpy as np
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    (ROOT / "review.claim").open("x").close()
    training = read(ROOT / "train-result-v1.json")
    assert training["frozen_weights_unchanged"] and training["RNG_unchanged"]
    assert ref(training["final_checkpoint"]["path"]) == training["final_checkpoint"]
    runtime(plan)
    state = torch.load(training["final_checkpoint"]["path"], map_location="cpu", weights_only=True)
    prior = read(plan["prior_scores"]["path"])
    expected = {r["id"]: r for r in prior["rows"] if r["method"] == "balanced-EMA"}
    assert len(expected) == 822
    metric = DetailMetrics(plan["metrics_sources"])
    design = read(plan["design"]["path"])["observations"]
    counts = {"wrapper": 0, "frozen": 0, "network": 0, "sampler": 0}
    rows = []
    native = {}
    weights = {}
    replays = ADC_exact = closure_channels = 0
    offset_rows = []
    captured_offsets = {}
    capture_state = {"enabled": False}
    CPU_RNG = torch.get_rng_state().clone()
    CUDA_RNG = torch.cuda.get_rng_state().clone()
    with (
        (ROOT / "forward-events-v1.jsonl").open("x") as events,
        (ROOT / "observations-v1.jsonl").open("x") as journal,
    ):
        for endpoint in ["raw", "EMA"]:
            module = make_module(plan, counts, state=state["models"]).eval()
            if endpoint == "EMA":
                module.network.load_state_dict(state["ema"], strict=True)
            if endpoint == "EMA":
                for name, child in module.network.named_modules():
                    if type(child).__name__ == "NonlocalBlock":

                        def capture(_module, _args, output, name=name):
                            if capture_state["enabled"]:
                                captured_offsets[name] = output.detach().cpu().numpy().copy()

                        child.offset_cnn.register_forward_hook(capture)
            before = model_hash(module)
            weights[endpoint] = {"before": before, "frozen": model_hash(module.frozen)}
            assert weights[endpoint]["frozen"] == plan["frozen_component"]["module_hash"]
            for ordinal, index in enumerate(plan["processing_order"]):
                resources(plan, "review", owner)
                case = design[index]
                assert (
                    ref(case["arrays"]["path"]) == case["arrays"]
                    and ref(case["parent"]["path"]) == case["parent"]
                )
                capture_state["enabled"] = (
                    endpoint == "EMA" and case["id"] in plan["offset_probe_cases"]
                )
                captured_offsets.clear()
                a = dict(np.load(case["arrays"]["path"]))
                base = np.load(case["parent"]["path"])
                batch = {
                    k: torch.from_numpy(a[k]).cuda() for k in ["packed", "variance", "colors", "wb"]
                }
                torch.cuda.synchronize()
                started = time.perf_counter()
                with torch.inference_mode():
                    output, aux = module(
                        torch.from_numpy(base).cuda(),
                        *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                        return_aux=True,
                    )
                torch.cuda.synchronize()
                elapsed = time.perf_counter() - started
                event = {
                    "endpoint": endpoint,
                    "index": index,
                    "id": case["id"],
                    "ordinal": ordinal,
                    "counts": dict(counts),
                    "seconds": elapsed,
                    "matching_evaluated": aux["matching_evaluated"],
                }
                events.write(json.dumps(event) + "\n")
                events.flush()
                value = output.cpu().numpy()
                frozen = aux["frozen_output"].cpu().numpy()
                correction = aux["correction"].cpu().numpy()
                assert fingerprint(frozen) == expected[case["id"]]["values"]
                replays += 1
                np.testing.assert_array_equal(value, frozen + correction)
                closure_channels += value.size
                if not aux["matching_evaluated"]:
                    assert np.array_equal(value, frozen) and not np.any(a["variance"])
                    ADC_exact += 1
                method = f"V175-{endpoint}"
                row = metric.measure(case, a, base, value)
                row.update(
                    method=method,
                    index=index,
                    values=fingerprint(value),
                    nonlocal_correction_RMS_DN16=float(
                        np.sqrt(np.mean(correction.astype(np.float64) ** 2))
                    )
                    * 65535,
                    nonlocal_correction_values=fingerprint(correction),
                    frozen_values=fingerprint(frozen),
                    frozen_replay_exact=True,
                    ADC_exact=not aux["matching_evaluated"],
                )
                if case["id"] in plan["native_cases"]:
                    for label, array in [(method, value), (method + "-correction", correction)]:
                        path = EXTERNAL / f"native/{label}-{index:03d}.npy"
                        assert not path.exists()
                        np.save(path, array, allow_pickle=False)
                        native.setdefault(case["id"], {})[label] = ref(path)
                    row["prediction"] = native[case["id"]][method]
                if capture_state["enabled"]:
                    scales = {"down1.0": 2, "down2.0": 4, "body.0": 8, "up2.1": 4, "up1.1": 2}
                    assert set(captured_offsets) == set(scales)
                    blocks = []
                    for name, array in captured_offsets.items():
                        path = EXTERNAL / "offsets" / f"EMA-{index:03d}-{name}.npy"
                        assert not path.exists()
                        np.save(path, array, allow_pickle=False)
                        blocks.append(
                            {
                                "name": name,
                                "array": ref(path),
                                "values": fingerprint(array),
                                "native_pixels_per_feature": scales[name],
                                "residual_bound": 9,
                            }
                        )
                    offset_rows.append(
                        {
                            "id": case["id"],
                            "index": index,
                            "endpoint": endpoint,
                            "input": case["arrays"],
                            "parent": case["parent"],
                            "output_values": row["values"],
                            "blocks": blocks,
                        }
                    )
                rows.append(row)
                record = {
                    "endpoint": endpoint,
                    "index": index,
                    "id": case["id"],
                    "arrays": case["arrays"],
                    "parent": case["parent"],
                    "inputs": {k: fingerprint(a[k]) for k in batch},
                    "row": row,
                    "frozen_replay_exact": True,
                    "closure_exact": True,
                }
                journal.write(json.dumps(record, allow_nan=False) + "\n")
                journal.flush()
                if ordinal % 16 == 0:
                    status = {
                        "status": "reviewing",
                        "owner": owner,
                        "endpoint": endpoint,
                        "index": index,
                        "counts": dict(counts),
                        "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                    }
                    save(ROOT / "review-status-v1.json", status)
                    print(json.dumps(status), flush=True)
                del output, aux, batch, value, correction, frozen, a, base
            assert before == model_hash(module)
            weights[endpoint]["after"] = model_hash(module)
            del module
    assert counts == plan["expected_quality_counts"] and len(rows) == 1644 and len(native) == 36
    assert replays == 1644 and ADC_exact == 144
    assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
        CUDA_RNG, torch.cuda.get_rng_state()
    )
    assert len(offset_rows) == 6 and {r["id"] for r in offset_rows} == set(
        plan["offset_probe_cases"]
    )
    save(
        ROOT / "offset-observations-v1.json",
        {
            "status": "captured30-pre-tanh-offset-arrays-from6-existing-EMA-quality-forwards",
            "checkpoint": training["final_checkpoint"],
            "rows": offset_rows,
            "new_matching_calls": 0,
            "scope": "Captured FP32 pre-tanh fields,not a causal RGB influence or whole-pipeline receptive field. Posthoc positions reconstructed according to the pinned sampler equation.",
        },
    )
    rows.sort(key=lambda r: (r["index"], r["method"]))
    guard(plan)
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-fixed-raw-EMA-streamed-quality",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "checkpoint": training["final_checkpoint"],
            "counts": counts,
            "rows": rows,
            "summary": summarize(rows),
            "native_predictions": native,
            "module_hashes": weights,
            "weights_unchanged": True,
            "RNG_unchanged": True,
            "exact_V169_replays": replays,
            "ADC_outputs_exact_V169": ADC_exact,
            "independent_inprocess_addition_channels": closure_channels,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "new_parent_DINO_forwards": 0,
            "new_source_noise_draws": 0,
            "new_training_updates": 0,
            "scope": plan["scope"],
        },
    )
    save(
        ROOT / "review-status-v1.json",
        {
            "status": "completed-awaiting-array-audit-and-native-viewing",
            "owner": owner,
            "counts": counts,
        },
    )
    print("REVIEW COMPLETED", counts, ";exact V169 replays", replays, flush=True)


def launch(phase):
    plan = read(ROOT / "plan-v1.json")
    assert (
        read(ROOT / "metric-runtime-readiness-v1.json")["status"] == "pass-before-training-launch"
    )
    guard(plan)
    if phase == "review":
        assert read(ROOT / "train-result-v1.json")["status"].startswith("completed")
    assert (
        not (ROOT / f"{phase}-launch-v1.json").exists() and not (ROOT / f"{phase}.claim").exists()
    )
    env = dict(
        os.environ,
        PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
        OMP_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    command = [str(REPO / ".venv/bin/python"), plan["runner"]["path"], phase]
    log = (ROOT / f"{phase}-v1.log").open("xb")
    child = subprocess.Popen(
        command,
        cwd=REPO,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(
        ROOT / f"{phase}-launch-v1.json",
        {
            "owner": owner,
            "command": command,
            "plan": ref(ROOT / "plan-v1.json"),
            "log_path": str(ROOT / f"{phase}-v1.log"),
        },
    )
    print("Launched", phase, owner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=["prepare", "check", "train", "review", "launch-train", "launch-review"]
    )
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode.startswith("launch-"):
        launch(args.mode.removeprefix("launch-"))
    else:
        plan = read(ROOT / "plan-v1.json")
        guard(plan)
        try:
            {"check": check, "train": train, "review": review}[args.mode](plan)
        except BaseException as error:
            save(
                ROOT / f"{args.mode}-failure-v1.json",
                {
                    "status": "failed-preserved-no-automatic-retry",
                    "error": repr(error),
                    "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                },
            )
            raise
