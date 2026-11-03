"""Train a small late spectral detail component on a frozen V143/DINO parent."""

import argparse
import gc
import hashlib
import math
import os
import random
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    import yaml
    from review_v146_window_transfer import relocated_controller_source

    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    recipe = REPO / "configs/quality-v143-late-spectral-v147.yaml"
    config = yaml.safe_load(recipe.read_text())
    assert config["steps"] == 1000 and config["batch_size"] == 4
    assert ref(config["parent"]["path"])["sha256"] == config["parent"]["sha256"]
    work = root / "work"
    files = list((REPO / "src/demosaic").glob("*.py"))
    files += [
        REPO / "scripts" / n
        for n in (
            "train_directional_bank_trial.py",
            "train_v43_quality_trial.py",
            "profile_raw_kernel_inference.py",
        )
    ]
    for source in files:
        dest = work / source.relative_to(REPO)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    runner = work / "scripts" / Path(__file__).name
    runner.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    target = work / "configs" / recipe.name
    target.parent.mkdir(parents=True)
    shutil.copyfile(recipe, target)
    data_refs = [
        ref(config[k])
        for k in ("manifest", "photo_sampling_reference_manifest", "reviewed_roi_catalogue")
    ]
    import json

    previous = REPO / ".cache/quality-20261103/V146-coherent-frequency-v1/preflight-v1.json"
    preflight = read(previous)
    for key in ("manifest", "photo_sampling_reference_manifest", "reviewed_roi_catalogue"):
        assert ref(config[key]) == preflight["manifest_refs"][key]
    old_queue = REPO / ".cache/quality-20261103/V146-window-transfer-v1/queue-plan-v2.json"
    queue = read(old_queue)
    collection = REPO / ".cache/quality-20261103/V146-window-transfer-v1/V143/collection-v1.json"
    parents = {o["id"]: o["prediction"] for o in read(collection)["observations"]}
    cases = [
        *queue["original_observations"],
        *({**o, "parent": parents[o["id"]]} for o in queue["fresh_flats"]),
    ]
    assert len(cases) == 766 and len({o["id"] for o in cases}) == 766
    heldout = {o["source"]["sha1"] for o in cases if o["kind"] == "photo"}
    checked = train_rows = 0
    for key in ("manifest", "photo_sampling_reference_manifest"):
        manifest = Path(config[key])
        for line in manifest.read_text().splitlines():
            row = json.loads(line)
            if row["split"] == "train":
                assert row["id"] not in heldout
            cache = (manifest.parent / row["cache"]).absolute()
            assert cache.is_relative_to(REPO) or cache.is_relative_to(Path("/mnt/external"))
            assert cache.is_file(), cache
            checked += 1
            if key == "manifest" and row["split"] == "train":
                assert min(row["shape"][:2]) >= 512 and row["bin_factor"] == 4
                train_rows += 1
    assert train_rows == 90782 and len(heldout) == 16
    save(
        root / "preflight-v1.json",
        {
            "status": "pass-cached-inputs-and-heldout-source-exclusion",
            "previous_preflight": ref(previous),
            "manifests": data_refs,
            "cache_paths_rechecked": checked,
            "train_pool": train_rows,
            "heldout_photo_ids": sorted(heldout),
            "RAW_decodes": 0,
            "scope": "Only repo/external cached arrays. Main and extra GFX scenes and siblings never enter these Commons-only sources.",
        },
    )
    save(
        root / "quality-design-v1.json",
        {
            "source_queue": ref(old_queue),
            "fresh_parent_collection": ref(collection),
            "endpoints": ["raw-step1000", "EMA-step1000"],
            "observations": cases,
            "module_forwards": 1532,
            "new_parent_or_DINO_forwards": 0,
            "new_noise_draws": 0,
            "metrics": "Full and native160 DN16 RMS; blank correction, mesh response; photo DCT16 error/gain; full flat spatial/block32. Real captures descriptive and unscored.",
            "scope": "Both final endpoints; no target-based selection, no short-context bypass. Reuse exact archived V143 arrays; local support must be checked in sky and beside strong edges. Native100% crops, both real-scene priors and JPEGs; ISO100/AHD/JPEG references are not exact GT.",
        },
    )
    plan = {
        "root": str(root),
        "work": str(work),
        "config": ref(target),
        "runner": ref(runner),
        "parent": config["parent"],
        "inputs": [
            ref(recipe),
            *data_refs,
            ref(config["parent"]["path"]),
            ref(root / "preflight-v1.json"),
            ref(root / "quality-design-v1.json"),
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "source_modules": len(list((work / "src/demosaic").glob("*.py"))),
        "CUDA_quota_GiB": 12,
        "launch_RAM_GiB": 52,
        "runtime_RAM_GiB": 32,
        "internal_reserve_GiB": 96,
        "external_reserve_GiB": 208,
        "scope": config["scope"],
    }
    assert plan["source_modules"] == 83
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def source_batch(config, dataset, step):
    """CPU-only stateless target/noise construction, independent of model RNG."""
    import json

    import numpy as np
    import torch

    from demosaic.data import augment_before_downsample, sample_broad_cameras
    from demosaic.suite import observation
    from demosaic.textures import crossed_line_texture, weak_texture

    seed = config["seed"]
    rng = random.Random(f"late-spectral:{seed}:{step}")
    if step <= 10:
        domain = config["first_ten_domains"][step - 1]
    else:
        draw, cumulative = rng.random(), 0.0
        for domain, fraction in config["domains"].items():
            cumulative += fraction
            if draw < cumulative:
                break
    size = config["domain_sizes"][domain]
    if step == 3 or rng.random() < 0.1:
        shot, read_noise = 0.0, 0.0
    elif step == 8 or rng.random() < 0.45:
        shot, read_noise = 0.00128, 6.5536e-6
    elif rng.random() < 0.5:
        shot, read_noise = 0.00256, 2.62144e-5
    else:
        shot, read_noise = (
            2 ** rng.uniform(math.log2(0.00008), math.log2(0.00256)),
            2 ** rng.uniform(math.log2(2e-8), math.log2(2.62144e-5)),
        )
    condition = {"name": f"train-step{step}", "shot": shot, "read": read_noise, "exposure": 1.0}
    state_seed = int.from_bytes(
        hashlib.sha256(f"camera:{seed}:{step}".encode()).digest()[:8], "little"
    ) % (2**63)
    with torch.random.fork_rng(devices=[]):
        torch.set_rng_state(torch.Generator(device="cpu").manual_seed(state_seed).get_state())
        wb, inverse = sample_broad_cameras(config["batch_size"], "cpu")
    matrices = torch.linalg.inv(inverse)
    patterns = ["RGGB", "BGGR", "GRBG", "GBRG"]
    rng.shuffle(patterns)
    cases, arrays = [], []
    yy, xx = torch.meshgrid(
        (torch.arange(2 * size) + 0.5) / 2, (torch.arange(2 * size) + 0.5) / 2, indexing="ij"
    )
    for index in range(config["batch_size"]):
        level = 2 ** rng.uniform(math.log2(0.002), math.log2(0.05))
        if domain == "photo":
            item = dataset[(step - 1) * 4 + index]
            rgb = item["rgb"]
            contrast = (
                2 ** rng.uniform(math.log2(0.005), math.log2(0.2)) if rng.random() < 0.5 else 1.0
            )
            mean = rgb.mean((-2, -1), keepdim=True)
            level = 2 ** rng.uniform(math.log2(0.001), math.log2(0.1))
            rgb = (mean + contrast * (rgb - mean)) * level / float(rgb.mean().clamp_min(1e-6))
            metadata = {
                "kind": domain,
                "source": json.loads(item["source"]),
                "contrast": contrast,
                "scene_mean": level,
            }
        elif domain in ("mesh", "weak"):
            if domain == "mesh":
                rgb, texture = crossed_line_texture(2 * size, rng, pixel_scale=2)
                rgb *= level / texture["level"]
            else:
                rgb, texture = weak_texture(2 * size, rng, pixel_scale=2)
                rgb *= level / texture["level"]
            rgb = augment_before_downsample(rgb, size, rng, optical_blur_probability=0.0)
            metadata = {"kind": domain, "recipe": texture, "scene_level_after_rescale": level}
        else:
            tint = torch.tensor([2 ** rng.uniform(-3, 0) for _ in range(3)])
            tint /= tint.max()
            if domain == "flat":
                level = 2 ** rng.uniform(math.log2(0.002), math.log2(0.9))
                slope_x, slope_y = (
                    (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05))
                    if rng.random() < 0.5
                    else (0.0, 0.0)
                )
                field = 1 + slope_x * (xx / size - 0.5) + slope_y * (yy / size - 0.5)
                rgb = level * tint[:, None, None] * field
                metadata = {
                    "kind": domain,
                    "level": level,
                    "tint": tint.tolist(),
                    "slopes": [slope_x, slope_y],
                }
            else:
                angle = rng.uniform(0, math.pi)
                coordinate = xx * math.cos(angle) + yy * math.sin(angle)
                center = rng.uniform(0.2, 0.8) * size * (math.cos(angle) + math.sin(angle))
                width = rng.uniform(2, 20)
                bar = ((coordinate - center).abs() < width).float()
                side = (
                    (xx > rng.uniform(0.2, 0.8) * size).float()
                    if rng.random() < 0.5
                    else torch.zeros_like(xx)
                )
                stripe_tint = torch.tensor([rng.uniform(0.2, 1) for _ in range(3)])
                rgb = level * (
                    tint[:, None, None]
                    + rng.uniform(0.25, 4) * stripe_tint[:, None, None] * bar
                    + rng.uniform(0.1, 1) * side
                )
                metadata = {
                    "kind": domain,
                    "level": level,
                    "angle": angle,
                    "width": width,
                    "center": center,
                    "quiet_background": True,
                }
            rgb = augment_before_downsample(rgb, size, rng, optical_blur_probability=0.0)
        identity = f"V147-train-{step:04d}-{index}"
        batch = observation(
            rgb[None],
            [identity],
            condition,
            patterns[index],
            wb[index].tolist(),
            matrices[index].tolist(),
            14703,
        )
        arrays.append({k: v.numpy() for k, v in batch.items()})
        cases.append({"id": identity, "pattern": patterns[index], "source": metadata})
    return {k: np.concatenate([a[k] for a in arrays], 0) for k in arrays[0]}, {
        "step": step,
        "domain": domain,
        "noise": condition,
        "cases": cases,
        "native_size": size,
    }


