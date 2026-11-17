"""Audit the active long schedule's data and crop observations through step 30,000."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil
import yaml

from demosaic.experiments.artifacts import checked, read_json, reference, write_json

root = Path(__file__).resolve().parent
base = root.parent / "full-corpus-scaling-v3"
launch = base / "production-handoff-v7/01-scale-long100k-launch.json"
owner = read_json(launch)
process = psutil.Process(owner["pid"])
assert process.create_time() == owner["create_time"] and process.status() != psutil.STATUS_ZOMBIE
plan = read_json(checked(owner["production_plan"]))
initial = checked(plan["adopted_states"]["long100k"]).parent
resume = Path(plan["work"]) / "artifacts/train/long100k/phase-001001-100000"
fixed_record = resume.parent / "step020000-receipt.json"
config_file = resume.parent / "config.yaml"
config = yaml.safe_load(config_file.read_bytes())
config = config.get("train", config)
assert config["steps"] == 100_000 and config["batch_size"] == 16
log = base / "production-handoff-v7/01-scale-long100k.log"
checkpoints = []
for line in log.read_text().splitlines():
    if line.startswith('{"event": "checkpoint"'):
        row = json.loads(line)
        if row["step"] == 30_000:
            checkpoints.append(row)
assert any(r["phase"] == "complete" for r in checkpoints)

orders = root.parent / "full-corpus-scaling-v1/order100k/photo-epoch-order.json"
header = read_json(orders)
header_ref = reference(orders)
indices = np.load(
    checked({**header["order"], "path": str(orders.parent / header["order"]["path"])})
)
with checked(header["source_manifest"]).open() as source:
    ids = [r["id"] for line in source if (r := json.loads(line))["split"] == "train"]
assert len(ids) == len(set(ids)) == 90_778
ordinary, reviewed, domains, procedural = Counter(), Counter(), Counter(), Counter()
boxes = defaultdict(list)
first_epoch = None
observed_prefixes = []
conditioning = []
for directory, start, stop in ((initial, 1, 1000), (resume, 1001, 30000)):
    path = directory / "source-crop-observations.jsonl"
    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as data:
        for step in range(start, stop + 1):
            line = next(data)
            row = json.loads(line)
            digest.update(line)
            byte_count += len(line)
            assert row["step"] == step and row["global_draw_start"] == (step - 1) * 16
            expected_seed = hashlib.sha256(f"data:{config['seed']}:{step}".encode()).digest()
            assert row["data_RNG_seed"] == int.from_bytes(expected_seed[:8], "little") % (2**63)
            domain = row["domain"]
            domains[domain] += 1
            at = row["global_draw_start"]
            expected = indices[at : at + 16]
            if domain != "commons":
                assert not row["sources"] and np.all(expected == -1)
                continue
            for item, pos in zip(row["sources"], expected, strict=True):
                if item["kind"] == "photographic":
                    sid = item["source_id"]
                    if item["reviewed_roi_xywh"] is None:
                        assert pos >= 0 and ids[pos] == sid
                        assert item["photo_epoch_order_sha256"] == header_ref["sha256"]
                        ordinary[sid] += 1
                        assert item["cache_xywh"]
                        boxes[sid].append(item["cache_xywh"])
                        if first_epoch is None and len(ordinary) == 90_778:
                            first_epoch = step
                    else:
                        assert pos == -1 and item["reviewed_roi_xywh"]
                        reviewed[sid] += 1
                else:
                    assert pos == -1
                    procedural[item["kind"]] += 1
    observed_prefixes.append(
        {
            "path": str(path),
            "start_step": start,
            "stop_step": stop,
            "prefix_bytes": byte_count,
            "prefix_sha256": digest.hexdigest(),
        }
    )
    for step in range(start, stop + 1, 250):
        path = directory / f"conditions-{step:06d}-{step + 249:06d}.npz"
        with np.load(path) as chunk:
            np.testing.assert_array_equal(chunk["steps"], np.arange(step, step + 250))
            assert chunk["values"].shape == (250, 16, 14)
            assert chunk["domains"].shape == (250,) and np.isfinite(chunk["values"]).all()
        conditioning.append(reference(path))
assert first_epoch == 17_039 and len(conditioning) == 120
assert len(ordinary) == 90_778 and sum(domains.values()) == 30_000
assert (
    sum(ordinary.values()) + sum(reviewed.values()) + sum(procedural.values())
    == domains["commons"] * 16
)


def intersection_over_union(first, second):
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    area = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
    return area / (aw * ah + bw * bh - area)


pairs = [v for v in boxes.values() if len(v) == 2]
assert len(ordinary) == len(boxes) and max(ordinary.values()) == 2
overlap = np.array([intersection_over_union(a, b) for a, b in pairs])
facts = {
    "producer": reference(__file__),
    "training_plan": owner["production_plan"],
    "owner": reference(launch),
    "source_manifest": header["source_manifest"],
    "photo_order": header_ref,
    "source_log_prefixes": observed_prefixes,
    "conditioning_chunks": conditioning,
    "checkpoint_events_at_step_30000": checkpoints,
    "immutable_20000_resume_lineage": reference(fixed_record),
    "training_config": reference(config_file),
    "prefix_updates": 30_000,
    "target_slots": 480_000,
    "domain_updates": dict(domains),
    "ordinary_draws": sum(ordinary.values()),
    "ordinary_distinct": len(ordinary),
    "ordinary_visit_histogram": dict(Counter(ordinary.values())),
    "reviewed_draws": sum(reviewed.values()),
    "reviewed_distinct": len(reviewed),
    "procedural_slot_counts": dict(procedural),
    "first_complete_epoch_update": first_epoch,
    "unique_ordinary_source_cache_rectangles": sum(
        len({tuple(b) for b in v}) for v in boxes.values()
    ),
    "second_visit_changed_cache_rectangle": sum(a != b for a, b in pairs),
    "second_visit_disjoint_rectangle": int((overlap == 0).sum()),
    "second_visit_cache_rect_IoU_10_50_90": np.quantile(overlap, [0.1, 0.5, 0.9]).tolist(),
    "scope": "Closed observed prefix of the live 100k-horizon run. Saved checkpoint event observed;"
    " no immutable 30k weight binding in this receipt. Cache boxes describe pre-transform"
    " spatial sampling. Native/paired source identities are unlogged. No quality scoring.",
}
write_json(root / "result.json", facts)
print(
    {
        k: v
        for k, v in facts.items()
        if k.endswith(
            (
                "draws",
                "distinct",
                "histogram",
                "rectangle",
                "10_50_90",
                "updates",
                "slots",
                "rectangles",
            )
        )
    }
)
