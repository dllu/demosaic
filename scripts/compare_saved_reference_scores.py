"""Compare completed reference scores with saved V43 and mature fresh arms.

Require equal observation coverage/metadata and bounded shared control scores.
After an exact-replay check failed, all drift is recorded under a post-hoc
four-float32-ULP bound; no bitwise-exact replay is claimed.
This avoids rerunning unchanged networks; all cross-run precision/batch metadata
is retained. Bootstrap intervals concern evaluation sources, not training seeds.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from audit_fresh_dino_statistics import (
    CLASSICAL,
    audit_photo,
    audit_real,
    average,
    group_means,
    sha,
)
from audit_nonlocal_reference_review import (
    BASE,
    NL,
    STATUS,
    V43_SHA,
    control_cases,
    control_differences,
    read,
)

from demosaic.safety import writable_path

REGISTRY = [
    ("V43", "docs/results/native-corpus-2k-review.json"),
    ("fresh", "docs/results/dino-convnext-pyramid-v58-10k-review.json"),
]


def rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream]


def selected_scores(records, label, panel):
    chosen = [r for r in records if r["model"] == label]
    assert chosen
    if panel == "full427":
        means = group_means(chosen, ["kind", "id"])
        return means
    capture = group_means(chosen, ["scene", "pair", "pattern"])
    source_rows = [{"id": k[0], "metrics": v} for k, v in capture.items()]
    return {("real", k[0]): v for k, v in group_means(source_rows, ["id"]).items()}


def observed_keys(records, label, panel):
    fields = (
        ["kind", "id", "condition", "pattern"]
        if panel == "full427"
        else ["scene", "pair", "tile_id", "pattern"]
    )
    return {tuple(r[f] for f in fields) for r in records if r["model"] == label}


def main(output):
    status = read(STATUS)
    if status["status"] == "failed":
        raise RuntimeError("Reference workflow failed; inspect before comparing")
    output = writable_path(output)
    if output.exists():
        raise ValueError("Comparison exists; choose a new output")
    comparisons = []
    sources = []
    witnesses = []
    new_inputs = []
    for panel, filename in [
        ("full427", "per-image.jsonl"),
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
    ]:
        root = Path(status["outputs"][panel])
        current_path = root / filename
        # These three immutable panels may finish while the GPU still renders
        # GFX. Validate their complete coverage; no full-workflow claim follows.
        if panel == "full427":
            audit_photo(root, expected_methods=6)
        else:
            audit_real(
                root,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                expected_methods=6,
            )
        new_inputs.append(
            {
                "panel": panel,
                "summary": str(root / "summary.json"),
                "summary_sha256": sha(root / "summary.json"),
                "cases": str(current_path),
                "cases_sha256": sha(current_path),
            }
        )
        summary = read(root / "summary.json")
        current = rows(current_path)
        assert any(m["label"] == NL for m in summary["models"])
        nl_scores = selected_scores(current, NL, panel)
        nl_keys = observed_keys(current, NL, panel)
        for kind in ["photo", "synthetic"] if panel == "full427" else ["real"]:
            assert (
                sum(k[0] == kind for k in nl_scores)
                == ({"photo": 427, "synthetic": 16, "real": 4 if panel == "known" else 5}[kind])
            )
        for family, registry_path in REGISTRY:
            registry = read(registry_path)
            old_record = registry["runs"][panel]
            report = Path(old_record.get("report", old_record.get("source")))
            digest = old_record.get("report_sha256", old_record.get("source_report_sha256"))
            assert sha(report) == digest
            old = read(report)
            old_path = report.parent / filename
            old_rows = rows(old_path)
            keys = (
                [
                    "protocol",
                    "manifest_sha256",
                    "split",
                    "sources",
                    "synthetic_sources",
                    "patch_size",
                    "native_crop",
                    "adc_bits",
                    "adc_black",
                    "reference_target",
                    "classical_baselines",
                    "observation_and_metrics_precision",
                    "noise_pairing",
                ]
                if panel == "full427"
                else [
                    "prepared_sha256",
                    "border",
                    "scenes",
                    "pairs",
                    "split",
                    "protocol",
                    "reference",
                    "precision",
                ]
            )
            for key in keys:
                assert old.get(key) == summary.get(key), (panel, family, key)
            fields = (
                ["model", "kind", "id", "condition", "pattern"]
                if panel == "full427"
                else ["model", "scene", "pair", "tile_id", "pattern"]
            )
            a, b = [control_cases(path, CLASSICAL, fields) for path in [old_path, current_path]]
            expected = (443 * 28 if panel == "full427" else 72 if panel == "known" else 90) * 3
            assert len(a) == len(b) == expected
            witnesses.append({"panel": panel, "family": family, **control_differences(a, b)})
            labels = []
            for m in old["models"]:
                name = m["label"]
                digest = m.get("sha256", m.get("weight_sha256"))
                if family == "V43":
                    if digest == V43_SHA:
                        labels.append(("V43", name, digest))
                elif name.split(":", 1)[0] in ["0", "1", "2", "3"]:
                    labels.append(
                        (
                            ["none10k", "S10k", "B10k", "ConvNeXt10k"][int(name.split(":", 1)[0])],
                            name,
                            digest,
                        )
                    )
            assert len(labels) == (1 if family == "V43" else 4)
            sources.append(
                {
                    "panel": panel,
                    "family": family,
                    "registry": registry_path,
                    "registry_sha256": sha(registry_path),
                    "summary": str(report),
                    "summary_sha256": sha(report),
                    "cases": str(old_path),
                    "case_sha256": sha(old_path),
                    "old_batch_size": old["batch_size"],
                    "reference_outer_batch_size": summary["batch_size"],
                    "external_native_batch_size": 1,
                    "old_neural_precision": {
                        arm: next(
                            m.get("compute_precision", old.get("precision"))
                            for m in old["models"]
                            if m["label"] == label
                        )
                        for arm, label, _ in labels
                    },
                    "reference_network_precision": "IEEE float32",
                    "metadata_fields_exact": keys,
                }
            )
            for arm, label, digest in labels:
                assert observed_keys(old_rows, label, panel) == nl_keys
                scores = selected_scores(old_rows, label, panel)
                assert scores.keys() == nl_scores.keys()
                metrics = (
                    ["linear_psnr", "srgb_psnr", "srgb_ssim"]
                    if panel == "full427"
                    else ["sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"]
                )
                for kind in ["photo", "synthetic"] if panel == "full427" else ["real"]:
                    ids = sorted(k for k in nl_scores if k[0] == kind)
                    for metric in metrics:
                        x = np.array([nl_scores[k][metric] for k in ids])
                        y = np.array([scores[k][metric] for k in ids])
                        delta = x - y
                        draws = np.random.default_rng(42).integers(
                            len(delta), size=(1000, len(delta))
                        )
                        interval = np.quantile(delta[draws].mean(1), [0.025, 0.975]).tolist()
                        comparisons.append(
                            {
                                "panel": panel,
                                "kind": kind,
                                "metric": metric,
                                "first": NL,
                                "second": arm,
                                "second_original_label": label,
                                "second_checkpoint_sha256": digest,
                                "sources": len(ids),
                                "first_source_balanced_mean": average(x.tolist()),
                                "second_source_balanced_mean": average(y.tolist()),
                                "mean_first_minus_second": average(delta.tolist()),
                                "source_bootstrap_95_interval": interval,
                            }
                        )
    assert len(comparisons) == 60
    result = {
        "status": "completed-saved-case-reference-comparisons-with-bounded-classical-witnesses",
        "workflow": str(BASE / "runs/nonlocal-reference-full-workflow.json"),
        "workflow_sha256": sha(BASE / "runs/nonlocal-reference-full-workflow.json"),
        "workflow_status_at_score_audit": status["status"],
        "scope": "Completed score panels only; full artifact/native review is separate.",
        "new_score_inputs": new_inputs,
        "sources": sources,
        "witnesses": witnesses,
        "comparisons": comparisons,
        "resampling": {"paired_source_bootstrap": 1000, "seed": 42},
        "driver_sha256": sha(__file__),
        "limitations": "Saved V43 and four mature neural score sets, not new inference of those weights. V43 real batch2 vs reference outerbatch4; current fresh real batch4; photo batch2; external nativeB1/F32 vs saved neuralFP16. Observation keys/metadata and nullable support are exact. All historical control differences are recorded under a post-hoc four-float32-ULP bound, not claimed exact. Training histories/budgets differ; external NIND training/validation membership is unknown, so unseen means held out of our training only. One seed/post-hoc development comparison, no strict external disjointness, training uncertainty, SOTA or broad real-photo superiority claim.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(output), "comparisons": len(comparisons)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
