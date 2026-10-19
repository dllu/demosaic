"""Queue source-only DINO neighbors for completed new Commons caches."""

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
from build_commons_content_bank import BACKBONE, RECIPE, read, resources, rows, save
from PIL import Image, ImageDraw
from profile_raw_kernel_inference import model_hash
from torch.nn import functional as F
from transformers import AutoModel

SUCCESS = "prepared-and-screened-downloaded-quarantine-awaiting-independent-review"


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            abs(process.create_time() - owner["created"]) < 0.02
            and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def partitions(records):
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate new source identity")
    if any(r["split"] not in {"train", "val", "test"} for r in records):
        raise ValueError("Use the complete direct8x prepared population")
    return (
        [i for i, r in enumerate(records) if r["split"] == "train"],
        [i for i, r in enumerate(records) if r["split"] in {"val", "test"}],
    )


def nearest(query, database, identities, count=3):
    """Exhaustive FP64 normalized cosine, with deterministic full tie handling."""
    q = np.asarray(query, np.float64)
    d = np.asarray(database, np.float64)
    if q.ndim != 2 or d.ndim != 2 or q.shape[1] != d.shape[1] or len(d) != len(identities):
        raise ValueError("Invalid retrieval dimensions")
    qnorm, dnorm = np.linalg.norm(q, axis=1), np.linalg.norm(d, axis=1)
    if (
        not np.isfinite(q).all()
        or not np.isfinite(d).all()
        or (qnorm <= 0).any()
        or (dnorm <= 0).any()
    ):
        raise ValueError("Nonfinite or empty feature vector")
    scores = (q / qnorm[:, None]) @ (d / dnorm[:, None]).T
    result = []
    count = min(count, len(d))
    for score in scores:
        if not count:
            result.append([])
            continue
        cutoff = np.partition(score, len(score) - count)[len(score) - count]
        candidates = np.flatnonzero(score >= cutoff)
        ordered = sorted(candidates, key=lambda i: (-float(score[i]), identities[i]))[:count]
        result.append([(int(i), float(score[i])) for i in ordered])
    return result


def freeze(producer, bank, titles, root, engineering=False):
    repo = Path(__file__).resolve().parents[1]
    root = Path(root).resolve()
    if root.exists() or not root.is_relative_to("/mnt/external/demosaic"):
        raise ValueError("Use a fresh external demosaic retrieval root")
    resources(root.parent)
    production = read(producer)
    state = read(producer.parent / "status.json")
    receipt = read(bank)
    if receipt["status"] != "completed-source-content-anchor-bank-no-training-admission":
        raise ValueError("Complete the content anchor bank first")
    if production["engineering_only"] != engineering or receipt["engineering"] != engineering:
        raise ValueError("Do not mix full-production and engineering inputs")
    if receipt["recipe"] != RECIPE or receipt["backbone_unchanged"] != BACKBONE:
        raise ValueError("Incompatible content bank")
    inputs = [
        ref(producer),
        ref(bank),
        ref(titles),
        production["selection"],
        receipt["plan"],
        receipt["input_rows"],
        receipt["vectors"],
    ]
    for item in inputs:
        if ref(item["path"]) != item:
            raise ValueError("Changed retrieval input")
    bank_plan = read(receipt["plan"]["path"])
    inputs += [r for r in bank_plan["inputs"] if r["path"].startswith(bank_plan["model_cache"])]
    root.mkdir(parents=True)
    source = []
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
    for file in files:
        destination = root / "work" / file.relative_to(repo)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, destination)
        source.append(ref(destination))
    plan = {
        "root": str(root),
        "producer": ref(producer),
        "producer_owner": state["owner"],
        "bank": ref(bank),
        "titles": ref(titles),
        "inputs": inputs,
        "source": source,
        "engineering": engineering,
        "model_cache": bank_plan["model_cache"],
        "recipe": RECIPE,
        "contacts": "Top24 rank-one pairs per available anchor pool by descending cosine then source IDs, plus top24 old-heldout rank-one pairs from no-title-flag queries; preserve duplicates with explicit selection reason.",
        "scope": "All new train-hash queries versus complete prior Commons heldout bank, cached native/protected sources and all new val/test hashes. Exhaustive FP64 cosine top3 per pool. Source overlap retrieval only, no quality scores, automatic cutoff, source release or training admission. Central-view retrieval is incomplete scene recognition.",
        "queue_seconds": 25200,
        "resource_wait_seconds": 3600,
        "stable_resource_seconds": 30,
    }
    save(root / "plan.json", plan)
    return ref(root / "plan.json")


