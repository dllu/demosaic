"""Verify a fresh, matched no-context / DINO-S / DINO-B comparison on CPU."""

import argparse
import hashlib
import json
from pathlib import Path

import torch
import yaml

from demosaic.cfa import PATTERNS, color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import initialize_rgb_prior
from demosaic.safety import writable_path


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def common_config(config):
    result = {k: v for k, v in config.items() if k not in ("run", "experiment_notes")}
    result["model"] = ModelConfig(**config["model"]).to_dict()
    for field in ("dino", "dino_model", "dino_revision"):
        result["model"].pop(field)
    return result


@torch.no_grad()
def preflight(config_paths, output):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    models, entries, lineages = [], [], []
    code = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    snapshot = output / "source"
    snapshot.mkdir()
    for name, payload in code.items():
        (snapshot / name).write_bytes(payload)
    for name in ("pyproject.toml", "uv.lock"):
        (snapshot / name).write_bytes(Path(name).read_bytes())
    (snapshot / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    configs = [yaml.safe_load(Path(p).read_text()) for p in config_paths]
    if len(configs) != 3 or not all(common_config(c) == common_config(configs[0]) for c in configs):
        raise ValueError("Expected three recipes differing only in DINO branch/backbone and run notes")
    if sum(c["model"]["dino"] for c in configs) != 2:
        raise ValueError("Expected two frozen DINO arms and one no-context control")
    for config_path, config in zip(config_paths, configs):
        torch.manual_seed(config["seed"])
        model = JointDemosaic(ModelConfig(**config["model"])).cpu().eval()
        lineages.append(
            initialize_rgb_prior(model, config["gaussian_initialization"], archive=output)
        )
        assert all(p.device.type == "cpu" for p in model.parameters())
        projection = model.pretrained_rgb.measurement_adapter
        assert torch.count_nonzero(projection.weight) == torch.count_nonzero(projection.bias) == 0
        backbone = None
        if model.context is not None:
            assert not model.config.dino_lora_rank
            assert torch.count_nonzero(model.context.gate) == 0
            assert all(not p.requires_grad for p in model.context.backbone.parameters())
            assert model.context.backbone.config._commit_hash == config["model"]["dino_revision"]
            backbone = {
                "repo": model.config.dino_model,
                "revision": model.config.dino_revision,
                "parameters": sum(p.numel() for p in model.context.backbone.parameters()),
                "hidden_size": model.context.backbone.config.hidden_size,
                "adapter_input_channels": model.context.adapter.in_channels,
            }
        models.append(model)
        entries.append(
            {
                "path": str(config_path),
                "sha256": digest(config_path),
                "config": config,
                "backbone": backbone,
                "parameters": sum(p.numel() for p in model.parameters()),
                "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
            }
        )
        (snapshot / Path(config_path).name).write_bytes(Path(config_path).read_bytes())
    states = [
        {k: v for k, v in m.state_dict().items() if not k.startswith("context.")}
        for m in models
    ]
    assert all(s.keys() == states[0].keys() for s in states)
    assert all(torch.equal(value, s[name]) for s in states[1:] for name, value in states[0].items())
    common_digest = hashlib.sha256()
    for name, value in sorted(states[0].items()):
        common_digest.update(
            json.dumps(
                {"name": name, "dtype": str(value.dtype), "shape": list(value.shape)},
                sort_keys=True,
            ).encode()
            + b"\0"
        )
        common_digest.update(value.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    wb = torch.tensor([[2.0, 1.0, 1.5]]).expand(4, -1)
    matrix = torch.tensor([[1.1, -0.08, -0.02], [-0.03, 1.06, -0.03], [-0.01, -0.1, 1.11]])
    matrix = matrix[None].expand(4, -1, -1)
    checks = []
    for height, width in [(16, 16), (24, 32)]:
        raw = torch.rand(4, 4, height, width, generator=torch.Generator().manual_seed(48)) * 0.3
        for shot, read in [(0.0, 0.0), (0.00002, 0.0000000016), (0.00256, 0.0000262144)]:
            variance = raw * shot + read
            for precision in ["float32", "bfloat16"]:
                with torch.autocast("cpu", enabled=precision != "float32", dtype=torch.bfloat16):
                    predictions = [
                        model.set_noise(shot, read)(raw, variance, colors, wb, matrix)
                        for model in models
                    ]
                assert all(p.dtype == torch.float32 and torch.isfinite(p).all() for p in predictions)
                assert all(torch.equal(predictions[0], p) for p in predictions[1:])
                checks.append(
                    {
                        "native_hw": [2 * height, 2 * width],
                        "shot": shot,
                        "read": read,
                        "compute_precision": precision,
                        "all_four_cfas_exact": True,
                    }
                )
    assert all(Path("src/demosaic", n).read_bytes() == value for n, value in code.items())
    result = {
        "status": "CPU genuine-weight initialization/forward preflight only; no GPU or trained quality claim",
        "configs": entries,
        "lineages": lineages,
        "common_state_tensors": len(states[0]),
        "common_state_sha256": common_digest.hexdigest(),
        "common_tensors_exact": True,
        "zero_measurement_and_context_gates": True,
        "original_foundation_parameters_frozen": True,
        "cpu_forward_checks": checks,
        "white_balance": wb[0].tolist(),
        "camera_matrix": matrix[0].tolist(),
        "torch": torch.__version__,
        "cuda_initialized": torch.cuda.is_initialized(),
        "source_files": {name: hashlib.sha256(value).hexdigest() for name, value in code.items()},
        "driver_sha256": digest(__file__),
        "limitation": "Three fresh Gaussian initializers, no inherited JDD/DINO history. Backbone width changes the context adapter width. GPU backward/memory and matched training/quality/convergence still require verification.",
    }
    assert not result["cuda_initialized"]
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({k: v for k, v in result.items() if k not in ("source_files", "configs", "lineages")}),
        flush=True,
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", nargs=3, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight(args.configs, args.output)
