"""Independent CPU audit for the separately initialized V67 joint stage."""

import hashlib
import json
import math
from pathlib import Path

import torch
from audit_fresh_dino_statistics import sha

from demosaic.model import ModelConfig


def audit_joint_state(checkpoint, recipe, plan, log_path, steps):
    """Check original schedule, joint optimizer, initialization, source and data."""
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
    assert sha(plan["parent"]) == plan["parent_sha256"]
    parent = torch.load(plan["parent"], map_location="cpu", weights_only=True, mmap=True)
    cfg = state["config"]
    assert state["step"] == steps <= cfg["steps"] == recipe["steps"] == 10000
    assert cfg["raw_kernel_only"] is recipe["raw_kernel_only"] is False
    assert state["model_config"] == parent["model_config"]
    assert state["model_config"] == ModelConfig(**recipe["model"]).to_dict()
    assert state["model_config"]["raw_kernel_reconstruction"] is True
    assert state["model_config"]["raw_kernel_phase_conditioning"] is True
    assert cfg["initialized_from"]["sha256"] == plan["parent_sha256"]
    assert cfg["source_sha256"] == plan["source_bundle_sha256"]
    assert parent["step"] == 1000 and parent["config"]["raw_kernel_only"] is True
    for key, value in recipe.items():
        if key != "validation_protocol":
            assert cfg[key] == value, key
    assert (
        sha(cfg["validation_protocol"])
        == sha(recipe["validation_protocol"])
        == cfg["validation_protocol_sha256"]
    )
    assert len(state["model"]) == len(state["ema"]) == len(parent["ema"]) == 94
    assert state["model"].keys() == state["ema"].keys() == parent["ema"].keys()
    buffers = {"context.mean", "context.std"}
    parameters = [n for n in state["model"] if n not in buffers]
    assert len(parameters) == 92
    assert sum(state["model"][n].numel() for n in parameters) == 32931920
    for name in state["model"]:
        assert state["model"][name].shape == state["ema"][name].shape == parent["ema"][name].shape
    for name in buffers:
        assert torch.equal(state["model"][name], parent["ema"][name])
        assert torch.equal(state["ema"][name], parent["ema"][name])
    changed = {
        key: [n for n in parameters if not torch.equal(state[key][n], parent["ema"][n])]
        for key in ["model", "ema"]
    }
    for changed_names in changed.values():
        for prefix in [
            "pretrained_rgb.network.",
            "pretrained_rgb.measurement_adapter.",
            "pretrained_rgb.raw_kernel.",
            "context.",
        ]:
            assert any(n.startswith(prefix) for n in changed_names), prefix
    optimizer = state["optimizer"]
    assert len(optimizer["state"]) == 92 and len(optimizer["param_groups"]) == 1
    ids = optimizer["param_groups"][0]["params"]
    assert len(ids) == len(set(ids)) == 92 and set(ids) == set(optimizer["state"])
    assert {int(v["step"]) for v in optimizer["state"].values()} == {steps}
    for name, index in zip(parameters, ids, strict=True):
        item = optimizer["state"][index]
        assert item["exp_avg"].shape == item["exp_avg_sq"].shape == state["model"][name].shape
        assert torch.all(item["exp_avg_sq"] >= 0)
    assert all(torch.isfinite(v).all() for key in ["model", "ema"] for v in state[key].values())
    assert all(
        torch.isfinite(v).all()
        for item in optimizer["state"].values()
        for v in item.values()
        if isinstance(v, torch.Tensor)
    )
    assert all(key in state for key in ["python_rng", "torch_rng", "cuda_rng"])
    assert len(state["cuda_rng"]) == (1 if torch.device(cfg["device"]).type == "cuda" else 0)
    assert math.isfinite(state["best"])
    snapshot = Path(cfg["source_snapshot"])
    package = Path(plan["package"]) / "demosaic"
    project = package.parents[1]
    names = {p.name for p in package.glob("*.py")}
    for name in names:
        assert sha(snapshot / name) == sha(package / name)
    fixed = {
        "pyproject.toml": project / "pyproject.toml",
        "uv.lock": project / "uv.lock",
        "Noise2VST-LICENSE": project / "third_party/gaussian/Noise2VST-LICENSE",
        "KAIR-LICENSE": project / "third_party/gaussian/KAIR-LICENSE",
        "paired-manifest.json": Path(cfg["paired_manifest"]),
        "raw-clean-manifest.json": Path(cfg["raw_clean_manifest"]),
        "validation-manifest.jsonl": Path(cfg["validation_manifest"]),
        "validation_protocol.yaml": Path(recipe["validation_protocol"]),
    }
    for name, path in fixed.items():
        assert sha(snapshot / name) == sha(path)
    assert {p.name for p in snapshot.iterdir()} == names | set(fixed) | {"manifest.jsonl"}
    bundle = hashlib.sha256()
    for name in sorted(names | set(fixed)):
        bundle.update(name.encode() + (snapshot / name).read_bytes())
    assert bundle.hexdigest() == cfg["source_sha256"]
    assert sha(snapshot / "manifest.jsonl") == sha(cfg["manifest"])
    for key in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]:
        assert cfg[key + "_sha256"] == sha(cfg[key])
    records = [
        r
        for line in Path(log_path).read_text().splitlines()
        if (r := json.loads(line)).get("event") == "train"
    ]
    assert [r["step"] for r in records] == sorted(
        {1, *range(cfg["log_every"], steps + 1, cfg["log_every"])}
    )
    assert {r["domain"] for r in records} == {"synthetic", "paired-RAW", "native-RAW-synthetic"}
    for record in records:
        assert all(math.isfinite(v) for v in record.values() if isinstance(v, (int, float)))
        assert len(record["batch_sha256"]) == 64
        step = record["step"]
        progress = max(0, step - cfg["warmup_steps"]) / max(1, cfg["steps"] - cfg["warmup_steps"])
        expected = (
            cfg["lr"]
            * min(1, step / cfg["warmup_steps"])
            * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        )
        assert record["lr"] == expected
    assert optimizer["param_groups"][0]["lr"] == records[-1]["lr"]
    return {
        "checkpoint": checkpoint,
        "step": steps,
        "original_planned_updates": cfg["steps"],
        "source_bundle_sha256": cfg["source_sha256"],
        "source_bundle_independently_reconstructed": True,
        "model_tensors": len(state["model"]),
        "EMA_tensors": len(state["ema"]),
        "AdamW_states": len(optimizer["state"]),
        "trainable_parameters": 32931920,
        "all_state_finite": True,
        "normalization_buffers_bitwise_parent": True,
        "changed_parent_parameter_tensors": changed,
        "all_original_recipe_fields_exact_except_resolved_protocol": True,
        "four_manifest_hashes_and_snapshot_contents_exact": True,
        "complete_RNG_present": True,
        "all_logged_LRs_match_original10000_schedule": True,
        "training_log": {
            "path": str(log_path),
            "sha256": sha(log_path),
            "train_rows": len(records),
        },
        "learning_rates": [g["lr"] for g in optimizer["param_groups"]],
        "scope": "Saved restoration/optimizer/source/data audit. DINO weights are deliberately absent from restoration checkpoints; actual frozen-backbone training checks are separate preflight evidence.",
    }
