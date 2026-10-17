"""Compare an audited palette checkpoint pair with saved parent and working V43."""

import argparse
import json
from pathlib import Path

import numpy as np
from audit_fresh_dino_statistics import CLASSICAL, average, sha
from audit_nonlocal_reference_review import control_cases, control_differences
from compare_saved_reference_scores import observed_keys, selected_scores

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
AUDIT = BASE / "evaluation/wide-flat-palette-first1k-complete-audit-v1/complete-audit.json"
REGISTRIES = [
    (
        "V43",
        "docs/results/native-corpus-2k-review.json",
        "0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5",
    ),
    (
        "parent10k",
        "docs/results/dino-convnext-pyramid-v58-10k-review.json",
        "cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3",
    ),
]


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def main(output, audit_path=AUDIT):
    audit = read(audit_path)
    assert (
        audit["actual_owner_exit_confirmed"]
        and audit["common_noisy_reference_pixels_coordinates_transforms_exact"]
    )
    output = writable_path(output)
    if output.exists():
        raise ValueError("Comparison exists; choose a new output")
    comparisons, sources, witnesses = [], [], []
    for panel, filename in [
        ("full427", "per-image.jsonl"),
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
    ]:
        current_path = Path(audit["runs"][panel]["report"])
        assert sha(current_path) == audit["runs"][panel]["report_sha256"]
        current = read(current_path)
        cases_path = current_path.parent / filename
        assert sha(cases_path) == audit["control_replay"][panel]["current_sha256"]
        current_rows = rows(cases_path)
        current_labels = [
            (
                arm,
                next(
                    m["label"]
                    for m in current["models"]
                    if m.get("sha256") == audit["weights"][arm]
                ),
            )
            for arm in ["control", "wide"]
        ]
        for old_arm, registry_path, checkpoint_sha in REGISTRIES:
            registry = read(registry_path)
            record = registry["runs"][panel]
            old_path = Path(record.get("report", record.get("source")))
            assert sha(old_path) == record.get("report_sha256", record.get("source_report_sha256"))
            old = read(old_path)
            old_cases = old_path.parent / filename
            old_rows = rows(old_cases)
            old_label = next(
                m["label"]
                for m in old["models"]
                if m.get("sha256", m.get("weight_sha256")) == checkpoint_sha
            )
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
                assert old.get(key) == current.get(key), (panel, old_arm, key)
            fields = (
                ["model", "kind", "id", "condition", "pattern"]
                if panel == "full427"
                else ["model", "scene", "pair", "tile_id", "pattern"]
            )
            a, b = [control_cases(p, CLASSICAL, fields) for p in [old_cases, cases_path]]
            assert (
                len(a)
                == len(b)
                == (443 * 28 if panel == "full427" else 72 if panel == "known" else 90) * 3
            )
            witnesses.append({"panel": panel, "old_arm": old_arm, **control_differences(a, b)})
            sources.append(
                {
                    "panel": panel,
                    "old_arm": old_arm,
                    "registry": registry_path,
                    "registry_sha256": sha(registry_path),
                    "old_summary": str(old_path),
                    "old_summary_sha256": sha(old_path),
                    "old_cases": str(old_cases),
                    "old_cases_sha256": sha(old_cases),
                    "new_summary": str(current_path),
                    "new_summary_sha256": sha(current_path),
                    "new_cases": str(cases_path),
                    "new_cases_sha256": sha(cases_path),
                    "metadata_fields_exact": keys,
                    "old_batch_size": old["batch_size"],
                    "new_batch_size": current["batch_size"],
                    "neural_precision": "FP16; physical FP32",
                }
            )
            old_scores = selected_scores(old_rows, old_label, panel)
            for arm, label in current_labels:
                assert observed_keys(old_rows, old_label, panel) == observed_keys(
                    current_rows, label, panel
                )
                scores = selected_scores(current_rows, label, panel)
                assert scores.keys() == old_scores.keys()
                for kind in ["photo", "synthetic"] if panel == "full427" else ["real"]:
                    ids = sorted(k for k in scores if k[0] == kind)
                    assert (
                        len(ids)
                        == {"photo": 427, "synthetic": 16, "real": 4 if panel == "known" else 5}[
                            kind
                        ]
                    )
                    for metric in (
                        ["linear_psnr", "srgb_psnr", "srgb_ssim"]
                        if panel == "full427"
                        else ["sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"]
                    ):
                        x, y = [np.array([r[k][metric] for k in ids]) for r in [scores, old_scores]]
                        delta = x - y
                        indices = np.random.default_rng(42).integers(
                            len(ids), size=(1000, len(ids))
                        )
                        comparisons.append(
                            {
                                "panel": panel,
                                "kind": kind,
                                "metric": metric,
                                "first": arm,
                                "second": old_arm,
                                "first_checkpoint_sha256": audit["weights"][arm],
                                "second_checkpoint_sha256": checkpoint_sha,
                                "sources": len(ids),
                                "first_source_balanced_mean": average(x.tolist()),
                                "second_source_balanced_mean": average(y.tolist()),
                                "mean_first_minus_second": average(delta.tolist()),
                                "source_bootstrap_95_interval": np.quantile(
                                    delta[indices].mean(1), [0.025, 0.975]
                                ).tolist(),
                            }
                        )
    assert len(comparisons) == 48 and len(sources) == len(witnesses) == 6
    result = {
        "status": "completed-saved-parent-and-V43-palette-comparisons",
        "audit": str(audit_path),
        "audit_sha256": sha(audit_path),
        "sources": sources,
        "witnesses": witnesses,
        "comparisons": comparisons,
        "resampling": {"paired_source_bootstrap": 1000, "seed": 42},
        "driver_sha256": sha(__file__),
        "limitations": "Saved complete case logs, no new inference of old weights. Same observation keys/metadata and nullable control support; all classical drift recorded under the inherited four-float32-ULP bound, not exact replay. V43 real batch2 versus current/parent batch4; photo batch2. Neural FP16/physical FP32. These development source intervals do not quantify training seed uncertainty or multiple-comparison selection. Parent versus fine-tuned arm includes additional training; only current control versus wide isolates the palette intervention. V43 differs in initialization/history. No strict final, SOTA or broad real superiority claim.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(output), "comparisons": len(comparisons)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    a = parser.parse_args()
    main(a.output, a.audit)
