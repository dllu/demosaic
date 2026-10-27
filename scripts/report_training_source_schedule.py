"""Publish source-schedule counts and a figure from an existing metadata audit."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def reference(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("verification", type=Path)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    result = json.loads(args.audit.read_text())
    verification = json.loads(args.verification.read_text())
    assert (
        result["status"] == "passed-full-schedule-actual-reader-metadata-and-independent-selection"
    )
    assert verification["executed_result"] == reference(args.audit)
    assert verification["CSV_records_checked"] == 319824
    assert not args.receipt.exists()
    args.images.mkdir(parents=True, exist_ok=False)
    csv_path = args.receipt.with_suffix(".csv")
    rows = []
    for case in result["recipes"]:
        for fraction, counts in case["fraction_summaries"].items():
            rows.append(
                {
                    "recipe": case["label"],
                    "reviewed_fraction": fraction,
                    "actual_recipe_fraction": float(fraction) == case["actual_reviewed_fraction"],
                    **{
                        key: counts[key]
                        for key in [
                            "available_training_sources",
                            "photographic_draws",
                            "ordinary_draws",
                            "reviewed_draws",
                            "unique_photographic_sources",
                            "source_coverage_percent",
                            "source_identity_entropy_effective_count",
                        ]
                    },
                }
            )
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none"})
    fig, (mix, coverage) = plt.subplots(
        1, 2, figsize=(11.8, 4.8), gridspec_kw={"width_ratios": [1.25, 1]}
    )
    categories = [
        ("photographic-ordinary", "Commons ordinary photo", "#4477aa"),
        ("photographic-reviewed", "Commons reviewed region", "#ee7733"),
        ("weak-texture", "Commons weak synthetic", "#228833"),
        ("procedural", "Commons other synthetic", "#99bb55"),
        ("smooth-field", "Commons smooth field", "#ccbb44"),
        ("native", "Native camera target", "#aa3377"),
        ("paired", "Registered paired RAW", "#999999"),
    ]
    for position, case in enumerate(result["recipes"]):
        counts = case["fraction_summaries"][str(case["actual_reviewed_fraction"])]["families"]
        counts = {
            **counts,
            **{key: case["domain_batches"][key] * 16 for key in ["native", "paired"]},
        }
        left = 0
        for key, label, color in categories:
            width = 100 * counts[key] / case["source_context_slots"]
            mix.barh(
                position, width, left=left, color=color, label=label if position == 0 else None
            )
            if width >= 4:
                mix.text(
                    left + width / 2,
                    position,
                    f"{width:.1f}",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=9,
                )
            left += width
        assert abs(left - 100) < 1e-10
    mix.set(
        yticks=[0, 1],
        yticklabels=["V124\n5% reviewed", "V131/V132\n50% reviewed"],
        xlim=(0, 100),
        xlabel="Scheduled clean target slots (%)",
        title="Planned training mixture",
    )
    mix.invert_yaxis()
    mix.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False, fontsize=8)
    case = next(row for row in result["recipes"] if row["label"] == "V131")
    xs = [100 * float(f) for f in case["fraction_summaries"]]
    ys = [row["source_coverage_percent"] for row in case["fraction_summaries"].values()]
    coverage.plot(xs, ys, color="#4477aa", marker="o")
    actual = case["fraction_summaries"]["0.5"]
    alternative = case["fraction_summaries"]["0.05"]
    for x, counts, label in [
        (50, actual, "Actual 50% quota"),
        (5, alternative, "Counterfactual 5%"),
    ]:
        coverage.annotate(
            f"{label}\n{counts['unique_photographic_sources']:,} sources ({counts['source_coverage_percent']:.2f}%)",
            xy=(x, counts["source_coverage_percent"]),
            xytext=(-8 if x == 50 else 8, 14 if x == 50 else -37),
            textcoords="offset points",
            ha="right" if x == 50 else "left",
            fontsize=9,
        )
    coverage.set(
        xlabel="Reviewed quota within photographic draws (%)",
        ylabel="Photo corpus visited at least once (%)",
        title="Same spatial-trial seed and corpus",
        ylim=(40, 76),
        xlim=(-2, 52),
    )
    coverage.grid(axis="y", alpha=0.25)
    for ax in (mix, coverage):
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("20,000 planned updates × 16 clean target slots", y=0.98, fontsize=13)
    fig.text(
        0.99,
        0.015,
        "Source identities; augmentation diversity and trained quality are not measured.",
        ha="right",
        fontsize=8,
    )
    fig.subplots_adjust(left=0.11, right=0.98, top=0.85, bottom=0.32, wspace=0.4)
    outputs = []
    for suffix in ["png", "svg"]:
        path = args.images / f"source-coverage.{suffix}"
        fig.savefig(path, dpi=150)
        outputs.append(reference(path))
    plt.close(fig)
    receipt = {
        "status": "published-prospective-source-schedule-coverage",
        "executed_audit": reference(args.audit),
        "independent_saved_CSV_verification": reference(args.verification),
        "auditor_source": reference(Path(__file__).with_name("audit_training_source_schedule.py")),
        "reporter_source": reference(__file__),
        "table": reference(csv_path),
        "figures": outputs,
        "actual_reader_metadata_stops": sum(
            row["actual_reader_metadata_stops"] for row in result["recipes"]
        ),
        "actual_saved_trace_rows_matched": sum(
            row["actual_trace_rows_matched"] for row in result["recipes"]
        ),
        "constructor_reviewed_cache_checks": sum(
            row["constructor_reviewed_cache_checks"] for row in result["recipes"]
        ),
        "recipes": result["recipes"],
        "scope": result["scope"],
        "new_training_targets": 0,
        "geometry_augmentations": 0,
        "neural_forwards": 0,
        "noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "training_recipes_changed": False,
        "checkpoint_selection_changed": False,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": reference(args.receipt), "figures": outputs}, indent=2))


if __name__ == "__main__":
    main()
