"""Independently reduce and publish the frozen V149 supervision diagnostics."""

import argparse
import json
import math
import shutil
import time
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def main(first, second):
    one, two = read(first / "result-v1.json"), read(second / "result-v1.json")
    plans = [read(r / "plan-v1.json") for r in [first, second]]
    assert all(x["status"] == "completed-zero-head-gradient-diagnostic" for x in [one, two])
    for p in plans:
        guard(p)
    assert plans[0]["selected"] == plans[1]["selected"]
    assert len(one["rows"]) == len(two["rows"]) == 400
    oldtrace = [json.loads(s) for s in (first / "trace-v1.jsonl").read_text().splitlines()]
    trace = [json.loads(s) for s in (second / "trace-v1.jsonl").read_text().splitlines()]
    assert oldtrace == one["rows"] and trace == two["rows"]
    checked = 0
    maximum_coefficient_difference = 0.0
    for old, new in zip(oldtrace, trace, strict=True):
        for key in old.keys() - {"bins"}:
            assert old[key] == new[key]
        for a, b in zip(old["bins"], new["bins"], strict=True):
            for key in a:
                if isinstance(a[key], dict):
                    for term, value in a[key].items():
                        delta = abs(value - b[key][term])
                        maximum_coefficient_difference = max(maximum_coefficient_difference, delta)
                        np.testing.assert_allclose(value, b[key][term], rtol=1e-10, atol=1e-18)
                        checked += 1
                else:
                    assert a[key] == b[key]
                    checked += 1
    selected = plans[1]["selected"]
    assert len(selected) == len(two["parameter_rows"]) == 100
    assert Counter(x["domain"] for x in trace) == dict.fromkeys(
        ["mesh", "weak", "photo", "mixed", "flat"], 80
    )
    for i, item in enumerate(selected):
        assert ref(item["arrays"]["path"]) == item["arrays"]
        for j, case in enumerate(item["metadata"]["cases"]):
            row = trace[4 * i + j]
            assert row["id"] == case["id"] and row["pattern"] == case["pattern"]
            assert row["batch"] == item["arrays"] and row["batch_step"] == item["step"]
    assert ref(two["parameter_vectors"]["path"]) == two["parameter_vectors"]
    arrays = dict(np.load(two["parameter_vectors"]["path"]))
    vectors = arrays["gradients"].astype(np.float64)
    names = two["parameter_vector_names"]
    assert vectors.shape == (100, len(names), 1040) and np.isfinite(vectors).all()
    assert arrays["original_steps"].tolist() == [x["step"] for x in selected]
    norms = np.einsum("bnp,bnp->bn", vectors, vectors)
    maximum_norm_difference = 0.0
    for i, row in enumerate(two["parameter_rows"]):
        assert row["step"] == selected[i]["step"] and row["batch"] == selected[i]["arrays"]
        for j, name in enumerate(names):
            value = row["parameter_squared_norm"][name]
            np.testing.assert_allclose(norms[i, j], value, rtol=1e-11, atol=1e-25)
            maximum_norm_difference = max(maximum_norm_difference, abs(norms[i, j] - value))
            checked += 1
    decimal_checks = 0
    with localcontext() as context:
        context.prec = 70
        for i in [0, 2, 7, 20, 60, 99]:
            for j in range(len(names)):
                precise = sum(Decimal.from_float(float(v)) ** 2 for v in vectors[i, j])
                np.testing.assert_allclose(float(precise), norms[i, j], rtol=1e-12, atol=1e-25)
                decimal_checks += 1
    combinations = {
        "RGB": ["pixel", "gradient"],
        "legacy_total": ["pixel", "gradient", "legacy_spectral"],
        "post_total": ["pixel", "gradient", "post_spectral"],
        "focused_post_total": ["pixel", "gradient", "focused_post_spectral"],
        "floor16_total": ["pixel16", "gradient16", "spectral16"],
    }
    maximum_linearity_relative_difference = 0.0
    for name, components in combinations.items():
        expected = sum(vectors[:, names.index(k)] for k in components)
        actual = vectors[:, names.index(name)]
        differences = np.linalg.norm(actual - expected, axis=1) / np.maximum(
            np.linalg.norm(expected, axis=1), 1e-30
        )
        assert differences.max() < 5e-5, (name, differences.max())
        maximum_linearity_relative_difference = max(
            maximum_linearity_relative_difference, float(differences.max())
        )
    assert len(two["preflight"]) == 10
    parity = [
        v
        for x in two["preflight"]
        for v in x["all1040_initial_output_parameter_gradients"].values()
    ]
    assert len(parity) == 20 and all(
        x["relative_L2_difference"] < 5e-5 and x["all_other_parameter_gradients_exact_zero"]
        for x in parity
    )
    batches = two["parameter_rows"]
    adc = np.array([x["noise"]["shot"] == x["noise"]["read"] == 0 for x in batches])
    baseline = vectors[:, names.index("legacy_total")]
    floor16 = vectors[:, names.index("floor16_total")]
    unchanged = np.all(baseline == floor16, axis=1)
    groups = []
    for domain in [None, "mesh", "weak", "flat", "mixed", "photo"]:
        mask = np.array([domain is None or x["domain"] == domain for x in batches])
        for adc_only in [True, False]:
            selection = mask & (adc == adc_only)
            groups.append(
                {
                    "domain": domain or "all-balanced-domains",
                    "ADC_only": adc_only,
                    "batches": int(selection.sum()),
                    "parameter_gradient_squared_norm_sum": {
                        name: float(norms[selection, j].sum()) for j, name in enumerate(names)
                    },
                    "unchanged_floor16_batch_gradients": int(unchanged[selection].sum()),
                }
            )
    coefficient_groups = []
    for domain in ["mesh", "weak", "flat", "mixed", "photo"]:
        for adc_only in [True, False]:
            rows = [
                x
                for x in trace
                if x["domain"] == domain
                and (x["noise"]["shot"] == x["noise"]["read"] == 0) == adc_only
            ]
            coefficient_groups.append(
                {
                    "domain": domain,
                    "ADC_only": adc_only,
                    "observations": len(rows),
                    "bins": [
                        {
                            "active_bins": sum(x["bins"][i]["active_bins"] for x in rows),
                            "matrix_field_gradient_squared_norm": {
                                name: sum(
                                    x["bins"][i]["matrix_field_gradient_squared_norm"][name]
                                    for x in rows
                                )
                                for name in names
                            },
                        }
                        for i in range(4)
                    ],
                }
            )
    owners = []
    for root, result in [(first, one), (second, two)]:
        owner = result["owner"]
        assert read(root / "launch-v1.json")["owner"] == owner
        try:
            process = psutil.Process(owner["pid"])
            state = (
                "pid-reused"
                if abs(process.create_time() - owner["created"]) > 0.01
                else process.status()
            )
        except psutil.NoSuchProcess:
            state = "absent"
        assert state in ["absent", "pid-reused", "zombie", "dead"]
        owners.append({"owner": owner, "terminal_state": state})
    summary = {
        "status": "pass-independent-projection-and-publication-audit",
        "recorded_unix_UTC": time.time(),
        "sources": [ref(first / "result-v1.json"), ref(second / "result-v1.json")],
        "auditor": ref(__file__),
        "scalar_checks": checked,
        "Decimal_reductions": decimal_checks,
        "maximum_previous_coefficient_scalar_difference": maximum_coefficient_difference,
        "maximum_parameter_norm_squared_difference": maximum_norm_difference,
        "maximum_linearity_relative_difference": maximum_linearity_relative_difference,
        "maximum_actual_parameter_gradient_relative_L2_difference": max(
            x["relative_L2_difference"] for x in parity
        ),
        "parameter_gradients_per_batch": 1040,
        "groups": groups,
        "coefficient_groups": coefficient_groups,
        "ADC_batches": int(adc.sum()),
        "noisy_batches": int((~adc).sum()),
        "noisy_batches_unchanged_floor16_gradients": int(unchanged[~adc].sum()),
        "owners": owners,
        "full_head_forward_calls_both_runs": 20,
        "additional_frequency_hidden_convolution_calls": 100,
        "new_parent_DINO_calls": 0,
        "new_noise_draws": 0,
        "optimizer_updates": 0,
        "scope": "100 first20/domain batches,400 old training observations, at zero initialization only. Independent float64/Decimal reductions of actual projected1040 parameter vectors; whole-head autograd parity on10 batches under both floors. All remaining parameter gradients are zero initially. Does not measure Adam dynamics, trained quality, the full1000-step source distribution or fresh validation. Both coefficient-only and parameter follow-up receipts remain unchanged.",
    }
    save(second / "independent-audit-v1.json", summary)
    publish(first, second, summary)


