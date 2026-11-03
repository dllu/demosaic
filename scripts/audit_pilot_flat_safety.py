"""Independently audit actual flat reductions, PNG cells and real-sky detrending."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import crop
from PIL import Image
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar


def reductions(error):
    channels = np.asarray(error, dtype=np.float64).reshape(3, 160, 160)
    means = np.array([channel.sum() / 25600 for channel in channels])
    centered = [channel - mean for channel, mean in zip(channels, means, strict=True)]
    result = {
        "DC_RGB": means.tolist(),
        "DC_MSE": float(np.dot(means, means) / 3),
        "MSE": float(sum(np.vdot(c, c) for c in channels) / 76800),
        "spatial_MSE": float(sum(np.vdot(c, c) for c in centered) / 76800),
        "block_RMS": {},
    }
    for side in (1, 4, 16, 32):
        if side == 1:
            energy = result["spatial_MSE"]
        else:
            means = [
                channel[y : y + side, x : x + side].sum() / side**2
                for channel in centered
                for y in range(0, 160, side)
                for x in range(0, 160, side)
            ]
            energy = np.dot(means, means) / len(means)
        result["block_RMS"][str(side)] = float(np.sqrt(energy))
    return result


def audit(root):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and "torch" not in sys.modules
    plan = read(root / "plan-v1.json")
    guard(plan)
    receipt = read(root / "flat-safety-v1.json")
    assert receipt["plan"] == ref(root / "plan-v1.json")
    collection = read(root / "collection-v1.json")
    assert collection["plan"] == ref(root / "plan-v1.json")
    assert collection["counts"] == {"root": 48, "encoder": 48}
    predictions = {r["id"]: r["prediction"] for r in collection["observations"]}
    expected = {(r["id"], r["method"]): r for r in receipt["flat_metrics"]}
    images = {r["case"]["id"]: r for r in receipt["flat_images"]}
    maximum = channels_checked = rows_checked = 0

    def checked(binding):
        assert ref(binding["path"]) == binding
        return binding["path"]

    def compare(actual, expected):
        nonlocal maximum
        for key in ("DC_RGB", "DC_MSE", "MSE", "spatial_MSE"):
            difference = float(np.max(np.abs(np.asarray(actual[key]) - expected[key])))
            maximum = max(maximum, difference)
            np.testing.assert_allclose(actual[key], expected[key], rtol=1e-10, atol=1e-16)
        for side in ("1", "4", "16", "32"):
            a, b = actual["block_RMS"][side], expected["block_RMS"][side]
            maximum = max(maximum, abs(a - b))
            np.testing.assert_allclose(a, b, rtol=1e-10, atol=1e-16)

    for observation in plan["observations"]:
        with np.load(checked(observation["arrays"]), allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        target = arrays["target"].astype(np.float64)
        assert np.array_equal(target, np.broadcast_to(target[..., :1, :1], target.shape))
        values = [
            ("V120", np.load(checked(observation["control"]), allow_pickle=False)),
            (
                plan["model_label"],
                np.load(checked(predictions[observation["id"]]), allow_pickle=False),
            ),
        ]
        for label, value in values:
            error = value.astype(np.float64)[..., 48:208, 48:208] - target[..., 48:208, 48:208]
            compare(reductions(error), expected[(observation["id"], label)])
            rows_checked += 1
        case = observation["case"]
        if case["pattern"] != "RGGB" or case["condition"]["name"] != "iso12800-prior":
            continue
        image = images[case["id"]]
        png = np.asarray(Image.open(checked(image["image"])))
        assert image["ROI_xywh"] == [48, 48, 160, 160] and image["display_exposure"] == 1
        for index, value in enumerate([noisy_malvar(arrays), *[v for _, v in values], target]):
            cell = crop(value, arrays, [48, 48, 160, 160], 1)
            np.testing.assert_array_equal(png[24:184, 8 + 168 * index : 168 + 168 * index], cell)
            channels_checked += cell.size

    primary = Path(plan["primary_root"])
    main = read(primary / "plan-v1.json")
    sky = next(o for o in main["observations"] if o["id"] == "main-overcast-sky")
    candidate = next(
        r for r in read(primary / "collection-v1.json")["observations"] if r["id"] == sky["id"]
    )
    expected_sky = {r["method"]: r for r in receipt["sky_metrics"]}
    x, y, w, h = sky["ROI_xywh"]
    yy, xx = np.mgrid[-1:1:160j, -1:1:160j]
    bindings = [
        (c.get("label", c.get("model", {}).get("label")), c["prediction"]) for c in sky["controls"]
    ] + [(main["model_label"], candidate["prediction"])]
    for label, binding in bindings:
        value = np.load(checked(binding), allow_pickle=False)[0, :, y : y + h, x : x + w].astype(
            np.float64
        )
        # The symmetric regular grid makes1,x,y mutually orthogonal; no lstsq.
        dc = value.mean((1, 2))
        sx = np.einsum("chw,hw->c", value, xx) / np.sum(xx**2)
        sy = np.einsum("chw,hw->c", value, yy) / np.sum(yy**2)
        residual = value - dc[:, None, None] - sx[:, None, None] * xx - sy[:, None, None] * yy
        compare(reductions(residual), expected_sky[label]["detrended_variation"])
    assert rows_checked == 96 and channels_checked == 6 * 4 * 160 * 160 * 3
    save(
        root / "independent-flat-audit-v1.json",
        {
            "status": "passed-independent-actual-flat-and-sky-audit",
            "report": ref(root / "flat-safety-v1.json"),
            "auditor": ref(__file__),
            "flat_metric_rows": rows_checked,
            "sky_methods": len(bindings),
            "maximum_absolute_metric_error": maximum,
            "PNG_channels_exact": channels_checked,
            "Torch_imported": False,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    audit(parser.parse_args().root.resolve())
