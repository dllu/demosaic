"""Independent norms, signed colour dot products/cross products and native pixels."""

import argparse
import sys
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import crop
from PIL import Image

from demosaic.archive_metrics import noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def audit(root):
    assert "torch" not in sys.modules
    assert read_json(root / "comparison-result.json")["all_corrections_closed"]
    plan = read_json(root / "plan.json")
    scores = read_json(root / "scores-v1.json")
    rows = {(r["profile"], r["source"], r["pattern"], r["method"]): r for r in scores["rows"]}
    assert len(rows) == len(scores["rows"]) == 400
    parents = {
        r["group"]: r["parent"] for r in read_json(root / "parents-collection.json")["groups"]
    }
    variants = {
        v["name"]: {r["id"]: r for r in read_json(Path(v["root"]) / "collection.json")["rows"]}
        for v in read_json(root / "comparison-plan.json")["variants"]
    }
    report = read_json(root / "native/report.json")
    maximum = 0.0
    fields = channels = 0
    for group in plan["groups"]:
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            truth = z["target"].astype(np.float64)
            masks = {k: z[k] for k in ["quiet", "edge_band"]}
            physical = {k: z[k][2:3] for k in ["packed", "colors", "wb", "matrix"]}
        values = {"V120": np.load(checked(parents[group["id"]]))}
        for name, cases in variants.items():
            for method in cases[group["cases"][0]]["predictions"]:
                values[name + "::" + method] = np.stack(
                    [np.load(checked(cases[c]["predictions"][method])) for c in group["cases"]]
                )
        for method, value in values.items():
            value = value.astype(np.float64)
            error = value - truth
            expected = {
                "full_error_RMS_DN16": float(
                    np.linalg.norm(error.ravel()) / np.sqrt(error.size) * 65535
                )
            }
            for name, mask in [("quiet", masks["quiet"]), ("edge", masks["edge_band"])]:
                selected = error[..., mask]
                dc = selected.mean(axis=-1, keepdims=True)
                expected[name + "_error_RMS_DN16"] = float(
                    np.linalg.norm(selected.ravel()) / np.sqrt(selected.size) * 65535
                )
                expected[name + "_DC_RMS_DN16"] = float(
                    np.linalg.norm(dc.ravel()) / np.sqrt(dc.size) * 65535
                )
                expected[name + "_spatial_RMS_DN16"] = float(
                    np.linalg.norm((selected - dc).ravel()) / np.sqrt(selected.size) * 65535
                )
            for name, first, second in [("strong", 0, 1), ("weak", 1, 2)]:
                delta, predicted = truth[second] - truth[first], value[second] - value[first]
                gain = float(
                    np.dot(delta.ravel(), predicted.ravel()) / np.dot(delta.ravel(), delta.ravel())
                )
                expected[name + "_gain"] = gain
                expected[name + "_increment_error_RMS_DN16"] = float(
                    np.linalg.norm((predicted - delta).ravel()) / np.sqrt(delta.size) * 65535
                )
                expected[name + "_orthogonal_RMS_DN16"] = float(
                    np.linalg.norm((predicted - gain * delta).ravel()) / np.sqrt(delta.size) * 65535
                )
                colour = delta.reshape(3, -1).sum(axis=1)
                colour /= np.sqrt(np.dot(colour, colour))
                cross = np.cross(predicted.transpose(1, 2, 0), colour)
                expected[name + "_colour_orthogonal_RMS_DN16"] = float(
                    np.linalg.norm(cross.ravel()) / np.sqrt(predicted.size) * 65535
                )
                for c, label in enumerate("RGB"):
                    expected[name + "_" + label + "_gain"] = float(
                        np.dot(predicted[c].ravel(), delta[c].ravel())
                        / np.dot(delta[c].ravel(), delta[c].ravel())
                    )
            recorded = rows[group["profile"], group["source"], group["pattern"], method]
            assert expected.keys() <= recorded.keys()
            for key, expected_value in expected.items():
                maximum = max(maximum, abs(expected_value - recorded[key]))
                fields += 1
        noisy = noisy_malvar(physical)
        for figure in report["figures"]:
            if figure["group"]["id"] != group["id"]:
                continue
            png = np.asarray(Image.open(checked(figure["image"])))
            for panel in figure["panels"]:
                key = panel["method"]
                value = (
                    noisy
                    if key == "Noisy Malvar"
                    else truth[2:3]
                    if key == "Exact GT"
                    else values[key][2:3]
                )
                encoded = crop(value, physical, figure["ROI_xywh"], figure["display_exposure"])
                x, y, w, h = panel["xywh"]
                np.testing.assert_array_equal(encoded, png[y : y + h, x : x + w])
                channels += encoded.size
    assert maximum < 1e-9 and channels == report["RGB_crop_channels_exact"] == 19046400
    assert "torch" not in sys.modules
    write_json(
        root / "independent-audit-v1.json",
        {
            "script": reference(__file__),
            "scores": reference(root / "scores-v1.json"),
            "report": reference(root / "native/report.json"),
            "metric_rows": 400,
            "fields_checked": fields,
            "maximum_absolute_error": maximum,
            "native_RGB_channels_exact": channels,
            "native_figures": 40,
            "Torch_imported": False,
            "new_neural_forwards": 0,
            "scope": "Independent L2 norms/dot products and colour cross-product residuals over all400 rows; all40 native boards/triplets reread against actual predictions/targets/calibration. No producer scoring/display helper used. Actual viewing/publication still required.",
        },
    )
    print(fields, "independent fields; maximum error", maximum, "; native channels", channels)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    audit(parser.parse_args().root)
