"""Export an opt-in ADC-only policy with unchanged restoration weights."""

import argparse
import hashlib
import json
from pathlib import Path

import torch

from demosaic.model import ModelConfig
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def tensor_digest(weights):
    digest = hashlib.sha256()
    for name, tensor in sorted(weights.items()):
        header = {"name": name, "dtype": str(tensor.dtype), "shape": list(tensor.shape)}
        digest.update(json.dumps(header, sort_keys=True).encode() + b"\0")
        digest.update(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def export(checkpoint, output, expected_sha256):
    checkpoint = Path(checkpoint)
    if sha(checkpoint) != expected_sha256:
        raise ValueError("Parent checkpoint SHA256 changed")
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    config = ModelConfig.from_checkpoint(state["model_config"])
    if (
        config.restoration_backbone != "pretrained-rgb"
        or not config.variance_stabilization
        or not config.physical_fp32
        or config.adc_cfa_projection
    ):
        raise ValueError("Expected stabilized physical-FP32 RGB without ADC projection")
    parent_config = config.to_dict()
    config.adc_cfa_projection = True
    assert [k for k, v in config.to_dict().items() if v != parent_config[k]] == ["adc_cfa_projection"]
    selection = "ema" if "ema" in state else "model"
    weights = state[selection]
    weight_hash = tensor_digest(weights)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "source"
    snapshot.mkdir()
    sources = {}
    for path in [Path(__file__), *sorted(Path("src/demosaic").glob("*.py"))]:
        payload = path.read_bytes()
        (snapshot / path.name).write_bytes(payload)
        sources[path.name] = hashlib.sha256(payload).hexdigest()
    provenance = {
        "operation": "Opt-in ADC-only projection; zero training updates; identical learned tensors",
        "parent_checkpoint": str(checkpoint.resolve()),
        "parent_sha256": expected_sha256,
        "parent_step": state["step"],
        "weight_selection": selection,
        "learned_tensors_sha256": weight_hash,
        "parent_model_config": parent_config,
        "model_config": config.to_dict(),
        "source_sha256": sources,
        "conditioning": "Only explicit shot=read=0 profiles activate projection; every positive shot or read prior bypasses it. No target fitting or output clamp.",
    }
    exported = {
        "format_version": 1,
        "model_config": config.to_dict(),
        "model": weights,
        "step": state["step"],
        "config": {"run": str(output.resolve()), "inference_only": True},
        "inference_export": provenance,
    }
    path = output / "model.pt"
    torch.save(exported, path)
    loaded = torch.load(path, map_location="cpu", weights_only=True)
    assert tensor_digest(loaded["model"]) == weight_hash
    assert loaded["model_config"] == config.to_dict()
    receipt = {
        **provenance, "export": str(path.resolve()), "export_sha256": sha(path),
        "identical_learned_tensors_verified_after_serialization": True,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.checkpoint, args.output, args.expected_sha256)), flush=True)
