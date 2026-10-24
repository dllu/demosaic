import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

from demosaic import archive_metrics as independent
from demosaic.cfa import PATTERNS, malvar
from demosaic.metrics import quality_metrics
from demosaic.prediction_archive import PredictionArchive, fingerprint

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_quality_archive import audit, paired_changes


def supervision(target):
    return {"target": target, "wb": np.ones((len(target), 3), np.float32),
            "matrix": np.broadcast_to(np.eye(3, dtype=np.float32), (len(target), 3, 3))}


@pytest.mark.parametrize("pattern", PATTERNS)
def test_independent_malvar_matches_all_phases_borders_and_unequal_wb(pattern):
    packed = np.random.default_rng(42).normal(.2, .3, (2, 4, 16, 19)).astype(np.float32)
    data = {"packed": packed, "colors": np.array([PATTERNS[pattern]]*2),
            "wb": np.array([[2.1, 1, 1.4], [1.3, .8, 2.4]], np.float32)}
    expected = malvar(*(torch.from_numpy(data[k]) for k in ("packed", "colors", "wb"))).numpy()
    np.testing.assert_allclose(independent.noisy_malvar(data), expected, atol=6e-7, rtol=2e-6)


def test_sensor_scores_use_only_valid_samples_and_minimum_count():
    prediction = np.full((1, 3, 96, 96), .8, np.float32)
    prediction[:, 0] = .25
    targets = supervision(np.full_like(prediction, .2))
    mask = np.zeros_like(prediction)
    mask[:, 0, ::2, ::2] = 1
    targets.update(reference_rgb=targets.pop("target"), sensor_reference=np.full_like(prediction, .2), sensor_mask=mask)
    actual = independent.photometry(prediction, targets, border=16, camera=True)
    expected = -10*np.log10((float(np.float32(.25))-float(np.float32(.2)))**2)
    assert actual["reference_samples"][0] == 1024
    assert actual["sensor_psnr"][0] == pytest.approx(expected, abs=1e-12)
    mask[:, 0, 16, 16] = 0
    assert np.isnan(independent.photometry(prediction, targets, border=16, camera=True)["sensor_psnr"][0])
    mask[0, 1, 17, 17] = .5
    with pytest.raises(ValueError, match="binary"):
        independent.photometry(prediction, targets, border=16, camera=True)


def test_photo_scores_clip_for_psnr_but_keep_native_archive_values():
    target = np.zeros((1, 3, 32, 32), np.float32)
    prediction = np.full_like(target, -2)
    metrics = independent.photometry(prediction, supervision(target), border=0)
    assert metrics["linear_psnr"][0] == metrics["srgb_psnr"][0] == 120
    assert prediction.min() == -2
    with pytest.raises(ValueError, match="Border"):
        independent.photometry(prediction, supervision(target), border=16)


def test_carrier_closed_form_separates_gain_phase_bias_and_residual():
    angle = np.arange(256)*2*np.pi/8
    target = np.broadcast_to((.2+.002*np.cos(angle))[None, None, None], (2, 3, 256, 256)).copy()
    prediction = np.broadcast_to((.2003+.001*np.cos(angle)+.0005*np.sin(angle))[None, None, None], target.shape).copy()
    m = independent.texture(prediction, supervision(target), period=8)
    np.testing.assert_allclose(m["in_phase_gain"], .5, atol=1e-12)
    np.testing.assert_allclose(m["quadrature_gain"], .25, atol=1e-12)
    np.testing.assert_allclose(m["amplitude_ratio"], np.sqrt(.5**2+.25**2), atol=1e-12)
    np.testing.assert_allclose(m["dc_bias_abs"], .0003, atol=1e-12)
    assert max(m["noncarrier_rms"]) < 1e-14
    with pytest.raises(ValueError, match="period"):
        independent.texture(prediction, supervision(target), period=7)


def test_flat_fft_reports_false_texture_without_dividing_by_target_texture():
    target = np.full((1, 3, 256, 256), .2)
    wave = .0005*np.cos(np.arange(256)*2*np.pi/8)
    prediction = target+.001+wave[None, None, None]
    m = independent.texture(prediction, supervision(target))
    assert m["dc_bias_abs_rgb"][0] == pytest.approx(.001)
    assert m["spatial_luma_rms"][0] == pytest.approx(.0005/np.sqrt(2))
    assert m["relative_peak_band_contrast"][0] == pytest.approx(.0005/.2)
    assert m["relative_band_rms"][0] == pytest.approx(.0005/np.sqrt(2)/.2)


def test_color_keeps_unclipped_camera_bias_and_cfa_phase_identity():
    target = np.full((1, 3, 256, 256), .2, np.float32)
    data = supervision(target)
    data.update(colors=np.array([[0, 1, 1, 2]]), packed=np.full((1, 4, 128, 128), .21, np.float32))
    prediction = target+np.array([-1., .1, 2.], np.float32)[None, :, None, None]
    m = independent.color(prediction, data)
    means = (prediction-target.astype(np.float64)).mean((0, 2, 3))
    np.testing.assert_allclose(m["camera_RGB_mean_error"], means)
    np.testing.assert_allclose(m["predicted_minus_GT_CFA_phase_mean"], means[[0, 1, 1, 2]])
    assert m["camera_RGB_mean_component_fraction"] == pytest.approx(1)
    assert m["spatially_centered_camera_RGB_RMS"] < 1e-12