def publish(first, second, summary):
    dest = REPO / "docs/results/spectral-loss-allocation-v1"
    dest.mkdir(exist_ok=False)
    copies = {}
    for label, root in [("coefficient", first), ("parameter", second)]:
        for name in ["plan-v1.json", "result-v1.json", "status-v1.json", "launch-v1.json"]:
            source = root / name
            target = dest / f"{label}-{name}"
            shutil.copyfile(source, target)
            assert ref(source)["sha256"] == ref(target)["sha256"]
            copies[target.name] = {"original": ref(source), "public": ref(target)}
    for source in [second / "parameter-gradients-v1.npz", second / "independent-audit-v1.json"]:
        target = dest / source.name
        shutil.copyfile(source, target)
        assert ref(source)["sha256"] == ref(target)["sha256"]
        copies[target.name] = {"original": ref(source), "public": ref(target)}
    source_plans = [read(root / "plan-v1.json") for root in [first, second]]
    frozen_neural = [
        {k.rsplit("/", 1)[-1]: v for k, v in p["frozen_files"].items() if "/src/demosaic/" in k}
        for p in source_plans
    ]
    assert frozen_neural[0] == frozen_neural[1] and len(frozen_neural[0]) == 85
    save(
        dest / "sources.json",
        {
            "frozen_neural_hashes_by_filename": frozen_neural[0],
            "sources": [
                dict(ref(p), text=p.read_text())
                for p in [
                    Path(source_plans[0]["runner"]["path"]),
                    Path(source_plans[1]["runner"]["path"]),
                    Path(__file__),
                ]
            ],
        },
    )
    save(dest / "summary.json", summary)
    save(
        REPO / "docs/results/spectral-loss-allocation-v1.json",
        {
            "status": "completed-two-frozen-diagnostics-and-independent-parameter-audit",
            "recorded_unix_UTC": time.time(),
            "copies": copies,
            "sources": ref(dest / "sources.json"),
            "summary": ref(dest / "summary.json"),
            "neural_sources_unchanged": 85,
            "scope": summary["scope"],
        },
    )
    for g in summary["groups"]:
        if g["domain"] == "all-balanced-domains":
            print(
                g["ADC_only"],
                g["batches"],
                {
                    k: math.sqrt(g["parameter_gradient_squared_norm_sum"][k])
                    for k in [
                        "RGB",
                        "legacy_spectral",
                        "post_spectral",
                        "focused_post_spectral",
                        "legacy_total",
                        "floor16_total",
                    ]
                },
            )
    print(
        "PASS",
        summary["scalar_checks"],
        "scalars,",
        summary["Decimal_reductions"],
        "Decimal reductions",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args()
    main(args.first.absolute(), args.second.absolute())
