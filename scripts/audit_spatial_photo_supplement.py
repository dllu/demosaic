"""Recompute photograph metrics, targets and native PNG panels independently."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from train_directional_bank_trial import guard, read, ref, save


def audit(path):
    from demosaic.archive_metrics import noisy_malvar

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    result_path = root / "report-v1/result-v1.json"
    result = read(result_path)
    assert result["plan"] == ref(path)
    assert len(result["rows"]) == 384 and len(result["images"]) == 56
    rows = {(r["id"], r["method"]): r for r in result["rows"]}
    assert len(rows) == 384
    inputs, values = {}, {}
    max_metric_error = max_target_error = 0.0
    n = np.arange(16)
    c = np.cos(np.pi * (n[None] + 0.5) * n[:, None] / 16) * np.sqrt(2 / 16)
    c[0] /= np.sqrt(2)
    radius = np.hypot(n[:, None] / 32, n[None] / 32)
    mask = (radius >= 1 / 8) & (radius < 1 / 3)

    def band(value, arrays, roi):
        x, y, w, h = roi
        camera = value[0, :, y : y + h, x : x + w].astype(np.float64)
        # Combine WB/matrix/luma explicitly instead of the report's batched transform.
        weights = np.array([0.2126, 0.7152, 0.0722]) @ arrays["matrix"][0].astype(np.float64)
        weights *= arrays["wb"][0].astype(np.float64)
        luma = sum(weights[i] * camera[i] for i in range(3))
        blocks = np.array(
            [luma[y : y + 16, x : x + 16] for y in range(0, 160, 16) for x in range(0, 160, 16)]
        )
        coefficients = np.einsum("iu,nuv,jv->nij", c, blocks, c, optimize=True)
        return coefficients[:, mask]

    for o in plan["observations"]:
        assert ref(o["arrays"]["path"]) == o["arrays"]
        with np.load(o["arrays"]["path"], allow_pickle=False) as a:
            arrays = {k: a[k] for k in a.files}
        inputs[o["id"]] = arrays
        source = o["source"]
        assert ref(source["cache"])["sha256"] == source["cache_sha256"]
        original = np.load(source["cache"], allow_pickle=False)
        x, y, w, h = o["source_ROI_xywh"]
        clean = original[y : y + h, x : x + w].astype(np.float64) / 65535
        mean = clean.mean((0, 1), keepdims=True)
        clean = (mean + o["variant"]["contrast_about_channel_means"] * (clean - mean)) * o["scale"]
        observed = np.einsum(
            "ij,jhw->hwi",
            arrays["matrix"][0].astype(np.float64),
            arrays["target"][0].astype(np.float64) * arrays["wb"][0, :, None, None],
        )
        max_target_error = max(max_target_error, float(np.max(np.abs(observed - clean))))
        np.testing.assert_allclose(observed, clean, rtol=5e-5, atol=2e-8)
        x, y, w, h = o["ROI_xywh"]
        truth = band(arrays["target"], arrays, o["ROI_xywh"])
        for method in ("V143", "V144", "V145"):
            row = rows[o["id"], method]
            assert ref(row["prediction"]["path"]) == row["prediction"]
            prediction = np.load(row["prediction"]["path"], allow_pickle=False)
            assert list(prediction.shape) == o["output_shape"] and np.isfinite(prediction).all()
            values[o["id"], method] = prediction
            error = prediction.astype(np.float64) - arrays["target"].astype(np.float64)
            cropped = error[..., y : y + h, x : x + w]
            dc = cropped.reshape(3, -1).sum(1) / (160 * 160)
            spatial = cropped - dc[None, :, None, None]
            predicted = band(prediction, arrays, o["ROI_xywh"])
            energy = np.dot(truth.ravel(), truth.ravel())
            gain = float(np.dot(predicted.ravel(), truth.ravel()) / energy)
            metrics = {
                "full_error_RMS_DN16": np.linalg.norm(error.ravel()) / np.sqrt(error.size) * 65535,
                "crop_error_RMS_DN16": np.linalg.norm(cropped.ravel())
                / np.sqrt(cropped.size)
                * 65535,
                "crop_DC_RMS_DN16": np.linalg.norm(dc) / np.sqrt(3) * 65535,
                "crop_spatial_RMS_DN16": np.linalg.norm(spatial.ravel())
                / np.sqrt(spatial.size)
                * 65535,
                "crop_linear_sRGB_luma_band_gain": gain,
                "crop_relative_band_error": np.linalg.norm(predicted - truth) / np.sqrt(energy),
                "crop_orthogonal_band_RMS_DN16": np.linalg.norm(predicted - gain * truth)
                / 160
                * 65535,
            }
            for k, v in metrics.items():
                max_metric_error = max(max_metric_error, abs(row[k] - v))
                np.testing.assert_allclose(row[k], v, rtol=1e-10, atol=1e-10)
    channels = 0
    for asset in result["images"]:
        assert ref(asset["image"]["path"]) == asset["image"]
        canvas = np.asarray(Image.open(asset["image"]["path"]))
        o = asset["observation"]
        arrays = inputs[o["id"]]
        x, y, w, h = o["ROI_xywh"]
        anchor = arrays["target"][0, :, y : y + h, x : x + w].astype(np.float64).mean((1, 2))
        np.testing.assert_array_equal(anchor, asset["shared_camera_RGB_anchor"])
        assert asset["display_exposure"] == o["display_exposure"] and asset["no_resize"]
        for panel in asset["panels"]:
            label = panel["label"]
            if label == "Noisy":
                value = noisy_malvar(arrays)
            elif label == "Constructed GT":
                value = arrays["target"]
            else:
                value = values[o["id"], label]
            rgb = value[0, :, y : y + h, x : x + w].transpose(1, 2, 0).astype(np.float64)
            rgb = anchor + asset["shared_display_contrast"] * (rgb - anchor)
            rgb = rgb * o["display_exposure"] * arrays["wb"][0].astype(np.float64)
            linear = np.einsum("ij,hwj->hwi", arrays["matrix"][0].astype(np.float64), rgb).clip(
                0, 1
            )
            encoded = np.where(
                linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055
            )
            expected = np.rint(encoded * 255).astype(np.uint8)
            xx, yy, ww, hh = panel["xywh"]
            assert (ww, hh) == (160, 160)
            np.testing.assert_array_equal(canvas[yy : yy + hh, xx : xx + ww], expected)
            channels += expected.size
    target = root / "report-v1/independent-audit-v1.json"
    assert not target.exists()
    save(
        target,
        {
            "status": "passed-independent-spatial-photo-metric-target-PNG-audit",
            "report": ref(result_path),
            "metric_rows": len(rows),
            "PNG_count": len(result["images"]),
            "PNG_RGB_channels_exact": channels,
            "maximum_absolute_metric_difference": max_metric_error,
            "maximum_source_target_linear_error": max_target_error,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
        },
    )
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    audit(parser.parse_args().plan.resolve())
