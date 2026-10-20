"""Independent NumPy reductions of saved spectral-component arrays; CPU only."""

import argparse
import hashlib
import math
from pathlib import Path

import numpy as np
from train_directional_bank_trial import read, ref, save

INPUTS = ["colors", "matrix", "packed", "target", "variance", "wb"]


def fingerprint(values):
    digest = hashlib.sha256()
    for name in INPUTS:
        a = values[name]
        dtype = {"float32": "torch.float32", "int64": "torch.int64"}[a.dtype.name]
        digest.update(name.encode() + dtype.encode() + str(tuple(a.shape)).encode())
        digest.update(a.tobytes(order="C"))
    return digest.hexdigest()


def linear(rgb, wb, matrix):
    return np.einsum(
        "bij,bjhw->bihw",
        matrix.astype(np.float64),
        rgb.astype(np.float64) * wb.astype(np.float64)[..., None, None],
    )


def metrics(prediction, target, period, roi):
    x, y, width, height = roi
    a, b = [v[..., y : y + height, x : x + width] for v in [prediction, target]]
    if period is not None:
        angle = np.arange(x, x + width, dtype=np.float64) * (2 * math.pi / period)
        basis = np.stack(
            [
                np.ones((height, width)),
                np.broadcast_to(np.cos(angle), (height, width)),
                np.broadcast_to(np.sin(angle), (height, width)),
            ],
            axis=-1,
        ).reshape(-1, 3)
        gram = basis.T @ basis
        a, b = a.reshape(*a.shape[:2], -1), b.reshape(*b.shape[:2], -1)
        betas = []
        for value in [a, b]:
            rhs = value @ basis
            betas.append(np.linalg.solve(gram, rhs.reshape(-1, 3).T).T.reshape(*rhs.shape))
        ba, bb = betas
        ca, cb = ba[..., 1:], bb[..., 1:]
        power = np.maximum(np.sum(cb**2, axis=-1), 1e-24)
        gain = np.sum(ca * cb, axis=-1) / power
        return {
            "in_phase_gain": gain.mean(1),
            "gain_channel_std": gain.std(1),
            "quadrature_gain": ((cb[..., 0] * ca[..., 1] - cb[..., 1] * ca[..., 0]) / power).mean(
                1
            ),
            "amplitude_ratio": np.sqrt(np.sum(ca**2, axis=-1) / power).mean(1),
            "dc_bias_abs": np.abs(ba[..., 0] - bb[..., 0]).mean(1),
            "noncarrier_rms": np.sqrt(np.mean((a - ba @ basis.T) ** 2, axis=(1, 2))),
            "linear_srgb_rmse": np.sqrt(np.mean((a - b) ** 2, axis=(1, 2))),
        }
    luma = a[:, 0] * 0.2126 + a[:, 1] * 0.7152 + a[:, 2] * 0.0722
    truth = b[:, 0] * 0.2126 + b[:, 1] * 0.7152 + b[:, 2] * 0.0722
    centered = luma - luma.mean((-2, -1), keepdims=True)
    spectrum = np.fft.fft2(centered)
    radius = np.sqrt(np.fft.fftfreq(height)[:, None] ** 2 + np.fft.fftfreq(width)[None, :] ** 2)
    band = (radius >= 1 / 48) & (radius <= 0.22)
    level = np.maximum(np.abs(truth.mean((-2, -1))), 1e-12)
    return {
        "dc_bias_abs_rgb": np.abs(a.mean((-2, -1)) - b.mean((-2, -1))).mean(1),
        "linear_srgb_rmse": np.sqrt(np.mean((a - b) ** 2, axis=(1, 2, 3))),
        "spatial_luma_rms": np.sqrt(np.mean(centered**2, axis=(-2, -1))),
        "relative_band_rms": np.sqrt(np.sum(np.abs(spectrum) ** 2 * band, axis=(-2, -1)))
        / (height * width)
        / level,
        "relative_peak_band_contrast": 2
        * np.max(np.abs(spectrum) * band, axis=(-2, -1))
        / (height * width)
        / level,
    }


