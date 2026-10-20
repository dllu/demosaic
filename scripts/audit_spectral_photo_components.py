"""CPU NumPy audit of the fixed photo/GFX spectral intervention pilot."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def checked(item):
    assert ref(item["path"]) == item
    return Path(item["path"])


def fingerprint(values):
    h = hashlib.sha256()
    for name, value in sorted(values.items()):
        dtype = {"float32": "torch.float32", "int64": "torch.int64"}[value.dtype.name]
        h.update(name.encode() + dtype.encode() + str(tuple(value.shape)).encode())
        h.update(value.tobytes(order="C"))
    return h.hexdigest()


def render(rgb, wb, matrix):
    linear = np.einsum(
        "bij,bjhw->bihw", matrix.astype(np.float64), rgb.astype(np.float64) * wb[..., None, None]
    ).clip(0, 1)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)


def psnr(prediction, target):
    mse = np.mean((prediction - target) ** 2, axis=(1, 2, 3))
    return -10 * np.log10(np.maximum(mse, 1e-12))


def main(root, output):
    review = read(root / "native/manual-review-before-statistics.json")
    assert review["statistics_interpreted"] is False
    assert all(b["actual_viewed"] for b in review["boards"])
    summary = read(checked(review["pilot"]))
    assert (
        summary["status"]
        == "completed-fixed-spectral-photo-GFX-component-pilot-awaiting-native-review"
    )
    max_mask = 0.0
    errors = {"linear_psnr": 0.0, "srgb_psnr": 0.0}
    scalars = identities = inputs = recovery_matches = 0
    comparisons = []
    for result in summary["results"]:
        with np.load(checked(result["arrays"]), allow_pickle=False) as a:
            names = ["colors", "matrix", "packed", "variance", "wb"]
            if result["kind"] == "photo":
                names.append("target")
            assert fingerprint({k: a[k] for k in names}) == result["inputs_sha256"]
            inputs += 1
            for mode, expected in [
                ("full", a["base"] + a["gate"][..., None, None] * a["innovation"]),
                ("unit", a["base"] + a["innovation"]),
            ]:
                assert expected.tobytes(order="C") == a[mode].tobytes(order="C")
                identities += len(expected)
            f = np.fft.rfft2(a["packed"].astype(np.float64), norm="ortho")
            scale = np.maximum(a["variance"], 0).astype(np.float64).mean((-2, -1), keepdims=True)
            power = (np.abs(f) ** 2 / np.maximum(scale, 1e-12)).sum(1, keepdims=True)
            t = math.log(a["packed"].shape[-2] * a["packed"].shape[-1] / 0.01)
            mask = np.maximum(1 - (4 + 4 * math.sqrt(t) + 2 * t) / np.maximum(power, 1e-12), 0)
            mask[..., 0, 0] = 0
            max_mask = max(max_mask, float(np.max(np.abs(mask - a["mask"]))))
            if result["kind"] != "photo":
                continue
            condition = result["condition"]["name"]
            rows = result["cases"]
            sources = list(dict.fromkeys(row["source_id"] for row in rows))
            scores = {(row["source_id"], row["mode"]): row["metrics"] for row in rows}
            for mode in ["full", "base", "unit"]:
                p, q = [v[..., 8:-8, 8:-8].astype(np.float64) for v in [a[mode], a["target"]]]
                values = {
                    "linear_psnr": psnr(p.clip(0, 1), q.clip(0, 1)),
                    "srgb_psnr": psnr(
                        render(p, a["wb"], a["matrix"]), render(q, a["wb"], a["matrix"])
                    ),
                }
                for metric, values_by_source in values.items():
                    for i, source in enumerate(sources):
                        errors[metric] = max(
                            errors[metric],
                            abs(float(values_by_source[i]) - scores[source, mode][metric]),
                        )
                        scalars += 1
            deltas = {}
            for mode, reference in [("unit", "full"), ("full", "base")]:
                deltas[mode + "_minus_" + reference] = {
                    metric: [
                        scores[s, mode][metric] - scores[s, reference][metric] for s in sources
                    ]
                    for metric in ["linear_psnr", "srgb_psnr", "srgb_ssim"]
                }
            comparisons.append({"condition": condition, "source_ids": sources, **deltas})
            failed = (
                root.parent
                / "spectral-photo-components-v1/cuda-pilot"
                / ("photo-" + condition)
                / "arrays.npz"
            )
            if condition in ["adc-only", "iso100-prior", "iso1600-prior", "iso12800-prior"]:
                with np.load(failed, allow_pickle=False) as old:
                    assert set(old.files) == set(a.files)
                    assert all(
                        old[k].tobytes(order="C") == a[k].tobytes(order="C") for k in a.files
                    )
                recovery_matches += 1
    assert inputs == 8 and identities == 36 and scalars == 84 and recovery_matches == 4
    assert max_mask < 1e-4 and max(errors.values()) < 1e-4
    cells = triplets = 0
    for board_ref in review["boards"]:
        board = read(checked(board_ref["receipt"]))
        pixels = np.asarray(Image.open(checked(board["board"])))
        for cell in board["cells"]:
            original = np.asarray(Image.open(checked(cell["image"])))
            x, y, w, h = cell["source_xywh"]
            xx, yy, ww, hh = cell["board_xywh"]
            source = original[y : y + h, x : x + w]
            assert (w, h, ww, hh) == (160,) * 4
            assert np.array_equal(source, pixels[yy : yy + hh, xx : xx + ww])
            assert hashlib.sha256(source.tobytes()).hexdigest() == cell["pixel_sha256"]
            cells += 1
        for report_ref in board["reports"]:
            report = read(checked(report_ref))
            shared = {}
            for crop in report["native_crops"]:
                original = np.asarray(
                    Image.open(
                        checked(
                            {
                                "path": str(Path(report_ref["path"]).parent / crop["image"]),
                                "sha256": crop["png_sha256"],
                            }
                        )
                    )
                )
                key = crop.get("source_id", crop.get("region", {}).get("name"))
                for i in [0, 2]:
                    x, y, w, h = crop["panels"][i]["png_xywh"]
                    part = original[y : y + h, x : x + w].tobytes()
                    assert shared.setdefault((key, i), part) == part
                triplets += 1
    assert cells == 90 and triplets == 54
    result = {
        "status": "completed-independent-NumPy-photo-GFX-component-audit",
        "driver": ref(__file__),
        "pilot": review["pilot"],
        "manual_review_before_statistics": ref(
            root / "native/manual-review-before-statistics.json"
        ),
        "input_batches_exact": inputs,
        "FP32_output_identities_exact": identities,
        "FP64_mask_max_abs_error": max_mask,
        "PSNR_scalars_independently_recomputed": scalars,
        "PSNR_max_abs_error_by_metric": errors,
        "SSIM_independently_recomputed": False,
        "first_four_failed_attempt_arrays_bitwise_replayed": recovery_matches,
        "native_cells_exact": cells,
        "source_triplets_exact": triplets,
        "comparisons": comparisons,
        "scope": "Two photo sources, seven conditions, one RGGB layout/draw; no population inference. GFX is qualitative only; no real-reference metrics. No neural inference, training, serving or policy change.",
    }
    assert output.is_relative_to(root) or output.is_relative_to(Path.cwd())
    output.write_text(json.dumps(result, indent=2) + "\n")
    print({k: v for k, v in result.items() if k not in ["comparisons", "scope"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.root.resolve(), args.output.resolve())
