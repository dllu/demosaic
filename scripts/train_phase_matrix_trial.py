"""Matched scalar/complex-phase heads on a single replayed observation cache."""

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
    import yaml

    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    recipe = REPO / "configs/quality-v143-phase-matrix-v148.yaml"
    config = yaml.safe_load(recipe.read_text())
    previous = Path(config["previous_trial"])
    old = read(previous / "plan-v1.json")
    guard(old)
    assert ref(config["shared_training_recipe"]["path"]) == config["shared_training_recipe"]
    shared = yaml.safe_load(Path(config["shared_training_recipe"]["path"]).read_text())
    for key in ("steps", "batch_size", "max_window", "lr", "warmup", "gradient_clip", "EMA_decay"):
        assert config[key] == shared[key]
    assert config["parent"] == {k: old["parent"][k] for k in ("path", "sha256")}
    original_trace = read(previous / "train-result-v1.json")["trace"]
    photo_caches = {
        c["source"]["source"]["cache"]
        for row in original_trace
        if row["metadata"]["domain"] == "photo"
        for c in row["metadata"]["cases"]
    }
    for filename in photo_caches:
        p = Path(filename)
        assert p.is_relative_to(REPO) or p.is_relative_to(Path("/mnt/external"))
        assert p.is_file()
    projected_bytes = sum(128 * row["metadata"]["native_size"] ** 2 for row in original_trace[10:])
    assert shutil.disk_usage(root).free > (96 + 2) * 2**30 + projected_bytes
    raw_collection = read(previous / "review-result-v1.json")["collections"]["raw-step1000"]
    assert ref(raw_collection["path"]) == raw_collection
    raw_export = read(raw_collection["path"])["export"]
    for row in read(previous / "execution-completion-v2.json")["terminal_owner_checks"]:
        assert not live(row["owner"])
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
    ):
        dest = work / "scripts" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, dest)
    runner = work / "scripts" / Path(__file__).name
    runner.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    target = work / "configs" / recipe.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(recipe, target)
    cases = read(previous / "quality-design-v1.json")["observations"]
    mixed = read(previous / "mixed-quiet-v1/plan-v1.json")["observations"]
    parents = {
        r["id"]: r["prediction"]
        for r in read(previous / "mixed-quiet-v1/result-v1.json")["rows"]
        if r["method"] == "parent"
    }
    cases += [
        {**c, "parent": parents[c["id"]], "kind": "mixed-quiet", "ROI_xywh": c["quiet_ROI_xywh"]}
        for c in mixed
    ]
    assert len(cases) == 798 and len({c["id"] for c in cases}) == 798
    for case in cases:
        for key in ("arrays", "parent"):
            p = Path(case[key]["path"])
            assert p.is_relative_to(REPO) or p.is_relative_to(Path("/mnt/external"))
    save(
        root / "quality-design-v1.json",
        {
            "observations": cases,
            "endpoints": [
                f"{arm}-{endpoint}-step1000"
                for arm in config["arms"]
                for endpoint in ("raw", "EMA")
            ],
            "new_component_forwards": 3192,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Prospectively fixed final raw/EMA endpoints for both arms on798 retained observations, including32 V147 mixed controls. Adaptive reused cohort, not fresh independent validation. All standing real windows/priors/JPEGs; reference frames not GT. No short-input bypass.",
        },
    )
    smoke = read(previous / "smoke-result-v1.json")
    prefix = [
        {"arrays": v["arrays"], "metadata": v["metadata"], "inputs": v["inputs"]}
        for v in smoke["prefix"]
    ]
    plan = {
        "root": str(root),
        "work": str(work),
        "config": ref(target),
        "runner": ref(runner),
        "parent": config["parent"],
        "previous": str(previous),
        "shared_recipe": config["shared_training_recipe"],
        "sampler": ref(Path(old["work"]) / "scripts/train_late_spectral_trial.py"),
        "legacy_module": ref(Path(old["work"]) / "src/demosaic/late_spectral_detail.py"),
        "original_trace": ref(previous / "train-result-v1.json"),
        "prefix": prefix,
        "inputs": [
            ref(recipe),
            ref(target),
            ref(previous / "plan-v1.json"),
            ref(previous / "train-result-v1.json"),
            config["shared_training_recipe"],
            ref(config["parent"]["path"]),
            ref(root / "quality-design-v1.json"),
        ]
        + [
            ref(shared[k])
            for k in ("manifest", "photo_sampling_reference_manifest", "reviewed_roi_catalogue")
        ]
        + [v["arrays"] for v in prefix],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "source_modules": len(list((work / "src/demosaic").glob("*.py"))),
        "scope": config["scope"],
    }
    assert plan["source_modules"] == 84
    for name, digest in old["frozen_files"].items():
        p = Path(name)
        if p.parent.name == "demosaic" and p.name != "late_spectral_detail.py":
            assert ref(work / "src/demosaic" / p.name)["sha256"] == digest
    save(
        root / "preflight-v1.json",
        {
            "status": "pass-replayed-source-pool-and-disk-headroom",
            "actual_photo_caches_exist": len(photo_caches),
            "projected_additional_cache_bytes": projected_bytes,
            "train_pool": 90782,
            "reviewed_regions": 27,
            "source": "Same immutable V147 recipe/trace. Input/target fingerprints will be checked during replay, before either production arm trains.",
            "new_noises_or_forwards": 0,
        },
    )
    plan["inputs"] += [
        plan["sampler"],
        plan["legacy_module"],
        raw_collection,
        raw_export,
        ref(root / "preflight-v1.json"),
    ]
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def classes():
    from demosaic.late_spectral_detail import LateSpectralDetail
    from demosaic.late_spectral_matrix import LateSpectralMatrixDetail

    return {"scalar-control": LateSpectralDetail, "phase-matrix": LateSpectralMatrixDetail}


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

    root, previous = Path(plan["root"]), Path(plan["previous"])
    assert ref(plan["legacy_module"]["path"]) == plan["legacy_module"]
    spec = importlib.util.spec_from_file_location(
        "demosaic._v147_legacy_detail", plan["legacy_module"]["path"]
    )
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    c = read(previous / "review-v1/raw-step1000/collection-v1.json")
    assert ref(c["export"]["path"]) == c["export"]
    state = torch.load(c["export"]["path"], map_location="cpu", weights_only=True)
    models = {
        "legacy": legacy.LateSpectralDetail(256).cuda().eval(),
        "scalar": classes()["scalar-control"](256).cuda().eval(),
        "embedded-matrix": classes()["phase-matrix"](256).cuda().eval(),
    }
    for name in ("legacy", "scalar"):
        models[name].load_state_dict(state["state_dict"], strict=True)
    matrix = models["embedded-matrix"]
    common = {k: v for k, v in state["state_dict"].items() if not k.startswith("frequency_out.")}
    assert len(common) == 10
    missing = matrix.load_state_dict(common, strict=False)
    assert (
        set(missing.missing_keys) == {"frequency_real_bias", "frequency_out.weight"}
        and not missing.unexpected_keys
    )
    with torch.no_grad():
        matrix.frequency_out.weight.zero_()
        matrix.frequency_real_bias.zero_()
        for i in range(4):
            matrix.frequency_out.weight[(4 * i + i) * 2].copy_(
                state["state_dict"]["frequency_out.weight"][0]
            )
            matrix.frequency_real_bias[i, i].copy_(state["state_dict"]["frequency_out.bias"][0])
    cases = read(root / "quality-design-v1.json")["observations"]
    selected = [v for v in cases if v["kind"] == "mesh" and v["seed"] == 2026112302]
    selected += [
        v
        for v in cases
        if v["kind"] == "photo"
        and (
            "3e638bbb" in v["id"]
            or ("02a76fd3" in v["id"] and v["variant"]["name"] == "photo-faint")
        )
    ]
    selected += [
        v
        for v in cases
        if v["kind"] == "flat"
        and v["id"]
        in (
            "flat512-gray-l0.02-adc-only-RGGB",
            "flat512-gray-l0.02-iso6400-prior-RGGB",
            "gray-l0.02-adc-only-RGGB",
            "gray-l0.02-iso12800-prior-RGGB",
        )
    ]
    selected += [
        v
        for v in cases
        if v["kind"] == "real"
        and (
            v["id"].startswith("mesh-") or v["id"] in ("main-overcast-sky", "main-building-detail")
        )
    ]
    assert len(selected) == 28
    archive = {v["id"]: v["prediction"] for v in c["observations"]}
    counts = {k: 0 for k in models}
    LIVE_PROGRESS.update(phase="parity", counts=counts)
    for label, model in models.items():
        model.register_forward_hook(
            lambda *args, label=label: counts.__setitem__(label, counts[label] + 1)
        )
    before = {k: model_hash(m) for k, m in models.items()}
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
            outputs = {k: m(base, *inputs).cpu().numpy() for k, m in models.items()}
        assert np.array_equal(outputs["legacy"], outputs["scalar"])
        difference = float(
            np.max(
                np.abs(
                    outputs["legacy"].astype(np.float64)
                    - outputs["embedded-matrix"].astype(np.float64)
                )
            )
        )
        assert difference <= 2e-7
        rows.append(
            {
                "id": case["id"],
                "scalar_exact_legacy": True,
                "embedded_matrix_max_difference_DN16": difference * 65535,
                "current_scalar_exact_archived": bool(
                    np.array_equal(outputs["scalar"], np.load(archive[case["id"]]["path"]))
                ),
            }
        )
    assert counts == {k: 28 for k in models} and before == {
        k: model_hash(m) for k, m in models.items()
    }
    save(
        root / "parity-result-v1.json",
        {
            "status": "pass-trained-scalar-dispatch-and-matrix-subfamily",
            "plan": ref(root / "plan-v1.json"),
            "rows": rows,
            "component_forwards": 84,
            "parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "counts": counts,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Engineering check only, not new quality validation. Legacy/current scalar exact; trained scalar embedded in matrix family within recorded float differences.",
        },
    )


