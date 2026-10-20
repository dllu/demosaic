"""Isolated CPU check of batching physical operations for scalar noise priors.

Generate two guarded edits of the actual restoration forward in memory. The
installed model, frozen training and queued review sources are never changed.
"""

import argparse
import ast
import copy
import hashlib
import inspect
import json
import math
import os
import shutil
import textwrap
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import read, ref, save

import demosaic.pretrained_rgb as rgb_module
from demosaic.cfa import PATTERNS, color_indices
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path
from demosaic.vst import GeneralizedAnscombe

REPO = Path(__file__).resolve().parents[1]
PARENT = Path("/mnt/external/demosaic/models/dino-convnext-wide-long-control-b16-v63-step20000.pt")
PARENT_SHA = "ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5"
SOURCE_SHA = "6c08681bedf20863eef5106703a70376548f6faceb1b29f60366444c817fc8ae"
GFX = (0.0014635775921166604, 0.0000010715704128646712)


def candidate_functions():
    """Keep the original multi-profile branches verbatim in the generated AST."""
    original = ast.parse(
        textwrap.dedent(inspect.getsource(rgb_module.PretrainedRgbDemosaic.forward))
    )
    candidate = copy.deepcopy(original)
    forward = candidate.body[0]
    stabilized = [
        n
        for n in forward.body
        if isinstance(n, ast.If) and ast.unparse(n.test) == "self.stabilized"
    ]
    assert len(stabilized) == 1
    body = stabilized[0].body
    starts = [
        i
        for i, n in enumerate(body)
        if isinstance(n, ast.Assign)
        and ast.unparse(n.targets[0]) == "(transformed, proxies, interpolated)"
    ]
    assert len(starts) == 1
    start = starts[0]
    original_front = copy.deepcopy(body[start:])
    assert len(original_front) == 4 and isinstance(original_front[1], ast.For)
    front = ast.parse("""
if len(self._noise_profiles) == 1:
    transform, scale, stochastic = self._noise_profiles[0]
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        packed = transform(packed) if transform is not None else (packed.double() / scale).float()
    variance = torch.ones_like(packed) if stochastic else torch.zeros_like(packed)
    base_rgb = malvar(packed, colors, None if transform is not None else wb)
""").body[0]
    front.orelse = copy.deepcopy(original_front)
    body[start:] = [front]
    inverses = [
        n
        for n in ast.walk(forward)
        if isinstance(n, ast.If) and ast.unparse(n.test) == "profiles is not None"
    ]
    assert len(inverses) == 1 and len(inverses[0].body) == 1
    original_inverse = copy.deepcopy(inverses[0].body)
    inverse = ast.parse("""
if len(self._noise_profiles) == 1:
    transform, scale, _ = profiles[0]
    output = transform.inverse(output) if transform is not None else (output.double() * scale).float()
""").body[0]
    inverse.orelse = copy.deepcopy(original_inverse)
    inverses[0].body = [inverse]
    # Verify only the two intended AST subtrees changed.
    restored = copy.deepcopy(candidate)
    restored.body[0].body[forward.body.index(stabilized[0])].body[start:] = original_front
    restored_inverse = next(
        n
        for n in ast.walk(restored)
        if isinstance(n, ast.If) and ast.unparse(n.test) == "profiles is not None"
    )
    restored_inverse.body = original_inverse
    assert ast.dump(restored, include_attributes=False) == ast.dump(
        original, include_attributes=False
    )
    namespace = dict(vars(rgb_module))
    exec(  # noqa: S102 -- compile only the guarded local source AST above.
        compile(ast.fix_missing_locations(candidate), "<uniform-physics-probe>", "exec"), namespace
    )
    result = {"forward": namespace["forward"]}
    definitions = {}
    for name, block, ending in [
        ("original_front", original_front, "return packed, variance, base_rgb"),
        ("candidate_front", [front], "return packed, variance, base_rgb"),
        ("original_inverse", original_inverse, "return output"),
        ("candidate_inverse", [inverse], "return output"),
    ]:
        function = ast.parse("""
def run(self, packed, colors, wb, output):
    profiles = self._noise_profiles * len(packed) if len(self._noise_profiles) == 1 else self._noise_profiles
""").body[0]
        function.body += copy.deepcopy(block) + ast.parse(ending).body
        module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
        exec(compile(module, "<uniform-physics-component>", "exec"), namespace)  # noqa: S102
        result[name] = namespace["run"]
        definitions[name] = ast.unparse(module)
    return result, ast.unparse(original), ast.unparse(candidate), definitions, namespace