def photo_archive(root):
    archive = PredictionArchive(root/"archive")
    target = np.broadcast_to(np.linspace(.01, .6, 256, dtype=np.float32)[None, None, None], (2, 3, 256, 256)).copy()
    data = supervision(target)
    data["colors"] = np.array([[0, 1, 1, 2]]*2)
    data["packed"] = np.stack([target[:, c, y::2, x::2] for c, (y, x) in zip([0, 1, 1, 2], [(0, 0), (0, 1), (1, 0), (1, 1)], strict=True)], axis=1)
    context = {"ids": ["bark", "foliage"], "stage": "photo", "pattern": "RGGB",
               "condition": {"name": "iso12800-prior", "shot": .00256, "read": .0000262144, "exposure": 1},
               "input_fingerprints": {"packed": fingerprint(data["packed"])}}
    models, rows = [], []
    for j in range(2):
        model = {"label": f"method-{j}", "sha256": str(j)*64, "self_ensemble": "none"}
        prediction = target+.001*(j+1)
        archive.append(model, context, prediction, data)
        label = f"{j}:fixture:step-1"
        models.append({**model, "label": label})
        measures = quality_metrics(torch.from_numpy(prediction[..., 8:-8, 8:-8]), torch.from_numpy(target[..., 8:-8, 8:-8]),
                                   torch.from_numpy(data["wb"]), torch.from_numpy(data["matrix"].copy()))
        for i, identity in enumerate(context["ids"]):
            rows.append({"id": identity, "kind": "photo", "model": label, "condition": "iso12800-prior", "pattern": "RGGB",
                         "metrics": {k: float(v[i]) if torch.isfinite(v[i]) else None for k, v in measures.items()}})
    report = root/"summary.json"
    report.write_text(json.dumps({"models": models, "protocol": {"border": 8}}))
    (root/"per-image.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    return archive.manifest, report


def test_complete_archive_join_and_native_triplets_match_actual_pixels(tmp_path):
    manifest, report = photo_archive(tmp_path)
    result = audit(manifest, report, tmp_path/"audit", stage="photo", material_ids=["bark", "foliage"])
    assert result["models"] == 2 and result["observations"] == {"method-0": 2, "method-1": 2}
    assert len(result["native_triplets"]) == 4
    shared = {}
    for receipt in result["native_triplets"]:
        assert receipt["review_status"].endswith("viewing pending")
        with Image.open(receipt["image"]["path"]) as image:
            assert image.size == (512, 192)
        for i in (0, 2):
            key = receipt["source_id"], i
            digest = receipt["panels"][i]["pixel_sha256"]
            assert shared.setdefault(key, digest) == digest
    with pytest.raises(FileExistsError):
        audit(manifest, report, tmp_path/"audit", stage="photo")


@pytest.mark.parametrize("corruption", ["score", "missing", "duplicate"])
def test_bad_scores_or_incomplete_duplicate_report_cannot_pass(tmp_path, corruption):
    manifest, report = photo_archive(tmp_path)
    path = tmp_path/"per-image.jsonl"
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    if corruption == "score":
        rows[0]["metrics"]["srgb_psnr"] += 1
    elif corruption == "missing":
        rows.pop()
    else:
        rows.append(rows[0])
    path.write_text("".join(json.dumps(r)+"\n" for r in rows))
    with pytest.raises((ValueError, KeyError)):
        audit(manifest, report, tmp_path/"audit", stage="photo")


def test_cli_help_and_metric_import_do_not_import_torch():
    result = subprocess.run([sys.executable, "-c", "import demosaic.archive_metrics; import sys; assert 'torch' not in sys.modules"],
                            check=True, capture_output=True, text=True)
    assert result.returncode == 0


def test_camera_contrasts_weight_captures_and_scenes_not_number_of_crops():
    rows = []
    for scene, pair, scores in [("a", "x", [1]), ("a", "y", [3, 3, 3]), ("b", "z", [10])]:
        for i, value in enumerate(scores):
            rows.append({"scene": scene, "pair": pair, "tile_id": f"{pair}:{i}", "pattern": "RGGB",
                         "metrics": {"sensor_psnr": value}})
    control = [{**r, "metrics": {"sensor_psnr": 0}} for r in rows]
    result = paired_changes(rows, control, stage="known", metric="sensor_psnr", bootstrap_draws=100)
    assert result["current_mean"] == result["change"] == 6
    assert result["units"] == 2 and result["observations"] == 5
    assert result["unit_changes"] == [{"unit": "a", "change": 2}, {"unit": "b", "change": 10}]
    with pytest.raises(ValueError, match="coverage"):
        paired_changes(rows[:-1], control, stage="known", metric="sensor_psnr")


def test_source_contrasts_exclude_procedural_sources_and_match_condition_cfa():
    rows = [{"id": "a", "kind": "photo", "condition": c, "pattern": "RGGB", "metrics": {"srgb_psnr": v}}
            for c, v in [("adc", 1), ("noisy", 3)]]
    rows.append({"id": "procedural", "kind": "synthetic", "condition": "adc", "pattern": "RGGB", "metrics": {"srgb_psnr": 100}})
    control = [{**r, "metrics": {"srgb_psnr": 0}} for r in rows]
    result = paired_changes(rows, control, stage="photo", metric="srgb_psnr", bootstrap_draws=100)
    assert result["units"] == 1 and result["observations"] == 2 and result["change"] == 2
