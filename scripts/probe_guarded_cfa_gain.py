"""Fixed CPU pilot: guarded photometry on saved GFX, color grid and GT photos."""

import argparse
import copy
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from guarded_cfa_gain import (
    POLICY,
    apply_gain,
    correct,
    fit_terms,
    numpy_apply,
    numpy_solve,
    numpy_terms,
    solve,
)
from PIL import Image
from probe_saved_cfa_gain_grid import read, ref

from demosaic.cfa import PATTERNS, malvar, mosaic
from demosaic.data import camera_pair
from demosaic.metrics import quality_metrics
from demosaic.reporting import display_crop, save_triplet


def batch(path):
    with np.load(path, allow_pickle=False) as values:
        return {k: values[k].copy() for k in values.files}


def checked_correction(prediction, arrays):
    t = {k: torch.from_numpy(v) for k, v in arrays.items()}
    output, gain, terms = correct(
        torch.from_numpy(prediction),
        *(t[k] for k in ["packed", "variance", "colors", "wb", "matrix"]),
    )
    oracle = numpy_terms(
        prediction, *(arrays[k] for k in ["packed", "variance", "colors", "wb", "matrix"])
    )
    np.testing.assert_array_equal(terms["count"].numpy(), oracle["count"])
    for key in ["numerator", "denominator"]:
        np.testing.assert_allclose(terms[key].numpy(), oracle[key], rtol=2e-12, atol=2e-12)
    ng = numpy_solve(oracle)
    np.testing.assert_allclose(gain.numpy(), ng, rtol=2e-12, atol=2e-12)
    expected = numpy_apply(prediction, ng, arrays["wb"], arrays["matrix"])
    error = float(np.max(np.abs(expected - output.numpy())))
    assert error <= 2e-7 and torch.isfinite(output).all()
    return output.numpy(), gain.numpy(), {k: v.tolist() for k, v in terms.items()}, error


def perfect_target_oracle():
    from probe_saved_cfa_gain_grid import channel_gain

    image = torch.full((1, 3, 64, 64), 0.2)
    image[..., :32] = torch.tensor([3.6, 1.8, 0.9])[None, :, None, None]
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    matrix = torch.tensor(
        [
            [
                [1.117647, -0.0588235, -0.0588235],
                [-0.0588235, 1.117647, -0.0588235],
                [-0.0588235, -0.0588235, 1.117647],
            ]
        ]
    )
    clean, target = camera_pair(image, torch.linalg.inv(matrix), wb, reconstruct_highlights=True)
    rows = []
    for pattern, labels in PATTERNS.items():
        colors = torch.tensor(labels)[None]
        packed = mosaic(clean.clamp(0, 1), colors)
        old, g0 = channel_gain(target, packed, colors)
        guarded, g1, terms = correct(target, packed, torch.zeros_like(packed), colors, wb, matrix)
        assert torch.equal(guarded, target)
        rows.append(
            {
                "pattern": pattern,
                "unmasked_MSE_from_perfect_target": float((old - target).square().mean()),
                "guarded_MSE_from_perfect_target": 0.0,
                "unmasked_gains": g0.tolist()[0],
                "guarded_gains": g1.tolist()[0],
                "guarded_fit_counts": terms["count"].tolist()[0],
            }
        )
    return {
        "scope": "Analytical target-compatibility oracle, not learned-model performance. Prediction deliberately equals exact reference-white target; observation is ideal noiseless ADC-clipped exposed CFA. This establishes a target/input conflict, not its contribution to real neural errors.",
        "cases": rows,
    }