def profile(shot, read):
    return (
        GeneralizedAnscombe(shot, read) if shot else None,
        math.sqrt(read) if read else 1.0,
        bool(shot or read),
    )


def canonical(value):
    return value.detach().reshape(-1).clone(memory_format=torch.contiguous_format).view(torch.uint8)


def comparison(original, candidate):
    assert original.shape == candidate.shape and original.dtype == candidate.dtype
    assert torch.isfinite(original).all() and torch.isfinite(candidate).all()
    delta = candidate.double() - original.double()
    return {
        "shape": list(original.shape),
        "values": original.numel(),
        "bytes_exact": torch.equal(canonical(original), canonical(candidate)),
        "max_abs": delta.abs().max().item(),
        "rms": delta.square().mean().sqrt().item(),
        "original_stride": list(original.stride()),
        "candidate_stride": list(candidate.stride()),
        "original_sha256": hashlib.sha256(canonical(original).numpy().tobytes()).hexdigest(),
        "candidate_sha256": hashlib.sha256(canonical(candidate).numpy().tobytes()).hexdigest(),
    }


@contextmanager
def calls(namespace):
    counts = Counter()
    malvar = rgb_module.malvar
    transform = GeneralizedAnscombe.forward
    inverse = GeneralizedAnscombe.inverse

    def counted(name, function):
        def run(*args, **kwargs):
            counts[name] += 1
            return function(*args, **kwargs)

        return run

    wrapped = counted("malvar", malvar)
    with (
        patch.object(rgb_module, "malvar", wrapped),
        patch.dict(namespace, {"malvar": wrapped}),
        patch.object(GeneralizedAnscombe, "forward", counted("GAT_forward", transform)),
        patch.object(GeneralizedAnscombe, "inverse", counted("GAT_inverse", inverse)),
    ):
        yield counts


