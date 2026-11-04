"""Matched pre-support and delivered-output spectral objectives on identical heads."""

import argparse
import importlib.util
import json
import math
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from review_v146_window_transfer import relocated_controller_source
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
LIVE_PROGRESS = {}


def prepare(root):
    import numpy as np
    import yaml

    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    assert not root.exists()
    recipe = REPO / "configs/quality-v143-delivered-objective-v153.yaml"
    config = yaml.safe_load(recipe.read_text())
    previous = Path(config["previous_trial"])
    old = read(previous / "plan-v1.json")
    guard(old)
    assert ref(config["shared_training_recipe"]["path"]) == config["shared_training_recipe"]
    shared = yaml.safe_load(Path(config["shared_training_recipe"]["path"]).read_text())
    assert all(
        config[k] == shared[k]
        for k in ("steps", "batch_size", "max_window", "lr", "warmup", "gradient_clip", "EMA_decay")
    )
    cache_path = Path(old["cache"]["path"])
    cached = read(cache_path)
    assert cached["all1000_input_target_fingerprints_exact_V147"]
    assert cached["parent_before"] == cached["parent_after"]
    assert cached["DINO_before"] == cached["DINO_after"] == config["expected_DINO_sha256"]
    assert len(cached["batches"]) == 1000
    from noisy_objective import ADC_only

    assert sum(ADC_only(x["metadata"]["noise"]) for x in cached["batches"]) == 118
    assert all(len(x["metadata"]["cases"]) == 4 for x in cached["batches"])
    cases = read(previous / "quality-design-v1.json")["observations"]
    assert len(cases) == 822 and len({c["id"] for c in cases}) == 822
    expected_review_bytes = sum(
        int(np.prod(np.load(c["parent"]["path"], mmap_mode="r").shape)) * 4 * 6 for c in cases
    )
    assert shutil.disk_usage(REPO).free > 98 * 2**30 + expected_review_bytes
    assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
    assert psutil.virtual_memory().available > 52 * 2**30
    for item in cached["batches"]:
        path = Path(item["arrays"]["path"])
        assert path.is_relative_to(REPO) and path.is_file()
    root.mkdir(parents=True)
    work = root / "work"
    for source in (REPO / "src/demosaic").glob("*.py"):
        dest = work / "src/demosaic" / source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    for name in (
        "train_directional_bank_trial.py",
        "train_v43_quality_trial.py",
        "profile_raw_kernel_inference.py",
        "review_v146_window_transfer.py",
        "noisy_objective.py",
        "delivered_spectral_objective.py",
    ):
        dest = work / "scripts" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, dest)
    runner = work / "scripts" / Path(__file__).name
    runner.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    target = work / "configs" / recipe.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(recipe, target)
    save(
        root / "quality-design-v1.json",
        {
            "observations": cases,
            "endpoints": [
                f"{arm}-{endpoint}-step1000"
                for arm in config["arms"]
                for endpoint in ("raw", "EMA")
            ],
            "new_component_forwards": 4932,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "scope": "All6 fixed final endpoints on822 cases:retained798 plus24 fixed ADC controls. Exact blank/quiet errors and both standing real scenes,priors,windows,JPEGs. Qualitative real references notGT. Adaptive reused cohort.",
        },
    )
    baseline = read(previous / "review-result-v1.json")["collections"][
        "relative-phase-raw-step1000"
    ]
    collection = read(baseline["path"])
    plan = {
        "root": str(root),
        "work": str(work),
        "config": ref(target),
        "runner": ref(runner),
        "parent": config["parent"],
        "previous": str(previous),
        "shared_recipe": config["shared_training_recipe"],
        "cache": ref(cache_path),
        "prefix": cached["batches"][:10],
        "legacy_relative": ref(Path(old["work"]) / "src/demosaic/late_spectral_relative.py"),
        "baseline_training": ref(previous / "train-result-v1.json"),
        "baseline_collection": baseline,
        "baseline_export": collection["export"],
        "inputs": [
            ref(recipe),
            ref(target),
            ref(previous / "plan-v1.json"),
            ref(cache_path),
            ref(cache_path.parent / "cache-trace-v1.jsonl"),
            ref(previous / "quality-design-v1.json"),
            ref(config["parent"]["path"]),
            config["shared_training_recipe"],
            baseline,
            collection["export"],
            ref(root / "quality-design-v1.json"),
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "source_modules": len(list((work / "src/demosaic").glob("*.py"))),
        "new_parent_DINO_forwards": 0,
        "new_noise_draws": 0,
        "adopted_training_observations": 4000,
        "ADC_training_batches": 118,
        "noisy_training_batches": 882,
        "expected_quality_output_bytes": expected_review_bytes,
        "scope": config["scope"],
    }
    assert plan["source_modules"] == 86
    for name, digest in old["frozen_files"].items():
        source = Path(name)
        if source.parent.name == "demosaic":
            assert ref(work / "src/demosaic" / source.name)["sha256"] == digest
    plan["inputs"] += [plan["legacy_relative"], plan["baseline_training"]]
    save(
        root / "preflight-v1.json",
        {
            "status": "pass-source-cache-and-headroom",
            "adopted_cache_batches": 1000,
            "adopted_observations": 4000,
            "new_parent_DINO_or_noise": 0,
            "expected_quality_output_bytes": expected_review_bytes,
            "frozen_neural_sources": 86,
            "scope": "V148 training cache and all822 V152 quality cases/parents are read only. Three fresh identical relative-phase heads adopt the same4000 old observations; only spectral-loss site/color coverage differs. All86 neural files unchanged, no new parent/DINO/noise or original lookup.",
        },
    )
    plan["inputs"].append(ref(root / "preflight-v1.json"))
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def classes():
    from demosaic.late_spectral_relative import LateSpectralRelativeDetail

    return {
        name: LateSpectralRelativeDetail
        for name in ["pre-control", "delivered-mosaic", "delivered-RGB"]
    }


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
    torch.use_deterministic_algorithms(True)
    torch.cuda.set_per_process_memory_fraction(
        12 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    assert psutil.virtual_memory().available > 52 * 2**30


def resource_check(root):
    assert psutil.virtual_memory().available > 32 * 2**30
    assert shutil.disk_usage(root).free > 96 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 208 * 2**30


def parity(plan):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    root = Path(plan["root"])
    assert ref(plan["legacy_relative"]["path"]) == plan["legacy_relative"]
    spec = importlib.util.spec_from_file_location(
        "demosaic._v152_frozen_relative", plan["legacy_relative"]["path"]
    )
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    saved = torch.load(plan["baseline_export"]["path"], map_location="cpu", weights_only=True)
    module = classes()["pre-control"](256).cuda().eval()
    frozen = legacy.LateSpectralRelativeDetail(256).cuda().eval()
    module.load_state_dict(saved["state_dict"], strict=True)
    frozen.load_state_dict(saved["state_dict"], strict=True)
    collection = read(plan["baseline_collection"]["path"])
    archived = {o["id"]: o["prediction"] for o in collection["observations"]}
    cases = read(root / "quality-design-v1.json")["observations"]
    selected = [c for c in cases if c["kind"] == "mesh" and c["seed"] == 2026112302]
    selected += [
        c
        for c in cases
        if c["kind"] == "photo"
        and (
            "3e638bbb" in c["id"]
            or ("02a76fd3" in c["id"] and c["variant"]["name"] == "photo-faint")
        )
    ]
    selected += [
        c
        for c in cases
        if c["kind"] == "flat"
        and c["id"]
        in (
            "flat512-gray-l0.02-adc-only-RGGB",
            "flat512-gray-l0.02-iso6400-prior-RGGB",
            "gray-l0.02-adc-only-RGGB",
            "gray-l0.02-iso12800-prior-RGGB",
        )
    ]
    selected += [
        c
        for c in cases
        if c["kind"] == "real"
        and (
            c["id"].startswith("mesh-") or c["id"] in ("main-overcast-sky", "main-building-detail")
        )
    ]
    assert len(selected) == 28
    before, frozen_before = model_hash(module), model_hash(frozen)
    rows = []
    for case in selected:
        resource_check(root)
        assert (
            ref(case["arrays"]["path"]) == case["arrays"]
            and ref(case["parent"]["path"]) == case["parent"]
        )
        a = dict(np.load(case["arrays"]["path"]))
        base = torch.from_numpy(np.load(case["parent"]["path"])).cuda()
        inputs = [torch.from_numpy(a[k]).cuda() for k in ("packed", "variance", "colors", "wb")]
        with torch.inference_mode():
            first = module(base, *inputs).cpu().numpy()
            second = frozen(base, *inputs).cpu().numpy()
        np.testing.assert_array_equal(first, second)
        assert ref(archived[case["id"]]["path"]) == archived[case["id"]]
        np.testing.assert_array_equal(first, np.load(archived[case["id"]]["path"]))
        rows.append({"id": case["id"], "exact_frozen_relative_forward_and_archived": True})
    assert model_hash(module) == before and model_hash(frozen) == frozen_before
    save(
        root / "parity-result-v1.json",
        {
            "status": "pass28-exact-relative-control-replays",
            "plan": ref(root / "plan-v1.json"),
            "legacy_relative": plan["legacy_relative"],
            "baseline_export": plan["baseline_export"],
            "rows": rows,
            "component_forward_evaluations": 56,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Current and frozen V152 relative-phase heads agree exactly on28 native256/384/512/768 contexts across all CFAs and protected real controls. Both match saved V152 relative raw outputs. Two actual evaluations per case,56 total. No architecture or forward changes; only training loss differs.",
        },
    )


def fit(plan, phase):
    import numpy as np
    import torch
    import yaml
    from delivered_spectral_objective import spectral_loss
    from noisy_objective import ADC_only, apply_ADC_weight

    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    config = yaml.safe_load(Path(plan["shared_recipe"]["path"]).read_text())
    recipe = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    counts = {label: 0 for label in recipe["arms"]}
    updates = dict(counts)
    supervised = dict(counts)
    zero_ADC = dict(counts)
    peak_evaluations = dict(counts)
    LIVE_PROGRESS.update(phase=phase, counts=counts, updates=updates, last_completed_step=0)

    def fresh():
        modules = {k: classes()[k](256).cuda() for k in recipe["arms"]}
        for name, value in modules["pre-control"].state_dict().items():
            assert all(torch.equal(value, m.state_dict()[name]) for m in modules.values())
        assert all(m.relative_in.weight.count_nonzero() == 0 for m in modules.values())
        for label, m in modules.items():
            assert (
                sum(p.numel() for p in m.parameters()) == recipe["arms"][label]["parameters"]
                and len(m.state_dict()) == recipe["arms"][label]["parameter_tensors"]
            )
            m.register_forward_hook(
                lambda *args, label=label: counts.__setitem__(label, counts[label] + 1)
            )
        opts = {k: torch.optim.AdamW(m.parameters(), lr=config["lr"]) for k, m in modules.items()}
        emas = {
            k: {n: v.detach().clone() for n, v in m.state_dict().items()}
            for k, m in modules.items()
        }
        return modules, opts, emas

    modules, optimizers, emas = fresh()
    maximum = {k: {n: 0.0 for n, _ in m.named_parameters()} for k, m in modules.items()}
    cache_rows = read(plan["cache"]["path"])["batches"] if phase == "train" else plan["prefix"]
    reference_trace = read(plan["baseline_training"]["path"])["trace"]
    checkpointdir = root / "checkpoints"
    checkpointdir.mkdir(exist_ok=True)
    trace = []
    last = 0
    journal = (root / f"{phase}-trace-v1.jsonl").open("x")

    def checkpoint(step):
        dest = checkpointdir / f"{phase}-step{step:04d}.pt"
        assert not dest.exists()
        with dest.open("xb") as stream:
            torch.save(
                {
                    "step": step,
                    "horizon": 1000,
                    "module_config": {"max_window": 256},
                    "arms": recipe["arms"],
                    "models": {k: m.state_dict() for k, m in modules.items()},
                    "emas": emas,
                    "optimizers": {k: o.state_dict() for k, o in optimizers.items()},
                    "counts": dict(counts),
                    "updates": dict(updates),
                    "parent": plan["parent"],
                    "plan": ref(root / "plan-v1.json"),
                    "config": config,
                    "torch_CPU_RNG": torch.get_rng_state(),
                    "torch_CUDA_RNG": torch.cuda.get_rng_state(),
                },
                stream,
            )
        return dest

    for step in range(1, 11 if phase == "smoke" else 1001):
        resource_check(root)
        item = cache_rows[step - 1]
        assert ref(item["arrays"]["path"]) == item["arrays"]
        a = dict(np.load(item["arrays"]["path"]))
        base = a.pop("parent")
        assert {k: fingerprint(v) for k, v in a.items()} == item["inputs"]
        batch = {k: torch.from_numpy(v).cuda() for k, v in a.items()}
        base = torch.from_numpy(base).cuda()
        row = {
            "step": step,
            "batch": item["arrays"],
            "domain": item["metadata"]["domain"],
            "arms": {},
        }
        progress = max(0, step - config["warmup"]) / max(1, 1000 - config["warmup"])
        lr = (
            config["lr"]
            * min(1, step / config["warmup"])
            * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        )
        for label, module in modules.items():
            optimizer = optimizers[label]
            optimizer.zero_grad(set_to_none=True)
            for group in optimizer.param_groups:
                group["lr"] = lr
            output, aux = module(
                base, *(batch[k] for k in ("packed", "variance", "colors", "wb")), return_aux=True
            )
            if step == 1:
                assert torch.equal(output, base) and aux["correction"].count_nonzero() == 0
            scale = (
                batch["variance"]
                .clamp_min(0)
                .mean((1, 2, 3), keepdim=True)
                .sqrt()
                .clamp_min(recipe["arms"][label]["loss_floor_DN16"] / 65535)
            )
            error = (output - batch["target"]) / scale
            pixel = (error.square() + config["pixel_epsilon_in_noise_units"] ** 2).sqrt().mean()
            derivatives = [error[..., 1:] - error[..., :-1], error[..., 1:, :] - error[..., :-1, :]]
            gradient = (
                sum(
                    (v.square() + config["gradient_epsilon_in_noise_units"] ** 2).sqrt().mean()
                    for v in derivatives
                )
                / 2
            )
            arm = recipe["arms"][label]
            is_ADC = ADC_only(item["metadata"]["noise"])
            peak_bonus = arm["spectral_peak_bonus"] if not is_ADC else 0
            assert peak_bonus == 0
            spectral = spectral_loss(
                module,
                output,
                batch["target"],
                batch["colors"],
                aux,
                arm["loss_floor_DN16"],
                arm["spectral_site"],
            )
            peak_evaluations[label] += int(peak_bonus > 0)
            loss = config["domain_loss_weights"][row["domain"]] * (
                pixel + config["gradient_weight"] * gradient + config["spectral_weight"] * spectral
            )
            loss = apply_ADC_weight(loss, item["metadata"]["noise"], arm["ADC_loss_weight"])
            has_supervision = not (is_ADC and arm["ADC_loss_weight"] == 0)
            supervised[label] += int(has_supervision)
            zero_ADC[label] += int(not has_supervision)
            assert torch.isfinite(loss)
            loss.backward()
            for name, p in module.named_parameters():
                assert p.grad is not None and torch.isfinite(p.grad).all()
                maximum[label][name] = max(maximum[label][name], float(p.grad.abs().max()))
                if not has_supervision:
                    assert p.grad.count_nonzero() == 0
            if not has_supervision:
                assert loss == 0
            norm = torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            updates[label] += 1
            decay = min(config["EMA_decay"], (1 + step) / (10 + step))
            with torch.no_grad():
                for name, value in module.state_dict().items():
                    emas[label][name].lerp_(value, 1 - decay)
            row["arms"][label] = {
                "loss": float(loss.detach()),
                "pixel": float(pixel.detach()),
                "gradient": float(gradient.detach()),
                "spectral": float(spectral.detach()),
                "gradient_norm": float(norm),
                "lr": lr,
            }
            if label == "pre-control":
                assert row["arms"][label] == reference_trace[step - 1]["arms"]["relative-phase"], (
                    phase,
                    step,
                )
            del output, aux, error, pixel, derivatives, gradient, spectral, loss, scale
        trace.append(row)
        journal.write(json.dumps(row, allow_nan=False) + "\n")
        journal.flush()
        LIVE_PROGRESS["last_completed_step"] = step
        last = step
        if step == 1 or step % 10 == 0:
            print(
                json.dumps(
                    {
                        "phase": phase,
                        "step": step,
                        "arms": row["arms"],
                        "CUDA_allocated_bytes": torch.cuda.memory_allocated(),
                    }
                ),
                flush=True,
            )
            save(
                root / f"{phase}-progress-v1.json",
                {"step": step, "counts": counts, "updates": updates},
            )
        del batch, base, a
        if phase == "smoke" and step == 8:
            path = checkpoint(8)
            s = torch.load(path, map_location="cpu", weights_only=True)
            modules, optimizers, emas = fresh()
            for label in modules:
                modules[label].load_state_dict(s["models"][label], strict=True)
                optimizers[label].load_state_dict(s["optimizers"][label])
                emas[label] = {n: v.cuda() for n, v in s["emas"][label].items()}
                assert len(optimizers[label].state) == recipe["arms"][label][
                    "parameter_tensors"
                ] and all(float(v["step"]) == 8 for v in optimizers[label].state.values())
                assert all(
                    torch.equal(v.cpu(), s["models"][label][n])
                    for n, v in modules[label].state_dict().items()
                )
            torch.set_rng_state(s["torch_CPU_RNG"])
            torch.cuda.set_rng_state(s["torch_CUDA_RNG"])
            del s
        if phase == "train" and step % 250 == 0:
            checkpoint(step)
    journal.close()
    final = checkpoint(last) if phase == "smoke" else checkpointdir / "train-step1000.pt"
    assert counts == updates == {k: last for k in modules}
    for label, module in modules.items():
        assert (
            min(maximum[label].values()) > 0
            and len(optimizers[label].state) == recipe["arms"][label]["parameter_tensors"]
        )
        assert all(float(v["step"]) == last for v in optimizers[label].state.values())
        assert all(
            torch.isfinite(t).all()
            for state in optimizers[label].state.values()
            for t in state.values()
        )
        assert all(
            torch.isfinite(v).all() for v in [*module.state_dict().values(), *emas[label].values()]
        )
    expected_ADC = sum(ADC_only(x["metadata"]["noise"]) for x in cache_rows[:last])
    assert supervised == {
        k: last - (expected_ADC if v["ADC_loss_weight"] == 0 else 0)
        for k, v in recipe["arms"].items()
    }
    assert zero_ADC == {
        k: (expected_ADC if v["ADC_loss_weight"] == 0 else 0) for k, v in recipe["arms"].items()
    }
    assert peak_evaluations == {
        k: (last - expected_ADC if v["spectral_peak_bonus"] else 0)
        for k, v in recipe["arms"].items()
    }
    guard(plan)
    save(
        root / f"{phase}-result-v1.json",
        {
            "status": "completed-matched-head-phase",
            "phase": phase,
            "steps": last,
            "plan": ref(root / "plan-v1.json"),
            "checkpoint": ref(final),
            "counts": counts,
            "updates": updates,
            "supervised_batches": supervised,
            "zero_ADC_gradient_batches": zero_ADC,
            "peak_weight_evaluations": peak_evaluations,
            "parameter_maximum_gradients": maximum,
            "loss_floors_DN16": {k: v["loss_floor_DN16"] for k, v in recipe["arms"].items()},
            "initial_outputs_exact_parent": True,
            "trace": trace,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Three fresh identical33713-parameter/13-tensor relative heads share4000 cached observations and noisy-only16DN routing. Only spectral loss changes from pre-support CFA coefficients to delivered mosaic or all-RGB phase-packed error. Same0.25 coefficient,frequency band/frame/noise scale;RGB repeats CFA proxies as training units,not calibrated covariance. Pixel/gradient terms remain delivered RGB. Pre-control trace exactly replays V152 relative at every completed step.882 supervised batches,118 zero-ADC gradients,all1000 AdamW/EMA clocks; smoke discarded. All86 neural files unchanged. No target/reference enters forward;zero new parent/DINO/noise/original/dataz access.",
        },
    )


def worker(path, phase):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["runner"]
    (root / f"{phase}.claim").open("x").close()
    runtime(plan)
    try:
        if phase == "parity":
            parity(plan)
        else:
            fit(plan, phase)
    except BaseException as error:
        save(
            root / f"{phase}-failure-v1.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "progress": LIVE_PROGRESS,
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            },
        )
        raise


def controller(path):
    plan = read(path)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None
    try:
        for phase in ("parity", "smoke", "train"):
            guard(plan)
            while psutil.virtual_memory().available < 52 * 2**30:
                save(
                    root / "status-v1.json",
                    {**state, "status": "waiting-for-headroom", "phase": phase},
                )
                time.sleep(2)
            env = dict(
                os.environ,
                PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
                OMP_NUM_THREADS="2",
                OPENBLAS_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                CUDA_VISIBLE_DEVICES="0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
            )
            with (root / f"{phase}-v1.log").open("x") as log:
                child = subprocess.Popen(
                    [
                        str(REPO / ".venv/bin/python"),
                        "-P",
                        plan["runner"]["path"],
                        "worker",
                        str(path),
                        "--phase",
                        phase,
                    ],
                    cwd=plan["work"],
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                save(
                    root / "status-v1.json",
                    {**state, "status": "running-declared-phase", "phase": phase, "child": owner},
                )
                observed = 0.0
                last = time.monotonic()
                while child.poll() is None:
                    time.sleep(2)
                    now = time.monotonic()
                    if live(owner) and psutil.Process(child.pid).status() != psutil.STATUS_STOPPED:
                        observed += min(now - last, 5.0)
                    last = now
                    assert observed < (1800 if phase in ("parity", "smoke") else 7200), phase
                assert child.returncode == 0, phase
            assert not live(owner)
            state["completed"][phase] = ref(root / f"{phase}-result-v1.json")
        save(
            root / "status-v1.json",
            {**state, "status": "completed-matched-training-awaiting-fixed-quality-review"},
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        save(
            root / "status-v1.json",
            {**state, "status": "failed-preserved-no-automatic-retry", "error": repr(error)},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("parity", "smoke", "train"))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    elif args.mode == "worker":
        worker(args.path.resolve(), args.phase)
    else:
        controller(args.path.resolve())
