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
ROOT = REPO / ".cache/quality-20261107/V174-spread-matching-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V174-spread-matching-v1")


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
    import ast
    import copy

    import torch
    from profile_raw_kernel_inference import model_hash
    from spread_matching_offsets import initialize_spread_offsets

    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail

    reference_path = REPO / ".cache/quality-20261107/V172-local-noise-matching-v1/plan-v1.json"
    reference = read(reference_path)
    guard(reference)
    admission = ROOT / "admission-result-v1.json"
    admitted = read(admission)
    assert admitted["status"].startswith("pass-")
    assert (
        not (ROOT / "plan-v1.json").exists()
        and not (ROOT / "work").exists()
        and not EXTERNAL.exists()
    )
    work = ROOT / "work"
    frozen = reference["frozen_component"]
    old = LateLocalNoiseMatchingDetail(**reference["module_config"]).load_frozen_component(
        frozen["export"]["path"]
    )
    module = LateLocalNoiseMatchingDetail(**reference["module_config"]).load_frozen_component(
        frozen["export"]["path"]
    )
    changed = initialize_spread_offsets(module, spacing=8)
    differences = [
        k for k, v in module.state_dict().items() if not torch.equal(v, old.state_dict()[k])
    ]
    assert differences == ["network." + k for k in changed] == admitted["changed_initial_tensors"]
    assert len(differences) == 5 and len(module.state_dict()) == 188
    assert model_hash(module) == admitted["initial_module_hash"]
    assert model_hash(old) == read(reference["admission"]["path"])["initial_module_hash"]

    def functions(text):
        return {
            n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(text).body
            if isinstance(n, ast.FunctionDef)
        }

    before, after = (
        functions(Path(reference["runner"]["path"]).read_text()),
        functions(Path(__file__).read_text()),
    )
    assert all(before[n] == after[n] for n in ["train", "runtime", "resources", "tree_equal"])
    old_objective = Path(reference["work"]) / "scripts/nonlocal_residual_objective.py"
    assert (
        ref(old_objective)["sha256"]
        == ref(REPO / "scripts/nonlocal_residual_objective.py")["sha256"]
    )
    previous = {
        Path(p).name: h for p, h in reference["frozen_files"].items() if "/src/demosaic/" in p
    }
    assert len(previous) == 96 and all(
        ref(REPO / "src/demosaic" / p)["sha256"] == h for p, h in previous.items()
    )
    probe = read(REPO / ".cache/quality-20261107/V174-offset-usage-v1/result-v1.json")
    probe_cases = read(probe["protocol"]["path"])["selected"]
    cases = {c["id"]: c for c in read(reference["design"]["path"])["observations"]}
    offset_bytes = 0
    for identifier in probe_cases:
        shape = cases[identifier]["output_shape"]
        n, _, h, w = shape
        assert n == 1 and h % 8 == w % 8 == 0
        offset_bytes += (
            18 * 4 * (2 * (h // 2) * (w // 2) + 2 * (h // 4) * (w // 4) + (h // 8) * (w // 8))
            + 5 * 128
        )
    assert offset_bytes == 102780672
    assert shutil.disk_usage(REPO).free > 49.5 * 2**30
    assert (
        shutil.disk_usage("/mnt/external").free
        > 110.5 * 2**30 + reference["projected_native_array_bytes"] + offset_bytes + 0.4 * 2**30
    )
    assert psutil.virtual_memory().available > 52 * 2**30
    names = [
        "train_spread_matching_trial.py",
        "render_spread_matching_trial.py",
        "spread_matching_offsets.py",
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
        "report_checkpoint_pilot.py",
        "report_late_spectral_mixed_quiet.py",
    ]
    sources = (
        list((REPO / "src/demosaic").glob("*.py"))
        + [REPO / "scripts" / name for name in names]
        + [REPO / "tests/test_spread_matching_offsets.py"]
    )
    for path in sources:
        destination = work / path.relative_to(REPO)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    EXTERNAL.mkdir()
    for name in ["checkpoints", "native", "offsets"]:
        (EXTERNAL / name).mkdir()
    plan = copy.deepcopy(reference)
    plan.pop("matched_V171_recipe")
    plan.update(
        root=str(ROOT),
        work=str(work),
        external=str(EXTERNAL),
        runner=ref(work / "scripts/train_spread_matching_trial.py"),
        admission=ref(admission),
        methods=["V174-raw", "V174-EMA"],
        prior_figures=ref(
            REPO / ".cache/quality-20261107/V173-weak-gradient-matching-v1/figures-v1.json"
        ),
        baseline_scores=ref(
            REPO
            / ".cache/quality-20261107/V172-local-noise-matching-v1/scores-method-labels-v2.json"
        ),
        earlier_flat_scores=ref(
            REPO / ".cache/quality-20261107/V171-matching-residual-v1/scores-v1.json"
        ),
        earlier_quiet_scores=ref(
            REPO / ".cache/quality-20261107/V173-weak-gradient-matching-v1/scores-v1.json"
        ),
        minimum_GiB={"RAM": 32, "local": 49, "external": 110},
        prior_neural_hashes=previous,
        offset_initializer=ref(work / "scripts/spread_matching_offsets.py"),
        offset_grid_spacing=8,
        offset_probe_cases=probe_cases,
        projected_offset_array_bytes=offset_bytes,
        baseline_offset_diagnostic=ref(
            REPO / ".cache/quality-20261107/V174-offset-usage-v1/result-v1.json"
        ),
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    plan["inputs"] = [
        plan[k]
        for k in [
            "cache",
            "pair_units",
            "training_provenance",
            "design",
            "prior_scores",
            "parent_scores",
            "prior_figures",
            "baseline_scores",
            "earlier_flat_scores",
            "earlier_quiet_scores",
            "admission",
            "sampling_library",
            "baseline_offset_diagnostic",
        ]
    ] + [frozen["export"], *plan["metrics_sources"]]
    plan["matched_V172_recipe"] = {
        "reference_plan": ref(reference_path),
        "reference_training": ref(
            REPO / ".cache/quality-20261107/V172-local-noise-matching-v1/train-result-v1.json"
        ),
        "objective": ref(old_objective),
        "unchanged_function_ASTs": ["train", "runtime", "resources", "tree_equal"],
        "initializer": plan["offset_initializer"],
        "changed_initial_tensors": differences,
        "changed_initial_scalar_values": 60,
        "other183_initial_tensors_exact": True,
        "old_initial_module_hash": model_hash(old),
        "new_initial_module_hash": model_hash(module),
        "new_initial_network_hash": model_hash(module.network),
    }
    plan["scope"] = (
        "V174 spread sample initialization: same V172 local feature/output forward graph,2.09M/141 trainable tensors,96 neural files,frozen V169 EMA/V143-DINO,1000 V168 cached rows,pair units,exact7-term criterion and AdamW/LR/EMA schedule. Only5 initial offset bias vectors/60 scalar values change: nominal3x3 spacing8 instead of1,through inverse tanh of the existing residual. Search bound9 is unchanged.183 other initial state tensors match. Zero tail retains initial V169 output;zero variance routing/ADC skip unchanged. No target enters inference.900 noisy updates/100 skips with genuine step8 restore and no replay. Atomic sampler gradients remain warn-only nondeterministic,no bit-exact retraining claim. Both endpoints/all822 cases fixed,1644 V169 replays,144 exact ADC outputs.36 native cases retain72 RGB+72 residual arrays;30 pre-tanh offset arrays from6 primary EMA cases are additionally retained during existing quality calls,not extra forwards.48 boards/12 triplets retain160px native pixels and both protected GFX scenes/priors/windows/JPEGs. Real references qualitative,notGT,unscored. Baseline offset probe separately adds6 V172 CUDA matching calls/30 samplers. No source/noise draws,original/dataz reads or new parent/DINO calls. No blind generalization,causal receptive-field or noisy-flat guarantee."
    )
    save(ROOT / "plan-v1.json", plan)
    guard(plan)
    save(
        REPO / "docs/results/v174-spread-matching-preparation-v1.json",
        {
            "status": "prepared-before-training-and-candidate-quality",
            "plan": ref(ROOT / "plan-v1.json"),
            "plan_contents": plan,
            "source_texts": [
                dict(ref(p), text=p.read_text()) for p in work.rglob("*") if p.is_file()
            ],
            "admission": dict(ref(admission), contents=admitted),
            "CPU_tests": dict(
                ref(REPO / ".cache/v174-relevant-CPU-tests-v2.log"),
                text=(REPO / ".cache/v174-relevant-CPU-tests-v2.log").read_text(),
            ),
            "previous_neural_files_unchanged": 96,
            "new_neural_source_files": 0,
            "new_CPU_test_cases": 10,
            "baseline_probe": plan["baseline_offset_diagnostic"],
            "new_training_updates_so_far": 0,
            "new_candidate_heldout_forwards_so_far": 0,
            "scope": plan["scope"],
        },
    )
    check = subprocess.run(
        [
            str(REPO / ".venv/bin/python"),
            "-c",
            f"from balanced_spatial_metrics import DetailMetrics;from train_directional_bank_trial import read;import torch;p=read({str(ROOT / 'plan-v1.json')!r});DetailMetrics(p['metrics_sources']);assert not torch.cuda.is_initialized();print('Frozen metric runtime ready without neural calls')",
        ],
        env=dict(os.environ, PYTHONPATH=f"{work}/src:{work}/scripts"),
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
    print(
        "Prepared spread initialization;native/offset bytes",
        plan["projected_native_array_bytes"],
        offset_bytes,
    )


def make_module(plan, counts, *, state=None):
    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail

    m = LateLocalNoiseMatchingDetail(**plan["module_config"])
    from spread_matching_offsets import initialize_spread_offsets

    initialize_spread_offsets(m, spacing=plan["offset_grid_spacing"])
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
                method = f"V174-{endpoint}"
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