def main(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(REPO).free > 64 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 500 * 2**30
    torch.set_num_threads(2)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = Path(rgb_module.__file__)
    assert ref(source)["sha256"] == SOURCE_SHA and ref(PARENT)["sha256"] == PARENT_SHA
    shutil.copytree(REPO / "src", root / "work/src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(__file__, root / Path(__file__).name)
    model_sources = [ref(p) for p in sorted((root / "work/src/demosaic").glob("*.py"))]
    assert len(model_sources) == 47
    functions, old, new, components, namespace = candidate_functions()
    (root / "original-forward.py").write_text(old + "\n")
    (root / "candidate-forward.py").write_text(new + "\n")
    save(root / "component-definitions.json", components)
    rng = torch.get_rng_state().clone()
    cases = []
    families = [
        ("poisson", [(0.001, 0)]),
        ("shot-read", [GFX]),
        ("read-dominated", [(1e-10, 0.0001)]),
        ("gaussian", [(0, 0.0004)]),
        ("ADC", [(0, 0)]),
        ("mixed-fallback", [(0.001, 0), GFX, (0, 0.0004), (0, 0)]),
        ("equal-list-fallback", [GFX] * 4),
    ]
    for name, priors in families:
        owner = SimpleNamespace(_noise_profiles=[profile(*p) for p in priors])
        for batch in [1, 4] if len(priors) == 1 else [4]:
            for height, width in [(8, 10), (9, 11)]:
                for layout in ["contiguous", "channels_last"]:
                    shape = (batch, 4, height, width)
                    packed = torch.linspace(-0.05, 1.1, math.prod(shape)).reshape(shape)
                    packed = packed.contiguous(
                        memory_format={
                            "contiguous": torch.contiguous_format,
                            "channels_last": torch.channels_last,
                        }[layout]
                    )
                    colors = torch.stack([color_indices(p) for p in PATTERNS])[:batch]
                    wb = torch.tensor([[2.0, 1, 1.5], [1, 1, 1], [1.6, 1, 2], [2.4, 1, 1.3]])[
                        :batch
                    ]
                    shape_out = (batch, 3, height * 2, width * 2)
                    inverse_input = torch.linspace(-2, 300, math.prod(shape_out)).reshape(shape_out)
                    arguments = owner, packed, colors, wb, inverse_input
                    with torch.inference_mode(), amp_context("cpu", dtype="float32"):
                        a = functions["original_front"](*arguments)
                        b = functions["candidate_front"](*arguments)
                        ai = functions["original_inverse"](*arguments)
                        bi = functions["candidate_inverse"](*arguments)
                    fields = [comparison(x, y) for x, y in zip((*a, ai), (*b, bi))]
                    cases.append(
                        {
                            "family": name,
                            "batch": batch,
                            "height": height,
                            "width": width,
                            "layout": layout,
                            "fields": fields,
                        }
                    )
    assert torch.equal(rng, torch.get_rng_state())
    save(root / "components.json", {"cases": cases})
    print(
        json.dumps(
            {
                "component_cases": len(cases),
                "nonexact_fields": sum(not f["bytes_exact"] for c in cases for f in c["fields"]),
            }
        ),
        flush=True,
    )
    fixture_path = Path(
        "/mnt/external/demosaic/benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json"
    )
    fixture = read(fixture_path)
    observation = fixture["serving_probes"][0]["observation"]
    assert ref(observation["path"]) == observation
    with np.load(observation["path"], allow_pickle=False) as archive:
        inputs = {
            k: torch.from_numpy(archive[k].copy())
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
    for key in ["packed", "variance"]:
        inputs[key] = inputs[key][..., 112:144, 108:148].contiguous()
    assert inputs["packed"].shape == (4, 4, 32, 40)
    model, checkpoint = load_checkpoint(PARENT, "cpu")
    del checkpoint
    model.eval()
    state = model_hash(model)
    rng = torch.get_rng_state().clone()
    results = []
    arguments = [inputs[k] for k in ["packed", "variance", "colors", "wb", "matrix"]]
    for name, shot, read_noise in [
        ("scalar-GFX", GFX[0], GFX[1]),
        ("equal-vector-fallback", [GFX[0]] * 4, [GFX[1]] * 4),
        ("scalar-ADC", 0.0, 0.0),
    ]:
        model.set_noise(shot, read_noise)
        parameter_ids = [id(p) for p in model.parameters()]
        with (
            torch.inference_mode(),
            amp_context("cpu", dtype="float32"),
            calls(namespace) as old_calls,
        ):
            original = model(*arguments)
        with (
            patch.object(rgb_module.PretrainedRgbDemosaic, "forward", functions["forward"]),
            torch.inference_mode(),
            amp_context("cpu", dtype="float32"),
            calls(namespace) as new_calls,
        ):
            candidate = model(*arguments)
        result = comparison(original, candidate)
        for label, array in [("original", original), ("candidate", candidate)]:
            np.save(root / f"{name}-{label}.npy", array.numpy(), allow_pickle=False)
        assert parameter_ids == [id(p) for p in model.parameters()]
        assert state == model_hash(model) and torch.equal(rng, torch.get_rng_state())
        results.append(
            {
                "name": name,
                "shot": shot,
                "read": read_noise,
                "comparison": result,
                "original_calls": dict(old_calls),
                "candidate_calls": dict(new_calls),
            }
        )
        print(json.dumps(results[-1]), flush=True)
    assert not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-isolated-uniform-physics-CPU-probe-no-speed-result",
        "driver": ref(__file__),
        "executed_driver_copy": ref(root / Path(__file__).name),
        "model_sources": model_sources,
        "helper_sources": [
            ref(REPO / "scripts" / name)
            for name in [
                "profile_raw_kernel_inference.py",
                "train_directional_bank_trial.py",
                "env.sh",
            ]
        ],
        "source": ref(source),
        "checkpoint": ref(PARENT),
        "original_forward": ref(root / "original-forward.py"),
        "candidate_forward": ref(root / "candidate-forward.py"),
        "component_definitions": ref(root / "component-definitions.json"),
        "components": ref(root / "components.json"),
        "component_cases": len(cases),
        "component_fields_exact": all(f["bytes_exact"] for c in cases for f in c["fields"]),
        "fixture": ref(fixture_path),
        "observation": observation,
        "relative_native_xywh": [216, 224, 80, 64],
        "model_sha256": state,
        "full_model": results,
        "full_model_fields_exact": all(r["comparison"]["bytes_exact"] for r in results),
        "saved_outputs": [ref(p) for p in sorted(root.glob("*.npy"))],
        "model_parameters_state_and_RNG_unchanged": True,
        "CUDA_initialized": False,
        "scope": "CPU FP32 engineering only; four cached GFX native64x80 subcontexts, no reference/GT scoring or visual-quality claim. Generated in-memory forward changes only scalar-profile front/inverse branches; multi-profile fallback AST stays exact. No production edit or new GPU work. Python call counts are not kernel counts, timings, peak-memory or a full-frame speed result. Batched MHC can choose different CUDA algorithms; GPU numerical validation remains required.",
    }
    save(root / "receipt.json", receipt)
    print(json.dumps(ref(root / "receipt.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
