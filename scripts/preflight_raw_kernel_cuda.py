"""Prepare, then separately execute, a gated CUDA engineering check of the RAW head.

Preparation is CPU-only and archives the tested candidate package and operators.
Execution requires the exact preceding artifact owner to finish and exit. Seven
discarded production-size updates are not a trained-quality or throughput trial.
"""

import argparse
import gc
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml

from demosaic.safety import writable_path

REPO = Path("/home/dllu/proj/demosaic")
BASE = Path("/mnt/external/demosaic")
PARENT = BASE / "models/dino-convnext-palette-wide-b16-v60-step4000.pt"
PARENT_SHA = "1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e"
CPU_PROOF = BASE / "benchmarks/raw-kernel-CPU-preflight-v1/receipt.json"
CPU_PROOF_SHA = "f32da09f2f98c14ff51df76f92db176d7d840f5c6fe4d4b4f4143aec83c576b1"
MODEL_SOURCE = "411d1669b050b8074d7a9d030b3c42ef1af6764c6f20efbd08ecf5466dc632d8"
PREDECESSOR = BASE / "runs/long-commons-v63-v64-first4k-artifact-workflow-v1.json"
TERMINAL = (
    "completed-independent-artifact-integrity-awaiting-actual-native-review-and-quality-decision"
)
OBSERVATIONS = BASE / "evaluation/two-fixed-examples-v43-none10k-cpu-v1"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            abs(process.create_time() - owner["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def completed_predecessor(plan):
    """Reject a live/failed/replaced owner before any CUDA initialization."""
    status = read(plan["after_workflow"])
    if status["controller"] != plan["after_owner"]:
        raise RuntimeError("Preceding artifact workflow has a different owner")
    if alive(plan["after_owner"]):
        raise RuntimeError("Preceding artifact owner remains live; wait without restarting")
    if status["status"] != TERMINAL:
        raise RuntimeError("Preceding artifact audit has not completed successfully")
    assert sha(status["audit"]) == status["audit_sha256"]
    assert (
        read(status["audit"])["status"]
        == "completed-independent-long-data-state-native-and-RGB16-integrity-audit"
    )
    return {"path": plan["after_workflow"], "sha256": sha(plan["after_workflow"]), "result": status}


def verify_plan(plan):
    for path, digest in {**plan["inputs"], **plan["archived_files"]}.items():
        assert sha(path) == digest, path
    assert (
        plan["parent_sha256"] == PARENT_SHA
        and plan["expected_source_bundle_sha256"] == MODEL_SOURCE
    )
    fixture = yaml.safe_load(Path(plan["fixture"]).read_text())
    assert fixture["model"]["raw_kernel_reconstruction"] is True
    assert fixture["model"]["raw_kernel_windows"] == [1, 5, 17]
    assert (fixture["batch_size"], fixture["patch_size"], fixture["precision"]) == (
        16,
        256,
        "bfloat16",
    )
    assert fixture["steps"] == 20000 and fixture["seed"] == 49
    assert fixture["flat_fraction"] == fixture["synthetic_fraction"] == 0
    assert fixture["workers"] == fixture["raw_clean_workers"] == fixture["paired_workers"] == 0
    assert plan["fixture_updates"] == 7
    return fixture


def prepare(output, after_workflow):
    from demosaic.model import ModelConfig
    from demosaic.train import training_domain

    assert not torch.cuda.is_initialized()
    output = writable_path(output)
    assert not output.exists()
    assert sha(CPU_PROOF) == CPU_PROOF_SHA and sha(PARENT) == PARENT_SHA
    proof = read(CPU_PROOF)
    assert proof["status"] == "completed-CPU-engineering-only-RAW-kernel-prototype"
    assert all(sha(path) == digest for path, digest in proof["source_files"].items())
    preceding = read(after_workflow)
    assert alive(preceding["controller"]) or preceding["status"] == TERMINAL
    template = REPO / "configs/dino-convnext-wide-long-control-b16-v63.yaml"
    cfg = yaml.safe_load(template.read_text())
    cfg["model"].update(raw_kernel_reconstruction=True, raw_kernel_windows=[1, 5, 17])
    assert ModelConfig(**cfg["model"]).raw_kernel_reconstruction
    cfg.update(
        run=str(output / "actual-B16"),
        workers=0,
        raw_clean_workers=0,
        paired_workers=0,
        flat_fraction=0,
        synthetic_fraction=0,
        log_every=1,
        checkpoint_every=7,
        val_batches=1,
        validation_images=2,
        validation_protocol=str(REPO / "configs/evaluation.yaml"),
    )
    domains = [
        training_domain(s, cfg["seed"], cfg["paired_fraction"], cfg["raw_clean_fraction"])
        for s in range(1, 8)
    ]
    assert set(domains) == {"commons", "native", "paired"} and domains.count("commons") >= 2
    paths = [CPU_PROOF, PARENT, template, REPO / "configs/evaluation.yaml", Path(preceding["plan"])]
    paths += [
        Path(cfg[k])
        for k in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]
    ]
    paths += [OBSERVATIONS / f"observation-{i}-cpu.npz" for i in range(2)]
    inputs = {str(path): sha(path) for path in paths}
    output.mkdir(parents=True)
    project = output / "candidate"
    package = project / "src/demosaic"
    package.mkdir(parents=True)
    archived = {}
    for original, digest in proof["source_files"].items():
        target = package / Path(original).name
        target.write_bytes(Path(original).read_bytes())
        assert sha(target) == digest
        archived[str(target)] = digest
    for name in [
        "pyproject.toml",
        "uv.lock",
        "third_party/gaussian/Noise2VST-LICENSE",
        "third_party/gaussian/KAIR-LICENSE",
        "third_party/dinov3/LICENSE.md",
    ]:
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / name).read_bytes())
        archived[str(target)] = sha(target)
    tools = output / "tools"
    tools.mkdir()
    for path in sorted((REPO / "scripts").glob("*.py")):
        target = tools / path.name
        target.write_bytes(path.read_bytes())
        archived[str(target)] = sha(target)
    fixture = output / "fixture.yaml"
    fixture.write_text(yaml.safe_dump(cfg, sort_keys=False))
    archived[str(fixture)] = sha(fixture)
    plan = {
        "status": "prepared-CPU-only-awaiting-actual-predecessor-exit-and-CUDA-checks",
        "after_workflow": str(after_workflow.resolve()),
        "after_owner": preceding["controller"],
        "parent": str(PARENT),
        "parent_sha256": PARENT_SHA,
        "expected_source_bundle_sha256": MODEL_SOURCE,
        "package": str(project / "src"),
        "operator": str(tools / Path(__file__).name),
        "fixture": str(fixture),
        "fixture_updates": 7,
        "domains": domains,
        "inputs": inputs,
        "archived_files": archived,
        "root_model_source_at_preparation": proof["source_files"],
        "CUDA_initialized": torch.cuda.is_initialized(),
        "scope": "Prepared engineering fixture only. Actual B16/native256/BF16, seed49/20k, original reviewed40170Commons/native128/paired32, forced real Commons/workers0/val2. Intended saved-state/RNG/optimizer/EMA, gradient,64clean native64 constant cases and peak allocation checks. No CUDA execution, quality trial, throughput or automatic model promotion.",
    }
    verify_plan(plan)
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(
        json.dumps(
            {"plan": str(output / "plan.json"), "status": plan["status"], "CUDA_initialized": False}
        ),
        flush=True,
    )