@torch.inference_mode()
def run(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("Hide CUDA explicitly")
    plan, binding = read(path), ref(path)
    root = Path(plan["root"])
    (root / ".run-claimed").touch(exist_ok=False)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    os.nice(10)
    torch.set_num_threads(2)

    def status(value, **extra):
        save(
            root / "status.json",
            {
                "owner": owner,
                "plan": binding,
                "status": value,
                "updated_unix": time.time(),
                **extra,
            },
        )

    def checked_inputs():
        for item in [*plan["inputs"], *plan["source"], binding]:
            if ref(item["path"]) != item:
                raise ValueError("Frozen retrieval input/source changed")
        if ref(__file__) not in plan["source"]:
            raise ValueError("Execute the frozen retrieval driver")

    try:
        checked_inputs()
        wait_start = time.monotonic()
        status("waiting-for-exact-new-cache-producer-exit")
        while alive(plan["producer_owner"]):
            if time.monotonic() - wait_start > plan["queue_seconds"]:
                raise RuntimeError("Source producer wait bound reached")
            time.sleep(15)
        producer_root = Path(plan["producer"]["path"]).parent
        terminal = read(producer_root / "status.json")
        if (
            terminal["owner"] != plan["producer_owner"]
            or terminal["plan"] != plan["producer"]
            or terminal["status"] != SUCCESS
        ):
            raise ValueError("Bound producer did not exit successfully")
        producer_receipt = terminal["receipt"]
        if ref(producer_receipt["path"]) != producer_receipt:
            raise ValueError("Changed source producer receipt")
        result = read(producer_receipt["path"])
        for item in [
            result[k]
            for k in ["cache_audit", "screening", "candidates", "selection", "original_integrity"]
        ]:
            if ref(item["path"]) != item:
                raise ValueError("Changed producer audit")
        audit = read(result["cache_audit"]["path"])
        total = read(plan["producer"]["path"])["selected_originals"]
        if (
            audit["prepared"] != {"4": total, "8": total}
            or any(audit["errors"].values())
            or audit["area_max_uint16_codes"] > 1
        ):
            raise ValueError("Producer did not verify all selected two-scale caches")
        manifest = producer_root / "work/outputs/prepared8/manifest.jsonl"
        records = rows(manifest)
        expected = {
            r["sha1_hex"] for r in read(read(plan["producer"]["path"])["selection"]["path"])
        }
        if len(records) != total or {r["id"] for r in records} != expected:
            raise ValueError("Incomplete new source population")
        for row in records:
            row["cache"] = str((manifest.parent / row["cache"]).resolve())
            if (
                not Path(row["cache"]).is_relative_to("/mnt/external/demosaic")
                or row["bin_factor"] != 8
                or row["dtype"] != "uint16"
                or row["color_space"] != "linear-sRGB"
            ):
                raise ValueError("Unexpected new source input recipe/storage")
        queries, reserved = partitions(records)
        bank = read(plan["bank"]["path"])
        reference_rows = rows(bank["input_rows"]["path"])
        if {r["id"] for r in reference_rows} & expected:
            raise ValueError("Arrival already exists in the bound anchor bank")
        resource_start, stable = time.monotonic(), None
        status("waiting-for-stable-content-retrieval-resources")
        while True:
            try:
                resources(root)
                stable = stable or time.monotonic()
                if time.monotonic() - stable >= plan["stable_resource_seconds"]:
                    break
            except RuntimeError:
                stable = None
            if time.monotonic() - resource_start > plan["resource_wait_seconds"]:
                raise RuntimeError("Content retrieval resource wait bound reached")
            time.sleep(5)
        started = time.monotonic()
        status("encoding-new-arrival-source-content-CPU-only", completed=0, total=total)
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

        def encode(batch):
            pixels = torch.stack([image_tensor(row) for row in batch])
            output = model(pixel_values=(pixels - mean) / std).pooler_output.float()
            assert (
                output.shape == (len(batch), 768)
                and torch.isfinite(output).all()
                and (output.norm(dim=1) > 1e-8).all()
            )
            return F.normalize(output, dim=1).numpy()

        vectors = np.lib.format.open_memmap(
            root / "new-unit-vectors-f32.npy",
            mode="w+",
            dtype=np.float32,
            shape=(len(records), 768),
        )
        for first in range(0, len(records), BATCH):
            resources(root, started)
            batch = records[first : first + BATCH]
            output = encode(batch)
            if first == 0:
                assert np.array_equal(output, encode(batch))
            vectors[first : first + len(batch)] = output
            if first % 128 == 0 or first + len(batch) == total:
                vectors.flush()
                status(
                    "encoding-new-arrival-source-content-CPU-only",
                    completed=first + len(batch),
                    total=total,
                )
        vectors.flush()
        old_vectors = np.load(bank["vectors"]["path"], allow_pickle=False)
        assert old_vectors.dtype == np.float32 and old_vectors.shape == (len(reference_rows), 768)
        reference_vectors = np.concatenate([old_vectors, vectors[reserved]], axis=0)
        reference_rows += [dict(records[i], pool="new-reserved") for i in reserved]
        for name, value in [
            ("new-input-rows.jsonl", records),
            ("reference-rows.jsonl", reference_rows),
        ]:
            (root / name).write_text("".join(json.dumps(row) + "\n" for row in value))
        title_decisions = {r["id"]: r["decision"] for r in read(plan["titles"]["path"])}
        if any(records[i]["id"] not in title_decisions for i in queries):
            raise ValueError("Missing preliminary title label")
        neighbors = []
        pools = sorted({r["pool"] for r in reference_rows})
        for pool in pools:
            indices = [i for i, r in enumerate(reference_rows) if r["pool"] == pool]
            database = reference_vectors[indices]
            identities = [reference_rows[i]["id"] for i in indices]
            for first in range(0, len(queries), 32):
                resources(root, started)
                local = queries[first : first + 32]
                found = nearest(vectors[local], database, identities)
                for qi, ranked in zip(local, found, strict=True):
                    for rank, (ri, cosine) in enumerate(ranked, 1):
                        index = indices[ri]
                        neighbors.append(
                            {
                                "query_index": qi,
                                "query_id": records[qi]["id"],
                                "reference_index": index,
                                "reference_id": reference_rows[index]["id"],
                                "pool": pool,
                                "rank": rank,
                                "cosine_F64": cosine,
                                "preliminary_title_decision": title_decisions[records[qi]["id"]],
                            }
                        )
            status("retrieving-exhaustive-F64-source-neighbors", pool=pool, saved=len(neighbors))
        save(root / "neighbors.json", neighbors)
        chosen = []
        order = lambda row: (-row["cosine_F64"], row["query_id"], row["reference_id"])
        for pool in pools:
            chosen += [
                dict(row, selection="top24-pool")
                for row in sorted(
                    (r for r in neighbors if r["pool"] == pool and r["rank"] == 1), key=order
                )[:24]
            ]
        chosen += [
            dict(row, selection="top24-old-heldout-no-title-flag")
            for row in sorted(
                (
                    r
                    for r in neighbors
                    if r["pool"] == "Commons-heldout"
                    and r["rank"] == 1
                    and r["preliminary_title_decision"] == "no-title-flag"
                ),
                key=order,
            )[:24]
        ]
        contacts = []
        for first in range(0, len(chosen), 12):
            resources(root, started)
            sheet = Image.new("RGB", (1200, 920), "#e8e8e8")
            draw = ImageDraw.Draw(sheet)
            for local, entry in enumerate(chosen[first : first + 12]):
                x, y = local % 3 * 400, local // 3 * 230
                for column, row in enumerate(
                    [records[entry["query_index"]], reference_rows[entry["reference_index"]]]
                ):
                    pixels = image_tensor(row).permute(1, 2, 0).numpy()
                    sheet.paste(
                        Image.fromarray(np.rint(pixels * 255).clip(0, 255).astype(np.uint8)),
                        (x + 4 + 200 * column, y + 22),
                    )
                draw.text(
                    (x + 3, y + 3),
                    f"{first + local:03d} {entry['pool']} {entry['cosine_F64']:.5f}",
                    fill="black",
                )
                draw.text(
                    (x + 3, y + 216),
                    f"{entry['query_id'][:9]} / {entry['reference_id'][:9]} {entry['preliminary_title_decision']}",
                    fill="black",
                )
            target = root / f"source-pairs-{first // 12:02d}.png"
            sheet.save(target)
            contacts.append(
                {"PNG": ref(target), "pair_indices": [first, min(first + 11, len(chosen) - 1)]}
            )
        save(root / "contact-pairs.json", chosen)
        checked_inputs()
        assert (
            model_hash(model) == BACKBONE
            and torch.equal(rng, torch.get_rng_state())
            and not torch.cuda.is_initialized()
        )
        assert (
            np.isfinite(vectors).all() and np.max(abs(np.linalg.norm(vectors, axis=1) - 1)) < 2e-6
        )
        result = {
            "status": "completed-source-content-neighbors-awaiting-actual-review-no-training-admission",
            "plan": binding,
            "producer_receipt": producer_receipt,
            "manifest": ref(manifest),
            "input_rows": ref(root / "new-input-rows.jsonl"),
            "reference_rows": ref(root / "reference-rows.jsonl"),
            "vectors": ref(root / "new-unit-vectors-f32.npy"),
            "neighbors": ref(root / "neighbors.json"),
            "contact_pairs": ref(root / "contact-pairs.json"),
            "contacts": contacts,
            "new_sources": total,
            "train_hash_queries": len(queries),
            "new_reserved_anchors": len(reserved),
            "anchor_pools": dict(Counter(r["pool"] for r in reference_rows)),
            "top3_records": len(neighbors),
            "contact_pairs_count": len(chosen),
            "engineering": plan["engineering"],
            "first_batch_repeat_bitwise": True,
            "backbone_unchanged": BACKBONE,
            "Torch_RNG_unchanged": True,
            "CUDA_initialized": False,
            "elapsed_seconds": time.monotonic() - started,
            "training_admission": False,
            "scope": plan["scope"],
        }
        save(root / "receipt.json", result)
        status(result["status"], receipt=ref(root / "receipt.json"))
        print(json.dumps(ref(root / "receipt.json")), flush=True)
    except BaseException:
        status("failed-content-retrieval-no-automatic-retry", traceback=traceback.format_exc())
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("freeze")
    for name in ["producer", "bank", "titles", "root"]:
        prepare.add_argument("--" + name, type=Path, required=True)
    prepare.add_argument("--engineering", action="store_true")
    execute = sub.add_parser("run")
    execute.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        print(
            json.dumps(freeze(args.producer, args.bank, args.titles, args.root, args.engineering))
        )
    else:
        run(args.plan)
