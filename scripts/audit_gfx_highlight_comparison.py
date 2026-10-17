"""Audit cached-input GFX comparison float outputs and native triplet pixels."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from audit_gfx_highlight_inputs import display64
from PIL import Image
from prepare_gfx_highlight_inputs import read, sha

from demosaic.safety import writable_path


def main(report, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    result = read(report)
    assert (
        result["status"]
        == "completed-GFX-highlight-CPU-comparison-awaiting-artifact-and-native-review"
    )
    assert result["quality_scores"] is None and result["CUDA_initialized"] is False
    assert sha(result["plan"]) == result["plan_sha256"]
    execution = read(result["plan"])
    assert sha(execution["inputs"]) == execution["inputs_sha256"]
    assert sha(execution["input_audit"]) == execution["input_audit_sha256"]
    inputs = read(execution["inputs"])
    input_audit = read(execution["input_audit"])
    assert input_audit["inputs_sha256"] == execution["inputs_sha256"]
    assert len(inputs["cases"]) == 2
    for path, digest in execution["source_files"].items():
        assert sha(path) == digest
    for record in result["checkpoints"]:
        if record["kind"] == "checkpoint":
            assert sha(record["path"]) == record["sha256"]
        else:
            assert record["kind"] == "RawNIND:CFA-channel" and record["clip_input"] is False
            assert sha(Path(record["path"]) / "utnet2-bayer.pt") == record["sha256"]
            assert sha(record["source"]) == record["source_sha256"]
    count = len(result["checkpoints"])
    expected_keys = {(model, case) for model in range(count) for case in range(2)}
    predictions = {(v["model_index"], v["case_index"]): v for v in result["float_predictions"]}
    crops = {(v["model_index"], v["case_index"]): v for v in result["native_crops"]}
    assert (
        len(predictions)
        == len(crops)
        == len(result["float_predictions"])
        == len(result["native_crops"])
        == count * 2
    )
    assert predictions.keys() == crops.keys() == expected_keys
    checks = []
    for (model_index, case_index), record in predictions.items():
        case = inputs["cases"][case_index]
        assert sha(case["arrays"]) == case["sha256"]
        with np.load(case["arrays"], allow_pickle=False) as loaded:
            arrays = {key: loaded[key].copy() for key in loaded.files}
        assert sha(record["path"]) == record["sha256"]
        prediction = np.load(record["path"], allow_pickle=False)
        assert prediction.dtype == np.float32 and list(prediction.shape) == record["shape"] == [
            1,
            3,
            512,
            512,
        ]
        assert np.isfinite(prediction).all()
        crop = crops[model_index, case_index]
        assert crop["region"] == case["region"] and crop["ROI_xywh"] == case["ROI_xywh"]
        assert crop["context_xywh"] == case["context_xywh"]
        assert crop["conditioning"] == inputs["conditioning"]
        assert crop["display_exposure"] == inputs["display_exposure"] == 4
        assert (
            crop["checkpoint_sha256"]
            == crop["model"]["sha256"]
            == result["checkpoints"][model_index]["sha256"]
        )
        path = report.parent / crop["image"]
        assert sha(path) == crop["png_sha256"] and read(path.with_suffix(".json")) == crop
        pixels = np.array(Image.open(path).convert("RGB"))
        assert pixels.shape == (192, 512, 3) and len(crop["panels"]) == 3
        differences = []
        for panel_index, panel in enumerate(crop["panels"]):
            x, y, w, h = panel["png_xywh"]
            assert [x, y, w, h] == [8 + panel_index * 168, 24, 160, 160]
            observed = pixels[y : y + h, x : x + w]
            if panel_index in [0, 2]:
                preview = case["previews"][0 if panel_index == 0 else 1]
                assert sha(preview["path"]) == preview["sha256"]
                assert np.array_equal(
                    observed, np.array(Image.open(preview["path"]).convert("RGB"))
                )
            px, py, pw, ph = case["ROI_xywh"]
            rgb = [
                arrays["noisy_rgb"][..., py : py + ph, px : px + pw],
                prediction[..., py : py + ph, px : px + pw],
                arrays["reference_rgb"],
            ][panel_index]
            expected = display64(rgb, arrays["wb"], arrays["matrix"], inputs["display_exposure"])
            difference = np.abs(observed.astype(np.int16) - expected.astype(np.int16))
            assert difference.max() <= 1
            differences.append(
                {
                    "panel": panel_index,
                    "channel_values": int(difference.size),
                    "changed_values": int(np.count_nonzero(difference)),
                    "maximum8bit_difference": int(difference.max()),
                }
            )
        checks.append(
            {
                "model_index": model_index,
                "case_index": case_index,
                "prediction_shape_dtype_finite": True,
                "noisy_and_reference_pixels_bitwise_inputs": True,
                "native_PNG_panels": differences,
            }
        )
    audit = {
        "status": "completed-independent-GFX-highlight-CPU-comparison-integrity-audit",
        "report": str(report),
        "report_sha256": sha(report),
        "float_predictions": len(predictions),
        "native_triplets": len(crops),
        "cases": checks,
        "CUDA_initialized": False,
        "driver_sha256": sha(__file__),
        "scope": "Saved float output and native display integrity only. Independent64 camera/display transform within predeclared1-code PNG rounding bound; common noisy/reference pixels exact. No reference scores, trained quality or actual visual review inferred from this audit.",
    }
    output = writable_path(output)
    assert not output.exists()
    output.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    (output.parent / "source" / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"audit": str(output), "triplets": len(crops)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
