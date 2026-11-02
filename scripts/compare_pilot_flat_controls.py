"""Compare an unchanged exact-flat panel with an additional retained control."""

import argparse
from pathlib import Path

import numpy as np
from audit_pilot_flat_safety import reductions
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_pilot_flat_safety import spatial_metrics
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar


def compare(candidate, control, output):
    plans = [read(p / "plan-v1.json") for p in (candidate, control)]
    for plan in plans:
        guard(plan)
    assert plans[0]["observations"] == plans[1]["observations"]
    predictions = []
    for root, plan in zip((candidate, control), plans, strict=True):
        collection = read(root / "collection-v1.json")
        assert collection["plan"] == ref(root / "plan-v1.json")
        assert collection["counts"] == {"root": 48, "encoder": 48}
        predictions.append({r["id"]: r["prediction"] for r in collection["observations"]})
    output.mkdir(parents=True, exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    rows, images = [], []
    max_error = channels = 0

    def load(binding):
        assert ref(binding["path"]) == binding
        return np.load(binding["path"], allow_pickle=False)

    for observation in plans[0]["observations"]:
        with load(observation["arrays"]) as archive:
            arrays = {k: archive[k] for k in archive.files}
        values = [
            ("V120", load(observation["control"])),
            (plans[1]["model_label"], load(predictions[1][observation["id"]])),
            (plans[0]["model_label"], load(predictions[0][observation["id"]])),
        ]
        target = arrays["target"].astype(np.float64)
        for label, value in values:
            error = (value.astype(np.float64) - target)[..., 48:208, 48:208]
            measured, independent = spatial_metrics(error), reductions(error)
            for key in ("DC_RGB", "MSE", "DC_MSE", "spatial_MSE"):
                delta = float(np.max(np.abs(np.asarray(measured[key]) - independent[key])))
                max_error = max(max_error, delta)
                np.testing.assert_allclose(measured[key], independent[key], rtol=1e-10, atol=1e-16)
            for side in ("1", "4", "16", "32"):
                a, b = measured["block_RMS"][side], independent["block_RMS"][side]
                max_error = max(max_error, abs(a - b))
                np.testing.assert_allclose(a, b, rtol=1e-10, atol=1e-16)
            rows.append(
                {"id": observation["id"], "case": observation["case"], "method": label, **measured}
            )
        case = observation["case"]
        if case["pattern"] != "RGGB" or case["condition"]["name"] != "iso12800-prior":
            continue
        cells = [("Noisy Malvar", noisy_malvar(arrays)), *values, ("GT (analytic flat)", target)]
        canvas = Image.new("RGB", (8 + 168 * len(cells), 192), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        for i, (label, value) in enumerate(cells):
            draw.text((8 + 168 * i, 5), label, fill="black", font=font)
            canvas.paste(
                Image.fromarray(pixels(value, arrays, [48, 48, 160, 160], 1)), (8 + 168 * i, 24)
            )
        path = output / (case["id"] + "-three-method-flat.png")
        canvas.save(path)
        saved = np.asarray(Image.open(path))
        from audit_checkpoint_pilot import crop

        for i, (_, value) in enumerate(cells):
            cell = crop(value, arrays, [48, 48, 160, 160], 1)
            np.testing.assert_array_equal(saved[24:184, 8 + 168 * i : 168 + 168 * i], cell)
            channels += cell.size
        images.append(
            {
                "image": ref(path),
                "case": case,
                "ROI_xywh": [48, 48, 160, 160],
                "display_exposure": 1,
                "no_resize": True,
                "methods": [label for label, _ in cells],
            }
        )
    summary = []
    for condition in ("adc-only", "iso12800-prior"):
        for label in ("V120", plans[1]["model_label"], plans[0]["model_label"]):
            selected = [
                r
                for r in rows
                if r["method"] == label and r["case"]["condition"]["name"] == condition
            ]
            assert len(selected) == 24
            summary.append(
                {
                    "method": label,
                    "condition": condition,
                    "mean_spatial_RMS_DN16": float(
                        np.mean([r["spatial_MSE"] ** 0.5 * 65535 for r in selected])
                    ),
                    "mean_block32_RMS_DN16": float(
                        np.mean([r["block_RMS"]["32"] * 65535 for r in selected])
                    ),
                    "max_abs_DC_DN16": max(
                        max(abs(x) for x in r["DC_RGB"]) * 65535 for r in selected
                    ),
                }
            )
    assert len(rows) == 144 and len(images) == 6 and channels == 2304000
    save(
        output / "result-v1.json",
        {
            "status": "scored-and-independently-audited-same48-flat-control-comparison",
            "plans": [ref(root / "plan-v1.json") for root in (candidate, control)],
            "checkpoints": [p["checkpoint"] for p in plans],
            "operator": ref(__file__),
            "rows": rows,
            "summary": summary,
            "images": images,
            "independent_maximum_metric_difference": max_error,
            "PNG_channels_exact": channels,
            "new_neural_calls_in_report": 0,
            "scope": "Same48 exact fields, all3 methods, shared native160 ROI/display. "
            "V129 controls were newly collected separately; V120 and candidate predictions reused. "
            "One draw per color/condition/CFA, not photographic quality or universal flat safety.",
        },
    )
    print(summary)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("candidate", type=Path)
    p.add_argument("control", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    compare(args.candidate, args.control, args.output)
