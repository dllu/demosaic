"""Independently reconstruct every global wave oracle and check its optimality."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.edge_response import measure
from demosaic.experiments.evaluation.native import load_native


def direct_columns(waves, bins, phase_free):
    """Construct each native CFA-cell column explicitly, without the fit helper."""
    count, _, h, w = waves.shape
    columns = np.empty((count * (2 if phase_free else 1), 2 * h, 2 * w), np.float32)
    for carrier in range(count):
        ky, kx = bins[carrier]
        if ky > (h - 1) // 2:
            ky -= h
        if kx > (w - 1) // 2:
            kx -= w
        real, imag = waves[carrier]
        for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            angle = np.pi * (float(ky) * dy / h + float(kx) * dx / w)
            cosine, sine = np.float32(np.cos(angle)), np.float32(np.sin(angle))
            columns[carrier, dy::2, dx::2] = real * cosine - imag * sine
            if phase_free:
                columns[count + carrier, dy::2, dx::2] = -real * sine - imag * cosine
    return columns.astype(np.float64)


def audit(root):
    if "torch" in sys.modules:
        raise RuntimeError("Require a fresh NumPy-only audit process")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    plan = read_json(root / "plan.json")
    scores = read_json(root / "scores.json")
    closed = read_json(checked(scores["closed_bases"]))
    fits = read_json(checked(scores["fits"]))
    expected_methods = {"V200-ema", "complementary-ema", *plan["methods"]}
    expected_indices = {r["index"] for r in plan["rows"]}
    expected_keys = {(i, m) for i in expected_indices for m in expected_methods}
    actual = {(r["index"], r["method"]): r for r in scores["rows"]}
    coefficients = {(r["index"], r["method"], r["role"], r["color"]): r for r in fits["rows"]}
    expected_fits = {
        (i, m, r, c)
        for i in expected_indices
        for m in plan["methods"]
        for r in range(3)
        for c in range(3)
    }
    if (
        len(expected_indices) != 64
        or set(actual) != expected_keys
        or len(actual) != len(scores["rows"])
    ):
        raise ValueError("Oracle score coverage/uniqueness differs")
    if set(coefficients) != expected_fits or len(coefficients) != len(fits["rows"]):
        raise ValueError("Oracle coefficient coverage/uniqueness differs")
    bases = {r["index"]: r for r in closed["rows"]}
    errors = {"native_RGB": 0.0, "metrics": 0.0, "MSE": 0.0, "gradient": 0.0}
    dual_gaps, channels, metric_fields, rows = [], 0, 0, []
    for item in plan["rows"]:
        index = item["index"]
        with np.load(checked(item["arrays"]), allow_pickle=False) as z:
            arrays = {k: z[k] for k in ["target", "quiet", "edge_band"]}
        anchor = load_native(item["anchor"]).astype(np.float64)
        learned = load_native(item["learned"]).astype(np.float64)
        waves = np.load(checked(bases[index]["waves"]), allow_pickle=False)
        bins = np.asarray(item["choice"]["bins_yx"]).reshape(3, 8, 2)
        outputs = {"V200-ema": anchor, "complementary-ema": learned}
        for method in plan["methods"]:
            prediction = np.load(
                checked(scores["predictions"][str(index)][method]), allow_pickle=False
            )
            reconstructed = anchor.copy()
            for role in range(3):
                for color in range(3):
                    receipt = coefficients[index, method, role, color]
                    columns = direct_columns(
                        waves[role, :, color], bins[role], method == "oracle-phase-free"
                    )
                    gains = np.asarray(receipt["coefficients"])
                    result = np.einsum("k,khw->hw", gains, columns)
                    reconstructed[role, color] += result
                    residual = anchor[role, color] + result - arrays["target"][role, color]
                    mse = float(np.mean(residual**2))
                    zero = float(
                        np.mean((anchor[role, color] - arrays["target"][role, color]) ** 2)
                    )
                    gradient = (columns * residual).mean((-1, -2))
                    errors["MSE"] = max(
                        errors["MSE"],
                        abs(mse - receipt["fitted_MSE"]),
                        abs(zero - receipt["zero_MSE"]),
                    )
                    errors["gradient"] = max(
                        errors["gradient"],
                        abs(float(np.max(np.abs(gradient))) - receipt["gradient_infinity_norm"]),
                    )
                    if mse > zero + 1e-15:
                        raise ValueError("A fitted oracle has worse full absolute error than zero")
                    if method == "oracle-real-bounded":
                        if np.max(np.abs(gains)) > 1 + 1e-12:
                            raise ValueError("Constant gains violate the actual real-gate box")
                        gap = float(np.sum(gradient * gains + np.abs(gradient)))
                        if gap > max(1e-18, zero * 1e-7):
                            raise ValueError("Independent full-space box optimality bound fails")
                        dual_gaps.append(max(0.0, gap))
            errors["native_RGB"] = max(
                errors["native_RGB"], float(np.max(np.abs(prediction - reconstructed)))
            )
            channels += prediction.size
            outputs[method] = prediction
        for method, value in outputs.items():
            measured = measure(arrays, value)
            reported = actual[index, method]
            for key, v in measured.items():
                errors["metrics"] = max(errors["metrics"], abs(v - reported[key]))
                metric_fields += 1
            rows.append(
                {
                    "index": index,
                    "method": method,
                    "full_MSE_nonincreasing_for_oracle": method in plan["methods"],
                }
            )
        if index % 16 == 15:
            print("audited", len(rows) // 5, "of64 oracle batches", flush=True)
    if (
        errors["native_RGB"] > 1e-12
        or errors["metrics"] > 1e-12
        or errors["MSE"] > 1e-16
        or errors["gradient"] > 1e-16
    ):
        raise ValueError(f"Independent numerical check differs: {errors}")
    if "torch" in sys.modules:
        raise RuntimeError("Oracle audit imported Torch")
    write_json(
        root / "independent-audit.json",
        {
            "status": "passed-all64-oracle-native-coefficient-metric-checks",
            "scores": reference(root / "scores.json"),
            "script": reference(__file__),
            "coefficient_fits_checked": len(coefficients),
            "bounded_KKT_checks": len(dual_gaps),
            "maximum_box_duality_gap_half_MSE": max(dual_gaps),
            "native_RGB_channels_checked": channels,
            "metric_fields_checked": metric_fields,
            "maximum_absolute_errors": errors,
            "Torch_imported": False,
            "new_neural_forwards": 0,
            "scope": "Independent direct CFA-offset synthesis, full-residual gradients and box duality gaps from saved coefficients. Every oracle RGB array/primary metric checked; no optimization rerun or target-dependent selection. GT oracles remain diagnostics, not deployable models.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    audit(parser.parse_args().root.resolve())
