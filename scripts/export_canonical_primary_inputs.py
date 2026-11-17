"""Freeze exact historic photo/camera inputs, without constructing a learned model."""

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic.cfa import color_indices, pack
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.suite import observation


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def checked(binding):
    path = Path(binding["path"])
    if ref(path)["sha256"] != binding["sha256"]:
        raise ValueError("Canonical input source changed")
    return path


def write(path, value):
    data = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    with Path(path).open("xb") as stream:
        stream.write(data)


def camera_batches(stage):
    manifest = checked(stage["manifest"])
    for case_index, case in enumerate(read(manifest)["cases"]):
        for start in range(0, len(case["crops"]), 4):
            crops = case["crops"][start : start + 4]
            yield manifest, case_index, case, crops


@torch.inference_mode()
def export(plan_path, action):
    plan = read(plan_path)
    assert ref(__file__) == plan["driver"]
    for binding in plan["inputs"]:
        checked(binding)
    for filename, digest in plan["frozen_files"].items():
        checked({"path": filename, "sha256": digest})
    root = Path(plan["root"])
    output = root / action
    output.mkdir()
    write(
        output / "owner.json",
        {"pid": os.getpid(), "create_time": psutil.Process().create_time(), "plan": ref(plan_path)},
    )
    os.sched_setaffinity(0, [0, 1])
    torch.set_num_threads(2)
    if psutil.virtual_memory().available < 52 * 2**30 or shutil.disk_usage(root).free < 256 * 2**30:
        raise RuntimeError("Canonical input RAM/internal disk admission unavailable")
    torch.cuda.set_per_process_memory_fraction(
        min(1, 2 * 2**30 / torch.cuda.get_device_properties(0).total_memory)
    )
    torch.cuda.reset_peak_memory_stats()
    forwards = []
    hook = torch.nn.modules.module.register_module_forward_pre_hook(
        lambda model, args: forwards.append(type(model).__name__)
    )
    protocol = plan["protocol"]
    adopted = {}
    if action == "full":
        admission = read(checked(plan["preflight"]))
        assert admission["all_input_witnesses_exact"] and admission["module_forwards"] == 0
        adopted = {(r["stage"], r["batch"]): r for r in admission["records"]}
    records = []
    began = time.monotonic()

    def retain(stage, index, batch, context, witness):
        if time.monotonic() - began > plan["maximum_seconds"]:
            raise TimeoutError("Canonical argument export deadline reached; no retry")
        if (
            psutil.virtual_memory().available < 32 * 2**30
            or shutil.disk_usage(root).free < 192 * 2**30
        ):
            raise RuntimeError("Canonical input runtime reserves unavailable")
        descriptions = {k: fingerprint(v) for k, v in batch.items()}
        for key, expected in witness["argument_fingerprints"].items():
            if descriptions[key]["sha256"] != expected:
                raise ValueError(f"Historic input differs: {stage}/{index}/{key}")
        if stage == "photo":
            for key, expected in witness["observation"]["input_fingerprints"].items():
                assert descriptions[key]["sha256"] == expected, (stage, index, key)
        path = output / f"{stage}-{index:05d}.npz"
        with path.open("xb") as stream:
            np.savez(stream, **{k: v.detach().cpu().contiguous().numpy() for k, v in batch.items()})
        path.chmod(0o444)
        record = {
            "stage": stage,
            "batch": index,
            "arrays": ref(path),
            "fingerprints": descriptions,
            "context": context,
            "historic_five_arguments_exact": True,
        }
        write(output / f"{stage}-{index:05d}.json", record)
        records.append(record)

    with ieee_fp32():
        witness = [
            json.loads(line)
            for line in checked(plan["stages"]["photo"]["input_witness"]).read_text().splitlines()
        ]
        assert len(witness) == 3108
        clean_name, clean = None, None
        for index, old in enumerate(witness):
            if action == "preflight" and index >= 28:
                break
            if ("photo", index) in adopted:
                records.append(adopted["photo", index])
                continue
            obs = old["observation"]
            if obs["clean_RGB"]["path"] != clean_name:
                path = checked(obs["clean_RGB"])
                clean = torch.from_numpy(np.load(path, allow_pickle=False)).cuda()
                clean_name = str(path)
            batch = observation(
                clean,
                obs["ids"],
                obs["condition"],
                obs["pattern"],
                protocol["white_balance"],
                protocol["camera_to_srgb"],
                obs["seed"],
            )
            retain(
                "photo",
                index,
                batch,
                {
                    "ids": obs["ids"],
                    "condition": obs["condition"],
                    "pattern": obs["pattern"],
                    "seed": obs["seed"],
                    "clean_RGB": obs["clean_RGB"],
                },
                old,
            )
            if (index + 1) % 28 == 0:
                print("photo", index + 1, "of3108", flush=True)
        for stage in ["known", "unseen"]:
            witnesses = [
                json.loads(line)
                for line in checked(plan["stages"][stage]["input_witness"]).read_text().splitlines()
            ]
            for index, (manifest, case_index, case, crops) in enumerate(
                camera_batches(plan["stages"][stage])
            ):
                if action == "preflight" and index >= 1:
                    break
                if (stage, index) in adopted:
                    records.append(adopted[stage, index])
                    continue
                arrays = []
                for crop in crops:
                    path = checked(
                        {"path": str(manifest.parent / crop["path"]), "sha256": crop["sha256"]}
                    )
                    with np.load(path, allow_pickle=False) as values:
                        arrays.append(
                            {
                                k: values[k]
                                for k in ["raw", "reference_rgb", "sensor_reference", "sensor_mask"]
                            }
                        )
                data = {
                    k: torch.from_numpy(np.stack([a[k] for a in arrays])).cuda() for k in arrays[0]
                }
                packed = pack(data.pop("raw")[:, None])
                meta = case["metadata"]
                shot, read_noise = case["conditioning"]["shot"], case["conditioning"]["read"]
                batch = {
                    **data,
                    "packed": packed,
                    "variance": packed.clamp_min(0) * shot + read_noise,
                    "colors": color_indices(meta["pattern"], device="cuda")[None].expand(
                        len(crops), -1
                    ),
                    "wb": packed.new_tensor(meta["white_balance"])[None].expand(len(crops), -1),
                    "matrix": packed.new_tensor(meta["camera_to_srgb"])[None].expand(
                        len(crops), -1, -1
                    ),
                }
                old = witnesses[index]
                assert old["observation_context"]["pair_sha256"] == case["noisy"]["sha256"]
                assert [c["id"] for c in old["observation_context"]["crops"]] == [
                    c["id"] for c in crops
                ]
                retain(
                    stage,
                    index,
                    batch,
                    {
                        "ids": [c["id"] for c in crops],
                        "case_index": case_index,
                        "scene": case["scene"],
                        "raw_source": case["noisy"],
                        "crop_xywh": [c["xywh"] for c in crops],
                        "noise": {"shot": shot, "read": read_noise},
                        "pattern": meta["pattern"],
                    },
                    old,
                )
    hook.remove()
    assert not forwards
    assert len(records) == (30 if action == "preflight" else 3162)
    write(
        output / "result.json",
        {
            "plan": ref(plan_path),
            "script": ref(__file__),
            "records": records,
            "all_input_witnesses_exact": True,
            "module_forwards": len(forwards),
            "seconds": time.monotonic() - began,
            "adopted_preflight_batches": len(adopted),
            "peak_CUDA_GiB": torch.cuda.max_memory_allocated() / 2**30,
            "scope": "Exact historic five-argument inputs and photo targets frozen for CPU model evaluation. No learned model construction, forward, optimizer or quality score. GPU only performs the historic physical observation/argument preparation, capped2GiB; existing training remains live and unchanged. Internal output storage, external input caches read-only. Preflight adopts no previous data; full export reuses all30 closed preflight batches without resimulation. Real references are independent, never exact RGB GT.",
        },
    )
    print(action, "all inputs exact", len(records), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("action", choices=["preflight", "full"])
    args = parser.parse_args()
    export(args.plan, args.action)
