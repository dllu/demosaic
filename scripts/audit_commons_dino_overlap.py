"""CPU-only content-neighbor screen of existing Commons development photographs.

This retrieves possible scene overlap, never restoration quality or an automatic
split change. No test, reserved camera capture or original JPEG/RAW is opened.
"""

import argparse
import hashlib
import json
import os
import shutil
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import psutil
import torch
from PIL import Image, ImageDraw
from profile_raw_kernel_inference import model_hash
from torch.nn import functional as F
from transformers import AutoModel

from demosaic.color import linear_to_srgb
from demosaic.safety import writable_path

MODEL = "facebook/dinov3-convnext-tiny-pretrain-lvd1689m"
REVISION = "10d30274b4d445111e2d5bf75ac93bbd94db274b"
EDGE = 192
BATCH = 8


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def inputs(args):
    train = sorted((r for r in rows(args.training) if r["split"] == "train"), key=lambda r: r["id"])
    queries = sorted(rows(args.queries), key=lambda r: r["id"])
    control = {r["id"] for r in rows(args.control_membership) if r["split"] == "train"}
    expanded = {r["id"] for r in rows(args.expanded_membership) if r["split"] == "train"}
    assert len(train) == len({r["id"] for r in train}) == 85048
    assert len(queries) == len({r["id"] for r in queries}) == 427
    assert len(control) == 40170 and len(expanded) == 66934
    assert control <= expanded <= {r["id"] for r in train}
    assert not ({r["id"] for r in train} & {r["id"] for r in queries})
    for row in train + queries:
        assert row["bin_factor"] == 8 and row["dtype"] == "uint16"
        assert row["color_space"] == "linear-sRGB"
        assert Path(row["cache"]).is_absolute()
        assert Path(row["cache"]).resolve().is_relative_to("/mnt/external")
        assert len(row["cache_sha256"]) == 64
    assert all(r["split"] == "val" for r in queries)
    return (
        train,
        queries,
        {
            "control40170": control,
            "expanded66934": expanded,
            "latest85048": {r["id"] for r in train},
        },
    )


def image_tensor(row):
    path = Path(row["cache"])
    assert sha(path) == row["cache_sha256"], row["id"]
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    assert array.dtype == np.uint16 and list(array.shape) == row["shape"]
    h, w, _ = array.shape
    side = min(h, w)
    assert side >= EDGE
    y, x = (h - side) // 2, (w - side) // 2
    rgb = (
        torch.from_numpy(array[y : y + side, x : x + side].copy()).permute(2, 0, 1).float() / 65535
    )
    rgb = F.interpolate(rgb[None], size=(EDGE, EDGE), mode="area")[0]
    return linear_to_srgb(rgb).clamp(0, 1)


def update(output, info, **extra):
    info.update(updated_UTC=datetime.now(UTC).isoformat(), **extra)
    path = output / "workflow.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(info, indent=2) + "\n")
    temporary.replace(path)


def resources(output, started):
    assert psutil.virtual_memory().available / 2**30 > 24, "Available shared memory below24GiB"
    assert shutil.disk_usage(output).free > 512 * 2**30, "SSD reserve below512GiB"
    assert time.monotonic() - started < 8 * 3600, "Eight-hour bound reached"


def neighbors(embeddings, train, queries, cohorts):
    n = len(queries)
    database = torch.from_numpy(embeddings[n:])
    membership = {
        name: np.array([i for i, r in enumerate(train) if r["id"] in ids], dtype=np.int64)
        for name, ids in cohorts.items()
    }
    output = []
    for first in range(0, n, 16):
        scores = (torch.from_numpy(embeddings[first : min(first + 16, n)]) @ database.T).numpy()
        for position, score in enumerate(scores):
            query_index = first + position
            q = embeddings[query_index].astype(np.float64)
            for cohort, indices in membership.items():
                values = score[indices]
                # Approximate F32 retrieval, then independent F64 cosine on16
                # candidates; this is not an exact all-F64 nearest-neighbor claim.
                best = indices[np.argpartition(-values, 15)[:16]]
                candidates = []
                for index in best:
                    t = embeddings[n + int(index)].astype(np.float64)
                    cosine = float(np.dot(q, t) / (np.linalg.norm(q) * np.linalg.norm(t)))
                    candidates.append((cosine, train[int(index)]["id"], int(index)))
                for rank, (cosine, _, index) in enumerate(
                    sorted(candidates, key=lambda v: (-v[0], v[1]))[:3], 1
                ):
                    output.append(
                        {
                            "query_index": query_index,
                            "train_index": index,
                            "query_id": queries[query_index]["id"],
                            "train_id": train[index]["id"],
                            "cohort": cohort,
                            "rank": rank,
                            "cosine_F64": cosine,
                        }
                    )
    assert len(output) == len(queries) * 3 * len(cohorts)
    return output


