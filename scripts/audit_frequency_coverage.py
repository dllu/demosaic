"""Audit V186 closed journals, QR/DFT values, local controls and exact means."""

import gzip
import hashlib
import json
import math
import sys
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
from frequency_coverage_reference import (
    dense_spectral_row,
    direct_local_power,
    independent_footprint,
    qr_spectrum,
    sorted_select,
)
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V186-frequency-coverage-v1"
METHODS = ["actual_high4", "FP64_high4", "broad4", "balanced8"]


def lines(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def fingerprint(value):
    return {
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest(),
    }


def sample(value, colors):
    return np.stack(
        [
            np.stack([rgb[color, p // 2 :: 2, p % 2 :: 2] for p, color in enumerate(layout)])
            for rgb, layout in zip(value, colors, strict=True)
        ]
    )


def audit():
    plan = read(ROOT / "plan-v1.json")
    result = read(ROOT / "result-v1.json")
    resume = read(ROOT / "control-resume-plan-v1.json")
    assert not owner_live(result["owner"]) and not owner_live(result["original_owner"])
    assert result["status"].startswith("completed-input-only-selection")
    seal = read(ROOT / "audit-source-v2.json")
    assert ref(__file__) == seal["auditor"]
    for b in seal["helpers"] + resume["sources"] + resume["original_prefix"]:
        assert ref(b["path"]) == b
    for b in plan["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    for n in [
        "input_completion",
        "input_journal",
        "template_journal",
        "control_measurements",
        "control_journal",
    ]:
        assert ref(result[n]["path"]) == result[n]
    inputs = lines(result["input_journal"]["path"])
    scored = lines(result["template_journal"]["path"])
    controls = read(result["control_measurements"]["path"])["rows"]
    assert scored == result["rows"] and controls == lines(result["control_journal"]["path"])
    assert len(inputs) == 550 and len(scored) == 512 and len(controls) == 160
    assert (
        result["retained_input_selection_replays"] == result["retained_clean_template_replays"] == 0
    )
    assert result["actual_vs_FP64_high4_case_mismatches"] == 0
    mapping = {c["id"]: c for c in plan["cases"]}
    source_rows = {}
    with gzip.open(plan["dependency"]["selection_journal"]["path"], "rt") as stream:
        for line in stream:
            r = json.loads(line)
            if r["method"] == "V185-spatial-context-raw" and r["id"] in mapping:
                source_rows[r["id"]] = r
    input_values = selections = 0
    for row in inputs:
        c = mapping[row["id"]]
        assert ref(c["arrays"]["path"]) == c["arrays"] == row["arrays"]
        assert row["bins"]["actual_high4"] == source_rows[c["id"]]["evidence"]["bin_yx"][0]
        assert row["bins"]["actual_high4"] == row["bins"]["FP64_high4"]
        assert row["bins"]["balanced8"] == [
            row["bins"]["actual_high4"][a] + row["bins"]["lower4"][a] for a in range(2)
        ]
        assert all(b == source_rows[c["id"]]["inputs"][n] for n, b in row["inputs"].items())
        input_values += 3
        selections += 8
        for method in METHODS:
            expected = 16 if method == "balanced8" else 8
            assert len(row["selected_stats"][method]) == expected
            assert all(
                math.isfinite(x[k])
                for x in row["selected_stats"][method]
                for k in ["selection_power", "other_phase_power", "bounded_cross_real"]
            )
    first_ids = set(plan["independent_verification_case_ids"])
    qr_bins = dft_rows = coverage_scalars = 0
    max_coefficient_error = max_variance_error = max_fraction_error = 0.0
    score_map = {r["id"]: r for r in scored}
    for row in inputs:
        if row["id"] not in first_ids:
            continue
        c = mapping[row["id"]]
        with np.load(c["arrays"]["path"], allow_pickle=False) as a:
            raw, variance, colors = [a[k] for k in ["packed", "variance", "colors"]]
            present = np.maximum(a["target_present"], np.float32(0))
            empty = np.maximum(a["target_empty"], np.float32(0))
        green = np.flatnonzero(colors[0] == 1)
        shape = tuple(raw.shape[-2:])
        clean = sample(present, colors).astype(float) - sample(empty, colors).astype(float)
        clean_power = np.zeros(shape, float)
        for direction, phase in enumerate(green):
            z, n, q, window = qr_spectrum(raw[0, phase], variance[0, phase])
            n = np.maximum(n, (1 / 65535) ** 2)
            for name, lower, upper, inclusive in [
                ("FP64_high4", 1 / 16, 1 / 3, True),
                ("lower4", 1 / 32, 1 / 16, False),
                ("broad4", 1 / 32, 1 / 3, True),
            ]:
                bins = sorted_select(z, n, lower, upper, inclusive)
                assert bins == row["bins"][name][direction]
                qr_bins += len(bins)
            unique = {tuple(v) for method in METHODS for v in row["bins"][method][direction]}
            for b in unique:
                vector = dense_spectral_row(shape, b, q, window)
                coefficient = (
                    vector @ (raw[0, phase].astype(float) - float(raw[0, phase, 0, 0])).ravel()
                )
                noise = float((abs(vector) ** 2) @ variance[0, phase].astype(float).ravel())
                np.testing.assert_allclose(coefficient, z[b], rtol=2e-9, atol=2e-13)
                np.testing.assert_allclose(
                    max(noise, (1 / 65535) ** 2), n[b], rtol=2e-10, atol=2e-16
                )
                max_coefficient_error = max(max_coefficient_error, float(abs(coefficient - z[b])))
                max_variance_error = max(
                    max_variance_error, abs(max(noise, (1 / 65535) ** 2) - n[b])
                )
                dft_rows += 1
            target_spectrum, _, _, _ = qr_spectrum(clean[0, phase], np.ones(shape))
            clean_power += abs(target_spectrum) ** 2
        expected = score_map[c["id"]]
        total = float(clean_power.sum())
        fy, fx = [np.fft.fftfreq(n) / 2 for n in shape]
        radius = np.hypot(fy[:, None], fx[None, :])
        masks = {
            "lower_octave_power_fraction": (radius >= 1 / 32) & (radius < 1 / 16),
            "high_band_power_fraction": (radius >= 1 / 16) & (radius <= 1 / 3),
            "below_lower_octave_power_fraction": radius < 1 / 32,
        }
        for method in METHODS:
            bins = np.asarray(row["bins"][method]).reshape(-1, 2)
            for name, r in [("near1", 1), ("localwidth", max(math.ceil(n / 65) for n in shape))]:
                masks[method + "_" + name + "_template_fraction"] = independent_footprint(
                    shape, bins, r
                )
        for name, mask in masks.items():
            value = float(clean_power[mask].sum() / total)
            difference = abs(value - expected[name])
            max_fraction_error = max(max_fraction_error, difference)
            assert difference < 2e-10, (c["id"], name, difference)
            coverage_scalars += 1
        assert math.isclose(
            total, expected["total_tapered_template_energy"], rel_tol=2e-10, abs_tol=2e-16
        )
    control_scalars = 0
    max_control_error = 0.0
    cache = {}
    for r in controls:
        c = mapping[r["id"]]
        if c["id"] not in cache:
            with np.load(c["arrays"]["path"], allow_pickle=False) as a:
                cache[c["id"]] = {k: a[k] for k in ["packed", "variance", "colors"]}
        a = cache[c["id"]]
        greens = np.flatnonzero(a["colors"][0] == 1)
        x, y, w, h = r["ROI_xywh"]
        assert r["center_packed_yx"] == [[(y + h // 2) // 2, (x + w // 2) // 2]]
        for value in r["measurements"]:
            for member, label in zip(
                [(0, 1), (1, 0)][value["direction"]],
                ["ROI_center_local_selection_power", "ROI_center_local_other_power"],
                strict=True,
            ):
                phase = greens[member]
                actual = direct_local_power(
                    a["packed"][0, phase],
                    a["variance"][0, phase],
                    value["bin_yx"],
                    r["center_packed_yx"][0],
                )
                np.testing.assert_allclose(actual, value[label], rtol=1e-7, atol=1e-8)
                max_control_error = max(max_control_error, abs(actual - value[label]))
                control_scalars += 1
    reduction = read(ROOT / "summary-reduction-v2.json")
    assert reduction["original_result"] == ref(ROOT / "result-v1.json")
    assert reduction["template_summary_by_presence"] == result["template_summary_by_presence"]
    mean_checks = 0
    for group_keys, summary_key in [
        (["present"], "template_summary_by_presence"),
        (
            ["present", "nominal_fundamentals_below_high"],
            "template_summary_by_presence_and_nominal_band",
        ),
    ]:
        groups = defaultdict(list)
        for r in scored:
            groups[tuple(r[k] for k in group_keys)].append(r)
        for summary in reduction[summary_key]:
            group = groups[tuple(summary[k] for k in group_keys)]
            assert summary["cases"] == len(group)
            for field, stats in summary.items():
                if not isinstance(stats, dict):
                    continue
                with localcontext() as ctx:
                    ctx.prec = 70
                    value = float(
                        sum((Decimal.from_float(float(r[field])) for r in group), Decimal(0))
                        / len(group)
                    )
                assert math.isclose(value, stats["mean"], rel_tol=3e-15, abs_tol=2e-13)
                mean_checks += 1
    for group in result["input_power_summary"]:
        cases = [
            r for r in inputs if r["kind"] == group["kind"] and r["present"] == group["present"]
        ]
        values = [
            max(x["other_phase_power"] for x in r["selected_stats"][group["method"]]) for r in cases
        ]
        assert (
            len(cases) == group["cases"]
            and float(np.median(values)) == group["max_other_phase_power_median"]
        )
        assert group["counts_at_predeclared_power"] == {
            str(t): sum(v >= t for v in values) for t in plan["descriptive_power_bins"]
        }
    for r in scored:
        assert all(0 <= r[k] <= 1 for k in r if k.endswith("_fraction"))
        for key in ["near1", "localwidth"]:
            assert (
                r[f"balanced8_{key}_template_fraction"]
                >= r[f"actual_high4_{key}_template_fraction"] - 1e-15
            )
        c = mapping[r["id"]]
        assert r["nominal_fundamentals_below_high"] == sum(
            p > 16 for p in c["source"]["recipe"]["periods_final_pixels"]
        )
    for name, digest in plan["dependency"]["neural100_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    proof = {
        "status": "pass-retained-prefix-bindings-independent-QR-DFT-footprints-local-ROIs-and-Decimal-means",
        "result": ref(ROOT / "result-v1.json"),
        "summary_reduction": ref(ROOT / "summary-reduction-v2.json"),
        "original_failed_audit": ref(ROOT / "verification-v1.log"),
        "source": dict(ref(__file__), text=Path(__file__).read_text()),
        "audit_seal": ref(ROOT / "audit-source-v2.json"),
        "input_fingerprints": input_values,
        "saved_actual_frequency_records": selections,
        "QR_frequency_bins_checked": qr_bins,
        "explicit_complex_DFT_rows_checked": dft_rows,
        "independent_template_fraction_scalars": coverage_scalars,
        "explicit_local_ROI_power_scalars": control_scalars,
        "independent_Decimal_means": mean_checks,
        "maximum_complex_DFT_absolute_error": max_coefficient_error,
        "maximum_DFT_variance_absolute_error": max_variance_error,
        "maximum_template_fraction_absolute_error": max_fraction_error,
        "maximum_ROI_power_absolute_error": max_control_error,
        "neural_sources_unchanged": 100,
        "new_neural_forwards": 0,
        "new_RGB_restorations": 0,
        "new_checkpoint_loads": 0,
        "target_reads_before_original_input_close": 0,
        "retained_input_selection_replays": 0,
        "retained_clean_template_replays": 0,
        "scope": "Independent numerical checks use orthonormal QR and explicit DFT rows on the fixed first12 constructed cases; all550input bindings/actual bins and all512derived rows/summary means checked. All160region-method control powers checked by explicit patch QR projection. This verifies the diagnostic, not recoverability or restored image quality.",
    }
    with (ROOT / "verification-v2.json").open("x") as f:
        json.dump(proof, f, indent=2)
        f.write("\n")
    print(
        "PASS",
        qr_bins,
        "QRbins",
        dft_rows,
        "DFTrows",
        coverage_scalars,
        "fractions",
        control_scalars,
        "ROI scalars",
        mean_checks,
        "means",
    )


if __name__ == "__main__":
    audit()
