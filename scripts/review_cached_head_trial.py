"""Queue a matched cached-head review, retaining existing native display choices.

This controller never trains or restarts a worker. Numerical completion leaves
native viewing and any recommendation to a separate, explicit report.
"""

import argparse
import math
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.cli import resolve_recipe, snapshot_environment
from demosaic.experiments.evaluation.crops import display_pixels
from demosaic.experiments.evaluation.native import load_native
from demosaic.experiments.runtime import exclusive_run, owner_identity, owner_live


def paired_comparison(candidate, baseline, baseline_method):
    """Pair by ID, never by file order; retain bad tails alongside means."""
    old = {r["id"]: r for r in baseline["rows"] if r["method"] == baseline_method}
    rows = candidate["rows"]
    if len(old) != len(rows) or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Comparison requires one matching row per case")
    groups = defaultdict(list)
    for row in rows:
        previous = old.get(row["id"])
        dimensions = ("kind", "present", "variant", "noise", "cohort")
        if previous is None or any(row.get(k) != previous.get(k) for k in dimensions):
            raise ValueError(f"Mismatched comparison case: {row['id']}")
        if row["kind"] == "real":
            if row.get("reference_scored") is not False:
                raise ValueError("Independent real references must not be scored")
            continue
        group = (
            row["kind"],
            row.get("present", row.get("variant", row.get("noise"))),
            row.get("cohort"),
        )
        for field in row.keys() & previous.keys():
            a, b = row[field], previous[field]
            if (
                field.endswith(("DN16", "gain", "error"))
                and type(a) in (int, float)
                and type(b) in (int, float)
            ):
                if not math.isfinite(a) or not math.isfinite(b):
                    raise ValueError("Nonfinite comparison metric")
                groups[*group, field].append((row["id"], a, b))
    results = []
    for (kind, condition, cohort, field), values in sorted(groups.items(), key=repr):
        a, b = [np.asarray([v[i] for v in values]) for i in (1, 2)]
        delta = a - b
        worst = np.argsort(delta)[-5:][::-1]
        results.append(
            {
                "kind": kind,
                "condition": condition,
                "cohort": cohort,
                "field": field,
                "cases": len(values),
                "candidate_mean": float(a.mean()),
                "baseline_mean": float(b.mean()),
                "mean_difference": float(delta.mean()),
                "difference_quantiles": dict(
                    zip(
                        ("p05", "p50", "p95", "max"),
                        np.quantile(delta, [0.05, 0.5, 0.95, 1]).tolist(),
                    )
                ),
                "positive": int((delta > 0).sum()),
                "negative": int((delta < 0).sum()),
                "equal": int((delta == 0).sum()),
                "largest_signed_differences": [
                    {"id": values[i][0], "difference": float(delta[i])} for i in worst
                ],
            }
        )
    return results


def prepare(args):
    run = args.run.absolute()
    training = read_json(run / "plan.json")
    verify_plan(training)
    owner = read_json(run / "owner.json")
    if not owner_live(owner) and not (run / "result.json").exists():
        raise ValueError("Expected a live training process or a completed run")
    control, _ = resolve_recipe(args.control_recipe)
    treatment = training["recipe"]
    changed = {k for k in treatment.keys() | control.keys() if treatment.get(k) != control.get(k)}
    if changed - {"name", "cache", "pair_units", "evidence"}:
        raise ValueError(f"Unmatched settings: {changed}")
    baseline = read_json(args.baseline_scores)
    baseline_plan = read_json(checked(baseline["plan"]))
    if reference(args.cases) != baseline_plan["design"]:
        raise ValueError("Review must use exactly the control's cached observations")
    observations = read_json(args.cases)["observations"]
    expected = {c["id"] for c in observations}
    if len(expected) != len(observations):
        raise ValueError("Duplicate cases")
    for method in args.baseline_methods:
        rows = [r for r in baseline["rows"] if r["method"] == method]
        if len(rows) != len(expected) or {r["id"] for r in rows} != expected:
            raise ValueError("Control must cover the complete matched suite")
    root = args.output.absolute()
    root.mkdir(parents=True, exist_ok=False)
    repository = Path(__file__).resolve().parents[1]
    work, sources = freeze_sources(repository, root, [Path(__file__).name])
    plan = {
        "run": str(run),
        "training": reference(run / "plan.json"),
        "training_owner": owner,
        "root": str(root),
        "work": str(work),
        "frozen_files": sources,
        "inputs": [
            reference(p)
            for p in (
                run / "plan.json",
                args.cases,
                args.control_recipe,
                args.baseline_scores,
                args.baseline_figures,
            )
        ],
        "cases": reference(args.cases),
        "expected_cases": len(observations),
        "baseline_scores": reference(args.baseline_scores),
        "baseline_figures": reference(args.baseline_figures),
        "baseline_methods": dict(zip(("raw", "ema"), args.baseline_methods)),
        "changed_recipe_fields": sorted(changed),
        "scope": "Combined shared-edge scene/coupling intervention; no automatic quality promotion.",
    }
    write_json(root / "plan.json", plan)
    return reference(root / "plan.json")


