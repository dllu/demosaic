"""Prospective exact quiet regions beside strong edges, with fresh noise."""

import argparse
import os
import shutil
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save


def prepare(root):
    import numpy as np
    import torch

    from demosaic.suite import observation

    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    point = root / "mixed-quiet-v1"
    point.mkdir(exist_ok=False)
    inputs = point / "inputs"
    inputs.mkdir()
    runner = point / "operator-v1.py"
    shutil.copyfile(__file__, runner)
    seed = 2026110309
    # These new analytic targets are not sampled from the training recipes.
    yy, xx = torch.meshgrid(
        (torch.arange(1024) + 0.5) / 2, (torch.arange(1024) + 0.5) / 2, indexing="ij"
    )
    conditions = [
        {"name": "iso6400-prior", "shot": 0.00128, "read": 6.5536e-6, "exposure": 1.0},
        {"name": "iso12800-prior", "shot": 0.00256, "read": 2.62144e-5, "exposure": 1.0},
    ]
    save(
        point / "design-lock-v1.json",
        {
            "seed": seed,
            "templates": ["vertical-step", "narrow-bar", "slanted-step", "striped-patch"],
            "conditions": conditions,
            "patterns": ["RGGB", "BGGR", "GRBG", "GBRG"],
            "quiet_ROI_xywh": [80, 176, 160, 160],
            "edge_ROI_xywh": [240, 176, 160, 160],
            "endpoints": ["parent", "raw-step1000", "EMA-step1000"],
            "planned_noise_draws": 32,
            "planned_parent_DINO_forwards": 32,
            "planned_module_forwards": 64,
            "scope": "Fresh512 analytic scenes; exact quiet background left of x250, strong colored edges/stripes start beyond x264. Not an independent natural-photo test. Both final endpoints. Compare quiet error and spatial variation, not just correction power. No training/RAW access.",
        },
    )
    before = torch.get_rng_state().clone()
    cases = []
    for template in read(point / "design-lock-v1.json")["templates"]:
        background = torch.tensor([0.003, 0.006, 0.004])[:, None, None].expand(3, 1024, 1024)
        tint = torch.tensor([0.05, 0.035, 0.08])[:, None, None]
        if template == "vertical-step":
            shape = (xx >= 272).float()
        elif template == "narrow-bar":
            shape = ((xx >= 272) & (xx < 280)).float()
        elif template == "slanted-step":
            shape = (xx >= 0.25 * yy + 220).float()
        else:
            shape = ((xx >= 280) & (yy >= 100) & (yy < 412)).float() * (
                0.7 + 0.3 * torch.sin(2 * torch.pi * xx / 8) * torch.sin(2 * torch.pi * yy / 9)
            )
        rgb = torch.nn.functional.avg_pool2d((background + tint * shape)[None], 2)
        for condition in conditions:
            for pattern in ("RGGB", "BGGR", "GRBG", "GBRG"):
                identity = f"mixed-{template}-{condition['name']}-{pattern}"
                values = observation(
                    rgb,
                    [identity],
                    condition,
                    pattern,
                    [2.0, 1.0, 1.5],
                    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                    seed,
                )
                arrays = {k: v.numpy() for k, v in values.items()}
                target = arrays["target"][..., 176:336, 80:240]
                assert np.array_equal(target, np.broadcast_to(target[..., :1, :1], target.shape))
                dest = inputs / f"{identity}.npz"
                np.savez(dest, **arrays)
                cases.append(
                    {
                        "id": identity,
                        "template": template,
                        "noise": condition,
                        "pattern": pattern,
                        "arrays": ref(dest),
                        "quiet_ROI_xywh": [80, 176, 160, 160],
                        "edge_ROI_xywh": [240, 176, 160, 160],
                        "display_exposure": 8,
                    }
                )
    assert (
        len(cases) == 32
        and torch.equal(before, torch.get_rng_state())
        and not torch.cuda.is_initialized()
    )
    save(
        point / "plan-v1.json",
        {
            "design": ref(point / "design-lock-v1.json"),
            "training_plan": ref(root / "plan-v1.json"),
            "runner": ref(runner),
            "observations": cases,
            "actual_noise_draws": 32,
            "CPU_RNG_unchanged": True,
        },
    )