def worker(path, phase):
    import json

    import numpy as np
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    from demosaic.data import CleanDataset
    from demosaic.inference import load_checkpoint
    from demosaic.late_spectral_detail import LateSpectralDetail
    from demosaic.prediction_archive import fingerprint

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    work = Path(plan["work"])
    assert ref(__file__) == plan["runner"]
    assert (
        Path(LateSpectralDetail.forward.__code__.co_filename).resolve().is_relative_to(work / "src")
    )
    (root / f"{phase}.claim").open("x").close()
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
    config = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    with torch.random.fork_rng(devices=[0]):
        parent, parent_state = load_checkpoint(plan["parent"]["path"], "cuda")
    assert parent_state["loaded_sha256"] == plan["parent"]["sha256"]
    del parent_state
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    parent_before = model_hash(parent)
    backbone_before = model_hash(parent.context.backbone)
    assert backbone_before == config["expected_DINO_sha256"]
    counts = {
        "parent_root": 0,
        "DINO": 0,
        "module_training": 0,
        "optimizer_updates": 0,
        "adopted_parent_batches": 0,
    }
    parent.register_forward_pre_hook(
        lambda *args: counts.__setitem__("parent_root", counts["parent_root"] + 1)
    )
    parent.context.backbone.register_forward_hook(
        lambda *args: counts.__setitem__("DINO", counts["DINO"] + 1)
    )
    module = LateSpectralDetail(config["max_window"]).cuda()
    optimizer = torch.optim.AdamW(module.parameters(), lr=config["lr"])
    ema = {k: v.detach().clone() for k, v in module.state_dict().items()}
    assert sum(v.numel() for v in module.parameters()) == 30402
    dataset = CleanDataset(
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
    assert len(dataset) == 90782
    prefix = root / "prefix"
    prefix.mkdir(exist_ok=True)
    trace = []
    maxima = {n: 0.0 for n, _ in module.named_parameters()}
    last_step = 0
    endpoints = root / "checkpoints"
    endpoints.mkdir(exist_ok=True)

    def checkpoint(name, step):
        dest = endpoints / name
        assert not dest.exists()
        with dest.open("xb") as stream:
            torch.save(
                {
                    "step": step,
                    "horizon": config["steps"],
                    "module_config": {"max_window": config["max_window"]},
                    "model": module.state_dict(),
                    "ema": ema,
                    "optimizer": optimizer.state_dict(),
                    "parent": plan["parent"],
                    "plan": ref(path),
                    "config": config,
                    "counts": dict(counts),
                    "torch_CPU_RNG": torch.get_rng_state(),
                    "torch_CUDA_RNG": torch.cuda.get_rng_state(),
                },
                stream,
            )
        return dest

    try:
        for step in range(1, (10 if phase == "smoke" else config["steps"]) + 1):
            assert psutil.virtual_memory().available > plan["runtime_RAM_GiB"] * 2**30
            assert (
                shutil.disk_usage(root).free > 96 * 2**30
                and shutil.disk_usage("/mnt/external").free > 208 * 2**30
            )
            if phase == "train" and step <= 10:
                binding = read(root / "smoke-result-v1.json")["prefix"][step - 1]
                assert ref(binding["arrays"]["path"]) == binding["arrays"]
                arrays = dict(np.load(binding["arrays"]["path"]))
                baseline = arrays.pop("parent")
                metadata = binding["metadata"]
                counts["adopted_parent_batches"] += 1
            else:
                arrays, metadata = source_batch(config, dataset, step)
                batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
                parent.set_noise(metadata["noise"]["shot"], metadata["noise"]["read"])
                with torch.no_grad():
                    baseline = (
                        parent(
                            *(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix"))
                        )
                        .cpu()
                        .numpy()
                    )
                del batch
                if phase == "smoke":
                    dest = prefix / f"step-{step:02d}.npz"
                    assert not dest.exists()
                    np.savez(dest, **arrays, parent=baseline)
            input_hash = {k: fingerprint(v) for k, v in arrays.items()}
            row = {"step": step, "metadata": metadata, "inputs": input_hash}
            if phase == "smoke":
                row["arrays"] = ref(prefix / f"step-{step:02d}.npz")
            batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
            base = torch.from_numpy(baseline).cuda()
            optimizer.zero_grad(set_to_none=True)
            progress = max(0, step - config["warmup"]) / max(1, config["steps"] - config["warmup"])
            lr = (
                config["lr"]
                * min(1, step / config["warmup"])
                * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            )
            for group in optimizer.param_groups:
                group["lr"] = lr
            result, aux = module(
                base,
                batch["packed"],
                batch["variance"],
                batch["colors"],
                batch["wb"],
                return_aux=True,
            )
            if step == 1:
                assert torch.equal(result, base) and aux["correction"].count_nonzero() == 0
            scale = (
                batch["variance"]
                .clamp_min(0)
                .mean((1, 2, 3), keepdim=True)
                .sqrt()
                .clamp_min(config["noise_unit_floor_DN16"] / 65535)
            )
            error = (result - batch["target"]) / scale
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
            loss = config["domain_loss_weights"][metadata["domain"]] * (
                pixel + config["gradient_weight"] * gradient + config["spectral_weight"] * spectral
            )
            assert torch.isfinite(loss)
            loss.backward()
            for name, p in module.named_parameters():
                assert p.grad is not None and torch.isfinite(p.grad).all()
                maxima[name] = max(maxima[name], float(p.grad.abs().max()))
            assert all(p.grad is None for p in parent.parameters())
            norm = torch.nn.utils.clip_grad_norm_(
                module.parameters(), config["gradient_clip"], error_if_nonfinite=True
            )
            optimizer.step()
            counts["optimizer_updates"] += 1
            counts["module_training"] += 1
            last_step = step
            decay = min(config["EMA_decay"], (1 + step) / (10 + step))
            with torch.no_grad():
                for k, v in module.state_dict().items():
                    ema[k].lerp_(v, 1 - decay)
            row.update(
                loss=float(loss),
                pixel=float(pixel),
                gradient=float(gradient),
                spectral=float(spectral),
                gradient_norm=float(norm),
                lr=lr,
            )
            trace.append(row)
            if step == 1 or step % 10 == 0:
                print(
                    json.dumps(
                        {
                            "phase": phase,
                            "step": step,
                            "domain": metadata["domain"],
                            "loss": float(loss),
                            "CUDA_allocated_bytes": torch.cuda.memory_allocated(),
                        }
                    ),
                    flush=True,
                )
                save(
                    root / f"{phase}-progress-v1.json",
                    {
                        "step": step,
                        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                        "counts": dict(counts),
                    },
                )
            del (
                result,
                aux,
                loss,
                batch,
                base,
                arrays,
                baseline,
                error,
                pixel,
                gradient,
                spectral,
                derivatives,
            )
            if phase == "smoke" and step == 8:
                saved = checkpoint("smoke-step0008.pt", 8)
                state = torch.load(saved, map_location="cpu", weights_only=True)
                module = LateSpectralDetail(config["max_window"]).cuda()
                module.load_state_dict(state["model"], strict=True)
                optimizer = torch.optim.AdamW(module.parameters(), lr=config["lr"])
                optimizer.load_state_dict(state["optimizer"])
                assert len(optimizer.state) == 12 and all(
                    float(v["step"]) == 8 for v in optimizer.state.values()
                )
                assert all(
                    torch.equal(module.state_dict()[k].cpu(), v) for k, v in state["model"].items()
                )
                ema = {k: v.cuda() for k, v in state["ema"].items()}
                torch.set_rng_state(state["torch_CPU_RNG"])
                torch.cuda.set_rng_state(state["torch_CUDA_RNG"])
                del state
            if phase == "train" and step % 250 == 0:
                checkpoint(f"train-step{step:04d}.pt", step)
        last = endpoints / ("train-step1000.pt" if phase == "train" else "smoke-step0010.pt")
        if phase == "smoke":
            last = checkpoint(last.name, 10)
        assert (
            model_hash(parent) == parent_before
            and model_hash(parent.context.backbone) == backbone_before
        )
        assert counts["DINO"] == counts["parent_root"] == (10 if phase == "smoke" else 990)
        assert all(v > 0 for v in maxima.values()) and len(optimizer.state) == 12
        assert all(float(v["step"]) == last_step for v in optimizer.state.values())
        assert all(torch.isfinite(v).all() for v in [*module.state_dict().values(), *ema.values()])
        guard(plan)
        result = {
            "status": "completed-declared-late-spectral-phase",
            "phase": phase,
            "plan": ref(path),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "checkpoint": ref(last),
            "counts": counts,
            "parent_model_before": parent_before,
            "parent_model_after": model_hash(parent),
            "DINO_before": backbone_before,
            "DINO_after": model_hash(parent.context.backbone),
            "parent_all_gradients_absent": True,
            "initial_output_exact_parent": True,
            "parameter_maximum_gradients": maxima,
            "steps": last_step,
            "trace": trace,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": config["scope"],
        }
        if phase == "smoke":
            result["prefix"] = trace
        else:
            smoke = read(root / "smoke-result-v1.json")
            assert all(
                a["inputs"] == b["inputs"] for a, b in zip(trace[:10], smoke["trace"], strict=True)
            )
        save(root / f"{phase}-result-v1.json", result)
    except BaseException as error:
        save(
            root / f"{phase}-failure-v1.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "last_completed_step": last_step,
                "counts": counts,
                "trace": trace,
            },
        )
        raise
    finally:
        gc.collect()


def controller(path):
    plan = read(path)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"plan": ref(path), "owner": owner, "completed": {}}
    child = child_owner = None
    try:
        for phase in ("smoke", "train"):
            guard(plan)
            began = time.monotonic()
            while psutil.virtual_memory().available < 52 * 2**30:
                assert time.monotonic() - began < 7200
                save(
                    root / "status-v1.json",
                    {**state, "status": "waiting-for-headroom", "phase": phase},
                )
                time.sleep(2)
            work = Path(plan["work"])
            env = dict(
                os.environ,
                PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
                CUDA_VISIBLE_DEVICES="0",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OMP_NUM_THREADS="2",
                OPENBLAS_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
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
                    cwd=work,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                save(
                    root / "status-v1.json",
                    {
                        **state,
                        "status": "running-declared-phase",
                        "phase": phase,
                        "child": child_owner,
                    },
                )
                assert child.wait(timeout=1800 if phase == "smoke" else 7200) == 0, phase
            assert not live(child_owner)
            state["completed"][phase] = ref(root / f"{phase}-result-v1.json")
        save(
            root / "status-v1.json",
            {**state, "status": "completed-training-awaiting-quality-review"},
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        save(
            root / "status-v1.json",
            {**state, "status": "failed-preserved-no-automatic-retry", "error": repr(error)},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("smoke", "train"))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase)