def gfx(plan, output):
    fixture = read(plan["fixture"]["path"])
    wb = torch.tensor(fixture["gfx_metadata"]["white_balance"])[None]
    matrix = torch.tensor(fixture["gfx_metadata"]["camera_to_srgb"])[None]
    colors = torch.tensor(PATTERNS[fixture["gfx_metadata"]["pattern"]])[None]
    rgb = np.load(plan["full_RGB"]["path"], mmap_mode="r", allow_pickle=False)
    raw = np.load(plan["full_raw"]["path"], mmap_mode="r", allow_pickle=False)
    assert rgb.shape == (3, 8746, 11662) and raw.shape == (8746, 11662)
    collected = {k: [[] for _ in range(3)] for k in ["numerator", "denominator", "count"]}
    independent = {k: [[] for _ in range(3)] for k in collected}
    shot, readvar = fixture["conditioning"]["shot"], fixture["conditioning"]["read"]
    for y in range(0, raw.shape[0], 256):
        p = np.array(rgb[:, y : y + 256], copy=True)[None]
        packed = np.stack(
            [
                np.asarray(raw[y + dy : min(y + 256, raw.shape[0]) : 2, dx::2])
                for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]
            ]
        )[None]
        z = torch.from_numpy(packed)
        variance = z.clamp_min(0) * shot + readvar
        terms = fit_terms(torch.from_numpy(p), z, variance, colors, wb, matrix)
        oracle = numpy_terms(
            p, packed, variance.numpy(), colors.numpy(), wb.numpy(), matrix.numpy()
        )
        np.testing.assert_array_equal(terms["count"].numpy(), oracle["count"])
        for key in collected:
            for channel in range(3):
                collected[key][channel].append(float(terms[key][0, channel]))
                independent[key][channel].append(float(oracle[key][0, channel]))
    total = {
        k: torch.tensor(
            [[math.fsum(v) for v in values]], dtype=torch.int64 if k == "count" else torch.float64
        )
        for k, values in collected.items()
    }
    oracle = {
        k: np.array(
            [[math.fsum(v) for v in values]], dtype=np.int64 if k == "count" else np.float64
        )
        for k, values in independent.items()
    }
    gain = solve(total)
    np.testing.assert_allclose(gain.numpy(), numpy_solve(oracle), rtol=2e-12, atol=2e-12)
    for key in ["numerator", "denominator"]:
        np.testing.assert_allclose(total[key].numpy(), oracle[key], rtol=2e-12, atol=2e-12)
    values_checked = 0
    max_pixel_error = 0.0
    maximum_change = 0.0
    squared = []
    for y in range(0, raw.shape[0], 256):
        p = np.array(rgb[:, y : y + 256], copy=True)[None]
        changed = apply_gain(torch.from_numpy(p), gain, wb, matrix).numpy()
        expected = numpy_apply(p, numpy_solve(oracle), wb.numpy(), matrix.numpy())
        error = float(np.max(np.abs(expected - changed)))
        max_pixel_error = max(max_pixel_error, error)
        assert error <= 2e-7 and np.isfinite(changed).all()
        delta = changed.astype(np.float64) - p.astype(np.float64)
        maximum_change = max(maximum_change, float(np.abs(delta).max()))
        squared.append(float(np.square(delta).sum()))
        values_checked += delta.size
    assert values_checked == 305987556
    output.mkdir()
    source_report = Path(plan["full_native_report"]["path"])
    templates = [
        c
        for c in read(source_report)["native_crops"]
        if c["model_label"] == "V63-step20000:original-FP32"
    ]
    highlights = Path(plan["highlight_report"]["path"])
    templates += [
        c
        for c in read(highlights)["native_crops"]
        if c["checkpoint_sha256"] == plan["checkpoint_sha256"]
    ]
    assert len(templates) == 6
    crops = []
    for index, template in enumerate(templates):
        parent = source_report.parent if index < 4 else highlights.parent
        src = parent / template["image"]
        assert ref(src)["sha256"] == template["png_sha256"]
        pixels = np.array(Image.open(src))
        x, y = template["region"]["noisy_xy"]
        p = torch.from_numpy(np.array(rgb[:, y : y + 160, x : x + 160], copy=True))[None]
        changed = apply_gain(p, gain, wb, matrix)
        for label, prediction, g in [
            ("V63-parent-saved-full-FP32", p, [1.0, 1.0, 1.0]),
            ("V63-guarded-global-gain-v1", changed, gain.tolist()[0]),
        ]:

            def panel(i, pixels=pixels, template=template):
                a, b, w, h = template["panels"][i]["png_xywh"]
                return pixels[b : b + h, a : a + w].astype(np.float64) / 255

            metadata = {
                "region": copy.deepcopy(template["region"]),
                "context_xywh": None,
                "full_frame": True,
                "conditioning": fixture["conditioning"],
                "display_exposure": 4.0,
                "shared_wb": wb.tolist()[0],
                "shared_matrix": matrix.tolist()[0],
                "checkpoint_sha256": plan["checkpoint_sha256"],
                "model": {
                    "label": label,
                    "sha256": plan["checkpoint_sha256"],
                    "base_prediction": plan["full_RGB"],
                    "global_input_only_gains": g,
                    "policy": POLICY if label.startswith("V63-guarded") else None,
                },
                "source": {
                    "fixture": plan["fixture"],
                    "source_noisy_reference_triplet": ref(src),
                    "GFX_sources": fixture["gfx_sources"],
                },
                "reference": "Separate DSCF3880 ISO100 f/5.6 AHD reference, not GT; framing/time/aperture/motion differ",
            }
            crops.append(
                save_triplet(
                    output,
                    label + ":" + template["region"]["name"],
                    [
                        ("Noisy (Malvar)", panel(0)),
                        (
                            "Denoised",
                            display_crop(prediction, wb, matrix, [0, 0, 160, 160], exposure=4.0),
                        ),
                        ("ISO100 ref (not GT)", panel(2)),
                    ],
                    caption=template["region"]["name"] + " / " + label,
                    metadata=metadata,
                )
            )
    report = {
        "status": "completed-guarded-global-gain-CPU-probe-awaiting-native-review",
        "native_crops": crops,
        "gains": gain.tolist()[0],
        "fit_totals": {k: v.tolist()[0] for k, v in total.items()},
        "independent_fit_totals": {k: v.tolist()[0] for k, v in oracle.items()},
        "all_corrected_values_checked": values_checked,
        "maximum_independent_pixel_difference": max_pixel_error,
        "maximum_camera_RGB_change": maximum_change,
        "RMS_camera_RGB_change": math.sqrt(math.fsum(squared) / values_checked),
        "scope": "One global fit then continuous per-pixel reference-white taper on saved original full-frame output. No new model call/RAW decode/full corrected array/export/timing/GT fit.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return ref(output / "report.json")


def grid(plan, output):
    from audit_colored_flats import metrics
    from evaluate_color_grid_cuda import summarize
    from prepare_color_grid import validate

    inputs = read(plan["color_inputs"]["path"])
    validate(inputs)
    saved = read(plan["color_report"]["path"])
    audit = read(plan["color_audit"]["path"])
    assert audit["input_report_sha256"] == plan["color_report"]["sha256"]
    assert audit["observations"] == 1176 and audit["float_predictions"] == 3528
    old = read(saved["plan"])
    assert ref(saved["plan"])["sha256"] == saved["plan_sha256"]
    assert (
        old["input_plan_sha256"] == plan["color_inputs"]["sha256"]
        and old["cases"] == inputs["cases"]
    )
    mi = plan["color_model_index"]
    assert saved["checkpoints"][mi]["sha256"] == plan["checkpoint_sha256"]
    predictions = {v["case"]: v for v in saved["float_predictions"] if v["model_index"] == mi}
    old_metrics = {v["case"]: v["metrics"] for v in saved["results"] if v["model_index"] == mi}
    output.mkdir()
    rows = []
    fits = []
    crops = []
    max_pixel_error = 0.0
    for ci, case in enumerate(inputs["cases"]):
        assert ref(case["arrays"])["sha256"] == case["sha256"]
        item = predictions[ci]
        assert ref(item["path"])["sha256"] == item["sha256"]
        arrays = batch(case["arrays"])
        before = np.load(item["path"], allow_pickle=False)
        changed, gain, terms, error = checked_correction(before, arrays)
        max_pixel_error = max(max_pixel_error, error)
        for model_index, p in enumerate([before, changed]):
            m = metrics(p, arrays)
            if model_index == 0:
                assert m == old_metrics[ci]
            rows.append(
                {
                    "model_index": model_index,
                    "case": ci,
                    "palette": case["palette"],
                    "condition": case["condition"]["name"],
                    "pattern": case["pattern"],
                    "source": case["source"],
                    "metrics": m,
                }
            )
        fits.append(
            {"case": ci, "gains": gain.tolist()[0], "terms": terms, "oracle_pixel_error": error}
        )
        if (
            case["palette"] in plan["native_palettes"]
            and case["condition"]["name"] == "iso12800-prior"
            and case["pattern"] == "RGGB"
        ):
            t = {k: torch.from_numpy(v) for k, v in arrays.items()}
            noisy = malvar(t["packed"], t["colors"], t["wb"])
            for index, p in enumerate([before, changed]):
                label = ["V63-parent-saved", "V63-guarded-gain-v1"][index]
                crops.append(
                    save_triplet(
                        output,
                        label + ":" + case["id"],
                        [
                            (n, display_crop(v, t["wb"], t["matrix"], inputs["roi_xywh"]))
                            for n, v in [
                                ("Noisy (Malvar)", noisy),
                                ("Denoised", torch.from_numpy(p)),
                                ("GT (analytic)", t["target"]),
                            ]
                        ],
                        caption=case["id"] + " / " + label,
                        metadata={
                            "case": case,
                            "ROI_xywh": inputs["roi_xywh"],
                            "conditioning": case["condition"],
                            "white_balance": inputs["white_balance"],
                            "camera_to_srgb": inputs["camera_to_srgb"],
                            "display_exposure": 1.0,
                            "reference": "Exact uniform analytic target, not a real photograph",
                            "model": {
                                "label": label,
                                "sha256": plan["checkpoint_sha256"],
                                "base_prediction": item,
                                "gain": gain.tolist()[0] if index else [1, 1, 1],
                                "policy": POLICY if index else None,
                            },
                        },
                    )
                )
    assert len(rows) == 2352 and len(fits) == 1176 and len(crops) == 14
    report = {
        "status": "completed-guarded-color-grid-awaiting-native-and-screen-review",
        "results": rows,
        "fits": fits,
        "native_crops": crops,
        "group_summary": summarize(rows),
        "maximum_independent_pixel_difference": max_pixel_error,
        "scope": "All fixed1176 saved observations/unchanged parent predictions. No model load or new noise; target used only for scores after input-only fitting.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return ref(output / "report.json")


def photos(plan, output):
    fixture = read(plan["fixture"]["path"])
    output.mkdir()
    crops = []
    scores = []
    for i, record in enumerate(plan["photos"]):
        arrays = batch(record["observation"]["path"])
        before = np.load(record["RGB"]["path"], allow_pickle=False)
        changed, gain, terms, error = checked_correction(before, arrays)
        t = {k: torch.from_numpy(v) for k, v in arrays.items()}
        noisy = malvar(t["packed"], t["colors"], t["wb"])
        for index, p in enumerate([before, changed]):
            label = ["V63-parent-saved", "V63-guarded-gain-v1"][index]
            pixels = torch.from_numpy(p)
            metric = quality_metrics(
                pixels[..., 48:208, 48:208], t["target"][..., 48:208, 48:208], t["wb"], t["matrix"]
            )
            scores.append(
                {
                    "source_id": fixture["photos"][i]["metadata"]["source_id"],
                    "method": label,
                    "metrics": {
                        k: float(v[0]) if torch.isfinite(v[0]) else None for k, v in metric.items()
                    },
                }
            )
            metadata = copy.deepcopy(fixture["photos"][i]["metadata"])
            metadata.update(
                checkpoint_sha256=plan["checkpoint_sha256"],
                cache_context_xywh=record["cache_context_xywh"],
                cache_display_ROI_xywh=record["cache_display_ROI_xywh"],
                model={
                    "label": label,
                    "sha256": plan["checkpoint_sha256"],
                    "base_prediction": record["RGB"],
                    "gains": gain.tolist()[0] if index else [1, 1, 1],
                    "terms": terms if index else None,
                    "policy": POLICY if index else None,
                },
                noise_draw="Existing fixed CPU-generated observation; not the separate full427 CUDA realization",
            )
            crops.append(
                save_triplet(
                    output,
                    label + ":" + str(i),
                    [
                        (n, display_crop(v, t["wb"], t["matrix"], [48, 48, 160, 160]))
                        for n, v in [
                            ("Noisy (Malvar)", noisy),
                            ("Denoised", pixels),
                            ("GT (synthetic)", t["target"]),
                        ]
                    ],
                    caption=metadata["source_id"] + " / " + label,
                    metadata=metadata,
                )
            )
        assert error <= 2e-7
    report = {
        "status": "completed-two-fixed-guarded-GT-photos-awaiting-native-review",
        "native_crops": crops,
        "scores": scores,
        "scope": "Two selected fixed CPU-noise observations, saved genuine GPU-FP32 parent predictions; no new network/noise. Not full427 scores.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return ref(output / "report.json")


@torch.inference_mode()
def main(plan_path):
    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan = read(plan_path)
    root = Path(plan["root"])
    output = Path(plan["output"])
    assert ref(__file__) == plan["worker"] and plan["policy"] == POLICY
    for item in [*plan["source_files"], *plan["inputs_to_verify"]]:
        assert ref(item["path"]) == item
    assert (
        psutil.virtual_memory().available > 24 * 2**30
        and psutil.disk_usage(root).free > 128 * 2**30
    )
    with (root / "claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": [],
    }

    def record(state, **values):
        status.update(status=state, updated_unix=time.time(), **values)
        tmp = root / "status.tmp"
        tmp.write_text(json.dumps(status, indent=2) + "\n")
        tmp.replace(root / "status.json")
        print(json.dumps({"status": state}), flush=True)

    try:
        output.mkdir(parents=True, exist_ok=False)
        oracle = perfect_target_oracle()
        (output / "perfect-target-oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
        for name, fn in [("gfx", gfx), ("grid", grid), ("photos", photos)]:
            record("running-guarded-CPU-" + name)
            result = fn(plan, output / name)
            status["completed"].append({"stage": name, "result": result})
        assert not torch.cuda.is_initialized()
        for item in plan["source_files"]:
            assert ref(item["path"]) == item
        record(
            "completed-guarded-CPU-pilot-awaiting-native-review-and-fixed-screen",
            CUDA_initialized=False,
            actual_model_forwards=0,
        )
    except BaseException as error:
        record("failed-guarded-CPU-pilot-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
