"""Replay one genuine training input; diagnose execution, never train or select models."""

import argparse
import hashlib
import json
import os
import random
import shutil
import time
from pathlib import Path

import psutil
import torch
import yaml
from profile_raw_kernel_inference import model_hash
from train_directional_interval_trial import guard

import demosaic.train as training
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.precision import amp_context, ieee_fp32
from demosaic.safety import writable_path

POLICIES = {
    "benchmark": (True, False, False),
    "no-benchmark": (False, False, False),
    "strict": (False, True, True),
}


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def cpu_copy(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone(memory_format=torch.preserve_format)
    if isinstance(value, dict):
        return {k: cpu_copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [cpu_copy(v) for v in value]
    if isinstance(value, tuple):
        return tuple(cpu_copy(v) for v in value)
    return value


def require_resources():
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(Path.cwd()).free > 128 * 2**30


def capture(plan, output):
    """Use the real trainer to capture its initial CPU state and first clean batch."""
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert not torch.cuda.is_initialized()
    cfg = yaml.safe_load(Path(plan["template"]["path"]).read_text())
    assert (cfg["batch_size"], cfg["patch_size"], cfg["seed"]) == (16, 256, 51)
    assert cfg["data_seed_per_step"] and cfg["reference_interval_weight"] == 0
    cfg.update(device="cpu", workers=0, paired_workers=0, raw_clean_workers=0)
    cfg["run"] = str(output / "discarded-capture-run")
    config_path = output / "capture.yaml"
    config_path.write_text(yaml.safe_dump(cfg))
    constructor, prepare = training.JointDemosaic, training.prepare_training_batch
    current = {}

    class Captured(Exception):
        pass

    def instrument(options):
        current["model"] = constructor(options)
        return current["model"]

    def intercept(data_step, domain, clean, **kwargs):
        assert (data_step, domain) == (1, "commons")
        net = current["model"]
        parent = torch.load(
            plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True
        )
        actual = net.restoration_state_dict()
        assert len(actual) == 99 and all(
            torch.equal(actual[k], v) for k, v in parent["ema"].items()
        )
        assert model_hash(net.pretrained_rgb.raw_directional) == plan["initial_branch_sha256"]
        assert model_hash(net.context.backbone) == plan["DINO_sha256"]
        torch.save(
            {
                "model": cpu_copy(actual),
                "model_config": net.config.to_dict(),
                "clean": cpu_copy(clean),
                "torch_rng": torch.get_rng_state(),
                "config": cfg,
                "data_step": data_step,
                "domain": domain,
            },
            output / "initial-and-clean.pt",
        )
        raise Captured

    training.JointDemosaic, training.prepare_training_batch = instrument, intercept
    try:
        training.train(config_path, initialize=plan["parent"]["path"], stop_after=1)
        raise AssertionError("Capture must stop before degradation/forward/backward/optimizer")
    except Captured:
        pass
    finally:
        training.JointDemosaic, training.prepare_training_batch = constructor, prepare
    assert not (Path(cfg["run"]) / "last.pt").exists()
    assert not torch.cuda.is_initialized()
    save(
        output / "capture.json",
        {
            "status": "captured-genuine-initial-state-and-first-clean-training-batch-CPU-only",
            "driver": ref(__file__),
            "payload": ref(output / "initial-and-clean.pt"),
            "initial_model_sha256": model_hash(current["model"]),
            "restoration_tensors": 99,
            "shape": list(clean_shape(output)),
            "CUDA_initialized": False,
            "scope": "Actual trainer initialization and selected clean input. CPU placement and zero loader workers only; no noisy input, inference, loss, gradient, update or evaluation. CUDA degradation hash must match the original full training record before GPU replay.",
        },
    )


def clean_shape(output):
    return torch.load(
        output / "initial-and-clean.pt", map_location="cpu", weights_only=True, mmap=True
    )["clean"]["rgb"].shape


def load_model(payload, device):
    torch.manual_seed(51)
    random.seed(51)
    model = JointDemosaic(ModelConfig.from_checkpoint(payload["model_config"]))
    result = model.load_state_dict(payload["model"], strict=False)
    assert not result.unexpected_keys
    assert result.missing_keys and all(
        k.startswith("context.backbone.") for k in result.missing_keys
    )
    model = model.to(device)
    if payload["config"]["channels_last"]:
        model = model.to(memory_format=torch.channels_last)
    model.train()
    return model


def gpu_input(plan, output):
    assert not (output / "original-first-batch.pt").exists()
    assert not (output / "gpu-input.json").exists()
    device = torch.device("cuda", torch.cuda.current_device())
    torch.cuda.set_per_process_memory_fraction(
        24 * 2**30 / torch.cuda.get_device_properties(device).total_memory
    )
    payload = torch.load(
        Path(plan["output"]) / "initial-and-clean.pt",
        map_location="cpu",
        weights_only=True,
        mmap=True,
    )
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = True
    model = load_model(payload, device)
    torch.set_rng_state(payload["torch_rng"])
    batch = training.prepare_training_batch(
        1,
        "commons",
        payload["clean"],
        model=model,
        device=device,
        config=payload["config"],
        seed=51,
    )
    actual_hash = training.batch_fingerprint(batch)
    assert actual_hash == plan["original_first_full_batch_sha256"], (
        "Actual noisy input differs; do not continue replay"
    )
    torch.save(
        {
            "batch": cpu_copy(batch),
            "strides": {k: list(v.stride()) for k, v in batch.items()},
            "torch_rng": torch.get_rng_state(),
            "cuda_rng": torch.cuda.get_rng_state_all(),
        },
        output / "original-first-batch.pt",
    )
    save(
        output / "gpu-input.json",
        {
            "status": "actual-CUDA-input-exactly-matches-original-first-training-batch",
            "payload": ref(output / "original-first-batch.pt"),
            "batch_sha256": actual_hash,
            "driver": ref(__file__),
            "scope": "Noise generation only, no neural inference, losses, updates or validation.",
        },
    )


def replay(plan, output, policy, cpu_check):
    source = Path(plan["output"])
    payload = torch.load(
        source / "initial-and-clean.pt", map_location="cpu", weights_only=True, mmap=True
    )
    device = torch.device("cpu" if cpu_check else "cuda")
    if not cpu_check:
        torch.cuda.set_per_process_memory_fraction(
            24 * 2**30 / torch.cuda.get_device_properties(device).total_memory
        )
    else:
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_float32_matmul_precision("high")
    model = load_model(payload, device)
    if cpu_check:
        clean = {"rgb": payload["clean"]["rgb"][:1, :, 96:160, 96:160].clone()}
        batch = training.prepare_training_batch(
            1, "commons", clean, model=model, device=device, config=payload["config"], seed=51
        )
        rng, cuda_rng = payload["torch_rng"], []
    else:
        gpu = read(source / "gpu-input.json")
        assert ref(gpu["payload"]["path"]) == gpu["payload"]
        saved = torch.load(gpu["payload"]["path"], map_location="cpu", weights_only=True, mmap=True)
        batch = {k: v.to(device) for k, v in saved["batch"].items()}
        assert all(list(v.stride()) == saved["strides"][k] for k, v in batch.items())
        rng, cuda_rng = saved["torch_rng"], saved["cuda_rng"]
        assert training.batch_fingerprint(batch) == plan["original_first_full_batch_sha256"]
    initial_hash, backbone_hash = model_hash(model), model_hash(model.context.backbone)
    assert backbone_hash == plan["DINO_sha256"]
    benchmark, deterministic, strict = POLICIES[policy]
    torch.backends.cudnn.benchmark = benchmark
    torch.backends.cudnn.deterministic = deterministic
    torch.use_deterministic_algorithms(strict)
    attempts = []
    for repeat in range(2):
        model.zero_grad(set_to_none=True)
        torch.set_rng_state(rng)
        if cuda_rng:
            torch.cuda.set_rng_state_all(cuda_rng)
        model.set_noise(batch["shot"], batch["read"])
        if not cpu_check:
            torch.cuda.synchronize()
        started = time.perf_counter()
        try:
            with amp_context(device, dtype="float32" if cpu_check else "bfloat16"):
                prediction, auxiliary = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                    auxiliary=True,
                )
                loss, terms = reconstruction_loss(
                    prediction,
                    batch,
                    auxiliary,
                    physical_fp32=True,
                    normalized_sensor_weight=0,
                    multiscale_sensor_weight=0,
                    objective="charbonnier-v1",
                    camera_supervision="sensor-valid-v1",
                    reference_interval_weight=0,
                )
            assert torch.isfinite(loss)
            with ieee_fp32():
                loss.backward()
                grad_norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1, error_if_nonfinite=True
                )
            if not cpu_check:
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            gradients = {n: p.grad for n, p in model.named_parameters() if p.requires_grad}
            assert len(gradients) == 97 and all(
                g is not None and torch.isfinite(g).all() for g in gradients.values()
            )
            tensors = {
                "prediction": prediction,
                "auxiliary": auxiliary,
                **{"gradient:" + n: v for n, v in gradients.items()},
            }
            result = {
                "repeat": repeat,
                "loss": loss.item(),
                "terms": {k: v.item() for k, v in terms.items()},
                "preclip_gradient_norm": float(grad_norm),
                "tensor_sha256": training.batch_fingerprint(tensors),
                "seconds_including_first_search_if_enabled": elapsed,
            }
            if repeat == 0:
                torch.save(cpu_copy(tensors), output / "tensors.pt")
                result["saved_tensors"] = ref(output / "tensors.pt")
            attempts.append(result)
            del prediction, auxiliary, loss, terms, gradients, tensors
        except RuntimeError as error:
            if policy != "strict" or "determin" not in str(error).lower():
                raise
            attempts.append(
                {
                    "repeat": repeat,
                    "status": "strict-policy-rejected-operation",
                    "error": str(error),
                }
            )
            break
    assert model_hash(model) == initial_hash
    assert model_hash(model.context.backbone) == backbone_hash
    assert not cpu_check or not torch.cuda.is_initialized()
    save(
        output / "result.json",
        {
            "status": "completed-execution-replay-no-optimizer-updates",
            "driver": ref(__file__),
            "policy": policy,
            "settings": {
                "benchmark": benchmark,
                "cudnn_deterministic": deterministic,
                "strict_algorithms": strict,
                "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            },
            "cpu_check": cpu_check,
            "input_shape": list(batch["packed"].shape),
            "input_sha256": training.batch_fingerprint(batch),
            "initial_model_sha256": initial_hash,
            "DINO_sha256": backbone_hash,
            "model_state_unchanged": True,
            "attempts": attempts,
            "scope": "Same unmodified genuine initialization/input; forward, loss and clipped gradients only, with no optimizer/EMA updates. CPU harness check uses B1/native64/FP32 and CPU noise, not the original CUDA observation. GPU uses actual B16/native256/BF16 first training batch, not held-out evaluation. Timing includes cold algorithm search and is not steady throughput. No quality, convergence, long-run reproducibility, numerical cause assignment or promotion claim.",
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["capture", "gpu-input", "replay"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--policy", choices=POLICIES, default="benchmark")
    parser.add_argument("--cpu-check", action="store_true")
    args = parser.parse_args()
    os.nice(10)
    torch.set_num_threads(2 if args.cpu_check or args.mode == "capture" else 4)
    plan = read(args.plan)
    assert ref(__file__) == plan["worker"]
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    guard(read(plan["review_plan"]["path"]))
    require_resources()
    output = writable_path(args.output or plan["output"])
    output.mkdir(parents=True, exist_ok=args.mode in ("capture", "gpu-input"))
    if args.mode == "capture":
        assert not (output / "initial-and-clean.pt").exists()
        capture(plan, output)
    elif args.mode == "gpu-input":
        gpu_input(plan, output)
    else:
        replay(plan, output, args.policy, args.cpu_check)
    guard(read(plan["review_plan"]["path"]))


if __name__ == "__main__":
    main()
