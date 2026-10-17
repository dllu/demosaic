"""Audit V61 primary panels and compare saved V60/parent/V43 without inference."""

import argparse
import json
from pathlib import Path

import numpy as np
from audit_fresh_dino_statistics import CLASSICAL, audit_photo, audit_real, average, sha
from audit_nonlocal_reference_review import control_cases, control_differences
from compare_saved_reference_scores import observed_keys, selected_scores

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
CANDIDATE = "f4b503c7b511c2d935ffd5dfb2f8f138c75945dfd29a83bc4fd5b2bb8a9ccf72"
REGISTRIES = [
    (
        "V60-first1k",
        "docs/results/wide-flat-palette-first1k-review.json",
        "dde398a05fc5df33167d73967d6b5f62ccf3b165f27f8c745b1fdeb45a87f19a",
    ),
    (
        "parent10k",
        "docs/results/dino-convnext-pyramid-v58-10k-review.json",
        "cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3",
    ),
    (
        "V43",
        "docs/results/native-corpus-2k-review.json",
        "0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5",
    ),
]


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def main(workflow, output):
    status = read(workflow)
    output = writable_path(output)
    if output.exists():
        raise ValueError("Score audit exists; choose a new output")
    statistics, sources, witnesses, comparisons = {}, [], [], []
    for panel, filename in [
        ("full427", "per-image.jsonl"),
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
    ]:
        root = Path(status["outputs"][panel])
        statistics[panel] = (
            audit_photo(root, 4)
            if panel == "full427"
            else audit_real(
                root,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                4,
                require_rawnind=False,
            )
        )
        current_path, current_cases = root / "summary.json", root / filename
        current, case_rows = read(current_path), rows(current_cases)
        label = next(m["label"] for m in current["models"] if m.get("sha256") == CANDIDATE)
        current_scores = selected_scores(case_rows, label, panel)
        for family, registry_path, checkpoint in REGISTRIES:
            registry = read(registry_path)
            record = registry["runs"][panel]
            old_path = Path(record.get("report", record.get("source")))
            assert sha(old_path) == record.get("report_sha256", record.get("source_report_sha256"))
            old, old_cases = read(old_path), old_path.parent / filename
            old_rows = rows(old_cases)
            old_label = next(
                m["label"]
                for m in old["models"]
                if m.get("sha256", m.get("weight_sha256")) == checkpoint
            )
            fields = (
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
            for field in fields:
                assert old.get(field) == current.get(field), (panel, family, field)
            identity = (
                ["model", "kind", "id", "condition", "pattern"]
                if panel == "full427"
                else ["model", "scene", "pair", "tile_id", "pattern"]
            )
            a, b = [control_cases(path, CLASSICAL, identity) for path in [old_cases, current_cases]]
            assert (
                len(a)
                == len(b)
                == (443 * 28 if panel == "full427" else 72 if panel == "known" else 90) * 3
            )
            witnesses.append({"panel": panel, "family": family, **control_differences(a, b)})
            sources.append(
                {
                    "panel": panel,
                    "family": family,
                    "registry": str(registry_path),
                    "registry_sha256": sha(registry_path),
                    "old_summary": str(old_path),
                    "old_summary_sha256": sha(old_path),
                    "new_summary": str(current_path),
                    "new_summary_sha256": sha(current_path),
                    "old_cases": str(old_cases),
                    "old_cases_sha256": sha(old_cases),
                    "new_cases": str(current_cases),
                    "new_cases_sha256": sha(current_cases),
                    "metadata_fields_exact": fields,
                    "old_batch_size": old["batch_size"],
                    "new_batch_size": current["batch_size"],
                }
            )
            assert observed_keys(old_rows, old_label, panel) == observed_keys(
                case_rows, label, panel
            )
            old_scores = selected_scores(old_rows, old_label, panel)
            assert current_scores.keys() == old_scores.keys()
            for kind in ["photo", "synthetic"] if panel == "full427" else ["real"]:
                ids = sorted(k for k in current_scores if k[0] == kind)
                assert (
                    len(ids)
                    == {"photo": 427, "synthetic": 16, "real": 4 if panel == "known" else 5}[kind]
                )
                for metric in (
                    ["linear_psnr", "srgb_psnr", "srgb_ssim"]
                    if panel == "full427"
                    else ["sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"]
                ):
                    x, y = [
                        np.array([r[key][metric] for key in ids])
                        for r in [current_scores, old_scores]
                    ]
                    delta = x - y
                    indices = np.random.default_rng(42).integers(len(ids), size=(1000, len(ids)))
                    comparisons.append(
                        {
                            "panel": panel,
                            "kind": kind,
                            "metric": metric,
                            "first": "V61-first1k",
                            "second": family,
                            "first_checkpoint_sha256": CANDIDATE,
                            "second_checkpoint_sha256": checkpoint,
                            "sources": len(ids),
                            "first_source_balanced_mean": average(x.tolist()),
                            "second_source_balanced_mean": average(y.tolist()),
                            "mean_first_minus_second": average(delta.tolist()),
                            "source_bootstrap_95_interval": np.quantile(
                                delta[indices].mean(1), [0.025, 0.975]
                            ).tolist(),
                        }
                    )
    assert len(comparisons) == 36 and len(witnesses) == len(sources) == 9
    result = {
        "status": "completed-independent-V61-primary-statistics-and-saved-control-comparisons",
        "workflow": str(workflow),
        "workflow_sha256_at_audit": sha(workflow),
        "statistics": statistics,
        "sources": sources,
        "witnesses": witnesses,
        "comparisons": comparisons,
        "resampling": {"paired_source_bootstrap": 1000, "seed": 42},
        "driver_sha256": sha(__file__),
        "limitations": "Read-only primary panels; no model inference or whole-workflow/native/hue completion claim. Same keys/metadata and nullable classical controls, inherited fixed four-F32-ULP bound with every difference retained. Source intervals do not quantify training/selection uncertainty. V60 matches initializer/data/schedule at1000 and isolates loss; parent includes extra training, V43 has different history and realbatch2 vs4. No protected-final or SOTA claim.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    archive = output.parent / (output.stem + "-executed-source.py")
    assert not archive.exists()
    archive.write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "output": str(output),
                "comparisons": len(comparisons),
                "primary_cases": sum(v["cases"] for v in statistics.values()),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.workflow, args.output)
