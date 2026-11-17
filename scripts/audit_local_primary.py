"""Independently rescore closed local-primary predictions with established NumPy tolerances."""

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from audit_quality_archive import _check

from demosaic.archive_metrics import photometry
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def audit(path, output):
    if "torch" in sys.modules or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Independent primary audit requires NumPy only and hidden CUDA")
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    result = read_json(path)
    assert result["all_complete"]
    assert (result["kind"], result["cases"]) in {("preflight", 3), ("full", 3162)}
    plan = read_json(checked(result["plan"]))
    canonical = read_json(checked(plan["canonical_inputs"]))
    lookup = {(r["stage"], r["batch"]): r for r in canonical["records"]}
    errors, stages, rows, keys = defaultdict(lambda: defaultdict(float)), Counter(), [], set()
    for binding in result["case_records"]:
        case = read_json(checked(binding))
        stage = case["stage"]
        assert case["canonical_arrays"] == lookup[stage, case["batch"]]["arrays"]
        with np.load(checked(case["canonical_arrays"]), allow_pickle=False) as data:
            arrays = dict(data)
        for variant in case["variants"]:
            assert variant["checkpoint"] == result["models"][variant["arm"]]["checkpoint"]
            prediction = np.load(checked(variant["prediction"]), allow_pickle=False)
            measures = photometry(
                prediction,
                arrays,
                border=8 if stage == "photo" else 32,
                camera=stage in {"known", "unseen"},
            )
            assert len(variant["rows"]) == prediction.shape[0]
            for index, original in enumerate(variant["rows"]):
                actual = {name: value[index] for name, value in measures.items()}
                _check(actual, original["metrics"], errors[stage], stage)
                key = (
                    stage,
                    original["model"],
                    original["id"],
                    original["pattern"],
                    original.get("condition"),
                    original.get("pair"),
                )
                assert key not in keys
                keys.add(key)
                rows.append(
                    {
                        **original,
                        "stage": stage,
                        "independent_metrics": {
                            name: float(value) if np.isfinite(value) else None
                            for name, value in actual.items()
                        },
                    }
                )
                stages[stage, variant["arm"]] += 1
    if result["kind"] == "full":
        for label in result["models"]:
            assert {stage: stages[stage, label] for stage in ["photo", "known", "unseen"]} == {
                "photo": 12404,
                "known": 72,
                "unseen": 90,
            }
            ids = {r["id"] for r in rows if r["model"] == label and r.get("kind") == "photo"}
            assert len(ids) == 427
    output = Path(output)
    output.mkdir()
    write_json(
        output / "result.json",
        {
            "producer": reference(__file__),
            "original_tolerance_helper": reference(
                Path(__file__).parent / "audit_quality_archive.py"
            ),
            "source_result": reference(path),
            "kind": result["kind"],
            "rows": rows,
            "stage_model_observation_counts": {f"{s}|{m}": n for (s, m), n in stages.items()},
            "maximum_discrepancies": dict(errors),
            "status": "passed",
            "scope": "Independent NumPy64 original photometry/measured-CFA subsets, fixed borders and original5e-4dB/2e-6 tolerances. Canonical array/model/prediction SHA identities and row uniqueness checked. Full means require all3162 cases/427 photos/known72/unseen90 crop observations per model;3-case qualification is not broad evaluation. SSIM/additional masked metrics retain the collector's original implementation. No neural/RAW/noise/GPU/optimizer calls.",
        },
    )
    print("Independent primary audit passed", len(rows), "rows", dict(errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit(args.result, args.output)
