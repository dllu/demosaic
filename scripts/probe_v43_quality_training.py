"""Discarded CPU V43 training proof for the quality-first data recipe."""

import argparse
import json
import os
import shutil
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    import yaml

    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    sources = list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / name
        for name in (
            "scripts/probe_v43_quality_training.py",
            "scripts/train_directional_bank_trial.py",
            "scripts/profile_raw_kernel_inference.py",
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/dinov3/LICENSE.md",
        )
    ]
    for source in sources:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    recipe = REPO / "configs/dino-v43-curated-fine-detail-v95.yaml"
    config = yaml.safe_load(recipe.read_text())
    parent = config["initialize_parent"]
    assert ref(parent["checkpoint"])["sha256"] == parent["sha256"]
    # Deliberately pre-curation and discarded: this is not a production run.
    config.update(
        manifest="/mnt/external/demosaic/commons-post4557-reviewed-20261020-v1/manifest4.jsonl",
        run=str(work / "discarded-training"),
        device="cpu",
        amp=False,
        precision="float32",
        batch_size=1,
        patch_size=32,
        cpu_threads=2,
        workers=0,
        paired_workers=0,
        raw_clean_workers=0,
        validation_protocol=str(work / "configs/evaluation.yaml"),
        log_every=1,
        experiment_notes="Discarded CPU/B1/native32 engineering proof on pre-curation data; no validation, quality result, CUDA or timing claim.",
    )
    configuration = work / "config.yaml"
    configuration.write_text(yaml.safe_dump(config, sort_keys=False))
    plan = {
        "root": str(root),
        "work": str(work),
        "config": ref(configuration),
        "recipe": ref(recipe),
        "parent": ref(parent["checkpoint"]),
        "updates": 24,
        "inputs": [ref(recipe), ref(parent["checkpoint"])]
        + [
            ref(config[key])
            for key in ("manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest")
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": config["experiment_notes"],
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def worker(plan_path):
    import psutil
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training
    from demosaic import data
    from demosaic.model import ModelConfig

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    with (root / "worker.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    assert psutil.virtual_memory().available > 32 * 2**30
    config = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    expected_config = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
    assert json.dumps(ModelConfig(**config["model"]).to_dict(), sort_keys=True) == json.dumps(
        expected_config, sort_keys=True
    )
    constructor, prepare_batch = training.JointDemosaic, training.prepare_training_batch
    attenuation, texture = data.attenuate_photographic_contrast, data.weak_texture
    capture, observations = {}, []
    counts = {
        "forwards": 0,
        "DINO": 0,
        "contrast_attenuation": 0,
        "weak_texture": 0,
        "optimizer_steps": 0,
    }

    def instrument(options):
        model = constructor(options)
        capture["model"] = model

        def before(module, args, kwargs):
            assert len(args) == 5 and set(kwargs) == {"auxiliary"} and kwargs["auxiliary"] is True
            assert all(isinstance(x, torch.Tensor) and x.device.type == "cpu" for x in args)
            if counts["forwards"] == 0:
                capture["initial_model_sha256"] = model_hash(module)
                assert (
                    capture["initial_model_sha256"]
                    == "4a45d92210acaeca3d4189c78eb22aa1cbc33f28b971dbeb56d1f6f29d62ed9a"
                )
                capture["DINO_sha256"] = model_hash(module.context.backbone)
                assert (
                    capture["DINO_sha256"]
                    == "35035ba142eb119cd5980cf0d9809bfa28f622538c259ffb0fcf348ca6e68898"
                )
                assert set(module.restoration_state_dict()) == set(parent["ema"])
                assert all(
                    torch.equal(value, parent["ema"][name])
                    for name, value in module.restoration_state_dict().items()
                )
            counts["forwards"] += 1

        def dino(*_):
            counts["DINO"] += 1

        model.register_forward_pre_hook(before, with_kwargs=True)
        model.context.backbone.register_forward_hook(dino)
        return model

    def batch(*args, **kwargs):
        value = prepare_batch(*args, **kwargs)
        observations.append(training.batch_fingerprint(value))
        return value

    def attenuated(*args, **kwargs):
        counts["contrast_attenuation"] += 1
        return attenuation(*args, **kwargs)

    def textured(*args, **kwargs):
        counts["weak_texture"] += 1
        return texture(*args, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("No optical PSF is permitted in this recipe")

    optimizer_factory = training.make_optimizer

    def optimizer(model, options):
        result = optimizer_factory(model, options)

        def after(_optimizer, _args, _kwargs):
            counts["optimizer_steps"] += 1
            assert all(p.grad is None for p in model.context.backbone.parameters())

        result.register_step_post_hook(after)
        return result

    training.JointDemosaic, training.prepare_training_batch = instrument, batch
    training.make_optimizer = optimizer
    data.attenuate_photographic_contrast, data.weak_texture = attenuated, textured
    data.optical_blur = forbidden
    checkpoint = training.train(
        plan["config"]["path"], initialize=plan["parent"]["path"], stop_after=plan["updates"]
    )
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    model = capture.pop("model")
    assert model_hash(model.context.backbone) == capture["DINO_sha256"]
    assert model_hash(model) != capture["initial_model_sha256"]
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    for section in ("model", "ema"):
        assert all(torch.isfinite(value).all() for value in state[section].values())
        assert any(
            not torch.equal(value, parent["ema"][name]) for name, value in state[section].items()
        )
    assert (
        state["step"]
        == counts["optimizer_steps"]
        == counts["forwards"]
        == counts["DINO"]
        == plan["updates"]
    )
    metrics = [
        json.loads(line) for line in (checkpoint.parent / "metrics.jsonl").read_text().splitlines()
    ]
    assert {m["event"] for m in metrics} == {"train"}
    assert {m["domain"] for m in metrics} == {"synthetic", "native-RAW-synthetic", "paired-RAW"}
    assert all(
        torch.isfinite(value).all()
        for values in state["optimizer"]["state"].values()
        for value in values.values()
        if isinstance(value, torch.Tensor)
    )
    assert not torch.cuda.is_initialized()
    guard(plan)
    save(
        root / "receipt.json",
        {
            "status": "completed-discarded-CPU-training-proof",
            "plan": ref(plan_path),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "checkpoint": ref(checkpoint),
            "metrics": ref(checkpoint.parent / "metrics.jsonl"),
            "counts": counts,
            **capture,
            "batch_fingerprints": observations,
            "domains": sorted({m["domain"] for m in metrics}),
            "exact_original_V43_EMA_and_architecture": True,
            "frozen_DINO_and_finite_gradients_optimizer_EMA": True,
            "CUDA_initialized": False,
            "scope": plan["scope"],
        },
    )
    print(ref(root / "receipt.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else worker)(args.path)
