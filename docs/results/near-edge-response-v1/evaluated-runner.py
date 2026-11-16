"""Freeze and run independent-noise near-edge response for retained head states."""

import argparse
import copy
import gc
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.checkpoints import load_torch, state_hash
from demosaic.experiments.cli import snapshot_environment
from demosaic.experiments.data.edge_response import CONDITION, edge_observation, scene_recipe
from demosaic.experiments.evaluation.edge_response import measure
from demosaic.experiments.evaluation.native import write_native
from demosaic.experiments.runtime import RuntimePolicy, exclusive_run, owner_identity
from demosaic.inference import load_checkpoint
from demosaic.models.compat import load_component
from demosaic.prediction_archive import fingerprint

REPO = Path(__file__).resolve().parents[1]


def prepare(output):
    root = output.absolute()
    root.mkdir(parents=True, exist_ok=False)
    original = read_json(REPO / ".cache/quality-20261108/V202-shared-edge-data-v2/plan-v1.json")
    control = read_json(
        REPO / ".cache/quality-20261108/V200-scale-supported-CFA-trial-v1/exports-v1.json"
    )
    trained = read_json(REPO / ".cache/experiments/shared-edge-review/result.json")
    methods = {
        f"V200-{state}": control["exports"][f"V200-scale-wave-{label}"]["export"]
        for state, label in [("raw", "raw"), ("ema", "EMA")]
    }
    methods.update({f"shared-{s}": b for s, b in trained["exports"].items()})
    cache = read_json(checked(original["cache"]))
    parity = cache["batches"][original["parent_validation_step"] - 1]
    work, sources = freeze_sources(REPO, root, [Path(__file__).name])
    plan = {
        "root": str(root),
        "work": str(work),
        "frozen_files": sources,
        "methods": methods,
        "parent": original["parent"],
        "library": original["sampling_library"],
        "parity": parity,
        "sources": [scene_recipe(i) for i in range(8)],
        "placements": ["near", "far"],
        "patterns": ["RGGB", "GRBG", "GBRG", "BGGR"],
        "repeats": 2,
        "gains": [0.0, 0.25, 0.5, 0.75, 1.0],
        "runtime": RuntimePolicy(cuda_quota_gib=24, minimum_ram_gib=32).to_dict(),
        "inputs": [
            original["parent"],
            original["sampling_library"],
            original["cache"],
            parity["arrays"],
            parity["parent"],
            *methods.values(),
            reference(REPO / ".cache/experiments/shared-edge-review/result.json"),
        ],
        "scope": "Eight held-out procedural sources, finite Gaussian wires, independent noise "
        "for zero/one/two-direction roles and two repeats. Same data across all methods. "
        "All four CFAs, near/far edges, nominal ISO6400 prior, zero optical blur. "
        "No training or protected imagery. Frozen common computation reused only after "
        "all193 anchor tensors match and actual full-forward delivery parities pass.",
    }
    verify_plan(plan)
    write_json(root / "plan.json", plan)
    return reference(root / "plan.json")


def save_numpy(path, value):
    with path.open("xb") as stream:
        np.save(stream, value, allow_pickle=False)
    return reference(path)


def status(root, stage, **fields):
    write_json(
        root / "progress.json", dict(stage=stage, owner=owner_identity(), **fields), replace=True
    )