def contact_sheets(output, records, train, queries):
    pairs = {}
    for r in records:
        pairs.setdefault((r["query_id"], r["train_id"]), r)
    chosen = sorted(pairs.values(), key=lambda r: (-r["cosine_F64"], r["query_id"], r["train_id"]))[
        :24
    ]
    sheets = []
    for first in range(0, 24, 6):
        sheet = Image.new("RGB", (832, 720), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        for local, r in enumerate(chosen[first : first + 6]):
            x = (local % 2) * 416
            y = (local // 2) * 240
            for column, row in enumerate([queries[r["query_index"]], train[r["train_index"]]]):
                value = image_tensor(row)
                pixels = (
                    (value.permute(1, 2, 0).numpy() * 255).round().clip(0, 255).astype(np.uint8)
                )
                sheet.paste(Image.fromarray(pixels), (x + 8 + column * 200, y + 32))
                draw.text(
                    (x + 8 + column * 200, y + 16),
                    ("VAL " if column == 0 else "TRAIN ") + row["id"][:10],
                    fill="black",
                )
            draw.text((x + 8, y + 224), f"cos={r['cosine_F64']:.6f}", fill="black")
        path = output / f"nearest-content-{first // 6 + 1}.png"
        sheet.save(path)
        sheets.append(
            {
                **ref(path),
                "pairs": chosen[first : first + 6],
                "display": "192px center-square scene thumbnails; resized data-audit views, not restoration100% crops",
            }
        )
    return sheets


@torch.inference_mode()
def run(args, output, status):
    started = time.monotonic()
    resources(output, started)
    train, queries, cohorts = inputs(args)
    proof = read(args.backbone_proof)
    expected = {r["DINO_hash"] for r in proof["initial_weight_and_DINO_checks"]}
    assert len(expected) == 1
    helper = Path(__file__).with_name("profile_raw_kernel_inference.py")
    plan = {
        "created_UTC": datetime.now(UTC).isoformat(),
        "driver": ref(__file__),
        "hash_helper": ref(helper),
        "model": MODEL,
        "revision": REVISION,
        "genuine_backbone_proof": ref(args.backbone_proof),
        "input_manifests": {
            name: ref(getattr(args, name))
            for name in ["training", "queries", "control_membership", "expanded_membership"]
        },
        "coverage": {
            "training_images": 85048,
            "development_queries": 427,
            "cohort_sizes": {k: len(v) for k, v in cohorts.items()},
        },
        "preprocessing": "Linear uint16 bin8 cache; center-square crop, linear area192, "
        "sRGB transfer, ImageNet mean/std, normalized genuine DINO pooler vector.",
        "runtime": {
            "device": "CPU",
            "precision": "float32",
            "torch_threads": 2,
            "batch": BATCH,
            "process_nice_increment": 10,
            "max_elapsed_hours": 8,
            "min_available_GiB": 24,
            "min_SSD_free_GiB": 512,
        },
        "selection_before_embeddings": "All85048 training files vs427 existing development photos. "
        "Three neighbors per query/cohort; F32 retrieval then F64 rescoring of16 candidates. "
        "Review24 highest unique pairs without tuning a similarity threshold. No automatic "
        "split changes, exclusions, scene counts or clean-independence conclusion.",
        "scope": "One center view is an incomplete content screen; crops, rotations and different "
        "views can remain unmatched. Test caches and protected camera captures are never "
        "opened. No restored image, quality scoring, training, original decode or GPU.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    shutil.copyfile(__file__, output / "source.py")
    shutil.copyfile(helper, output / helper.name)
    update(output, status, status="loading-genuine-backbone-CPU-only")
    model = AutoModel.from_pretrained(MODEL, revision=REVISION).float().eval().requires_grad_(False)
    assert model.config._commit_hash == REVISION
    before = model_hash(model)
    assert before in expected
    rng = torch.get_rng_state().clone()
    mean = torch.tensor([0.485, 0.456, 0.406])[None, :, None, None]
    std = torch.tensor([0.229, 0.224, 0.225])[None, :, None, None]

    def encode(values):
        vector = model(pixel_values=(values - mean) / std).pooler_output.float()
        assert vector.shape == (len(values), 768) and torch.isfinite(vector).all()
        assert (vector.norm(dim=1) > 1e-8).all()
        return F.normalize(vector, dim=1)

    sample_rows = queries[:8] + train[:24]
    timer = time.monotonic()
    sample = torch.stack([image_tensor(r) for r in sample_rows])
    batches = torch.cat([encode(batch) for batch in sample.split(BATCH)])
    single = torch.cat([encode(batch) for batch in sample.split(1)])
    repeated = encode(sample[:BATCH])
    assert torch.equal(repeated, batches[:BATCH])
    delta = float((single - batches).abs().max())
    assert delta < 5e-5
    assert float((single * batches).sum(1).min()) > 0.999999
    pilot = {
        "status": "passed-genuine-CPU-batch-preprocessing-and-repeat-check",
        "rows": [
            {"id": r["id"], "cache": r["cache"], "cache_sha256": r["cache_sha256"]}
            for r in sample_rows
        ],
        "max_B1_vs_B8_component_difference": delta,
        "B8_exact_repeat": True,
        "genuine_backbone_hash": before,
        "seconds_including_32_B1_and_five_B8_forwards_and_preprocessing": time.monotonic() - timer,
        "CUDA_initialized": torch.cuda.is_initialized(),
    }
    preview = Image.new("RGB", (4 * EDGE, 4 * (EDGE + 20)), "#eeeeee")
    draw = ImageDraw.Draw(preview)
    for index, value in enumerate(sample[:16]):
        x, y = index % 4 * EDGE, index // 4 * (EDGE + 20)
        pixels = (value.permute(1, 2, 0).numpy() * 255).round().clip(0, 255).astype(np.uint8)
        preview.paste(Image.fromarray(pixels), (x, y + 20))
        draw.text((x + 2, y + 2), sample_rows[index]["id"][:12], fill="black")
    preview.save(output / "pilot-inputs.png")
    pilot["input_preview"] = ref(output / "pilot-inputs.png")
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    np.save(output / "pilot-unit-embeddings-f32.npy", batches.numpy(), allow_pickle=False)
    (output / "pilot.json").write_text(json.dumps(pilot, indent=2) + "\n")
    if args.pilot_only:
        assert model_hash(model) == before
        update(
            output,
            status,
            status="completed-pilot-only-no-full-extraction",
            pilot=ref(output / "pilot.json"),
        )
        return
    pilot_proof = read(args.pilot_proof)
    pilot_plan = read(Path(args.pilot_proof).parent / "plan.json")
    assert (
        pilot_proof["status"] == pilot["status"] and pilot_proof["genuine_backbone_hash"] == before
    )
    assert pilot_plan["driver"]["sha256"] == sha(__file__)
    assert pilot_plan["input_manifests"] == plan["input_manifests"]
    all_rows = queries + train
    with (output / "input-rows.jsonl").open("x") as stream:
        for r in all_rows:
            stream.write(json.dumps(r) + "\n")
    path = output / "unit-embeddings-f32.npy"
    embedding = np.lib.format.open_memmap(
        path, mode="w+", dtype=np.float32, shape=(len(all_rows), 768)
    )
    update(
        output,
        status,
        status="extracting-all85475-genuine-CPU-content-vectors",
        completed=0,
        total=len(all_rows),
    )
    inference_batches = 37
    for first in range(0, len(all_rows), BATCH):
        values = torch.stack([image_tensor(r) for r in all_rows[first : first + BATCH]])
        vector = encode(values).numpy()
        embedding[first : first + len(vector)] = vector
        inference_batches += 1
        completed = first + len(vector)
        if completed % 256 == 0 or completed == len(all_rows):
            embedding.flush()
            resources(output, started)
            update(
                output,
                status,
                status="extracting-all85475-genuine-CPU-content-vectors",
                completed=completed,
                total=len(all_rows),
                elapsed_seconds=time.monotonic() - started,
                actual_neural_batches=inference_batches,
            )
    embedding.flush()
    update(output, status, status="retrieving-three-cohort-content-neighbors-CPU-only")
    retrieved = neighbors(embedding, train, queries, cohorts)
    sheets = contact_sheets(output, retrieved, train, queries)
    assert model_hash(model) == before and torch.equal(rng, torch.get_rng_state())
    assert all(not p.requires_grad and p.grad is None for p in model.parameters())
    assert not torch.cuda.is_initialized()
    for record in plan["input_manifests"].values():
        assert sha(record["path"]) == record["sha256"]
    result = {
        "status": "completed-CPU-content-neighbor-screen-awaiting-independent-and-native-review",
        "plan": ref(output / "plan.json"),
        "input_rows": ref(output / "input-rows.jsonl"),
        "embeddings": ref(path),
        "genuine_backbone_hash_unchanged": before,
        "actual_neural_batches": inference_batches,
        "query_rows": 427,
        "training_rows": 85048,
        "neighbors": retrieved,
        "contact_sheets": sheets,
        "CUDA_initialized": False,
        "Torch_RNG_unchanged": True,
        "all_cache_hashes_verified_on_read": True,
        "elapsed_seconds": time.monotonic() - started,
        "limits": plan["scope"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    update(output, status, status=result["status"], result=ref(output / "result.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in [
        "training",
        "queries",
        "control-membership",
        "expanded-membership",
        "backbone-proof",
        "output",
    ]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--pilot-only", action="store_true")
    parser.add_argument("--pilot-proof", type=Path)
    args = parser.parse_args()
    assert args.pilot_only or args.pilot_proof is not None, (
        "Run/review a separate pilot before full extraction"
    )
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    os.nice(10)
    torch.set_num_threads(2)
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    status = {"owner": {"pid": os.getpid(), "created": psutil.Process().create_time()}}
    update(output, status, status="initializing-CPU-content-screen")
    try:
        run(args, output, status)
    except BaseException as error:
        update(
            output,
            status,
            status="failed-no-automatic-retry",
            error=str(error),
            traceback=traceback.format_exc(),
        )
        raise


if __name__ == "__main__":
    main()