def photo(index, device):
    path = OBSERVATIONS / f"observation-{index}-cpu.npz"
    with np.load(path, allow_pickle=False) as values:
        batch = {
            k: torch.from_numpy(values[k].copy()).to(device)
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
    return path, batch


def call(model, batch, precision):
    from demosaic.precision import amp_context

    model.set_noise(0.00256, 0.0000262144)
    with amp_context("cuda", dtype=precision):
        return model(
            batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
        )


def initialized_parent(cfg):
    from demosaic.cfa import bilinear
    from demosaic.model import JointDemosaic, ModelConfig

    parent = torch.load(PARENT, map_location="cpu", weights_only=True, mmap=True)
    model = JointDemosaic(ModelConfig(**cfg["model"]))
    result = model.load_state_dict(parent["ema"], strict=False)
    new = sorted(k for k in result.missing_keys if not k.startswith("context.backbone."))
    assert not result.unexpected_keys and new == [
        "pretrained_rgb.raw_kernel.coefficients.bias",
        "pretrained_rgb.raw_kernel.coefficients.weight",
    ]
    current = model.restoration_state_dict()
    assert all(torch.equal(current[k], v) for k, v in parent["ema"].items())
    assert all(not p.requires_grad for p in model.context.backbone.parameters())
    model.eval().to("cuda", memory_format=torch.channels_last)
    _, batch = photo(0, "cuda")
    with torch.inference_mode():
        actual = call(model, batch, "bfloat16")
        expected = bilinear(batch["packed"], batch["colors"])
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    return {
        "all_existing_parent_EMA_tensors_exact": True,
        "only_new_tensors": new,
        "actual_DINO_backbone_frozen": True,
        "initial_GPU_BF16_output_exact_bilinear_not_parent_quality": True,
    }


def extra_saved_checks(checkpoint, state, output):
    from demosaic.cfa import PATTERNS, color_indices, mosaic
    from demosaic.inference import load_checkpoint
    from demosaic.model import JointDemosaic, ModelConfig

    manual = JointDemosaic(ModelConfig.from_checkpoint(state["model_config"])).to(
        "cuda", memory_format=torch.channels_last
    )
    loaded = manual.load_state_dict(state["ema"], strict=False)
    assert not loaded.unexpected_keys and all(
        k.startswith("context.backbone.") for k in loaded.missing_keys
    )
    portable, _ = load_checkpoint(checkpoint, "cuda")
    portable.to(memory_format=torch.channels_last)
    manual.eval()
    portable.eval()
    first, second = manual.state_dict(), portable.state_dict()
    assert first.keys() == second.keys() and all(torch.equal(first[k], second[k]) for k in first)
    photos = []
    with torch.inference_mode():
        for i in range(2):
            path, batch = photo(i, "cuda")
            a, b = [call(model, batch, "bfloat16") for model in [manual, portable]]
            torch.testing.assert_close(a, b, rtol=0, atol=0)
            assert a.dtype == torch.float32 and torch.isfinite(a).all()
            saved = output / f"portable-photo-{i}-BF16-f32.npy"
            np.save(saved, a.cpu().numpy(), allow_pickle=False)
            photos.append(
                {
                    "input": str(path),
                    "input_sha256": sha(path),
                    "prediction": str(saved),
                    "prediction_sha256": sha(saved),
                    "BF16_portable_EMA_exact": True,
                }
            )
        palette = torch.tensor(
            [[0.02, 0.18, 0.9], [1.4, -0.02, 0.00001], [0, 0, 0], [0.9, 0.2, 0.1]], device="cuda"
        )
        colors = torch.stack([color_indices(p, device="cuda") for p in PATTERNS]).repeat_interleave(
            4, 0
        )
        target = palette.repeat(4, 1)[..., None, None].expand(-1, -1, 64, 64)
        raw = mosaic(target, colors)
        wb = torch.tensor([2.0, 1.0, 1.5], device="cuda")[None].expand(16, -1)
        matrix = torch.eye(3, device="cuda")[None].expand(16, -1, -1)
        cases = []
        for shot, read_noise in [(0.0, 0.0), (0.00256, 0.0000262144)]:
            portable.set_noise(shot, read_noise)
            for precision in ["float32", "bfloat16"]:
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=precision == "bfloat16"):
                    restored = portable(
                        raw, raw.clamp_min(0) * shot + read_noise, colors, wb, matrix
                    )
                error = float((restored - target).abs().max())
                assert (
                    restored.dtype == torch.float32
                    and torch.isfinite(restored).all()
                    and error <= 3e-7
                )
                cases.append(
                    {
                        "shot": shot,
                        "read": read_noise,
                        "precision": precision,
                        "clean_native64_fields": 16,
                        "maximum_RGB_error": error,
                    }
                )
    # Use the actual model state for a gradient probe, not its slower-moving EMA.
    manual.load_state_dict(state["model"], strict=False)
    manual.zero_grad(set_to_none=True)
    _, batch = photo(0, "cuda")
    loss = call(manual, batch, "bfloat16").square().mean()
    loss.backward()
    names = [
        "pretrained_rgb.network.m_head.weight",
        "pretrained_rgb.network.m_tail.weight",
        "pretrained_rgb.raw_kernel.coefficients.weight",
    ]
    parameters = dict(manual.named_parameters())
    gradients = {}
    for name in names:
        gradient = parameters[name].grad
        assert gradient is not None and torch.isfinite(gradient).all() and gradient.abs().sum() > 0
        gradients[name] = float(gradient.float().norm())
    assert all(p.grad is None and not p.requires_grad for p in manual.context.backbone.parameters())
    return {
        "all_manual_and_portable_EMA_tensors_including_DINO_exact": True,
        "BF16_photos": photos,
        "clean_constant_cases": cases,
        "total_clean_constant_fields": 64,
        "native256_B1_BF16_gradient_norms": gradients,
        "frozen_DINO_has_no_gradients": True,
        "scope": "Engineering checks of discarded seven-update state. Clean fields contain no added noise. Not noisy-field unbiasedness or restoration-quality evidence.",
    }


