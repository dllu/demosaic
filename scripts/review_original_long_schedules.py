"""Review the completed original V63/V64 schedules using retained measurements.

No training, checkpoint selection or promotion. Measurement kernels and artifact
rules come from the already executed long-data review tools. New bindings verify
the genuine isolated-resume workflow and add each arm's own first4k comparison.
"""

import argparse
import importlib.util
import json
from pathlib import Path

import torch
from audit_long_commons_artifacts import audit_panels
from audit_sensor_mean_artifacts import exited
from compare_long_commons_scores import compare_pair, compare_panels, descriptor, read, rows, sha
from evaluate_color_grid_cuda import evaluate_records
from evaluate_long_commons_grid import PARENT, retained_records

from demosaic.safety import writable_path


def completed(primary_path, training_path):
    """Require the actual closed original20000 owners before any output/inference."""
    primary, training = read(primary_path), read(training_path)
    if primary["status"] != "completed-primary-panels-awaiting-hue-statistical-and-native-review":
        raise RuntimeError("Original20000 primary evaluation is incomplete")
    exited(primary)
    if (
        training["status"]
        != "completed-both-original20000-schedules-awaiting-full-quality-and-native-review"
    ):
        raise RuntimeError("Original20000 training is incomplete")
    exited(training)
    plan, train_plan = read(primary["plan"]), read(training["plan"])
    assert plan["previous_owner"] == training["controller"]
    assert train_plan["original_planned_updates"] == 20000
    assert train_plan["resumed_from_step"] == 4000
    assert training["all802_logged_step_domain_LR_fields_match_between_arms"]
    for path, digest in {
        **plan["inputs"],
        **plan["source_files"],
        **plan["tools"],
        **train_plan["guards"],
    }.items():
        assert sha(path) == digest, path
    checkpoints = sorted(primary["checkpoints"], key=lambda x: x["arm"])
    assert [c["arm"] for c in checkpoints] == ["control", "expanded"]
    for c in checkpoints:
        boundary = training["completed"][c["arm"]]
        assert boundary["step"] == boundary["original_planned_updates"] == c["step"] == 20000
        assert boundary["finite91model91EMA89Adam"]
        assert boundary["training_log"]["train_rows"] == 802
        assert boundary["frozen_checkpoint"] == {k: c[k] for k in ["path", "sha256"]}
        assert sha(c["path"]) == c["sha256"]
        c["label"] = ("V63-control" if c["arm"] == "control" else "V64-expanded") + "-original20k"
    return primary, training, train_plan, checkpoints


def compare_progress(outputs, checkpoints, prior_review):
    """Compare saved observations to the same arm's genuine4k trajectory boundary."""
    assert prior_review["review_complete"]
    boundary = prior_review["boundary"]
    comparisons, sources, witnesses = [], [], []
    for panel, filename in [
        ("full427", "per-image.jsonl"),
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
    ]:
        report = Path(outputs[panel]) / "summary.json"
        cases = report.parent / filename
        summary, records = read(report), rows(cases)
        for c in checkpoints:
            old = boundary[c["arm"]]["checkpoint"]
            assert old["step"] == boundary[c["arm"]]["step"] == 4000
            saved = [
                item[role]
                for item in prior_review["primary_statistics"]["sources"]
                for role in ["first", "second"]
                if item["panel"] == panel and item[role]["checkpoint_sha256"] == old["sha256"]
            ]
            assert saved and all(x == saved[0] for x in saved)
            retained = saved[0]
            assert sha(retained["report"]) == retained["report_sha256"]
            assert sha(retained["cases"]) == retained["cases_sha256"]
            first = descriptor(c["label"], c["sha256"], report, cases, summary, records)
            second = descriptor(
                retained["label"] + "-first4k-same-schedule",
                old["sha256"],
                retained["report"],
                retained["cases"],
                read(retained["report"]),
                rows(retained["cases"]),
            )
            result, source, witness = compare_pair(panel, first, second)
            comparisons.extend(result)
            sources.append(source)
            witnesses.append(witness)
    assert len(comparisons) == 24 and len(sources) == len(witnesses) == 6
    return {"comparisons": comparisons, "sources": sources, "witnesses": witnesses}