def main(root, output):
    import json

    summary = read(root / "cuda-diagnostic/summary.json")
    assert summary["status"] == "completed-read-only-spectral-gate-component-diagnostic"
    rows = [json.loads(x) for x in Path(summary["per_case"]["path"]).read_text().splitlines()]
    assert ref(summary["per_case"]["path"]) == summary["per_case"]
    keyed = {
        (
            tuple(
                r[k]
                for k in ["kind", "level", "contrast", "period", "condition", "pattern", "draw"]
            ),
            r["model"],
        ): r["metrics"]
        for r in rows
    }
    assert len(keyed) == len(rows) == 1792
    max_error = max_gate = max_mask = 0.0
    scalar_count = 0
    sample_hashes = set()
    flat_equal = 0
    gates = []
    adc = []
    for stat in summary["case_component_statistics"]:
        assert ref(stat["arrays"]["path"]) == stat["arrays"]
        with np.load(stat["arrays"]["path"], allow_pickle=False) as a:
            assert fingerprint({k: a[k] for k in INPUTS}) == stat["input_sha256"]
            for i in range(len(a["packed"])):
                sample_hashes.add(fingerprint({k: a[k][i : i + 1] for k in INPUTS}))
            expected = a["base"] + a["gate"][..., None, None] * a["innovation"]
            assert expected.tobytes(order="C") == a["full"].tobytes(order="C")
            assert (a["base"] + a["innovation"]).tobytes(order="C") == a["unit"].tobytes(order="C")
            gate = np.tanh(
                a["pooled"].astype(np.float64) @ a["head_weight"].astype(np.float64).T
                + a["head_bias"].astype(np.float64)
            )
            max_gate = max(max_gate, float(np.max(np.abs(gate - a["gate"]))))
            assert max_gate < 1e-6
            f = np.fft.rfft2(a["packed"].astype(np.float64), norm="ortho")
            scale = np.maximum(
                np.maximum(a["variance"], 0).astype(np.float64).mean((-2, -1), keepdims=True), 1e-12
            )
            power = (np.abs(f) ** 2 / scale).sum(1, keepdims=True)
            t = math.log(a["packed"].shape[-2] * a["packed"].shape[-1] / 0.01)
            mask = np.maximum(1 - (4 + 4 * math.sqrt(t) + 2 * t) / np.maximum(power, 1e-12), 0)
            mask[..., 0, 0] = 0
            max_mask = max(max_mask, float(np.max(np.abs(mask - a["mask"]))))
            assert max_mask < 1e-4
            target = linear(a["target"], a["wb"], a["matrix"])
            for mode in ["full", "base", "unit"]:
                result = metrics(
                    linear(a[mode], a["wb"], a["matrix"]),
                    target,
                    stat["period"],
                    summary["roi_xywh"],
                )
                for draw in range(summary["draws"]):
                    case = tuple(
                        stat[k]
                        for k in ["kind", "level", "contrast", "period", "condition", "pattern"]
                    ) + (draw,)
                    old = keyed[(case, mode)]
                    for name, value in result.items():
                        max_error = max(max_error, abs(float(value[draw]) - old[name]))
                        scalar_count += 1
                    if (
                        stat["kind"] == "carrier"
                        and stat["condition"] == "adc-only"
                        and mode == "unit"
                    ):
                        adc.append(
                            {
                                "case": list(case),
                                "unit_minus_full_gain": old["in_phase_gain"]
                                - keyed[(case, "full")]["in_phase_gain"],
                            }
                        )
            if stat["kind"] == "flat" and stat["condition"] == "iso12800-prior":
                assert not np.count_nonzero(a["mask"])
                assert (
                    a["full"].tobytes(order="C")
                    == a["base"].tobytes(order="C")
                    == a["unit"].tobytes(order="C")
                )
                flat_equal += summary["draws"]
            gates.extend(float(v) for v in a["gate"].flatten())
    assert max_error < 1e-8 and flat_equal == 32 and len(adc) == 192
    failures = [x for x in adc if x["unit_minus_full_gain"] < -0.05]
    failed_layouts = {tuple(x["case"][:6]) for x in failures}
    result = {
        "status": "completed-independent-NumPy-spectral-component-array-audit",
        "driver": ref(__file__),
        "diagnostic": ref(root / "cuda-diagnostic/summary.json"),
        "actual_view_before_statistics": ref(root / "native/manual-review-before-statistics.json"),
        "case_rows": len(rows),
        "array_metric_rows": 1344,
        "independent_metric_scalars": scalar_count,
        "maximum_metric_difference": max_error,
        "maximum_FP64_gate_difference": max_gate,
        "maximum_FP64_mask_difference": max_mask,
        "all112_batch_input_fingerprints_exact": True,
        "all_full_and_unit_FP32_output_decompositions_byte_exact": True,
        "case_slots_per_mode": 448,
        "unique_input_samples_including_target_and_metadata": len(sample_hashes),
        "ADC_draw_labels_repeat_deterministic_quantized_observations": True,
        "high_noise_flat_cases_all_empty_mask_and_full_base_unit_bytes_exact": flat_equal,
        "ADC_unit_minus_full_cases": adc,
        "ADC_unit_gain_loss_below_minus_.05_count": len(failures),
        "ADC_unit_failed_distinct_layout_signal_cases": len(failed_layouts),
        "all_gate_min_max": [min(gates), max(gates)],
        "scope": "Independent NumPy normal equations, FFT/flat reductions and raw input/gate/mask/output arithmetic. Metrics recomputed from all saved full/base/unit arrays; MHC witnesses come from the separate exact original replay. FP64 gate/mask comparisons are numerical approximations of FP32 CUDA arithmetic. Fixed unit gate is an analytic intervention only, not a new quality/production recommendation.",
    }
    save(output, result)
    print({k: v for k, v in result.items() if not isinstance(v, (dict, list))})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.root, a.output)
