"""Split a saved spectral innovation with GT, for diagnosis only; CPU only."""

import argparse
import copy
import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np
import psutil
import torch
from build_native_crop_board import build

from demosaic.cfa import PATTERNS, malvar
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path

MODES = {
    "full": "V89/full",
    "base": "V89/base",
    "unit": "V89/unit",
    "oracle_target": "ORACLE target term",
    "oracle_discrepancy": "ORACLE discrepancy term",
}


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def checked(item):
    assert ref(item["path"]) == item
    return Path(item["path"])


def sample(rgb, colors):
    return np.stack(
        [
            np.stack([rgb[i, c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(row)])
            for i, row in enumerate(colors)
        ]
    )


def mhc(packed, colors, wb):
    """Independent FP64 signed Malvar stencils, including WB and reflect borders."""
    packed = packed.astype(np.float64)
    wb = wb.astype(np.float64)
    batch, _, h, w = packed.shape
    raw = np.empty((batch, 2 * h, 2 * w), dtype=np.float64)
    labels = np.empty_like(raw, dtype=np.int64)
    for i in range(batch):
        for phase, color in enumerate(colors[i]):
            raw[i, phase // 2 :: 2, phase % 2 :: 2] = packed[i, phase] * wb[i, color]
            labels[i, phase // 2 :: 2, phase % 2 :: 2] = color
    padded = np.pad(raw, ((0, 0), (2, 2), (2, 2)), mode="reflect")

    def convolution(kernel):
        out = np.zeros_like(raw)
        for y, x in zip(*np.nonzero(kernel), strict=True):
            out += kernel[y, x] * padded[:, y : y + 2 * h, x : x + 2 * w]
        return out

    kg = (
        np.array(
            [
                [0, 0, -1, 0, 0],
                [0, 0, 2, 0, 0],
                [-1, 2, 4, 2, -1],
                [0, 0, 2, 0, 0],
                [0, 0, -1, 0, 0],
            ]
        )
        / 8
    )
    kh = (
        np.array(
            [
                [0, 0, 0.5, 0, 0],
                [0, -1, 0, -1, 0],
                [-1, 4, 5, 4, -1],
                [0, -1, 0, -1, 0],
                [0, 0, 0.5, 0, 0],
            ]
        )
        / 8
    )
    kd = (
        np.array(
            [
                [0, 0, -1.5, 0, 0],
                [0, 2, 0, 2, 0],
                [-1.5, 0, 6, 0, -1.5],
                [0, 2, 0, 2, 0],
                [0, 0, -1.5, 0, 0],
            ]
        )
        / 8
    )
    green, horizontal, vertical, diagonal = map(convolution, [kg, kh, kh.T, kd])
    channels = []
    parity = np.arange(2 * h)[None, :, None] % 2
    for color in [0, 1, 2]:
        if color == 1:
            value = green
        else:
            row = np.argmax(colors == color, axis=1)[:, None, None] // 2
            value = np.where(parity == row, horizontal, vertical)
            value = np.where(labels == 2 - color, diagonal, value)
        channels.append(np.where(labels == color, raw, value))
    return np.stack(channels, axis=1) / wb[..., None, None]


def correction(residual, mask, colors, wb):
    filtered = np.fft.irfft2(
        np.fft.rfft2(residual, norm="ortho") * mask,
        s=residual.shape[-2:],
        norm="ortho",
    )
    rgb = mhc(filtered, colors, wb)
    assert np.max(np.abs(sample(rgb, colors) - filtered)) < 1e-14
    return rgb


def render(rgb, wb, matrix):
    linear = np.einsum("bij,bjhw->bihw", matrix.astype(np.float64), rgb * wb[..., None, None]).clip(
        0, 1
    )
    return np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)


def psnr(prediction, target):
    mse = np.mean((prediction - target) ** 2, axis=(1, 2, 3))
    return -10 * np.log10(np.maximum(mse, 1e-12))


def preflight(root, plan):
    rows = []
    y, x = np.indices((8, 10), dtype=np.float64)
    fixtures = [np.full((4, 8, 10), 0.2), np.stack([0.01 * (x - 2 * y + c) for c in range(4)])]
    impulse = np.zeros((4, 8, 10))
    impulse[:, 3, 4] = [1, -0.5, 0.25, 1.5]
    fixtures.append(impulse)
    for pattern, phases in PATTERNS.items():
        colors = np.array([phases], dtype=np.int64)
        for wb_row in [[1.0, 1.0, 1.0], [2.0, 1.0, 1.5]]:
            wb = np.array([wb_row])
            for fixture in fixtures:
                raw = fixture[None]
                expected = mhc(raw, colors, wb)
                actual = malvar(
                    torch.tensor(raw, dtype=torch.float32),
                    torch.from_numpy(colors),
                    torch.tensor(wb, dtype=torch.float32),
                ).numpy()
                error = float(np.max(np.abs(expected - actual)))
                assert error < plan["MHC_FP32_replay_atol"]
                assert np.max(np.abs(sample(expected, colors) - raw)) < 1e-14
                rows.append({"pattern": pattern, "wb": wb_row, "max_abs_error": error})
    save(
        root / "preflight.json",
        {
            "status": "completed-independent-MHC-CPU-preflight",
            "driver": ref(__file__),
            "plan": ref(root / "plan.json"),
            "cases": rows,
            "CUDA_initialized": torch.cuda.is_initialized(),
        },
    )
    print({"status": "completed-CPU-preflight", "cases": len(rows)}, flush=True)


def prepare(root, plan):
    assert read(root / "preflight.json")["driver"] == plan["worker"]
    result = []
    boards = []
    for original in plan["photo_results"]:
        name = original["condition"]["name"]
        out = root / name
        out.mkdir()
        with np.load(checked(original["arrays"]), allow_pickle=False) as stored:
            a = {k: stored[k].copy() for k in stored.files}
        values = {k: a[k].astype(np.float64) for k in ["base", "target", "packed", "mask", "wb"]}
        colors = a["colors"]
        sampled_target = sample(values["target"], colors)
        target_term = correction(
            sampled_target - sample(values["base"], colors), values["mask"], colors, values["wb"]
        )
        discrepancy_term = correction(
            values["packed"] - sampled_target, values["mask"], colors, values["wb"]
        )
        together = target_term + discrepancy_term
        replay = float(np.max(np.abs(together - a["innovation"])))
        assert replay < plan["innovation_FP32_replay_atol"]
        unit_error = float(np.max(np.abs(values["base"] + together - a["unit"])))
        assert unit_error < plan["innovation_FP32_replay_atol"]
        a.update(
            target_term=target_term,
            discrepancy_term=discrepancy_term,
            oracle_target=values["base"] + target_term,
            oracle_discrepancy=values["base"] + discrepancy_term,
        )
        assert all(np.isfinite(value).all() for value in a.values())
        np.savez_compressed(out / "arrays.npz", **a)
        result.append(
            {
                "condition": name,
                "original_arrays": original["arrays"],
                "arrays": ref(out / "arrays.npz"),
                "innovation_replay_max_abs_error": replay,
                "unit_replay_max_abs_error": unit_error,
            }
        )
        if name in plan["native_conditions"]:
            template_path = (
                Path(plan["pilot_root"]) / "cuda-pilot" / ("photo-" + name) / "report.json"
            )
            templates = read(template_path)["native_crops"][:2]
            crops = []
            for mode, label in MODES.items():
                for i, template in enumerate(templates):
                    metadata = {
                        k: copy.deepcopy(v)
                        for k, v in template.items()
                        if k
                        not in [
                            "image",
                            "caption",
                            "pixel_scale",
                            "display_encoding",
                            "panels",
                            "png_sha256",
                            "model_label",
                        ]
                    }
                    metadata.update(
                        model_label=label,
                        reference="Exact synthetic target. ORACLE rows use GT inside a diagnostic decomposition and cannot be used as inference methods.",
                        diagnostic_definitions=plan["definitions"],
                        compute_precision="Saved learned outputs FP32; independent component math FP64; common crop display original CPU FP32",
                    )
                    panels = [
                        (
                            p,
                            display_crop(
                                torch.tensor(v[i : i + 1], dtype=torch.float32),
                                torch.from_numpy(a["wb"][i : i + 1]),
                                torch.from_numpy(a["matrix"][i : i + 1]),
                                [48, 48, 160, 160],
                            ),
                        )
                        for p, v in [
                            ("Noisy (Malvar)", a["noisy"]),
                            (label, a[mode]),
                            ("GT (synthetic)", a["target"]),
                        ]
                    ]
                    crops.append(
                        save_triplet(
                            out,
                            template["source_id"] + ":" + mode,
                            panels,
                            caption=name + " / " + label,
                            metadata=metadata,
                        )
                    )
            save(out / "report.json", {"native_crops": crops, "scope": plan["scope"]})
            board = build([out / "report.json"], out / "native.png", "synthetic")
            boards.append(
                {
                    "condition": name,
                    "board": board["board"],
                    "receipt": ref(out / "native.json"),
                    "cells": board["native_cells_exact"],
                    "triplets": len(board["source_triplets"]),
                }
            )
        print({"event": "prepared-fixed-decomposition", "condition": name}, flush=True)
    save(
        root / "preparation.json",
        {
            "status": "prepared-fixed-innovation-splits-awaiting-native-view",
            "driver": ref(__file__),
            "plan": ref(root / "plan.json"),
            "results": result,
            "boards": boards,
            "new_quality_statistics_computed": False,
        },
    )


def score(root, plan):
    review = read(root / "manual-review-before-statistics.json")
    assert (
        review["all_boards_actually_viewed"] is True and review["statistics_interpreted"] is False
    )
    prepared = read(checked(review["preparation"]))
    assert review["boards"] == prepared["boards"]
    rows, witnesses, max_closure = [], [], 0.0
    for result, original in zip(prepared["results"], plan["photo_results"], strict=True):
        name = result["condition"]
        with np.load(checked(result["arrays"]), allow_pickle=False) as stored:
            a = {k: stored[k].astype(np.float64) for k in stored.files}
        source_ids = list(dict.fromkeys(c["source_id"] for c in original["cases"]))
        for region, roi in [("evaluation240", [8, 8, 240, 240]), ("native160", [48, 48, 160, 160])]:
            x, y, w, h = roi
            crop = lambda v, x=x, y=y, w=w, h=h: v[..., y : y + h, x : x + w]
            e = crop(a["base"] - a["target"])
            s, d = crop(a["target_term"]), crop(a["discrepancy_term"])
            mean = lambda v: v.mean((1, 2, 3))
            terms = {
                "base_MSE": mean(e**2),
                "target_component_MSE_change": 2 * mean(e * s) + mean(s**2),
                "discrepancy_component_MSE_change_alone": 2 * mean(e * d) + mean(d**2),
                "component_cross_term": 2 * mean(s * d),
                "target_component_energy": mean(s**2),
                "discrepancy_component_energy": mean(d**2),
                "discrepancy_increment_after_target": 2 * mean((e + s) * d) + mean(d**2),
                "decomposed_unit_MSE": mean((e + s + d) ** 2),
            }
            algebra = (
                terms["base_MSE"]
                + terms["target_component_MSE_change"]
                + terms["discrepancy_component_MSE_change_alone"]
                + terms["component_cross_term"]
            )
            closure = float(np.max(np.abs(algebra - terms["decomposed_unit_MSE"])))
            max_closure = max(max_closure, closure)
            assert closure < 1e-12
            metrics = {}
            for mode in MODES:
                p, t = crop(a[mode]), crop(a["target"])
                metrics[mode] = {
                    "unclipped_camera_MSE": mean((p - t) ** 2),
                    "linear_psnr": psnr(p.clip(0, 1), t.clip(0, 1)),
                    "srgb_psnr": psnr(
                        render(p, a["wb"], a["matrix"]), render(t, a["wb"], a["matrix"])
                    ),
                }
                if region == "evaluation240" and mode in ["full", "base", "unit"]:
                    for i, identity in enumerate(source_ids):
                        expected = next(
                            c["metrics"]
                            for c in original["cases"]
                            if c["source_id"] == identity and c["mode"] == mode
                        )
                        for key in ["linear_psnr", "srgb_psnr"]:
                            error = abs(float(metrics[mode][key][i]) - expected[key])
                            assert error < plan["PSNR_replay_atol"]
                            witnesses.append(error)
            for i, identity in enumerate(source_ids):
                rows.append(
                    {
                        "condition": name,
                        "source_id": identity,
                        "region": region,
                        "ROI_xywh": roi,
                        "MSE_terms": {k: float(v[i]) for k, v in terms.items()},
                        "metrics": {
                            m: {k: float(v[i]) for k, v in scores.items()}
                            for m, scores in metrics.items()
                        },
                    }
                )
    save(
        root / "scores.json",
        {
            "status": "completed-conditional-GT-innovation-split-diagnostic",
            "driver": ref(__file__),
            "plan": ref(root / "plan.json"),
            "preparation": ref(root / "preparation.json"),
            "manual_review": ref(root / "manual-review-before-statistics.json"),
            "original_PSNR_witnesses": len(witnesses),
            "original_PSNR_max_abs_error": max(witnesses),
            "MSE_algebra_max_abs_error": max_closure,
            "rows": rows,
            "scope": plan["scope"],
        },
    )
    print(
        {
            "status": "completed-GT-innovation-split-scoring",
            "rows": len(rows),
            "original_PSNR_witnesses": len(witnesses),
        },
        flush=True,
    )


def main(plan_path, phase):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    plan = read(plan_path)
    root = writable_path(plan["root"])
    assert root / "plan.json" == plan_path.resolve()
    assert ref(__file__) == plan["worker"]
    assert psutil.virtual_memory().available > 24 * 2**30
    assert shutil.disk_usage(root).free > 500 * 2**30
    assert shutil.disk_usage(Path.cwd()).free > 64 * 2**30
    for item in plan["inputs"]:
        checked(item)
    rng = torch.get_rng_state().clone()
    with torch.inference_mode():
        {"preflight": preflight, "prepare": prepare, "score": score}[phase](root, plan)
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--phase", choices=["preflight", "prepare", "score"], required=True)
    args = parser.parse_args()
    main(args.plan, args.phase)
