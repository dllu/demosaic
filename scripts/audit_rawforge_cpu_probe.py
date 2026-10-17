"""Audit actual RawForge pilot ADC contracts, units, scores and native pixels."""

import argparse
import ast
import json
import math
from pathlib import Path

import numpy as np
import torch
from audit_colored_flats import sha
from PIL import Image

from demosaic.cfa import PATTERNS, malvar
from demosaic.color import render
from demosaic.reporting import display_crop
from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def main(report_path, output):
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    report = read(report_path)
    plan = read(report["plan"])
    assert sha(report["plan"]) == report["plan_sha256"]
    root = Path(report_path).parent
    assert sha(root / "probe_rawforge_cpu.py") == plan["driver_sha256"]
    assert sha(plan["inspection"]) == plan["inspection_sha256"]
    inspection = read(plan["inspection"])
    assert len(inspection["models"]) == 2 and not inspection["CUDA_initialized"]
    models = {m["name"]: m for m in inspection["models"]}
    cases = {c["id"]: c for c in plan["cases"]}
    assert len(cases) == 6 and len(report["arrays"]) == len(report["native_crops"]) == 12
    helper = plan["preprocessing_fixture"]["helper"]
    assert sha(helper) == plan["preprocessing_fixture"]["helper_sha256"]
    function = next(
        n
        for n in ast.parse(Path(helper).read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == "sparse_representation_and_mask"
    )
    ns = {"np": np}
    # Isolate the reviewed helper from the independently packaged upstream wheel.
    exec(compile(ast.Module(body=[function], type_ignores=[]), helper, "exec"), ns)  # noqa: S102
    upstream = ns[function.name]
    output = writable_path(output)
    if output.exists():
        raise ValueError("Pilot audit exists; choose a new output")
    normalization_delta, score_delta, adc_delta, images = [], [], [], []
    seen = set()
    for item in report["arrays"]:
        key = item["model"], item["case"]
        assert key not in seen
        seen.add(key)
        model, case = models[key[0]], cases[key[1]]
        assert sha(model["original"]) == model["original_sha256"]
        assert sha(model["CPU_port"]) == model["CPU_port_sha256"]
        assert sha(case["observation"]) == case["observation_sha256"]
        if case["kind"] == "synthetic-photo":
            with np.load(case["observation"], allow_pickle=False) as data:
                b = {k: torch.from_numpy(data[k].copy()) for k in data.files}
            wb, matrix, target = b["wb"], b["matrix"], b["target"]
        else:
            packed = np.load(case["observation"], allow_pickle=False)
            b = {
                "packed": torch.from_numpy(packed),
                "colors": torch.tensor([PATTERNS[case["pattern"]]]),
            }
            assert sha(case["reference_array"]) == case["reference_array_sha256"]
            wb = torch.tensor(case["wb"], dtype=torch.float32).reshape(1, 3)
            matrix = torch.tensor(case["matrix"], dtype=torch.float32).reshape(1, 3, 3)
            target = torch.from_numpy(np.load(case["reference_array"], allow_pickle=False))
        arrays = {}
        for name, f in item["files"].items():
            assert sha(f["path"]) == f["sha256"]
            v = np.load(f["path"], allow_pickle=False)
            assert v.dtype == np.float32 and list(v.shape) == f["shape"] and np.isfinite(v).all()
            arrays[name] = v
        packed = b["packed"].numpy().astype(np.float64)
        black = np.array(case["black"])[None, :, None, None]
        white = np.array(case["white"])[None, :, None, None]
        counts = np.round(packed * (white - black) + black)
        recovered = (counts - black) / (white - black)
        delta = float(np.abs(recovered - packed).max())
        assert delta < 1e-7
        adc_delta.append(delta)
        values = counts - black if model["registry"]["subtract_bl"] else counts
        # Interleave independently using a reshape/transpose, then use the
        # publisher's own sparse/mask function and F16 boundary conversion.
        _, _, h, w = values.shape
        cfa = values.reshape(2, 2, h, w).transpose(2, 0, 3, 1).reshape(2 * h, 2 * w)
        sparse, mask = upstream(cfa, np.array(PATTERNS[case["pattern"]]).reshape(2, 2).copy())
        expected_input = (
            np.concatenate([np.clip(sparse / case["adc_white"], 0, 1), mask])[None]
            .astype(np.float16)
            .astype(np.float32)
        )
        np.testing.assert_array_equal(arrays["input-six-f32"], expected_input)
        y, p = arrays["raw-network-f32"], arrays["normalized-RGB-f32"]
        assert y.shape == p.shape == (1, 3, 2 * h, 2 * w)
        black_mean = math.fsum(case["black"]) / (4 * case["adc_white"])
        expected = (
            np.clip(y.astype(np.float64), 0, 1)
            - (0 if model["registry"]["subtract_bl"] else black_mean)
        ) / (1 - black_mean)
        delta = float(np.abs(expected - p).max())
        assert delta < 2e-7
        normalization_delta.append(delta)
        x0, y0, side, _ = case["roi_xywh"]
        roi = torch.from_numpy(p[..., y0 : y0 + side, x0 : x0 + side])
        row = next(r for r in report["results"] if (r["model"], r["case"]) == key)
        if case["kind"] == "synthetic-photo":
            truth = target[..., y0 : y0 + side, x0 : x0 + side]
            for name, a, both in [
                ("linear_psnr", roi.clamp(0, 1), truth.clamp(0, 1)),
                ("srgb_psnr", render(roi, wb, matrix), render(truth, wb, matrix)),
            ]:
                error = a.numpy().astype(np.float64) - both.numpy().astype(np.float64)
                psnr = -10 * math.log10(max(float(np.square(error).mean()), 1e-12))
                delta = abs(psnr - row["metrics"][name])
                assert delta < 1e-5
                score_delta.append(delta)
        else:
            assert row["metrics"] is None
        crop = next(
            c
            for c in report["native_crops"]
            if c["case"]["id"] == key[1] and c["model"]["name"] == key[0]
        )
        image_path = root / crop["image"]
        assert (
            sha(image_path) == crop["png_sha256"] and read(image_path.with_suffix(".json")) == crop
        )
        with Image.open(image_path) as im:
            assert im.size == (512, 192) and im.mode == "RGB"
            pixels = np.array(im)
        desired = [malvar(b["packed"], b["colors"], wb), torch.from_numpy(p), target]
        for i, rgb in enumerate(desired):
            roi_xywh = (
                [0, 0, 160, 160]
                if i == 2 and case["kind"] != "synthetic-photo"
                else case["roi_xywh"]
            )
            display = display_crop(rgb, wb, matrix, roi_xywh, exposure=case["display_exposure"])
            native = np.rint(np.clip(display, 0, 1) * 255).astype(np.uint8)
            np.testing.assert_array_equal(native, pixels[24:184, 8 + 168 * i : 168 + 168 * i])
        old = (
            case["source"]["source_crop"]
            if case["kind"] == "synthetic-photo"
            else case["original_crop_receipt"]
        )
        old_root = Path(case["observation"]).parent
        with Image.open(old_root / old["image"]) as im:
            before = np.array(im)
        for x in [8, 344]:
            np.testing.assert_array_equal(pixels[24:184, x : x + 160], before[24:184, x : x + 160])
        images.append(
            {
                "path": str(image_path),
                "sha256": sha(image_path),
                "all3native_panels_rerender_exact": True,
                "noisy_reference_panels_exact_to_preexisting_method": True,
            }
        )
    assert seen == {(m, c) for m in models for c in cases} and len(score_delta) == 8
    assert not torch.cuda.is_initialized()
    result = {
        "status": "completed-RawForge-CPU-pilot-input-unit-score-native-audit",
        "report": str(report_path),
        "report_sha256": sha(report_path),
        "predictions": 12,
        "float_arrays": 36,
        "all12_inputs_bit_exact_to_publisher_sparse_mask_F16_contract": True,
        "maximum_ADC_reconstruction_error": max(adc_delta),
        "maximum_independent_nominal_unit_conversion_error": max(normalization_delta),
        "PSNR_scalar_checks": len(score_delta),
        "maximum_NumPy64_vs_Torch32_PSNR_difference": max(score_delta),
        "native_triplets": images,
        "CUDA_initialized": False,
        "driver_sha256": sha(__file__),
        "scope": "Exact declared observations and publisher preprocessing; per-phase physical input units retained, global mean black used for nominal output units as documented. PNG reconstruction and independent PSNR checks do not establish SSIM-definition independence, visual inspection, original CUDA parity or broad quality.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in result.items() if k not in ["native_triplets", "scope"]}),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.report, a.output)