def write(output, result):
    output = writable_path(output)
    assert not output.exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


def hue_records(checkpoints, reuse_report):
    retained = retained_records(reuse_report)
    records = [retained[0]]
    for c in checkpoints:
        records.append(
            {
                "path": c["path"],
                "sha256": c["sha256"],
                "kind": "joint-checkpoint",
                "arm": c["arm"] + f"-original{c['step'] // 1000}k",
                "comparison_role": "matched-long-data-" + c["arm"],
            }
        )
    return records + [retained[1]]


def main(args):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    primary, training, plan, checkpoints = completed(args.workflow, args.training_workflow)
    common = {
        "workflow": str(args.workflow),
        "workflow_sha256": sha(args.workflow),
        "training_workflow": str(args.training_workflow),
        "training_workflow_sha256": sha(args.training_workflow),
        "driver_sha256": sha(__file__),
    }
    if args.action == "scores":
        old_review = Path(plan["review"]["path"])
        assert sha(old_review) == plan["review"]["sha256"]
        statistics = compare_panels(primary["outputs"], checkpoints)
        progress = compare_progress(primary["outputs"], checkpoints, read(old_review))
        for field in ["comparisons", "sources", "witnesses"]:
            statistics[field].extend(progress[field])
        assert len(statistics["comparisons"]) == 108
        assert len(statistics["witnesses"]) == 27
        write(
            args.output,
            {
                "status": "completed-original20k-long-data-statistics-and-4k-progress",
                **common,
                **statistics,
                "CUDA_initialized": torch.cuda.is_initialized(),
                "prior_review": {"path": str(old_review), "sha256": sha(old_review)},
                "limitations": "One seed. V64 minus V63 isolates original data membership within this matched stage. Own4k-to20k comparisons are progress along each original trajectory, not architecture/seed ablations or proof of convergence. Source bootstrap does not include training/selection uncertainty. Historical V60/V58/V43 training differs; V43 paired batch differs. No protected-final scores, inference or promotion.",
            },
        )
    elif args.action == "hue":
        assert all(x is not None for x in [args.inputs, args.reuse_report, args.reuse_audit])
        records = hue_records(checkpoints, args.reuse_report)
        evaluate_records(
            args.inputs,
            args.workflow,
            args.output,
            records,
            PARENT,
            20000,
            args.reuse_report,
            args.reuse_audit,
        )
        (args.output / "source" / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    else:
        auditor = Path(training["plan"]).parent / "audit_long_commons_full20k_state.py"
        assert sha(auditor) == plan["guards"][str(auditor)]
        spec = importlib.util.spec_from_file_location("original20k_state_auditor", auditor)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        states = {
            c["arm"]: module.audit(plan, c["arm"], Path(c["path"]), 20000) for c in checkpoints
        }
        artifacts = audit_panels(primary["outputs"], checkpoints)
        assert len(artifacts["images"]) == 38
        assert len(artifacts["float_arrays"]) == 26 and len(artifacts["full_RGB16_files"]) == 4
        write(
            args.output / "audit.json",
            {
                "status": "completed-original20k-long-data-state-native-and-RGB16-integrity-audit",
                **common,
                "boundary": states,
                **artifacts,
                "CUDA_initialized": torch.cuda.is_initialized(),
            },
        )
        (args.output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    assert args.action == "hue" or not torch.cuda.is_initialized()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scores", "hue", "artifacts"])
    for name in ["workflow", "training-workflow", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ["inputs", "reuse-report", "reuse-audit"]:
        parser.add_argument("--" + name, type=Path)
    main(parser.parse_args())
