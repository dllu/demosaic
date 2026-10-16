"""Export an inference-only precision variant without changing learned tensors.

The FP32 physical head/native skip is retained; the first hidden encoder stage
follows the active CNN autocast dtype. This is a numerical change requiring
quality validation, not an optimization silently applied to existing weights.
"""

import argparse
import hashlib
import json
from pathlib import Path

import torch

from demosaic.model import ModelConfig
from demosaic.safety import writable_path


def tensor_digest(weights):
    digest = hashlib.sha256()
    for name, tensor in sorted(weights.items()):
        header = {"name": name, "dtype": str(tensor.dtype), "shape": list(tensor.shape)}
        digest.update(json.dumps(header, sort_keys=True).encode() + b"\0")
        digest.update(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path, help="New output directory")
    args = parser.parse_args()
    with args.checkpoint.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != args.expected_sha256:
            raise ValueError("Parent checkpoint SHA256 changed")
        handle.seek(0)
        state = torch.load(handle, map_location="cpu", weights_only=True)
    config = ModelConfig.from_checkpoint(state["model_config"])
    if config.restoration_backbone != "pretrained-rgb" or config.rgb_hidden_autocast:
        raise ValueError("Expected an original pretrained-RGB precision policy")
    parent_config = config.to_dict()
    config.rgb_hidden_autocast = True
    selection = "ema" if "ema" in state else "model"
    weights = state[selection]
    weight_hash = tensor_digest(weights)
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "source"
    snapshot.mkdir()
    sources = {}
    for path in [Path(__file__), *sorted(Path("src/demosaic").glob("*.py"))]:
        payload = path.read_bytes()
        (snapshot / path.name).write_bytes(payload)
        sources[path.name] = hashlib.sha256(payload).hexdigest()
    provenance = {
        "operation": "Inference-only hidden-autocast export; zero training updates; identical learned tensors",
        "parent_checkpoint": str(args.checkpoint.resolve()),
        "parent_sha256": digest,
        "parent_step": state["step"],
        "weight_selection": selection,
        "learned_tensors_sha256": weight_hash,
        "parent_model_config": parent_config,
        "model_config": config.to_dict(),
        "source_sha256": sources,
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
    with path.open("rb") as handle:
        export_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    receipt = {**provenance, "export": str(path.resolve()), "export_sha256": export_hash, "identical_learned_tensors_verified_after_serialization": True}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