def execute(output):
    output = writable_path(output)
    plan = read(output / "plan.json")
    preceding = completed_predecessor(plan)
    cfg = verify_plan(plan)
    assert not (output / "receipt.json").exists() and not Path(cfg["run"]).exists()
    from preflight_flat_palette_cuda import portable_predictions

    from demosaic import model as module
    from demosaic.train import train

    assert Path(module.__file__).resolve() == Path(plan["package"]) / "demosaic/model.py"
    assert not torch.cuda.is_initialized()
    assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 32
    assert psutil.disk_usage(BASE).free / 1024**3 > 512
    torch.set_num_threads(4)
    initial = initialized_parent(cfg)
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    checkpoint = train(plan["fixture"], initialize=PARENT, stop_after=plan["fixture_updates"])
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == 7 and state["config"]["steps"] == 20000
    assert state["config"]["source_sha256"] == MODEL_SOURCE
    assert state["config"]["initialized_from"]["sha256"] == PARENT_SHA
    assert len(state["model"]) == len(state["ema"]) == 93 and len(state["optimizer"]["state"]) == 91
    assert {int(v["step"]) for v in state["optimizer"]["state"].values()} == {7}
    assert all(torch.isfinite(v).all() for key in ["model", "ema"] for v in state[key].values())
    assert all(
        torch.isfinite(v).all()
        for item in state["optimizer"]["state"].values()
        for v in item.values()
        if isinstance(v, torch.Tensor)
    )
    rows = [
        r
        for line in (Path(cfg["run"]) / "metrics.jsonl").read_text().splitlines()
        if (r := json.loads(line)).get("event") == "train"
    ]
    assert [r["step"] for r in rows] == list(range(1, 8))
    assert {r["domain"] for r in rows} == {"synthetic", "native-RAW-synthetic", "paired-RAW"}
    assert all(math.isfinite(v) for r in rows for v in r.values() if isinstance(v, (int, float)))
    portable = portable_predictions(checkpoint, state, cfg)
    extra = extra_saved_checks(checkpoint, state, output)
    verify_plan(plan)
    assert sha(preceding["path"]) == preceding["sha256"]
    result = {
        "status": "completed-discarded-B16-native256-CUDA-RAW-kernel-engineering-checks",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "preceding_completed_workflow": preceding,
        "initialization": initial,
        "checkpoint": {"path": str(checkpoint), "sha256": sha(checkpoint)},
        "all93_model93_EMA91_AdamW_finite": True,
        "original_planned_updates": 20000,
        "training_observations": rows,
        "FP16_portable_predictions_and_saved_state_RNG_restoration": portable,
        "extra_saved_checks": extra,
        "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
        "device": torch.cuda.get_device_name(),
        "compute_capability": torch.cuda.get_device_capability(),
        "driver_sha256": sha(__file__),
        "scope": "Seven discarded B16/native256/BF16 updates; zero workers, forced real Commons, val2. State/optimizer/RNG restoration checks do not establish deterministic CUDA optimization after restart. Constants are clean native64 fields, with no added noise. Peak CUDA allocation is not total unified RAM or throughput. No quality trial, production continuation, source/data substitution, model promotion or protected-final scores.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "receipt": str(output / "receipt.json"),
                "peak_cuda_allocated_bytes": result["peak_cuda_allocated_bytes"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--after-workflow", type=Path, default=PREDECESSOR)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare(args.output, args.after_workflow)
    else:
        execute(args.output)
