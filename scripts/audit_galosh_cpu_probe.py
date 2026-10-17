"""Audit the saved GALOSH wire format, metrics and native report panels."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from prepare_galosh_cpu import sha

from demosaic.cfa import PATTERNS, malvar
from demosaic.reporting import display_crop
from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def display64(rgb, wb, matrix):
    linear = torch.einsum(
        "bij,bjhw->bihw", matrix.double(), rgb.double() * wb.double()[..., None, None]
    ).clamp(0, 1)
    return torch.where(
        linear <= 0.0031308, 12.92 * linear, 1.055 * linear.clamp_min(1e-10).pow(1 / 2.4) - 0.055
    ).clamp(0, 1)


def main(report_path, output):
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    report = read(report_path)
    assert sha(report["plan"]) == report["plan_sha256"]
    plan = read(report["plan"])
    assert sha(plan["build"]) == plan["build_sha256"]
    built = read(plan["build"])
    assert built["binary"] == plan["binary"]
    assert sha(built["binary"]["path"]) == built["binary"]["sha256"]
    for path, digest in {
        **plan["source_files"],
        **built["official_sources"],
        **built["local_sources"],
    }.items():
        assert sha(path) == digest
    cases = {c["id"]: c for c in plan["cases"]}
    assert len(cases) == 6 and plan["modes"] == ["blind", "supplied-nominal"]
    assert len(report["arrays"]) == len(report["native_crops"]) == len(report["results"]) == 12
    errors, images, seen = [], [], set()
    for item in report["arrays"]:
        key = item["case"], item["mode"]
        assert key not in seen
        seen.add(key)
        case = cases[item["case"]]
        assert sha(case["observation"]) == case["observation_sha256"]
        if case["kind"] == "synthetic-photo":
            with np.load(case["observation"], allow_pickle=False) as values:
                data = {k: torch.from_numpy(values[k].copy()) for k in values.files}
            wb, matrix, target = data["wb"], data["matrix"], data["target"]
            nominal = case["source"]["source_crop"]["condition"]
        else:
            assert sha(case["reference_array"]) == case["reference_array_sha256"]
            data = {
                "packed": torch.from_numpy(np.load(case["observation"], allow_pickle=False)),
                "colors": torch.tensor([PATTERNS[case["pattern"]]]),
            }
            target = torch.from_numpy(np.load(case["reference_array"], allow_pickle=False))
            wb = torch.tensor(case["wb"], dtype=torch.float32).reshape(1, 3)
            matrix = torch.tensor(case["matrix"], dtype=torch.float32).reshape(1, 3, 3)
            nominal = {"shot": 0.0014635775921166604, "read": 0.0000010715704128646712}
        packed = data["packed"].numpy()
        _, _, h, w = packed.shape
        # Different layout construction from the writer's phase slicing.
        original = packed.reshape(2, 2, h, w).transpose(2, 0, 3, 1).reshape(2 * h, 2 * w)
        for name in ["input", "raw_output", "RGB"]:
            assert sha(item[name]["path"]) == item[name]["sha256"]
        expected = np.clip(original, 0, 1).astype("<f4")
        actual = np.fromfile(item["input"]["path"], dtype="<f4").reshape(2 * h, 2 * w)
        np.testing.assert_array_equal(actual, expected)
        assert item["input_clipping"] == {
            "below_zero_samples": int((original < 0).sum()),
            "above_one_samples": int((original > 1).sum()),
            "total_samples": original.size,
        }
        raw = np.fromfile(item["raw_output"]["path"], dtype="<f4").reshape(2 * h, 2 * w)
        assert np.isfinite(raw).all()
        repacked = raw.reshape(h, 2, w, 2).transpose(1, 3, 0, 2).reshape(1, 4, h, w).copy()
        prediction = torch.from_numpy(np.load(item["RGB"]["path"], allow_pickle=False))
        assert (
            prediction.shape == (1, 3, 2 * h, 2 * w)
            and prediction.dtype == torch.float32
            and torch.isfinite(prediction).all()
        )
        assert torch.equal(prediction, malvar(torch.from_numpy(repacked), data["colors"], wb))
        shot, read_noise = (
            (0.0, 0.0) if item["mode"] == "blind" else (nominal["shot"], nominal["read"])
        )
        assert item["command"] == [
            plan["binary"]["path"],
            item["input"]["path"],
            item["raw_output"]["path"],
            str(2 * w),
            str(2 * h),
            "galosh",
            "1",
            "1",
            "1",
            str(shot),
            str(read_noise),
        ]
        row = next(r for r in report["results"] if (r["case"], r["mode"]) == key)
        roi = case["roi_xywh"]
        x, y, side, _ = roi
        if case["kind"] == "synthetic-photo":
            a, b = [
                value[..., y : y + side, x : x + side].double() for value in [prediction, target]
            ]
            for name, first, second in [
                ("camera_clipped_PSNR", a.clamp(0, 1), b.clamp(0, 1)),
                ("sRGB_PSNR", display64(a, wb, matrix), display64(b, wb, matrix)),
            ]:
                mse = float((first - second).square().mean())
                expected_psnr = -10 * math.log10(max(mse, 1e-12))
                error = abs(row["metrics"][name] - expected_psnr)
                assert error < 3e-5
                errors.append(error)
        else:
            assert row["metrics"] is None
        crop = next(
            c
            for c in report["native_crops"]
            if c["case"]["id"] == key[0] and c["conditioning"]["mode"] == key[1]
        )
        path = report_path.parent / crop["image"]
        assert sha(path) == crop["png_sha256"] and read(path.with_suffix(".json")) == crop
        assert (
            crop["method"]["binary"] == plan["binary"]
            and crop["display_exposure"] == case["display_exposure"]
        )
        with Image.open(path) as im:
            assert im.mode == "RGB" and im.size == (512, 192)
            pixels = np.array(im)
        noisy = malvar(data["packed"], data["colors"], wb)
        for index, rgb in enumerate([noisy, prediction, target]):
            area = [0, 0, 160, 160] if index == 2 and case["kind"] != "synthetic-photo" else roi
            displayed = display_crop(rgb, wb, matrix, area, exposure=case["display_exposure"])
            expected_pixels = np.rint(np.clip(displayed, 0, 1) * 255).astype(np.uint8)
            np.testing.assert_array_equal(
                pixels[24:184, 8 + 168 * index : 168 + 168 * index], expected_pixels
            )
        old = (
            case["source"]["source_crop"]
            if case["kind"] == "synthetic-photo"
            else case["original_crop_receipt"]
        )
        with Image.open(Path(case["observation"]).parent / old["image"]) as im:
            previous = np.array(im)
        for left in [8, 344]:
            np.testing.assert_array_equal(
                pixels[24:184, left : left + 160], previous[24:184, left : left + 160]
            )
        images.append(
            {
                "path": str(path),
                "sha256": sha(path),
                "all3native_panels_rerender_exact": True,
                "common_noisy_reference_pixels_exact_to_original": True,
            }
        )
    assert len(errors) == 8 and seen == {(c, m) for c in cases for m in plan["modes"]}
    assert not torch.cuda.is_initialized()
    output = writable_path(output)
    if output.exists():
        raise ValueError("Audit exists; inspect it or select a fresh output")
    output.mkdir(parents=True)
    result = {
        "status": "completed-independent-GALOSH-wire-array-metric-native-integrity-audit",
        "report": str(report_path),
        "report_sha256": sha(report_path),
        "observations": len(cases),
        "executions": len(seen),
        "C_float32_wire_inputs_independently_interleaved_exact": True,
        "clipping_counts_exact": True,
        "nominal_and_blind_command_contracts_exact": True,
        "saved_Bayer_to_Malvar_RGB_bitwise_exact": True,
        "independent_Torch64_metric_fields": len(errors),
        "maximum_PSNR_arithmetic_delta": max(errors),
        "PSNR_arithmetic_bound": 3e-5,
        "images": images,
        "driver_sha256": sha(__file__),
        "CUDA_initialized": False,
        "scope": "Independent layout/clipping/command contract and Torch64 metric arithmetic; saved Bayer-to-RGB and PNG rerenders use the declared production Malvar/render as an artifact check. No independent recreation of GALOSH, original x86/GPU parity, actual visual inspection, full-frame speed or quality promotion.",
    }
    (output / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "audit": str(output / "audit.json"),
                "PSNR_fields": len(errors),
                "PNG": len(images),
                "maximum_PSNR_delta": max(errors),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.report, args.output)