def run_child(plan, stage, arguments):
    root, run = Path(plan["root"]), Path(plan["run"])
    training = read_json(checked(plan["training"]))
    # Run the original training snapshot's package, even after workspace edits.
    command = [sys.executable, "-m", "demosaic.experiments", *arguments]
    with (root / f"{stage}.log").open("xb") as log:
        child = subprocess.Popen(
            command, env=snapshot_environment(training), stdout=log, stderr=subprocess.STDOUT
        )
        import psutil

        identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
        write_json(
            root / "status.json",
            {"stage": stage, "owner": owner_identity(), "child": identity},
            replace=True,
        )
        result = child.wait()
    if result:
        raise RuntimeError(f"{stage} exited {result}; retained {stage}.log")
    if reference(run / "plan.json") != plan["training"]:
        raise ValueError("Training plan changed")


def audit_training(plan):
    """Read each committed row; no forwards, gradients, resampling or CUDA calls."""
    import torch

    run = Path(plan["run"])
    training = read_json(checked(plan["training"]))
    result = read_json(run / "result.json")
    if result["status"] != "completed" or result["plan"] != plan["training"]:
        raise ValueError("Training did not complete under the bound plan")
    from demosaic.experiments.data.cache import CachedBatches
    from demosaic.experiments.training import TrainingConfig

    spec = training["recipe"]
    config = TrainingConfig(**spec["training"])
    cache = CachedBatches(spec["cache"], spec["pair_units"])
    checkpoints = sorted((run / "checkpoints").glob("row-*.pt"))
    if len(checkpoints) != len(cache) or len(cache) != config.steps:
        raise ValueError("Missing committed training rows")
    updates = skipped = 0
    domains = defaultdict(int)
    for step, (path, item) in enumerate(zip(checkpoints, cache.rows, strict=True), 1):
        payload = torch.load(path, map_location="cpu", weights_only=True)
        row = payload["row"]
        if (
            path.name != f"row-{step:06d}.pt"
            or row["step"] != step
            or row["batch"] != item["arrays"]
            or row["parent"] != item["parent"]
            or row["domain"] != item["metadata"]["domain"]
            or payload["plan"] != plan["training"]
            or payload["frozen_hash"] != result["frozen_hash"]
            or row["lr"] != config.learning_rate(step)
        ):
            raise ValueError(f"Training identity mismatch at row {step}")
        updates += row["noisy"]
        skipped += not row["noisy"]
        domains[row["domain"]] += row["noisy"]
        if (
            payload["updates"] != updates
            or payload["skipped"] != skipped
            or row["updates"] != updates
            or row["ADC_skips"] != skipped
        ):
            raise ValueError("Training clock mismatch")
        for state in (payload["trainable"], payload["ema"]):
            if len(state) != 4 or sum(v.numel() for v in state.values()) != 643:
                raise ValueError("Unexpected trained head")
            if not all(torch.isfinite(v).all() for v in state.values()):
                raise ValueError("Nonfinite trained state")
        for state in payload["optimizer"]["state"].values():
            if int(state["step"]) != updates:
                raise ValueError("Adam clock mismatch")
    if (updates, skipped) != (result["updates"], result["ADC_skips"]):
        raise ValueError("Terminal training accounting mismatch")
    checked(result["checkpoint"])
    return {
        "rows": len(checkpoints),
        "updates": updates,
        "ADC_skips": skipped,
        "noisy_domains": dict(domains),
        "frozen_hash": result["frozen_hash"],
        "result": reference(run / "result.json"),
        "new_neural_forwards": 0,
    }


