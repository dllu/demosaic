import json

import numpy as np
import pytest

from demosaic.prediction_archive import PredictionArchive, fingerprint, iter_predictions


def batch():
    target = np.arange(2*3*12*16, dtype=np.float32).reshape(2, 3, 12, 16)/1000
    context = {"ids": ["bark", "canopy"], "condition": "iso100", "pattern": "RGGB",
               "input_fingerprints": {"packed": fingerprint(target[:, :, ::2, ::2])}}
    supervision = {"target": target, "wb": np.ones((2, 3), np.float32),
                   "matrix": np.broadcast_to(np.eye(3, dtype=np.float32), (2, 3, 3))}
    return context, target, supervision


def model(label="Tiny", digest="a", policy="none"):
    return {"label": label, "sha256": digest*64, "self_ensemble": policy}


def test_exact_native_signed_hdr_values_and_shared_targets_across_models(tmp_path):
    context, target, supervision = batch()
    archive = PredictionArchive(tmp_path / "archive")
    prediction = target*3-1  # Negative and above-white outputs must survive.
    a = archive.append(model(), context, prediction, supervision)
    b = archive.append(model("Small", "b"), context, prediction+.0001, supervision)
    assert a["supervision"] == b["supervision"]
    assert archive.verify_alignment() == {"models": 2, "observations_per_model": 1,
                                          "records": 2, "unique_supervision_arrays": 1}
    values = list(iter_predictions(archive.manifest))
    assert np.array_equal(values[0][1], prediction)
    assert values[0][1].dtype == np.float32 and values[0][1].shape == prediction.shape
    assert np.array_equal(values[1][1], prediction+.0001)
    assert np.array_equal(values[0][2]["target"], target)
    assert values[0][2]["matrix"].shape == (2, 3, 3)


@pytest.mark.parametrize("change", ["input", "ids", "target"])
def test_mismatched_inputs_source_order_and_supervision_are_rejected(tmp_path, change):
    context, target, supervision = batch()
    archive = PredictionArchive(tmp_path / "archive")
    archive.append(model(), context, target, supervision)
    context = json.loads(json.dumps(context))
    if change == "input":
        context["input_fingerprints"]["packed"]["sha256"] = "0"*64
    elif change == "ids":
        context["ids"].reverse()
    else:
        supervision = {**supervision, "target": target+.01}
    archive.append(model("Small", "b"), context, target, supervision)
    with pytest.raises(ValueError, match="different observations"):
        archive.verify_alignment()


@pytest.mark.parametrize("field", ["prediction", "supervision"])
def test_corrupt_files_are_detected_without_overwriting_completed_evidence(tmp_path, field):
    context, target, supervision = batch()
    archive = PredictionArchive(tmp_path / "archive")
    row = archive.append(model(), context, target, supervision)
    path = tmp_path / "archive" / ("predictions/batch-000000.npy" if field == "prediction" else "supervision/"+row[field]["path"].split("/")[-1])
    path.chmod(0o644)
    with path.open("r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"x")
    with pytest.raises(ValueError, match="checksum mismatch"):
        list(iter_predictions(archive.manifest))
    assert archive.manifest.exists() and path.read_bytes()[-1:] == b"x"


def test_no_overwrite_duplicate_context_and_changed_model_identity(tmp_path):
    context, target, supervision = batch()
    archive = PredictionArchive(tmp_path / "archive")
    archive.append(model(), context, target, supervision)
    with pytest.raises(ValueError, match="Duplicate"):
        archive.append(model(), context, target, supervision)
    with pytest.raises(ValueError, match="metadata changed"):
        archive.append(model("Different name"), context, target, supervision)
    with pytest.raises(FileExistsError):
        PredictionArchive(archive.output)
    assert len(list(iter_predictions(archive.manifest))) == 1


def test_inference_policy_distinguishes_same_checkpoint(tmp_path):
    context, target, supervision = batch()
    archive = PredictionArchive(tmp_path / "archive")
    archive.append(model(), context, target, supervision)
    archive.append(model(policy="dihedral8"), context, target, supervision)
    assert archive.verify_alignment()["models"] == 2


def test_noncontiguous_input_layout_has_same_fingerprint():
    data = np.arange(3*8*10, dtype=np.float32).reshape(3, 8, 10).transpose(2, 0, 1)
    assert not data.flags.c_contiguous
    assert fingerprint(data) == fingerprint(data.copy())


def test_existing_color_prediction_is_shared_without_another_array_copy(tmp_path):
    context, target, supervision = batch()
    source = tmp_path / "already-evaluated.npy"
    np.save(source, target, allow_pickle=False)
    original = source.read_bytes()
    archive = PredictionArchive(tmp_path / "archive")
    row = archive.append(model(), context, target, supervision, prediction_file=source)
    from pathlib import Path
    assert Path(row["prediction"]["path"]).samefile(source)
    assert source.read_bytes() == original
    assert np.array_equal(next(iter_predictions(archive.manifest))[1], target)


@pytest.mark.parametrize("invalid", ["half", "nonfinite", "shape", "missing-target"])
def test_invalid_data_cannot_publish_a_record(tmp_path, invalid):
    context, target, supervision = batch()
    archive = PredictionArchive(tmp_path / "archive")
    prediction = target.copy()
    if invalid == "half":
        prediction = prediction.astype(np.float16)
    elif invalid == "nonfinite":
        prediction[0, 0, 0, 0] = np.nan
    elif invalid == "shape":
        prediction = prediction[..., :-1]
    else:
        supervision = {k: v for k, v in supervision.items() if k != "target"}
    with pytest.raises(ValueError):
        archive.append(model(), context, prediction, supervision)
    assert archive.manifest.read_text() == ""