def dataset(config):
    from demosaic.data import CleanDataset

    return CleanDataset(
        config["manifest"],
        patch_size=256,
        seed=config["seed"],
        synthetic_fraction=0.0,
        flat_fraction=0.0,
        augmentation_downsample=2,
        optical_blur_probability=0.0,
        photographic_low_contrast_fraction=0.0,
        reviewed_roi_catalogue=config["reviewed_roi_catalogue"],
        reviewed_roi_fraction=config["reviewed_roi_fraction"],
        photo_sampling_reference_manifest=config["photo_sampling_reference_manifest"],
        photo_sampling_reference_sha256=config["photo_sampling_reference_sha256"],
        trace_sources=True,
    )


def cache(plan):
    import numpy as np
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    config = yaml.safe_load(Path(plan["shared_recipe"]["path"]).read_text())
    expected = read(plan["original_trace"]["path"])["trace"]
    spec = importlib.util.spec_from_file_location("frozen_v147_sampler", plan["sampler"]["path"])
    sampler = importlib.util.module_from_spec(spec)
    assert ref(plan["sampler"]["path"]) == plan["sampler"]
    spec.loader.exec_module(sampler)
    data = dataset(config)
    assert len(data) == 90782
    with torch.random.fork_rng(devices=[0]):
        parent, loaded = load_checkpoint(plan["parent"]["path"], "cuda")
    assert loaded["loaded_sha256"] == plan["parent"]["sha256"]
    del loaded
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before, backbone = model_hash(parent), model_hash(parent.context.backbone)
    previous = read(plan["original_trace"]["path"])
    assert before == previous["parent_model_before"] and backbone == config["expected_DINO_sha256"]
    counts = {"parent_root": 0, "DINO": 0}
    LIVE_PROGRESS.update(phase="cache", counts=counts, last_completed_step=0)
    parent.register_forward_hook(
        lambda *args: counts.__setitem__("parent_root", counts["parent_root"] + 1)
    )
    parent.context.backbone.register_forward_hook(
        lambda *args: counts.__setitem__("DINO", counts["DINO"] + 1)
    )
    destdir = root / "batches"
    destdir.mkdir(exist_ok=False)
    rows = []
    journal = (root / "cache-trace-v1.jsonl").open("x")
    for step in range(1, 1001):
        resource_check(root)
        if step <= 10:
            item = plan["prefix"][step - 1]
            assert ref(item["arrays"]["path"]) == item["arrays"]
            a = dict(np.load(item["arrays"]["path"]))
            base = a.pop("parent")
            metadata = item["metadata"]
            binding = item["arrays"]
        else:
            a, metadata = sampler.source_batch(config, data, step)
            assert {k: fingerprint(v) for k, v in a.items()} == expected[step - 1][
                "inputs"
            ] and metadata == expected[step - 1]["metadata"]
            tensors = {k: torch.from_numpy(v).cuda() for k, v in a.items()}
            parent.set_noise(metadata["noise"]["shot"], metadata["noise"]["read"])
            with torch.inference_mode():
                base = (
                    parent(*(tensors[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
                    .cpu()
                    .numpy()
                )
            del tensors
            dest = destdir / f"step-{step:04d}.npz"
            with dest.open("xb") as stream:
                np.savez(stream, **a, parent=base)
            binding = ref(dest)
        assert {k: fingerprint(v) for k, v in a.items()} == expected[step - 1]["inputs"]
        rows.append(
            {
                "step": step,
                "arrays": binding,
                "metadata": metadata,
                "inputs": expected[step - 1]["inputs"],
                "parent_values": fingerprint(base),
                "adopted_old_prefix": step <= 10,
            }
        )
        journal.write(json.dumps(rows[-1], allow_nan=False) + "\n")
        journal.flush()
        LIVE_PROGRESS["last_completed_step"] = step
        if step == 1 or step % 10 == 0:
            save(root / "cache-progress-v1.json", {"step": step, "counts": dict(counts)})
            print(json.dumps({"phase": "cache", "step": step, "counts": counts}), flush=True)
        del a, base
    journal.close()
    assert (
        counts == {"parent_root": 990, "DINO": 990}
        and model_hash(parent) == before
        and model_hash(parent.context.backbone) == backbone
    )
    guard(plan)
    save(
        root / "cache-result-v1.json",
        {
            "status": "completed-single-matched-observation-parent-cache",
            "plan": ref(root / "plan-v1.json"),
            "batches": rows,
            "counts": counts,
            "all1000_input_target_fingerprints_exact_V147": True,
            "parent_before": before,
            "parent_after": model_hash(parent),
            "DINO_before": backbone,
            "DINO_after": model_hash(parent.context.backbone),
            "new_replayed_observation_constructions": 3960,
            "adopted_observations": 40,
            "new_independent_observations": 0,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": "Same V147 inputs/noise realization replayed once, not fresh validation. Both heads will read these exact cached parent/target arrays.",
        },
    )


def fit(plan, phase):
    import numpy as np
    import torch
    import yaml

    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    config = yaml.safe_load(Path(plan["shared_recipe"]["path"]).read_text())
    recipe = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    counts = {label: 0 for label in recipe["arms"]}
    updates = dict(counts)
    LIVE_PROGRESS.update(phase=phase, counts=counts, updates=updates, last_completed_step=0)

    def fresh():
        modules = {k: classes()[k](256).cuda() for k in recipe["arms"]}
        common = [
            k for k in modules["scalar-control"].state_dict() if not k.startswith("frequency_out.")
        ]
        assert len(common) == 10 and all(
            torch.equal(
                modules["scalar-control"].state_dict()[k], modules["phase-matrix"].state_dict()[k]
            )
            for k in common
        )
        for label, m in modules.items():
            assert (
                sum(p.numel() for p in m.parameters()) == recipe["arms"][label]["parameters"]
                and len(m.state_dict()) == 12
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
    cache_rows = (
        read(root / "cache-result-v1.json")["batches"] if phase == "train" else plan["prefix"]
    )
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
                .clamp_min(config["noise_unit_floor_DN16"] / 65535)
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
            spectral = module.spectral_supervision(batch["target"], batch["colors"], aux)
            loss = config["domain_loss_weights"][row["domain"]] * (
                pixel + config["gradient_weight"] * gradient + config["spectral_weight"] * spectral
            )
            assert torch.isfinite(loss)
            loss.backward()
            for name, p in module.named_parameters():
                assert p.grad is not None and torch.isfinite(p.grad).all()
                maximum[label][name] = max(maximum[label][name], float(p.grad.abs().max()))
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
                assert len(optimizers[label].state) == 12 and all(
                    float(v["step"]) == 8 for v in optimizers[label].state.values()
                )
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
        assert min(maximum[label].values()) > 0 and len(optimizers[label].state) == 12
        assert all(float(v["step"]) == last for v in optimizers[label].state.values())
        assert all(
            torch.isfinite(t).all()
            for state in optimizers[label].state.values()
            for t in state.values()
        )
        assert all(
            torch.isfinite(v).all() for v in [*module.state_dict().values(), *emas[label].values()]
        )
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
            "parameter_maximum_gradients": maximum,
            "initial_outputs_exact_parent": True,
            "trace": trace,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Both heads consume identical cached inputs/parents and start fresh. Smoke weights discarded. Training loss/config inherited verbatim; only frequency-operator family differs.",
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
        elif phase == "cache":
            cache(plan)
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
        for phase in ("parity", "smoke", "cache", "train"):
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
    parser.add_argument("--phase", choices=("parity", "smoke", "cache", "train"))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    elif args.mode == "worker":
        worker(args.path.resolve(), args.phase)
    else:
        controller(args.path.resolve())
