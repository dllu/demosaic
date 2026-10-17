"""Audit two matched long-data arms and compare retained source-balanced scores.

No inference or model selection. The executable entry point requires completed,
exited primary/training owners; compare_panels also permits an explicitly labeled
engineering replay of real historical panels without inventing new results.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from audit_fresh_dino_statistics import CLASSICAL, audit_photo, audit_real, average, sha
from audit_nonlocal_reference_review import control_cases, control_differences
from audit_sensor_mean_artifacts import exited
from compare_saved_reference_scores import observed_keys, selected_scores

from demosaic.safety import writable_path

REGISTRIES = [
    (
        "V60-full4k-parent",
        "docs/results/wide-flat-palette-full4k-review.json",
        "b65ab9cfa235f0684959861432a4093d4e99f397baf9117ecc22523c54d0d1c2",
        "1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e",
    ),
    (
        "V58-10k",
        "docs/results/dino-convnext-pyramid-v58-10k-review.json",
        "15fb953c63f646df52ef0bf95d28479569b193c80d7073b0131b20f11fefff1b",
        "cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3",
    ),
    (
        "V43",
        "docs/results/native-corpus-2k-review.json",
        "73e7d0b1d44e121fc962e114cfe4d840ffa82130bcd71e21d78345136141a645",
        "0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5",
    ),
]
PHOTO_FIELDS = [
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
REAL_FIELDS = [
    "prepared_sha256",
    "border",
    "scenes",
    "pairs",
    "split",
    "protocol",
    "reference",
    "precision",
]


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def historical_runs(path, expected_sha256):
    if expected_sha256 is not None:
        assert sha(path) == expected_sha256, path
    registry = read(path)
    if "runs" in registry:
        return registry["runs"]
    audit = registry["audit"]
    assert sha(audit["path"]) == audit["sha256"]
    actual = read(audit["path"])
    assert actual == audit["result"]
    return actual["runs"]


def compare_pair(panel, first, second):
    """Pair actual source means only after metadata/observation/control checks."""
    fields = PHOTO_FIELDS if panel == "full427" else REAL_FIELDS
    for field in fields:
        assert first["summary"].get(field) == second["summary"].get(field), (panel, field)
    identity = (
        ["model", "kind", "id", "condition", "pattern"]
        if panel == "full427"
        else ["model", "scene", "pair", "tile_id", "pattern"]
    )
    controls = [control_cases(p["cases"], CLASSICAL, identity) for p in [second, first]]
    count = (443 * 28 if panel == "full427" else 72 if panel == "known" else 90) * 3
    assert len(controls[0]) == len(controls[1]) == count
    witness = control_differences(*controls)
    assert observed_keys(first["rows"], first["model_label"], panel) == observed_keys(
        second["rows"], second["model_label"], panel
    )
    scores = [selected_scores(p["rows"], p["model_label"], panel) for p in [first, second]]
    assert scores[0].keys() == scores[1].keys()
    comparisons = []
    for kind in ["photo", "synthetic"] if panel == "full427" else ["real"]:
        ids = sorted(k for k in scores[0] if k[0] == kind)
        assert (
            len(ids) == {"photo": 427, "synthetic": 16, "real": 4 if panel == "known" else 5}[kind]
        )
        metrics = (
            ["linear_psnr", "srgb_psnr", "srgb_ssim"]
            if panel == "full427"
            else ["sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"]
        )
        for metric in metrics:
            x, y = [np.array([v[k][metric] for k in ids]) for v in scores]
            assert np.isfinite(x).all() and np.isfinite(y).all()
            delta = x - y
            indices = np.random.default_rng(42).integers(len(ids), size=(1000, len(ids)))
            comparisons.append(
                {
                    "panel": panel,
                    "kind": kind,
                    "metric": metric,
                    "first": first["label"],
                    "second": second["label"],
                    "first_checkpoint_sha256": first["checkpoint_sha256"],
                    "second_checkpoint_sha256": second["checkpoint_sha256"],
                    "sources": len(ids),
                    "first_source_balanced_mean": average(x.tolist()),
                    "second_source_balanced_mean": average(y.tolist()),
                    "mean_first_minus_second": average(delta.tolist()),
                    "source_bootstrap_95_interval": np.quantile(
                        delta[indices].mean(1), [0.025, 0.975]
                    ).tolist(),
                }
            )
    source = {"panel": panel, "metadata_fields_exact": fields}
    for name, item in [("first", first), ("second", second)]:
        source[name] = {
            k: item[k] for k in ["label", "checkpoint_sha256", "report", "cases", "model_label"]
        }
        source[name].update(
            report_sha256=sha(item["report"]),
            cases_sha256=sha(item["cases"]),
            batch_size=item["summary"]["batch_size"],
        )
    return (
        comparisons,
        source,
        {
            "panel": panel,
            "first": first["label"],
            "second": second["label"],
            **witness,
        },
    )


def descriptor(label, digest, report, cases, summary, records):
    models = [m for m in summary["models"] if m.get("sha256", m.get("weight_sha256")) == digest]
    assert len(models) == 1, (label, digest)
    return {
        "label": label,
        "checkpoint_sha256": digest,
        "report": str(report),
        "cases": str(cases),
        "summary": summary,
        "rows": records,
        "model_label": models[0]["label"],
    }


def compare_panels(outputs, checkpoints, expected_methods=5):
    assert len(checkpoints) == 2 and len({c["sha256"] for c in checkpoints}) == 2
    histories = [
        (label, path, sha(path), digest, historical_runs(path, expected))
        for label, path, expected, digest in REGISTRIES
    ]
    statistics, sources, witnesses, comparisons = {}, [], [], []
    for panel, filename in [
        ("full427", "per-image.jsonl"),
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
    ]:
        root = Path(outputs[panel])
        statistics[panel] = (
            audit_photo(root, expected_methods)
            if panel == "full427"
            else audit_real(
                root,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                expected_methods,
                require_rawnind=False,
            )
        )
        report, cases = root / "summary.json", root / filename
        summary, records = read(report), rows(cases)
        current = [
            descriptor(c["label"], c["sha256"], report, cases, summary, records)
            for c in checkpoints
        ]
        retained = []
        for label, path, _, digest, runs in histories:
            record = runs[panel]
            old_report = Path(record.get("report", record.get("source")))
            assert sha(old_report) == record.get(
                "report_sha256", record.get("source_report_sha256")
            )
            old_cases = old_report.parent / filename
            retained.append(
                descriptor(label, digest, old_report, old_cases, read(old_report), rows(old_cases))
            )
        pairs = [(current[1], current[0])]
        pairs += [(arm, old) for arm in current for old in retained]
        for first, second in pairs:
            result, source, witness = compare_pair(panel, first, second)
            comparisons.extend(result)
            sources.append(source)
            witnesses.append(witness)
    assert len(comparisons) == 84 and len(sources) == len(witnesses) == 21
    return {
        "statistics": statistics,
        "comparisons": comparisons,
        "sources": sources,
        "witnesses": witnesses,
        "retained_registries": [
            {"label": label, "path": str(path), "sha256": digest, "checkpoint_sha256": checkpoint}
            for label, path, digest, checkpoint, _ in histories
        ],
        "resampling": {"paired_source_bootstrap": 1000, "seed": 42},
    }


def main(workflow, output):
    assert not torch.cuda.is_initialized()
    status = read(workflow)
    assert status["status"] == "completed-primary-panels-awaiting-hue-statistical-and-native-review"
    exited(status)
    plan = read(status["plan"])
    previous = Path("/mnt/external/demosaic/runs/long-commons-v63-v64-first4k-workflow-v1.json")
    training = read(previous)
    assert training["status"] == "trained-both-first4000-awaiting-controlled-quality-review"
    assert training["controller"] == plan["previous_owner"]
    assert training["checkpoints"] == status["checkpoints"]
    assert training["all161_logged_domains_LRs_and_unchanged_domain_hashes_match"]
    exited(training)
    for guard in [plan, read(training["plan"])]:
        for path, digest in {
            **guard["inputs"],
            **guard["source_files"],
            **guard.get("tools", {}),
        }.items():
            assert sha(path) == digest, path
    checkpoints = sorted(status["checkpoints"], key=lambda c: c["arm"])
    assert [c["arm"] for c in checkpoints] == ["control", "expanded"]
    for checkpoint in checkpoints:
        assert checkpoint["step"] == 4000 and sha(checkpoint["path"]) == checkpoint["sha256"]
        checkpoint["label"] = "V63-control" if checkpoint["arm"] == "control" else "V64-expanded"
    output = writable_path(output)
    assert not output.exists()
    result = {
        "status": "completed-independent-long-data-primary-statistics-and-saved-comparisons",
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "training_workflow": str(previous),
        "training_workflow_sha256": sha(previous),
        **compare_panels(status["outputs"], checkpoints),
        "driver_sha256": sha(__file__),
        "CUDA_initialized": torch.cuda.is_initialized(),
        "helper_sources": {
            str(Path(__file__).with_name(name)): sha(Path(__file__).with_name(name))
            for name in [
                "audit_fresh_dino_statistics.py",
                "audit_nonlocal_reference_review.py",
                "audit_sensor_mean_artifacts.py",
                "compare_saved_reference_scores.py",
            ]
        },
        "limitations": "Read-only primary panels; no model inference, native/hue/state completion or quality promotion. V64 minus V63 isolates declared data membership within one seed/stage. Parent comparisons also include extra updates and fresh AdamW/EMA; V43 has different history and real batch2. Keys/metadata and nullable support must match; every inherited classical drift is retained under the pre-existing four-F32-ULP bound. Source bootstrap does not measure training/selection uncertainty. No protected-final or SOTA claim.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    archive = output.parent / (output.stem + "-executed-source.py")
    assert not archive.exists()
    archive.write_bytes(Path(__file__).read_bytes())
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output), "comparisons": 84}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
