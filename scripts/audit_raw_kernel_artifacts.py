"""Independently inspect the frozen RAW-head warmup state and primary artifacts."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import torch
import yaml
from audit_fresh_dino_statistics import sha
from audit_long_commons_artifacts import audit_panels
from audit_sensor_mean_artifacts import exited
from review_raw_kernel_results import REPO, completed_primary, read

from demosaic.safety import writable_path


def audit_head_state(checkpoint, recipe, plan, log_path, steps):
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
    parent = torch.load(plan["parent"], map_location="cpu", weights_only=True, mmap=True)
    assert sha(plan["parent"]) == plan["parent_sha256"]
    cfg = state["config"]
    assert state["step"] == steps <= cfg["steps"] == recipe["steps"] == 1000
    assert cfg["raw_kernel_only"] is True and state["model_config"]["raw_kernel_reconstruction"]
    assert cfg["initialized_from"]["sha256"] == plan["parent_sha256"]
    assert cfg["source_sha256"] == plan["source_bundle_sha256"]
    for key, value in recipe.items():
        if key != "validation_protocol":
            assert cfg[key] == value, key
    assert (
        sha(cfg["validation_protocol"])
        == sha(recipe["validation_protocol"])
        == cfg["validation_protocol_sha256"]
    )
    assert len(state["model"]) == len(state["ema"]) == 93 and len(parent["ema"]) == 91
    assert state["model"].keys() == state["ema"].keys()
    assert len(state["optimizer"]["state"]) == 2
    assert {int(v["step"]) for v in state["optimizer"]["state"].values()} == {steps}
    assert all(torch.isfinite(v).all() for k in ["model", "ema"] for v in state[k].values())
    assert all(
        torch.isfinite(v).all()
        for item in state["optimizer"]["state"].values()
        for v in item.values()
        if isinstance(v, torch.Tensor)
    )
    for name, value in parent["ema"].items():
        assert torch.equal(state["model"][name], value) and torch.equal(
            state["ema"][name], value
        ), name
    new = sorted(set(state["model"]) - set(parent["ema"]))
    assert new == [
        "pretrained_rgb.raw_kernel.coefficients.bias",
        "pretrained_rgb.raw_kernel.coefficients.weight",
    ]
    assert all(torch.count_nonzero(state["model"][name]) > 0 for name in new)
    assert all(key in state for key in ["python_rng", "torch_rng", "cuda_rng"])
    assert len(state["cuda_rng"]) == 1 and math.isfinite(state["best"])
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
    assert all(math.isfinite(v) for r in records for v in r.values() if isinstance(v, (int, float)))
    assert all(len(r["batch_sha256"]) == 64 for r in records)
    return {
        "checkpoint": checkpoint,
        "step": steps,
        "original_planned_updates": cfg["steps"],
        "source_bundle_sha256": cfg["source_sha256"],
        "source_bundle_independently_reconstructed": True,
        "all91_existing_model_and_EMA_tensors_bitwise_parent": True,
        "new_head_tensors": new,
        "model_tensors": 93,
        "EMA_tensors": 93,
        "AdamW_states": 2,
        "all_state_finite": True,
        "all_original_recipe_fields_exact_except_resolved_protocol": True,
        "four_manifest_hashes_and_snapshot_contents_exact": True,
        "complete_RNG_present": True,
        "training_log": {
            "path": str(log_path),
            "sha256": sha(log_path),
            "train_rows": len(records),
        },
        "learning_rates": [g["lr"] for g in state["optimizer"]["param_groups"]],
    }


def main(workflow, training_workflow, after_workflow, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    after = read(after_workflow)
    if (
        after["status"]
        != "completed-independent-primary-statistics-and-hue-awaiting-artifact-native-review"
    ):
        raise RuntimeError("RAW-head statistics/hue workflow has not completed")
    exited(after)
    after_plan = read(after["plan"])
    assert after_plan["previous_workflow"] == str(workflow)
    status, _training, _, plan = completed_primary(workflow, training_workflow)
    assert after["checkpoint"] == status["checkpoint"]
    assert after_plan["previous_owner"] == status["controller"]
    for path, digest in after_plan["guards"].items():
        assert sha(path) == digest
    cp = {**status["checkpoint"], "step": 1000, "arm": "head-only-warmup"}
    recipe = yaml.safe_load(Path(plan["recipe"]).read_text())
    result = {
        "status": "completed-independent-RAW-head-state-native-and-RGB16-integrity-audit",
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "training_workflow": str(training_workflow),
        "training_workflow_sha256": sha(training_workflow),
        "after_workflow": str(after_workflow),
        "after_workflow_sha256": sha(after_workflow),
        "boundary": audit_head_state(cp, recipe, plan, Path(plan["run"]) / "metrics.jsonl", 1000),
        **audit_panels(
            status["outputs"],
            [cp],
            old_registry=REPO / "docs/results/wide-flat-palette-full4k-review.json",
        ),
        "driver_sha256": sha(__file__),
        "CUDA_initialized": False,
        "scope": "State/native-preview/fullRGB16 integrity only. Selected CPU and hue arrays have separate independent Torch64 audits. Actual native visual review and quality interpretation remain required; no continuation or promotion.",
    }
    output = writable_path(output)
    assert not output.exists()
    output.mkdir(parents=True)
    (output / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"output": str(output), "PNG": 19, "F32": 23, "RGB16": 2}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["workflow", "training-workflow", "after-workflow", "output"]:
        p.add_argument("--" + name, required=True, type=Path)
    main(**vars(p.parse_args()))