def worker(root):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.late_spectral_detail import LateSpectralDetail

    point = root / "mixed-quiet-v1"
    plan = read(point / "plan-v1.json")
    assert ref(__file__) == plan["runner"]
    assert ref(plan["training_plan"]["path"]) == plan["training_plan"]
    training = read(plan["training_plan"]["path"])
    guard(training)
    assert (
        Path(LateSpectralDetail.forward.__code__.co_filename)
        .resolve()
        .is_relative_to(Path(training["work"]) / "src")
    )
    assert read(root / "status-v1.json")["status"] == "completed-training-awaiting-quality-review"
    result = read(root / "train-result-v1.json")
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000
    (point / "worker.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[2:4])
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
    with torch.random.fork_rng(devices=[0]):
        parent, _ = load_checkpoint(training["parent"]["path"], "cuda")
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before, backbone = model_hash(parent), model_hash(parent.context.backbone)
    assert backbone == state["config"]["expected_DINO_sha256"]
    counts = {"parent": 0, "DINO": 0, "raw-step1000": 0, "EMA-step1000": 0}
    parent.register_forward_hook(lambda *args: counts.__setitem__("parent", counts["parent"] + 1))
    parent.context.backbone.register_forward_hook(
        lambda *args: counts.__setitem__("DINO", counts["DINO"] + 1)
    )
    modules = {}
    for label, key in (("raw-step1000", "model"), ("EMA-step1000", "ema")):
        m = LateSpectralDetail(**state["module_config"]).cuda().eval()
        m.load_state_dict(state[key], strict=True)
        m.register_forward_hook(
            lambda *args, label=label: counts.__setitem__(label, counts[label] + 1)
        )
        modules[label] = m
    module_before = {k: model_hash(m) for k, m in modules.items()}
    rows = []
    for case in plan["observations"]:
        assert (
            psutil.virtual_memory().available > 32 * 2**30
            and shutil.disk_usage(root).free > 96 * 2**30
        )
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        batch = {
            k: torch.from_numpy(a[k]).cuda()
            for k in ("packed", "variance", "colors", "wb", "matrix")
        }
        parent.set_noise(case["noise"]["shot"], case["noise"]["read"])
        with torch.inference_mode():
            base = parent(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
            values = {"parent": base.cpu().numpy()}
            values.update(
                {
                    k: m(base, *(batch[n] for n in ("packed", "variance", "colors", "wb")))
                    .cpu()
                    .numpy()
                    for k, m in modules.items()
                }
            )
        for label, value in values.items():
            assert np.isfinite(value).all() and value.dtype == np.float32
            dest = point / f"{case['id']}-{label}.npy"
            assert not dest.exists()
            np.save(dest, value)
            error = value.astype(np.float64) - a["target"].astype(np.float64)
            quiet = error[..., 176:336, 80:240]
            dc = quiet.mean((-2, -1), keepdims=True)
            rows.append(
                {
                    "id": case["id"],
                    "template": case["template"],
                    "noise": case["noise"]["name"],
                    "method": label,
                    "prediction": ref(dest),
                    "full_RMS_DN16": float(np.sqrt(np.mean(error**2)) * 65535),
                    "quiet_RMS_DN16": float(np.sqrt(np.mean(quiet**2)) * 65535),
                    "quiet_spatial_RMS_DN16": float(np.sqrt(np.mean((quiet - dc) ** 2)) * 65535),
                    "quiet_correction_RMS_DN16": float(
                        np.sqrt(
                            np.mean(
                                (
                                    value[..., 176:336, 80:240].astype(np.float64)
                                    - values["parent"][..., 176:336, 80:240]
                                )
                                ** 2
                            )
                        )
                        * 65535
                    ),
                }
            )
        del batch, base, values
    assert counts == {"parent": 32, "DINO": 32, "raw-step1000": 32, "EMA-step1000": 32}
    assert model_hash(parent) == before and model_hash(parent.context.backbone) == backbone
    assert module_before == {k: model_hash(m) for k, m in modules.items()}
    guard(training)
    save(
        point / "result-v1.json",
        {
            "status": "completed-mixed-quiet-controls",
            "plan": ref(point / "plan-v1.json"),
            "training_checkpoint": result["checkpoint"],
            "counts": counts,
            "rows": rows,
            "parent_before": before,
            "parent_after": model_hash(parent),
            "DINO_before": backbone,
            "DINO_after": model_hash(parent.context.backbone),
            "module_before": module_before,
            "module_after": {k: model_hash(m) for k, m in modules.items()},
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else worker)(args.root.resolve())
