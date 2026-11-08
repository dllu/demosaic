"""Independent QR rows, phase responses and Decimal analytical-support audit."""

import gzip, json, sys, os, time
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import psutil
from dense_support_reference import reference
from phase_admission_protocol import read, ref, owner_live
from report_dense_measurement_support import ROOT, guard, save


def audit():
    p, r = read(ROOT / "plan-v1.json"), read(ROOT / "result-v1.json")
    guard(p)
    assert ref(__file__) == p["auditor"] and r["plan"] == ref(ROOT / "plan-v1.json")
    assert not owner_live(r["owner"]) and r["owner"] == read(ROOT / "launch-v1.json")["owner"]
    assert ref(r["measurements"]["path"]) == r["measurements"]
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    with gzip.open(r["measurements"]["path"], "rt") as f:
        rows = [json.loads(line) for line in f]
    assert len(rows) == len(p["cases"]) == 1152
    maxima = {}
    checks = 0
    for case, row in zip(p["cases"], rows, strict=True):
        assert case["id"] == row["id"]
        expected = reference(case)
        for key, value in expected.items():
            observed = np.asarray(row[key])
            value = np.asarray(value)
            error = float(abs(observed - value).max())
            maxima[key] = max(maxima.get(key, 0), error)
            np.testing.assert_allclose(observed, value, rtol=2e-10, atol=2e-10)
            checks += value.size
        assert row["maximum_affine_annihilation_error"] < 1e-11
    lookup = {c["id"]: row for c, row in zip(p["cases"], rows, strict=True)}
    groups = defaultdict(dict)
    for c in p["cases"]:
        groups[tuple(c[k] for k in ["target", "position", "noise", "mode"])][c["method"]] = lookup[
            c["id"]
        ]
    measured = {
        (q["target"], q["position"], q["noise"], q["mode"], q["method"]): q for q in r["ratios"]
    }
    assert len(measured) == 768
    for key, values in groups.items():
        for method in ["hann65_grid65", "hann129_grid129"]:
            expected = (
                values[method]["phase_averaged_signal_to_noise_power"]
                / values["rect65_grid256"]["phase_averaged_signal_to_noise_power"]
            )
            assert measured[*key, method]["ratio_to_rect65"] == expected
    groups = defaultdict(list)
    for q in r["ratios"]:
        groups[tuple(q[k] for k in ["position", "noise", "mode", "method"])].append(
            q["ratio_to_rect65"]
        )
    for s in r["summary"]:
        values = groups[tuple(s[k] for k in ["position", "noise", "mode", "method"])]
        assert len(values) == s["cases"] == 48
        with localcontext() as ctx:
            ctx.prec = 50
            mean = float(sum(Decimal(str(v)) for v in values) / len(values))
        assert (
            abs(mean - s["mean"]) < 1e-12
            and s["median"] == float(np.median(values))
            and s["minimum"] == min(values)
            and s["maximum"] == max(values)
        )
        assert s["above_one"] == sum(v > 1 for v in values) and s["below_one"] == sum(
            v < 1 for v in values
        )
    assert len(groups) == 16 and "torch" not in sys.modules and "rawpy" not in sys.modules
    guard(p)
    save(
        ROOT / "verification-v1.json",
        {
            "status": "pass-independent-QR-all1152linearrows-and768ratios-and16Decimalmeans",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "independent_coordinate_checks": checks,
            "independent_ratios": 768,
            "Decimal_summary_means": 16,
            "maximum_errors": maxima,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
        },
    )
    print("PASS1152independentQRrows/", checks, "coordinates/768ratios/16Decimalmeans", flush=True)


if __name__ == "__main__":
    audit()
