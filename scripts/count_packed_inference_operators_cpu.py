"""Count executed learned operators without claiming GPU time or a speedup.

Spatially constant camera metadata occupies24/32 local-stem inputs and96/128
quarter-stem inputs. Count their nominal convolution MACs in the actual trained
graph before deciding whether a separate folding implementation is worthwhile.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch
from torch import nn

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def state_sha(model):
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        digest.update(name.encode() + value.detach().contiguous().numpy().tobytes())
    return digest.hexdigest()


def observe(model, inputs):
    records, handles = [], []

    def hook(name, module, args, output):
        inputs = args[0]
        item = {
            "name": name,
            "type": type(module).__name__,
            "input": list(inputs.shape),
            "output": list(output.shape),
            "output_elements": output.numel(),
            "output_tensor_bytes": output.numel() * output.element_size(),
        }
        if isinstance(module, nn.Conv2d):
            item.update(
                in_channels=module.in_channels,
                out_channels=module.out_channels,
                kernel_size=list(module.kernel_size),
                groups=module.groups,
                nominal_MACs=output.numel()
                * (module.in_channels // module.groups)
                * module.kernel_size[0]
                * module.kernel_size[1],
            )
        elif isinstance(module, nn.Linear):
            item["nominal_MACs"] = output.numel() * module.in_features
        records.append(item)

    for name, module in model.named_modules():
        if isinstance(module, (nn.Conv2d, nn.Linear, nn.LayerNorm)):
            handles.append(
                module.register_forward_hook(lambda m, a, o, name=name: hook(name, m, a, o))
            )
    try:
        with amp_context("cpu", dtype="float32"):
            predicted = model(*inputs)
    finally:
        for handle in handles:
            handle.remove()
    return predicted, records


@torch.inference_mode()
def main(checkpoints, inputs, output):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    os.nice(10)
    fixture = json.loads(Path(inputs).read_text())
    for path, digest in fixture["files"].items():
        assert sha(path) == digest, path
    source = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "source").mkdir()
    for path in [Path(__file__), *map(Path, source)]:
        (output / "source" / path.name).write_bytes(path.read_bytes())
    cases = [
        ("fixed-photo-native256", fixture["photos"][0]["observation"]),
        ("four-GFX-contexts-native512", fixture["serving_probes"][0]["observation"]),
    ]
    counts = []
    for checkpoint in checkpoints:
        checkpoint = ref(checkpoint)
        model, state = load_checkpoint(checkpoint["path"], "cpu")
        assert model.config.restoration_backbone == "packed-isotropic"
        model.eval()
        before, rng = state_sha(model), torch.get_rng_state().clone()
        metadata = {
            "checkpoint": checkpoint,
            "step": state["step"],
            "model_config": model.config.to_dict(),
        }
        del state
        for name, observation in cases:
            assert ref(observation["path"]) == observation
            with np.load(observation["path"], allow_pickle=False) as arrays:
                values = {k: torch.from_numpy(arrays[k].copy()) for k in arrays.files}
            condition = (
                fixture["photos"][0]["metadata"]["condition"]
                if "photo" in name
                else fixture["conditioning"]
            )
            model.set_noise(condition["shot"], condition["read"])
            args = [values[k] for k in ["packed", "variance", "colors", "wb", "matrix"]]
            with amp_context("cpu", dtype="float32"):
                original = model(*args)
            predicted, operations = observe(model, args)
            assert torch.equal(original, predicted) and torch.isfinite(predicted).all()
            assert state_sha(model) == before and torch.equal(torch.get_rng_state(), rng)
            stems = [
                op
                for op in operations
                if op["name"] in ["packed_isotropic.local_stem", "packed_isotropic.stem"]
            ]
            assert len(stems) == 2 and [op["in_channels"] for op in stems] == [32, 128]
            total = sum(op.get("nominal_MACs", 0) for op in operations)
            stem_macs = sum(op["nominal_MACs"] for op in stems)
            constant = stem_macs * 3 // 4
            case = {
                **metadata,
                "case": name,
                "observation": observation,
                "packed_shape": list(values["packed"].shape),
                "executed_modules": operations,
                "learned_Conv_Linear_nominal_MACs": total,
                "stem_nominal_MACs": stem_macs,
                "constant_metadata_stem_nominal_MACs": constant,
                "stem_fraction_of_counted_MACs": stem_macs / total,
                "constant_metadata_fraction_of_counted_MACs": constant / total,
                "hooked_unhooked_RGB_bitwise_equal": True,
                "model_and_RNG_unchanged": True,
            }
            counts.append(case)
            print(
                json.dumps(
                    {
                        k: case[k]
                        for k in [
                            "case",
                            "step",
                            "learned_Conv_Linear_nominal_MACs",
                            "constant_metadata_fraction_of_counted_MACs",
                        ]
                    }
                ),
                flush=True,
            )
    assert all(sha(path) == digest for path, digest in source.items())
    result = {
        "status": "completed-executed-packed-operator-CPU-census-no-speed-or-quality-result",
        "driver": ref(__file__),
        "inputs": ref(inputs),
        "source_files": source,
        "results": counts,
        "CUDA_initialized": torch.cuda.is_initialized(),
        "scope": "Actual completed checkpoint forwards on pre-existing frozen native256/B1 and native512/B4 inputs. Counts are learned Conv2d/Linear multiply-accumulates, not FLOPs, GPU attribution, wall time, traffic or peak memory. LayerNorm executed shapes/output sizes also retained. Functional physical filters/render, elementwise gates/residuals, data movement and allocation are excluded; output tensor bytes are not unique allocation counts. Potential75% stem MAC removal assumes constant metadata can be folded with exact padding/numerical behavior, which is not implemented or verified here. No training, source/recipe change, output correction, GPU work or optimization adoption.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoints", type=Path, nargs="+")
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.checkpoints, args.inputs, args.output)
