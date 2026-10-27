"""Compare genuine BF16/IEEE-FP32 gradients on fixed faint training observations."""

import argparse
import gc
import hashlib
import os
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
from parameter_precision_math import gradient_summary, relative_band_error, valid_reference_blocks
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
NAMES = ("packed", "variance", "colors", "wb", "matrix")
CHECKPOINT = REPO / ".cache/current-quality-20261023-v1/conditional-noise-response-v1/plan-v1.json"


def checked(item):
    assert ref(item["path"]) == item
    return Path(item["path"])


def tensor_hash(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def prepare(root):
    import torch

    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    prior = (
        REPO
        / ".cache/current-quality-20261023-v1/normalized-band-integration-v1/parameter-plan-v1.json"
    )
    previous = read(prior)
    guard(previous)
    model = next(m for m in read(CHECKPOINT)["methods"] if m["label"] == "V120")
    checked(model["checkpoint"])
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = (
        list((REPO / "src/demosaic").glob("*.py"))
        + [
            REPO / "scripts" / n
            for n in (
                "probe_training_precision_gradients.py",
                "parameter_precision_math.py",
                "feature_probe_math.py",
                "train_directional_bank_trial.py",
                "profile_raw_kernel_inference.py",
            )
        ]
        + [REPO / n for n in ("pyproject.toml", "uv.lock", "third_party/dinov3/LICENSE.md")]
    )
    for source in files:
        dest = work / source.relative_to(REPO)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    output = work / "artifacts/prepared"
    output.mkdir(parents=True)
    cases, inputs = [], [ref(prior), ref(CHECKPOINT), model["checkpoint"]]
    for index, old in enumerate(previous["cases"]):
        with np.load(checked(old["arrays"]), allow_pickle=False) as data:
            values = {k: data[k] for k in (*NAMES, "target")}
        assert {k: tensor_hash(v) for k, v in values.items()} == {
            k: old["input_tensor_SHA256"][k] for k in values
        }
        clean = values.pop("target")
        t, wb, matrix = [
            torch.from_numpy(v.copy()) for v in (clean, values["wb"], values["matrix"])
        ]
        linear = torch.einsum("bij,bjhw->bihw", matrix, t * wb[..., None, None]).clamp(0, 1)
        target = (
            torch.einsum("bij,bjhw->bihw", torch.linalg.inv(matrix), linear) / wb[..., None, None]
        )
        values.update(sensor_target=clean, target=target.numpy())
        mask = valid_reference_blocks(clean, values["wb"], values["matrix"])
        path = output / f"case-{index:02d}.npz"
        np.savez(path, **values, reference_block_mask=mask)
        cases.append(
            {
                "index": index,
                "source_id": old["source_id"],
                "contrast": old["additional_contrast_factor"],
                "condition": old["condition"],
                "noise": old["noise_conditioning"],
                "arrays": ref(path),
                "original_arrays": old["arrays"],
                "input_hashes": {k: tensor_hash(values[k]) for k in NAMES},
                "blocks": int(mask.sum()),
                "precision_order": ["float32", "bfloat16"]
                if index % 2 == 0
                else ["bfloat16", "float32"],
            }
        )
        inputs += [old["arrays"], ref(path)]
    assert len(cases) == 8
    plan = {
        "root": str(root),
        "work": str(work),
        "worker": ref(work / "scripts/probe_training_precision_gradients.py"),
        "model": model,
        "cases": cases,
        "planned_root_forwards": 16,
        "planned_encoder_forwards": 16,
        "planned_training_gradient_evaluations": 16,
        "planned_band_gradient_evaluations": 8,
        "retained_full_gradient_cases": [0, 4],
        "launch_available_RAM_GiB": 48,
        "runtime_available_RAM_GiB": 32,
        "CUDA_cap_GiB": 8,
        "maximum_worker_seconds": 1200,
        "runtime_internal_free_GiB": 96,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "16 new differentiable native256/B1 V120 forward calls, not ordinary inference replay. Eight retained training observations:2 sources x contrasts.025/1 x ADC/ISO12800, no new noise/RAW. Compare actual current Charbonnier.0003 gradients in BF16/IEEE FP32; use FP32 normalized DCT16 band-error gradient as a common local direction.24 autograd evaluations, zero optimizer updates/weight changes. No speed, trained-quality, Adam-step or broad precision claim. Preserve existing jobs and outputs; no automatic retry.",
    }
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def collect(path):
    import random

    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.execution import training_execution
    from demosaic.inference import load_checkpoint
    from demosaic.losses import reconstruction_loss
    from demosaic.precision import amp_context, ieee_fp32

    plan = read(path)
    guard(plan)
    assert ref(__file__) == plan["worker"] and os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert (
        Path(load_checkpoint.__code__.co_filename)
        .resolve()
        .is_relative_to(Path(plan["work"]) / "src")
    )
    root = Path(plan["root"])
    (root / "collect.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    assert psutil.virtual_memory().available >= plan["launch_available_RAM_GiB"] * 2**30
    torch.cuda.set_per_process_memory_fraction(
        plan["CUDA_cap_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    with torch.random.fork_rng(devices=[0]):
        model, state = load_checkpoint(plan["model"]["checkpoint"]["path"], "cuda")
    assert (
        state["loaded_sha256"] == plan["model"]["checkpoint"]["sha256"] and state["step"] == 20000
    )
    assert all(
        torch.equal(v.cpu(), state["ema"][k]) for k, v in model.restoration_state_dict().items()
    )
    del state
    model.train().to(memory_format=torch.channels_last)
    parameters = {k: p for k, p in model.named_parameters() if p.requires_grad}
    assert len(parameters) == 89 and len(model.restoration_state_dict()) == 91
    before, backbone = model_hash(model), model_hash(model.context.backbone)
    assert before == plan["model"]["expected_full_model_sha256"]
    assert backbone == plan["model"]["expected_backbone"]["sha256"]
    configuration = model.config.to_dict()
    rng, cuda_rng, py_rng, np_rng = (
        torch.get_rng_state().clone(),
        torch.cuda.get_rng_state().clone(),
        random.getstate(),
        np.random.get_state(),
    )
    counts = {"root": 0, "encoder": 0, "training_gradients": 0, "band_gradients": 0}
    began, rows, dtypes, current = time.monotonic(), [], {}, None
    output = Path(plan["work"]) / "artifacts/collected"
    output.mkdir(parents=True, exist_ok=False)

    def resources():
        assert time.monotonic() - began < plan["maximum_worker_seconds"]
        assert psutil.virtual_memory().available >= plan["runtime_available_RAM_GiB"] * 2**30
        assert shutil.disk_usage(root).free >= plan["runtime_internal_free_GiB"] * 2**30

    def pre(module, args):
        resources()
        assert counts["root"] < 16 and module.training and not model.context.backbone.training
        assert {k: tensor_hash(v) for k, v in zip(NAMES, args, strict=True)} == current[
            "input_hashes"
        ]
        counts["root"] += 1

    model.register_forward_pre_hook(pre)
    model.context.backbone.register_forward_hook(
        lambda *args: counts.update(encoder=counts["encoder"] + 1)
    )
    for label, module in (
        ("head", model.pretrained_rgb.network.m_head),
        ("hidden_conv", model.pretrained_rgb.network.m_down1[0].res[0]),
        ("tail", model.pretrained_rgb.network.m_tail),
        ("DINO_stage0", model.context.backbone.stages[0]),
    ):
        module.register_forward_hook(
            lambda m, a, value, key=label: dtypes.__setitem__(key, str(value.dtype))
        )
    try:
        with training_execution("deterministic-v1", "cuda") as execution:
            for case in plan["cases"]:
                current = case
                with np.load(checked(case["arrays"]), allow_pickle=False) as data:
                    batch = {
                        k: torch.from_numpy(data[k].copy()).to("cuda")
                        for k in (*NAMES, "target", "sensor_target")
                    }
                    mask = data["reference_block_mask"]
                for k, v in batch.items():
                    if v.ndim == 4:
                        batch[k] = v.contiguous(memory_format=torch.channels_last)
                model.set_noise(case["noise"]["shot"], case["noise"]["read"])
                vectors, observations = {}, {}
                for precision in case["precision_order"]:
                    with amp_context("cuda", dtype=precision):
                        prediction, auxiliary = model(*(batch[k] for k in NAMES), auxiliary=True)
                        loss, terms = reconstruction_loss(
                            prediction,
                            batch,
                            auxiliary,
                            camera_supervision="sensor-valid-v1",
                            reconstruction_charbonnier_epsilon=0.0003,
                        )
                    assert torch.isfinite(prediction).all() and prediction.dtype == torch.float32
                    assert dtypes["head"] == dtypes["tail"] == "torch.float32"
                    assert dtypes["hidden_conv"] == (
                        "torch.float32" if precision == "float32" else "torch.bfloat16"
                    )
                    with torch.autocast("cuda", enabled=False), ieee_fp32():
                        band = relative_band_error(prediction, batch["sensor_target"], mask)
                    if precision == "float32":
                        gradient = torch.autograd.grad(
                            band, tuple(parameters.values()), retain_graph=True, allow_unused=True
                        )
                        vectors["band"] = [
                            torch.zeros_like(p, device="cpu") if g is None else g.detach().cpu()
                            for p, g in zip(parameters.values(), gradient, strict=True)
                        ]
                        counts["band_gradients"] += 1
                    gradient = torch.autograd.grad(
                        loss, tuple(parameters.values()), allow_unused=True
                    )
                    vectors[precision] = [
                        torch.zeros_like(p, device="cpu") if g is None else g.detach().cpu()
                        for p, g in zip(parameters.values(), gradient, strict=True)
                    ]
                    counts["training_gradients"] += 1
                    predpath = output / f"prediction-{case['index']:02d}-{precision}.npy"
                    np.save(predpath, prediction.detach().cpu().numpy(), allow_pickle=False)
                    observations[precision] = {
                        "loss": float(loss.detach()),
                        "terms": {k: float(v.detach()) for k, v in terms.items()},
                        "relative_band_error": float(band.detach()),
                        "dtypes": dict(dtypes),
                        "prediction": ref(predpath),
                    }
                    del prediction, auxiliary, loss, terms, band, gradient
                    gc.collect()
                labels = ("float32", "bfloat16", "band")
                total, layers, maximum = np.zeros((3, 3)), [], 0.0
                for index, (name, parameter) in enumerate(parameters.items()):
                    values = [vectors[key][index].contiguous() for key in labels]
                    assert all(torch.isfinite(v).all() for v in values)
                    arrays = [v.numpy().ravel().astype(np.float64) for v in values]
                    gram = np.array([[float(a @ b) for b in arrays] for a in arrays])
                    second = np.array(
                        [
                            [
                                float(torch.dot(a.reshape(-1).double(), b.reshape(-1).double()))
                                for b in values
                            ]
                            for a in values
                        ]
                    )
                    maximum = max(maximum, float(np.max(np.abs(gram - second))))
                    np.testing.assert_allclose(gram, second, rtol=2e-10, atol=1e-9)
                    total += gram
                    layers.append(
                        {
                            "name": name,
                            "shape": list(parameter.shape),
                            "gradients_sha256": {
                                key: tensor_hash(value)
                                for key, value in zip(labels, values, strict=True)
                            },
                            "Gram_F64": gram.tolist(),
                        }
                    )
                retained = None
                if case["index"] in plan["retained_full_gradient_cases"]:
                    file = output / f"full-gradients-{case['index']:02d}.npz"
                    np.savez(
                        file,
                        **{
                            f"g{i}_{j}": value.numpy()
                            for i, key in enumerate(labels)
                            for j, value in enumerate(vectors[key])
                        },
                    )
                    retained = ref(file)
                row = {
                    "case": case,
                    "observations": observations,
                    "layers": layers,
                    "Gram_F64": total.tolist(),
                    "summary": gradient_summary(total),
                    "maximum_two_reduction_error": maximum,
                    "full_gradients": retained,
                }
                rows.append(row)
                save(
                    root / "progress-v1.json",
                    {
                        "completed_cases": len(rows),
                        "counts": counts,
                        "last_summary": row["summary"],
                    },
                )
                print(
                    {"case": case["index"], "counts": counts, "summary": row["summary"]}, flush=True
                )
                del vectors, batch, arrays, values
                gc.collect()
            assert counts == {
                "root": 16,
                "encoder": 16,
                "training_gradients": 16,
                "band_gradients": 8,
            }
        assert (
            model_hash(model) == before
            and model_hash(model.context.backbone) == backbone
            and model.config.to_dict() == configuration
        )
        assert all(p.grad is None for p in model.parameters())
        assert (
            torch.equal(rng, torch.get_rng_state())
            and torch.equal(cuda_rng, torch.cuda.get_rng_state())
            and random.getstate() == py_rng
        )
        after = np.random.get_state()
        assert (
            after[0] == np_rng[0]
            and np.array_equal(after[1], np_rng[1])
            and after[2:] == np_rng[2:]
        )
        guard(plan)
        save(
            root / "collection-v1.json",
            {
                "status": "completed16-new-precision-gradient-forwards-zero-optimizer-updates",
                "plan": ref(path),
                "rows": rows,
                "counts": counts,
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "model_backbone_config_and_rng_unchanged": True,
                "model_hash": before,
                "backbone_hash": backbone,
                "training_execution": execution,
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "optimizer_updates": 0,
                "new_noise_observations": 0,
                "RAW_decodes": 0,
                "scope": plan["scope"],
            },
        )
    except BaseException as error:
        save(
            root / "failure-v1.json",
            {
                "error": repr(error),
                "counts": counts,
                "completed_rows": rows,
                "status": "failed-preserved-no-automatic-retry",
            },
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "collect"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    else:
        collect(args.path.resolve())
