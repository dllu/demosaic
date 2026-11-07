"""Train a fresh matching RGB residual on the fixed free-image V168 cache.

The V169 EMA component and its V143/DINO parent remain frozen. A single worker
continues after an actual checkpoint restoration; no successful prefix repeats.
"""

import argparse
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
ROOT = REPO / ".cache/quality-20261107/V172-local-noise-matching-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V172-local-noise-matching-v1")


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


def prepare():
    import numpy as np

    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail

    admission = ROOT / "admission-result-v1.json"
    assert read(admission)["status"].startswith("pass-")
    assert not (ROOT / "plan-v1.json").exists() and not (ROOT / "work").exists()
    prior = read(REPO / ".cache/quality-20261107/V168-fine-mesh-ladder-v3/plan-v1.json")
    cache = read(prior["candidate_cache"]["path"])
    units = read(prior["candidate_pair_unit_table"]["path"])
    assert len(cache["batches"]) == len(units["rows"]) == 1000
    assert all(
        a["step"] == b["step"] and a["arrays"] == b["batch"]
        for a, b in zip(cache["batches"], units["rows"], strict=True)
    )
    frozen = read(REPO / "docs/results/v169-balanced-spatial-final-v1.json")["checkpoints"]["EMA"]
    old = read(REPO / ".cache/quality-20261107/V170-nonlocal-raw-v2/plan-v1.json")
    design = read(old["design"]["path"])
    assert len(design["observations"]) == 822
    expected_noisy = sum(
        np.any(np.load(c["arrays"]["path"])["variance"] > 0) for c in design["observations"]
    )
    assert expected_noisy == 750
    projected = 4 * sum(
        np.load(c["parent"]["path"], mmap_mode="r").nbytes + 128
        for c in design["observations"]
        if c["id"] in old["native_cases"]
    )
    assert shutil.disk_usage(REPO).free > 52.5 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 114.5 * 2**30 + projected + 0.4 * 2**30
    assert psutil.virtual_memory().available > 52 * 2**30
    work = ROOT / "work"
    names = [
        "train_local_noise_matching_trial.py",
        "nonlocal_residual_objective.py",
        "train_directional_bank_trial.py",
        "train_v43_quality_trial.py",
        "profile_raw_kernel_inference.py",
        "flat_target_anchor.py",
        "local_excess_risk.py",
        "regional_dc_objective.py",
        "paired_response_objective.py",
        "paired_common_objective.py",
        "balanced_spatial_metrics.py",
        "render_local_noise_matching_trial.py",
        "report_checkpoint_pilot.py",
        "report_late_spectral_mixed_quiet.py",
    ]
    sources = list((REPO / "src/demosaic").glob("*.py"))
    sources += [REPO / "scripts" / n for n in names]
    sources += [REPO / "tests/test_late_local_noise_matching.py"]
    for p in sources:
        q = work / p.relative_to(REPO)
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, q)
    EXTERNAL.mkdir(exist_ok=False)
    (EXTERNAL / "checkpoints").mkdir()
    (EXTERNAL / "native").mkdir()
    m = LateLocalNoiseMatchingDetail().load_frozen_component(frozen["export"]["path"])
    plan = {
        "root": str(ROOT),
        "work": str(work),
        "external": str(EXTERNAL),
        "runner": ref(work / "scripts/train_local_noise_matching_trial.py"),
        "module_config": {"width": 16, "max_search": 9.0},
        "trainable_parameters": 2088906,
        "trainable_tensors": 141,
        "frozen_parameters": 124909,
        "frozen_tensors": 47,
        "frozen_component": frozen,
        "cache": prior["candidate_cache"],
        "pair_units": prior["candidate_pair_unit_table"],
        "training_provenance": ref(
            REPO / ".cache/quality-20261107/V168-fine-mesh-ladder-v3/data-plan-v1.json"
        ),
        "design": old["design"],
        "prior_scores": old["prior_scores"],
        "parent_scores": old["parent_scores"],
        "prior_figures": ref(
            REPO / ".cache/quality-20261107/V171-matching-residual-v1/figures-v1.json"
        ),
        "baseline_scores": ref(
            REPO / ".cache/quality-20261107/V171-matching-residual-v1/scores-v1.json"
        ),
        "metrics_sources": old["metrics_sources"],
        "native_cases": old["native_cases"],
        "processing_order": old["processing_order"],
        "methods": ["V172-raw", "V172-EMA"],
        "expected_quality_counts": {
            "wrapper": 1644,
            "frozen": 1644,
            "network": 1500,
            "sampler": 7500,
        },
        "projected_native_array_bytes": projected,
        "steps": 1000,
        "lr": 0.0003,
        "warmup": 50,
        "gradient_clip": 1.0,
        "weight_decay": 0.01,
        "EMA_decay": 0.999,
        "domain_weights": {"mesh": 4.0, "weak": 4.0, "photo": 1.0, "flat": 1.0, "mixed": 1.0},
        "minimum_GiB": {"RAM": 32, "local": 52, "external": 114},
        "CUDA_quota_GiB": 24,
        "launch_RAM_GiB": 52,
        "projection_margin_GiB": 0.5,
        "admission": ref(admission),
        "sampling_library": read(ROOT / "admission-source-freeze-v1.json")["native_library"],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "inputs": [
            prior["candidate_cache"],
            prior["candidate_pair_unit_table"],
            frozen["export"],
            old["design"],
            old["prior_scores"],
            old["parent_scores"],
            ref(REPO / ".cache/quality-20261107/V171-matching-residual-v1/figures-v1.json"),
            ref(REPO / ".cache/quality-20261107/V171-matching-residual-v1/scores-v1.json"),
            *old["metrics_sources"],
            ref(admission),
        ],
        "scope": "V172 local-noise matching: same2.09M/141-tensor network,initialization,frozenV169EMA,"
        "V1681000-row cache,pair units,V171 loss,AdamW/LR/EMA and900 noisy updates. Only the new "
        "feature coordinate system and output unit change together:local Bayer-cell RGB mean/"
        "noiseRMS replace image-wide statistics. No target/reference enters forward,no new weights "
        "or releasedV170 initialization. FrozenV169/cachedDINO still provide spatial context;"
        "feature locality is not whole-pipeline invariance or a noisy-flat guarantee. Zero local "
        "variance retains V169 there;ADC-only rows skip updates. Exact step8 restoration continues9 "
        "without prefix replay. Sampler grad-input is atomic/warn-only nondeterministic;no exact "
        "retraining control is claimed. Both raw/EMA endpoints and all822 quality cases fixed;"
        "1644 V169 replays,1500 new matching calls,7500 nested samplers,144 exact ADC outputs. "
        "Metrics/fingerprints/addition checks stream;36 native cases retain72 RGB+72 residuals. "
        "Fixed48 boards/12 triplets include both protected scenes/priors/windows/JPEGs;real "
        "references qualitative,notGT,unscored. No source/noise draws,original/dataz reads or "
        "new parent/DINO calls. Previous95 neural files unchanged;no blind or general win claim.",
    }
    assert sum(p.numel() for p in m.network.parameters()) == plan["trainable_parameters"]
    reference_trial = read(REPO / ".cache/quality-20261107/V171-matching-residual-v1/plan-v1.json")
    previous = {
        Path(p).name: h for p, h in reference_trial["frozen_files"].items() if "/src/demosaic/" in p
    }
    assert len(previous) == 95
    assert all(ref(REPO / "src/demosaic" / p)["sha256"] == h for p, h in previous.items())
    plan["prior_neural_hashes"] = previous
    import ast

    old_runner = Path(reference_trial["runner"]["path"])

    def functions(path):
        return {
            n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(Path(path).read_text()).body
            if isinstance(n, ast.FunctionDef)
        }

    before, after = functions(old_runner), functions(__file__)
    matched = [
        name
        for name in ["train", "runtime", "resources", "tree_equal"]
        if before[name] == after[name]
    ]
    assert len(matched) == 4
    for key in [
        "steps",
        "lr",
        "warmup",
        "gradient_clip",
        "weight_decay",
        "EMA_decay",
        "domain_weights",
        "minimum_GiB",
        "CUDA_quota_GiB",
        "module_config",
        "cache",
        "pair_units",
        "design",
        "metrics_sources",
        "frozen_component",
    ]:
        assert plan[key] == reference_trial[key], key
    old_objective = Path(reference_trial["work"]) / "scripts/nonlocal_residual_objective.py"
    assert (
        ref(old_objective)["sha256"]
        == ref(REPO / "scripts/nonlocal_residual_objective.py")["sha256"]
    )
    initial = read(admission)
    assert initial["initial_tensors_exact_seeded_V171"]
    plan["matched_V171_recipe"] = {
        "reference_plan": ref(
            REPO / ".cache/quality-20261107/V171-matching-residual-v1/plan-v1.json"
        ),
        "reference_training": ref(
            REPO / ".cache/quality-20261107/V171-matching-residual-v1/train-result-v1.json"
        ),
        "unchanged_function_ASTs": matched,
        "objective": ref(old_objective),
        "initial_network_hash": initial["initial_network_hash"],
        "initial_tensors_exact_seeded_V171": True,
    }
    plan["inputs"].append(plan["sampling_library"])
    save(ROOT / "plan-v1.json", plan)
    guard(plan)
    save(
        REPO / "docs/results/v172-local-noise-matching-preparation-v1.json",
        {
            "status": "prepared-before-scientific-training-and-heldout-inference",
            "plan": ref(ROOT / "plan-v1.json"),
            "plan_contents": plan,
            "source_texts": [
                dict(ref(p), text=p.read_text()) for p in work.rglob("*") if p.is_file()
            ],
            "admission": dict(ref(admission), contents=read(admission)),
            "admission_failures": [],
            "CPU_tests": dict(
                ref(REPO / ".cache/v172-relevant-CPU-tests-v2.log"),
                text=(REPO / ".cache/v172-relevant-CPU-tests-v2.log").read_text(),
            ),
            "previous_neural_files_unchanged": 95,
            "new_neural_source_files": 1,
            "new_training_updates_so_far": 0,
            "new_heldout_forwards_so_far": 0,
            "scope": plan["scope"],
        },
    )
    environment = dict(os.environ, PYTHONPATH=f"{work}/src:{work}/scripts")
    check = subprocess.run(
        [
            str(REPO / ".venv/bin/python"),
            "-c",
            (
                "from balanced_spatial_metrics import DetailMetrics;from train_directional_bank_trial import read;import torch;"
                f"p=read({str(ROOT / 'plan-v1.json')!r});DetailMetrics(p['metrics_sources']);"
                "assert not torch.cuda.is_initialized();print('Frozen metric runtime ready without neural calls')"
            ),
        ],
        env=environment,
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0, (check.stdout, check.stderr)
    save(
        ROOT / "metric-runtime-readiness-v1.json",
        {
            "status": "pass-before-training-launch",
            "stdout": check.stdout,
            "stderr": check.stderr,
            "new_neural_forwards": 0,
        },
    )
    print("Prepared", plan["trainable_parameters"], "trainable parameters;native bytes", projected)


def make_module(plan, counts, *, state=None):
    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail

    m = LateLocalNoiseMatchingDetail(**plan["module_config"])
    m.load_frozen_component(plan["frozen_component"]["export"]["path"])
    if state is not None:
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


def train(plan):
    import numpy as np
    import torch
    from nonlocal_residual_objective import objective
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    (ROOT / "train.claim").open("x").close()
    runtime(plan)
    counts = {"wrapper": 0, "frozen": 0, "network": 0, "sampler": 0}
    module = make_module(plan, counts)
    frozen = model_hash(module.frozen)
    assert frozen == plan["frozen_component"]["module_hash"]
    optimizer = torch.optim.AdamW(
        module.network.parameters(), lr=plan["lr"], weight_decay=plan["weight_decay"]
    )
    ema = {k: v.detach().clone() for k, v in module.network.state_dict().items()}
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    rows = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    trace = []
    updates = skipped = images = 0
    maximum = {n: 0.0 for n, p in module.network.named_parameters()}
    checkpoints = []
    restoration = None
    journal = (ROOT / "train-trace-v1.jsonl").open("x")

    def checkpoint(step):
        path = EXTERNAL / f"checkpoints/step{step:04d}.pt"
        assert not path.exists()
        state = {
            "step": step,
            "models": module.state_dict(),
            "ema": ema,
            "optimizer": optimizer.state_dict(),
            "updates": updates,
            "skipped": skipped,
            "counts": dict(counts),
            "module_config": plan["module_config"],
            "plan": ref(ROOT / "plan-v1.json"),
            "frozen_component": plan["frozen_component"],
            "CPU_RNG": torch.get_rng_state(),
            "CUDA_RNG": torch.cuda.get_rng_state(),
        }
        with path.open("xb") as stream:
            torch.save(state, stream)
        binding = ref(path)
        checkpoints.append(binding)
        return binding

    for step, item in enumerate(rows, 1):
        resources(plan, "train", owner)
        assert (
            ref(item["arrays"]["path"]) == item["arrays"]
            and ref(item["parent"]["path"]) == item["parent"]
        )
        arrays = dict(np.load(item["arrays"]["path"]))
        parent = np.load(item["parent"]["path"])
        assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"]
        assert fingerprint(parent) == item["parent_values"]
        assert units[step - 1]["step"] == step and units[step - 1]["batch"] == item["arrays"]
        progress = max(0, step - plan["warmup"]) / (plan["steps"] - plan["warmup"])
        lr = (
            plan["lr"]
            * min(1, step / plan["warmup"])
            * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
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
            torch.cuda.synchronize()
            started = time.perf_counter()
            output, aux = module(
                base, *(batch[k] for k in ["packed", "variance", "colors", "wb"]), return_aux=True
            )
            if updates == 0:
                assert torch.equal(output, aux["frozen_output"])
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
            assert not any(p.grad is not None for p in module.frozen.parameters())
            norm = torch.nn.utils.clip_grad_norm_(
                module.network.parameters(), plan["gradient_clip"], error_if_nonfinite=True
            )
            optimizer.step()
            updates += 1
            images += len(base)
            decay = min(plan["EMA_decay"], (1 + updates) / (10 + updates))
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
                updates=updates,
            )
            del output, aux, loss, terms, mask, batch, base, pair_units
        else:
            skipped += 1
            row.update(
                skipped="zero supplied variance;no new model or optimizer evaluation",
                counts=dict(counts),
                updates=updates,
            )
        assert model_hash(module.frozen) == frozen
        trace.append(row)
        journal.write(json.dumps(row, allow_nan=False) + "\n")
        journal.flush()
        if step == 1 or step % 10 == 0:
            status = {
                "status": "training",
                "owner": owner,
                "step": step,
                "updates": updates,
                "skipped": skipped,
                "counts": dict(counts),
                "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
            }
            save(ROOT / "train-status-v1.json", status)
            print(json.dumps(status), flush=True)
        if step in [8, 250, 500, 750, 1000]:
            binding = checkpoint(step)
            if step == 8:
                before_hash = model_hash(module)
                state = torch.load(binding["path"], map_location="cpu", weights_only=True)
                del optimizer, module
                module = make_module(plan, counts, state=state["models"])
                optimizer = torch.optim.AdamW(
                    module.network.parameters(), lr=plan["lr"], weight_decay=plan["weight_decay"]
                )
                optimizer.load_state_dict(state["optimizer"])
                assert model_hash(module) == before_hash
                assert tree_equal(optimizer.state_dict(), state["optimizer"])
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
                    "continued_at_step": 9,
                    "repeated_prefix_forwards": 0,
                }
                save(ROOT / "checkpoint-restoration-v1.json", restoration)
                del state
        del arrays, parent
    journal.close()
    assert (
        len(trace) == 1000
        and updates + skipped == 1000
        and counts
        == {"wrapper": updates, "frozen": updates, "network": updates, "sampler": 5 * updates}
    )
    assert min(maximum.values()) > 0 and len(optimizer.state) == 141
    assert all(
        float(s["step"]) == updates and all(torch.isfinite(v).all() for v in s.values())
        for s in optimizer.state.values()
    )
    assert all(torch.isfinite(v).all() for v in [*module.state_dict().values(), *ema.values()])
    assert model_hash(module.frozen) == frozen
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    guard(plan)
    save(
        ROOT / "train-result-v1.json",
        {
            "status": "completed1000-row-schedule-with-actual-checkpoint-restoration",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "checkpoints": checkpoints,
            "final_checkpoint": checkpoints[-1],
            "updates": updates,
            "skipped_ADC_batches": skipped,
            "counts": counts,
            "training_images": images,
            "trace": trace,
            "parameter_maximum_gradients": maximum,
            "final_Adam_states": 141,
            "checkpoint_restoration": restoration,
            "frozen_module_hash": frozen,
            "frozen_weights_unchanged": True,
            "RNG_unchanged": True,
            "new_parent_DINO_forwards": 0,
            "new_source_noise_draws": 0,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": plan["scope"],
        },
    )
    save(
        ROOT / "train-status-v1.json",
        {
            "status": "completed-training-awaiting-fixed-quality",
            "owner": owner,
            "step": 1000,
            "updates": updates,
            "counts": counts,
        },
    )
    print("TRAIN COMPLETED", updates, "updates;", skipped, "ADC skips", flush=True)


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
                method = f"V171-{endpoint}"
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
        "mode", choices=["prepare", "train", "review", "launch-train", "launch-review"]
    )
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode.startswith("launch-"):
        launch(args.mode.removeprefix("launch-"))
    else:
        plan = read(ROOT / "plan-v1.json")
        guard(plan)
        {"train": train, "review": review}[args.mode](plan)
