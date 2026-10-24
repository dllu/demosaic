"""Pair independently audited endpoints with identical inputs and supervision.

Only saved archive metadata and independently rebuilt scores are read. Network
execution, observation generation and model selection are outside this tool.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from audit_quality_archive import binding, paired_changes, write

from demosaic.safety import writable_path

STAGES = ("photo", "known", "unseen", "texture", "color")
METHOD_FIELDS = {"model", "model_index", "checkpoint_sha256", "metrics", "self_ensemble"}


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))


def read_bound(item):
    if binding(item["path"]) != item:
        raise ValueError(f"Changed comparison input: {item['path']}")
    return json.loads(Path(item["path"]).read_text())


def identity(sha256, policy="none"):
    if (not isinstance(sha256, str) or len(sha256) != 64
            or any(c not in "0123456789abcdef" for c in sha256)
            or policy not in {"none", "dihedral8"}):
        raise ValueError("Declare the exact checkpoint and inference policy")
    return {"sha256": sha256, "self_ensemble": policy}


def normalize_row(row, stage):
    result = dict(row)
    if stage in {"known", "unseen"}:
        # Early arithmetic proofs omitted an explicit pair field. The prepared
        # dataset ID encodes it unambiguously; production rows already carry it.
        fields = result["tile_id"].rsplit(":", 3)
        if (len(fields) != 4 or fields[0] != result["scene"] or len(fields[1]) != 64
                or any(c not in "0123456789abcdef" for c in fields[1])
                or not all(value.isdigit() for value in fields[2:])):
            raise ValueError("Camera tile ID does not identify its scene/capture/coordinates")
        if result.get("pair", fields[1]) != fields[1]:
            raise ValueError("Camera capture differs from its tile ID")
        result["pair"] = fields[1]
    return result


def row_key(row):
    return canonical({key: value for key, value in row.items() if key not in METHOD_FIELDS})


def audited_model(path, selected, stage):
    audit_binding = binding(path)
    audit = read_bound(audit_binding)
    if audit["stage"] != stage:
        raise ValueError("Independent audit stage differs")
    report = read_bound(audit["report"])
    models = report["checkpoints" if stage == "color" else "models"]
    matches = [(i, model) for i, model in enumerate(models)
               if model.get("sha256") == selected["sha256"]
               and model.get("self_ensemble", "none") == selected["self_ensemble"]]
    if len(matches) != 1:
        raise ValueError("Checkpoint/policy is missing or ambiguous in audited report")
    index, model = matches[0]
    label = index if stage == "color" else model["label"]
    rows = [normalize_row(row, stage) for row in read_bound(audit["independent_rows"])
            if row["checkpoint_sha256"] == selected["sha256"]
            and row["model_index" if stage == "color" else "model"] == label]
    indexed = {row_key(row): row for row in rows}
    if not rows or len(indexed) != len(rows):
        raise ValueError("Missing or duplicate independent observations")
    if binding(audit["manifest"]["path"]) != audit["manifest"]:
        raise ValueError("Changed archive manifest")
    contexts, archive_label = {}, None
    for expected_index, line in enumerate(Path(audit["manifest"]["path"]).read_text().splitlines()):
        record = json.loads(line)
        if record["schema"] != "demosaic-predictions-v1" or record["index"] != expected_index:
            raise ValueError("Archive sequence differs from its audited schema")
        if any(record["model"][key] != value for key, value in selected.items()):
            continue
        if archive_label is None:
            archive_label = record["model"]["label"]
        if archive_label != record["model"]["label"]:
            raise ValueError("Selected archive model label changed")
        context = record["context"]
        if context["stage"] != stage or not context.get("input_fingerprints"):
            raise ValueError("Missing or inconsistent archived observation context")
        key = canonical({k: v for k, v in context.items() if k != "input_fingerprints"})
        if key in contexts:
            raise ValueError("Duplicate archived observation context")
        contexts[key] = {"ids": context["ids"], "inputs": context["input_fingerprints"],
                         "supervision": record["supervision_values"]}
    observations = sum(len(value["ids"]) for value in contexts.values())
    if (not contexts or observations != len(rows)
            or audit["observations"].get(archive_label) != observations):
        raise ValueError("Selected archive and independent rows have different coverage")
    return {"audit": audit_binding, "report": audit["report"], "manifest": audit["manifest"],
            "independent_rows": audit["independent_rows"], "model": selected,
            "contexts": contexts, "rows": indexed, "observations": observations,
            "native_triplets": audit["native_triplets"]}


def metric_delta(candidate, control):
    if candidate is None or control is None:
        if candidate is not None or control is not None:
            raise ValueError("Only one method has a missing score")
        return None
    a, b = np.asarray(candidate, np.float64), np.asarray(control, np.float64)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Nonfinite or differently shaped comparison metrics")
    value = a - b
    return float(value) if value.ndim == 0 else value.tolist()


def scalar_contrast(candidate, control, stage, metric, bootstrap_draws):
    if stage == "photo":
        candidate = [row for row in candidate if row["kind"] == "photo"]
        control = [row for row in control if row["kind"] == "photo"]
    accepted = [i for i, (a, b) in enumerate(zip(candidate, control, strict=True))
                if a["metrics"][metric] is not None and b["metrics"][metric] is not None]
    missing = len(candidate) - len(accepted)
    if not accepted:
        return {"metric": metric, "shared_invalid_observations": missing, "available": False}
    result = paired_changes([candidate[i] for i in accepted], [control[i] for i in accepted],
                            stage=stage, metric=metric, bootstrap_draws=bootstrap_draws)
    return {**result, "shared_invalid_observations": missing, "available": True}


def analytic_groups(rows, stage):
    groups = defaultdict(list)
    fields = ("kind", "level", "contrast", "period", "condition") if stage == "texture" else ("condition", "palette")
    for row in rows:
        groups[canonical({key: row[key] for key in fields})].append(row)
    result = []
    for key, group in sorted(groups.items()):
        methods = {}
        for method in ("control", "candidate"):
            if stage == "color":
                bias = [max(map(abs, row[method]["camera_RGB_mean_error"])) * 65535 for row in group]
                spatial = [row[method]["spatially_centered_camera_RGB_RMS"] * 65535 for row in group]
                worst = int(np.argmax(bias))
                methods[method] = {"mean_max_channel_bias_DN16": float(np.mean(bias)),
                                   "p95_max_channel_bias_DN16": float(np.quantile(bias, .95)),
                                   "max_channel_bias_DN16": float(max(bias)),
                                   "mean_centered_RGB_RMS_DN16": float(np.mean(spatial)),
                                   "worst_observation": group[worst]["observation"]}
            else:
                methods[method] = {metric: {"mean": float(np.mean([r[method][metric] for r in group])),
                                             "maximum": float(np.max([r[method][metric] for r in group]))}
                                   for metric in group[0][method]}
                if group[0]["kind"] == "carrier":
                    methods[method]["absolute_gain_error_from_one"] = {
                        "mean": float(np.mean([abs(r[method]["in_phase_gain"] - 1) for r in group]))}
        result.append({"group": json.loads(key), "observations": len(group), **methods})
    return result


def compare_stage(control_audit, candidate_audit, control_model, candidate_model, *, stage,
                  expected_observations=None, bootstrap_draws=10000):
    if stage not in STAGES:
        raise ValueError("Compare numerical stages only; real GFX has no pixelwise GT score")
    control = audited_model(control_audit, control_model, stage)
    candidate = audited_model(candidate_audit, candidate_model, stage)
    reports = [read_bound(value["report"]) for value in (control, candidate)]
    protocols = [report.get("protocol") if stage == "photo" else report.get("border", 32)
                 for report in reports]
    if protocols[0] != protocols[1]:
        raise ValueError("Different independent scoring protocols")
    if control["contexts"].keys() != candidate["contexts"].keys():
        raise ValueError("Archive observation coverage/order differs")
    for key, old in control["contexts"].items():
        new = candidate["contexts"][key]
        if old["inputs"] != new["inputs"]:
            raise ValueError("Different noisy input values in matched archive context")
        if old["supervision"] != new["supervision"]:
            raise ValueError("Different target, mask or display values in matched archive context")
    if control["rows"].keys() != candidate["rows"].keys():
        raise ValueError("Independent observation metadata/coverage differs")
    if expected_observations is not None and len(candidate["rows"]) != expected_observations:
        raise ValueError("Incomplete declared numerical comparison")
    old_rows, new_rows, rows = [], [], []
    for key in sorted(control["rows"]):
        a, b = candidate["rows"][key], control["rows"][key]
        if a["metrics"].keys() != b["metrics"].keys():
            raise ValueError("Methods have different independent metric definitions")
        rows.append({"observation": json.loads(key), **json.loads(key),
                     "control": b["metrics"], "candidate": a["metrics"],
                     "candidate_minus_control": {name: metric_delta(a["metrics"][name], b["metrics"][name])
                                                 for name in a["metrics"]}})
        old_rows.append(b)
        new_rows.append(a)
    summaries = {}
    if stage in {"photo", "known", "unseen"}:
        metrics = ("srgb_psnr", "linear_psnr", "chroma_mae", "gradient_mae") if stage == "photo" else (
            "sensor_psnr", "ahd_srgb_psnr", "ahd_chroma_mae", "ahd_gradient_mae")
        summaries["all"] = [scalar_contrast(new_rows, old_rows, stage, name, bootstrap_draws) for name in metrics]
        if stage == "photo":
            summaries["photo_conditions"] = {
                condition: [scalar_contrast([r for r in new_rows if r["condition"] == condition],
                                            [r for r in old_rows if r["condition"] == condition],
                                            stage, name, bootstrap_draws) for name in metrics]
                for condition in sorted({r["condition"] for r in new_rows if r["kind"] == "photo"})}
        primary = "srgb_psnr" if stage == "photo" else "sensor_psnr"
        ordered = sorted((row for row in rows if row["candidate_minus_control"][primary] is not None),
                         key=lambda row: row["candidate_minus_control"][primary])
        summaries["worst_primary_changes"] = ordered[:8]
        summaries["best_primary_changes"] = ordered[-8:][::-1]
    else:
        summaries["analytic_groups"] = analytic_groups(rows, stage)
    return {"stage": stage, "control": {k: v for k, v in control.items() if k not in {"contexts", "rows", "native_triplets"}},
            "candidate": {k: v for k, v in candidate.items() if k not in {"contexts", "rows", "native_triplets"}},
            "matched_batches": len(control["contexts"]), "matched_observations": len(rows),
            "all_noisy_inputs_targets_masks_and_transforms_equal": True,
            "shared_contexts_sha256": hashlib.sha256(canonical(control["contexts"]).encode()).hexdigest(),
            "rows": rows, "summaries": summaries,
            "control_native_triplets": control["native_triplets"],
            "candidate_native_triplets": candidate["native_triplets"],
            "scope": "Differences of independently audited metrics, after exact archive-context/input/supervision matching. Source/scene intervals do not measure training-seed uncertainty. Analytic patterns are descriptive. Pixel files were validated by their independent audits; this join checks those audit/row/manifest bytes and logical value fingerprints without rereading every prediction. No inference, noise generation or automatic model choice."}


def compare(control_audit, candidate_audit, control_sha256, candidate_sha256, output, *,
            expected_observations=None):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    control, candidate = (read_bound(binding(path)) for path in (control_audit, candidate_audit))
    if set(control["stages"]) != set(STAGES) or set(candidate["stages"]) != set(STAGES):
        raise ValueError("A full endpoint comparison requires all five numerical stages")
    stages = {}
    for stage in STAGES:
        for top in (control, candidate):
            read_bound(top["stages"][stage])
        result = compare_stage(control["stages"][stage]["path"], candidate["stages"][stage]["path"],
                               identity(control_sha256), identity(candidate_sha256), stage=stage,
                               expected_observations=(expected_observations or {}).get(stage))
        write(output / f"{stage}.json", result)
        stages[stage] = binding(output / f"{stage}.json")
    result = {"control_audit": binding(control_audit), "candidate_audit": binding(candidate_audit),
              "control_sha256": control_sha256, "candidate_sha256": candidate_sha256, "stages": stages,
              "new_neural_forwards": 0, "new_encoder_forwards": 0, "new_noise_observations": 0,
              "RAW_decodes": 0, "scope": "Matched independently audited endpoints. Native/GFX review remains required; no automatic promotion."}
    write(output / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-audit", type=Path, required=True)
    parser.add_argument("--candidate-audit", type=Path, required=True)
    parser.add_argument("--control-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compare(args.control_audit, args.candidate_audit, args.control_sha256, args.candidate_sha256,
            args.output)
