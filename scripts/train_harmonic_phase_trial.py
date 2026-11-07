"""Matched V162 flat-anchor control and cross-frequency phase inputs."""

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
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    recipe = REPO / "configs/quality-v143-harmonic-phase-v163.yaml"
    config = yaml.safe_load(recipe.read_text())
    assert list(config["arms"]) == ["anchor-control", "harmonic-phase"]
    previous = Path(config["previous_trial"])
    prior = read(previous / "plan-v1.json")
    guard(prior)
    shared = config["shared_training_recipe"]
    assert ref(shared["path"]) == shared
    oldconfig = yaml.safe_load(Path(shared["path"]).read_text())
    control, candidate = config["arms"].values()
    assert control == oldconfig["arms"]["flat-anchor"]
    assert {
        k: v for k, v in control.items() if k not in ["class", "parameters", "parameter_tensors"]
    } == {
        k: v for k, v in candidate.items() if k not in ["class", "parameters", "parameter_tensors"]
    }
    assert (control["parameters"], candidate["parameters"]) == (124397, 124909)
    assert (control["parameter_tensors"], candidate["parameter_tensors"]) == (46, 47)
    assert all(
        config[k] == oldconfig[k]
        for k in [
            "max_window",
            "steps",
            "batch_size",
            "lr",
            "warmup",
            "gradient_clip",
            "EMA_decay",
            "pixel_epsilon_in_noise_units",
            "gradient_epsilon_in_noise_units",
            "gradient_weight",
            "spectral_weight",
            "pair_epsilon",
            "domain_loss_weights",
            "local_risk_window_native",
            "local_risk_transition_noise_units",
            "regional_DC_window_native",
            "flat_anchor_window",
            "flat_anchor_tolerance_DN16",
            "flat_anchor_unit_DN16",
        ]
    )
    cache_path = Path(prior["cache"]["path"])
    assert ref(cache_path) == prior["cache"]
    cache = read(cache_path)
    assert (
        len(cache["batches"]) == 1000
        and cache["parent_before"] == cache["parent_after"]
        and cache["DINO_before"] == cache["DINO_after"]
    )
    cases = read(previous / "quality-design-v1.json")["observations"]
    assert len(cases) == len({c["id"] for c in cases}) == 822
    selected = []
    for c in cases:
        mesh = (
            c["kind"] == "mesh" and c["seed"] in [2026112302, 2026112309] and c["pattern"] == "RGGB"
        )
        flat = c["id"] in [
            "flat512-gray-l0.02-iso6400-prior-RGGB",
            "flat512-gray-l0.02-iso12800-prior-RGGB",
        ]
        quiet = c["id"] in [
            "mixed-vertical-step-iso6400-prior-RGGB",
            "mixed-vertical-step-iso12800-prior-RGGB",
        ]
        real = c["kind"] == "real" and (
            c["id"].startswith("mesh-") or c["id"] == "main-overcast-sky"
        )
        photo = (
            c["kind"] == "photo"
            and "02a76fd3" in c["id"]
            and c["variant"]["name"] == "photo-faint"
            and c["pattern"] == "RGGB"
        )
        if mesh or flat or quiet or real or photo:
            selected.append(c["id"])
    assert len(selected) == len(set(selected)) == 12
    per_endpoint = sum(np.load(c["parent"]["path"], mmap_mode="r").nbytes + 128 for c in cases)
    removal_bytes = 2 * sum(
        np.load(c["parent"]["path"], mmap_mode="r").nbytes + 128
        for c in cases
        if c["id"] in selected
    )
    external = Path(config["external_root"])
    assert external.is_relative_to("/mnt/external") and not external.exists()
    assert shutil.disk_usage(REPO).free > 60.75 * 2**30
    assert (
        shutil.disk_usage("/mnt/external").free > 148.5 * 2**30 + 2 * per_endpoint + removal_bytes
    )
    assert psutil.virtual_memory().available > 52 * 2**30
    root.mkdir(parents=True)
    external.mkdir(parents=True)
    work = root / "work"
    sources = list((REPO / "src/demosaic").glob("*.py"))
    sources += [
        REPO / "scripts" / n
        for n in [
            "train_directional_bank_trial.py",
            "train_v43_quality_trial.py",
            "profile_raw_kernel_inference.py",
            "review_v146_window_transfer.py",
            "noisy_objective.py",
            "delivered_spectral_objective.py",
            "robust_spectral_objective.py",
            "local_excess_risk.py",
            "regional_dc_objective.py",
            "paired_response_objective.py",
            "flat_target_anchor.py",
            "review_harmonic_phase_trial.py",
            "diagnose_harmonic_phase_trial.py",
        ]
    ]
    sources += [
        REPO / "tests" / n
        for n in [
            "test_flat_target_anchor.py",
            "test_late_harmonic_context.py",
            "test_late_harmonic_phase.py",
        ]
    ]
    for source in sources:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    runner = work / "scripts" / Path(__file__).name
    runner.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    target = work / "configs" / recipe.name
    target.parent.mkdir(parents=True)
    shutil.copyfile(recipe, target)
    review = read(previous / "review-result-v1.json")
    controls = {
        f"anchor-control-{e}-step1000": review["collections"][f"flat-anchor-{e}-step1000"]
        for e in ["raw", "EMA"]
    }
    baseline = controls["anchor-control-raw-step1000"]
    collection = read(baseline["path"])
    save(
        root / "quality-design-v1.json",
        {
            "observations": cases,
            "endpoints": [f"{a}-{e}-step1000" for a in config["arms"] for e in ["raw", "EMA"]],
            "new_component_forwards": 3288,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "phase_removal": {
                "case_ids": selected,
                "endpoints": ["harmonic-phase-raw-step1000", "harmonic-phase-EMA-step1000"],
                "new_head_calls": 48,
                "new_off_arrays": 24,
                "expected_bytes": removal_bytes,
            },
            "scope": "Four fixed endpoints/822 cases;1644 actual control replays before storage adoption/1644 new candidate arrays. Additional fixed12 contexts/raw-EMA/on-off48 calls;24 off arrays external. Real references qualitative,not exactGT.",
        },
    )
    plan = {
        "root": str(root),
        "work": str(work),
        "runner": ref(runner),
        "config": ref(target),
        "parent": config["parent"],
        "previous": str(previous),
        "cache": ref(cache_path),
        "prefix": cache["batches"][:10],
        "baseline_training": ref(previous / "train-result-v1.json"),
        "baseline_collection": baseline,
        "baseline_export": collection["export"],
        "control_collections": controls,
        "legacy_harmonic": ref(Path(prior["work"]) / "src/demosaic/late_harmonic_context.py"),
        "external_quality_root": str(external),
        "external_root": str(external),
        "quality_output_roots": {
            f"{a}-{e}-step1000": str((root if a == "anchor-control" else external) / "review-v1")
            for a in config["arms"]
            for e in ["raw", "EMA"]
        },
        "expected_new_quality_bytes_external": 2 * per_endpoint,
        "expected_new_quality_bytes_per_endpoint": per_endpoint,
        "expected_phase_removal_bytes": removal_bytes,
        "new_parent_DINO_forwards": 0,
        "new_noise_draws": 0,
        "inputs": [
            ref(recipe),
            ref(target),
            ref(previous / "plan-v1.json"),
            ref(cache_path),
            shared,
            ref(previous / "train-result-v1.json"),
            ref(previous / "quality-design-v1.json"),
            baseline,
            collection["export"],
            *controls.values(),
            ref(root / "quality-design-v1.json"),
            ref(REPO / "docs/results/harmonic-phase-research-20261107-v1.json"),
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "source_modules": len(list((work / "src/demosaic").glob("*.py"))),
        "scope": config["scope"],
    }
    assert plan["source_modules"] == 89
    old_neural = {
        p: h for p, h in prior["frozen_files"].items() if Path(p).parent.name == "demosaic"
    }
    assert len(old_neural) == 88
    for p, h in old_neural.items():
        assert ref(work / "src/demosaic" / Path(p).name)["sha256"] == h
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def classes():
    from demosaic.late_harmonic_context import LateHarmonicContextDetail
    from demosaic.late_harmonic_phase import LateHarmonicPhaseDetail

    return {"anchor-control": LateHarmonicContextDetail, "harmonic-phase": LateHarmonicPhaseDetail}


def equal_tree(first, second):
    import torch

    if isinstance(first, torch.Tensor):
        return isinstance(second, torch.Tensor) and torch.equal(first.cpu(), second.cpu())
    if isinstance(first, dict):
        return first.keys() == second.keys() and all(
            equal_tree(v, second[k]) for k, v in first.items()
        )
    if isinstance(first, (list, tuple)):
        return (
            type(first) is type(second)
            and len(first) == len(second)
            and all(equal_tree(a, b) for a, b in zip(first, second, strict=True))
        )
    return first == second


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
    assert shutil.disk_usage(root).free > 60 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 148 * 2**30


def cuda_loss_checks(plan):
    import numpy as np
    import torch
    from flat_target_anchor import flat_target_anchor_loss, flat_target_mask

    from demosaic.prediction_archive import fingerprint

    records = []
    for row in plan["prefix"]:
        resource_check(Path(plan["root"]))
        a = dict(np.load(row["arrays"]["path"]))
        clean = a["target"]
        base = np.load(row["parent"]["path"])

        def maximum(x):
            height, width = x.shape[-2:]
            p = np.pad(x, ((0, 0), (0, 0), (0, 0), (8, 8)), mode="edge")
            x = np.maximum.reduce([p[..., i : i + width] for i in range(17)])
            p = np.pad(x, ((0, 0), (0, 0), (8, 8), (0, 0)), mode="edge")
            return np.maximum.reduce([p[..., i : i + height, :] for i in range(17)])

        mask = (maximum(clean) + maximum(-clean)).max(1, keepdims=True) <= 1 / 65535
        target = torch.from_numpy(clean).cuda()
        actual_mask = flat_target_mask(target)
        np.testing.assert_array_equal(actual_mask.cpu().numpy(), mask)
        value = torch.from_numpy(base).cuda().requires_grad_()
        loss = flat_target_anchor_loss(value, target, actual_mask)
        loss.backward()
        error = (base.astype(np.float64) - clean.astype(np.float64)) * 65535 / 16
        expected = float(np.mean(error**2 / (np.sqrt(1 + error**2) + 1) * mask))
        derivative = error / np.sqrt(1 + error**2) * (65535 / 16) / error.size * mask
        np.testing.assert_allclose(float(loss.detach()), expected, rtol=2e-6, atol=1e-8)
        actual = value.grad.cpu().numpy()
        np.testing.assert_allclose(actual, derivative, rtol=2e-5, atol=2e-8)
        records.append(
            {
                "step": row["step"],
                "domain": row["metadata"]["domain"],
                "mask": fingerprint(mask),
                "eligible_pixels": int(mask.sum()),
                "total_pixels": mask.size,
                "loss": float(loss.detach()),
                "independent_loss": expected,
                "maximum_adjoint_difference": float(np.max(np.abs(actual - derivative))),
                "leaf_backwards": 1,
                "neural_forwards": 0,
            }
        )
        del target, actual_mask, value, loss, error, derivative, actual
    assert len(records) == 10
    return records


def parity(plan):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    assert ref(plan["legacy_harmonic"]["path"]) == plan["legacy_harmonic"]
    spec = importlib.util.spec_from_file_location(
        "demosaic._v162_frozen_harmonic", plan["legacy_harmonic"]["path"]
    )
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    saved = torch.load(plan["baseline_export"]["path"], map_location="cpu", weights_only=True)
    module = classes()["harmonic-phase"](256).cuda().eval()
    frozen = legacy.LateHarmonicContextDetail(256).cuda().eval()
    missing, unexpected = module.load_state_dict(saved["state_dict"], strict=False)
    assert missing == ["phase_in.weight"] and not unexpected
    assert module.phase_in.weight.count_nonzero() == 0
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
        assert fingerprint(first) == fingerprint(second)
        assert ref(archived[case["id"]]["path"]) == archived[case["id"]]
        np.testing.assert_array_equal(first, np.load(archived[case["id"]]["path"]))
        rows.append(
            {
                "id": case["id"],
                "exact_frozen_harmonic_forward_and_archived": True,
            }
        )
    assert model_hash(module) == before and model_hash(frozen) == frozen_before
    loss_checks = cuda_loss_checks(plan)
    save(
        root / "parity-result-v1.json",
        {
            "status": "pass28-exact-harmonic-replays-and10-CUDA-loss-checks",
            "plan": ref(root / "plan-v1.json"),
            "legacy_harmonic": plan["legacy_harmonic"],
            "baseline_export": plan["baseline_export"],
            "rows": rows,
            "CUDA_anchor_loss_checks": loss_checks,
            "component_forward_evaluations": 56,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Zero-phase-adapter V163 candidate and frozen V162 flat-anchor class replay28 archived outputs/all CFAs/native256/384/512/768/both scenes:56 calls. All88 prior neural sources unchanged;one new module. Additional10 prefix leaf-output backwards independently check flat-mask/loss/gradient arithmetic;these are not neural forwards. New mask/targets only define loss,never inference.",
        },
    )


def fit(plan, phase):
    import numpy as np
    import torch
    import yaml
    from flat_target_anchor import flat_target_anchor_loss, flat_target_mask
    from local_excess_risk import local_excess_risk
    from noisy_objective import ADC_only, apply_ADC_weight
    from paired_response_objective import paired_response_loss
    from regional_dc_objective import regional_dc_excess
    from robust_spectral_objective import spectral_loss

    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    config = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    recipe = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    counts = {label: 0 for label in recipe["arms"]}
    updates = dict(counts)
    supervised = dict(counts)
    zero_ADC = dict(counts)
    peak_evaluations = dict(counts)
    LIVE_PROGRESS.update(phase=phase, counts=counts, updates=updates, last_completed_step=0)

    def fresh():
        modules = {k: classes()[k](256).cuda() for k in recipe["arms"]}
        for name, value in modules["anchor-control"].state_dict().items():
            assert all(torch.equal(value, m.state_dict()[name]) for m in modules.values())
        assert all(m.relative_in.weight.count_nonzero() == 0 for m in modules.values())
        assert modules["harmonic-phase"].harmonic_in.weight.count_nonzero() == 0
        assert modules["harmonic-phase"].phase_in.weight.count_nonzero() == 0
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
    cache_rows = read(plan["cache"]["path"])["batches"]
    reference_trace = read(plan["baseline_training"]["path"])["trace"]
    compatible_steps = 0
    smoke_trace = read(root / "smoke-result-v1.json")["trace"] if phase == "train" else None
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
        assert ref(item["parent"]["path"]) == item["parent"]
        base = np.load(item["parent"]["path"])
        assert fingerprint(base) == item["parent_values"]
        assert {k: fingerprint(v) for k, v in a.items()} == item["inputs"]
        batch = {k: torch.from_numpy(v).cuda() for k, v in a.items()}
        base = torch.from_numpy(base).cuda()
        row = {
            "step": step,
            "batch": item["arrays"],
            "domain": item["metadata"]["domain"],
            "arms": {},
        }
        mask = flat_target_mask(
            batch["target"],
            window=recipe["flat_anchor_window"],
            tolerance_DN16=recipe["flat_anchor_tolerance_DN16"],
        )
        mask_cpu = mask.cpu().numpy()
        row["flat_target_mask"] = {
            "values": fingerprint(mask_cpu),
            "eligible_pixels": int(mask_cpu.sum()),
            "total_pixels": mask_cpu.size,
            "per_image_eligible_pixels": [int(v.sum()) for v in mask_cpu],
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
                arm["penalty"],
                arm["spectral_epsilon"],
            )
            peak_evaluations[label] += int(peak_bonus > 0)
            loss = config["domain_loss_weights"][row["domain"]] * (
                pixel + config["gradient_weight"] * gradient + config["spectral_weight"] * spectral
            )
            local_penalty = output.new_zeros(())
            if arm["local_risk_weight"]:
                local_penalty = local_excess_risk(
                    output,
                    base,
                    batch["target"],
                    scale,
                    window=recipe["local_risk_window_native"],
                    transition=recipe["local_risk_transition_noise_units"],
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["local_risk_weight"]
                    * local_penalty
                )
            dc_penalty = output.new_zeros(())
            if arm["regional_DC_weight"]:
                dc_penalty = regional_dc_excess(
                    output,
                    base,
                    batch["target"],
                    scale,
                    window=recipe["regional_DC_window_native"],
                    transition=arm["regional_DC_transition_units"],
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["regional_DC_weight"]
                    * dc_penalty
                )
            pair_penalty = output.new_zeros(())
            if arm["paired_response_weight"] and len(batch["pair_indices"]):
                pair_penalty = paired_response_loss(
                    output,
                    batch["target"],
                    batch["pair_units"],
                    batch["pair_indices"],
                    epsilon=recipe["pair_epsilon"],
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["paired_response_weight"]
                    * pair_penalty
                )
            anchor_penalty = output.new_zeros(())
            if arm["flat_anchor_weight"]:
                anchor_penalty = flat_target_anchor_loss(
                    output, batch["target"], mask, unit_DN16=recipe["flat_anchor_unit_DN16"]
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["flat_anchor_weight"]
                    * anchor_penalty
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
                "local_excess_risk": float(local_penalty.detach()),
                "regional_DC_excess": float(dc_penalty.detach()),
                "regional_DC_transition_units": arm["regional_DC_transition_units"],
                "paired_response": float(pair_penalty.detach()),
                "flat_target_anchor": float(anchor_penalty.detach()),
                "coupled_pairs": len(batch["pair_indices"]),
                **(
                    {
                        "spatial_correction_RMS_DN16": float(
                            aux["spatial_correction"].detach().square().mean().sqrt()
                        )
                        * 65535
                    }
                    if "spatial_correction" in aux
                    else {}
                ),
            }
            if label == "anchor-control":
                expected = reference_trace[step - 1]["arms"]["flat-anchor"]
                assert {k: row["arms"][label][k] for k in expected} == expected, (
                    phase,
                    step,
                    "V162 control trace",
                )
                compatible_steps += 1
            del (
                output,
                aux,
                error,
                pixel,
                derivatives,
                gradient,
                spectral,
                local_penalty,
                dc_penalty,
                loss,
                scale,
                pair_penalty,
                anchor_penalty,
            )
        if phase == "train" and step <= 10:
            assert row == smoke_trace[step - 1], (step, "smoke/train prefix continuation")
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
        del batch, base, a, mask, mask_cpu
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
                assert all(
                    torch.equal(v.cpu(), s["emas"][label][n]) for n, v in emas[label].items()
                )
                reloaded = optimizers[label].state_dict()
                assert reloaded["param_groups"] == s["optimizers"][label]["param_groups"]
                for index, state in reloaded["state"].items():
                    for key, value in state.items():
                        assert torch.equal(value.cpu(), s["optimizers"][label]["state"][index][key])
            torch.set_rng_state(s["torch_CPU_RNG"])
            torch.cuda.set_rng_state(s["torch_CUDA_RNG"])
            assert torch.equal(torch.get_rng_state(), s["torch_CPU_RNG"])
            assert torch.equal(torch.cuda.get_rng_state().cpu(), s["torch_CUDA_RNG"])
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
    if phase == "train":
        previous = read(plan["baseline_training"]["path"])
        assert ref(previous["checkpoint"]["path"]) == previous["checkpoint"]
        saved = torch.load(previous["checkpoint"]["path"], map_location="cpu", weights_only=True)
        assert equal_tree(modules["anchor-control"].state_dict(), saved["models"]["flat-anchor"])
        assert equal_tree(emas["anchor-control"], saved["emas"]["flat-anchor"])
        assert equal_tree(
            optimizers["anchor-control"].state_dict(), saved["optimizers"]["flat-anchor"]
        )
        del saved
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
            "exact_V162_control_trace_rows": compatible_steps,
            "control_final_raw_EMA_Adam_exact": phase == "train",
            "head_image_evaluations": 8 * last,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": recipe["scope"],
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
