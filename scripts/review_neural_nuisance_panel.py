"""Full eight-source/CFA/repeat audit and preselected native neural-nuisance review."""

import argparse
import math
import os
import subprocess
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from audit_local_wave_panel import _scalars
from report_local_wave_panel import summarize

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").exists())
PAIRS = (
    ("V143", "conditional-local-t2"),
    ("V143", "local-t2"),
    ("conditional-local-t2", "local-t2"),
    ("global-t2", "local-t2"),
    ("H1-local-t2", "conditional-local-t2"),
)


def prepare(producer, root, *, pilot_role_errors=None, baseline_summary=None):
    plan = read_json(producer / "plan.json")
    assert plan["full_panel"] and plan["fixed_analytic_frequencies"]
    assert (len(plan["rows"]), len(plan["finite_groups"])) == (1164, 384)
    assert plan["thresholds"] == [2]
    producer_launch = reference(producer / "launch.json")
    old_roles = (
        reference(pilot_role_errors)
        if pilot_role_errors is not None
        else reference(
            REPO
            / ".cache/experiments/neural-nuisance-fixed-proposals-pilot-v1/summary-review/absolute-role-errors.json"
        )
    )
    baseline = reference(baseline_summary) if baseline_summary is not None else None
    root.mkdir(exist_ok=False)
    work, files = freeze_sources(
        REPO,
        root,
        entries=(
            "review_neural_nuisance_panel.py",
            "audit_neural_nuisance_inputs.py",
            "report_local_validated_waves.py",
            "audit_local_wave_pilot.py",
            "report_phase_aggregation.py",
            "pilot_phase_aggregation.py",
            "audit_local_wave_panel.py",
            "report_local_wave_panel.py",
            "compare_neural_nuisance_panels.py",
        ),
    )
    own = {
        "producer": str(producer),
        "producer_plan": reference(producer / "plan.json"),
        "producer_launch": producer_launch,
        "model": plan["model"],
        "pilot_role_errors": old_roles,
        "cross_study_baseline_summary": baseline,
        "work": str(work),
        "python": sys.executable,
        "script": reference(work / "scripts/review_neural_nuisance_panel.py"),
        "native_selection": {
            "sources": list(range(8)),
            "profiles": ["iso400", "iso1600", "iso6400"],
            "placements": ["near", "far"],
            "pattern": "RGGB",
            "repeat": 0,
            "role": 2,
            "ROI_xywh": [176, 176, 160, 160],
            "display_exposure": 2,
            "display_contrast": 1,
            "all12_material_protected_contexts": True,
        },
        "primary": ["conditional-local-t2", "local-t2"],
        "contrasts": PAIRS,
        "inputs": [
            reference(producer / "plan.json"),
            producer_launch,
            plan["model"],
            old_roles,
        ]
        + ([baseline] if baseline else []),
        "frozen_files": files,
        "scope": "Predeclared complete1152 finite-role/all8-source/all4-CFA/two-repeat/three-prior audit plus all12 standing contexts. Require exact producer termination and complete1164-case closure before GT/reference analysis. Stream independent metrics/all absolute roles, descriptive paired8-source bootstrap and tails. Native48 RGGB/repeat0 role2 source/noise/placement boards plus all protected/material contexts, same native160 ROI/exposure. Full inference/control sources frozen separately, no new model/RAW/noise/training work in review. Real references qualitative, not exact GT. Actual viewing remains a separate required step.",
    }
    write_json(root / "plan.json", own)
    verify_plan(own)
    return root / "plan.json"


def independent_summary_check(summary, rows, metrics):
    counts = np.array(
        [np.diff([-1, *bars, 15]) - 1 for bars in combinations(range(15), 7)], np.int64
    )
    weights = []
    for row in counts:
        remaining, weight = 8, 1
        for n in row:
            weight *= math.comb(remaining, int(n))
            remaining -= int(n)
        weights.append(weight)
    weights = np.asarray(weights, np.int64)
    assert weights.sum() == 8**8 and len(weights) == 6435
    maximum = 0.0
    fields = 0
    for mean in summary["means"]:
        selected = [
            r for r in rows if all(r[k] == mean[k] for k in ("profile", "placement", "method"))
        ]
        assert len(selected) == 64
        for key in metrics:
            maximum = max(maximum, abs(float(np.mean([r[key] for r in selected])) - mean[key]))
            fields += 1
    for contrast in summary["contrasts"]:
        cell = [r for r in rows if all(r[k] == contrast[k] for k in ("profile", "placement"))]
        for key in metrics:
            delta = []
            for source in range(8):
                means = [
                    np.mean(
                        [
                            r[key]
                            for r in cell
                            if r["source"] == source and r["method"] == contrast[method]
                        ]
                    )
                    for method in ("first", "second")
                ]
                delta.append(means[1] - means[0])
            recorded = contrast["fields"][key]
            maximum = max(
                maximum, float(np.max(np.abs(np.asarray(delta) - recorded["source_deltas"])))
            )
            boot = counts.dot(np.asarray(delta)) / 8
            order = np.argsort(boot, kind="stable")
            cumulative = np.cumsum(weights[order])
            percentiles = [
                float(boot[order[np.searchsorted(cumulative, q * 8**8)]]) for q in (0.025, 0.975)
            ]
            maximum = max(
                maximum,
                float(
                    np.max(
                        np.abs(
                            np.asarray(percentiles)
                            - recorded["source_bootstrap_percentiles_2p5_97p5"]
                        )
                    )
                ),
            )
            fields += 11
    assert maximum < 1e-10
    return {
        "fields_checked": fields,
        "maximum_absolute_error": maximum,
        "independent_count_vectors": len(counts),
        "ordered_source_resamples": int(weights.sum()),
        "scope": "Independent flat means and stars-and-bars/combinatorial enumeration of paired8-source empirical percentiles. No calibrated population-confidence claim.",
    }


