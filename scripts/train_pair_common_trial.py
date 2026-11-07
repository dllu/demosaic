"""Matched V164 stronger-pair control and absolute pair-common supervision."""

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
    recipe = REPO / "configs/quality-v143-pair-common-v165.yaml"
    config = yaml.safe_load(recipe.read_text())
    assert list(config["arms"]) == ["fine-control", "pair-common"]
    assert config["pair_common_unit_DN16"] == 16
    previous = Path(config["previous_trial"])
    prior = read(previous / "plan-v1.json")
    guard(prior)
    shared = config["shared_training_recipe"]
    assert ref(shared["path"]) == shared
    oldconfig = yaml.safe_load(Path(shared["path"]).read_text())
    for name, arm in config["arms"].items():
        assert {k: v for k, v in arm.items() if k != "pair_common_weight"} == oldconfig["arms"][
            "fine-pair"
        ]
        assert arm["pair_unit_floor_DN16"] == 2
        assert arm["pair_common_weight"] == (0 if name == "fine-control" else 1)
        assert (arm["parameters"], arm["parameter_tensors"]) == (124909, 47)
    for k in [
        "max_window",
        "steps",
        "batch_size",
        "lr",
        "warmup",
        "gradient_clip",
        "EMA_decay",
        "domain_loss_weights",
        "pixel_epsilon_in_noise_units",
        "gradient_epsilon_in_noise_units",
        "gradient_weight",
        "spectral_weight",
        "pair_epsilon",
        "local_risk_window_native",
        "local_risk_transition_noise_units",
        "regional_DC_window_native",
        "flat_anchor_window",
        "flat_anchor_tolerance_DN16",
        "flat_anchor_unit_DN16",
    ]:
        assert config[k] == oldconfig[k]
    table_binding = config["pair_unit_table"]
    assert ref(table_binding["path"]) == table_binding
    table = read(table_binding["path"])
    assert len(table["rows"]) == 1000 and table["supervised_pairs_changed"] == 620
    cache_path = Path(prior["cache"]["path"])
    assert ref(cache_path) == prior["cache"] == table["cache"]
    cache = read(cache_path)
    assert (
        len(cache["batches"]) == 1000
        and cache["parent_before"] == cache["parent_after"]
        and cache["DINO_before"] == cache["DINO_after"]
    )
    cases = read(previous / "quality-design-v1.json")["observations"]
    assert len(cases) == len({c["id"] for c in cases}) == 822
    per_endpoint = sum(np.load(c["parent"]["path"], mmap_mode="r").nbytes + 128 for c in cases)
    external = Path(config["external_root"])
    assert external.is_relative_to("/mnt/external") and not external.exists()
    assert shutil.disk_usage(REPO).free > 56.75 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 136.5 * 2**30 + 2 * per_endpoint
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
            "pair_unit_floor.py",
            "paired_common_objective.py",
            "review_pair_common_trial.py",
        ]
    ]
    sources += [
        REPO / "tests" / n
        for n in [
            "test_pair_unit_floor.py",
            "test_paired_common_objective.py",
            "test_flat_target_anchor.py",
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
        f"fine-control-{e}-step1000": review["collections"][f"fine-pair-{e}-step1000"]
        for e in ["raw", "EMA"]
    }
    baseline = controls["fine-control-raw-step1000"]
    collection = read(baseline["path"])
    save(
        root / "quality-design-v1.json",
        {
            "observations": cases,
            "endpoints": [f"{a}-{e}-step1000" for a in config["arms"] for e in ["raw", "EMA"]],
            "new_component_forwards": 3288,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Four fixed endpoints/822 cases.1644 actual V164 control replays before adoption;1644 new candidate arrays external. No extra neural ablation. Both real scenes/priors/windows/JPEGs qualitative references,not exactGT.",
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
        "legacy_phase": ref(Path(prior["work"]) / "src/demosaic/late_harmonic_phase.py"),
        "pair_unit_table": table_binding,
        "external_quality_root": str(external),
        "external_root": str(external),
        "quality_output_roots": {
            f"{a}-{e}-step1000": str((root if a == "fine-control" else external) / "review-v1")
            for a in config["arms"]
            for e in ["raw", "EMA"]
        },
        "expected_new_quality_bytes_external": 2 * per_endpoint,
        "expected_new_quality_bytes_per_endpoint": per_endpoint,
        "new_parent_DINO_forwards": 0,
        "new_noise_draws": 0,
        "inputs": [
            ref(recipe),
            ref(target),
            ref(previous / "plan-v1.json"),
            ref(cache_path),
            shared,
            table_binding,
            ref(REPO / "docs/results/v165-pair-common-motivation-v1.json"),
            ref(previous / "train-result-v1.json"),
            ref(previous / "quality-design-v1.json"),
            baseline,
            collection["export"],
            *controls.values(),
            ref(root / "quality-design-v1.json"),
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "source_modules": len(list((work / "src/demosaic").glob("*.py"))),
        "scope": config["scope"],
    }
    assert plan["source_modules"] == 89
    old_neural = {
        p: h for p, h in prior["frozen_files"].items() if Path(p).parent.name == "demosaic"
    }
    assert len(old_neural) == 89
    for p, h in old_neural.items():
        assert ref(work / "src/demosaic" / Path(p).name)["sha256"] == h
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def classes():
    from demosaic.late_harmonic_phase import LateHarmonicPhaseDetail

    return {"fine-control": LateHarmonicPhaseDetail, "pair-common": LateHarmonicPhaseDetail}


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
    resources = {
        "RAM_available_bytes": psutil.virtual_memory().available,
        "local_free_bytes": shutil.disk_usage(root).free,
        "external_free_bytes": shutil.disk_usage("/mnt/external").free,
    }
    assert (
        resources["RAM_available_bytes"] > 32 * 2**30
        and resources["local_free_bytes"] > 56 * 2**30
        and resources["external_free_bytes"] > 136 * 2**30
    ), resources


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


def cuda_pair_unit_checks(plan):
    import numpy as np
    import torch
    from paired_response_objective import paired_response_loss

    from demosaic.prediction_archive import fingerprint

    table = read(plan["pair_unit_table"]["path"])["rows"]
    records = []
    for item in plan["prefix"]:
        a = dict(np.load(item["arrays"]["path"]))
        pairs = a["pair_indices"]
        if not len(pairs):
            continue
        base = np.load(item["parent"]["path"])
        target = a["target"]
        entry = table[item["step"] - 1]
        units = np.array(entry["candidate_units_FP32"], dtype=np.float32).reshape(entry["shape"])
        value = torch.from_numpy(base).cuda().requires_grad_()
        clean = torch.from_numpy(target).cuda()
        scale = torch.from_numpy(units).cuda()
        loss = paired_response_loss(value, clean, scale, pairs)
        loss.backward()
        first, second = pairs.T
        residual = ((base[first] - base[second]) - (target[first] - target[second])) / units
        error = residual.astype(np.float64)
        expected = float(np.mean(error**2 / (np.sqrt(error**2 + 0.003**2) + 0.003)))
        derivative = error / np.sqrt(error**2 + 0.003**2) / units.astype(np.float64) / error.size
        adjoint = np.zeros(base.shape, dtype=np.float64)
        adjoint[first] = derivative
        adjoint[second] = -derivative
        actual = value.grad.cpu().numpy()
        np.testing.assert_allclose(float(loss.detach()), expected, rtol=3e-6, atol=1e-8)
        np.testing.assert_allclose(actual, adjoint, rtol=3e-5, atol=3e-8)
        records.append(
            {
                "step": item["step"],
                "units": fingerprint(units),
                "loss": float(loss.detach()),
                "independent_loss": expected,
                "maximum_adjoint_difference": float(np.max(np.abs(actual - adjoint))),
                "leaf_backwards": 1,
                "neural_forwards": 0,
            }
        )
        del value, clean, scale, loss, actual
    assert len(records) == 6
    return records


def cuda_common_checks(plan):
    import numpy as np
    import torch
    from paired_common_objective import paired_common_error_loss
    rows=[]
    for index,(size,offset,ADC) in enumerate([(5,0.0,False),(7,0.1,False),(9,8.0,False),(11,64.0,True)]):
        rng=np.random.default_rng(16510+index)
        target=rng.normal(size=(4,3,size,size+2)).astype(np.float32)*.01
        value=target+rng.normal(size=target.shape).astype(np.float32)*.0001+np.float32(offset/65535)
        pairs=np.array([[3,1],[2,0]],dtype=np.int64)
        output=torch.tensor(value,device='cuda',requires_grad=True)
        loss=paired_common_error_loss(output,torch.tensor(target,device='cuda'),pairs,unit_DN16=16)
        if ADC:loss=loss*0
        loss.backward()
        error=value.astype(np.float64)-target.astype(np.float64)
        first,second=pairs.T;z=(error[first]+error[second])/(2*16/65535)
        expected=float(np.mean(z*z/(np.sqrt(1+z*z)+1)))
        derivative=z/np.sqrt(1+z*z)/(2*16/65535)/z.size
        gradient=np.zeros_like(error);gradient[first]=derivative;gradient[second]=derivative
        if ADC:expected=0.;gradient*=0
        actual=output.grad.cpu().numpy();np.testing.assert_allclose(actual,gradient,rtol=3e-6,atol=1e-7)
        np.testing.assert_allclose(float(loss.detach()),expected,rtol=3e-6,atol=1e-8)
        assert np.array_equal(actual[first],actual[second])
        rows.append({'size':size,'offset_DN16':offset,'ADC_zero_weight':ADC,
            'loss':float(loss.detach()),'independent_loss':expected,
            'maximum_full_output_adjoint_difference':float(np.max(np.abs(actual-gradient)))})
    return rows


def parity(plan):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    assert ref(plan["legacy_phase"]["path"]) == plan["legacy_phase"]
    spec = importlib.util.spec_from_file_location(
        "demosaic._v164_frozen_phase", plan["legacy_phase"]["path"]
    )
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    saved = torch.load(plan["baseline_export"]["path"], map_location="cpu", weights_only=True)
    module = classes()["pair-common"](256).cuda().eval()
    frozen = legacy.LateHarmonicPhaseDetail(256).cuda().eval()
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
    pair_checks = cuda_pair_unit_checks(plan)
    common_checks = cuda_common_checks(plan)
    save(
        root / "parity-result-v1.json",
        {
            "status": "pass28-exact-phase-replays-and20-CUDA-leaf-checks",
            "plan": ref(root / "plan-v1.json"),
            "legacy_phase": plan["legacy_phase"],
            "baseline_export": plan["baseline_export"],
            "rows": rows,
            "CUDA_anchor_loss_checks": loss_checks,
            "CUDA_pair_unit_loss_checks": pair_checks,
            "CUDA_pair_common_loss_checks": common_checks,
            "component_forward_evaluations": 56,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Identical inference and frozen V164 phase class replay28 archived contexts/allCFAs/native256/384/512/768/both scenes:56calls. All89 neural sources unchanged. Additional20 leaf-output CUDA backwards:10 inherited flat-anchor,6 pair-unit and4 new common-error loss/full-adjoint checks,not neural forwards. Only added common-error training loss changes.",
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
    from paired_common_objective import paired_common_error_loss
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
        for name, value in modules["fine-control"].state_dict().items():
            assert all(torch.equal(value, m.state_dict()[name]) for m in modules.values())
        assert all(m.relative_in.weight.count_nonzero() == 0 for m in modules.values())
        assert modules["pair-common"].harmonic_in.weight.count_nonzero() == 0
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
    unit_rows = read(plan["pair_unit_table"]["path"])["rows"]
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
            pair_scale = batch["pair_units"]
            if arm["pair_unit_floor_DN16"] == 2:
                entry = unit_rows[step - 1]
                assert entry["step"] == step and entry["batch"] == item["arrays"]
                pair_scale = pair_scale.new_tensor(entry["candidate_units_FP32"]).reshape(
                    entry["shape"]
                )
            pair_penalty = output.new_zeros(())
            if arm["paired_response_weight"] and len(batch["pair_indices"]):
                pair_penalty = paired_response_loss(
                    output,
                    batch["target"],
                    pair_scale,
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
            common_penalty = output.new_zeros(())
            if arm["pair_common_weight"] and len(batch["pair_indices"]):
                common_penalty = paired_common_error_loss(
                    output, batch["target"], batch["pair_indices"],
                    unit_DN16=recipe["pair_common_unit_DN16"],
                )
                loss = loss + config["domain_loss_weights"][row["domain"]] * arm["pair_common_weight"] * common_penalty
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
                "pair_common_error": float(common_penalty.detach()),
                "pair_unit_values": fingerprint(pair_scale.detach().cpu().numpy()),
                "pair_unit_floor_DN16": arm["pair_unit_floor_DN16"],
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
            if label == "fine-control":
                expected = reference_trace[step - 1]["arms"]["fine-pair"]
                assert {k: row["arms"][label][k] for k in expected} == expected, (
                    phase,
                    step,
                    "V164 control trace",
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
                common_penalty,
                pair_scale,
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
        assert equal_tree(modules["fine-control"].state_dict(), saved["models"]["fine-pair"])
        assert equal_tree(emas["fine-control"], saved["emas"]["fine-pair"])
        assert equal_tree(
            optimizers["fine-control"].state_dict(), saved["optimizers"]["fine-pair"]
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
            "exact_V164_control_trace_rows": compatible_steps,
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
