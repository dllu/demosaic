"""Rebuild saved flat metrics in Torch64 and verify native pixels without inference."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from audit_colored_flats import sha
from PIL import Image
from prepare_color_grid import SUITE, validate

from demosaic.cfa import malvar, mosaic
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def score(prediction, batch):
    p, t = [v[..., 48:208, 48:208].double() for v in [prediction, batch["target"]]]
    e = p - t
    mean = e.mean((0, 2, 3))
    mse = float(e.square().mean())
    cfa, truth = [mosaic(v, batch["colors"]) for v in [p, t]]
    measured = batch["packed"][..., 24:104, 24:104].double()
    return {
        "camera_RGB_mean_error": mean.tolist(),
        "camera_RGB_MSE": mse,
        "camera_RGB_mean_component_fraction": float(mean.square().mean()) / max(mse, 1e-24),
        "spatially_centered_camera_RGB_RMS": float(
            (e - mean[None, :, None, None]).square().mean().sqrt()
        ),
        "predicted_minus_GT_CFA_phase_mean": (cfa - truth).mean((0, 2, 3)).tolist(),
        "observed_minus_GT_CFA_phase_mean": (measured - truth).mean((0, 2, 3)).tolist(),
    }


@torch.inference_mode()
def main(report_path, output, extra_palettes):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    report = read(report_path)
    plan = read(report["plan"])
    assert sha(report["plan"]) == report["plan_sha256"]
    original = read(plan["inputs"])
    assert sha(plan["inputs"]) == plan["input_plan_sha256"]
    if original.get("suite") == SUITE:
        validate(original)
    else:
        assert len(original["cases"]) == 32
    assert plan["cases"] == original["cases"]
    assert plan["ROI_xywh"] == original["roi_xywh"] == [48, 48, 160, 160]
    output = writable_path(output)
    if output.exists():
        raise ValueError("Audit output exists; choose a new directory")
    arrays = {}
    predictions = {}
    errors = []
    fields = 0
    for i, c in enumerate(plan["cases"]):
        assert sha(c["arrays"]) == c["sha256"]
        with np.load(c["arrays"], allow_pickle=False) as v:
            batch = {k: torch.from_numpy(v[k].copy()) for k in v.files}
        assert batch["target"].shape == (1, 3, 256, 256) and batch["packed"].shape == (
            1,
            4,
            128,
            128,
        )
        assert all(torch.isfinite(v).all() for v in batch.values())
        arrays[i] = batch
    assert len(arrays) == len(original["cases"])
    for r in report["checkpoints"]:
        if r.get("kind", "joint-checkpoint") == "joint-checkpoint":
            assert sha(r["path"]) == r["sha256"]
        else:
            receipt = r["reference_receipt"]
            export = receipt["weights_only_export"]
            assert sha(export["path"]) == export["sha256"]
            for name, digest in receipt["source_receipts"].items():
                assert sha(Path(r["path"]) / name) == digest
    for item in report["float_predictions"]:
        assert sha(item["path"]) == item["sha256"]
        v = np.load(item["path"], allow_pickle=False)
        assert v.dtype == np.float32 and v.shape == (1, 3, 256, 256) and np.isfinite(v).all()
        key = item["model_index"], item["case"]
        assert key not in predictions
        predictions[key] = torch.from_numpy(v)
        row = next(r for r in report["results"] if (r["model_index"], r["case"]) == key)
        actual = score(predictions[key], arrays[item["case"]])
        assert actual.keys() == row["metrics"].keys()
        for name, value in actual.items():
            delta = float(np.max(np.abs(np.asarray(value) - np.asarray(row["metrics"][name]))))
            assert delta < 2e-14, (key, name, delta)
            errors.append(delta)
            fields += 1
    assert len(predictions) == len(report["results"]) == len(arrays) * len(report["checkpoints"])
    output.mkdir(parents=True, exist_ok=False)
    extra = []
    for model_index, model in enumerate(report["checkpoints"]):
        for palette in extra_palettes:
            index = next(
                i
                for i, c in enumerate(plan["cases"])
                if c["palette"] == palette
                and c["pattern"] == "RGGB"
                and c["condition"]["name"] == "iso12800-prior"
            )
            batch = arrays[index]
            noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
            p = predictions[model_index, index]
            extra.append(
                save_triplet(
                    output,
                    f"extra:{model_index}:{palette}",
                    [
                        (
                            label,
                            display_crop(rgb, batch["wb"], batch["matrix"], original["roi_xywh"]),
                        )
                        for label, rgb in [
                            ("Noisy (Malvar)", noisy),
                            ("Denoised", p),
                            ("GT (analytic)", batch["target"]),
                        ]
                    ],
                    caption=model["label"] + " / " + palette + " / saved arrays",
                    metadata={
                        "case": plan["cases"][index],
                        "model": model,
                        "ROI_xywh": original["roi_xywh"],
                        "white_balance": batch["wb"].tolist(),
                        "camera_to_srgb": batch["matrix"].tolist(),
                        "conditioning": plan["cases"][index]["condition"],
                        "display_exposure": 1.0,
                        "reference": "Exact uniform analytic target, not a real photograph.",
                    },
                )
            )
    native = []
    for root, crops in [(Path(report_path).parent, report["native_crops"]), (output, extra)]:
        for c in crops:
            p = root / c["image"]
            assert sha(p) == c["png_sha256"]
            case = c["case"]
            i = next(i for i, r in enumerate(plan["cases"]) if r == case)
            mi = next(i for i, r in enumerate(report["checkpoints"]) if r == c["model"])
            b = arrays[i]
            noisy = malvar(b["packed"], b["colors"], b["wb"])
            with Image.open(p) as im:
                assert im.size == (512, 192) and im.mode == "RGB"
                pixels = np.array(im)
            assert [r["png_xywh"] for r in c["panels"]] == [
                [8, 24, 160, 160],
                [176, 24, 160, 160],
                [344, 24, 160, 160],
            ]
            for x, rgb in zip([8, 176, 344], [noisy, predictions[mi, i], b["target"]]):
                desired = np.rint(
                    np.clip(display_crop(rgb, b["wb"], b["matrix"], original["roi_xywh"]), 0, 1)
                    * 255
                ).astype(np.uint8)
                np.testing.assert_array_equal(pixels[24:184, x : x + 160], desired)
            native.append(
                {"path": str(p), "sha256": sha(p), "all_three_native_panels_rerender_exact": True}
            )
    result = {
        "status": "completed-independent-saved-flat-Torch64-audit-and-native-rendering",
        "input_report": str(report_path),
        "input_report_sha256": sha(report_path),
        "observations": len(arrays),
        "float_predictions": len(predictions),
        "metric_fields": fields,
        "maximum_Torch64_vs_saved_NumPy64_metric_difference": max(errors),
        "native_panel_triplets": native,
        "additional_native_crops": extra,
        "CUDA_initialized": False,
        "driver_sha256": sha(__file__),
        "scope": "Saved observations/predictions only, no model inference or new draws. Native pixel reconstruction does not claim visual inspection; additional triplets still require viewing. The supplied finite color grid/one draw per case is not a broad photographic quality benchmark.",
    }
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "audit": str(output / "audit.json"),
                "metric_fields": fields,
                "max_delta": max(errors),
                "native_triplets": len(native),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--additional-palette", action="append", default=[])
    a = p.parse_args()
    main(a.report, a.output, a.additional_palette)
