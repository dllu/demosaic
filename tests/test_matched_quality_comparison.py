"""Fair saved-output joins and native reporting must fail on mismatched evidence."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import queue_detail_data_comparison as queue
from audit_quality_archive import audit, binding
from compare_quality_archives import (
    analytic_groups,
    compare_stage,
    identity,
    metric_delta,
    normalize_row,
)
from compare_quality_crops import gfx_comparison, photo_comparison, triplet_pixels
from queue_detail_data_comparison import recipe_contrast

from demosaic.archive_metrics import photometry
from demosaic.prediction_archive import PredictionArchive, fingerprint


def saved_photo(root, sha, error):
    root.mkdir()
    archive = PredictionArchive(root/"archive")
    target = np.full((2, 3, 256, 256), .25, np.float32)
    data = {"target": target, "wb": np.ones((2, 3), np.float32),
            "matrix": np.broadcast_to(np.eye(3, dtype=np.float32), (2, 3, 3)),
            "packed": np.full((2, 4, 128, 128), .25, np.float32),
            "colors": np.array([[0, 1, 1, 2]]*2)}
    context = {"ids": ["bark", "foliage"], "stage": "photo", "pattern": "RGGB",
               "condition": {"name": "iso12800-prior", "shot": .00256, "read": .0000262144, "exposure": 1},
               "input_fingerprints": {"packed": fingerprint(data["packed"])}}
    model = {"label": f"archive-{sha[:1]}", **identity(sha)}
    prediction = target+error
    archive.append(model, context, prediction, data)
    label = f"report-{sha[:1]}"
    report = root/"summary.json"
    report.write_text(json.dumps({"models": [{**model, "label": label}], "protocol": {"border": 8}}))
    metrics = photometry(prediction, data)
    rows = [{"id": source, "kind": "photo", "condition": "iso12800-prior", "pattern": "RGGB", "model": label,
             "metrics": {key: float(value[i]) for key, value in metrics.items()}}
            for i, source in enumerate(context["ids"])]
    (root/"per-image.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows))
    audit(archive.manifest, report, root/"audit", stage="photo", material_ids=context["ids"])
    return root/"audit/result.json"


@pytest.fixture
def photo_pair(tmp_path):
    return saved_photo(tmp_path/"control", "a"*64, 1/64), saved_photo(tmp_path/"candidate", "b"*64, 1/128)


def contrast(paths, **kwargs):
    return compare_stage(*paths, identity("a"*64), identity("b"*64), stage="photo",
                         bootstrap_draws=100, **kwargs)


def test_independent_archive_gain_and_native_panels_have_closed_form(photo_pair, tmp_path):
    result = contrast(photo_pair, expected_observations=2)
    linear = next(r for r in result["summaries"]["all"] if r["metric"] == "linear_psnr")
    assert linear["change"] == pytest.approx(20*np.log10(2), abs=1e-12)
    assert linear["units"] == linear["observations"] == 2
    output = tmp_path/"crops"
    output.mkdir()
    crops = photo_comparison(result, output)
    assert len(crops["comparison"]["panels"]) == 8
    for receipt in crops["candidate_triplets"]:
        np.testing.assert_array_equal(triplet_pixels(receipt)[0], triplet_pixels(receipt)[2])
        assert binding(receipt["image"]["path"])["sha256"] == receipt["original_image"]["sha256"]
    with pytest.raises(FileExistsError):
        photo_comparison(result, output)


@pytest.mark.parametrize("corruption", ["noisy", "target", "mask", "order", "missing", "duplicate", "unbound", "protocol"])
def test_different_inputs_supervision_coverage_or_protocol_cannot_pair(photo_pair, corruption):
    path = photo_pair[1]
    audit_result = json.loads(path.read_text())
    manifest_path = Path(audit_result["manifest"]["path"])
    record = json.loads(manifest_path.read_text())
    rows_path = Path(audit_result["independent_rows"]["path"])
    rows = json.loads(rows_path.read_text())
    if corruption == "noisy":
        record["context"]["input_fingerprints"]["packed"]["sha256"] = "c"*64
    elif corruption in {"target", "mask"}:
        key = "target" if corruption == "target" else "sensor_mask"
        record["supervision_values"][key] = {"sha256": "c"*64}
    elif corruption == "order":
        record["context"]["ids"].reverse()
    elif corruption in {"missing", "duplicate", "unbound"}:
        if corruption == "missing":
            rows.pop()
        elif corruption == "duplicate":
            rows.append(rows[0])
        else:
            rows[0]["metrics"]["srgb_psnr"] += 1
        rows_path.write_text(json.dumps(rows))
        if corruption != "unbound":
            audit_result["independent_rows"] = binding(rows_path)
    else:
        report_path = Path(audit_result["report"]["path"])
        report = json.loads(report_path.read_text())
        report["protocol"]["border"] = 16
        report_path.write_text(json.dumps(report))
        audit_result["report"] = binding(report_path)
    manifest_path.write_text(json.dumps(record)+"\n")
    audit_result["manifest"] = binding(manifest_path)
    path.write_text(json.dumps(audit_result))
    with pytest.raises(ValueError):
        contrast(photo_pair)


def test_missing_endpoint_wrong_policy_count_and_display_are_rejected(photo_pair, tmp_path):
    with pytest.raises(ValueError, match="Checkpoint/policy"):
        compare_stage(*photo_pair, identity("a"*64), identity("b"*64, "dihedral8"), stage="photo")
    with pytest.raises(ValueError, match="Incomplete"):
        contrast(photo_pair, expected_observations=3)
    result = contrast(photo_pair)
    result["candidate_native_triplets"][0]["display_exposure"] = 2
    with pytest.raises(ValueError, match="display differs"):
        photo_comparison(result, tmp_path)


def test_camera_capture_identity_comes_from_full_tile_id_and_metrics_are_finite():
    row = {"scene": "scene", "tile_id": "scene:"+"c"*64+":12:34"}
    assert normalize_row(row, "known")["pair"] == "c"*64
    with pytest.raises(ValueError, match="capture differs"):
        normalize_row({**row, "pair": "d"*64}, "unseen")
    for a, b in [(None, 1), ([1, 2], [1]), (float("inf"), 0)]:
        with pytest.raises(ValueError):
            metric_delta(a, b)
    assert metric_delta(None, None) is None
    assert metric_delta([1, 2], [2, 1]) == [-1, 1]
    rows = [{"kind": "carrier", "level": .18, "contrast": .02, "period": 4,
             "condition": "noisy", "control": {"in_phase_gain": .8}, "candidate": {"in_phase_gain": 1.4}}]
    group = analytic_groups(rows, "texture")[0]
    assert group["candidate"]["absolute_gain_error_from_one"]["mean"] > group["control"]["absolute_gain_error_from_one"]["mean"]


def saved_gfx(root, sha, error):
    root.mkdir()
    report = {"selection": {"display_exposure": 4}, "sources": [{"role": "noisy", "sha256": "c"*64}],
              "conditioning": {"shot": .001, "read": .000001}, "reference_calibration": {},
              "native_crops": [], "float_contexts": []}
    native = []
    for i, name in enumerate(["sky", "building", "foliage", "chain-link-fence", "sign", "platform"]):
        region = {"name": name, "noisy_xy": [176, 176], "reference_xy": [177, 176], "size": 160}
        for role, shape in [("noisy-packed", (1, 4, 256, 256)), ("reference-rgb", (1, 3, 160, 160))]:
            path = root/f"{i}-{role}.npy"
            np.save(path, np.full(shape, .125, np.float32))
            receipt = {"region": region, "role": role, "image": path.name, "sha256": binding(path)["sha256"], "shape": list(shape)}
            receipt.update({"pattern": "RGGB", "context_xywh": [0, 0, 512, 512]} if role == "noisy-packed" else {"source_roi_xywh": [177, 176, 160, 160]})
            report["float_contexts"].append(receipt)
        report["native_crops"].append({"checkpoint_sha256": sha, "full_frame": True, "region": region,
                                       "conditioning": report["conditioning"], "display_exposure": 4,
                                       "shared_wb": [1, 1, 1], "shared_matrix": np.eye(3).tolist(),
                                       "reference": "Independent ISO100; not exact GT"})
        path = root/f"{i}-prediction.npy"
        np.save(path, np.full((1, 3, 160, 160), .125+error, np.float32))
        native.append({"checkpoint": {"sha256": sha}, "region": region, "array": binding(path)})
    report_path = root/"report.json"
    report_path.write_text(json.dumps(report))
    result_path = root/"result.json"
    result_path.write_text(json.dumps({"report": binding(report_path), "full_native_floats": native}))
    return result_path


def test_gfx_full_floats_render_common_inputs_and_approximate_reference(tmp_path):
    a, b = saved_gfx(tmp_path/"a", "a"*64, 1/64), saved_gfx(tmp_path/"b", "b"*64, 1/128)
    output = tmp_path/"gfx"
    output.mkdir()
    result = gfx_comparison(a, b, "a"*64, "b"*64, output)
    assert result["quality_scores"] is None and result["new_neural_forwards"] == 0
    assert len(result["boards"]) == 2 and len(result["boards"][0]["panels"]) == 12
    named_output = tmp_path/"tiny-small"
    named_output.mkdir()
    named = gfx_comparison(a, b, "a"*64, "b"*64, named_output, labels=("V114 Tiny", "V115 Small"))
    for original, renamed in zip(result["boards"], named["boards"], strict=True):
        assert [p["pixel_sha256"] for p in original["panels"]] == [p["pixel_sha256"] for p in renamed["panels"]]
        assert {p["label"] for p in renamed["panels"]} == {"Noisy", "V114 Tiny", "V115 Small", "ISO100 ref (not GT)"}
        assert all(source["candidate"]["prediction"]["checkpoint"]["sha256"] == "b"*64 for source in renamed["sources"])
    path = b.parent/"0-reference-rgb.npy"
    reference = np.load(path)
    reference[..., 0, 0] += .01
    np.save(path, reference)
    report_path = b.parent/"report.json"
    report = json.loads(report_path.read_text())
    report["float_contexts"][1]["sha256"] = binding(path)["sha256"]
    report_path.write_text(json.dumps(report))
    stage = json.loads(b.read_text())
    stage["report"] = binding(report_path)
    b.write_text(json.dumps(stage))
    with pytest.raises(ValueError, match="input/reference/transform"):
        gfx_comparison(a, b, "a"*64, "b"*64, output)


def test_comparison_modules_import_without_torch_or_cuda():
    script = Path(__file__).resolve().parents[1]/"scripts"
    code = f"import sys; sys.path.insert(0, {str(script)!r}); import compare_quality_archives, compare_quality_crops, queue_detail_data_comparison; assert 'torch' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)


@pytest.mark.parametrize("change", [None, "model", "seed", "blur", "parent", "loss"])
def test_recipe_changes_are_limited_to_declared_data_and_equivalent_protocol(tmp_path, change):
    protocol_a, protocol_b, reviewed = (tmp_path/name for name in ("protocol-a.yaml", "protocol-b.yaml", "reviewed.json"))
    for path in (protocol_a, protocol_b):
        path.write_text("border: 8\n")
    reviewed.write_text("{}")
    base = {"run": "old", "experiment_notes": "control", "validation_protocol": str(protocol_a),
            "paired_manifest": "old.json", "steps": 20000, "seed": 63, "blur": 0,
            "model": {"dino": "tiny"}, "initialize_parent": {"sha256": "c"*64}}
    candidate = {**base, "run": "new", "paired_manifest": str(reviewed), "validation_protocol": str(protocol_b),
                 "fine_weak_texture_fraction": .075, "normalized_band_weight": 0}
    changes = {"model": {"dino": "small"}, "seed": 64, "blur": .1,
               "parent": {"sha256": "d"*64}, "loss": .01}
    if change:
        candidate[{"parent": "initialize_parent", "loss": "normalized_band_weight"}.get(change, change)] = changes[change]
    a, b = tmp_path/"control.json", tmp_path/"candidate.json"
    a.write_text(json.dumps(base))
    b.write_text(json.dumps(candidate))
    if change:
        with pytest.raises(ValueError, match="Unplanned"):
            recipe_contrast(binding(a), binding(b), binding(reviewed))
    else:
        result = recipe_contrast(binding(a), binding(b), binding(reviewed))
        assert set(result["differences"]) == {"run", "paired_manifest", "validation_protocol", "fine_weak_texture_fraction"}


@pytest.mark.parametrize("corruption", [None, "audit-owner", "missing-stage", "arm", "execution", "checkpoint"])
def test_completed_dependency_requires_actual_owner_arm_budget_source_and_bytes(tmp_path, monkeypatch, corruption):
    def saved(name, value):
        path = tmp_path/name
        path.write_text(json.dumps(value))
        return binding(path)
    monkeypatch.setattr(queue, "live", lambda owner: False)
    audit_owner, train_owner, worker_owner = ({"pid": i, "created": 10+i} for i in (1, 2, 3))
    audit_plan, execution = saved("audit-plan.json", {}), saved("execution.json", {})
    checkpoint_path = tmp_path/"not-a-model.pt"
    checkpoint_path.write_bytes(b"Engineering identity fixture, never loaded as a model")
    checkpoint = binding(checkpoint_path)
    worker = saved("worker.json", {"arm": "V114" if corruption != "arm" else "V115", "updates": 20000,
                                   "owner": worker_owner, "checkpoint": checkpoint, "source_sha256": "c"*64})
    counts = {"training_forwards": 20000, "encoder_training_forwards": 20000, "optimizer_steps": 20000,
              "prepared_training_batches": 20000, "validation_forwards": 640, "encoder_validation_forwards": 640}
    receipt = saved("accounting.json", {"counts": counts, "worker_result": worker, "owner": worker_owner,
                    "execution_plan": execution if corruption != "execution" else {}, "phase": "train",
                    "checkpoint": checkpoint, "source_sha256": "c"*64, "fresh_AdamW_states": 89,
                    "all_AdamW_steps": 20000, "initial_all91_EMA_exact_to_explicit_parent": True,
                    "frozen_encoder_no_gradients": True, "model_EMA_Adam_finite": True,
                    "official_frozen_encoder_hash": "d"*64,
                    "status": "Historical generic Small text; actual worker arm is authoritative"})
    training = saved("training-status.json", {"owner": train_owner, "execution_plan": execution,
                     "status": "done", "result": saved("training-result.json", {}),
                     "completed": {"train-V114": receipt}})
    gfx = saved("full-gfx.json", {})
    boundary = saved("boundary.json", {"stage_results": {"full-gfx": gfx}})
    audited = saved("audit-result.json", {"owner": audit_owner, "queue_plan": audit_plan,
                   "stages": {s: {} for s in ("photo", "known", "unseen", "texture", "color") if corruption != "missing-stage" or s != "known"},
                   "Torch_imported": False, "new_neural_forwards": 0, "new_encoder_forwards": 0,
                   "RAW_decodes": 0, "new_noise_observations": 0, "completed_evaluation": boundary})
    state = saved("audit-status.json", {"owner": audit_owner if corruption != "audit-owner" else {}, "plan": audit_plan,
                  "status": queue.AUDIT_TERMINAL, "result": audited})
    role = {"arm": "V114", "audit_status": state["path"], "audit_owner": audit_owner, "audit_plan": audit_plan,
            "training_status": training["path"], "training_owner": train_owner, "training_execution": execution,
            "training_terminal": "done", "expected_source_archive_sha256": "c"*64}
    if corruption == "checkpoint":
        checkpoint_path.write_bytes(b"Changed")
    if corruption:
        with pytest.raises(ValueError):
            queue.completed_role(role)
    else:
        result = queue.completed_role(role)
        assert result["checkpoint"] == checkpoint and result["full_gfx"] == gfx