def parent_cache(plan, policy):
    root = Path(plan["root"])
    parent, payload = load_checkpoint(str(checked(plan["parent"])), "cuda")
    assert payload["loaded_sha256"] == plan["parent"]["sha256"]
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before = state_hash(parent.state_dict())
    counts = {"parent": 0, "DINO": 0}
    for name, module in [("parent", parent), ("DINO", parent.context.backbone)]:
        module.register_forward_hook(
            lambda *_, name=name: counts.__setitem__(name, counts[name] + 1)
        )

    def predict(arrays, noise):
        policy.resources(root)
        parent.set_noise(noise["shot"], noise["read"])
        tensors = [
            torch.from_numpy(arrays[k]).cuda()
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        ]
        with torch.inference_mode():
            value = parent(*tensors).float().cpu().numpy()
        if value.shape != arrays["target"].shape or not np.isfinite(value).all():
            raise ValueError("Invalid cached parent")
        return value

    original = plan["parity"]
    with np.load(checked(original["arrays"]), allow_pickle=False) as archive:
        arrays = dict(archive)
    parity = predict(arrays, original["metadata"]["noise"])
    expected = np.load(checked(original["parent"]), allow_pickle=False)
    np.testing.assert_array_equal(parity.view(np.uint32), expected.view(np.uint32))
    write_json(
        root / "parent-parity.json",
        {
            "original": original["parent"],
            "bit_exact": True,
            "values": fingerprint(parity),
            "counts": dict(counts),
        },
    )
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    directory = root / "cache"
    directory.mkdir()
    rows = []
    for recipe in plan["sources"]:
        for placement in plan["placements"]:
            for pattern in plan["patterns"]:
                for repeat in range(plan["repeats"]):
                    arrays, metadata = edge_observation(recipe, placement, pattern, repeat)
                    index = len(rows)
                    path = directory / f"inputs-{index:04d}.npz"
                    with path.open("xb") as stream:
                        np.savez(stream, **arrays)
                    value = predict(arrays, CONDITION)
                    row = {
                        "index": index,
                        "arrays": reference(path),
                        "metadata": metadata,
                        "parent": save_numpy(directory / f"parent-{index:04d}.npy", value),
                        "parent_values": fingerprint(value),
                        "inputs": {k: fingerprint(v) for k, v in arrays.items()},
                    }
                    write_json(directory / f"row-{index:04d}.json", row)
                    rows.append(row)
                    status(
                        root,
                        "parent-cache",
                        batches=len(rows),
                        images=len(rows) * 3,
                        counts=dict(counts),
                    )
    assert before == state_hash(parent.state_dict())
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    write_json(
        root / "cache.json",
        {
            "rows": rows,
            "parent_counts": counts,
            "parent_weights_unchanged": True,
            "global_RNG_unchanged": True,
            "training_updates": 0,
        },
    )
    parent = None
    gc.collect()
    torch.cuda.empty_cache()
    return rows


