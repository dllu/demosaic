"""Independently reconstruct every native comparison pixel in Float64."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import noisy_malvar


def render(value, arrays, roi, exposure):
    v = np.einsum(
        "bij,bjhw->bihw",
        arrays["matrix"].astype(np.float64),
        value.astype(np.float64) * exposure * arrays["wb"].astype(np.float64)[..., None, None],
    ).clip(0, 1)
    v = np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)
    x, y, w, h = roi
    return np.rint(v[0, :, y : y + h, x : x + w].transpose(1, 2, 0) * 255).astype(np.uint8)


def main(ROOT):
    figures = read(ROOT / "figures-v1.json")
    result = read(ROOT / "scores-v1.json")
    assert figures["result"] == ref(ROOT / "scores-v1.json")
    rows = {}
    for row in result["rows"]:
        rows.setdefault(row["id"], {})[row["method"]] = row
    channels, triplets = 0, 0
    for item in figures["images"]:
        assert ref(item["image"]["path"]) == item["image"]
        actual = np.asarray(Image.open(item["image"]["path"]))
        if "source_board" in item:
            assert ref(item["source_board"]["path"]) == item["source_board"]
            source = np.asarray(Image.open(item["source_board"]["path"]))
            for panel in item["panels"]:
                x, y, w, h = panel["xywh"]
                sx, sy, sw, sh = panel["source_xywh"]
                assert (w, h) == (sw, sh) == (160, 160)
                np.testing.assert_array_equal(
                    actual[y : y + h, x : x + w], source[sy : sy + sh, sx : sx + sw]
                )
                triplets += 3 * w * h
            continue
        case = item["case"]
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        r = rows[item["id"]]
        values = {
            "Noisy Malvar": noisy_malvar(a),
            "V143 parent": np.load(r["parent"]["prediction"]["path"]),
        }
        for method, label in [("raw-step1000", "V147 raw1000"), ("EMA-step1000", "V147 EMA1000")]:
            values[label] = np.load(r[method]["prediction"]["path"])
        if "periodic-detail" in r:
            values["Periodic detail"] = np.load(r["periodic-detail"]["prediction"]["path"])
        if case["kind"] == "real":
            values["ISO100 AHD, not GT"] = (
                a["reference_rgb"]
                if "reference_rgb" in a
                else np.load(case["reference_binding"]["path"])
            )
        else:
            values["Exact constructed GT"] = a["target"]
        for panel in item["panels"]:
            label = panel["label"]
            x, y, w, h = panel["xywh"]
            assert (w, h) == (160, 160)
            if "JPEG" in label:
                window = next(w for w in case["cases"] if w["ROI_xywh"] == item["ROI_xywh"])
                key = (
                    "noisy_camera_jpeg" if label.startswith("ISO6400") else "reference_camera_jpeg"
                )
                binding = window["camera_JPEGs"][key]["pixels"]
                assert ref(binding["path"]) == binding
                expected = np.load(binding["path"])
                assert item["JPEG_display"] == "native sRGB8 without exposure/contrast adjustment"
            else:
                v = values[label.removesuffix(" bypass")].astype(np.float64)
                anchor = np.array(item["shared_camera_RGB_anchor"]).reshape(1, 3, 1, 1)
                transformed = anchor + item["shared_display_contrast"] * (v - anchor)
                roi = (
                    [0, 0, 160, 160]
                    if case["kind"] == "real"
                    and label == "ISO100 AHD, not GT"
                    and v.shape[-2:] == (160, 160)
                    else item["ROI_xywh"]
                )
                expected = render(transformed, a, roi, item["RAW_exposure"])
            assert expected.shape == (160, 160, 3)
            np.testing.assert_array_equal(actual[y : y + h, x : x + w], expected)
            channels += expected.size
    for item in figures["sheets"]:
        assert ref(item["image"]["path"]) == item["image"]
        sheet = np.asarray(Image.open(item["image"]["path"]))
        for j, index in enumerate(item["board_indices"]):
            source = np.asarray(Image.open(figures["images"][index]["image"]["path"]))
            h, w, _ = source.shape
            np.testing.assert_array_equal(sheet[j * 212 : j * 212 + h, :w], source)
    assert len(figures["images"]) == 34 and len(figures["sheets"]) == 9
    assert channels == 10982400 and triplets == 1843200
    save(
        ROOT / "independent-figures-audit-v1.json",
        {
            "status": "pass",
            "figures": ref(ROOT / "figures-v1.json"),
            "auditor": ref(__file__),
            "images": 34,
            "sheets": 9,
            "direct_RGB_channels": channels,
            "triplet_RGB_channels": triplets,
            "all_RGB_channels_checked": channels + triplets,
            "JPEGs_native_not_exposure_boosted": True,
            "no_resize": True,
            "new_model_forwards": 0,
            "new_noise_draws": 0,
        },
    )
    print("PASS:", channels + triplets, "native RGB channels")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    main(p.parse_args().root.resolve())
