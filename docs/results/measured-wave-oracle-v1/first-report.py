"""Summarize the fixed-bank GT oracles without presenting them as inference."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.crops import display_pixels
from demosaic.experiments.evaluation.native import load_native


def report(root):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    scores = read_json(root / "scores.json")
    plan = read_json(checked(scores["plan"]))
    audit = read_json(root / "independent-audit.json")
    if audit["scores"] != reference(root / "scores.json") or not audit["status"].startswith(
        "passed-"
    ):
        raise ValueError("Require the exact independently reconstructed oracle outputs")
    methods = ["V200-ema", "complementary-ema", *plan["methods"]]
    names = [k for k in scores["rows"][0] if k.endswith(("_DN16", "_gain"))]
    summaries = []
    for method in methods:
        rows = [r for r in scores["rows"] if r["method"] == method]
        summaries.append(
            {
                "method": method,
                "views": len(rows),
                "sources": len({r["source"] for r in rows}),
                **{k: float(np.mean([r[k] for r in rows])) for k in names},
            }
        )
    by_method = {r["method"]: r for r in summaries}
    by_index = {(r["index"], r["method"]): r for r in scores["rows"]}
    paired = []
    for method in plan["methods"]:
        rows = []
        for item in plan["rows"]:
            base, new = [by_index[item["index"], m] for m in ["complementary-ema", method]]
            rows.append(
                {
                    "index": item["index"],
                    "source": base["source"],
                    **{k: new[k] - base[k] for k in names},
                }
            )
        paired.append(
            {
                "method": method,
                "rows": rows,
                "weak_response_increases": sum(r["weak_gain"] > 0 for r in rows),
                "quiet_error_increases": sum(r["quiet_error_RMS_DN16"] > 0 for r in rows),
                "weak_increment_error_increases": sum(
                    r["weak_increment_error_RMS_DN16"] > 0 for r in rows
                ),
            }
        )
    fits = read_json(checked(scores["fits"]))["rows"]
    fit_summary = []
    for method in plan["methods"]:
        rows = [r for r in fits if r["method"] == method]
        fit_summary.append(
            {
                "method": method,
                "fits": len(rows),
                "maximum_absolute_gain": max(r["maximum_absolute_gain"] for r in rows),
                "gains_at_bounds": sum(r["gains_at_bounds"] for r in rows),
                "rank_range": [
                    min(r["numerical_rank"] for r in rows),
                    max(r["numerical_rank"] for r in rows),
                ],
            }
        )
    output = root / "report"
    output.mkdir()
    write_json(
        output / "summary.json",
        {
            "scores": reference(root / "scores.json"),
            "independent_audit": reference(root / "independent-audit.json"),
            "summaries": summaries,
            "paired": paired,
            "fits": fit_summary,
            "scope": "Descriptive fixed400/far means over64 related views of8 sources. Every GT oracle uses targets to choose gains; no deployable quality gain or spatial-head capacity bound.",
        },
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), layout="constrained")
    labels = [
        "V200\nEMA",
        "Complementary\nEMA",
        "Bounded\nGT oracle",
        "Unbounded\nGT oracle",
        "Phase-free\nGT oracle",
    ]
    bars = axes[0].bar(
        np.arange(5),
        [100 * by_method[m]["weak_gain"] for m in methods],
        color=["#888888", "#4477aa", "#cc8844", "#cc8844", "#cc8844"],
    )
    axes[0].bar_label(bars, fmt="%.2f", fontsize=8)
    axes[0].set(
        xticks=np.arange(5),
        xticklabels=labels,
        ylabel="Weak-increment response (% of exact GT)",
        ylim=(0, 24),
    )
    axes[0].tick_params(axis="x", labelsize=8)
    for i, (metric, label, color) in enumerate(
        [
            ("quiet_error_RMS_DN16", "Quiet error", "#228833"),
            ("full_error_RMS_DN16", "Absolute error", "#4477aa"),
            ("weak_increment_error_RMS_DN16", "Weak-increment error", "#cc6677"),
        ]
    ):
        values = [
            100 * (by_method[m][metric] / by_method["complementary-ema"][metric] - 1)
            for m in plan["methods"]
        ]
        axes[1].bar(np.arange(3) + (i - 1) * 0.24, values, 0.24, label=label, color=color)
    axes[1].axhline(0, color="#777777", linewidth=0.6)
    axes[1].set(
        xticks=np.arange(3),
        xticklabels=labels[2:],
        ylabel="Mean RMS change versus complementary EMA (%)",
    )
    axes[1].tick_params(axis="x", labelsize=8)
    axes[1].legend(fontsize=8)
    fig.suptitle(
        "Fixed additional-wave bank: target-assisted global fits, not inference", fontsize=11
    )
    fig.savefig(output / "oracle-response-and-error.png", dpi=150)
    plt.close(fig)

    previous = read_json("docs/images/complementary-edge-response-v1/manifest.json")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []

    def board(path, parts):
        canvas = Image.new("RGB", (8 + 168 * len(parts), 192), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        panels = []
        for i, (label, pixels) in enumerate(parts):
            x = 8 + i * 168
            draw.text((x, 5), label, font=font, fill="black")
            canvas.paste(Image.fromarray(pixels), (x, 24))
            panels.append({"label": label, "xywh": [x, 24, 160, 160]})
        canvas.save(path)
        reread = np.asarray(Image.open(path))
        for panel, (_, pixels) in zip(panels, parts, strict=True):
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(reread[y : y + h, x : x + w], pixels)
        return {"image": reference(path), "panels": panels, "no_resize": True}

    for source in [0, 1]:
        item = next(
            r
            for r in plan["rows"]
            if r["metadata"]["recipe"]["source"] == source
            and r["metadata"]["pattern"] == "RGGB"
            and r["metadata"]["repeat"] == 0
        )
        old = next(
            r["triplet"]
            for r in previous["figures"]
            if r["profile"] == "iso400" and r["source"] == source and r["placement"] == "far"
        )
        if old["source"]["arrays"] != item["arrays"] or old["ROI_xywh"] != [176, 176, 160, 160]:
            raise ValueError("Old native crop has different source/ROI")
        pixels = np.array(Image.open(checked(old["image"])))
        if pixels.shape != (160, 480, 3):
            raise ValueError("Require original native noisy/learned/GT strip")
        with np.load(checked(item["arrays"]), allow_pickle=False) as z:
            arrays = {k: z[k] for k in ["wb", "matrix", "target"]}
        calibration = {k: arrays[k][2:3] for k in ["wb", "matrix"]}
        rendered = {}
        for label, value in [
            ("V200 EMA", load_native(item["anchor"])),
            ("Complementary EMA", load_native(item["learned"])),
            *[
                (
                    m,
                    np.load(
                        checked(scores["predictions"][str(item["index"])][m]), allow_pickle=False
                    ),
                )
                for m in plan["methods"]
            ],
            ("Exact GT", arrays["target"]),
        ]:
            rendered[label] = display_pixels(value[2:3], calibration, [176, 176, 160, 160], 2)
        np.testing.assert_array_equal(rendered["Complementary EMA"], pixels[:, 160:320])
        np.testing.assert_array_equal(rendered["Exact GT"], pixels[:, 320:480])
        main = board(
            output / f"source{source}-comparison.png",
            [
                ("Noisy Malvar", pixels[:, :160]),
                ("V200 EMA", rendered["V200 EMA"]),
                ("Complementary EMA", rendered["Complementary EMA"]),
                ("GT oracle: bounded", rendered["oracle-real-bounded"]),
                ("Exact GT", rendered["Exact GT"]),
            ],
        )
        relaxed = board(
            output / f"source{source}-relaxations.png",
            [
                ("GT oracle: bounded", rendered["oracle-real-bounded"]),
                ("GT oracle: unbounded", rendered["oracle-real-unbounded"]),
                ("GT oracle: phase-free", rendered["oracle-phase-free"]),
                ("Exact GT", rendered["Exact GT"]),
            ],
        )
        triplets = []
        for label in ["Complementary EMA", "oracle-real-bounded"]:
            path = (
                output
                / f"source{source}-{'learned' if label == 'Complementary EMA' else 'GT-oracle'}-triplet.png"
            )
            value = np.concatenate([pixels[:, :160], rendered[label], rendered["Exact GT"]], axis=1)
            Image.fromarray(value).save(path)
            np.testing.assert_array_equal(np.asarray(Image.open(path)), value)
            triplets.append(
                {
                    "image": reference(path),
                    "columns": ["noisy", label, "exact constructed GT"],
                    "no_resize": True,
                }
            )
        figures.append(
            {
                "source": source,
                "index": item["index"],
                "original_learned_triplet": old,
                "main": main,
                "relaxations": relaxed,
                "triplets": triplets,
                "GT_oracle_uses_target_for_fitting": True,
                "target_used_for_inference": False,
                "ROI_xywh": [176, 176, 160, 160],
                "display_exposure": 2,
                "display_contrast": 1,
                "wb": calibration["wb"].tolist(),
                "matrix": calibration["matrix"].tolist(),
                "noise_conditioning": old["noise_conditioning"],
                "checkpoint": old["checkpoint"],
            }
        )
    write_json(
        output / "figures.json",
        {
            "figures": figures,
            "plot": reference(output / "oracle-response-and-error.png"),
            "script": reference(__file__),
            "actual_viewing_pending": True,
            "new_neural_forwards": 0,
            "scope": "Two original fixed source0/source1 far/RGGB/repeat0 native160 ROIs, no resizing. Original learned/noisy/GT pixels verified against prior published strips. Target-assisted oracles are explicitly labeled and are not inference models.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    report(parser.parse_args().root.resolve())