def run(root):
    assert "torch" not in sys.modules
    own = read_json(root / "plan.json")
    verify_plan(own)
    assert reference(__file__) == own["script"]
    producer = Path(own["producer"])
    assert read_json(producer / "controller-result.json")["producer_stages_succeeded"]
    plan, collection = (
        read_json(checked(own["producer_plan"])),
        read_json(producer / "collection.json"),
    )
    assert collection["plan"] == own["producer_plan"]
    records = {r["id"]: r for r in collection["rows"]}
    assert len(records) == len(collection["rows"]) == len(plan["rows"]) == 1164
    assert set(records) == {r["id"] for r in plan["rows"]}
    (root / "review.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    write_json(
        root / "closed-inputs.json",
        {
            "collection": reference(producer / "collection.json"),
            "finite_scores": reference(producer / "finite-scores.json"),
            "plan": reference(root / "plan.json"),
        },
    )
    work = Path(own["work"])
    env = os.environ.copy()
    env.update(
        CUDA_VISIBLE_DEVICES="",
        PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
        OMP_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="2",
        MKL_NUM_THREADS="2",
    )

    def command(name, args):
        with (root / (name + ".log")).open("x") as log:
            subprocess.run(
                [own["python"], str(work / "scripts" / args[0]), *map(str, args[1:])],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )

    command(
        "background-audit",
        ["audit_neural_nuisance_inputs.py", producer, root / "background-independent-audit.json"],
    )
    scores = read_json(producer / "finite-scores.json")["rows"]
    methods = ["V143", *records[plan["rows"][0]["id"]]["predictions"]]
    assert len(methods) == 7 and len(scores) == 2688
    recorded = {(r["group_index"], r["method"]): r for r in scores}
    assert len(recorded) == len(scores)
    by_id = {r["id"]: r for r in plan["rows"]}
    independent, roles, metrics = [], [], None
    maximum = identity = 0.0
    for index, group in enumerate(plan["finite_groups"]):
        meta = group["metadata"]
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            target, quiet, edge = z["target"], z["quiet"], z["edge_band"]
        parent = np.load(checked(by_id[group["cases"][0]]["parent"]))
        for method in methods:
            value = (
                parent
                if method == "V143"
                else np.stack(
                    [
                        np.load(checked(records[case]["predictions"][method]))
                        for case in group["cases"]
                    ]
                )
            )
            assert (
                value.shape == target.shape
                and value.dtype == np.float32
                and np.isfinite(value).all()
            )
            scalars = _scalars(target, value, quiet, edge)
            row = recorded[index, method]
            assert all(
                row[k] == v
                for k, v in {
                    "profile": group["profile"],
                    "source": meta["recipe"]["source"],
                    "placement": meta["placement"],
                    "pattern": meta["pattern"],
                    "repeat": meta["repeat"],
                }.items()
            )
            maximum = max(maximum, max(abs(scalars[k] - row[k]) for k in scalars))
            metrics = list(scalars)
            independent.append({**row, **scalars})
            error = value.astype(np.float64) - target.astype(np.float64)
            for role in range(3):
                entry = {
                    k: row[k]
                    for k in (
                        "group_index",
                        "profile",
                        "source",
                        "placement",
                        "pattern",
                        "repeat",
                        "method",
                    )
                }
                entry["role"] = role
                for name, mask in (
                    ("full", np.ones(target.shape[-2:], bool)),
                    ("quiet", quiet),
                    ("edge", edge),
                ):
                    e = error[role][:, mask]
                    dc = e.mean(-1, keepdims=True)
                    mse, bias, spatial = (
                        float(np.mean(e**2)),
                        float(np.mean(dc**2)),
                        float(np.mean((e - dc) ** 2)),
                    )
                    identity = max(identity, abs(mse - bias - spatial))
                    for suffix, v in (("", mse), ("_DC", bias), ("_spatial", spatial)):
                        entry[name + suffix + "_RMS_DN16"] = float(np.sqrt(v) * 65535)
                roles.append(entry)
        write_json(
            root / "progress.json",
            {"groups_audited": index + 1, "expected_groups": 384, "maximum_scalar_error": maximum},
            replace=True,
        )
    assert maximum < 1e-10 and identity < 1e-14 and len(roles) == 8064
    summary = summarize(scores, methods=methods, contrast_pairs=PAIRS)
    summary_check = independent_summary_check(summary, independent, metrics)
    old_roles = read_json(checked(own["pilot_role_errors"]))["rows"]
    old_lookup = {
        (r["profile"], r["source"], r["placement"], r["method"], r["role"]): r for r in old_roles
    }
    overlap, overlap_error = 0, 0.0
    for row in roles:
        key = tuple(row[k] for k in ("profile", "source", "placement", "method", "role"))
        if row["pattern"] != "RGGB" or row["repeat"] != 0 or key not in old_lookup:
            continue
        before = old_lookup[key]
        overlap_error = max(
            overlap_error, max(abs(v - before[k]) for k, v in row.items() if isinstance(v, float))
        )
        overlap += 1
    assert overlap == 252 and overlap_error < 1e-10
    write_json(
        root / "independent-audit.json",
        {
            "collection": reference(producer / "collection.json"),
            "finite_scores": reference(producer / "finite-scores.json"),
            "script": reference(__file__),
            "scalar_fields": len(independent) * len(metrics),
            "maximum_scalar_error": maximum,
            "absolute_role_rows": len(roles),
            "maximum_MSE_DC_spatial_identity_error": identity,
            "adopted_pilot_absolute_role_rows_checked": overlap,
            "maximum_pilot_role_error": overlap_error,
            "source_summary_audit": summary_check,
            "Torch_imported": False,
            "new_neural_forwards": 0,
            "status": "passed-full-cohort-independent-metrics-roles-and-source-statistics",
        },
    )
    write_json(
        root / "absolute-role-errors.json",
        {
            "collection": reference(producer / "collection.json"),
            "rows": roles,
            "scope": "Absolute role0/1/2 errors, every source/CFA/repeat/noise/method, without role-difference cancellation.",
        },
    )
    write_json(
        root / "summary.json",
        {
            **summary,
            "rows": scores,
            "collection": reference(producer / "collection.json"),
            "independent_audit": reference(root / "independent-audit.json"),
            "scope": own["scope"],
        },
    )
    # Render only the predeclared RGGB/repeat0 views after the full collection closes.
    native = root / "native-subset"
    native.mkdir()
    groups = [
        g
        for g in plan["finite_groups"]
        if g["metadata"]["pattern"] == "RGGB" and g["metadata"]["repeat"] == 0
    ]
    ids = {case for g in groups for case in g["cases"]}
    rows = [r for r in plan["rows"] if r["id"] in ids or r["kind"] != "finite-wire"]
    assert len(groups) == 48 and len(rows) == 156
    selected = {
        **plan,
        "root": str(native),
        "work": str(work),
        "rows": rows,
        "finite_groups": groups,
        "source_complete_collection": reference(producer / "collection.json"),
        "scope": "Predeclared native subset from complete1164-case panel:8 sources/all3 priors/near-far, RGGB/repeat0 plus all12 protected/material contexts. No new inference; real references qualitative, not GT.",
    }
    write_json(native / "plan.json", selected)
    write_json(
        native / "collection.json",
        {
            **collection,
            "plan": reference(native / "plan.json"),
            "rows": [records[r["id"]] for r in rows],
            "source_complete_collection": reference(producer / "collection.json"),
            "new_neural_forwards": 0,
        },
    )
    command("native-score", ["pilot_phase_aggregation.py", "score", native])
    command("native-report", ["report_local_validated_waves.py", native])
    command("native-audit", ["audit_local_wave_pilot.py", native])
    command(
        "native-matched",
        [
            "report_phase_aggregation.py",
            native,
            native / "matched",
            "--method-label",
            "Fixed proposal NN",
            "--control-method",
            "conditional-local-t2",
            "--control-label",
            "Conditional H1 t2",
            "--skip-old-h1-equivalence",
        ],
    )
    assert "torch" not in sys.modules
    comparison = None
    if own.get("cross_study_baseline_summary"):
        command(
            "cross-study",
            [
                "compare_neural_nuisance_panels.py",
                root,
                checked(own["cross_study_baseline_summary"]),
                root / "cross-study-comparison.json",
            ],
        )
        comparison = reference(root / "cross-study-comparison.json")
    write_json(
        root / "completed.json",
        {
            "plan": reference(root / "plan.json"),
            "producer_collection": reference(producer / "collection.json"),
            "summary": reference(root / "summary.json"),
            "independent_audit": reference(root / "independent-audit.json"),
            "background_input_audit": reference(root / "background-independent-audit.json"),
            "native_report": reference(native / "matched/report.json"),
            "native_independent_audit": reference(native / "independent-audit.json"),
            "cross_study_comparison": comparison,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "status": "complete-full-neural-nuisance-panel-metrics-and-native-rendering-awaiting-actual-viewing",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--producer", type=Path)
    parser.add_argument("--pilot-role-errors", type=Path)
    parser.add_argument("--baseline-summary", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(
            prepare(
                args.producer.resolve(),
                args.root.resolve(),
                pilot_role_errors=args.pilot_role_errors,
                baseline_summary=args.baseline_summary,
            )
        )
    else:
        run(args.root.resolve())
