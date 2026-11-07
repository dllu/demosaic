"""Fresh matched ordinary and coupled-pair response supervision."""

import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
LIVE_PROGRESS = {}


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


def cache(plan, phase):
    import numpy as np
    import torch
    import yaml
    from paired_response_counters import count_source_draws
    from paired_response_data import source_batch
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    config = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    data = dataset(config)
    assert len(data) == 90782
    with torch.random.fork_rng(devices=[0]):
        parent, loaded = load_checkpoint(plan["parent"]["path"], "cuda")
    assert loaded["loaded_sha256"] == plan["parent"]["sha256"]
    del loaded
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before, backbone = model_hash(parent), model_hash(parent.context.backbone)
    assert before == "cfac283dcb0de6087321957bfb389b0b98843b4c0daa1b792f2236901a82ae2b"
    assert backbone == config["expected_DINO_sha256"]
    counts = {"parent_root": 0, "DINO": 0}
    source_counts = {
        "batches": 0,
        "observations": 0,
        "Poisson": 0,
        "Gaussian": 0,
        "procedural_Poisson": 0,
        "procedural_Gaussian": 0,
    }
    LIVE_PROGRESS.update(
        phase=phase, counts=counts, source_counts=source_counts, last_completed_step=0
    )
    parent.register_forward_hook(
        lambda *args: counts.__setitem__("parent_root", counts["parent_root"] + 1)
    )
    parent.context.backbone.register_forward_hook(
        lambda *args: counts.__setitem__("DINO", counts["DINO"] + 1)
    )
    destdir = Path(plan["external_root"]) / "training-batches"
    destdir.mkdir(exist_ok=True)
    inspected = {x["step"]: x for x in plan["inspected_batches"]}
    rows = read(plan["adoption"]["path"])["batches"]
    start, end = 24, 1000
    heldout = set(read(plan["inspection"]["path"])["source_preflight"]["heldout_photo_ids"])
    journal = (root / f"{phase}-trace-v2.jsonl").open("x")
    forward_journal = (root / f"{phase}-forward-events-v2.jsonl").open("x")
    CPU_RNG, CUDA_RNG = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    for step in range(start, end + 1):
        resource_check(root)
        if step in inspected:
            item = inspected[step]
            assert ref(item["arrays"]["path"]) == item["arrays"]
            a = dict(np.load(item["arrays"]["path"]))
            metadata = item["metadata"]
            binding = item["arrays"]
            assert {k: fingerprint(v) for k, v in a.items()} == item["inputs"]
        else:
            with count_source_draws() as draws:
                a, metadata = source_batch(config, data, step)
            for key in ["Poisson", "Gaussian"]:
                assert draws[f"sensor_{key}"] == metadata["sensor"]["sampler_calls"][key]
                source_counts[key] += draws[f"sensor_{key}"]
                source_counts[f"procedural_{key}"] += draws[f"procedural_{key}"]
            metadata["actual_sampler_calls"] = draws
            source_counts["batches"] += 1
            source_counts["observations"] += 4
            for c in metadata["cases"]:
                if c["source"]["kind"] == "photo":
                    s = c["source"]["source"]
                    assert s["source_id"] not in heldout
                    assert ref(s["cache"])["sha256"] == s["cache_sha256"]
            path = destdir / f"step-{step:04d}-inputs.npz"
            assert not path.exists()
            with path.open("xb") as stream:
                np.savez(stream, **a)
            binding = ref(path)
        tensors = {
            k: torch.from_numpy(a[k]).cuda()
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
        parent.set_noise(metadata["noise"]["shot"], metadata["noise"]["read"])
        with torch.inference_mode():
            base = (
                parent(*(tensors[k] for k in ["packed", "variance", "colors", "wb", "matrix"]))
                .cpu()
                .numpy()
            )
        forward_journal.write(
            json.dumps({"step": step, "returned_forwards": dict(counts), "images": 4}) + "\n"
        )
        forward_journal.flush()
        assert base.shape == a["target"].shape and np.isfinite(base).all()
        path = destdir / f"step-{step:04d}-parent.npy"
        assert not path.exists()
        with path.open("xb") as stream:
            np.save(stream, base, allow_pickle=False)
        rows.append(
            {
                "step": step,
                "arrays": binding,
                "parent": ref(path),
                "metadata": metadata,
                "inputs": {k: fingerprint(v) for k, v in a.items()},
                "parent_values": fingerprint(base),
                "adopted_inspected_input": step in inspected,
            }
        )
        journal.write(json.dumps(rows[-1], allow_nan=False) + "\n")
        journal.flush()
        LIVE_PROGRESS["last_completed_step"] = step
        assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
            CUDA_RNG, torch.cuda.get_rng_state()
        )
        if step == start or step % 10 == 0:
            save(
                root / f"{phase}-progress-v2.json",
                {"step": step, "counts": dict(counts), "source_counts": source_counts},
            )
            print(
                json.dumps(
                    {"phase": phase, "step": step, "counts": counts, "source_counts": source_counts}
                ),
                flush=True,
            )
        del tensors, a, base
    journal.close()
    forward_journal.close()
    assert counts == {"parent_root": end - start + 1, "DINO": end - start + 1}
    assert before == model_hash(parent) and backbone == model_hash(parent.context.backbone)
    assert all(not p.requires_grad and p.grad is None for p in parent.parameters())
    guard(plan)
    save(
        root / f"{phase}-result-v2.json",
        {
            "status": "completed-fresh-paired-data-parent-cache-phase",
            "phase": phase,
            "batches": rows,
            "plan": ref(root / "plan-v2.json"),
            "counts": counts,
            "source_counts": source_counts,
            "batch_images": 4,
            "parent_images": 4 * (end - start + 1),
            "DINO_images": 4 * (end - start + 1),
            "parent_before": before,
            "parent_after": model_hash(parent),
            "DINO_before": backbone,
            "DINO_after": model_hash(parent.context.backbone),
            "global_Torch_RNG_unchanged": True,
            "adopted_inspected_inputs": sum(x["adopted_inspected_input"] for x in rows),
            "adopted_parent_batches": 23,
            "adoption": plan["adoption"],
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Accounting continuation:977 new parent/DINO batches at steps24-1000 adopt all23 completed parent batches,including six inspected inputs. Failed source24 is reconstructed once;no successful parent forward replayed. Targets/pair fields never enter parent/head forward.",
        },
    )


