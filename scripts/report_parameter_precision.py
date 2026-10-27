"""Publish the audited fixed-weight precision-gradient diagnostic."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from train_directional_bank_trial import read, ref, save


def report(root, destination):
    plan = read(root / "plan-v1.json")
    collection = read(root / "collection-v1.json")
    audit = read(root / "independent-audit-v1.json")
    assert audit["collection"] == ref(root / "collection-v1.json")
    assert audit["status"].startswith("passed-independent")
    destination.mkdir(parents=True, exist_ok=False)
    rows = []
    for row in collection["rows"]:
        case = row["case"]
        rows.append(
            {
                "case_index": case["index"],
                "source_id": case["source_id"],
                "stratum": "new-photo" if case["index"] < 4 else "reviewed-ROI",
                "contrast": case["contrast"],
                "condition": case["condition"],
                "eligible_blocks": case["blocks"],
                **row["summary"],
                "loss_BF16_over_FP32": row["observations"]["bfloat16"]["loss"]
                / row["observations"]["float32"]["loss"],
            }
        )
    with (destination / "gradients.csv").open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    labels = [
        f"{'Photo' if r['stratum'] == 'new-photo' else 'ROI'} ×{r['contrast']:g}\n{'ADC' if r['condition'] == 'adc-only' else 'ISO12800'}"
        for r in rows
    ]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
    axes[0].bar(x, [r["BF16_gradient_relative_L2_difference"] * 100 for r in rows], color="#bf6e2c")
    axes[0].set_ylabel("BF16 vs FP32 gradient L2 difference (%)")
    axes[0].set_xticks(x, labels, fontsize=8)
    axes[1].bar(
        x - 0.18,
        [r["FP32_training_band_gradient_cosine"] for r in rows],
        0.36,
        label="FP32 training gradient",
        color="#3878ad",
    )
    axes[1].bar(
        x + 0.18,
        [r["BF16_training_FP32_band_gradient_cosine"] for r in rows],
        0.36,
        label="BF16 training gradient",
        color="#bf6e2c",
    )
    axes[1].set_ylabel("Alignment with FP32 band-error gradient")
    axes[1].set_xticks(x, labels, fontsize=8)
    axes[1].axhline(0, color="#333333", linewidth=0.8)
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    fig.suptitle(
        "V120 fixed-weight training-gradient precision diagnosis\nTwo training sources · eight retained observations · native256/B1 · no optimizer updates",
        fontsize=11,
    )
    fig.savefig(destination / "parameter-gradient-precision.png", dpi=160)
    fig.savefig(destination / "parameter-gradient-precision.svg")
    svg = destination / "parameter-gradient-precision.svg"
    svg.write_text("\n".join(s.rstrip() for s in svg.read_text().splitlines()) + "\n")
    plt.close(fig)
    save(
        destination / "result.json",
        {
            "status": "audited-fixed-weight-precision-diagnostic-not-trained-quality",
            "plan": ref(root / "plan-v1.json"),
            "collection": ref(root / "collection-v1.json"),
            "audit": audit,
            "model": plan["model"],
            "counts": collection["counts"],
            "CUDA_peak_allocated_bytes": collection["CUDA_peak_allocated_bytes"],
            "model_backbone_config_and_rng_unchanged": collection[
                "model_backbone_config_and_rng_unchanged"
            ],
            "rows": rows,
            "case_bindings": plan["cases"],
            "report_source": ref(__file__),
            "scope": plan["scope"],
            "new_neural_forwards_in_report": 0,
            "optimizer_updates": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
        },
    )
    print({"rows": len(rows), "destination": str(destination)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    report(args.root.resolve(), args.destination.resolve())
