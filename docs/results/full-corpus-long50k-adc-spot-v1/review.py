"""Apply the retained calibrated ADC repair to the 50k native spot panel."""

from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from report_checkpoint_pilot import statistics
from report_scene_wave_guides import native_board

from demosaic.adc_bins import adc_bin_bounds, adc_bin_projection
from demosaic.archive_metrics import color, noisy_malvar
from demosaic.cfa import adc_cfa_projection, mosaic
from demosaic.experiments.artifacts import checked, read_json, reference, write_json

ROOT = Path(__file__).resolve().parent
SAVED = ROOT.parent / "full-corpus-long50k-native-queue-v1"
MODELS = ("V120", "scale-long50k")
CROPS = {
    "bark-contrast0p025-adc-RGGB",
    "raccoon-fur-contrast0p025-adc-RGGB",
    "flat-h030-s0.98-l0.90-BGGR",
    "flat-h030-s0.98-l0.90-RGGB",
}


@torch.inference_mode()
def review():
    torch.set_num_threads(2)
    plan_path, coll_path = SAVED / "plan.json", SAVED / "collection/result.json"
    native, coll = read_json(plan_path), read_json(coll_path)
    assert coll["plan"] == reference(plan_path)
    out = ROOT / "output"
    out.mkdir()
    grouped = defaultdict(list)
    rows, camera, boards = [], [], []
    for o, r in zip(native["observations"], coll["records"], strict=True):
        case = read_json(checked(r))
        assert o["id"] == case["id"]
        variants = {v["label"]: v for v in case["variants"]}
        kind = o["kind"]
        profile = {k: o["noise"][k] for k in ("shot", "read")}
        adc = profile["shot"] == profile["read"] == 0
        if not adc and kind not in ("gfx", "mesh"):
            continue
        with np.load(checked(o["arrays"])) as f:
            arrays = {k: f[k] for k in ("packed", "wb", "matrix", "colors")}
        packed, colors, wb = [torch.from_numpy(arrays[k]) for k in ("packed", "colors", "wb")]
        precision = "float32" if kind == "color-spot-check" else "float64"
        settings = {"bit_depth": 16, "black_level": 0.03, "quantizer_precision": precision}
        if not adc:
            for model in MODELS:
                prediction = torch.from_numpy(np.load(checked(variants[model]["prediction"])))
                corrected = adc_bin_projection(
                    prediction, packed, colors, wb, **settings, **profile
                )
                assert corrected is prediction
            camera.append({"id": o["id"], "models": MODELS, "bypassed": True})
            continue
        predictions = {}
        for model in MODELS:
            p = torch.from_numpy(np.load(checked(variants[model]["prediction"])))
            predictions[model] = {
                "raw": p,
                "Malvar": adc_cfa_projection(p, packed, colors, wb, mode="malvar"),
                "bins": adc_bin_projection(p, packed, colors, wb, **settings, **profile),
            }
        lo, hi = adc_bin_bounds(packed, **settings)
        with np.load(checked(o["target"])) as f:
            truth = f["target"]
        real = mosaic(torch.from_numpy(truth), colors)
        assert ((real >= lo) & (real <= hi)).all()
        for model, arms in predictions.items():
            actual = mosaic(arms["bins"], colors)
            original = mosaic(arms["raw"], colors)
            assert ((actual >= lo) & (actual <= hi)).all()
            assert (
                (actual.double() - real.double()).square()
                <= (original.double() - real.double()).square()
            ).all()
            for arm, pred in arms.items():
                category = "flat" if kind == "color-spot-check" else "faint"
                if category == "flat":
                    v = color(pred.numpy(), arrays | {"target": truth})
                    stats = {
                        "bias_DN16": 65535 * max(abs(x) for x in v["camera_RGB_mean_error"]),
                        "spatial_RMS_DN16": 65535 * v["spatially_centered_camera_RGB_RMS"],
                    }
                else:
                    v = statistics(pred.numpy(), truth, arrays)
                    stats = {
                        "faint_sRGB_PSNR": v["sRGB_PSNR"],
                        "fine_band_DN16": 65535
                        * next(b["band_error_RMS"] for b in v["bands"] if b["bin"] == 0),
                    }
                grouped[model, arm, category].append(stats)
                rows.append(
                    {
                        "id": o["id"],
                        "model": model,
                        "mode": arm,
                        "kind": category,
                        "prediction": variants[model]["prediction"],
                        "codec": precision,
                        **stats,
                    }
                )
        if o["id"] in CROPS:
            p = [v[0].numpy() for v in predictions["scale-long50k"].values()]
            boards.append(
                native_board(
                    out,
                    o["id"],
                    [noisy_malvar(arrays)[0], *p, truth[0]],
                    arrays,
                    {
                        "ROI_xywh": [48, 48, 160, 160],
                        "noise": o["noise"],
                        "code_precision": precision,
                        "checkpoint": native["models"]["scale-long50k"]["checkpoint"],
                        "input_arrays": o["arrays"],
                    },
                    labels=("Noisy Malvar", "50k EMA", "Exact MHC", "ADC bins", "Exact GT"),
                    triplet_indices=(0, 3, 4),
                    exposure=1,
                )
            )
    summary = []
    for (model, arm, category), group in grouped.items():
        assert len(group) == (8 if category == "flat" else 16)
        values = {
            k: float((max if category == "flat" else np.mean)([r[k] for r in group]))
            for k in group[0]
        }
        summary.append({"model": model, "mode": arm, "kind": category, **values})
    assert len(rows) == 144 and len(boards) == 4 and len(camera) == 6
    write_json(
        ROOT / "result.json",
        {
            "source": reference(__file__),
            "plan": reference(plan_path),
            "saved": reference(coll_path),
            "rows": rows,
            "summary": summary,
            "camera_bypass": camera,
            "boards": boards,
            "new_neural_calls": 0,
        },
    )
    for row in summary:
        print(row, flush=True)


if __name__ == "__main__":
    review()
