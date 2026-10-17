"""CPU execution/state checks for in-place compilation on an actual checkpoint.

The eager Dynamo backend tests graph capture and portable naming only. It does
not test Inductor, CUDA precision, speed, restoration quality or model promotion.
"""

import argparse
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import torch

from demosaic.inference import compile_restoration_blocks, load_checkpoint
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(items):
    value = hashlib.sha256()
    for name, tensor in items:
        value.update(name.encode())
        value.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return value.hexdigest()


@torch.inference_mode()
def main(checkpoint, output):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = Path(checkpoint).resolve()
    sources = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    source = Path(__file__).resolve()
    operator_sha = sha(source)
    model, state = load_checkpoint(checkpoint, "cpu")
    model.eval()
    assert model.config.restoration_backbone == "packed-isotropic"
    checkpoint_sha = state["loaded_sha256"]
    identities = {name: id(value) for name, value in model.named_parameters()}
    keys = tuple(model.state_dict())
    before = digest(model.state_dict().items())
    metadata = {
        "path": str(checkpoint),
        "sha256": checkpoint_sha,
        "step": state["step"],
        "model_config": model.config.to_dict(),
    }
    del state
    folder = Path("/mnt/external/demosaic/evaluation/two-fixed-examples-v43-none10k-cpu-v1")
    cases = []
    for index in range(2):
        path = folder / f"observation-{index}-cpu.npz"
        with np.load(path, allow_pickle=False) as values:
            batch = {key: torch.from_numpy(values[key].copy()) for key in values.files}
        args = [batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"]]
        cases.append((path, args, model(*args)))
    compile_restoration_blocks(model, backend="eager")
    blocks = [
        model.packed_isotropic.local_blocks,
        *model.packed_isotropic.groups,
        model.packed_isotropic.decoder,
    ]
    compiled_calls = [block._compiled_call_impl for block in blocks]
    assert all(callable(value) for value in compiled_calls)
    compile_restoration_blocks(model, backend="eager")
    assert compiled_calls == [block._compiled_call_impl for block in blocks]
    predictions = []
    for path, args, expected in cases:
        actual = model(*args)
        assert actual.dtype == torch.float32 and torch.isfinite(actual).all()
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
        predictions.append(
            {
                "observation": str(path),
                "observation_sha256": sha(path),
                "FP32_prediction_sha256": digest([("RGB", actual)]),
                "eager_Dynamo_prediction_bitwise_equal": True,
            }
        )
    assert keys == tuple(model.state_dict()) and not any("_orig_mod" in key for key in keys)
    assert identities == {name: id(value) for name, value in model.named_parameters()}
    assert digest(model.state_dict().items()) == before
    portable = output / "portable-restoration.pt"
    torch.save(
        {"model_config": model.config.to_dict(), "model": model.restoration_state_dict()}, portable
    )
    restored, _ = load_checkpoint(portable, "cpu")
    restored.eval()
    assert not hasattr(restored, "_restoration_compilation_backend")
    assert digest(restored.state_dict().items()) == before
    for _, args, expected in cases:
        torch.testing.assert_close(restored(*args), expected, rtol=0, atol=0)
    for path, expected in sources.items():
        assert sha(path) == expected, path
    assert sha(source) == operator_sha and sha(checkpoint) == checkpoint_sha
    result = {
        "status": "completed-actual-checkpoint-CPU-inplace-compilation-state-preflight",
        "scope": "Two fixed actual observations; CPU FP32, Dynamo eager backend only. "
        "Parameter identities, all state keys/tensor bytes and predictions remain exact; "
        "portable state reload is uncompiled and exact. No Inductor/CUDA, new quality score, "
        "performance, full-frame, promotion or active-recipe change.",
        "checkpoint": metadata,
        "source_files": sources,
        "operator_sha256": operator_sha,
        "torch_version": str(torch.__version__),
        "Module_compile_implementation": inspect.getsource(torch.nn.Module.compile),
        "compiled_components": len(blocks),
        "parameter_tensors": len(identities),
        "state_tensors": len(keys),
        "whole_model_state_sha256_unchanged": before,
        "backend": "eager",
        "idempotent": True,
        "predictions": predictions,
        "portable_checkpoint": {"path": str(portable), "sha256": sha(portable)},
        "portable_reload_is_uncompiled_and_bitwise_equal": True,
        "CUDA_initialized": torch.cuda.is_initialized(),
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "operator.py").write_bytes(source.read_bytes())
    print(
        json.dumps(
            {
                "receipt": str(output / "receipt.json"),
                "checkpoint": metadata,
                "compiled_components": len(blocks),
                "state_tensors": len(keys),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.checkpoint, args.output)
