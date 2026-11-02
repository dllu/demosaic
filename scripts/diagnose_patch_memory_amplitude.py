"""Measure the trained V140 memory bottleneck on six existing branch contexts."""

import argparse
from pathlib import Path

import numpy as np
import torch
from train_directional_bank_trial import read, ref, save

from demosaic.raw_patch_memory_features import PatchMemoryRawGlobalFeatures


def diagnose(output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = read("docs/results/v140-standalone-quality-v1.json")["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    source = Path(state["config"]["source_snapshot"])
    for name in (
        "raw_patch_memory_features.py",
        "raw_global_memory_features.py",
        "raw_global_conditioned_features.py",
        "raw_global_features.py",
    ):
        assert (Path("src/demosaic") / name).read_bytes() == (source / name).read_bytes()
    before_rng = torch.get_rng_state().clone()
    branch = PatchMemoryRawGlobalFeatures().eval()
    weights = {
        k.removeprefix("pretrained_rgb.raw_global."): v
        for k, v in state["ema"].items()
        if k.startswith("pretrained_rgb.raw_global.")
    }
    branch.load_state_dict(weights, strict=True)
    original = {k: v.clone() for k, v in branch.state_dict().items()}
    samples = read(
        ".cache/current-quality-20261023-v1/V137-trained-memory-mechanism-v1/plan-v1.json"
    )["samples"]
    assert len(samples) == 6
    rows = []
    for item in samples:
        binding = item["branch_inputs"]
        assert ref(binding["path"]) == binding
        with np.load(binding["path"], allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files}
        retained = {}

        def hook(name, before=False, storage=retained):
            def record(module, args, module_output=None):
                v = args[0] if before else module_output
                storage[name] = v.detach().numpy().copy()

            return record

        handles = []
        for name in ("embed", "patch_embed", "read_out", "write_out", "expand", "project"):
            module = getattr(branch, name)
            handles.append(module.register_forward_pre_hook(hook(name + "_input", True)))
            handles.append(module.register_forward_hook(hook(name + "_output")))
        with torch.inference_mode():
            value = branch(
                *(torch.from_numpy(arrays[k]) for k in ("packed", "variance", "colors", "span"))
            )
        assert torch.isfinite(value).all()
        for handle in handles:
            handle.remove()
        destination = output / (item["sample"]["id"] + "-activations.npz")
        np.savez(destination, **retained)
        stats = {}
        for name, value in retained.items():
            a = value.astype(np.float64)
            stats[name] = {
                "RMS": float(np.sqrt(np.mean(a * a))),
                "max_abs": float(np.max(np.abs(a))),
                "shape": list(a.shape),
            }
        rows.append(
            {
                "sample": item["sample"]["id"],
                "branch_inputs": binding,
                "activations": ref(destination),
                "statistics": stats,
            }
        )
    assert all(torch.equal(v, original[k]) for k, v in branch.state_dict().items())
    assert torch.equal(before_rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    save(
        output / "result-v1.json",
        {
            "status": "completed-V140-six-context-memory-amplitude-diagnostic",
            "checkpoint": checkpoint,
            "operator": ref(__file__),
            "rows": rows,
            "branch_forwards": 6,
            "full_model_forwards": 0,
            "DINO_forwards": 0,
            "VST_calls": 0,
            "target_reads": 0,
            "optimizer_updates": 0,
            "scope": "Six previously reconstructed CPU branch inputs, not asserted bitwise original GPU activations. "
            "CNN feature amplitudes only, not final RGB quality or a causal performance explanation.",
        },
    )
    for row in rows:
        s = row["statistics"]
        print(
            row["sample"],
            {
                k: s[k]["RMS"]
                for k in (
                    "embed_output",
                    "read_out_output",
                    "write_out_output",
                    "expand_input",
                    "project_output",
                )
            },
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    diagnose(p.parse_args().output)
