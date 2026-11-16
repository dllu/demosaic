"""Exercise reporting-failure recovery without replaying parent/source work."""

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import prepare_shared_edge_cache as worker
import pytest
import torch
from paired_response_data import source_batch
from phase_admission_protocol import ref
from prepare_shared_edge_cache import cache
from profile_raw_kernel_inference import model_hash
from test_paired_response_data import config

from demosaic.prediction_archive import fingerprint


class FixtureParent(torch.nn.Module):
    def __init__(self, calls):
        super().__init__()
        self.context = torch.nn.Module()
        self.context.backbone = torch.nn.Identity()
        self.calls = calls

    def set_noise(self, shot, read):
        pass

    def forward(self, packed, variance, colors, wb, matrix):
        self.calls.append(fingerprint(packed.numpy())["sha256"])
        value = packed[:, :1].repeat_interleave(2, -2).repeat_interleave(2, -1).repeat(1, 3, 1, 1)
        return self.context.backbone(value)


def fixture_parent_values(arrays):
    a = np.repeat(np.repeat(arrays["packed"][:, :1], 2, axis=-2), 2, axis=-1)
    return np.repeat(a, 3, axis=1)


def test_full_cache_resumes_saved_prefix_after_reporting_exception(tmp_path, monkeypatch):
    torch.set_num_threads(2)
    root = tmp_path / "cache"
    root.mkdir()
    (root / "training-batches").mkdir()
    monkeypatch.setattr(worker, "ROOT", root)
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    cfg = config()
    cfg["domains"] = {"mixed": 1.0}
    cfg["first_ten_domains"] = ["mixed"] * 10
    rows = []
    for step in range(1, 157):
        arrays, metadata = source_batch(cfg, None, step)
        path = old_dir / f"{step}.npz"
        np.savez(path, **arrays)
        parent = path.with_suffix(".npy")
        base = fixture_parent_values(arrays)
        np.save(parent, base)
        rows.append(
            {
                "step": step,
                "arrays": ref(path),
                "metadata": metadata,
                "inputs": {k: fingerprint(v) for k, v in arrays.items()},
                "parent": ref(parent),
                "parent_values": fingerprint(base),
            }
        )
    for step in range(157, 1001):
        rows.append(dict(rows[0], step=step, metadata=dict(rows[0]["metadata"], step=step)))
    old_cache = old_dir / "cache.json"
    old_cache.write_text(json.dumps({"batches": rows}))
    old_units = old_dir / "units.json"
    old_units.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "step": r["step"],
                        "batch": r["arrays"],
                        "shape": [0, 1, 1, 1],
                        "candidate_units_FP32": [],
                    }
                    for r in rows
                ]
            }
        )
    )
    checkpoint = old_dir / "fixture-parent.pt"
    checkpoint.write_text("CPU workflow fixture; no learned checkpoint")
    calls = []
    expected_hash = model_hash(FixtureParent(calls))
    plan = {
        "cache": ref(old_cache),
        "old_pair_units": ref(old_units),
        "selected": [{"step": n, "ordinal": n - 1} for n in range(1, 157)],
        "parent_validation_step": 1,
        "parent": ref(checkpoint),
        "parent_module_hash": expected_hash,
        "DINO_module_hash": expected_hash,
        "sampling_library": {"path": "CPU-fixture-no-library"},
        "CUDA_quota_GiB": 12,
        "minimum_GiB": {"local": 0, "RAM": 0},
        "inputs": [],
        "frozen_files": {},
        "scope": "CPU fixture, not scientific model work",
    }
    (root / "plan-v1.json").write_text(json.dumps(plan))
    inspection = []
    for item in rows[:6]:
        _, record = worker.construct(plan, item, item["step"] - 1)
        inspection.append(record)
    path = root / "inspection-v1.json"
    path.write_text(json.dumps({"batches": inspection}))
    (root / "actual-viewing-v1.json").write_text(json.dumps({"inspection": ref(path)}))

    from demosaic import inference

    monkeypatch.setattr(
        inference,
        "load_checkpoint",
        lambda *a: (FixtureParent(calls), {"loaded_sha256": plan["parent"]["sha256"]}),
    )
    monkeypatch.setattr(torch.Tensor, "cuda", lambda self: self)
    monkeypatch.setattr(torch.ops, "load_library", lambda *a: None)
    monkeypatch.setattr(torch.cuda, "set_per_process_memory_fraction", lambda *a: None)
    monkeypatch.setattr(
        torch.cuda, "get_device_properties", lambda *a: SimpleNamespace(total_memory=128 * 2**30)
    )
    monkeypatch.setattr(torch.cuda, "get_rng_state", lambda *a: torch.zeros(1, dtype=torch.uint8))
    monkeypatch.setattr(torch.cuda, "set_rng_state", lambda *a: None)
    monkeypatch.setattr(torch.cuda, "max_memory_allocated", lambda: 0)
    real_suffix = Path.with_suffix
    armed = True

    def fail_reporting_once(path, suffix):
        nonlocal armed
        if path.name == "cache-progress-v1.json" and armed:
            armed = False
            raise OSError("injected reporting exception after saved parent")
        return real_suffix(path, suffix)

    monkeypatch.setattr(Path, "with_suffix", fail_reporting_once)
    with pytest.raises(OSError, match="reporting exception"):
        cache(plan, {"pid": 0, "created": 0})
    assert len(calls) == 2
    events = [json.loads(line) for line in (root / "cache-trace-v1.jsonl").read_text().splitlines()]
    assert [e["event"] for e in events] == ["before-parent", "completed"]
    completed = events[-1]["record"]
    frozen_parent = ref(completed["parent"]["path"])
    assert all(v == 2 for v in events[-1]["counts"].values())
    plan["resumption_journal"] = "resume2-cache-trace-v1.jsonl"
    plan["execution_plan_path"] = str(root / "resume-plan-v2.json")
    (root / "resume-plan-v2.json").write_text(json.dumps(plan))
    fresh_steps = []
    real_construct = worker.construct

    def observe_construct(plan, item, ordinal):
        fresh_steps.append(item["step"])
        return real_construct(plan, item, ordinal)

    monkeypatch.setattr(worker, "construct", observe_construct)
    cache(
        plan,
        {"pid": 0, "created": 0},
        resume={"records": {1: completed}, "counts": events[-1]["counts"]},
    )
    result = json.loads((root / "cache-result-v1.json").read_text())
    assert len(calls) == 157  # Original parity + 156 distinct new parents, no replay.
    assert calls.count(calls[0]) == calls.count(calls[1]) == 1
    assert fresh_steps == list(range(7, 157))
    assert ref(completed["parent"]["path"]) == frozen_parent
    assert result["batches"][0] == completed
    assert result["prefix_adopted_without_source_or_parent_replay"] == [1]
    assert result["parent_roots_in_this_segment"] == 155
    assert all(v == 157 for v in result["counts"].values())
    assert len(result["batches"]) == 1000 and result["adopted_legacy_batches"] == 844
