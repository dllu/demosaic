"""Compare every original control score against its ConvNeXt-panel replay."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cases(path, fields):
    result = {}
    with Path(path).open() as stream:
        for line in stream:
            row = json.loads(line)
            if row["model"].startswith("3:"):
                continue
            key = tuple(row[k] for k in fields)
            if key in result:
                raise ValueError(f"Duplicate control observation: {key}")
            result[key] = row["metrics"]
    return result


def main(steps, output):
    suffix = {1000: "1k", 10000: "10k"}[steps]
    workflow_path = BASE / (
        "runs/dino-convnext-pyramid-v58-workflow.json"
        if steps == 1000
        else "runs/dino-convnext-pyramid-v58-10k-workflow.json"
    )
    workflow = read(workflow_path)
    expected_status = (
        "completed-first1000-and-evaluation-awaiting-manual-review"
        if steps == 1000
        else "completed-to10000-and-evaluation-awaiting-manual-review"
    )
    if workflow["status"] != expected_status:
        raise ValueError("Workflow incomplete; inspect/wait without restarting it")
    output = writable_path(output)
    if output.exists():
        raise ValueError("Replay audit already exists; choose a new output")
    specs = [
        (
            "photo",
            f"synthetic-fresh-dino-capacity-{suffix}-full427",
            f"synthetic-convnext-v58-fresh-{suffix}-full427",
            "per-image.jsonl",
            ["model", "id", "kind", "condition", "pattern"],
            99232,
        ),
        (
            "known",
            f"paired-known-fresh-dino-capacity-{suffix}",
            f"paired-known-convnext-v58-fresh-{suffix}",
            "per-crop.jsonl",
            ["model", "tile_id", "pair", "pattern", "scene"],
            576,
        ),
        (
            "unseen",
            f"paired-unseen-fresh-dino-capacity-{suffix}",
            f"paired-unseen-convnext-v58-fresh-{suffix}",
            "per-crop.jsonl",
            ["model", "tile_id", "pair", "pattern", "scene"],
            720,
        ),
    ]
    metadata_fields = {
        "photo": [
            "protocol",
            "manifest_sha256",
            "split",
            "sources",
            "synthetic_sources",
            "patch_size",
            "native_crop",
            "batch_size",
            "adc_bits",
            "adc_black",
            "reference_target",
            "classical_baselines",
            "observation_and_metrics_precision",
            "noise_pairing",
        ],
        "real": [
            "prepared_sha256",
            "reference_input_scales",
            "precision",
            "border",
            "batch_size",
            "learned_model_variance_multiplier",
            "prior_window_override",
            "scenes",
            "pairs",
            "split",
            "protocol",
            "reference",
            "caveats",
            "dataset_license",
            "attribution",
        ],
    }
    panels = {}
    for panel, old_name, new_name, filename, fields, count in specs:
        old_path, new_path = (
            BASE / "evaluation" / name / filename for name in [old_name, new_name]
        )
        old_summary, new_summary = (
            read(path.parent / "summary.json") for path in [old_path, new_path]
        )
        for field in metadata_fields["photo" if panel == "photo" else "real"]:
            assert old_summary.get(field) == new_summary.get(field), (panel, field)

        def weights(summary):
            return {
                m["label"]: m.get("sha256", m.get("weight_sha256"))
                for m in summary["models"]
                if not m["label"].startswith("3:")
            }

        assert weights(old_summary) == weights(new_summary), panel
        old, new = cases(old_path, fields), cases(new_path, fields)
        assert old.keys() == new.keys() and len(old) == count, panel
        methods = defaultdict(list)
        for key in old:
            methods[key[0]].append(key)
        replay = {}
        for method, keys in methods.items():
            exact, maximum = 0, 0.0
            for key in keys:
                assert old[key].keys() == new[key].keys()
                exact += old[key] == new[key]
                for metric, a in old[key].items():
                    b = new[key][metric]
                    assert (a is None) == (b is None), (panel, method, metric)
                    if a is not None:
                        maximum = max(maximum, abs(a - b))
            if not method[0].isdigit():
                assert exact == len(keys), (panel, method, maximum)
            replay[method] = {
                "cases": len(keys),
                "exact_all_metric_cases": exact,
                "nullable_support_exact": True,
                "max_absolute_metric_difference": maximum,
            }
        panels[panel] = {
            "old_case_file": str(old_path),
            "old_case_sha256": sha(old_path),
            "new_case_file": str(new_path),
            "new_case_sha256": sha(new_path),
            "protocol_grid_data_and_control_weight_metadata_exact": True,
            "cases": count,
            "methods": replay,
        }
    result = {
        "scope": "Complete original-control saved-score replay and metadata audit only. No inference, pixel review, estimator uncertainty, training effect or quality decision.",
        "steps": steps,
        "workflow": str(workflow_path),
        "workflow_sha256": sha(workflow_path),
        "panels": panels,
        "total_control_cases": sum(p["cases"] for p in panels.values()),
        "total_exact_all_metric_cases": sum(
            m["exact_all_metric_cases"] for p in panels.values() for m in p["methods"].values()
        ),
        "driver_sha256": sha(__file__),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    output.with_suffix(".py").write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "output": str(output),
                "cases": result["total_control_cases"],
                "exact": result["total_exact_all_metric_cases"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, choices=[1000, 10000], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.steps, args.output)
