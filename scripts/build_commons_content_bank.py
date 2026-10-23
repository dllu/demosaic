"""Build a CPU-only source-retrieval bank from cached, held-out photographs.

These are content embeddings for overlap review, never restoration predictions
or an admission decision. Originals and all model-training inputs are read-only.
"""

import argparse
import json
import os
import shutil
import time
import traceback
from collections import Counter
from pathlib import Path

import numpy as np
import psutil
import torch
from audit_commons_dino_overlap import BATCH, MODEL, REVISION, image_tensor, ref
from profile_raw_kernel_inference import model_hash
from torch.nn import functional as F
from transformers import AutoModel

BACKBONE = "370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd"
HELDOUT = {"val", "test", "reserved"}
RECIPE = "bin8 uint16 linear-sRGB; center square; linear area192; sRGB; ImageNet mean/std; DINO pooler L2; CPU/F32/B8/two threads"


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def key(row):
    """Pixel identity and every preprocessing-relevant manifest field."""
    return (
        row["id"],
        row["cache_sha256"],
        tuple(row["shape"]),
        row["bin_factor"],
        row["dtype"],
        row["color_space"],
    )


def anchors(base, additional, *, workspace_cache=None):
    selected = [dict(row, pool="Commons-heldout") for row in base if row["split"] in HELDOUT]
    selected += [dict(row) for row in additional if row["pool"] in {"native150", "protected45"}]
    if len({(row["pool"], row["id"]) for row in selected}) != len(selected):
        raise ValueError("Ambiguous source identities in the retrieval bank")
    cache_root = (
        Path(workspace_cache).resolve()
        if workspace_cache is not None
        else Path(__file__).resolve().parents[1] / ".cache"
    )
    for row in selected:
        path = Path(row["cache"]).resolve()
        if not (path.is_relative_to("/mnt/external/demosaic") or path.is_relative_to(cache_root)):
            raise ValueError("Content review must use SSD caches, never original HDD paths")
        if (
            row["bin_factor"] != 8
            or row["dtype"] != "uint16"
            or row["color_space"] != "linear-sRGB"
        ):
            raise ValueError("Incompatible content input recipe")
        if len(row["shape"]) != 3 or row["shape"][2] != 3 or min(row["shape"][:2]) < 192:
            raise ValueError("Incompatible content input shape")
    return selected


def reused_locations(selected, pools):
    lookup = {}
    for number, source in enumerate(pools):
        for index, row in enumerate(source):
            identity = key(row)
            if identity in lookup:
                raise ValueError("Ambiguous reusable embedding provenance")
            lookup[identity] = (number, index)
    return [lookup.get(key(row)) for row in selected]


def resources(root, started=None, *, reserve_gib=548):
    if type(reserve_gib) is not int or reserve_gib < 256:
        raise ValueError("External disk reserve must be an integer of at least256GiB")
    if psutil.virtual_memory().available < 48 * 2**30:
        raise RuntimeError("Available RAM below48GiB content-review reserve")
    if shutil.disk_usage(root).free < reserve_gib * 2**30:
        raise RuntimeError(f"External free space below{reserve_gib}GiB content-review reserve")
    if started is not None and time.monotonic() - started > 3600:
        raise RuntimeError("One-hour content-bank bound reached")