def classes():
    from demosaic.late_spatial_rgb import LateSpatialRgbDetail

    return {name: LateSpatialRgbDetail for name in ["ordinary", "paired-response"]}


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
    assert shutil.disk_usage("/mnt/external").free > 156 * 2**30


def fit(plan, phase):
    import numpy as np
    import torch
    import yaml
    from frozen_v159_base_loss import reference_loss
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
        for name, value in modules["ordinary"].state_dict().items():
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
    cache_rows = read(
        root / ("cache-result-v2.json" if phase == "train" else "prefix-result-v1.json")
    )["batches"]
    compatible_tensors = compatible_steps = 0
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
                    "plan": ref(root / "plan-v2.json"),
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
            loss = apply_ADC_weight(loss, item["metadata"]["noise"], arm["ADC_loss_weight"])
            reference_grads = None
            if phase == "smoke" and label == "ordinary":
                reference = reference_loss(
                    module, output, aux, batch, base, item, config, recipe, label, row
                )
                assert torch.equal(reference.detach(), loss.detach()), (
                    step,
                    "base-loss compatibility",
                )
                reference_grads = torch.autograd.grad(
                    reference, tuple(module.parameters()), retain_graph=True
                )
                compatible_steps += 1
            has_supervision = not (is_ADC and arm["ADC_loss_weight"] == 0)
            supervised[label] += int(has_supervision)
            zero_ADC[label] += int(not has_supervision)
            assert torch.isfinite(loss)
            loss.backward()
            for index, (name, p) in enumerate(module.named_parameters()):
                if reference_grads is not None:
                    assert torch.equal(p.grad, reference_grads[index]), (
                        step,
                        name,
                        "frozen V159 base gradient",
                    )
                    compatible_tensors += 1
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
                reference_grads,
            )
            if phase == "smoke" and label == "ordinary":
                del reference
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
    guard(plan)
    save(
        root / f"{phase}-result-v1.json",
        {
            "status": "completed-matched-head-phase",
            "phase": phase,
            "steps": last,
            "plan": ref(root / "plan-v2.json"),
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
            "base_compatibility_steps": compatible_steps,
            "base_compatibility_parameter_gradients": compatible_tensors,
            "base_loss_reference": plan["base_loss_reference"],
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
    (root / f"{phase}-v2.claim").open("x").close()
    runtime(plan)
    try:
        if phase == "cache":
            cache(plan, phase)
        else:
            fit(plan, phase)
    except BaseException as error:
        save(
            root / f"{phase}-failure-v2.json",
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
    (root / "controller-v2.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None
    try:
        for phase in ("cache", "train"):
            guard(plan)
            while psutil.virtual_memory().available < 52 * 2**30:
                save(
                    root / "status-v2.json",
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
            with (root / f"{phase}-v2.log").open("x") as log:
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
                    root / "status-v2.json",
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
            state["completed"][phase] = ref(
                root / ("cache-result-v2.json" if phase == "cache" else "train-result-v1.json")
            )
        save(
            root / "status-v2.json",
            {**state, "status": "completed-matched-training-awaiting-fixed-quality-review"},
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        save(
            root / "status-v2.json",
            {**state, "status": "failed-preserved-no-automatic-retry", "error": repr(error)},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("worker", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("cache", "train"))
    args = parser.parse_args()
    if args.mode == "worker":
        worker(args.path.resolve(), args.phase)
    else:
        controller(args.path.resolve())
