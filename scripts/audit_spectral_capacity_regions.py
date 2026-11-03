"""Actual blank errors and GT-only line-search/coefficient algebra checks."""

import argparse
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from train_directional_bank_trial import read, ref, save


def main(root):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[6:8])
    plan = read(root / "plan-v1.json")
    diagnostic = read(root / "result-v1.json")
    scores = read(root / "scores-v1.json")
    by_id = defaultdict(list)
    for row in scores["rows"]:
        if row["kind"] == "mesh":
            by_id[row["id"]].append(row)
    rows = []
    for case in plan["cases"]:
        if case["kind"] != "mesh":
            continue
        a = dict(np.load(case["arrays"]["path"]))
        mask = (
            np.all(a["target_present"] == a["target_empty"], axis=1)[0]
            if case["present"]
            else np.ones((512, 512), bool)
        )
        assert mask.any()
        target = a["target"][0].astype(np.float64)[:, mask]
        base = np.load(case["parent"]["path"])[0].astype(np.float64)[:, mask]
        for row in by_id[case["id"]]:
            assert ref(row["prediction"]["path"]) == row["prediction"]
            v = np.load(row["prediction"]["path"])[0].astype(np.float64)[:, mask]
            error = v - target
            means = error.mean(1)
            total = float(np.linalg.norm(error) / np.sqrt(error.size) * 65535)
            spatial = float(np.sqrt(np.mean((error - means[:, None]) ** 2)) * 65535)
            dc = float(np.sqrt(np.mean(means**2)) * 65535)
            assert abs(total**2 - spatial**2 - dc**2) < 1e-8
            added = float(np.sqrt(np.mean((v - base) ** 2)) * 65535)
            assert abs(added - row["blank_added_RMS_DN16"]) < 1e-10
            rows.append(
                {
                    "id": case["id"],
                    "present": case["present"],
                    "method": row["method"],
                    "prediction": row["prediction"],
                    "blank_pixels": int(mask.sum()),
                    "blank_error_RMS_DN16": total,
                    "blank_spatial_RMS_DN16": spatial,
                    "blank_DC_RMS_DN16": dc,
                    "blank_added_RMS_DN16": added,
                }
            )
    assert len(rows) == 6144
    groups = defaultdict(list)
    for row in rows:
        groups[row["present"], row["method"]].append(row)
    summary = []
    fields = [
        "blank_error_RMS_DN16",
        "blank_spatial_RMS_DN16",
        "blank_DC_RMS_DN16",
        "blank_added_RMS_DN16",
    ]
    for (present, method), group in groups.items():
        summary.append(
            {
                "present": present,
                "method": method,
                "cases": len(group),
                **{k: float(np.mean([r[k] for r in group])) for k in fields},
            }
        )
    witnesses = {o["id"]: o for o in diagnostic["observations"]}
    line_rows = []
    largest_excess = 0.0
    for case in plan["cases"]:
        obs = witnesses[case["id"]]
        errors = obs["coefficient_squared_error"]
        parent_error = obs["parent_coefficient_squared_error"]
        tolerance = 1e-6 * max(parent_error, 1e-12)
        for key in ("scalar", "matrix", "L2"):
            assert errors[key] <= parent_error + tolerance
        for key in ("scalar", "matrix"):
            assert errors["L2"] <= errors[key] + tolerance
        assert errors["unbanded"] == 0 and obs["maximum_matrix_gauge"] <= 1 + 2e-6
        base = np.load(case["parent"]["path"]).astype(np.float64)
        a = dict(np.load(case["arrays"]["path"]))
        target = a["target"].astype(np.float64)
        full = np.load(obs["predictions"]["GT-matrix-full-support"]["path"]).astype(np.float64)
        actual = np.load(obs["predictions"]["GT-matrix-image-alpha"]["path"]).astype(np.float64)
        correction = full - base
        power = np.sum(correction**2)
        optimal = (
            float(np.clip(np.sum((target - base) * correction) / power, 0, 1)) if power else 0.0
        )
        expected = base + optimal * correction
        alpha = obs["image_alpha"]
        assert 0 <= alpha <= 1
        ulp = max(
            float(np.abs(np.spacing(np.float32(np.max(np.abs(v)))))) for v in (base, full, actual)
        )
        pixel_tolerance = max(4 * ulp, 2e-10)
        replay_error = float(np.max(np.abs(actual - (base + alpha * correction))))
        assert replay_error <= pixel_tolerance
        mse = float(np.mean((actual - target) ** 2))
        oracle_line_mse = float(np.mean((expected - target) ** 2))
        mse_tolerance = pixel_tolerance * (2 * np.sqrt(oracle_line_mse) + pixel_tolerance)
        excess = mse - oracle_line_mse
        assert excess <= mse_tolerance, (case["id"], excess, mse_tolerance)
        largest_excess = max(largest_excess, excess)
        line_rows.append(
            {
                "id": case["id"],
                "recorded_alpha": alpha,
                "RGB_published_line_alpha": optimal,
                "maximum_pixel_replay_difference": replay_error,
                "pixel_roundoff_allowance": pixel_tolerance,
                "MSE_excess_over_independent_RGB_line_minimum": excess,
                "MSE_roundoff_allowance": float(mse_tolerance),
            }
        )
    save(
        root / "region-and-algebra-audit-v1.json",
        {
            "status": "pass",
            "auditor": ref(__file__),
            "plan": ref(root / "plan-v1.json"),
            "scores": ref(root / "scores-v1.json"),
            "diagnostic": ref(root / "result-v1.json"),
            "rows": rows,
            "summary": summary,
            "image_line_checks": line_rows,
            "mesh_region_rows": 6144,
            "coefficient_case_checks": 792,
            "global_image_line_checks": 792,
            "maximum_MSE_excess_over_independent_line_minimum": largest_excess,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Actual GT error inside exact constant mesh/absent masks, separated into spatial/DC components. Added correction RMS can include removal of existing error and is not itself hallucination. All792 coefficient witnesses check scalar/matrix feasibility and relaxed-L2 dominance; global GT-only image-alpha checked independently from archived RGB values with explicit FP32 roundoff allowances. This does not make any GT oracle available at inference.",
        },
    )
    print("PASS6144 blank-region rows and792 coefficient/image-line cases")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.absolute())
