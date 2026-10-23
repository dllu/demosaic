"""Reuse verified source embeddings to extend the complete held-out content bank."""

import argparse
import json
import os
import shutil
import time
from collections import Counter
from pathlib import Path

import numpy as np
import psutil
from audit_commons_dino_overlap import BATCH, MODEL, REVISION, image_tensor, ref
from build_commons_content_bank import (
    BACKBONE,
    RECIPE,
    anchors,
    key,
    read,
    resources,
    reused_locations,
    rows,
    save,
)


def population(previous, arrivals, *, workspace_cache=None):
    """Preserve every prior pool and every new holdout, including protected flags."""
    pools = {"Commons-heldout", "native150", "protected45"}
    if not previous or any(row.get("pool") not in pools for row in previous):
        raise ValueError("Unexpected previous anchor pool")
    if len({row["id"] for row in previous}) != len(previous):
        raise ValueError("Duplicate previous source identity")
    if len({row["id"] for row in arrivals}) != len(arrivals):
        raise ValueError("Duplicate arrival source identity")
    if any(row["split"] not in {"train", "val", "test"} for row in arrivals):
        raise ValueError("Use all original direct8x arrival hash buckets")
    if {row["id"] for row in previous} & {row["id"] for row in arrivals}:
        raise ValueError("Arrivals overlap the previous source bank")
    commons = [row for row in previous if row["pool"] == "Commons-heldout"]
    if any(row["split"] not in {"val", "test", "reserved"} for row in commons):
        raise ValueError("Training source in the previous heldout pool")
    if len(anchors(commons, previous, workspace_cache=workspace_cache)) != len(previous):
        raise ValueError("Incomplete previous pool coverage")
    additions = [row for row in arrivals if row["split"] in {"val", "test"}]
    selected = [dict(row) for row in previous] + anchors(
        additions, [], workspace_cache=workspace_cache
    )
    locations = reused_locations(selected, [previous, arrivals])
    if any(location is None for location in locations):
        raise ValueError("Missing verified embedding for an anchor")
    return selected, locations


def freeze(previous, arrivals, root, *, reserve_gib=548):
    repo = Path(__file__).resolve().parents[1]
    root = Path(root).resolve()
    if root.exists() or not root.is_relative_to("/mnt/external/demosaic"):
        raise ValueError("Use a fresh external demosaic bank root")
    resources(root.parent, reserve_gib=reserve_gib)
    old, new = read(previous), read(arrivals)
    if old["status"] != "completed-source-content-anchor-bank-no-training-admission":
        raise ValueError("Previous content bank is incomplete")
    if (
        new["status"]
        != "completed-source-content-neighbors-awaiting-actual-review-no-training-admission"
    ):
        raise ValueError("Arrival embedding computation is incomplete")
    inputs = [ref(previous), ref(arrivals)]
    for receipt in [old, new]:
        if (
            receipt["engineering"]
            or receipt["backbone_unchanged"] != BACKBONE
            or receipt["CUDA_initialized"]
            or not receipt["Torch_RNG_unchanged"]
        ):
            raise ValueError("Incompatible or unverified encoder provenance")
        for field in ["plan", "input_rows", "vectors"]:
            item = receipt[field]
            if ref(item["path"]) != item:
                raise ValueError("Changed source embedding artifact")
            inputs.append(item)
    old_plan, new_plan = read(old["plan"]["path"]), read(new["plan"]["path"])
    if any(recipe != RECIPE for recipe in [old["recipe"], old_plan["recipe"], new_plan["recipe"]]):
        raise ValueError("Incompatible source preprocessing")
    if old_plan["model"] != MODEL or old_plan["revision"] != REVISION:
        raise ValueError("Incompatible source encoder")
    if old_plan["model_cache"] != new_plan["model_cache"]:
        raise ValueError("Model cache provenance differs")
    source_rows = [rows(receipt["input_rows"]["path"]) for receipt in [old, new]]
    if len(source_rows[0]) != old["rows"] or len(source_rows[1]) != new["new_sources"]:
        raise ValueError("Source population differs from completed receipt")
    workspace_cache = str(repo / ".cache")
    selected, locations = population(*source_rows, workspace_cache=workspace_cache)
    if len(selected) - len(source_rows[0]) != new["new_reserved_anchors"]:
        raise ValueError("Missing original arrival holdout bucket")
    model_inputs = [r for r in old_plan["inputs"] if r["path"].startswith(old_plan["model_cache"])]
    if len(model_inputs) < 2:
        raise ValueError("Missing pinned model config/weights")
    inputs.extend(model_inputs)
    root.mkdir(parents=True)
    files = list((repo / "src/demosaic").glob("*.py"))
    files += [
        repo / "scripts" / name
        for name in [
            Path(__file__).name,
            "build_commons_content_bank.py",
            "audit_commons_dino_overlap.py",
            "profile_raw_kernel_inference.py",
        ]
    ]
    frozen = []
    for file in files:
        destination = root / "work" / file.relative_to(repo)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, destination)
        frozen.append(ref(destination))
    selected_path = root / "input-rows.jsonl"
    selected_path.write_text("".join(json.dumps(row) + "\n" for row in selected))
    plan = {
        "root": str(root),
        "inputs": inputs,
        "source": frozen,
        "previous": ref(previous),
        "arrivals": ref(arrivals),
        "input_rows": ref(selected_path),
        "locations": locations,
        "rows": len(selected),
        "pools": dict(Counter(row["pool"] for row in selected)),
        "model": MODEL,
        "revision": REVISION,
        "model_cache": old_plan["model_cache"],
        "workspace_cache": workspace_cache,
        "backbone": BACKBONE,
        "recipe": RECIPE,
        "reserve_gib": reserve_gib,
        "scope": "Complete previous heldout/native/protected bank plus every prior-arrival val/test hash, including protected flags. Every selected embedding is reused by exact pixel/recipe identity. Recheck source pixels and original B8 CPU encoder replays. No restoration inference, quality selection, automatic exclusion or training admission.",
    }
    save(root / "plan.json", plan)
    return ref(root / "plan.json")