def evaluate(plan, rows, policy):
    root = Path(plan["root"])
    payloads = {name: load_torch(binding) for name, binding in plan["methods"].items()}
    first = payloads["V200-raw"]["state_dict"]
    frozen = {k: v for k, v in first.items() if not k.startswith("cfa_readout.")}
    assert len(frozen) == 193
    for payload in payloads.values():
        candidate = {
            k: v for k, v in payload["state_dict"].items() if not k.startswith("cfa_readout.")
        }
        assert candidate.keys() == frozen.keys()
        assert all(torch.equal(v, candidate[k]) for k, v in frozen.items())
    torch.ops.load_library(str(checked(plan["library"])))
    core, _ = load_component(
        "scale-supported-cfa-wave", checked(plan["methods"]["V200-raw"]), device="cuda"
    )
    core.eval().requires_grad_(False)
    heads = {}
    for name, payload in payloads.items():
        head = copy.deepcopy(core.readout)
        head.load_state_dict(
            {
                k.removeprefix("cfa_readout."): v
                for k, v in payload["state_dict"].items()
                if k.startswith("cfa_readout.")
            },
            strict=True,
        )
        heads[name] = head.eval().requires_grad_(False)
    hashes = {name: state_hash(head.state_dict()) for name, head in heads.items()}
    anchor_hash = state_hash(core.anchor.state_dict())
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    native = root / "predictions"
    native.mkdir()
    scores, predictions, parity_channels = [], {}, 0
    with torch.inference_mode():
        for item in rows:
            policy.resources(root)
            with np.load(checked(item["arrays"]), allow_pickle=False) as archive:
                arrays = dict(archive)
            assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"]
            base = np.load(checked(item["parent"]), allow_pickle=False)
            args = [
                torch.from_numpy(arrays[k]).cuda() for k in ["packed", "variance", "colors", "wb"]
            ]
            base_tensor = torch.from_numpy(base).cuda()
            _, aux = core(base_tensor, *args, return_aux=True)
            assert aux["matching_evaluated"]
            anchor, sigma = aux["anchor_output"], aux["sigma"]
            values = {"V195-ema": anchor.float().cpu().numpy()}
            for name, head in heads.items():
                wave = head(aux["cfa_context"], aux["cfa_waves"], aux["cfa_evidence"]["bin_yx"])
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                value = torch.where(sigma > 0, anchor + wave, anchor)
                if item["index"] == 0:
                    core.readout = head
                    expected = core(base_tensor, *args)
                    assert torch.equal(value, expected), name
                    parity_channels += value.numel()
                values[name] = value.float().cpu().numpy()
            saved = {}
            for method, value in values.items():
                saved[method] = write_native(
                    native / f"{item['index']:04d}-{method}.json", value, baseline=item["parent"]
                )
                for gain in [0.0] if method == "V195-ema" else plan["gains"]:
                    delivered = values["V195-ema"].astype(np.float64) + gain * (
                        value.astype(np.float64) - values["V195-ema"].astype(np.float64)
                    )
                    scores.append(
                        dict(
                            index=item["index"],
                            source=item["metadata"]["recipe"]["source"],
                            placement=item["metadata"]["placement"],
                            pattern=item["metadata"]["pattern"],
                            repeat=item["metadata"]["repeat"],
                            method=method,
                            gain_scale=gain,
                            **measure(arrays, delivered),
                        )
                    )
            predictions[str(item["index"])] = saved
            write_json(native / f"{item['index']:04d}-bindings.json", saved)
            status(root, "head-evaluation", batches=item["index"] + 1, metric_rows=len(scores))
    assert hashes == {name: state_hash(head.state_dict()) for name, head in heads.items()}
    assert anchor_hash == state_hash(core.anchor.state_dict())
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    write_json(
        root / "scores.json",
        {
            "status": "completed-fresh-noise-edge-response-awaiting-analysis-and-native-viewing",
            "plan": reference(root / "plan.json"),
            "rows": scores,
            "native_predictions": predictions,
            "methods": plan["methods"],
            "anchor193_tensors_exact_across_methods": True,
            "full_forward_delivery_bit_exact_channels": parity_channels,
            "weights_unchanged": True,
            "global_RNG_unchanged": True,
            "new_source_images": 0,
            "training_updates": 0,
            "scope": "Metrics use exact GT only after inference. Each role/repeat has independent sensor noise. "
            "Gain sweep interpolates delivered final corrections relative to V195; no retraining. "
            "Eight procedural sources with all CFA/repeat views clustered by source in later analysis.",
        },
    )


def run(root):
    plan = read_json(root / "plan.json")
    verify_plan(plan)
    policy = RuntimePolicy(**plan["runtime"])
    with exclusive_run(root):
        try:
            policy.resources(root)
            policy.apply()
            rows = parent_cache(plan, policy)
            evaluate(plan, rows, policy)
            verify_plan(plan)
            status(root, "completed-numerical-review", scores=reference(root / "scores.json"))
        except BaseException as error:
            write_json(root / "failure.json", {"error": repr(error), "owner": owner_identity()})
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "launch", "run"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.root))
    elif args.command == "launch":
        root = args.root.absolute()
        plan = read_json(root / "plan.json")
        verify_plan(plan)
        with (root / "worker.log").open("xb") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(plan["work"]) / "scripts" / Path(__file__).name),
                    "run",
                    str(root),
                ],
                env=snapshot_environment(plan),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print({"pid": process.pid, "log": str(root / "worker.log")})
    else:
        run(args.root.absolute())