def freeze(base, previous, additional, root, limit=0):
    repo = Path(__file__).resolve().parents[1]
    root = Path(root).resolve()
    if root.exists() or not root.is_relative_to("/mnt/external/demosaic"):
        raise ValueError("Use a fresh external demosaic root")
    resources(root.parent)
    if limit < 0:
        raise ValueError("Invalid engineering limit")
    sources, inputs, reusable = [], [ref(base), ref(previous), ref(additional)], []
    model_cache = repo / ".cache/huggingface/hub"
    snapshot = (
        model_cache
        / "models--facebook--dinov3-convnext-tiny-pretrain-lvd1689m"
        / "snapshots"
        / REVISION
    )
    inputs += [ref(snapshot / name) for name in ["config.json", "model.safetensors"]]
    for path, kind in [(previous, "embeddings"), (additional, "vectors")]:
        receipt = read(path)
        for field in ["plan", "input_rows", kind]:
            item = receipt[field]
            if ref(item["path"]) != item:
                raise ValueError("Changed reusable embedding artifact")
            inputs.append(item)
        plan = read(receipt["plan"]["path"])
        if plan["model"] != MODEL or plan["revision"] != REVISION:
            raise ValueError("Different reusable encoder")
        actual = receipt.get(
            "genuine_backbone_hash_unchanged", receipt.get("genuine_backbone_unchanged")
        )
        if actual != BACKBONE or receipt["CUDA_initialized"] or not receipt["Torch_RNG_unchanged"]:
            raise ValueError("Reusable encoder lacks the required identity/state proof")
        reusable.append({"rows": receipt["input_rows"], "vectors": receipt[kind]})
        sources.append(rows(receipt["input_rows"]["path"]))
    selected = anchors(rows(base), sources[1])
    locations = reused_locations(selected, sources)
    if limit:
        # Keep a genuine historical batch and both kinds of cached RAW renders,
        # followed by fresh held-out sources. This mode cannot claim full coverage.
        chosen = list(range(min(8, len(selected))))
        chosen += [
            next(i for i, row in enumerate(selected) if row["pool"] == pool)
            for pool in ["native150", "protected45"]
        ]
        chosen += [i for i, item in enumerate(locations) if item is None][:limit]
        chosen = sorted(set(chosen))
        selected, locations = [selected[i] for i in chosen], [locations[i] for i in chosen]
    root.mkdir(parents=True)
    work = root / "work"
    files = list((repo / "src/demosaic").glob("*.py"))
    files += [
        repo / "scripts" / name
        for name in [
            Path(__file__).name,
            "audit_commons_dino_overlap.py",
            "profile_raw_kernel_inference.py",
        ]
    ]
    frozen = []
    for source in files:
        destination = work / source.relative_to(repo)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        frozen.append(ref(destination))
    input_rows = root / "input-rows.jsonl"
    input_rows.write_text("".join(json.dumps(row) + "\n" for row in selected))
    plan = {
        "root": str(root),
        "base": ref(base),
        "inputs": inputs,
        "source": frozen,
        "input_rows": ref(input_rows),
        "reusable": reusable,
        "locations": locations,
        "rows": len(selected),
        "fresh": locations.count(None),
        "pools": dict(Counter(row["pool"] for row in selected)),
        "engineering": bool(limit),
        "model": MODEL,
        "model_cache": str(model_cache),
        "revision": REVISION,
        "backbone": BACKBONE,
        "recipe": RECIPE,
        "resources": {
            "CPU_threads": 2,
            "batch": 8,
            "nice_increment": 10,
            "CUDA": False,
            "available_RAM_GiB": 48,
            "external_reserve_GiB": 548,
            "active_seconds": 3600,
        },
        "scope": "Content-overlap anchor bank only; cached images, no original reads, restoration predictions, automatic exclusion or training admission. One central view does not prove scene independence.",
    }
    save(root / "plan.json", plan)
    return ref(root / "plan.json")