def run(path):
    import torch
    from profile_raw_kernel_inference import model_hash
    from torch.nn import functional as F
    from transformers import AutoModel

    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("Hide CUDA for source-bank reuse")
    plan = read(path)
    root = Path(plan["root"])
    (root / ".run-claimed").touch(exist_ok=False)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    started = time.monotonic()
    os.nice(10)
    torch.set_num_threads(2)

    def status(value, **fields):
        save(
            root / "status.json",
            {
                "status": value,
                "owner": owner,
                "updated_unix": time.time(),
                "plan": ref(path),
                **fields,
            },
        )

    def unchanged():
        for item in [*plan["inputs"], *plan["source"], plan["input_rows"]]:
            if ref(item["path"]) != item:
                raise ValueError("Changed frozen bank input or source")

    try:
        resources(root, started, reserve_gib=plan["reserve_gib"])
        unchanged()
        assert ref(__file__) in plan["source"]
        receipts = [read(plan[name]["path"]) for name in ["previous", "arrivals"]]
        source_rows = [rows(r["input_rows"]["path"]) for r in receipts]
        selected, locations = population(*source_rows, workspace_cache=plan["workspace_cache"])
        assert selected == rows(plan["input_rows"]["path"])
        assert [list(x) for x in locations] == plan["locations"]
        arrays = [
            np.load(r["vectors"]["path"], mmap_mode="r", allow_pickle=False) for r in receipts
        ]
        for records, array in zip(source_rows, arrays, strict=True):
            assert array.dtype == np.float32 and array.shape == (len(records), 768)
        status("checking-complete-reused-anchor-pixels-and-vectors")
        vectors = np.lib.format.open_memmap(
            root / "unit-vectors-f32.npy", mode="w+", dtype=np.float32, shape=(len(selected), 768)
        )
        for i, (row, location) in enumerate(zip(selected, locations, strict=True)):
            if i % 128 == 0:
                resources(root, started, reserve_gib=plan["reserve_gib"])
                status(
                    "checking-complete-reused-anchor-pixels-and-vectors",
                    checked=i,
                    total=len(selected),
                )
            assert ref(row["cache"])["sha256"] == row["cache_sha256"]
            pixels = np.load(row["cache"], mmap_mode="r", allow_pickle=False)
            assert pixels.dtype == np.uint16 and list(pixels.shape) == row["shape"]
            source, index = location
            assert key(row) == key(source_rows[source][index])
            vectors[i] = arrays[source][index]
        vectors.flush()
        assert (
            np.isfinite(vectors).all() and np.max(abs(np.linalg.norm(vectors, axis=1) - 1)) < 2e-6
        )
        status("replaying-two-original-B8-encoder-inputs-CPU-only")
        model = (
            AutoModel.from_pretrained(
                MODEL, revision=REVISION, cache_dir=plan["model_cache"], local_files_only=True
            )
            .float()
            .eval()
            .requires_grad_(False)
        )
        assert model.config._commit_hash == REVISION and model_hash(model) == BACKBONE
        rng = torch.get_rng_state().clone()
        mean = torch.tensor([0.485, 0.456, 0.406])[None, :, None, None]
        std = torch.tensor([0.229, 0.224, 0.225])[None, :, None, None]
        with torch.inference_mode():
            for records, array in zip(source_rows, arrays, strict=True):
                values = torch.stack([image_tensor(row) for row in records[:BATCH]])
                encoded = F.normalize(
                    model(pixel_values=(values - mean) / std).pooler_output.float(), dim=1
                ).numpy()
                assert np.array_equal(encoded, array[:BATCH]), "B8 source embedding replay differs"
        assert model_hash(model) == BACKBONE and torch.equal(rng, torch.get_rng_state())
        assert not torch.cuda.is_initialized()
        unchanged()
        receipt = {
            "status": "completed-source-content-anchor-bank-no-training-admission",
            "plan": ref(path),
            "input_rows": plan["input_rows"],
            "vectors": ref(root / "unit-vectors-f32.npy"),
            "rows": len(selected),
            "fresh": 0,
            "reused": len(selected),
            "pools": plan["pools"],
            "engineering": False,
            "original_two_B8_replays_bitwise": True,
            "all_selected_pixel_hashes_checked": True,
            "all_selected_vectors_exact_to_completed_sources": True,
            "backbone_unchanged": BACKBONE,
            "Torch_RNG_unchanged": True,
            "CUDA_initialized": False,
            "elapsed_seconds": time.monotonic() - started,
            "recipe": RECIPE,
            "training_admission": False,
            "scope": plan["scope"],
        }
        save(root / "receipt.json", receipt)
        status(receipt["status"], receipt=ref(root / "receipt.json"))
    except BaseException as error:
        status("failed-reused-content-anchor-bank-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    command = sub.add_parser("freeze")
    for name in ["previous", "arrivals", "root"]:
        command.add_argument("--" + name, type=Path, required=True)
    command.add_argument("--reserve-gib", type=int, default=548)
    command = sub.add_parser("run")
    command.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.mode == "freeze":
        print(
            json.dumps(
                freeze(args.previous, args.arrivals, args.root, reserve_gib=args.reserve_gib)
            )
        )
    else:
        run(args.plan)