def render(plan, scores, exports):
    """Keep every old board, triplet, ROI and transform, replacing method cells."""
    from PIL import Image, ImageDraw, ImageFont

    root = Path(plan["root"])
    old = read_json(checked(plan["baseline_figures"]))
    out = root / "figures"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    records = []
    for index, figure in enumerate(old["images"]):
        case = figure["case"]
        with np.load(checked(case["arrays"]), allow_pickle=False) as archive:
            arrays = dict(archive)
        source = np.asarray(Image.open(checked(figure["image"])))
        if figure["triplet"]:
            state = "ema" if figure["panels"][1]["label"].endswith("EMA") else "raw"
            selections = [figure["panels"][0], state, figure["panels"][-1]]
        else:
            retained = [
                p
                for p in figure["panels"][1:]
                if p["label"] == "V195-whole-response-EMA"
                or p["label"] in plan["baseline_methods"].values()
            ]
            references = [p for p in figure["panels"] if p["label"].startswith(("Exact", "ISO"))]
            selections = [figure["panels"][0], *retained, "raw", "ema", *references]
        panel = Image.new("RGB", (8 + 168 * len(selections), 212), "#eeeeee")
        draw = ImageDraw.Draw(panel)
        draw.text(
            (8, 4),
            f"{case['id']} | native160, exposure{figure['exposure']:g}, "
            f"contrast{figure['contrast']:g}",
            font=font,
            fill="black",
        )
        cells = []
        for column, selection in enumerate(selections):
            x = 8 + 168 * column
            if isinstance(selection, str):
                binding = scores[selection]["native_predictions"][case["id"]]
                value = load_native(binding)
                anchor = np.asarray(figure["anchor"]).reshape(1, 3, 1, 1)
                value = anchor + figure["contrast"] * (value.astype(np.float64) - anchor)
                crop = display_pixels(value, arrays, figure["ROI_xywh"], figure["exposure"])
                label = "Shared-edge " + selection
                provenance = {
                    "prediction": binding,
                    "checkpoint": exports[selection],
                    "state": selection,
                }
            else:
                sx, sy, w, h = selection["xywh"]
                crop = source[sy : sy + h, sx : sx + w].copy()
                label = selection["label"]
                provenance = {"source_figure": figure["image"], "source_xywh": selection["xywh"]}
            if crop.shape != (160, 160, 3):
                raise ValueError("Every displayed cell must retain native160 pixels")
            panel.paste(Image.fromarray(crop), (x, 44))
            draw.text(
                (x, 26),
                label.replace("V200-scale-wave-", "V200 ").replace("V195-whole-response-", "V195 "),
                font=font,
                fill="black",
            )
            cells.append(dict(label=label, xywh=[x, 44, 160, 160], **provenance))
        path = out / f"comparison-{index:02d}.png"
        panel.save(path)
        records.append(
            {
                "image": reference(path),
                "case": case,
                "ROI_xywh": figure["ROI_xywh"],
                "anchor": figure["anchor"],
                "contrast": figure["contrast"],
                "exposure": figure["exposure"],
                "no_resize": True,
                "triplet": figure["triplet"],
                "panels": cells,
                "checkpoint_exports": exports,
                "reference_role": figure["reference_role"],
            }
        )
    write_json(root / "figures.json", {"images": records, "no_resize": True, "viewed": False})
    return reference(root / "figures.json")


def run(root):
    root = root.absolute()
    plan = read_json(root / "plan.json")
    verify_plan(plan)
    with exclusive_run(root):
        try:
            while not (Path(plan["run"]) / "result.json").exists():
                if not owner_live(plan["training_owner"]):
                    # Recheck terminal publication after observing process exit.
                    if not (Path(plan["run"]) / "result.json").exists():
                        raise RuntimeError("Bound training worker exited without completion")
                else:
                    write_json(
                        root / "status.json",
                        {
                            "stage": "waiting-for-training",
                            "owner": owner_identity(),
                            "training_owner": plan["training_owner"],
                        },
                        replace=True,
                    )
                    time.sleep(15)
            audit = audit_training(plan)
            write_json(root / "training-audit.json", audit)
            scores, exports, contrasts = {}, {}, {}
            baseline = read_json(checked(plan["baseline_scores"]))
            for state in ("raw", "ema"):
                endpoint = root / f"shared-edge-{state}.pt"
                run_child(
                    plan,
                    f"export-{state}",
                    ["export", plan["run"], str(endpoint), "--state", state],
                )
                exports[state] = reference(endpoint)
                output = root / f"evaluation-{state}"
                run_child(
                    plan,
                    f"evaluate-{state}",
                    ["evaluate", plan["run"], plan["cases"]["path"], str(output), "--state", state],
                )
                scores[state] = read_json(output / "scores.json")
                if scores[state]["cases"] != plan["cases"]:
                    raise ValueError("Evaluation used a different case suite")
                contrasts[state] = paired_comparison(
                    scores[state], baseline, plan["baseline_methods"][state]
                )
            figures = render(plan, scores, exports)
            verify_plan(plan)
            result = {
                "status": "evaluated-awaiting-native-viewing",
                "plan": reference(root / "plan.json"),
                "training_audit": reference(root / "training-audit.json"),
                "exports": exports,
                "scores": {s: reference(root / f"evaluation-{s}" / "scores.json") for s in scores},
                "matched_comparisons": contrasts,
                "figures": figures,
                "real_references_scored": False,
                "new_parent_forwards": 0,
                "new_noise_draws": 0,
            }
            write_json(root / "result.json", result)
            write_json(
                root / "status.json",
                {
                    "stage": result["status"],
                    "owner": owner_identity(),
                    "result": reference(root / "result.json"),
                },
                replace=True,
            )
        except BaseException as error:
            write_json(root / "failure.json", {"error": repr(error), "owner": owner_identity()})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("run", "control-recipe", "cases", "baseline-scores", "baseline-figures", "output"):
        prep.add_argument("--" + name, type=Path, required=True)
    prep.add_argument("--baseline-methods", nargs=2, required=True, metavar=("RAW", "EMA"))
    worker = sub.add_parser("run")
    worker.add_argument("root", type=Path)
    launch = sub.add_parser("launch")
    launch.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args))
    elif args.command == "run":
        run(args.root)
    else:
        root = args.root.absolute()
        plan = read_json(root / "plan.json")
        verify_plan(plan)
        with (root / "controller.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(plan["work"]) / "scripts" / Path(__file__).name),
                    "run",
                    str(root),
                ],
                env=snapshot_environment(plan),
                start_new_session=True,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        print({"pid": child.pid, "log": str(root / "controller.log")})


if __name__ == "__main__":
    main()