@torch.inference_mode()
def run(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("Hide CUDA explicitly for content review")
    plan, binding = read(path), ref(path)
    root = Path(plan["root"])
    claim = root / ".run-claimed"
    claim.touch(exist_ok=False)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    started = time.monotonic()
    os.nice(10)
    torch.set_num_threads(2)

    def status(value, **fields):
        save(
            root / "status.json",
            {
                "owner": owner,
                "plan": binding,
                "status": value,
                "updated_unix": time.time(),
                **fields,
            },
        )

    try:
        resources(root, started)
        for item in [*plan["inputs"], *plan["source"], plan["input_rows"]]:
            if ref(item["path"]) != item:
                raise ValueError("Frozen content-bank input/source changed")
        if ref(__file__) not in plan["source"]:
            raise ValueError("Execute the frozen content-bank driver")
        selected = rows(plan["input_rows"]["path"])
        source_rows = [rows(item["rows"]["path"]) for item in plan["reusable"]]
        if reused_locations(selected, source_rows) != [
            None if loc is None else tuple(loc) for loc in plan["locations"]
        ]:
            raise ValueError("Reuse mapping changed")
        cached = [
            np.load(item["vectors"]["path"], mmap_mode="r", allow_pickle=False)
            for item in plan["reusable"]
        ]
        for array, records in zip(cached, source_rows, strict=True):
            if array.dtype != np.float32 or array.shape != (len(records), 768):
                raise ValueError("Invalid reusable vector schema")
        status("loading-genuine-frozen-DINO-CPU-for-source-review")
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

        def encode(records):
            values = torch.stack([image_tensor(row) for row in records])
            output = model(pixel_values=(values - mean) / std).pooler_output.float()
            assert (
                output.shape == (len(records), 768)
                and torch.isfinite(output).all()
                and (output.norm(dim=1) > 1e-8).all()
            )
            return F.normalize(output, dim=1).numpy()

        # Replay the exact original first batch of both sources. Their original
        # B8 context is important: do not claim bitwise B1/B8 equivalence.
        for records, array in zip(source_rows, cached, strict=True):
            resources(root, started)
            assert np.array_equal(encode(records[:BATCH]), array[:BATCH]), (
                "Original B8 embedding replay differs"
            )
        vectors = np.lib.format.open_memmap(
            root / "unit-vectors-f32.npy", mode="w+", dtype=np.float32, shape=(len(selected), 768)
        )
        reused = 0
        fresh = []
        for index, location in enumerate(plan["locations"]):
            if location is None:
                fresh.append(index)
            else:
                # Read/verify the actual selected cached pixels, including
                # headers, even when the neural feature is reused.
                row = selected[index]
                assert ref(row["cache"])["sha256"] == row["cache_sha256"]
                pixels = np.load(row["cache"], mmap_mode="r", allow_pickle=False)
                assert pixels.dtype == np.uint16 and list(pixels.shape) == row["shape"]
                vectors[index] = cached[location[0]][location[1]]
                reused += 1
                if reused % 128 == 0:
                    resources(root, started)
        for first in range(0, len(fresh), BATCH):
            resources(root, started)
            indices = fresh[first : first + BATCH]
            batch = [selected[i] for i in indices]
            output = encode(batch)
            if first == 0:
                assert np.array_equal(output, encode(batch)), "Fresh B8 repeat differs"
            vectors[indices] = output
            if first % 128 == 0 or first + len(indices) == len(fresh):
                vectors.flush()
                status(
                    "encoding-heldout-content-anchors-CPU-only",
                    fresh_completed=first + len(indices),
                    fresh_total=len(fresh),
                    reused=reused,
                )
        vectors.flush()
        assert (
            np.isfinite(vectors).all() and np.max(abs(np.linalg.norm(vectors, axis=1) - 1)) < 2e-6
        )
        assert (
            model_hash(model) == BACKBONE
            and torch.equal(rng, torch.get_rng_state())
            and not torch.cuda.is_initialized()
        )
        for item in [*plan["inputs"], *plan["source"], plan["input_rows"], binding]:
            assert ref(item["path"]) == item
        result = {
            "status": "completed-source-content-anchor-bank-no-training-admission",
            "plan": binding,
            "input_rows": plan["input_rows"],
            "vectors": ref(root / "unit-vectors-f32.npy"),
            "rows": len(selected),
            "fresh": len(fresh),
            "reused": reused,
            "pools": plan["pools"],
            "engineering": plan["engineering"],
            "original_two_B8_replays_bitwise": True,
            "first_fresh_batch_repeat_bitwise": True,
            "all_selected_pixel_hashes_checked": True,
            "backbone_unchanged": BACKBONE,
            "Torch_RNG_unchanged": True,
            "CUDA_initialized": False,
            "elapsed_seconds": time.monotonic() - started,
            "recipe": RECIPE,
            "training_admission": False,
        }
        save(root / "receipt.json", result)
        status(result["status"], receipt=ref(root / "receipt.json"))
        print(json.dumps(ref(root / "receipt.json")), flush=True)
    except BaseException:
        status("failed-content-anchor-bank-no-automatic-retry", traceback=traceback.format_exc())
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("freeze")
    for name in ["base", "previous", "additional", "root"]:
        prepare.add_argument("--" + name, type=Path, required=True)
    prepare.add_argument("--engineering-fresh", type=int, default=0)
    execute = sub.add_parser("run")
    execute.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        print(
            json.dumps(
                freeze(args.base, args.previous, args.additional, args.root, args.engineering_fresh)
            )
        )
    else:
        run(args.plan)
